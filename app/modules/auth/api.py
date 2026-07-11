from fastapi import APIRouter, Depends, Request

from app.modules.auth.deps import get_auth_service, get_current_user
from app.modules.auth.schemas import (
    AdminLoginRequest,
    AuthResponse,
    ChangePasswordRequest,
    GoogleLoginRequest,
    LoginRequest,
    LogoutRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    RiderLocationUpdateRequest,
    UserSummary,
)
from app.modules.auth.service import AuthService
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=ApiResponse[AuthResponse])
async def register(
    payload: RegisterRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    result = await service.register(payload, request)
    return ApiResponse(message="Registration successful.", data=result)


@router.post("/login", response_model=ApiResponse[AuthResponse])
async def login(
    payload: LoginRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    result = await service.login(payload, request)
    return ApiResponse(message="Login successful.", data=result)


@router.post("/admin/login", response_model=ApiResponse[AuthResponse])
async def admin_login(
    payload: AdminLoginRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    result = await service.admin_login(payload, request)
    return ApiResponse(message="Admin login successful.", data=result)


@router.post("/google", response_model=ApiResponse[AuthResponse])
async def google_login(
    payload: GoogleLoginRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    result = await service.login_with_google(payload, request)
    return ApiResponse(message="Google login successful.", data=result)


@router.post("/refresh", response_model=ApiResponse[AuthResponse])
async def refresh(
    payload: RefreshRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    result = await service.refresh(payload.refresh_token, request)
    return ApiResponse(message="Token refreshed successfully.", data=result)


@router.post("/logout", response_model=ApiResponse[dict])
async def logout(
    payload: LogoutRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    await service.logout(payload.refresh_token, request)
    return ApiResponse(message="Logout successful.", data={"success": True})


@router.post("/password-reset/request", response_model=ApiResponse[dict])
async def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    data = await service.request_password_reset(payload, request)
    return ApiResponse(message="Password reset request processed.", data=data)


@router.post("/password-reset/confirm", response_model=ApiResponse[dict])
async def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    data = await service.confirm_password_reset(payload, request)
    return ApiResponse(message="Password has been reset successfully.", data=data)


@router.post("/change-password", response_model=ApiResponse[dict])
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    user=Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    data = await service.change_password(user, payload, request)
    return ApiResponse(message="Password changed successfully.", data=data)


@router.get("/me", response_model=ApiResponse[UserSummary])
async def me(
    user=Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    data = await service.get_current_user_summary(user)
    return ApiResponse(message="Current user fetched successfully.", data=data)


@router.patch("/me/rider-location", response_model=ApiResponse[UserSummary])
async def update_rider_location(
    payload: RiderLocationUpdateRequest,
    request: Request,
    user=Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    data = await service.update_rider_location(user, payload, request)
    return ApiResponse(message="Rider location updated successfully.", data=data)
