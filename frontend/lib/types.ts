// ---------------------------------------------------------------------------
// Part 1 mirrors backend/app/schemas.py and schemas_data.py. FastAPI sends every field,
// so unset values arrive as null.
// ---------------------------------------------------------------------------

export type DeliveryType = "vaginal" | "c-section";
export type FeedingType = "breastfeeding" | "formula" | "mixed";
export type Language = "en" | "es";
export type Bleeding = "none" | "light" | "heavy";

/** Baseline profile: collected once at onboarding, editable in Settings (backend Profile). */
export interface Profile {
  consent_granted: boolean;
  delivery_date: string; // YYYY-MM-DD
  gestation_weeks: number | null;
  delivery_method: DeliveryType;
  feeding_type: FeedingType;
  history_mental_health: boolean;
  history_pregnancy_complications: string[];
  language_preference: Language;
  support_person_name: string | null;
  support_person_phone: string | null; // E.164
  support_sms_consent: boolean;
  name: string | null;
}

export interface ProfileOut extends Profile {
  patient_id: string;
  day_postpartum: number;
  categories: string[];
  demo: boolean;
}

export interface AuthResponse {
  token: string;
  username: string;
  patient_id: string | null;
}

export interface Account {
  username: string;
  patient_id: string | null;
}

export interface Overview {
  patient_id: string;
  demo: boolean;
  name: string | null;
  day_postpartum: number;
  delivery_method: DeliveryType;
  feeding_type: FeedingType | null;
  history_mental_health: boolean;
  history_pregnancy_complications: string[];
  epds_due: boolean;
  last_epds_score: number | null;
  last_epds_date: string | null;
}

export interface EpdsQuestion {
  number: number;
  text: string;
  options: string[];
}

export interface EpdsQuestions {
  citation: string;
  followup_question: string;
  questions: EpdsQuestion[];
}

export interface EpdsResult {
  score: number;
  item10: number;
  band: "low" | "watch" | "amber";
  level: RedFlagLevel | null;
  needs_followup: boolean;
  response: string | null;
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
  red_flag_level?: RedFlagLevel | null; // "emergency" = 911 card, "urgent" = call your provider now
  support_alerted?: boolean; // the support-person SMS actually went out
  transcript?: string | null; // what the backend heard
  metrics: CheckinMetrics;
  // Not in schemas.py yet. Optional so the real backend still type-checks.
  // Agree the exact shape with P1/P2 before building the citations and booking UI.
  citations?: Citation[];
  slots?: Slot[];
  tiers?: CategoryTier[];
}

export type RedFlagLevel = "emergency" | "urgent";

export interface CategoryTier {
  category: string;
  tier: Tier;
  reasons: string[];
  next_step: string;
}

export interface TrendPoint {
  day: string; // YYYY-MM-DD
  day_postpartum?: number | null;
  mood: number | null;
  pain: number | null;
  incision_pain?: number | null;
  sleep_hrs: number | null;
  headache?: boolean;
  bp_sys: number | null;
  bp_dia: number | null;
  epds_score?: number | null; // weekly; null on other days
  item_10_alert?: boolean;
}

/** Numbers for one day, typed or corrected (backend DayEntry). */
export interface DayEntry {
  mood?: number | null;
  pain?: number | null;
  incision_pain?: number | null;
  sleep_hrs?: number | null;
  headache?: boolean;
  bp_sys?: number | null;
  bp_dia?: number | null;
}

export interface DayOut {
  day: string;
  saved?: boolean;
  red_flag?: boolean;
  red_flag_level?: RedFlagLevel | null;
  red_flag_reason?: string | null;
  urgent_message?: string | null;
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

// --- Agents and care (backend app/routes/agents.py) -----------------------------------------
export interface Citation2 {
  title: string;
  url: string;
  site?: string;
  /** The exact passage from the page that the answer relies on (Claude web search). */
  quote?: string;
}

export interface AskResult {
  answer: string;
  citations: Citation2[];
  tools_called: string[];
  red_flag: boolean;
  red_flag_level: RedFlagLevel | null;
  source: "web" | "curated" | "none" | "off_topic" | "safety";
}

export interface Place {
  name: string;
  kind: "emergency" | "hospital" | "obgyn" | "midwife";
  kind_label: string;
  address: string | null;
  phone: string | null;
  website: string | null;
  distance_km: number;
  directions_url: string;
  source?: "npi" | "osm";
}

export interface CareRequest {
  id: string | null;
  tier: Tier;
  reasons: string[];
  patient_message: string;
  clinician_note?: string | null;
  facilities: Place[];
  slots: string[];
  status?: string;
  demo?: boolean;
}

export interface Appointment {
  id: string;
  slot: string;
  reason: string | null;
  facility_name: string | null;
  facility_address: string | null;
  facility_phone: string | null;
}

export interface RiskResult {
  overall: Tier;
  tiers: (CategoryTier & { score: number })[];
  care_request: CareRequest | null;
  appointments: Appointment[];
}

export interface Nearby {
  places: Place[];
  label: string | null;
  nearest_er: Place | null;
  needs_location: boolean;
}

export interface CircleView {
  name: string;
  day_postpartum: number;
  status: Tier;
  how_to_help: string;
  avg_sleep_7d: number | null;
  last_checkin: string | null;
  appointments: { slot: string; where: string | null }[];
}
