"use client";

import Wordmark from "@/components/Wordmark";
import { useEffect, useMemo, useState } from "react";
import { AlertIcon } from "@/components/icons";
import { getClinicianOverview } from "@/lib/api";
import { DEMO_PATIENT_ID } from "@/lib/config";
import type { Tier } from "@/lib/types";
import { focusRing } from "@/lib/ui";

// Clinician portal: every patient the Watch agent has assessed, most urgent first, with the reasons
// and its handoff note, plus booked visits. Database timings (Tiger Data) are kept out of the
// clinical view, in a labelled "technical details" disclosure at the end.
// Hackathon demo: no clinician login yet (noted on the page).

type Data = Awaited<ReturnType<typeof getClinicianOverview>>;
// Plain labels, said as text; the more serious tiers are set larger and carry the alert icon.
// The API prefixes each reason with its category key ("high_blood_pressure: ..."); say it in words.
const CATEGORY: Record<string, string> = {
  high_blood_pressure: "Blood pressure", depression_anxiety: "Mood", post_cesarean: "C-section recovery",
  sleep: "Sleep", disengagement: "Check-ins",
};
// Stored reasons may also be several joined with "; ". Each becomes its own sentence, and the
// category word is dropped when the reason already names it ("Blood pressure 144/93 ...").
function plainReasons(reasons: string[]): string {
  return reasons
    .flatMap((r) => {
      const m = r.match(/^([a-z_]+): ([\s\S]*)$/);
      const label = m ? CATEGORY[m[1]] : undefined;
      const parts = (m ? m[2] : r).split(/;\s+/).map((x) => x.trim().replace(/\.$/, "")).filter(Boolean);
      if (!label) return parts;
      const first = label.split(" ")[0].toLowerCase();
      const says = (x: string) => x.toLowerCase().startsWith(first) || x.toLowerCase().includes(label.toLowerCase());
      return parts.map((x) => (says(x) ? x : `${label}: ${x}`));
    })
    .map((x) => `${x}.`)
    .join(" ");
}

const TIER: Record<Tier, string> = {
  red: "Needs care now", amber: "Visit soon", watch: "Watching", green: "Steady",
};

export default function ClinicianPortal() {
  const [data, setData] = useState<Data | null>(null);
  const [failed, setFailed] = useState(false);
  const [filter, setFilter] = useState<Tier | "all">("all");
  const [showSynthetic, setShowSynthetic] = useState(true);

  useEffect(() => {
    getClinicianOverview().then(setData, () => setFailed(true));
  }, []);

  const rows = useMemo(
    () => (data?.patients ?? []).filter((p) => (filter === "all" || p.overall_tier === filter) && (showSynthetic || !p.is_synthetic)),
    [data, filter, showSynthetic]
  );
  const counts = useMemo(() => {
    const c: Record<string, number> = { red: 0, amber: 0, watch: 0, green: 0 };
    for (const p of data?.patients ?? []) c[p.overall_tier]++;
    return c;
  }, [data]);

  return (
    <div className="mx-auto w-full max-w-6xl px-5 pb-16 sm:px-8">
      <header className="flex h-20 items-center justify-between gap-4">
        <Wordmark href="/" />
        <p className="text-right text-base text-navy/80">Clinician view, demo without login</p>
      </header>
      <main id="main" className="pt-4">
        <h1 className="font-display text-4xl font-semibold leading-tight">Your patients</h1>
        <p className="mt-2 max-w-[62ch] text-lg text-navy/85">
          Most urgent first, by Tidewell&apos;s latest check of each patient&apos;s numbers against guideline limits.
          Reasons come from patients&apos; own check-ins. Tidewell never diagnoses.
        </p>
        {data && (
          <p className="mt-3 text-lg">
            {data.timing.patients_30d.toLocaleString()} patients and {data.timing.checkins_30d.toLocaleString()} check-ins
            in the last 30 days. Most are synthetic demo patients.
          </p>
        )}

        <div className="mt-8 flex flex-wrap items-center gap-2" role="group" aria-label="Filter by tier">
          {(["all", "red", "amber", "watch", "green"] as const).map((t) => (
            <button
              key={t}
              type="button"
              aria-pressed={filter === t}
              onClick={() => setFilter(t)}
              className={`min-h-11 rounded-full border-2 px-4 text-base font-semibold transition-[background-color,color,transform] duration-150 ease-out motion-safe:active:scale-[0.97] ${filter === t ? "border-navy bg-navy text-white" : "border-navy/25 bg-white"} ${focusRing}`}
            >
              {t === "all" ? "All" : `${TIER[t]} (${counts[t]})`}
            </button>
          ))}
          <label className="ml-auto flex cursor-pointer items-center gap-2 text-base">
            <input type="checkbox" checked={showSynthetic} onChange={(e) => setShowSynthetic(e.target.checked)} className="size-5 accent-tide-deep" />
            Include synthetic patients
          </label>
        </div>

        {failed && <p role="alert" className="mt-6 text-lg text-alert">Couldn&apos;t load patients.</p>}
        {!data && !failed && <p role="status" className="mt-6 text-lg">Loading…</p>}

        <ul className="mt-6 divide-y divide-navy/10 rounded-2xl bg-white shadow-paper ring-1 ring-navy/10">
          {rows.slice(0, 60).map((p) => {
            const serious = p.overall_tier === "red" || p.overall_tier === "amber";
            return (
              <li key={p.patient_id} className="flex gap-3 p-5">
                {serious ? (
                  <AlertIcon className={`mt-1 size-6 shrink-0 ${p.overall_tier === "red" ? "text-alert" : "text-navy"}`} />
                ) : (
                  <span aria-hidden="true" className="size-6 shrink-0" />
                )}
                <div className="min-w-0 flex-1">
                  <p className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <span className={serious ? "text-xl font-semibold" : "text-lg font-semibold"}>{p.name ?? "Patient"}</span>
                    <span className="text-base text-navy/75">
                      Day {p.day_postpartum}, {p.delivery_type === "c-section" ? "C-section" : "vaginal birth"}
                      {p.is_synthetic
                        ? " (synthetic)"
                        : p.patient_id === DEMO_PATIENT_ID
                          ? " (demo patient)"
                          : " (account created in the app, may be a test)"}
                    </span>
                  </p>
                  <p className={`mt-1 ${serious ? "text-lg" : "text-base text-navy/85"}`}>
                    <span className={`font-semibold ${p.overall_tier === "red" ? "text-alert" : ""}`}>{TIER[p.overall_tier]}.</span>{" "}
                    {plainReasons(p.reasons)}
                  </p>
                  {p.note && <p className="mt-2 rounded-xl bg-sand/60 p-3 text-base"><strong>Handoff note:</strong> {p.note}</p>}
                </div>
              </li>
            );
          })}
        </ul>
        {rows.length > 60 && <p className="mt-3 text-base text-navy/75">Showing the 60 most urgent of {rows.length}.</p>}

        {data && data.appointments.length > 0 && (
          <section className="mt-10" aria-labelledby="appts">
            <h2 id="appts" className="font-display text-2xl font-semibold">Booked visits</h2>
            <ul className="mt-3 divide-y divide-navy/10 rounded-2xl bg-white shadow-paper ring-1 ring-navy/10">
              {data.appointments.map((a, i) => (
                <li key={i} className="p-4">
                  <p className="font-semibold">{new Date(a.slot).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" })} · {a.facility_name ?? "Clinic"}</p>
                  {a.clinician_note && <p className="mt-1 text-base text-navy/85">{a.clinician_note}</p>}
                </li>
              ))}
            </ul>
          </section>
        )}

        {data && (
          <details className="mt-12 text-base text-navy/80">
            <summary className={`w-fit cursor-pointer rounded-md font-semibold ${focusRing}`}>
              Technical details for the demo (not clinical)
            </summary>
            <p className="mt-2 max-w-[62ch]">
              This page is served live from Tiger Data (hypertables and continuous aggregates). The risk overview query
              took {data.timing.overview_ms} ms and the continuous aggregate {data.timing.aggregate_ms} ms on this load.
            </p>
          </details>
        )}
      </main>
    </div>
  );
}
