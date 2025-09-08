"""Application configuration management."""
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application settings
    app_name: str = "Rick and Morty SRE App"
    app_version: str = "1.0.0"
    debug: bool = False

    # API settings
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # Rick and Morty API settings
    rick_morty_api_url: str = "https://rickandmortyapi.com/api"
    rick_morty_timeout: int = 30
    rick_morty_max_retries: int = 3
    rick_morty_backoff_factor: float = 0.3

    # Database settings
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/rickmorty"
    )
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout: int = 30

    # Redis cache settings
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl: int = 3600  # 1 hour
    cache_prefix: str = "rickmorty:"

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # Observability settings
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    jaeger_endpoint: Optional[str] = None

    # Logging settings
    log_level: str = "INFO"
    log_format: str = "json"

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
