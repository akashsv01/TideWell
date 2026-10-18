"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useSyncExternalStore } from "react";
import CircleSettings from "@/components/CircleSettings";
import NightModeSetting from "@/components/NightModeSetting";
import ProfileEditor from "@/components/ProfileEditor";
import { deleteMyData, logout, switchToDemo } from "@/lib/api";
import {
  getSpokenReplies,
  setSpokenReplies,
  spokenRepliesServerValue,
  subscribeSpokenReplies,
} from "@/lib/prefs";
import { clearSession, useSession } from "@/lib/session";
import { btnOutline, btnPrimary, focusRing } from "@/lib/ui";

type DeleteState = "idle" | "confirm" | "deleting" | "error";

export default function SettingsPanel() {
  const router = useRouter();
  const { session } = useSession();
  const spoken = useSyncExternalStore(subscribeSpokenReplies, getSpokenReplies, spokenRepliesServerValue);
  const [del, setDel] = useState<DeleteState>("idle");
  const demo = session?.kind === "demo";
  const patientId = session?.patientId ?? null;

  async function signOut() {
    await logout();
    clearSession();
    router.push("/");
  }

  async function confirmDelete() {
    if (!patientId) return;
    setDel("deleting");
    try {
      await deleteMyData(patientId); // also deletes the account and ends every session
      clearSession();
      router.push("/");
    } catch {
      setDel("error");
    }
  }

  return (
    <div className="space-y-14">
      <h1 className="font-display text-4xl leading-tight">Settings</h1>

      <section aria-labelledby="details-title" className="motion-safe:animate-section-in">
        <h2 id="details-title" className="font-display text-2xl">
          Your details
        </h2>
        <div className="mt-3">{patientId && <ProfileEditor patientId={patientId} demo={demo} />}</div>
      </section>

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
            className={`relative h-9 w-16 shrink-0 rounded-full transition-colors duration-150 ${spoken ? "bg-tide-deep" : "bg-navy/40"} ${focusRing}`}
          >
            <span
              aria-hidden="true"
              className={`absolute left-1 top-1 size-7 rounded-full bg-white shadow transition-transform duration-150 ease-out ${spoken ? "translate-x-7" : ""}`}
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
            <a href="tel:911" className={`rounded font-semibold underline underline-offset-4 ${focusRing}`}>Call 911</a> for an emergency.
          </li>
          <li>
            <a href="tel:988" className={`rounded font-semibold underline underline-offset-4 ${focusRing}`}>Call or text 988</a> if you are thinking of harming yourself or your baby.
          </li>
          <li>
            <a href="tel:18338526262" className={`rounded font-semibold underline underline-offset-4 ${focusRing}`}>1-833-852-6262</a>, the National Maternal Mental Health Hotline, any time.
          </li>
        </ul>
      </section>

      <NightModeSetting />

      {!demo && patientId && <CircleSettings patientId={patientId} />}

      <section aria-labelledby="account-title">
        <h2 id="account-title" className="font-display text-2xl">
          Account
        </h2>
        {demo ? (
          <>
            <p className="mt-2 max-w-[46ch] text-lg leading-relaxed">
              You are looking at Maya, our demo parent. Nothing you do here is saved to an account of yours.
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Link href="/register" onClick={() => clearSession()} className={btnPrimary}>
                Create my own account
              </Link>
              <button type="button" onClick={() => { clearSession(); router.push("/"); }} className={btnOutline}>
                Exit demo
              </button>
            </div>
          </>
        ) : (
          <>
            <p className="mt-2 text-lg">
              Signed in as <strong>{session?.kind === "user" ? session.username : ""}</strong>.
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <button type="button" onClick={signOut} className={btnOutline}>
                Log out
              </button>
              <button
                type="button"
                onClick={async () => {
                  await switchToDemo();
                  router.push("/home");
                }}
                className={btnOutline}
              >
                Try the demo
              </button>
            </div>
          </>
        )}
      </section>

      {!demo && (
        <section aria-labelledby="data-title">
          <h2 id="data-title" className="font-display text-2xl">
            Your data
          </h2>
          <p className="mt-2 max-w-[46ch] text-lg leading-relaxed">
            Delete your account, check-ins, trends and answers. This cannot be undone.
          </p>
          <div className="mt-4" aria-live="polite">
            {del === "idle" && (
              <button type="button" onClick={() => setDel("confirm")} className={btnOutline}>
                Delete my account and data
              </button>
            )}
            {(del === "confirm" || del === "deleting") && (
              <div className="rounded-3xl bg-sand/70 p-5 motion-safe:animate-reply-in">
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
      )}
    </div>
  );
}
