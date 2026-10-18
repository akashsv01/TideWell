"use client";

import Wordmark from "@/components/Wordmark";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { getCircle } from "@/lib/api";
import type { CircleView } from "@/lib/types";

// Care Circle: what a support person sees from the private link. Deliberately limited: how the
// parent is doing and how to help. No transcripts, no mood-check answers.

// Said as a sentence; the more serious, the larger.
const STATUS = {
  green: "Things look steady.",
  watch: "This has been a harder week.",
  amber: "Tidewell has suggested a doctor visit.",
  red: "Tidewell says they need care now.",
} as const;

export default function CircleViewPanel() {
  const { token } = useParams<{ token: string }>();
  const [v, setV] = useState<CircleView | null>(null);
  const [gone, setGone] = useState(false);

  useEffect(() => {
    if (token) getCircle(token).then(setV, () => setGone(true));
  }, [token]);

  return (
    <div className="flex min-h-dvh flex-col bg-foam text-navy">
      <header className="mx-auto flex h-16 w-full max-w-xl items-center justify-between gap-4 px-5 sm:px-8 md:h-20">
        <Wordmark href="/" />
        <p className="text-base text-navy/80">Care Circle, read only</p>
      </header>
      <main id="main" className="mx-auto w-full max-w-xl flex-1 px-5 pb-12 sm:px-8">
        {gone && (
          <div role="alert" className="mt-6">
            <h1 className="font-display text-4xl font-semibold leading-tight">This link is no longer active</h1>
            <p className="mt-3 max-w-[48ch] text-lg leading-relaxed">
              Care Circle links can be turned off or replaced. Ask the person who shared it for a new one.
            </p>
          </div>
        )}
        {!v && !gone && <p role="status" className="mt-10 text-xl">Loading…</p>}
        {v && (
          <div className="motion-safe:animate-reply-in">
            <h1 className="mt-4 font-display text-4xl font-semibold leading-tight">How {v.name} is doing</h1>
            <p className="mt-2 text-lg text-navy/85">Day {v.day_postpartum} after giving birth</p>
            <div className={`mt-6 rounded-2xl bg-white p-6 shadow-paper ${v.status === "red" ? "ring-2 ring-alert/40" : "ring-1 ring-navy/10"}`}>
              <p className={v.status === "green" ? "text-xl font-semibold" : `font-display text-3xl font-semibold leading-snug ${v.status === "red" ? "text-alert" : ""}`}>
                {STATUS[v.status]}
              </p>
              <p className="mt-2 text-lg leading-relaxed">{v.how_to_help}</p>
            </div>
            <dl className="mt-6 divide-y divide-navy/10 rounded-2xl bg-white px-5 text-lg shadow-paper ring-1 ring-navy/10">
              <div className="flex justify-between gap-4 py-4">
                <dt className="text-navy/80">Sleep, average this week</dt>
                <dd className="font-semibold tabular-nums">{v.avg_sleep_7d != null ? `${v.avg_sleep_7d} hours a night` : "Not logged"}</dd>
              </div>
              <div className="flex justify-between gap-4 py-4">
                <dt className="text-navy/80">Last check-in</dt>
                <dd className="font-semibold">{v.last_checkin ? new Date(v.last_checkin).toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" }) : "None yet"}</dd>
              </div>
            </dl>
            {v.appointments.length > 0 && (
              <div className="mt-6">
                <h2 className="font-display text-2xl font-semibold">Upcoming visits</h2>
                {v.appointments.map((a, i) => (
                  <p key={i} className="mt-2 text-lg">{new Date(a.slot).toLocaleString("en-US", { weekday: "long", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}{a.where ? ` · ${a.where}` : ""}</p>
                ))}
              </div>
            )}
            <p className="mt-8 text-base text-navy/80">If they tell you about severe headache, vision changes, chest pain, heavy bleeding or thoughts of harming themselves or the baby, call 911.</p>
          </div>
        )}
      </main>
    </div>
  );
}
