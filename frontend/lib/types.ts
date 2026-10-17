// ---------------------------------------------------------------------------
// Part 1 mirrors backend/app/schemas.py. The team agreed to rename user_id to
// patient_id and add tiers to the check-in response, so those two follow the plan
// even if schemas.py has not been updated yet. FastAPI sends every field, so unset
// values arrive as null.
// ---------------------------------------------------------------------------

export type DeliveryType = "vaginal" | "c-section";
export type Bleeding = "none" | "light" | "heavy";

export interface OnboardRequest {
  patient_id: string; // use the Clerk user id
  birth_date: string; // YYYY-MM-DD
  delivery_type: DeliveryType;
  conditions: string[];
  breastfeeding: boolean;
  support_phone: string | null;
  language: string; // "en"
}

export interface CheckinRequest {
  patient_id: string;
  text?: string;
  audio_base64?: string; // raw base64, no "data:" prefix
  audio_mime?: string; // for example "audio/webm" (Chrome) or "audio/mp4" (Safari). Backend must pass it to speech-to-text.
}

export interface CheckinMetrics {
  mood: number | null; // 0 to 10
  pain: number | null;
  incision_pain: number | null;
  sleep_hrs: number | null;
  headache: boolean;
  vision_change: boolean;
  bleeding: Bleeding | null;
  fever: boolean;
  bp_sys: number | null;
  bp_dia: number | null;
  mentions: string[];
}

export interface CheckinResponse {
  reply_text: string;
  reply_audio_base64: string | null; // mp3, base64
  red_flag: boolean;
  red_flag_reason: string | null;
  metrics: CheckinMetrics;
  // Not in schemas.py yet. Optional so the real backend still type-checks.
  // Agree the exact shape with P1/P2 before building the citations and booking UI.
  citations?: Citation[];
  slots?: Slot[];
  tiers?: Record<string, Tier>;
}

export interface TrendPoint {
  day: string; // YYYY-MM-DD
  mood: number | null;
  pain: number | null;
  sleep_hrs: number | null;
  bp_sys: number | null;
  bp_dia: number | null;
}

// ---------------------------------------------------------------------------
// Part 2 comes from the plan's API contract (section 7). The backend has not
// defined these yet. Treat every field as a proposal until P1/P2 confirm it.
// ---------------------------------------------------------------------------

export type Tier = "green" | "watch" | "amber" | "red";

export interface Citation {
  source: string; // for example "CDC Hear Her"
  url: string;
}

export interface Slot {
  slot: string; // ISO timestamp
}

export interface OnboardResponse {
  patient_id: string;
  categories: string[];
}

export interface PhotoReading {
  bp_sys: number;
  bp_dia: number;
  needs_confirm: boolean;
}

export interface ClinicianPatient {
  patient: { id: string; name: string };
  overall_tier: Tier;
  reasons: string[];
}
