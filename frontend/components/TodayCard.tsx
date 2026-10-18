"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getOverview, getRisk, getTodaysEpds } from "@/lib/api";
import { usePatientId } from "@/lib/session";
import type { Overview } from "@/lib/types";
import { focusRing } from "@/lib/ui";

// Top of the check-in screen: a personal greeting, the mood check (weekly reminder, available any
// day, editable the same day), and a nudge when the care agents suggest a visit.
export default function TodayCard() {
  const patientId = usePatientId();
  const [ov, setOv] = useState<Overview | null>(null);
  const [taken, setTaken] = useState(false);
  const [visit, setVisit] = useState(false);

  useEffect(() => {
    if (!patientId) return;
    let cancelled = false;
    getOverview(patientId).then((o) => !cancelled && setOv(o), () => {});
    getTodaysEpds(patientId).then((t) => !cancelled && setTaken(t.taken), () => {});
    getRisk(patientId).then((r) => !cancelled && setVisit(Boolean(r.care_request && r.care_request.tier !== "red")), () => {});
    return () => {
      cancelled = true;
    };
  }, [patientId]);

  if (!ov) return <div className="h-7" aria-hidden="true" />;

  const card = `group flex items-center justify-between gap-4 rounded-3xl p-5 transition-[background-color,transform] duration-150 ease-out motion-safe:active:scale-[0.99] ${focusRing} motion-safe:animate-reply-in`;
  const arrow = (
    <span aria-hidden="true" className="grid size-11 shrink-0 place-items-center rounded-full bg-tide-deep text-xl text-white transition-transform duration-150 ease-out group-hover:translate-x-0.5">
      →
    </span>
  );

  return (
    <div className="w-full space-y-3 motion-safe:animate-fade-in">
      <p className="text-center text-lg text-navy/85">
        {ov.name ? `Hi ${ov.name}. ` : ""}Day {ov.day_postpartum} after giving birth
      </p>
      {visit && (
        <Link href="/care" className={`${card} border-l-8 border-chart-amber bg-sand/80 hover:bg-sand`}>
          <span>
            <span className="block font-display text-xl">Tidewell suggests a visit</span>
            <span className="mt-1 block text-base text-navy/85">See why, and pick a time near you.</span>
          </span>
          {arrow}
        </Link>
      )}
      <Link href="/mood-check" className={`${card} bg-sand/60 hover:bg-sand/90`}>
        <span>
          <span className="block font-display text-xl">
            {taken ? "Edit today's mood check" : ov.epds_due ? "Your weekly mood check" : "Mood check"}
          </span>
          <span className="mt-1 block text-base text-navy/85">
            {taken ? "Change any answer from today." : "10 short questions, about two minutes."}
          </span>
        </span>
        {arrow}
      </Link>
    </div>
  );
}
