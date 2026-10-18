"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AlertIcon } from "@/components/icons";
import { getOverview, getRisk, getTodaysEpds } from "@/lib/api";
import { usePatientId } from "@/lib/session";
import type { Overview } from "@/lib/types";
import { focusRing } from "@/lib/ui";

// Top of the check-in screen: a personal greeting, the daily mood check (editable the same day), and a
// nudge when the care agents suggest a visit.
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

  const row = `group flex items-center justify-between gap-4 px-5 py-4 transition-[background-color] duration-150 ease-out hover:bg-sand/50 ${focusRing}`;
  const chevron = (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="size-6 shrink-0 text-navy/60 transition-transform duration-150 ease-out group-hover:translate-x-0.5">
      <path d="m9 6 6 6-6 6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );

  return (
    <section aria-label="Today" className="w-full motion-safe:animate-fade-in">
      <p className="text-center text-lg text-navy/85">
        {ov.name ? `${ov.name}, day` : "Day"} {ov.day_postpartum} after giving birth
      </p>
      <div className="mt-3 divide-y divide-navy/10 overflow-hidden rounded-2xl bg-white shadow-paper ring-1 ring-navy/10">
        {visit && (
          <Link href="/care" className={row}>
            <span>
              <span className="flex items-center gap-2 text-lg font-semibold">
                <AlertIcon className="size-5 shrink-0 text-navy" />
                Tidewell suggests a visit
              </span>
              <span className="mt-0.5 block text-base text-navy/80">See why, and pick a time that suits you.</span>
            </span>
            {chevron}
          </Link>
        )}
        <Link href="/mood-check" className={row}>
          <span>
            <span className="block text-lg font-semibold">
              {taken ? "Change today's mood check" : "Today's mood check"}
            </span>
            <span className="mt-0.5 block text-base text-navy/80">
              {taken ? "You can change any answer from today." : "10 short questions, about two minutes."}
            </span>
          </span>
          {chevron}
        </Link>
      </div>
    </section>
  );
}
