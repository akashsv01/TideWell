"""API contract shared with the frontend. Every optional field defaults to None/False/[]
so a partial Gemini extraction never fails validation."""
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


class OnboardRequest(BaseModel):
    patient_id: str
    birth_date: date
    delivery_type: Literal["vaginal", "c-section"]
    conditions: list[str] = Field(default_factory=list)
    breastfeeding: bool = False
    support_phone: Optional[str] = None
    language: str = "en"


class CheckinRequest(BaseModel):
    patient_id: str
    text: Optional[str] = None
    audio_base64: Optional[str] = None


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
    metrics: CheckinMetrics = Field(default_factory=CheckinMetrics)
    tiers: list[CategoryTier] = Field(default_factory=list)


class TrendPoint(BaseModel):
    day: date
    mood: Optional[int] = None
    pain: Optional[int] = None
    sleep_hrs: Optional[float] = None
    bp_sys: Optional[int] = None
    bp_dia: Optional[int] = None
