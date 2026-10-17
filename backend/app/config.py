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
    gemini_model: str = "gemini-3.8-flash"
    backboard_api_key: str = ""
    tiger_database_url: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    # Comma-separated browser origins allowed by CORS (local Next.js + your Vercel URL).
    frontend_origins: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
