import type { Visit, VisitMode } from "@/lib/types";

// Helpers for showing and exporting visits. Times are shown in the clinic's time zone so the
// patient and the provider read the same clock.

const TZ = "America/New_York";

export const modeLabel = (m: VisitMode) => (m === "virtual" ? "Video visit" : "In person");

export function dayLabel(iso: string): string {
  return new Intl.DateTimeFormat("en-US", { weekday: "long", month: "long", day: "numeric", timeZone: TZ }).format(
    new Date(iso)
  );
}

export function timeLabel(iso: string, withZone = false): string {
  return new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
    timeZone: TZ,
    ...(withZone ? { timeZoneName: "short" as const } : {}),
  }).format(new Date(iso));
}

export const whenLabel = (iso: string) => `${dayLabel(iso)} at ${timeLabel(iso, true)}`;

/** Groups slots by clinic-local day, keeping order. */
export function groupByDay(slots: { slot: string }[]): { day: string; slots: string[] }[] {
  const out: { day: string; slots: string[] }[] = [];
  for (const { slot } of slots) {
    const day = dayLabel(slot);
    const last = out[out.length - 1];
    if (last && last.day === day) last.slots.push(slot);
    else out.push({ day, slots: [slot] });
  }
  return out;
}

const VISIT_MS = 30 * 60_000;
const END_GRACE_MS = 2 * 3600_000;

/** A booked visit that has not ended yet (video rooms stay open two hours past the start). */
export const isUpcoming = (v: Visit, now = Date.now()) =>
  v.status === "booked" && new Date(v.slot).getTime() + END_GRACE_MS > now;

const icsStamp = (d: Date) => d.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
const icsText = (s: string) => s.replace(/\\/g, "\\\\").replace(/[;,]/g, (c) => `\\${c}`).replace(/\r?\n/g, "\\n");

/** A calendar file (.ics) for one visit, so it can go into any calendar app. */
export function buildIcs(v: Visit): string {
  const start = new Date(v.slot);
  const end = new Date(start.getTime() + VISIT_MS);
  const where = v.mode === "virtual" ? "Video visit (join from the Visits tab in Tidewell)" : [v.provider.clinic, v.provider.address].filter(Boolean).join(", ");
  return [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Tidewell//Visits//EN",
    "BEGIN:VEVENT",
    `UID:${v.appointment_id}@tidewell`,
    `DTSTAMP:${icsStamp(new Date())}`,
    `DTSTART:${icsStamp(start)}`,
    `DTEND:${icsStamp(end)}`,
    `SUMMARY:${icsText(`Visit with ${v.provider.name}`)}`,
    `LOCATION:${icsText(where)}`,
    `DESCRIPTION:${icsText(v.reason || "Postpartum visit")}`,
    "END:VEVENT",
    "END:VCALENDAR",
  ].join("\r\n");
}

export function downloadIcs(v: Visit) {
  const url = URL.createObjectURL(new Blob([buildIcs(v)], { type: "text/calendar" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = "tidewell-visit.ics";
  a.click();
  URL.revokeObjectURL(url);
}
