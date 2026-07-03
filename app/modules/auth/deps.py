from fastapi import Depends, HTTPException, status

from app.core.security import get_current_token_payload, get_optional_current_token_payload
from app.db.session import get_db
from app.modules.auth.repository import AuthRepository
from app.modules.auth.service import AuthService


def get_auth_service(db=Depends(get_db)) -> AuthService:
    return AuthService(AuthRepository(db))


async def get_current_user(
    service: AuthService = Depends(get_auth_service),
    payload: dict = Depends(get_current_token_payload),
):
    user_id = int(payload["sub"])
    return await service.get_current_user(user_id)


async def get_current_user_optional(
    service: AuthService = Depends(get_auth_service),
    payload: dict | None = Depends(get_optional_current_token_payload),
):
    if payload is None:
        return None
    user_id = int(payload["sub"])
    return await service.get_current_user(user_id)


def require_role(allowed_roles: list[str]):
    async def dependency(user=Depends(get_current_user)):
        user_role_codes = {item.role.code for item in user.roles}
        if not user_role_codes.intersection(set(allowed_roles)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role is not allowed to access this resource.",
            )
        return user

    return dependency
