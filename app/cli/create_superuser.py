from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.db.base import Base  # noqa: F401
from app.db.session import AsyncSessionLocal
from app.modules.auth.models import Role, User, UserRole, UserStatus
from app.utils.security import get_password_hash


async def create_or_update_superuser(
    *,
    email: str,
    password: str,
    full_name: str,
    phone: str | None = None,
) -> User:
    normalized_email = email.strip().lower()
    async with AsyncSessionLocal() as session:
        role = await session.scalar(select(Role).where(Role.code == "super_admin"))
        if role is None:
            raise RuntimeError("Role 'super_admin' is missing. Run migrations first.")

        user = await session.scalar(select(User).where(User.email == normalized_email))
        if user is None:
            user = User(
                email=normalized_email,
                phone=phone.strip() if phone else None,
                full_name=full_name.strip(),
                password_hash=get_password_hash(password),
                status=UserStatus.active,
                is_active=True,
                is_verified=True,
            )
            session.add(user)
            await session.flush()
        else:
            user.full_name = full_name.strip()
            user.phone = phone.strip() if phone else user.phone
            user.password_hash = get_password_hash(password)
            user.status = UserStatus.active
            user.is_active = True
            user.is_verified = True
            await session.flush()

        existing_role = await session.scalar(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role_id == role.id,
                UserRole.restaurant_id.is_(None),
                UserRole.branch_id.is_(None),
            )
        )
        if existing_role is None:
            session.add(UserRole(user_id=user.id, role_id=role.id))

        await session.commit()
        await session.refresh(user)
        return user


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create or update a YummyDoors superuser.")
    parser.add_argument("--email", required=True, help="Superuser email")
    parser.add_argument("--password", required=True, help="Superuser password")
    parser.add_argument("--full-name", required=True, help="Superuser full name")
    parser.add_argument("--phone", help="Optional phone number")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    user = asyncio.run(
        create_or_update_superuser(
            email=args.email,
            password=args.password,
            full_name=args.full_name,
            phone=args.phone,
        )
    )
    print(f"Superuser ready: id={user.id} email={user.email}")


if __name__ == "__main__":
    main()
