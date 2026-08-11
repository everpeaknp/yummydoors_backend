from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "YummyDoors API"
    app_env: str = "development"
    debug: bool = True
    db_echo: bool = False
    api_v1_prefix: str = "/api/v1"

    database_url: str
    pos_database_url: str | None = None

    # Freelance/platform-tier riders collect COD cash for orders that also
    # include money owed to the restaurant, with no enforced mechanism yet
    # to get the restaurant's share back from an anonymous gig rider (see
    # RiderPayoutService / RestaurantSettlementService COD comments). Off
    # by default until that settlement flow is built — private (restaurant-
    # employed) rider dispatch is completely unaffected either way.
    gig_dispatch_enabled: bool = False

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24 * 7
    reset_code_expire_minutes: int = 10
    debug_expose_reset_code: bool = True
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices(
            "REDIS_URL",
            "YUMMYDOORS_REDIS_URL",
        ),
    )

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False

    google_client_id: str | None = None
    web_push_vapid_public_key: str | None = None
    web_push_vapid_private_key: str | None = None
    web_push_subject: str | None = None
    firebase_credentials_base64: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "FIREBASE_CREDENTIALS_BASE64",
            "YUMMYDOORS_FIREBASE_CREDENTIALS_BASE64",
        ),
    )
    firebase_credentials_path: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "GOOGLE_APPLICATION_CREDENTIALS",
            "YUMMYDOORS_FIREBASE_CREDENTIALS_PATH",
        ),
    )
    firebase_project_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "FIREBASE_PROJECT_ID",
            "YUMMYDOORS_FIREBASE_PROJECT_ID",
        ),
    )

    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # eSewa merchant credentials, held server-side only. Never send esewa_secret_key
    # to any client — it must only ever be used for the server-to-server verify call.
    esewa_client_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ESEWA_CLIENT_ID", "YUMMYDOORS_ESEWA_CLIENT_ID"),
    )
    esewa_secret_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ESEWA_SECRET_KEY", "YUMMYDOORS_ESEWA_SECRET_KEY"),
    )
    esewa_environment: str = Field(
        default="test",
        validation_alias=AliasChoices("ESEWA_ENVIRONMENT", "YUMMYDOORS_ESEWA_ENVIRONMENT"),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="YUMMYDOORS_",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if isinstance(value, str) and value.strip().startswith("["):
            import json
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except Exception:
                pass
        return [item.strip() for item in value.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
