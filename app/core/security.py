from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/login",
    auto_error=False,
)


def create_token(
    subject: str,
    token_type: str,
    expires_minutes: int,
    extra_claims: dict | None = None,
) -> tuple[str, str, datetime]:
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=expires_minutes)
    jti = uuid4().hex
    payload = {
        "sub": subject,
        "jti": jti,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, jti, expire


def create_access_token(user_id: int, claims: dict) -> tuple[str, str, datetime]:
    return create_token(
        subject=str(user_id),
        token_type="access",
        expires_minutes=settings.access_token_expire_minutes,
        extra_claims=claims,
    )


def create_refresh_token(user_id: int) -> tuple[str, str, datetime]:
    return create_token(
        subject=str(user_id),
        token_type="refresh",
        expires_minutes=settings.refresh_token_expire_minutes,
    )


def decode_token(token: str, expected_type: str) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise credentials_exception from exc
    if payload.get("type") != expected_type:
        raise credentials_exception
    if payload.get("sub") is None:
        raise credentials_exception
    return payload


def get_current_token_payload(token: str = Depends(oauth2_scheme)) -> dict:
    return decode_token(token, expected_type="access")


def get_optional_current_token_payload(
    token: str | None = Depends(optional_oauth2_scheme),
) -> dict | None:
    if not token:
        return None
    return decode_token(token, expected_type="access")
