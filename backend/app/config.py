"""App settings loaded from backend/.env (never hard-code or print keys)."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "EXAVITQu4vr4xnSDxMaL"  # premade "Sarah"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    gemini_fast_model: str = "gemini-3.5-flash-lite"  # latency-critical calls (red-flag backup)
    backboard_api_key: str = ""
    tiger_database_url: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
