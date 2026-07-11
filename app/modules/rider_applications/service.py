from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.auth.notifications import send_email_message
from app.modules.notifications.service import NotificationService
from app.modules.rider_applications.models import RiderApplication
from app.modules.rider_applications.repository import RiderApplicationRepository
from app.modules.rider_applications.schemas import RiderApplicationCreateRequest, RiderApplicationResponse
from app.tasks.notifications import send_email_task, send_user_push_task


class RiderApplicationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = RiderApplicationRepository(session)
        self.notifications = NotificationService(session)

    async def create_application(self, *, current_user: User, payload: RiderApplicationCreateRequest) -> RiderApplicationResponse:
        if any((item.role.code == "rider") for item in current_user.roles):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This account already has rider access.")

        latest = await self.repository.get_latest_application_for_user(current_user.id)
        if latest is not None and latest.status in {"submitted", "approved"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have an active rider application.",
            )

        application = RiderApplication(
            user_id=current_user.id,
            status="submitted",
            full_name=(payload.full_name or current_user.full_name).strip(),
            email=(payload.email or current_user.email),
            phone=(payload.phone or current_user.phone),
            city_area=payload.city_area.strip(),
            address=payload.address.strip() if payload.address else None,
            vehicle_type=payload.vehicle_type.strip(),
            availability=payload.availability.strip(),
            notes=payload.notes.strip() if payload.notes else None,
        )
        await self.repository.create_application(application)
        await self.repository.commit()

        stored = await self.repository.get_application_by_id(application.id)
        if stored is None:
            raise HTTPException(status_code=500, detail="Rider application creation failed.")

        await self._notify_admins_about_application(stored)
        return self._build_response(stored)

    async def list_my_applications(self, user_id: int) -> list[RiderApplicationResponse]:
        applications = await self.repository.list_user_applications(user_id)
        return [self._build_response(application) for application in applications]

    async def list_admin_applications(self) -> list[RiderApplicationResponse]:
        applications = await self.repository.list_all_applications()
        return [self._build_response(application) for application in applications]

    async def approve_application(self, *, application_id: int, admin_user: User, admin_notes: str | None = None) -> RiderApplicationResponse:
        application = await self.repository.get_application_by_id(application_id)
        if application is None:
            raise HTTPException(status_code=404, detail="Rider application not found.")
        if application.status == "approved":
            return self._build_response(application)

        application.status = "approved"
        application.admin_notes = admin_notes.strip() if admin_notes else application.admin_notes
        application.reviewed_by_user_id = admin_user.id
        application.reviewed_at = datetime.now(UTC)

        rider_role = await self.repository.get_role_by_code("rider")
        if rider_role is None:
            raise HTTPException(status_code=500, detail="Rider role is missing.")

        already_has_role = any(item.role.code == "rider" for item in application.user.roles)
        if not already_has_role:
            await self.repository.add_user_role(user_id=application.user_id, role_id=rider_role.id)

        await self.repository.commit()
        refreshed = await self.repository.get_application_by_id(application.id)
        if refreshed is None:
            raise HTTPException(status_code=500, detail="Failed to approve rider application.")

        await self._notify_applicant(refreshed, title="Your rider application was approved", body="You can now access the rider board.", deep_link="/rider")
        return self._build_response(refreshed)

    async def reject_application(self, *, application_id: int, admin_user: User, admin_notes: str | None = None) -> RiderApplicationResponse:
        application = await self.repository.get_application_by_id(application_id)
        if application is None:
            raise HTTPException(status_code=404, detail="Rider application not found.")
        if application.status == "rejected":
            return self._build_response(application)

        application.status = "rejected"
        application.admin_notes = admin_notes.strip() if admin_notes else application.admin_notes
        application.reviewed_by_user_id = admin_user.id
        application.reviewed_at = datetime.now(UTC)
        await self.repository.commit()

        refreshed = await self.repository.get_application_by_id(application.id)
        if refreshed is None:
            raise HTTPException(status_code=500, detail="Failed to reject rider application.")

        await self._notify_applicant(
            refreshed,
            title="Your rider application was reviewed",
            body="Please check the admin notes and try again if needed.",
            deep_link="/become-a-rider",
        )
        return self._build_response(refreshed)

    async def _notify_admins_about_application(self, application: RiderApplication) -> None:
        admins = await self.repository.list_users_by_role_codes(["super_admin", "ops_admin"])
        if not admins:
            return

        deep_link = "/manage/rider-applications"
        payload = {
            "event": "rider_application_submitted",
            "event_id": f"rider-application-{application.id}-submitted",
            "audience": "admin",
            "category": "rider_application",
            "application_id": application.id,
            "user_id": application.user_id,
            "title": "New rider application",
            "body": f"{application.full_name} applied to become a rider.",
            "deep_link": deep_link,
            "tag": f"rider-application-{application.id}",
        }

        for admin in admins:
            try:
                await self.notifications.create_notification_from_payload(
                    recipient_user_id=admin.id,
                    payload=payload,
                    actor_user_id=application.user_id,
                )
            except Exception:
                pass

            try:
                if admin.email:
                    try:
                        send_email_task.delay(
                            recipient=admin.email,
                            subject="New rider application submitted",
                            body=(
                                f"A new rider application was submitted.\n\n"
                                f"Name: {application.full_name}\n"
                                f"Email: {application.email or 'n/a'}\n"
                                f"Phone: {application.phone or 'n/a'}\n"
                                f"City/Area: {application.city_area}\n"
                                f"Vehicle type: {application.vehicle_type}\n"
                                f"Availability: {application.availability}\n"
                                f"Notes: {application.notes or 'n/a'}\n\n"
                                f"Open the admin dashboard to review: {deep_link}\n"
                            ),
                        )
                    except Exception:
                        await send_email_message(
                            recipient=admin.email,
                            subject="New rider application submitted",
                            body=(
                                f"A new rider application was submitted.\n\n"
                                f"Name: {application.full_name}\n"
                                f"Email: {application.email or 'n/a'}\n"
                                f"Phone: {application.phone or 'n/a'}\n"
                                f"City/Area: {application.city_area}\n"
                                f"Vehicle type: {application.vehicle_type}\n"
                                f"Availability: {application.availability}\n"
                                f"Notes: {application.notes or 'n/a'}\n\n"
                                f"Open the admin dashboard to review: {deep_link}\n"
                            ),
                        )
            except Exception:
                pass

            try:
                send_user_push_task.delay(user_id=admin.id, payload=payload)
            except Exception:
                await self.notifications.send_web_push_to_user(user_id=admin.id, payload=payload)
                await self.notifications.send_fcm_to_user(user_id=admin.id, payload=payload)

    async def _notify_applicant(self, application: RiderApplication, *, title: str, body: str, deep_link: str) -> None:
        payload = {
            "event": "rider_application_status_changed",
            "event_id": f"rider-application-{application.id}-{application.status}",
            "audience": "customer",
            "category": "rider_application",
            "application_id": application.id,
            "title": title,
            "body": body,
            "deep_link": deep_link,
            "tag": f"rider-application-{application.id}",
        }

        if application.email:
            try:
                try:
                    send_email_task.delay(
                        recipient=application.email,
                        subject=title,
                        body=f"{body}\n\nOpen: {deep_link}\n",
                    )
                except Exception:
                    await send_email_message(
                        recipient=application.email,
                        subject=title,
                        body=f"{body}\n\nOpen: {deep_link}\n",
                    )
            except Exception:
                pass

        try:
            await self.notifications.create_notification_from_payload(
                recipient_user_id=application.user_id,
                payload=payload,
                actor_user_id=None,
            )
        except Exception:
            pass

        try:
            send_user_push_task.delay(user_id=application.user_id, payload=payload)
        except Exception:
            await self.notifications.send_web_push_to_user(user_id=application.user_id, payload=payload)
            await self.notifications.send_fcm_to_user(user_id=application.user_id, payload=payload)

    def _build_response(self, application: RiderApplication) -> RiderApplicationResponse:
        return RiderApplicationResponse(
            id=application.id,
            user_id=application.user_id,
            status=application.status,
            full_name=application.full_name,
            email=application.email,
            phone=application.phone,
            city_area=application.city_area,
            address=application.address,
            vehicle_type=application.vehicle_type,
            availability=application.availability,
            notes=application.notes,
            admin_notes=application.admin_notes,
            reviewed_by_user_id=application.reviewed_by_user_id,
            reviewed_by_user_name=getattr(application.reviewed_by_user, "full_name", None),
            reviewed_at=application.reviewed_at,
            created_at=application.created_at,
            updated_at=application.updated_at,
        )
