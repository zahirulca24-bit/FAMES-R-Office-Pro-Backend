from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./fames_office.db"
    jwt_secret: str = Field(default="development-only-change-me-please-32chars")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 480
    remember_token_minutes: int = 43_200
    login_max_failures: int = 5
    login_lock_minutes: int = 15
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.app_env.lower() != "production":
            return self

        if not self.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
            raise ValueError("Production DATABASE_URL must use PostgreSQL")

        if self.jwt_secret == "development-only-change-me-please-32chars" or len(self.jwt_secret) < 32:
            raise ValueError("Production JWT_SECRET must be a unique value of at least 32 characters")

        if not self.cors_origin_list:
            raise ValueError("Production CORS_ORIGINS must contain at least one frontend origin")

        if "*" in self.cors_origin_list:
            raise ValueError("Wildcard CORS origin is not allowed in production")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
