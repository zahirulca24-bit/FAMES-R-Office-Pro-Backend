import re

import pytest
from pydantic import ValidationError

from app.config import Settings


VALID_PRODUCTION_SETTINGS = {
    "app_env": "production",
    "database_url": "postgresql+psycopg://user:password@localhost:5432/fames",
    "jwt_secret": "production-secret-that-is-longer-than-32-characters",
    "cors_origins": "https://fames-r-office-pro-frontend.vercel.app",
}


def test_vercel_preview_cors_regex_is_restricted_to_project_prefix():
    pattern = r"^https://fames-r-office-pro-frontend(?:-[a-z0-9-]+)*\.vercel\.app$"
    settings = Settings(**VALID_PRODUCTION_SETTINGS, cors_origin_regex=pattern)

    assert settings.normalized_cors_origin_regex == pattern
    assert re.fullmatch(pattern, "https://fames-r-office-pro-frontend.vercel.app")
    assert re.fullmatch(
        pattern,
        "https://fames-r-office-pro-frontend-git-main-zahirulca24-1843s-projects.vercel.app",
    )
    assert re.fullmatch(pattern, "https://fames-r-office-pro-frontend-6k5h1b08l.vercel.app")
    assert not re.fullmatch(pattern, "https://unrelated-project.vercel.app")
    assert not re.fullmatch(pattern, "https://fames-r-office-pro-frontend.attacker.example")


def test_invalid_production_cors_regex_is_rejected():
    with pytest.raises(ValidationError, match="CORS_ORIGIN_REGEX must be a valid regular expression"):
        Settings(**VALID_PRODUCTION_SETTINGS, cors_origin_regex="[")
