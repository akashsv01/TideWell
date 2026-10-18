"""API contract shared with the frontend. Every optional field defaults to None/False/[]
so a partial Gemini extraction never fails validation."""
import re
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

_E164 = re.compile(r"^\+[1-9]\d{7,14}$")

DeliveryMethod = Literal["vaginal", "c-section"]
FeedingType = Literal["breastfeeding", "formula", "mixed"]


class Profile(BaseModel):
    """Baseline profile, collected once at onboarding and editable in Settings (PUT /profile)."""

    consent_granted: bool = Field(description="Explicit agreement to store check-in data. Must be true.")
    delivery_date: date
    gestation_weeks: Optional[int] = Field(default=None, ge=20, le=45)
    delivery_method: DeliveryMethod
    feeding_type: FeedingType
    history_mental_health: bool = False  # prior depression or anxiety -> always at least "watch"
    history_pregnancy_complications: list[str] = Field(default_factory=list, max_length=10)
    language_preference: Literal["en", "es"] = "en"
    support_person_name: Optional[str] = Field(default=None, max_length=80)
    support_person_phone: Optional[str] = None  # E.164, e.g. +12025550123
    support_sms_consent: bool = False  # permission to text the support person in an emergency
    name: Optional[str] = Field(default=None, max_length=80)  # what Tidewell calls you

    @field_validator("support_person_phone")
    @classmethod
    def _phone_e164(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not v.strip():
            return None
        v = v.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if not _E164.match(v):
            raise ValueError("support_person_phone must be in E.164 format, e.g. +12025550123")
        return v

    @field_validator("history_pregnancy_complications")
    @classmethod
    def _clean(cls, v: list[str]) -> list[str]:
        return [s.strip()[:80] for s in v if s and s.strip()]


class ProfileOut(Profile):
    patient_id: str
    day_postpartum: int
    categories: list[str] = Field(default_factory=list)
    demo: bool = False


class CheckinRequest(BaseModel):
    patient_id: str
    text: Optional[str] = None
    audio_base64: Optional[str] = None
    audio_mime: Optional[str] = None  # e.g. "audio/webm;codecs=opus" (Chrome) or "audio/mp4" (Safari)


class CheckinMetrics(BaseModel):
    mood: Optional[int] = Field(default=None, ge=0, le=10, description="Self-reported mood, 0 (worst) to 10 (best)")
    pain: Optional[int] = Field(default=None, ge=0, le=10, description="General pain, 0 to 10")
    incision_pain: Optional[int] = Field(default=None, ge=0, le=10, description="C-section incision pain, 0 to 10")
    sleep_hrs: Optional[float] = Field(default=None, ge=0, le=24, description="Hours slept in the last night")
    headache: bool = False
    vision_change: bool = Field(default=False, description="Blurry vision, spots, or any change in vision")
    bleeding: Optional[Literal["none", "light", "heavy"]] = None
    fever: bool = False
    bp_sys: Optional[int] = Field(default=None, description="Systolic blood pressure (top number)")
    bp_dia: Optional[int] = Field(default=None, description="Diastolic blood pressure (bottom number)")
    mentions: list[str] = Field(default_factory=list, description="Other notable symptoms or concerns, short phrases")


Tier = Literal["green", "watch", "amber", "red"]


class CategoryTier(BaseModel):
    category: str
    tier: Tier = "green"
    reasons: list[str] = Field(default_factory=list)
    next_step: str = ""


class CheckinResponse(BaseModel):
    reply_text: str
    reply_audio_base64: Optional[str] = None
    red_flag: bool = False
    red_flag_reason: Optional[str] = None
    red_flag_level: Optional[Literal["emergency", "urgent"]] = None  # emergency = 911 card, urgent = call provider now
    support_alerted: bool = False  # True only if the support-person SMS actually went out
    transcript: Optional[str] = None  # what we heard, so the UI can show it back
    metrics: CheckinMetrics = Field(default_factory=CheckinMetrics)
    tiers: list[CategoryTier] = Field(default_factory=list)


class TrendPoint(BaseModel):
    day: date
    day_postpartum: Optional[int] = None
    mood: Optional[int] = None
    pain: Optional[int] = None
    incision_pain: Optional[int] = None
    sleep_hrs: Optional[float] = None
    headache: bool = False
    bp_sys: Optional[int] = None
    bp_dia: Optional[int] = None
    resting_hr: Optional[int] = None  # from Apple Health (vitals.heart_rate), beats per minute
    epds_score: Optional[int] = None  # weekly (about days 7, 14, 21); null on other days
    item_10_alert: bool = False  # EPDS question 10 (self-harm thoughts) answered above "Never"
