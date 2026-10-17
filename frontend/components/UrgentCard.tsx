"use client";

import { useEffect, useRef } from "react";

// SAFETY COMPONENT. Render it only when the API returns red_flag === true.
// The wording is fixed on purpose and must never show AI-generated text. It matches
// URGENT_RESPONSE in backend/app/ai/red_flags.py, so keep the two in sync.
// TODO: Person 4 to confirm the PSI helpline number before the demo.

type Props = {
  /** Show the "support person notified" line only when consent was given and the SMS went out. */
  supportAlerted?: boolean;
};

export default function UrgentCard({ supportAlerted = false }: Props) {
  const dialogRef = useRef<HTMLDivElement>(null);

  // Move focus to the card itself, not a call button. Screen readers then read the whole
  // message first, and a stray Enter key can't dial 911.
  useEffect(() => {
    dialogRef.current?.focus();
  }, []);

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-alert">
      {/* min-h-full + items-center centers short content without cutting off tall content. */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div
          ref={dialogRef}
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="urgent-title"
          aria-describedby="urgent-body-1 urgent-body-2"
          tabIndex={-1}
          className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl focus:outline-none"
        >
          <h1 id="urgent-title" className="text-2xl font-bold text-alert">
            Get care now
          </h1>

          <p id="urgent-body-1" className="mt-3 text-lg leading-relaxed text-navy">
            What you just described can be a sign of a serious problem after birth, and it needs
            care right now. Please call 911 or go to the nearest emergency room. Tell them you
            recently gave birth.
          </p>
          <p id="urgent-body-2" className="mt-3 text-lg leading-relaxed text-navy">
            If you are thinking about harming yourself or your baby, you can also call or text 988
            any time. You are not alone, and getting help right now is the right thing to do.
          </p>

          <div className="mt-6 flex flex-col gap-3">
            <a
              href="tel:911"
              className="flex min-h-14 items-center justify-center rounded-xl bg-alert px-4 text-lg font-semibold text-white focus:outline-none focus-visible:ring-4 focus-visible:ring-navy focus-visible:ring-offset-2"
            >
              Call 911
            </a>
            <a
              href="tel:988"
              className="flex min-h-14 items-center justify-center rounded-xl bg-navy px-4 text-lg font-semibold text-white focus:outline-none focus-visible:ring-4 focus-visible:ring-tide focus-visible:ring-offset-2"
            >
              Call or text 988
            </a>
            <a
              href="tel:18009444773"
              className="flex min-h-14 items-center justify-center rounded-xl border-2 border-navy px-4 text-center text-lg font-semibold text-navy focus:outline-none focus-visible:ring-4 focus-visible:ring-tide focus-visible:ring-offset-2"
            >
              Postpartum Support International helpline
            </a>
          </div>

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
