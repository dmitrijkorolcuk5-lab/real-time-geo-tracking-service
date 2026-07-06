from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="real-time-geo-tracking-service", alias="APP_NAME")
    environment: str = Field(default="local", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/geotracking",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, alias="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(default=1800, alias="DB_POOL_RECYCLE")
    queue_maxsize: int = Field(default=10000, alias="QUEUE_MAXSIZE")
    batch_max_size: int = Field(default=500, alias="BATCH_MAX_SIZE")
    batch_flush_interval_seconds: float = Field(default=1.0, alias="BATCH_FLUSH_INTERVAL_SECONDS")
    websocket_update_queue_size: int = Field(default=512, alias="WEBSOCKET_UPDATE_QUEUE_SIZE")
    websocket_alert_queue_size: int = Field(default=512, alias="WEBSOCKET_ALERT_QUEUE_SIZE")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
