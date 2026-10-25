from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Mandi Lens API"
    frontend_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    sarvam_api_key: str | None = None
    sarvam_speech_model: str = "saaras:v4"
    sarvam_tts_model: str = "bulbul:v3"
    request_timeout_seconds: float = 120.0
    max_upload_bytes: int = 10 * 1024 * 1024

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
