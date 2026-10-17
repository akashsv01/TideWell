"""Request/response models for the data-layer endpoints (Person 2).

Kept separate from app/schemas.py so Person 1 and Person 2 never edit the same file.
Models that already exist in schemas.py (OnboardRequest, TrendPoint, CheckinMetrics) are reused.
"""
import re
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas import OnboardRequest

_E164 = re.compile(r"^\+[1-9]\d{7,14}$")


class OnboardIn(OnboardRequest):
    """Person 1's OnboardRequest, with patient_id optional and a few chart fields added."""

    patient_id: Optional[str] = None  # if it is a valid UUID it is used as the id, else one is generated
    name: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=12, le=70)
    gestation_weeks: Optional[int] = Field(default=None, ge=20, le=45)
    support_consent: bool = Field(default=False, description="Explicit permission to text the support person")
    clerk_user_id: Optional[str] = Field(default=None, max_length=200, description="Login id; links the account")

    @field_validator("support_phone")
    @classmethod
    def _phone_e164(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        v = v.replace(" ", "").replace("-", "")
        if not _E164.match(v):
            raise ValueError("support_phone must be in E.164 format, e.g. +12025550123")
        return v


class OnboardOut(BaseModel):
    patient_id: UUID
    categories: list[str]


class MeOut(BaseModel):
    patient_id: UUID
    name: Optional[str] = None
    days_postpartum: Optional[int] = None
    delivery_type: Optional[str] = None


class VitalsIn(BaseModel):
    patient_id: UUID
    bp_sys: Optional[int] = Field(default=None, ge=50, le=300)
    bp_dia: Optional[int] = Field(default=None, ge=30, le=200)
    heart_rate: Optional[int] = Field(default=None, ge=20, le=250)
    temp_c: Optional[float] = Field(default=None, ge=30, le=45)
    glucose: Optional[int] = Field(default=None, ge=20, le=700)
    source: Literal["typed", "voice", "photo"] = "typed"


class VitalsOut(BaseModel):
    saved: bool
    red_flag: bool = False
    red_flag_reason: Optional[str] = None
    urgent_message: Optional[str] = None  # fixed pre-written text, shown verbatim when red_flag is true


class Slot(BaseModel):
    slot: datetime


class AppointmentIn(BaseModel):
    patient_id: UUID
    slot: datetime
    reason: str = Field(max_length=500)
    urgency: Literal["watch", "amber"] = "amber"


class AppointmentOut(BaseModel):
    appointment_id: UUID


class ClinicianPatient(BaseModel):
    patient_id: UUID
    name: Optional[str] = None
    overall_tier: Literal["red", "amber", "watch", "green"]
    reasons: list[str]
    categories: dict[str, str]  # category -> tier
    synthetic: bool = False
