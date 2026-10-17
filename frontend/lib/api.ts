import type {
  CheckinMetrics,
  CheckinRequest,
  CheckinResponse,
  ClinicianPatient,
  OnboardRequest,
  OnboardResponse,
  PhotoReading,
  Slot,
  TrendPoint,
} from "@/lib/types";

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const wait = (ms = 400) => new Promise((r) => setTimeout(r, ms));

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

function postJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
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

export async function onboard(input: OnboardRequest): Promise<OnboardResponse> {
  if (USE_MOCK) {
    await wait();
    return { patient_id: input.patient_id ?? "mock-patient", categories: ["postpartum_high_bp", "post_cesarean"] };
  }
  return postJson("/onboard", input);
}

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

export async function getSlots(urgency = "amber"): Promise<Slot[]> {
  if (USE_MOCK) {
    await wait(300);
    return mockSlots();
  }
  return request(`/appointments/slots?urgency=${urgency}`);
}

export async function bookAppointment(
  patientId: string,
  slot: string,
  reason: string
): Promise<{ appointment_id: string }> {
  if (USE_MOCK) {
    await wait(500);
    return { appointment_id: "mock-appt-1" };
  }
  return postJson("/appointments", { patient_id: patientId, slot, reason });
}

export async function getClinicianPatients(): Promise<ClinicianPatient[]> {
  if (USE_MOCK) {
    await wait(300);
    return [
      {
        patient: { id: "maya", name: "Maya (synthetic)" },
        overall_tier: "amber",
        reasons: [
          "BP rose 4 readings in a row",
          "Headaches 3 of 7 days",
          "Prior gestational hypertension",
        ],
      },
    ];
  }
  return request("/clinician/patients");
}

/** Deletes everything Tidewell holds for this patient. Endpoint is a proposal until P1/P2 confirm it. */
export async function deleteMyData(patientId: string): Promise<void> {
  if (USE_MOCK) {
    await wait(700);
    return;
  }
  const res = await fetch(`${BASE}/patients/${patientId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
}
