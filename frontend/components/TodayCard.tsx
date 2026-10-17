"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getOverview } from "@/lib/api";
import { usePatientId } from "@/lib/session";
import type { Overview } from "@/lib/types";
import { focusRing } from "@/lib/ui";

// Top of the check-in screen: a personal greeting with the postpartum day, and the weekly mood
// check when it is due (weekly from day 7).
export default function TodayCard() {
  const patientId = usePatientId();
  const [ov, setOv] = useState<Overview | null>(null);

  useEffect(() => {
    if (!patientId) return;
    let cancelled = false;
    getOverview(patientId).then(
      (o) => !cancelled && setOv(o),
      () => {}
    );
    return () => {
      cancelled = true;
    };
  }, [patientId]);

  if (!ov) return <div className="h-7" aria-hidden="true" />;

  return (
    <div className="w-full space-y-4 motion-safe:animate-fade-in">
      <p className="text-center text-lg text-navy/85">
        {ov.name ? `Hi ${ov.name}. ` : ""}Day {ov.day_postpartum} after giving birth
      </p>
      {ov.epds_due && (
        <Link
          href="/mood-check"
          className={`group flex items-center justify-between gap-4 rounded-3xl bg-sand/80 p-5 transition-colors duration-150 hover:bg-sand ${focusRing} motion-safe:animate-reply-in`}
        >
          <span>
            <span className="block font-display text-xl">Your weekly mood check</span>
            <span className="mt-1 block text-base text-navy/85">10 short questions, about two minutes.</span>
          </span>
          <span
            aria-hidden="true"
            className="grid size-11 shrink-0 place-items-center rounded-full bg-tide-deep text-xl text-white transition-transform duration-150 ease-out group-hover:translate-x-0.5"
          >
            →
          </span>
        </Link>
      )}
    </div>
  );
}
