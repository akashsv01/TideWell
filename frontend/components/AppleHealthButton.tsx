"use client";

import Link from "next/link";
import { useState } from "react";
import { HeartPlusIcon } from "@/components/icons";
import UrgentCard from "@/components/UrgentCard";
import { ApiError, importAppleHealth, removeSampleHealth } from "@/lib/api";
import { useSession } from "@/lib/session";
import type { HealthImport, RedFlagLevel } from "@/lib/types";
import { focusRing } from "@/lib/ui";

// "Get my Apple Health data", under the voice button. Brings the last 7 days from the iPhone into the
// tide: sleep, blood pressure and resting heart rate (backend POST /wearables/import). With no iPhone
// connected it fills a clearly labelled SAMPLE week in normal ranges, which can be removed.
// The Watch agent then looks at the new numbers exactly as after a check-in.

type State = "idle" | "busy" | "done" | "error";

const dayLabel = (iso: string) =>
  new Date(`${iso}T12:00:00Z`).toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });

export default function AppleHealthButton() {
  const { session } = useSession();
  const patientId = session?.patientId ?? null;
  const demo = session?.kind === "demo";
  const [state, setState] = useState<State>("idle");
  const [res, setRes] = useState<HealthImport | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [urgent, setUrgent] = useState<RedFlagLevel | null>(null);

  async function run() {
    if (!patientId || state === "busy") return;
    if (demo) {
      setState("error");
      setMsg("The demo can't receive Apple Health data. Create your own account to try it.");
      return;
    }
    setState("busy");
    setMsg(null);
    try {
      const r = await importAppleHealth(patientId);
      setRes(r);
      setState("done");
      if (r.red_flag && r.red_flag_level) setUrgent(r.red_flag_level);
    } catch (e) {
      setState("error");
      setMsg(e instanceof ApiError ? e.message : "We couldn't reach Tidewell. Try again.");
    }
  }

  async function removeSample() {
    if (!patientId) return;
    try {
      await removeSampleHealth(patientId);
      setRes(null);
      setState("idle");
      setMsg("Sample data removed.");
    } catch {
      setMsg("We couldn't remove the sample data. Try again.");
    }
  }

  if (urgent)
    return (
      <UrgentCard
        level={urgent}
        context={res?.latest_bp ? `Your blood pressure cuff sent a reading of ${res.latest_bp.sys}/${res.latest_bp.dia} through Apple Health.` : undefined}
        onBack={() => setUrgent(null)}
      />
    );

  const sample = res?.source === "sample";
  return (
    <div className="mt-6 flex w-full flex-col items-center" aria-live="polite">
      <button
        type="button"
        onClick={run}
        aria-disabled={state === "busy"}
        className={`inline-flex min-h-12 items-center gap-2 rounded-full border-2 border-navy/25 bg-white px-5 text-lg font-semibold transition-[background-color,border-color,transform] duration-150 ease-out hover:border-navy/50 motion-safe:active:scale-[0.97] aria-disabled:opacity-60 ${focusRing}`}
      >
        <HeartPlusIcon className="size-5 text-alert" />
        {state === "busy" ? "Getting your Apple Health data…" : "Get my Apple Health data"}
      </button>

      {msg && <p role="status" className="mt-3 max-w-[40ch] text-center text-base text-navy/85">{msg}</p>}

      {state === "done" && res && (
        <section
          aria-label="Apple Health data added"
          className="mt-4 w-full rounded-3xl bg-white p-5 ring-1 ring-navy/10 motion-safe:animate-reply-in"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-display text-xl">{sample ? "Sample Apple Health data" : "From your iPhone"}</h2>
            {sample && (
              <span className="rounded-full bg-sand px-3 py-1 text-sm font-semibold">Sample, not from your phone</span>
            )}
          </div>
          <dl className="mt-4 grid gap-3 sm:grid-cols-3">
            <Stat label="Sleep" value={res.latest_sleep ? `${res.latest_sleep.hours} h` : "–"} note={res.latest_sleep ? dayLabel(res.latest_sleep.day) : "No sleep data"} />
            <Stat label="Blood pressure" value={res.latest_bp ? `${res.latest_bp.sys}/${res.latest_bp.dia}` : "–"} note={res.latest_bp ? dayLabel(res.latest_bp.time.slice(0, 10)) : "No cuff readings"} />
            <Stat label="Resting heart rate" value={res.latest_resting_hr ? `${res.latest_resting_hr.bpm} bpm` : "–"} note={res.latest_resting_hr ? dayLabel(res.latest_resting_hr.day) : "No heart data"} />
          </dl>
          <p className="mt-4 text-base text-navy/85">
            Added {res.sleep_days} {res.sleep_days === 1 ? "night" : "nights"} of sleep, {res.bp_added} BP{" "}
            {res.bp_added === 1 ? "reading" : "readings"} and {res.hr_days} days of heart rate from the last week.
            {res.kept_own_sleep > 0 && ` Your own sleep entries were kept on ${res.kept_own_sleep} ${res.kept_own_sleep === 1 ? "day" : "days"}.`}
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2">
            <Link href="/dashboard" className={`rounded-md py-1 text-lg font-semibold underline underline-offset-4 ${focusRing}`}>
              See my tide
            </Link>
            {sample && (
              <>
                <Link href="/settings#apple-health" className={`rounded-md py-1 text-lg font-semibold underline underline-offset-4 ${focusRing}`}>
                  Connect your iPhone
                </Link>
                <button type="button" onClick={removeSample} className={`rounded-md py-1 text-lg font-semibold underline underline-offset-4 ${focusRing}`}>
                  Remove sample data
                </button>
              </>
            )}
          </div>
        </section>
      )}
    </div>
  );
}

function Stat({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="rounded-2xl bg-foam p-3">
      <dt className="text-sm font-semibold text-navy/75">{label}</dt>
      <dd className="font-display text-2xl tabular-nums">{value}</dd>
      <dd className="text-sm text-navy/70">{note}</dd>
    </div>
  );
}
