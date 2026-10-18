"use client";

import { useEffect, useRef } from "react";
import type { RedFlagLevel } from "@/lib/types";

// SAFETY COMPONENT. Render it only when the API returns red_flag === true.
// The wording is fixed on purpose and must never show AI-generated text. It matches
// EMERGENCY_RESPONSE and URGENT_RESPONSE in backend/app/ai/red_flags.py, so keep them in sync.
// TODO: Person 4 to confirm the helpline numbers before the demo.

type Props = {
  /** "emergency" (RED: call 911 now) or "urgent" (AMBER: call your provider now). */
  level?: RedFlagLevel;
  /** Show the "support person notified" line only when consent was given and the SMS went out. */
  supportAlerted?: boolean;
  /** Return to the screen behind the card (the help stays one tap away if they need it again). */
  onBack?: () => void;
};

const btn =
  "flex min-h-14 items-center justify-center rounded-xl px-4 text-center text-lg font-semibold focus:outline-none focus-visible:ring-4 focus-visible:ring-offset-2";

export default function UrgentCard({ level = "emergency", supportAlerted = false, onBack }: Props) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const emergency = level === "emergency";

  // Move focus to the card itself, not a call button. Screen readers then read the whole
  // message first, and a stray Enter key can't dial 911.
  useEffect(() => {
    dialogRef.current?.focus();
  }, []);

  // Escape works like the Back button.
  useEffect(() => {
    if (!onBack) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onBack();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onBack]);

  return (
    <div
      className={`fixed inset-0 z-50 overflow-y-auto animate-backdrop-in ${emergency ? "bg-alert" : "bg-chart-amber"}`}
    >
      {/* min-h-full + items-center centers short content without cutting off tall content. */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div
          ref={dialogRef}
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="urgent-title"
          aria-describedby="urgent-body-1 urgent-body-2"
          tabIndex={-1}
          className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl focus:outline-none motion-safe:animate-card-in motion-reduce:animate-fade-in"
        >
          {emergency ? (
            <>
              <h1 id="urgent-title" className="text-2xl font-bold text-alert">
                Get care now
              </h1>
              <p id="urgent-body-1" className="mt-3 text-lg leading-relaxed text-navy">
                What you just described can be a sign of a serious problem after birth, and it needs
                care right now. Please call 911 or go to the nearest emergency room. Tell them you
                recently gave birth.
              </p>
              <p id="urgent-body-2" className="mt-3 text-lg leading-relaxed text-navy">
                If you are thinking about harming yourself or your baby, you can also call or text
                988 any time. You are not alone, and getting help right now is the right thing to do.
              </p>
            </>
          ) : (
            <>
              <h1 id="urgent-title" className="text-2xl font-bold text-navy">
                Call your care team today
              </h1>
              <p id="urgent-body-1" className="mt-3 text-lg leading-relaxed text-navy">
                What you just described is a warning sign after birth that should be checked today.
                Please call your doctor, midwife or clinic right now and tell them you recently gave
                birth. If you can&apos;t reach them, go to the emergency room or call 911.
              </p>
              <p id="urgent-body-2" className="mt-3 text-lg leading-relaxed text-navy">
                If this is about your mood or scary thoughts, you can also call or text the National
                Maternal Mental Health Hotline any time, or 988 if you are thinking about harming
                yourself.
              </p>
            </>
          )}

          <div className="mt-6 flex flex-col gap-3">
            {emergency ? (
              <>
                <a href="tel:911" className={`${btn} bg-alert text-white focus-visible:ring-navy`}>
                  Call 911
                </a>
                <a href="tel:988" className={`${btn} bg-navy text-white focus-visible:ring-tide`}>
                  Call or text 988
                </a>
                <a
                  href="tel:18009444773"
                  className={`${btn} border-2 border-navy text-navy focus-visible:ring-tide`}
                >
                  Postpartum Support International helpline
                </a>
              </>
            ) : (
              <>
                <a
                  href="tel:18338526262"
                  className={`${btn} bg-navy text-white focus-visible:ring-tide`}
                >
                  Maternal Mental Health Hotline (1-833-852-6262)
                </a>
                <a href="tel:988" className={`${btn} border-2 border-navy text-navy focus-visible:ring-tide`}>
                  Call or text 988
                </a>
                <a href="tel:911" className={`${btn} border-2 border-alert text-alert focus-visible:ring-navy`}>
                  Can&apos;t reach your provider? Call 911
                </a>
              </>
            )}
          </div>

          {onBack && (
            <button
              type="button"
              onClick={onBack}
              className="mt-5 inline-flex min-h-12 items-center gap-2 rounded-xl px-3 text-lg font-semibold text-navy underline underline-offset-4 hover:bg-navy/5 focus:outline-none focus-visible:ring-4 focus-visible:ring-tide"
            >
              <span aria-hidden="true">←</span> Go back
            </button>
          )}

          {supportAlerted && (
            <p className="mt-5 text-base text-navy">We have also let your support person know.</p>
          )}
          <p className="mt-5 text-sm text-navy/80">
            Tidewell does not diagnose. It helps you get care quickly.
          </p>
        </div>
      </div>
    </div>
  );
}
