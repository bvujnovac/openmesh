"""
Application configuration management using Pydantic settings.
Loads configuration from environment variables and .env files.
"""

from typing import Any
from pydantic import RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import secrets


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    # Application
    APP_NAME: str = "OpenMesh"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = secrets.token_urlsafe(32)
    API_V1_PREFIX: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True

    # Database - SQLite by default, supports PostgreSQL
    DATABASE_URL: str = "sqlite+aiosqlite:///./openmesh.db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: RedisDsn | str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # InfluxDB for metrics
    INFLUXDB_URL: str = "http://localhost:8086"
    INFLUXDB_TOKEN: str = "openmesh-token"
    INFLUXDB_ORG: str = "openmesh"
    INFLUXDB_BUCKET: str = "metrics"

    # Security
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Monitoring
    METRICS_COLLECTION_INTERVAL: int = 30
    BABEL_METRICS_PORT: int = 33123
    ALERT_LATENCY_THRESHOLD_MS: int = 100
    ALERT_NODE_DOWN_TIMEOUT_SEC: int = 300

    # Network Configuration
    MESH_NETWORK_CIDR: str = "10.0.0.0/16"
    MESH_INFRASTRUCTURE_CIDR: str = "10.0.0.0/23"
    MESH_CLIENT_POOL_START: str = "10.0.2.0"
    MAX_ROUTERS: int = 508
    CLIENTS_PER_ROUTER: int = 126

    # Image Builder
    IMAGEBUILDER_PATH: str = "/app/imagebuilder"
    OPENWRT_VERSION: str = "23.05.2"
    FIRMWARE_STORAGE_PATH: str = "/app/firmware"
    BUILD_TIMEOUT_SECONDS: int = 1800

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: str = "/var/log/openmesh/app.log"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for Alembic migrations."""
        url = str(self.DATABASE_URL)
        # Handle both SQLite and PostgreSQL
        if "sqlite" in url:
            return url.replace("+aiosqlite", "")
        return url.replace("+asyncpg", "")

    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite database."""
        return "sqlite" in str(self.DATABASE_URL).lower()

    @property
    def is_postgres(self) -> bool:
        """Check if using PostgreSQL database."""
        return "postgresql" in str(self.DATABASE_URL).lower()

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"


# Global settings instance
settings = Settings()
