from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.modules.workspaces.schemas import WorkspaceSummary


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str | None = None
    password: str = Field(min_length=8, max_length=128)
    link_existing_pos_account: bool = False

    @model_validator(mode="after")
    def require_email_or_phone(self) -> "RegisterRequest":
        if not self.email and not self.phone:
            raise ValueError("Either email or phone is required.")
        return self


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class AdminLoginRequest(LoginRequest):
    pass


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=255)


class PasswordResetConfirmRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=255)
    code: str = Field(min_length=4, max_length=20)
    new_password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class GoogleLoginRequest(BaseModel):
    credential: str = Field(min_length=20)


class RoleSummary(BaseModel):
    code: str
    name: str
    restaurant_id: int | None = None
    branch_id: int | None = None


class PosRestaurantMatch(BaseModel):
    pos_restaurant_id: str
    name: str
    phone: str | None = None
    relationship_sources: list[str] = []
    is_owner: bool = False


class PosLinkStatus(BaseModel):
    enabled: bool
    status: str
    message: str
    matched_by: list[str] = []
    matched_user_id: str | None = None
    matched_user_name: str | None = None
    matched_user_email: str | None = None
    matched_roles: list[str] = []
    matched_restaurants: list[PosRestaurantMatch] = []
    linked_user_ids: list[str] = []
    linked_restaurant_ids: list[str] = []


class UserSummary(BaseModel):
    id: int
    full_name: str
    email: str | None
    phone: str | None
    status: str
    is_verified: bool
    roles: list[RoleSummary]
    restaurant_ids: list[int]
    external_links: list[dict]
    pos_link_status: PosLinkStatus
    active_restaurant_id: int | None = None
    active_workspace_id: int | None = None
    active_workspace: WorkspaceSummary | None = None
    workspaces: list[WorkspaceSummary] = []


class AuthTokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime


class PosLinkCandidate(BaseModel):
    match_type: str
    identifier: str
    system_name: str


class AuthResponse(BaseModel):
    tokens: AuthTokens
    user: UserSummary
    pos_link_candidates: list[PosLinkCandidate] = []
