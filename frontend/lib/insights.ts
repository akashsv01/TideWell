import type { TrendPoint } from "@/lib/types";

// Plain-language summaries computed from the trend data. They describe what the numbers did.
// They never diagnose. Clinical rules belong to the backend and Person 4.

const mean = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);

const nums = (points: TrendPoint[], key: keyof Omit<TrendPoint, "day">) =>
  points.map((p) => p[key]).filter((v): v is number => v !== null);

/** "Oct 3" style label for a YYYY-MM-DD day. */
export function shortDay(day: string): string {
  return new Date(`${day}T00:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function moodSentence(points: TrendPoint[]): string | null {
  const mood = nums(points, "mood");
  if (mood.length < 6) return null;
  const early = mean(mood.slice(0, 5))!;
  const late = mean(mood.slice(-5))!;
  const diff = late - early;
  if (diff <= -1) {
    return `Your mood has drifted down, from about ${Math.round(early)} to about ${Math.round(late)} out of 10.`;
  }
  if (diff >= 1) {
    return `Your mood has been lifting, from about ${Math.round(early)} to about ${Math.round(late)} out of 10.`;
  }
  return `Your mood has held steady, around ${Math.round(late)} out of 10.`;
}

export function sleepSentence(points: TrendPoint[]): string | null {
  const sleep = nums(points.slice(-7), "sleep_hrs");
  if (!sleep.length) return null;
  const avg = mean(sleep)!;
  return `You have been sleeping about ${avg.toFixed(1)} hours a night this week.`;
}

export type BpRise = {
  readings: { sys: number; dia: number }[];
  latest: { sys: number; dia: number };
  atOrAbove140: boolean;
};

/** Looks at the last four readings. Returns details only if the top number rose every time. */
export function bpRise(points: TrendPoint[]): BpRise | null {
  const readings = points
    .filter((p) => p.bp_sys !== null && p.bp_dia !== null)
    .map((p) => ({ sys: p.bp_sys as number, dia: p.bp_dia as number }))
    .slice(-4);
  if (readings.length < 4) return null;
  for (let i = 1; i < readings.length; i++) {
    if (readings[i].sys <= readings[i - 1].sys) return null;
  }
  const latest = readings[readings.length - 1];
  return { readings, latest, atOrAbove140: latest.sys >= 140 || latest.dia >= 90 };
}
