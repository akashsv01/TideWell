"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getClinicianOverview } from "@/lib/api";
import type { Tier } from "@/lib/types";
import { focusRing } from "@/lib/ui";

// Clinician portal: every patient the Watch agent has assessed, most urgent first, with the reasons
// and its handoff note, plus booked visits. The timing panel shows Tiger Data serving it live.
// Hackathon demo: no clinician login yet (noted on the page).

type Data = Awaited<ReturnType<typeof getClinicianOverview>>;
const TIER: Record<Tier, string> = {
  red: "bg-alert text-white", amber: "bg-chart-amber text-white", watch: "bg-tide-light/40 text-tide-deep", green: "bg-[#e3f1e8] text-[#2f5d3f]",
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
      <header className="flex h-20 items-center justify-between">
        <Link href="/" className={`rounded-md font-display text-2xl text-tide-deep ${focusRing}`}>Tidewell</Link>
        <span className="rounded-full bg-sand px-3 py-1 text-sm font-semibold">Clinician view · demo</span>
      </header>
      <main id="main">
        <h1 className="font-display text-4xl leading-tight">Your patients</h1>
        <p className="mt-2 max-w-[60ch] text-lg text-navy/85">
          Sorted by the Watch agent&apos;s latest assessment. Reasons come from patients&apos; own check-ins; Tidewell never diagnoses.
        </p>

        {data && (
          <div className="mt-6 grid gap-3 sm:grid-cols-4">
            <Stat label="Patients (30 days)" value={data.timing.patients_30d.toLocaleString()} />
            <Stat label="Check-ins (30 days)" value={data.timing.checkins_30d.toLocaleString()} />
            <Stat label="Risk overview query" value={`${data.timing.overview_ms} ms`} />
            <Stat label="Continuous aggregate" value={`${data.timing.aggregate_ms} ms`} />
          </div>
        )}
        {data && <p className="mt-2 text-sm text-navy/70">Live from Tiger Data: hypertables + continuous aggregates.</p>}

        <div className="mt-8 flex flex-wrap items-center gap-2" role="group" aria-label="Filter by tier">
          {(["all", "red", "amber", "watch", "green"] as const).map((t) => (
            <button
              key={t}
              type="button"
              aria-pressed={filter === t}
              onClick={() => setFilter(t)}
              className={`min-h-11 rounded-full border-2 px-4 text-base font-semibold capitalize transition-[background-color,color,transform] duration-150 ease-out motion-safe:active:scale-[0.97] ${filter === t ? "border-navy bg-navy text-white" : "border-navy/25 bg-white"} ${focusRing}`}
            >
              {t}{t !== "all" ? ` (${counts[t]})` : ""}
            </button>
          ))}
          <label className="ml-auto flex cursor-pointer items-center gap-2 text-base">
            <input type="checkbox" checked={showSynthetic} onChange={(e) => setShowSynthetic(e.target.checked)} className="size-5 accent-[#0e6a70]" />
            Include synthetic patients
          </label>
        </div>

        {failed && <p role="alert" className="mt-6 text-lg text-alert">Couldn&apos;t load patients.</p>}
        {!data && !failed && <p role="status" className="mt-6 text-lg">Loading…</p>}

        <ul className="mt-6 space-y-3">
          {rows.slice(0, 60).map((p) => (
            <li key={p.patient_id} className="rounded-2xl bg-white p-5 ring-1 ring-navy/10">
              <div className="flex flex-wrap items-center gap-3">
                <span className={`rounded-full px-3 py-1 text-sm font-bold uppercase ${TIER[p.overall_tier]}`}>{p.overall_tier}</span>
                <span className="text-lg font-semibold">{p.name ?? "Patient"}</span>
                <span className="text-base text-navy/75">Day {p.day_postpartum} · {p.delivery_type === "c-section" ? "C-section" : "Vaginal"}</span>
                {p.is_synthetic && <span className="rounded-full bg-navy/10 px-2 py-0.5 text-xs font-semibold">synthetic</span>}
              </div>
              {p.reasons.length > 0 && <p className="mt-2 text-base leading-relaxed text-navy/85">{p.reasons.join(" · ")}</p>}
              {p.note && <p className="mt-2 rounded-xl bg-sand/60 p-3 text-base"><strong>Agent note:</strong> {p.note}</p>}
            </li>
          ))}
        </ul>
        {rows.length > 60 && <p className="mt-3 text-base text-navy/75">Showing the 60 most urgent of {rows.length}.</p>}

        {data && data.appointments.length > 0 && (
          <section className="mt-10" aria-labelledby="appts">
            <h2 id="appts" className="font-display text-2xl">Booked visits</h2>
            <ul className="mt-3 space-y-2">
              {data.appointments.map((a, i) => (
                <li key={i} className="rounded-2xl bg-white p-4 ring-1 ring-navy/10">
                  <p className="font-semibold">{new Date(a.slot).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" })} · {a.facility_name ?? "Clinic"}</p>
                  {a.clinician_note && <p className="mt-1 text-base text-navy/85">{a.clinician_note}</p>}
                </li>
              ))}
            </ul>
          </section>
        )}
      </main>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-navy p-4 text-white">
      <p className="text-sm text-white/75">{label}</p>
      <p className="font-display text-2xl tabular-nums">{value}</p>
    </div>
  );
}
