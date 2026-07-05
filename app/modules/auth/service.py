from __future__ import annotations

from datetime import UTC, datetime, timedelta
from secrets import randbelow

from fastapi import HTTPException, Request, status
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.modules.auth.google_auth import verify_google_credential
from app.modules.auth.models import AuthAuditLog, AuthRateLimit, PasswordResetCode, RefreshSession, User, UserStatus
from app.modules.auth.notifications import send_password_reset_code, smtp_is_configured
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import (
    AuthResponse,
    AuthTokens,
    ChangePasswordRequest,
    GoogleLoginRequest,
    LoginRequest,
    RegisterRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RoleSummary,
    UserSummary,
)
from app.modules.integrations.pos.lookup import lookup_pos_link_status
from app.modules.integrations.pos.models import ExternalUserLink
from app.modules.workspaces.schemas import WorkspaceSummary
from app.modules.workspaces.service import WorkspaceService
from app.utils.security import get_password_hash, verify_password


class AuthService:
    def __init__(self, repo: AuthRepository):
        self.repo = repo

    async def register(self, payload: RegisterRequest, request: Request | None = None) -> AuthResponse:
        await self._enforce_rate_limit(
            action="register",
            key=self._compose_rate_limit_key(request, payload.email or payload.phone or "unknown"),
            request=request,
            identifier=payload.email or payload.phone,
        )
        if payload.email and await self.repo.get_user_by_email(payload.email):
            await self._audit(
                action="register",
                outcome="failed",
                identifier=payload.email,
                request=request,
                detail={"reason": "email_in_use"},
            )
            await self.repo.commit()
            raise HTTPException(status_code=409, detail="Email is already in use.")
        if payload.phone and await self.repo.get_user_by_phone(payload.phone):
            await self._audit(
                action="register",
                outcome="failed",
                identifier=payload.phone,
                request=request,
                detail={"reason": "phone_in_use"},
            )
            await self.repo.commit()
            raise HTTPException(status_code=409, detail="Phone is already in use.")

        user = User(
            full_name=payload.full_name.strip(),
            email=payload.email.lower() if payload.email else None,
            phone=payload.phone,
            password_hash=get_password_hash(payload.password),
            status=UserStatus.active,
            is_active=True,
            is_verified=False,
        )
        await self.repo.create_user(user)

        customer_role = await self.repo.get_role_by_code("customer")
        if customer_role is None:
            raise HTTPException(status_code=500, detail="Base role setup is missing.")
        await self.repo.add_user_role(user.id, customer_role.id)
        workspace_service = WorkspaceService(self.repo.db)
        await workspace_service.ensure_customer_workspace(user)

        hydrated = await self.repo.get_user_by_id(user.id)
        if hydrated is None:
            raise HTTPException(status_code=500, detail="User hydration failed after registration.")
        tokens = await self._issue_tokens(hydrated, request)
        await self._audit(
            action="register",
            outcome="success",
            identifier=hydrated.email or hydrated.phone,
            user_id=hydrated.id,
            request=request,
        )
        await self.repo.commit()
        return await self._build_auth_response(hydrated, tokens)

    async def login(self, payload: LoginRequest, request: Request | None = None) -> AuthResponse:
        normalized_identifier = payload.identifier.strip()
        await self._enforce_rate_limit(
            action="login",
            key=self._compose_rate_limit_key(request, normalized_identifier),
            request=request,
            identifier=normalized_identifier,
        )
        user = await self.repo.get_user_for_login(normalized_identifier)
        if user is None or user.password_hash is None:
            await self._audit(
                action="login",
                outcome="failed",
                identifier=normalized_identifier,
                request=request,
                detail={"reason": "invalid_credentials"},
            )
            await self.repo.commit()
            raise HTTPException(status_code=401, detail="Invalid credentials.")
        if not verify_password(payload.password, user.password_hash):
            await self._audit(
                action="login",
                outcome="failed",
                identifier=normalized_identifier,
                user_id=user.id,
                request=request,
                detail={"reason": "invalid_credentials"},
            )
            await self.repo.commit()
            raise HTTPException(status_code=401, detail="Invalid credentials.")
        if not user.is_active:
            await self._audit(
                action="login",
                outcome="failed",
                identifier=normalized_identifier,
                user_id=user.id,
                request=request,
                detail={"reason": "inactive_account"},
            )
            await self.repo.commit()
            raise HTTPException(status_code=403, detail="Account is inactive.")

        await self._ensure_user_workspace(user)
        user.last_login_at = datetime.now(UTC)
        tokens = await self._issue_tokens(user, request)
        await self._audit(
            action="login",
            outcome="success",
            identifier=normalized_identifier,
            user_id=user.id,
            request=request,
        )
        await self.repo.commit()
        return await self._build_auth_response(user, tokens)

    async def login_with_google(
        self,
        payload: GoogleLoginRequest,
        request: Request | None = None,
    ) -> AuthResponse:
        await self._enforce_rate_limit(
            action="google_login",
            key=self._compose_rate_limit_key(request, "google_login"),
            request=request,
            identifier="google_login",
        )
        if not settings.google_client_id:
            raise HTTPException(status_code=503, detail="Google sign-in is not configured.")

        try:
            token_payload = await verify_google_credential(payload.credential)
        except ValueError as exc:
            await self._audit(
                action="google_login",
                outcome="failed",
                request=request,
                detail={"reason": f"invalid_google_token:{exc}"},
            )
            await self.repo.commit()
            raise HTTPException(status_code=401, detail="Google credential is invalid.") from exc

        email = token_payload.get("email")
        google_sub = token_payload.get("sub")
        email_verified = bool(token_payload.get("email_verified"))
        full_name = token_payload.get("name") or "Google User"
        picture = token_payload.get("picture")

        if not google_sub or not email:
            await self._audit(
                action="google_login",
                outcome="failed",
                request=request,
                detail={"reason": "missing_google_identity_fields"},
            )
            await self.repo.commit()
            raise HTTPException(status_code=400, detail="Google account payload is incomplete.")

        link = await self.repo.get_external_user_link(system_name="google", external_user_id=google_sub)
        if link:
            user = await self.repo.get_user_by_id(link.user_id)
        else:
            user = await self.repo.get_user_by_email(email)

        if user is None:
            user = User(
                full_name=full_name.strip(),
                email=email.lower(),
                phone=None,
                password_hash=None,
                avatar_url=picture,
                status=UserStatus.active,
                is_active=True,
                is_verified=email_verified,
            )
            await self.repo.create_user(user)

            customer_role = await self.repo.get_role_by_code("customer")
            if customer_role is None:
                raise HTTPException(status_code=500, detail="Base role setup is missing.")
            await self.repo.add_user_role(user.id, customer_role.id)
            workspace_service = WorkspaceService(self.repo.db)
            await workspace_service.ensure_customer_workspace(user)
        else:
            user.full_name = user.full_name or full_name.strip()
            user.avatar_url = picture or user.avatar_url
            user.is_verified = user.is_verified or email_verified
            user.is_active = True
            user.status = UserStatus.active
            workspace_service = WorkspaceService(self.repo.db)
            await workspace_service.ensure_customer_workspace(user)

        if link is None:
            await self.repo.create_external_user_link(
                ExternalUserLink(
                    user_id=user.id,
                    system_name="google",
                    external_user_id=google_sub,
                    external_role_snapshot="google_account",
                    external_restaurant_id=None,
                    match_source="oauth",
                    metadata_json={"email": email, "picture": picture},
                )
            )

        hydrated = await self.repo.get_user_by_id(user.id)
        if hydrated is None:
            raise HTTPException(status_code=500, detail="User hydration failed after Google sign-in.")

        hydrated.last_login_at = datetime.now(UTC)
        tokens = await self._issue_tokens(hydrated, request)
        await self._audit(
            action="google_login",
            outcome="success",
            identifier=email,
            user_id=hydrated.id,
            request=request,
        )
        await self.repo.commit()
        return await self._build_auth_response(hydrated, tokens)

    async def refresh(self, refresh_token: str, request: Request | None = None) -> AuthResponse:
        payload = decode_token(refresh_token, expected_type="refresh")
        session = await self.repo.get_refresh_session(payload["jti"])
        if session is None or session.revoked_at is not None or session.expires_at <= datetime.now(UTC):
            await self._audit(
                action="refresh",
                outcome="failed",
                request=request,
                detail={"reason": "invalid_refresh_token"},
            )
            await self.repo.commit()
            raise HTTPException(status_code=401, detail="Refresh token is invalid.")

        user = await self.repo.get_user_by_id(int(payload["sub"]))
        if user is None or not user.is_active:
            await self._audit(
                action="refresh",
                outcome="failed",
                user_id=int(payload["sub"]),
                request=request,
                detail={"reason": "user_unavailable"},
            )
            await self.repo.commit()
            raise HTTPException(status_code=401, detail="User is not available.")

        await self._ensure_user_workspace(user)
        await self.repo.revoke_refresh_session(session)
        tokens = await self._issue_tokens(user, request)
        await self._audit(
            action="refresh",
            outcome="success",
            identifier=user.email or user.phone,
            user_id=user.id,
            request=request,
        )
        await self.repo.commit()
        return await self._build_auth_response(user, tokens)

    async def logout(self, refresh_token: str, request: Request | None = None) -> None:
        payload = decode_token(refresh_token, expected_type="refresh")
        session = await self.repo.get_refresh_session(payload["jti"])
        if session:
            await self.repo.revoke_refresh_session(session)
            await self._audit(
                action="logout",
                outcome="success",
                user_id=session.user_id,
                request=request,
            )
            await self.repo.commit()

    async def request_password_reset(
        self,
        payload: PasswordResetRequest,
        request: Request | None = None,
    ) -> dict:
        normalized_identifier = payload.identifier.strip()
        await self._enforce_rate_limit(
            action="password_reset_request",
            key=self._compose_rate_limit_key(request, normalized_identifier),
            request=request,
            identifier=normalized_identifier,
        )
        user = await self.repo.get_user_by_identifier(normalized_identifier)
        reset_code_preview: str | None = None
        delivery: dict = {"delivered": False, "channel": None, "reason": "account_not_found"}

        if user and user.is_active:
            await self.repo.expire_password_reset_codes_for_user(user.id)
            reset_code = PasswordResetCode(
                user_id=user.id,
                code=self._generate_reset_code(),
                expires_at=datetime.now(UTC) + timedelta(minutes=settings.reset_code_expire_minutes),
                used=False,
            )
            await self.repo.create_password_reset_code(reset_code)
            if user.email:
                try:
                    delivery = await send_password_reset_code(recipient=user.email, code=reset_code.code)
                except Exception as exc:
                    delivery = {
                        "delivered": False,
                        "channel": "email",
                        "reason": f"smtp_error:{exc.__class__.__name__}",
                    }
            else:
                delivery = {
                    "delivered": False,
                    "channel": None,
                    "reason": "no_supported_delivery_channel",
                }
            if settings.debug and settings.debug_expose_reset_code and not smtp_is_configured():
                reset_code_preview = reset_code.code

            await self._audit(
                action="password_reset_request",
                outcome="success",
                identifier=normalized_identifier,
                user_id=user.id,
                request=request,
                detail=delivery,
            )
        else:
            await self._audit(
                action="password_reset_request",
                outcome="success",
                identifier=normalized_identifier,
                request=request,
                detail=delivery,
            )

        await self.repo.commit()
        return {
            "success": True,
            "message": "If the account exists, a reset code has been prepared.",
            "reset_code": reset_code_preview,
            "delivery": delivery if settings.debug else None,
        }

    async def confirm_password_reset(
        self,
        payload: PasswordResetConfirmRequest,
        request: Request | None = None,
    ) -> dict:
        normalized_identifier = payload.identifier.strip()
        await self._enforce_rate_limit(
            action="password_reset_confirm",
            key=self._compose_rate_limit_key(request, normalized_identifier),
            request=request,
            identifier=normalized_identifier,
        )
        user = await self.repo.get_user_by_identifier(normalized_identifier)
        if user is None or not user.is_active:
            await self._audit(
                action="password_reset_confirm",
                outcome="failed",
                identifier=normalized_identifier,
                request=request,
                detail={"reason": "invalid_or_expired_code"},
            )
            await self.repo.commit()
            raise HTTPException(status_code=400, detail="Reset code is invalid or expired.")

        reset_code = await self.repo.get_valid_password_reset_code(user_id=user.id, code=payload.code.strip())
        if reset_code is None or reset_code.expires_at <= datetime.now(UTC):
            await self._audit(
                action="password_reset_confirm",
                outcome="failed",
                identifier=normalized_identifier,
                user_id=user.id,
                request=request,
                detail={"reason": "invalid_or_expired_code"},
            )
            await self.repo.commit()
            raise HTTPException(status_code=400, detail="Reset code is invalid or expired.")

        user.password_hash = get_password_hash(payload.new_password)
        user.is_verified = True
        reset_code.used = True
        await self.repo.revoke_all_refresh_sessions_for_user(user.id)
        await self._audit(
            action="password_reset_confirm",
            outcome="success",
            identifier=normalized_identifier,
            user_id=user.id,
            request=request,
        )
        await self.repo.commit()
        return {"success": True}

    async def change_password(
        self,
        user: User,
        payload: ChangePasswordRequest,
        request: Request | None = None,
    ) -> dict:
        await self._enforce_rate_limit(
            action="change_password",
            key=self._compose_rate_limit_key(request, str(user.id)),
            request=request,
            identifier=user.email or user.phone,
            user_id=user.id,
        )
        if user.password_hash is None or not verify_password(payload.current_password, user.password_hash):
            await self._audit(
                action="change_password",
                outcome="failed",
                identifier=user.email or user.phone,
                user_id=user.id,
                request=request,
                detail={"reason": "incorrect_current_password"},
            )
            await self.repo.commit()
            raise HTTPException(status_code=400, detail="Current password is incorrect.")

        user.password_hash = get_password_hash(payload.new_password)
        await self.repo.revoke_all_refresh_sessions_for_user(user.id)
        await self._audit(
            action="change_password",
            outcome="success",
            identifier=user.email or user.phone,
            user_id=user.id,
            request=request,
        )
        await self.repo.commit()
        return {"success": True}

    async def get_current_user(self, user_id: int) -> User:
        user = await self.repo.get_user_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")
        return user

    async def get_current_user_summary(self, user: User) -> UserSummary:
        await self._ensure_user_workspace(user)
        await self.repo.commit()
        return await self._build_user_summary(user)

    async def _issue_tokens(self, user: User, request: Request | None) -> AuthTokens:
        claims = {
            "email": user.email,
            "roles": [user_role.role.code for user_role in user.roles],
            "restaurant_ids": sorted(
                {assignment.restaurant_id for assignment in user.restaurant_assignments if assignment.restaurant_id}
            ),
        }
        access_token, _, access_expiry = create_access_token(user.id, claims)
        refresh_token, refresh_jti, refresh_expiry = create_refresh_token(user.id)
        session = RefreshSession(
            user_id=user.id,
            token_jti=refresh_jti,
            expires_at=refresh_expiry,
            user_agent=request.headers.get("user-agent") if request else None,
            ip_address=request.client.host if request and request.client else None,
        )
        await self.repo.create_refresh_session(session)
        return AuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            access_token_expires_at=access_expiry,
            refresh_token_expires_at=refresh_expiry,
        )

    async def _build_user_summary(self, user: User) -> UserSummary:
        roles = [
            RoleSummary(
                code=user_role.role.code,
                name=user_role.role.name,
                restaurant_id=user_role.restaurant_id,
                branch_id=user_role.branch_id,
            )
            for user_role in user.roles
        ]
        restaurant_ids = sorted(
            {
                assignment.restaurant_id
                for assignment in user.restaurant_assignments
                if assignment.restaurant_id is not None
            }
        )
        pos_link_status = await lookup_pos_link_status(
            email=user.email,
            external_links=user.external_links,
        )
        workspace_summaries: list[WorkspaceSummary] = []
        for membership in sorted(
            user.workspace_memberships,
            key=lambda item: (item.workspace.workspace_type, item.workspace.id),
        ):
            if membership.status != "active":
                continue
            workspace_summaries.append(
                WorkspaceSummary(
                    id=membership.workspace.id,
                    workspace_type=membership.workspace.workspace_type,
                    name=membership.workspace.name,
                    slug=membership.workspace.slug,
                    status=membership.workspace.status,
                    membership_role=membership.membership_role,
                    is_primary=membership.is_primary,
                    primary_restaurant_id=membership.workspace.primary_restaurant_id,
                    primary_restaurant_name=(
                        membership.workspace.primary_restaurant.name
                        if membership.workspace.primary_restaurant
                        else None
                    ),
                )
            )
        active_workspace = next(
            (workspace for workspace in workspace_summaries if workspace.id == user.active_workspace_id),
            None,
        )
        return UserSummary(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            phone=user.phone,
            status=user.status,
            is_verified=user.is_verified,
            roles=roles,
            restaurant_ids=restaurant_ids,
            external_links=[
                {
                    "system_name": link.system_name,
                    "external_user_id": link.external_user_id,
                    "external_role_snapshot": link.external_role_snapshot,
                }
                for link in user.external_links
            ],
            pos_link_status=pos_link_status,
            active_restaurant_id=user.active_restaurant_id,
            active_workspace_id=user.active_workspace_id,
            active_workspace=active_workspace,
            workspaces=workspace_summaries,
        )

    async def _build_auth_response(self, user: User, tokens: AuthTokens) -> AuthResponse:
        summary = await self._build_user_summary(user)
        pos_candidates = await self.repo.find_pos_link_candidates(user.email, user.phone)
        if summary.pos_link_status.status not in {"match_found", "linked"}:
            pos_candidates = []
        return AuthResponse(tokens=tokens, user=summary, pos_link_candidates=pos_candidates)

    async def _ensure_user_workspace(self, user: User) -> None:
        workspace_service = WorkspaceService(self.repo.db)
        await workspace_service.ensure_customer_workspace(user)

    def _generate_reset_code(self) -> str:
        return f"{randbelow(1_000_000):06d}"

    async def _enforce_rate_limit(
        self,
        *,
        action: str,
        key: str,
        request: Request | None = None,
        identifier: str | None = None,
        user_id: int | None = None,
    ) -> None:
        now = datetime.now(UTC)
        max_attempts, window_minutes, block_minutes = self._rate_limit_rule(action)
        record = await self.repo.get_rate_limit(action=action, key=key)
        if record is None:
            try:
                record = AuthRateLimit(
                    action=action,
                    key=key,
                    attempt_count=0,
                    window_started_at=now,
                    last_attempt_at=now,
                    blocked_until=None,
                )
                await self.repo.create_rate_limit(record)
            except IntegrityError:
                await self.repo.rollback()
                record = await self.repo.get_rate_limit(action=action, key=key)
                if record is None:
                    raise
        elif record.blocked_until and record.blocked_until > now:
            await self._audit(
                action=action,
                outcome="rate_limited",
                identifier=identifier,
                user_id=user_id,
                request=request,
                detail={"reason": "blocked_until_active"},
            )
            await self.repo.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Please try again later.",
            )

        if record.window_started_at + timedelta(minutes=window_minutes) <= now:
            record.attempt_count = 0
            record.window_started_at = now
            record.blocked_until = None

        record.attempt_count += 1
        record.last_attempt_at = now
        if record.attempt_count > max_attempts:
            record.blocked_until = now + timedelta(minutes=block_minutes)
            await self._audit(
                action=action,
                outcome="rate_limited",
                identifier=identifier,
                user_id=user_id,
                request=request,
                detail={"reason": "max_attempts_exceeded"},
            )
            await self.repo.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Please try again later.",
            )

    async def _audit(
        self,
        *,
        action: str,
        outcome: str,
        identifier: str | None = None,
        user_id: int | None = None,
        request: Request | None = None,
        detail: dict | None = None,
    ) -> None:
        await self.repo.create_audit_log(
            AuthAuditLog(
                user_id=user_id,
                action=action,
                outcome=outcome,
                identifier=identifier,
                ip_address=request.client.host if request and request.client else None,
                user_agent=request.headers.get("user-agent") if request else None,
                detail_json=detail,
            )
        )

    def _compose_rate_limit_key(self, request: Request | None, identifier: str) -> str:
        ip_address = request.client.host if request and request.client else "unknown"
        return f"{identifier.lower()}::{ip_address}"

    def _rate_limit_rule(self, action: str) -> tuple[int, int, int]:
        rules = {
            "register": (5, 60, 60),
            "login": (5, 15, 15),
            "google_login": (10, 15, 15),
            "password_reset_request": (3, 15, 30),
            "password_reset_confirm": (5, 15, 30),
            "change_password": (5, 15, 15),
        }
        return rules.get(action, (10, 15, 15))
