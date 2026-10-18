"""Request/response models for the data-layer endpoints (Person 2).

Kept separate from app/schemas.py so Person 1 and Person 2 never edit the same file.
Shared contract models (Profile, TrendPoint, CheckinMetrics) live in schemas.py.
"""
from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# --- Accounts -------------------------------------------------------------------------
class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)


class AuthOut(BaseModel):
    token: str
    username: str
    patient_id: Optional[UUID] = None  # None until onboarding is done


class AccountOut(BaseModel):
    username: str
    patient_id: Optional[UUID] = None


# --- Weekly EPDS --------------------------------------------------------------------------
class EpdsIn(BaseModel):
    patient_id: UUID
    answers: list[int] = Field(min_length=10, max_length=10)  # option index (0-3) per question, in display order


class EpdsOut(BaseModel):
    score: int
    item10: int
    band: Literal["low", "watch", "amber"]  # thresholds.md: 10-12 watch, 13+ amber
    level: Optional[Literal["emergency", "urgent"]] = None  # question 10 safety outcome
    needs_followup: bool = False  # ask "Are you thinking of ending your life or hurting yourself?"
    response: Optional[str] = None  # fixed text to show when level is set


class EpdsFollowupIn(BaseModel):
    patient_id: UUID
    answer: Literal["yes", "no", "unsure"]


class EpdsFollowupOut(BaseModel):
    level: Literal["emergency", "urgent"]
    response: str


class Overview(BaseModel):
    """Header facts for the home and tide screens."""
    patient_id: UUID
    demo: bool
    name: Optional[str] = None
    day_postpartum: int
    delivery_method: str
    feeding_type: Optional[str] = None
    history_mental_health: bool = False
    history_pregnancy_complications: list[str] = Field(default_factory=list)
    epds_due: bool = False
    last_epds_score: Optional[int] = None
    last_epds_date: Optional[date] = None


class DayEntry(BaseModel):
    """The numbers for one day, typed or corrected by the patient. None = not recorded."""
    mood: Optional[int] = Field(default=None, ge=0, le=10)
    pain: Optional[int] = Field(default=None, ge=0, le=10)
    incision_pain: Optional[int] = Field(default=None, ge=0, le=10)
    sleep_hrs: Optional[float] = Field(default=None, ge=0, le=24)
    headache: bool = False
    bp_sys: Optional[int] = Field(default=None, ge=50, le=300)
    bp_dia: Optional[int] = Field(default=None, ge=30, le=200)


class DayOut(BaseModel):
    day: date
    saved: bool = True
    red_flag: bool = False
    red_flag_level: Optional[Literal["emergency", "urgent"]] = None
    red_flag_reason: Optional[str] = None
    urgent_message: Optional[str] = None


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


# --- Smartwatch data (Apple Health via Health Auto Export) ---------------------------------
class WearableTokenOut(BaseModel):
    token: str                   # shown once; only its SHA-256 is stored
    ingest_path: str             # append to the API base URL
    header_name: str = "Authorization"
    header_value: str            # "Bearer <token>"


class WearableIngestOut(BaseModel):
    saved: bool
    recognized: dict[str, int]   # TideWell metric -> points kept
    ignored: list[str]           # Health Auto Export metric names TideWell does not use
    rejected: int                # points dropped as unreadable or implausible
    new_bp_readings: int = 0
    red_flag: bool = False       # only ever from a cuff BP reading, never from watch metrics
    red_flag_level: Optional[Literal["emergency", "urgent"]] = None
    red_flag_reason: Optional[str] = None
    urgent_message: Optional[str] = None


class WearableDay(BaseModel):
    day: date
    resting_hr: Optional[float] = None
    heart_rate: Optional[float] = None
    hrv_ms: Optional[float] = None
    steps: Optional[int] = None
    sleep_hrs: Optional[float] = None
    spo2: Optional[float] = None
    resp_rate: Optional[float] = None
    wrist_temp_c: Optional[float] = None


class WearableNudge(BaseModel):
    metric: str
    kind: str
    message: str
    recent: float
    baseline: Optional[float] = None


class WearablesOut(BaseModel):
    connected: bool
    synthetic: bool = False      # True for the demo patient's generated watch data
    last_sync: Optional[datetime] = None
    days: list[WearableDay]
    nudges: list[WearableNudge]  # prompts to check in; never a diagnosis or a red flag
