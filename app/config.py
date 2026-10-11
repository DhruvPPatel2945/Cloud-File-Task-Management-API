from typing import Literal

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(min_length=1)
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=30, gt=0)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


try:
    settings = Settings()
except ValidationError as exc:
    raise RuntimeError(
        "Invalid or missing configuration. Copy .env.example to .env, "
        "then set DATABASE_URL and a JWT_SECRET_KEY of at least 32 characters."
    ) from exc


# Keep these names because app/security.py already imports them.
DATABASE_URL = settings.database_url
JWT_SECRET_KEY = settings.jwt_secret_key
JWT_ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
LOG_LEVEL = settings.log_level