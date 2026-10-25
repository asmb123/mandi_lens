from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Skillgraph API"
    environment: str = "development"
    database_url: str = "sqlite:///./skillgraph.db"
    frontend_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    session_cookie_name: str = "skillgraph_session"
    session_ttl_seconds: int = 60 * 60 * 24 * 7
    csrf_cookie_name: str = "skillgraph_csrf"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="SKILLGRAPH_", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()