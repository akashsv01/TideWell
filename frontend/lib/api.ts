import { authToken, clearSession, getSession, startDemo } from "@/lib/session";
import type {
  Account,
  AuthResponse,
  CheckinMetrics,
  CheckinRequest,
  CheckinResponse,
  ClinicianPatient,
  AskResult,
  CircleView,
  Nearby,
  RiskResult,
  Tier,
  DayEntry,
  DayOut,
  EpdsQuestions,
  EpdsResult,
  JoinInfo,
  Overview,
  PhotoReading,
  Profile,
  ProfileOut,
  Provider,
  RedFlagLevel,
  Slot,
  TrendPoint,
  Visit,
  VisitMode,
  VisitUrgency,
} from "@/lib/types";

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const wait = (ms = 400) => new Promise((r) => setTimeout(r, ms));

/** Error with the HTTP status and the backend's `detail` message, for showing to people. */
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
  }
}

async function raw(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const token = authToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail) && body.detail[0]?.msg) detail = body.detail[0].msg;
    } catch {
      /* not JSON */
    }
    // An expired or revoked login: drop it so the app shows the sign-in choices again.
    if (res.status === 401 && getSession()?.kind === "user") clearSession();
    throw new ApiError(res.status, detail);
  }
  return res;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await raw(path, init);
  return (res.status === 204 ? undefined : await res.json()) as T;
}

function sendJson<T>(method: string, path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function postJson<T>(path: string, body: unknown): Promise<T> {
  return sendJson<T>("POST", path, body);
}

/** Blob (from MediaRecorder) to raw base64, which is what POST /checkin expects. */
export function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = String(reader.result ?? "");
      resolve(result.slice(result.indexOf(",") + 1));
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

/** Use as the src of an Audio element to play reply_audio_base64 (mp3). */
export const replyAudioSrc = (b64: string) => `data:audio/mpeg;base64,${b64}`;

// Maya, day 18. The last four BP readings are 132/84, 136/88, 141/90, 144/92.
const MAYA = {
  mood: [7, 7, 6, 6, 7, 6, 5, 6, 5, 5, 6, 5, 4, 5, 4, 4, 3, 4],
  pain: [6, 6, 5, 5, 5, 4, 4, 4, 4, 3, 3, 3, 3, 3, 3, 2, 2, 2],
  sleep: [5.5, 5, 4.5, 5, 4.5, 4.5, 4, 4.5, 4, 4, 4.5, 4, 3.5, 4, 3.8, 3.5, 4, 3.8],
  bp_sys: [124, 125, 126, 124, 127, 128, 126, 127, 129, 128, 130, 129, 128, 131, 132, 136, 141, 144],
  bp_dia: [78, 78, 80, 79, 80, 81, 80, 80, 82, 81, 82, 81, 82, 83, 84, 88, 90, 92],
};

function mockTrends(): TrendPoint[] {
  const n = MAYA.mood.length;
  return MAYA.mood.map((mood, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (n - 1 - i));
    return {
      day: d.toISOString().slice(0, 10),
      mood,
      pain: MAYA.pain[i],
      sleep_hrs: MAYA.sleep[i],
      bp_sys: MAYA.bp_sys[i],
      bp_dia: MAYA.bp_dia[i],
    };
  });
}

function mockSlots(): Slot[] {
  const a = new Date();
  a.setDate(a.getDate() + 2);
  a.setHours(10, 0, 0, 0);
  const b = new Date();
  b.setDate(b.getDate() + 3);
  b.setHours(14, 0, 0, 0);
  return [{ slot: a.toISOString() }, { slot: b.toISOString() }];
}

const EMPTY_METRICS: CheckinMetrics = {
  mood: null,
  pain: null,
  incision_pain: null,
  sleep_hrs: null,
  headache: false,
  vision_change: false,
  bleeding: null,
  fever: false,
  bp_sys: null,
  bp_dia: null,
  mentions: [],
};

// --- Accounts --------------------------------------------------------------------------
export const register = (username: string, password: string) =>
  postJson<AuthResponse>("/auth/register", { username, password });

export const login = (username: string, password: string) =>
  postJson<AuthResponse>("/auth/login", { username, password });

/** Revokes the token on the server. Never throws: logging out must always work locally. */
export async function logout(): Promise<void> {
  try {
    await raw("/auth/logout", { method: "POST" });
  } catch {
    /* offline or already expired */
  }
}

/** Leave a signed-in account (revoking the token) and open the shared Maya demo. */
export async function switchToDemo(): Promise<void> {
  await logout();
  startDemo();
}

export const getAccount = () => request<Account>("/auth/me");

// --- Profile ------------------------------------------------------------------------------
export const onboard = (profile: Profile) => postJson<ProfileOut>("/onboard", profile);

export const updateProfile = (profile: Profile) => sendJson<ProfileOut>("PUT", "/profile", profile);

export function getProfile(patientId?: string): Promise<ProfileOut> {
  const q = patientId ? `?patient_id=${encodeURIComponent(patientId)}` : "";
  return request<ProfileOut>(`/profile${q}`);
}

export const getOverview = (patientId: string) => request<Overview>(`/patients/${patientId}/overview`);

// --- Weekly mood check (EPDS) -------------------------------------------------------------
export const getEpdsQuestions = () => request<EpdsQuestions>("/epds/questions");

export const submitEpds = (patientId: string, answers: number[]) =>
  postJson<EpdsResult>("/epds", { patient_id: patientId, answers });

export const epdsFollowup = (patientId: string, answer: "yes" | "no" | "unsure") =>
  postJson<{ level: RedFlagLevel; response: string }>("/epds/followup", { patient_id: patientId, answer });

export async function checkin(
  patientId: string,
  input: { text?: string; audio?: Blob }
): Promise<CheckinResponse> {
  if (USE_MOCK) {
    await wait(900);
    // In mock mode, typing "blurry" triggers the red-flag path for testing.
    if (input.text?.toLowerCase().includes("blurry")) {
      return {
        reply_text:
          "What you just described can be a sign of a serious problem after birth, and it needs care right now.",
        reply_audio_base64: null,
        red_flag: true,
        red_flag_reason: "blurry or changed vision",
        red_flag_level: "emergency",
        metrics: { ...EMPTY_METRICS, vision_change: true },
      };
    }
    return {
      reply_text:
        "Your blood pressure has gone up four readings in a row, and you've had headaches this week. With your history, guidelines recommend getting it checked soon. I have two times open. Want me to book one?",
      reply_audio_base64: null,
      red_flag: false,
      red_flag_reason: null,
      metrics: { ...EMPTY_METRICS, mood: 4, headache: true, bp_sys: 144, bp_dia: 92 },
      citations: [{ source: "CDC Hear Her", url: "https://www.cdc.gov/hearher/" }],
      slots: mockSlots(),
      tiers: [
        { category: "high_blood_pressure", tier: "amber", reasons: [], next_step: "Offer a visit within 1-3 days" },
        { category: "depression_anxiety", tier: "watch", reasons: [], next_step: "Repeat mood check in 3 days" },
        { category: "post_cesarean", tier: "green", reasons: [], next_step: "Routine daily check-in" },
      ],
    };
  }
  const body: CheckinRequest = { patient_id: patientId };
  if (input.text) body.text = input.text;
  if (input.audio) {
    body.audio_base64 = await blobToBase64(input.audio);
    body.audio_mime = input.audio.type || undefined;
  }
  return postJson("/checkin", body);
}

export async function readCuffPhoto(patientId: string, image: File): Promise<PhotoReading> {
  if (USE_MOCK) {
    await wait(1200);
    return { bp_sys: 144, bp_dia: 92, needs_confirm: true };
  }
  // Photo upload shape is not defined in schemas.py yet. Multipart is the likely choice.
  const form = new FormData();
  form.append("patient_id", patientId);
  form.append("image", image);
  return request("/vitals/photo", { method: "POST", body: form });
}

export async function getTrends(patientId: string, range = "21d"): Promise<TrendPoint[]> {
  if (USE_MOCK) {
    await wait(300);
    return mockTrends();
  }
  return request(`/trends/${patientId}?range=${range}`);
}

/** Log or correct one day's numbers (PUT /patients/{id}/days/{day}). */
export function saveDay(patientId: string, day: string, entry: DayEntry): Promise<DayOut> {
  return sendJson<DayOut>("PUT", `/patients/${patientId}/days/${day}`, entry);
}

// --- Visits -------------------------------------------------------------------------------
// Mock mode mirrors backend/app/providers_data.py and keeps visits in memory.
const MOCK_PROVIDERS: Provider[] = [
  {
    id: "00000000-0000-4000-8000-0000000000a1", name: "Dr. Amara Okafor", specialty: "Obstetrician-gynecologist",
    kind: "obstetrics", bio: "Postpartum checkups, recovery after a C-section, and anything that feels off after birth.",
    modes: ["in_person", "virtual"], clinic: "Harbor Women's Health", address: "100 Harbor Street, College Park, MD",
    is_synthetic: true,
  },
  {
    id: "00000000-0000-4000-8000-0000000000a2", name: "Dr. Daniel Reyes",
    specialty: "Blood pressure and heart health after pregnancy", kind: "blood_pressure",
    bio: "Checks rising blood pressure, reviews your home readings and adjusts the plan with you.",
    modes: ["in_person", "virtual"], clinic: "Harbor Women's Health", address: "100 Harbor Street, College Park, MD",
    is_synthetic: true,
  },
  {
    id: "00000000-0000-4000-8000-0000000000a3", name: "Nina Patel, CNM", specialty: "Certified nurse-midwife",
    kind: "midwifery", bio: "Longer visits for recovery, feeding, sleep and the questions that come up at home.",
    modes: ["in_person", "virtual"], clinic: "Tidewater Midwifery", address: "42 Bayview Avenue, Hyattsville, MD",
    is_synthetic: true,
  },
  {
    id: "00000000-0000-4000-8000-0000000000a4", name: "Grace Lin, IBCLC", specialty: "Lactation consultant",
    kind: "lactation", bio: "Help with latch, pain, supply and pumping, by video from your couch.",
    modes: ["virtual"], clinic: "Tidewater Midwifery", address: null, is_synthetic: true,
  },
  {
    id: "00000000-0000-4000-8000-0000000000a5", name: "Dr. Marcus Webb", specialty: "Perinatal mental health",
    kind: "mental_health", bio: "Support for low mood, anxiety and overwhelm after birth. No judgment, no rush.",
    modes: ["virtual", "in_person"], clinic: "Calm Harbor Counseling", address: "7 Lighthouse Lane, Greenbelt, MD",
    is_synthetic: true,
  },
];
const MOCK_HOURS = [10, 11, 14, 15];
let mockVisits: Visit[] = [];

function mockVisitSlots(): Slot[] {
  const out: Slot[] = [];
  const day = new Date();
  for (let i = 0; out.length < 12 && i < 14; i++) {
    day.setDate(day.getDate() + 1);
    if (day.getDay() === 0 || day.getDay() === 6) continue;
    for (const h of MOCK_HOURS) {
      const t = new Date(day);
      t.setHours(h, 0, 0, 0);
      out.push({ slot: t.toISOString() });
    }
  }
  return out.filter((s) => !mockVisits.some((v) => v.status === "booked" && v.slot === s.slot));
}

export async function listProviders(): Promise<Provider[]> {
  if (USE_MOCK) {
    await wait(250);
    return MOCK_PROVIDERS;
  }
  return request("/providers");
}

export async function getSlots(
  urgency: VisitUrgency = "amber",
  opts: { providerId?: string; mode?: VisitMode } = {}
): Promise<Slot[]> {
  if (USE_MOCK) {
    await wait(300);
    return mockVisitSlots();
  }
  const q = new URLSearchParams({ urgency });
  if (opts.providerId) q.set("provider_id", opts.providerId);
  if (opts.mode) q.set("mode", opts.mode);
  return request(`/appointments/slots?${q}`);
}

export async function bookVisit(input: {
  patientId: string;
  providerId: string;
  mode: VisitMode;
  slot: string;
  reason: string;
  urgency: VisitUrgency;
}): Promise<Visit> {
  if (USE_MOCK) {
    await wait(500);
    const provider = MOCK_PROVIDERS.find((p) => p.id === input.providerId) ?? MOCK_PROVIDERS[0];
    const opens = new Date(new Date(input.slot).getTime() - 15 * 60_000).toISOString();
    const closes = new Date(new Date(input.slot).getTime() + 2 * 3600_000).toISOString();
    const v: Visit = {
      appointment_id: `mock-${mockVisits.length + 1}`,
      patient_id: input.patientId,
      provider,
      slot: input.slot,
      mode: input.mode,
      reason: input.reason,
      urgency: input.urgency,
      status: "booked",
      join: input.mode === "virtual" ? { can_join: true, opens_at: opens, closes_at: closes } : null,
    };
    mockVisits = [...mockVisits, v];
    return v;
  }
  const res = await postJson<{ visit: Visit }>("/appointments", {
    patient_id: input.patientId,
    provider_id: input.providerId,
    mode: input.mode,
    slot: input.slot,
    reason: input.reason,
    urgency: input.urgency,
  });
  return res.visit;
}

export async function listVisits(patientId: string): Promise<Visit[]> {
  if (USE_MOCK) {
    await wait(250);
    return mockVisits;
  }
  return request(`/appointments?patient_id=${encodeURIComponent(patientId)}`);
}

export async function cancelVisit(appointmentId: string): Promise<Visit> {
  if (USE_MOCK) {
    await wait(300);
    mockVisits = mockVisits.map((v) => (v.appointment_id === appointmentId ? { ...v, status: "cancelled" } : v));
    return mockVisits.find((v) => v.appointment_id === appointmentId)!;
  }
  return request(`/appointments/${appointmentId}/cancel`, { method: "POST" });
}

/** `asProvider` is for trying the demo from two devices: it opens the doctor's side of the room. */
export async function joinVisit(appointmentId: string, asProvider = false): Promise<JoinInfo> {
  if (USE_MOCK) {
    await wait(300);
    return { url: `https://meet.jit.si/tidewell-mock-${appointmentId}`, service: "jitsi", embeddable: false };
  }
  return request(`/appointments/${appointmentId}/join${asProvider ? "?as=provider" : ""}`, { method: "POST" });
}

export async function getClinicianPatients(): Promise<ClinicianPatient[]> {
  if (USE_MOCK) {
    await wait(300);
    return [
      {
        patient_id: "00000000-0000-4000-8000-000000000001",
        name: "Maya",
        overall_tier: "amber",
        reasons: [
          "BP rose 4 readings in a row",
          "Headaches 3 of 7 days",
          "Prior gestational hypertension",
        ],
        categories: { high_blood_pressure: "amber", depression_anxiety: "watch", post_cesarean: "green" },
        synthetic: true,
      },
    ];
  }
  return request("/clinician/patients");
}

/** Deletes the patient record, Backboard memories and the account itself (backend ends every session). */
export async function deleteMyData(patientId: string): Promise<void> {
  if (USE_MOCK) {
    await wait(700);
    return;
  }
  await raw(`/patients/${patientId}`, { method: "DELETE" });
}

// --- Agents and care ------------------------------------------------------------------------
export const ask = (patientId: string, question: string) =>
  postJson<AskResult>("/ask", { patient_id: patientId, question });

export const getRisk = (patientId: string) => request<RiskResult>(`/patients/${patientId}/risk`);

export const saveLocation = (patientId: string, loc: { lat?: number; lon?: number; postal_code?: string }) =>
  sendJson<{ lat: number; lon: number; label: string | null }>("PUT", `/patients/${patientId}/location`, loc);

export const getNearby = (patientId: string) => request<Nearby>(`/care/nearby?patient_id=${patientId}`);

/** Nearby care for a ZIP code without saving it (the demo is read-only). */
export const getNearbyByZip = (zip: string) => request<Nearby>(`/care/nearby?zip=${encodeURIComponent(zip)}`);

export async function clearLocation(patientId: string): Promise<void> {
  await raw(`/patients/${patientId}/location`, { method: "DELETE" });
}

export const bookCare = (requestId: string, slot: string, facilityIndex: number) =>
  postJson<{ appointment_id: string }>(`/care-requests/${requestId}/book`, { slot, facility_index: facilityIndex });

export async function dismissCare(requestId: string): Promise<void> {
  await raw(`/care-requests/${requestId}/dismiss`, { method: "POST" });
}

/** Downloads the one-page visit summary PDF (authorized fetch, then a temporary link). */
export async function downloadSummary(patientId: string): Promise<void> {
  const res = await raw(`/patients/${patientId}/summary.pdf`);
  const url = URL.createObjectURL(await res.blob());
  const a = Object.assign(document.createElement("a"), { href: url, download: "tidewell-visit-summary.pdf" });
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

export const createCircle = (patientId: string) =>
  postJson<{ token: string; path: string }>(`/patients/${patientId}/circle`, {});

export async function revokeCircle(patientId: string): Promise<void> {
  await raw(`/patients/${patientId}/circle`, { method: "DELETE" });
}

export const getCircle = (token: string) => request<CircleView>(`/circle/${encodeURIComponent(token)}`);

export const getTodaysEpds = (patientId: string) =>
  request<{ taken: boolean; score: number | null; answers: number[] | null }>(`/epds/today?patient_id=${patientId}`);

export interface ClinicianRow {
  patient_id: string;
  name: string | null;
  is_synthetic: boolean;
  day_postpartum: number;
  delivery_type: string;
  overall_tier: Tier;
  reasons: string[];
  note: string | null;
}

export const getClinicianOverview = () =>
  request<{
    patients: ClinicianRow[];
    appointments: { patient_id: string; slot: string; facility_name: string | null; clinician_note: string | null }[];
    timing: { overview_ms: number; aggregate_ms: number; patients_30d: number; checkins_30d: number };
  }>("/clinician/overview?limit=300");
