from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "SANS PMS"
    APP_NAME_AR: str = "نظام إدارة مشاريع سانس"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    VERSION: str = "1.0.0"
    COMPANY_ID: str = "00000000-0000-0000-0000-000000000001"

    # Database
    DATABASE_URL: str
    DATABASE_SYNC_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI
    ANTHROPIC_API_KEY: Optional[str] = None
    AI_MODEL: str = "claude-sonnet-4-6"
    AI_MAX_TOKENS: int = 4096

    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None

    # Email
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: str = "noreply@sans-intl.com"
    SMTP_TLS: bool = True

    # File storage
    UPLOAD_DIR: str = "/app/uploads"
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = [
        "pdf", "xlsx", "xls", "xer", "xml",
        "docx", "doc", "csv", "jpg", "jpeg",
        "png", "gif", "mp4", "mov"
    ]

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Backup
    BACKUP_DIR: str = "/app/backups"
    BACKUP_RETENTION_DAYS: int = 30

    # Pagination
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 500

    class Config:
        env_file = ".env"
        case_sensitive = True

    @validator("DEBUG", pre=True)
    def set_debug(cls, v, values):
        return values.get("ENVIRONMENT") == "development"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
