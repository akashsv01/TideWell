import { todayIso } from "@/lib/profile";
import type { TrendPoint } from "@/lib/types";

/** Shift a YYYY-MM-DD by N days (noon anchor avoids DST off-by-one). */
export function addDaysIso(iso: string, days: number): string {
  const d = new Date(`${iso}T12:00:00`);
  d.setDate(d.getDate() + days);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** Delivery date from overview day_postpartum. */
export function deliveryFromDayPostpartum(dayPostpartum: number): string {
  return addDaysIso(todayIso(), -dayPostpartum);
}

/**
 * Continuous daily series from max(delivery, today-20) to today.
 * Missing days are null metrics with headache false (so the headache strip is complete).
 */
export function fillDailySeries(raw: TrendPoint[], deliveryDate: string): TrendPoint[] {
  const today = todayIso();
  const windowStart = addDaysIso(today, -20);
  const start = deliveryDate > windowStart ? deliveryDate : windowStart;
  const byDay = new Map(raw.map((p) => [p.day, p]));
  const out: TrendPoint[] = [];
  for (let day = start; day <= today; day = addDaysIso(day, 1)) {
    const existing = byDay.get(day);
    if (existing) {
      out.push({ ...existing, headache: Boolean(existing.headache) });
    } else {
      const birth = new Date(`${deliveryDate}T12:00:00`);
      const cur = new Date(`${day}T12:00:00`);
      const dayPostpartum = Math.round((cur.getTime() - birth.getTime()) / 86_400_000);
      out.push({
        day,
        day_postpartum: dayPostpartum,
        mood: null,
        pain: null,
        incision_pain: null,
        sleep_hrs: null,
        headache: false,
        bp_sys: null,
        bp_dia: null,
        epds_score: null,
        item_10_alert: false,
      });
    }
  }
  return out;
}
