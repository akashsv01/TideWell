"""App settings loaded from backend/.env (never hard-code or print keys)."""
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
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
    # Claude: cited web answers in Ask (web search tool) and the topic guardrail. Optional; Gemini is the
    # primary. Read from ANTHROPIC_API_KEY, or CLAUDE_API_KEY if that is the name used in .env.
    anthropic_api_key: str = Field(default="", validation_alias=AliasChoices("anthropic_api_key", "claude_api_key"))
    claude_model: str = "claude-opus-5-5"
    backboard_api_key: str = ""
    tiger_database_url: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    # Video visits. Empty = use the WebRTC video server (see app/video.py and video-server/).
    daily_api_key: str = ""
    # Testing only: true lets anyone join a video visit at any time (normally 15 minutes before to 2 hours after).
    video_join_anytime: bool = False
    # Where video-server/ (the WebRTC signaling page) is reachable from the browser. Use an https ngrok address to test across devices.
    webrtc_base_url: str = "http://localhost:5000"
    # Doctor email for video visits (Resend, https://resend.com). One inbox for every doctor. Empty = no email is sent.
    resend_api_key: str = ""
    resend_from: str = "Tidewell <onboarding@resend.dev>"
    doctor_email: str = ""
    # Public address of this API (e.g. https://tidewell-api.onrender.com): the doctor's emailed join link and the
    # iPhone setup guide point here. Empty: the guide uses the request's host and email links use localhost:8000.
    public_api_url: str = ""
    # Optional SMS through Vonage instead of Twilio (used only when both are set).
    vonage_api_key: str = ""
    vonage_api_secret: str = ""
    vonage_from_number: str = ""
    # Comma-separated browser origins allowed by CORS (local Next.js + your Vercel URL).
    frontend_origins: str = "http://localhost:3000,http://localhost:3001"  # local dev server + local prod build


@lru_cache
def get_settings() -> Settings:
    return Settings()
