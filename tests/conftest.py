import os


os.environ.setdefault(
    "YUMMYDOORS_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/yummydoors_test",
)
os.environ.setdefault("YUMMYDOORS_JWT_SECRET_KEY", "test-secret-key")
