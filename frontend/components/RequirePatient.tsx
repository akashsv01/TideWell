"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getMe } from "@/lib/api";
import { AUTH_ENABLED } from "@/lib/auth";
import { chooseDemoAccount, setPatientId, useClerkUserId, usePatientId } from "@/lib/identity";
import { btnOutline, btnPrimary, focusRing } from "@/lib/ui";

// Guards the signed-in screens. Shows them once we know whose data to load:
//   1. a patient id saved on this device (from onboarding, a past sign-in, or the demo), or
//   2. the signed-in login's patient, looked up with GET /me (404 -> onboarding).
// Otherwise it offers: set up Tidewell, sign in, or try the demo as Maya.
export default function RequirePatient({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { patientId, ready } = usePatientId();
  const { clerkUserId, loaded } = useClerkUserId();
  const [settled, setSettled] = useState<string | null>(null); // login we already looked up

  const lookingUp = AUTH_ENABLED && !!clerkUserId && !patientId && settled !== clerkUserId;

  useEffect(() => {
    if (!lookingUp || !clerkUserId) return;
    let cancelled = false;
    getMe(clerkUserId).then(
      (me) => {
        if (cancelled) return;
        if (me) setPatientId(me.patient_id);
        else router.replace("/onboarding");
        setSettled(clerkUserId);
      },
      () => {
        if (!cancelled) setSettled(clerkUserId);
      }
    );
    return () => {
      cancelled = true;
    };
  }, [lookingUp, clerkUserId, router]);

  if (!ready || (AUTH_ENABLED && !loaded) || lookingUp) {
    return (
      <p role="status" className="py-24 text-center text-xl motion-safe:animate-fade-in">
        Opening Tidewell…
      </p>
    );
  }
  if (patientId) return <>{children}</>;

  return (
    <section
      aria-labelledby="start-title"
      className="mx-auto mt-6 w-full max-w-md rounded-3xl bg-sand/70 p-7 motion-safe:animate-step-in"
    >
      <h1 id="start-title" className="font-display text-3xl leading-tight">
        Let&apos;s get you set up
      </h1>
      <p className="mt-3 text-lg leading-relaxed">
        Answer a few questions so Tidewell can look out for you, or look around with Maya, our demo
        parent on day 18 after a C-section.
      </p>
      <div className="mt-6 flex flex-col gap-3">
        <Link href={AUTH_ENABLED && !clerkUserId ? "/sign-up" : "/onboarding"} className={btnPrimary}>
          Set up Tidewell
        </Link>
        <button type="button" onClick={chooseDemoAccount} className={btnOutline}>
          Try the demo as Maya
        </button>
        {AUTH_ENABLED && !clerkUserId && (
          <Link
            href="/sign-in"
            className={`self-center rounded-md py-2 text-lg font-semibold underline underline-offset-4 ${focusRing}`}
          >
            I already have an account
          </Link>
        )}
      </div>
    </section>
  );
}
