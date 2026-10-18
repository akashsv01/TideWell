"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Waves from "@/components/Waves";
import { getCircle } from "@/lib/api";
import type { CircleView } from "@/lib/types";
import { focusRing } from "@/lib/ui";

// Care Circle: what a support person sees from the private link. Deliberately limited: how the
// parent is doing and how to help. No transcripts, no mood-check answers.

const STATUS = {
  green: { title: "Steady", tone: "bg-[#e3f1e8] text-[#2f5d3f]" },
  watch: { title: "A harder week", tone: "bg-tide-light/30 text-tide-deep" },
  amber: { title: "A doctor visit is suggested", tone: "bg-chart-amber/20 text-[#7a4a10]" },
  red: { title: "Needs care now", tone: "bg-alert/15 text-alert" },
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
      <header className="mx-auto flex h-16 w-full max-w-xl items-center px-5">
        <Link href="/" className={`rounded-md font-display text-2xl text-tide-deep ${focusRing}`}>Tidewell</Link>
      </header>
      <main id="main" className="mx-auto w-full max-w-xl flex-1 px-5 pb-10">
        {gone && <p role="alert" className="mt-10 text-xl">This link is no longer active. Ask for a new one.</p>}
        {!v && !gone && <p role="status" className="mt-10 text-xl">Loading…</p>}
        {v && (
          <div className="motion-safe:animate-reply-in">
            <p className="text-lg text-navy/80">Care Circle</p>
            <h1 className="font-display text-4xl leading-tight">How {v.name} is doing</h1>
            <p className="mt-2 text-lg">Day {v.day_postpartum} after giving birth</p>
            <div className={`mt-6 rounded-3xl p-6 ${STATUS[v.status].tone}`}>
              <p className="font-display text-2xl">{STATUS[v.status].title}</p>
              <p className="mt-2 text-lg leading-relaxed text-navy">{v.how_to_help}</p>
            </div>
            <dl className="mt-6 grid grid-cols-2 gap-3">
              <div className="rounded-2xl bg-white p-4 ring-1 ring-navy/10">
                <dt className="text-base text-navy/75">Sleep this week</dt>
                <dd className="font-display text-2xl">{v.avg_sleep_7d != null ? `${v.avg_sleep_7d} h` : "–"}</dd>
              </div>
              <div className="rounded-2xl bg-white p-4 ring-1 ring-navy/10">
                <dt className="text-base text-navy/75">Last check-in</dt>
                <dd className="font-display text-2xl">{v.last_checkin ? new Date(v.last_checkin).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "–"}</dd>
              </div>
            </dl>
            {v.appointments.length > 0 && (
              <div className="mt-6">
                <h2 className="font-display text-2xl">Upcoming visits</h2>
                {v.appointments.map((a, i) => (
                  <p key={i} className="mt-2 text-lg">{new Date(a.slot).toLocaleString("en-US", { weekday: "long", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}{a.where ? ` · ${a.where}` : ""}</p>
                ))}
              </div>
            )}
            <p className="mt-8 text-base text-navy/80">If they tell you about severe headache, vision changes, chest pain, heavy bleeding or thoughts of harming themselves or the baby, call 911.</p>
          </div>
        )}
      </main>
      <Waves className="relative h-20" layers={[{ color: "#efe3c8", amp: 8, cycles: 2, top: 60, seconds: 34 }, { color: "#13828a", amp: 10, cycles: 3, top: 86, seconds: 26, reverse: true }, { color: "#0b2545", amp: 11, cycles: 2, top: 112, seconds: 20 }]} />
    </div>
  );
}
