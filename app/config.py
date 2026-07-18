from functools import lru_cache

from pydantic import Field
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
