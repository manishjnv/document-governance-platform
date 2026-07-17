import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    # +asyncpg is required: app/db/session.py uses create_async_engine, which
    # rejects the plain psycopg2-style "postgresql://" scheme at startup.
    database_url: str = "postgresql+asyncpg://edgp_user:edgp_password@localhost:5432/edgp_dev"
    database_echo: bool = False
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_recycle: int = 1800

    # Redis
    redis_url: str = "redis://localhost:6379"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_env: str = "development"
    api_log_level: str = "INFO"

    # JWT
    jwt_secret_key: str = "your-super-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    jwt_refresh_expiration_days: int = 7

    # Encryption at rest (T-2050)
    # ponytail: dev-only static key; production needs KMS-backed key rotation
    encryption_key: str = ""

    # AI
    claude_api_key: str = ""
    claude_model: str = "claude-3-5-sonnet-20241022"
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo"
    ai_max_retries: int = 3
    ai_timeout_seconds: int = 60

    # Storage
    storage_type: str = "local"
    storage_local_path: str = "./data/uploads"
    max_document_size_mb: int = 50

    # Rate Limiting
    rate_limit_requests_per_minute: int = 60
    rate_limit_login_attempts: int = 5

    class Config:
        env_file = ".env"
        case_sensitive = False


# Create global settings instance
settings = Settings()
