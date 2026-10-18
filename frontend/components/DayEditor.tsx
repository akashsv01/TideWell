"use client";

import Link from "next/link";
import { useId, useState } from "react";
import CuffPhotoButton from "@/components/CuffPhotoButton";
import UrgentCard from "@/components/UrgentCard";
import { ApiError, saveDay } from "@/lib/api";
import { todayIso } from "@/lib/profile";
import type { DayEntry, DeliveryType, RedFlagLevel, TrendPoint } from "@/lib/types";
import { btnPrimary, focusRing } from "@/lib/ui";

const field = `mt-2 min-h-14 w-full rounded-2xl border-2 border-navy bg-white px-4 text-lg ${focusRing}`;

type Props = {
  patientId: string;
  demo: boolean;
  deliveryDate: string; // YYYY-MM-DD
  deliveryMethod: DeliveryType;
  points: TrendPoint[];
  day: string;
  onDayChange: (day: string) => void;
  onSaved: () => void;
};

function numOrEmpty(v: number | null | undefined): string {
  return v == null ? "" : String(v);
}

function parseOptInt(s: string): number | null {
  const t = s.trim();
  if (!t) return null;
  const n = Number(t);
  return Number.isFinite(n) ? Math.round(n) : null;
}

function parseOptFloat(s: string): number | null {
  const t = s.trim();
  if (!t) return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
}

type Draft = {
  mood: string;
  pain: string;
  incision: string;
  sleep: string;
  headache: boolean;
  bpSys: string;
  bpDia: string;
};

function draftFromPoint(p: TrendPoint | undefined): Draft {
  return {
    mood: numOrEmpty(p?.mood),
    pain: numOrEmpty(p?.pain),
    incision: numOrEmpty(p?.incision_pain),
    sleep: numOrEmpty(p?.sleep_hrs),
    headache: Boolean(p?.headache),
    bpSys: numOrEmpty(p?.bp_sys),
    bpDia: numOrEmpty(p?.bp_dia),
  };
}

export default function DayEditor(props: Props) {
  if (props.demo) {
    return (
      <section id="log" aria-labelledby="log-title" className="rounded-3xl bg-sand/70 p-6">
        <h2 id="log-title" className="font-display text-2xl">
          Log or edit a day
        </h2>
        <p className="mt-3 text-lg leading-relaxed">
          Maya&apos;s numbers are read-only.{" "}
          <Link href="/register" className={`font-semibold underline underline-offset-4 ${focusRing}`}>
            Create an account
          </Link>{" "}
          to log your own days.
        </p>
      </section>
    );
  }

  // Remount when the day (or that day's data) changes so fields re-init without an effect.
  const point = props.points.find((x) => x.day === props.day);
  const formKey = `${props.day}:${point?.mood ?? ""}:${point?.bp_sys ?? ""}:${point?.headache ? 1 : 0}`;

  return <DayEditorForm key={formKey} {...props} initial={draftFromPoint(point)} />;
}

function DayEditorForm({
  patientId,
  deliveryDate,
  deliveryMethod,
  day,
  onDayChange,
  onSaved,
  initial,
}: Props & { initial: Draft }) {
  const ids = useId();
  const today = todayIso();
  const csection = deliveryMethod === "c-section";

  const [mood, setMood] = useState(initial.mood);
  const [pain, setPain] = useState(initial.pain);
  const [incision, setIncision] = useState(initial.incision);
  const [sleep, setSleep] = useState(initial.sleep);
  const [headache, setHeadache] = useState(initial.headache);
  const [bpSys, setBpSys] = useState(initial.bpSys);
  const [bpDia, setBpDia] = useState(initial.bpDia);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flag, setFlag] = useState<RedFlagLevel | null>(null);

  if (flag) return <UrgentCard level={flag} />;

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    if (saving) return;
    const sys = parseOptInt(bpSys);
    const dia = parseOptInt(bpDia);
    if ((sys == null) !== (dia == null)) {
      setError("Enter both blood pressure numbers, or leave both blank.");
      return;
    }
    const entry: DayEntry = {
      mood: parseOptInt(mood),
      pain: parseOptInt(pain),
      incision_pain: csection ? parseOptInt(incision) : null,
      sleep_hrs: parseOptFloat(sleep),
      headache,
      bp_sys: sys,
      bp_dia: dia,
    };
    setSaving(true);
    setError(null);
    try {
      const out = await saveDay(patientId, day, entry);
      onSaved();
      if (out.red_flag && out.red_flag_level) setFlag(out.red_flag_level);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "We couldn't save. Check your connection and try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section id="log" aria-labelledby="log-title" className="rounded-3xl bg-sand/70 p-6">
      <h2 id="log-title" className="font-display text-2xl">
        Log or edit a day
      </h2>
      <p className="mt-2 text-lg text-navy/85">Add or correct the numbers for one day. Voice check-ins still work as usual.</p>

      <form onSubmit={onSave} className="mt-6 space-y-5">
        <div>
          <label htmlFor={`${ids}-day`} className="text-base font-semibold">
            Day
          </label>
          <input
            id={`${ids}-day`}
            type="date"
            required
            min={deliveryDate}
            max={today}
            value={day}
            onChange={(e) => onDayChange(e.target.value)}
            className={field}
          />
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label htmlFor={`${ids}-mood`} className="text-base font-semibold">
              Mood (0–10)
            </label>
            <input id={`${ids}-mood`} type="number" inputMode="numeric" min={0} max={10} value={mood} onChange={(e) => setMood(e.target.value)} className={field} />
          </div>
          <div>
            <label htmlFor={`${ids}-pain`} className="text-base font-semibold">
              Pain (0–10)
            </label>
            <input id={`${ids}-pain`} type="number" inputMode="numeric" min={0} max={10} value={pain} onChange={(e) => setPain(e.target.value)} className={field} />
          </div>
          {csection && (
            <div>
              <label htmlFor={`${ids}-inc`} className="text-base font-semibold">
                Incision pain (0–10)
              </label>
              <input id={`${ids}-inc`} type="number" inputMode="numeric" min={0} max={10} value={incision} onChange={(e) => setIncision(e.target.value)} className={field} />
            </div>
          )}
          <div>
            <label htmlFor={`${ids}-sleep`} className="text-base font-semibold">
              Sleep (hours)
            </label>
            <input id={`${ids}-sleep`} type="number" inputMode="decimal" min={0} max={24} step={0.1} value={sleep} onChange={(e) => setSleep(e.target.value)} className={field} />
          </div>
        </div>

        <fieldset>
          <legend className="text-base font-semibold">Headache</legend>
          <div className="mt-2 flex gap-3">
            <label className={`flex min-h-12 flex-1 cursor-pointer items-center justify-center rounded-2xl border-2 px-4 text-lg font-semibold transition-[color,background-color,border-color,transform] duration-150 ease-out motion-safe:active:scale-[0.97] ${headache ? "border-tide-deep bg-tide-deep text-white" : "border-navy/25 bg-white"}`}>
              <input type="radio" name={`${ids}-head`} checked={headache} onChange={() => setHeadache(true)} className="sr-only" />
              Yes
            </label>
            <label className={`flex min-h-12 flex-1 cursor-pointer items-center justify-center rounded-2xl border-2 px-4 text-lg font-semibold transition-[color,background-color,border-color,transform] duration-150 ease-out motion-safe:active:scale-[0.97] ${!headache ? "border-tide-deep bg-tide-deep text-white" : "border-navy/25 bg-white"}`}>
              <input type="radio" name={`${ids}-head`} checked={!headache} onChange={() => setHeadache(false)} className="sr-only" />
              No
            </label>
          </div>
        </fieldset>

        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label htmlFor={`${ids}-sys`} className="text-base font-semibold">
              Blood pressure (top)
            </label>
            <input id={`${ids}-sys`} type="number" inputMode="numeric" min={50} max={300} value={bpSys} onChange={(e) => setBpSys(e.target.value)} className={field} />
          </div>
          <div>
            <label htmlFor={`${ids}-dia`} className="text-base font-semibold">
              Blood pressure (bottom)
            </label>
            <input id={`${ids}-dia`} type="number" inputMode="numeric" min={30} max={200} value={bpDia} onChange={(e) => setBpDia(e.target.value)} className={field} />
          </div>
        </div>
        <CuffPhotoButton
          patientId={patientId}
          onRead={(s, d) => {
            setBpSys(String(s));
            setBpDia(String(d));
          }}
        />

        {error && (
          <p role="alert" className="text-lg text-alert">
            {error}
          </p>
        )}

        <button type="submit" aria-disabled={saving} className={btnPrimary}>
          {saving ? "Saving…" : "Save this day"}
        </button>
      </form>
    </section>
  );
}
