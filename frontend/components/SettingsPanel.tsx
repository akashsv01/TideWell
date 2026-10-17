"use client";

import { useState, useSyncExternalStore } from "react";
import { deleteMyData } from "@/lib/api";
import { DEMO_PATIENT_ID } from "@/lib/config";
import {
  getSpokenReplies,
  setSpokenReplies,
  spokenRepliesServerValue,
  subscribeSpokenReplies,
} from "@/lib/prefs";
import { btnOutline, focusRing } from "@/lib/ui";

type DeleteState = "idle" | "confirm" | "deleting" | "done" | "error";

export default function SettingsPanel() {
  const spoken = useSyncExternalStore(
    subscribeSpokenReplies,
    getSpokenReplies,
    spokenRepliesServerValue
  );
  const [del, setDel] = useState<DeleteState>("idle");

  async function confirmDelete() {
    setDel("deleting");
    try {
      await deleteMyData(DEMO_PATIENT_ID);
      setDel("done");
    } catch {
      setDel("error");
    }
  }

  return (
    <div className="space-y-12">
      <h1 className="font-display text-4xl leading-tight">Settings</h1>

      <section aria-labelledby="voice-title">
        <h2 id="voice-title" className="font-display text-2xl">
          Voice
        </h2>
        <div className="mt-3 flex items-center justify-between gap-4">
          <div>
            <p id="spoken-label" className="text-lg font-semibold">
              Spoken replies
            </p>
            <p id="spoken-hint" className="text-base text-navy/80">
              Tidewell reads each reply out loud. You can always read it instead.
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={spoken}
            aria-labelledby="spoken-label"
            aria-describedby="spoken-hint"
            onClick={() => setSpokenReplies(!spoken)}
            className={`relative h-9 w-16 shrink-0 rounded-full transition-colors ${spoken ? "bg-tide-deep" : "bg-navy/40"} ${focusRing}`}
          >
            <span
              aria-hidden="true"
              className={`absolute left-1 top-1 size-7 rounded-full bg-white shadow transition-transform ${spoken ? "translate-x-7" : ""}`}
            />
          </button>
        </div>
      </section>

      <section aria-labelledby="help-title">
        <h2 id="help-title" className="font-display text-2xl">
          Get help now
        </h2>
        <p className="mt-2 text-lg leading-relaxed">
          Tidewell does not diagnose. If you think you need care right now, do not wait for an answer here.
        </p>
        <ul className="mt-4 space-y-2 text-lg">
          <li>
            <a href="tel:911" className={`rounded font-semibold underline underline-offset-4 ${focusRing}`}>
              Call 911
            </a>{" "}
            for an emergency.
          </li>
          <li>
            <a href="tel:988" className={`rounded font-semibold underline underline-offset-4 ${focusRing}`}>
              Call or text 988
            </a>{" "}
            if you are thinking of harming yourself or your baby.
          </li>
        </ul>
      </section>

      <section aria-labelledby="data-title">
        <h2 id="data-title" className="font-display text-2xl">
          Your data
        </h2>
        <p className="mt-2 max-w-[46ch] text-lg leading-relaxed">
          You can delete your check-ins, trends and answers at any time. This cannot be undone.
        </p>

        <div className="mt-4" aria-live="polite">
          {del === "idle" && (
            <button type="button" onClick={() => setDel("confirm")} className={btnOutline}>
              Delete my data
            </button>
          )}
          {(del === "confirm" || del === "deleting") && (
            <div className="rounded-3xl bg-sand/70 p-5">
              <p className="text-lg font-semibold">Delete everything Tidewell has about you?</p>
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => del === "confirm" && confirmDelete()}
                  aria-disabled={del === "deleting"}
                  className={`inline-flex min-h-12 items-center rounded-full bg-alert px-6 font-semibold text-white aria-disabled:opacity-60 ${focusRing}`}
                >
                  {del === "deleting" ? "Deleting" : "Yes, delete it"}
                </button>
                <button
                  type="button"
                  onClick={() => del === "confirm" && setDel("idle")}
                  aria-disabled={del === "deleting"}
                  className={`inline-flex min-h-12 items-center rounded-full border-2 border-navy px-6 font-semibold aria-disabled:opacity-60 ${focusRing}`}
                >
                  Keep my data
                </button>
              </div>
            </div>
          )}
          {del === "done" && (
            <p className="rounded-3xl bg-sand/70 p-5 text-lg" role="status">
              Your data has been deleted.
            </p>
          )}
          {del === "error" && (
            <div role="alert" className="rounded-3xl bg-white p-5 text-lg text-alert ring-2 ring-alert/30">
              <p>We couldn&apos;t delete your data. Please try again.</p>
              <button type="button" onClick={() => setDel("confirm")} className={`mt-3 ${btnOutline}`}>
                Try again
              </button>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
