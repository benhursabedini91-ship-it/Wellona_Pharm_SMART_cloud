from functools import lru_cache
from typing import Optional
from pydantic import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    # Core paths
    WPH_ROOT: str = r"C:\\Wellona\\wphAI"
    OB_OUTDIR: Optional[str] = None

    # Database
    WPH_DB_HOST: str = "127.0.0.1"
    WPH_DB_PORT: int = 5432
    WPH_DB_NAME: str = "wph_ai"
    WPH_DB_USER: str = "postgres"
    WPH_DB_PASS: str = ""

    # Orchestrator
    WPH_SUPPLIER: str = "PHOENIX"
    WPH_SERVICE_LEVEL: float = 0.95
    WPH_REVIEW_DAYS: int = 7
    WPH_BUDGET_RSD: float = 0.0
    WPH_ROUND_TO: int = 1

    # IMAP
    IMAP_HOST: Optional[str] = None
    IMAP_USER: Optional[str] = None
    IMAP_PASS: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
