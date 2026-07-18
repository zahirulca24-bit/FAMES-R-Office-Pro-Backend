from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


INSECURE_JWT_SECRETS = {
    "development-only-change-me-please-32chars",
    "replace-with-a-long-random-secret-at-least-32-characters",
    "change-me",
}
ALLOWED_ENVIRONMENTS = {"development", "test", "staging", "production"}
ALLOWED_JWT_ALGORITHMS = {"HS256", "HS384", "HS512"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./fames_office.db"
    jwt_secret: str = Field(default="development-only-change-me-please-32chars", min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "fames-r-office-pro"
    jwt_audience: str = "fames-r-office-pro-frontend"
    access_token_minutes: int = Field(default=480, ge=5, le=1_440)
    remember_token_minutes: int = Field(default=43_200, ge=60, le=43_200)
    login_max_failures: int = Field(default=5, ge=3, le=20)
    login_lock_minutes: int = Field(default=15, ge=1, le=1_440)
    cors_origins: str = "http://localhost:5173"

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def normalized_database_url(self) -> str:
        value = self.database_url.strip()
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        origins: list[str] = []
        for raw_origin in self.cors_origins.split(","):
            origin = raw_origin.strip().rstrip("/")
            if not origin:
                continue
            if origin == "*":
                raise ValueError("Wildcard CORS origins are not allowed with credentialed requests.")
            parsed = urlparse(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(f"Invalid CORS origin: {origin}")
            origins.append(origin)
        if not origins:
            raise ValueError("At least one CORS origin must be configured.")
        return list(dict.fromkeys(origins))

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        self.app_env = self.app_env.strip().lower()
        if self.app_env not in ALLOWED_ENVIRONMENTS:
            raise ValueError(f"APP_ENV must be one of {sorted(ALLOWED_ENVIRONMENTS)}")
        if self.jwt_algorithm not in ALLOWED_JWT_ALGORITHMS:
            raise ValueError("Unsupported JWT algorithm.")
        if self.remember_token_minutes < self.access_token_minutes:
            raise ValueError("REMEMBER_TOKEN_MINUTES cannot be shorter than ACCESS_TOKEN_MINUTES.")

        origins = self.cors_origin_list
        if self.is_production:
            if not self.normalized_database_url.startswith("postgresql+psycopg://"):
                raise ValueError("Production requires a PostgreSQL DATABASE_URL.")
            if self.jwt_secret in INSECURE_JWT_SECRETS:
                raise ValueError("Production JWT_SECRET must be an explicit strong secret.")
            if any("localhost" in origin or "127.0.0.1" in origin for origin in origins):
                raise ValueError("Production CORS_ORIGINS cannot include localhost.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
