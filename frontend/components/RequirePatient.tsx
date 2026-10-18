"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getAccount } from "@/lib/api";
import { setOwnPatient, startDemo, useSession } from "@/lib/session";
import { btnOutline, btnPrimary, focusRing } from "@/lib/ui";

// Guards the app screens.
//   demo session              -> show the screen (Maya)
//   signed in, onboarded      -> check the login is still valid, then show the screen
//   signed in, not onboarded  -> /onboarding
//   nobody                    -> sign in / create account / try the demo
// The page itself is always rendered (just hidden) so Next.js can still pre-render and validate
// the route segment; dropping it trips Next 16's instant-navigation check.
export default function RequirePatient({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { session, ready } = useSession();
  const [verified, setVerified] = useState<string | null>(null); // token we already checked
  const token = session?.kind === "user" ? session.token : null;

  // Once per login per page load: confirm the token still works and pick up the patient id
  // (it may have been created on another device). A 401 clears the session inside the api client.
  useEffect(() => {
    if (!token || verified === token) return;
    let cancelled = false;
    getAccount().then(
      (acct) => {
        if (cancelled) return;
        setOwnPatient(acct.patient_id);
        setVerified(token);
        if (!acct.patient_id) router.replace("/onboarding");
      },
      () => {
        if (!cancelled) setVerified(token);
      }
    );
    return () => {
      cancelled = true;
    };
  }, [token, verified, router]);

  const checking = !ready || (!!token && verified !== token);
  const patientId = session?.patientId ?? null;
  const show = !checking && !!patientId;

  return (
    <>
      {checking ? (
        <p role="status" className="py-24 text-center text-xl motion-safe:animate-fade-in">
          Opening Tidewell…
        </p>
      ) : (
        !session && <StartChooser />
      )}
      <div key={session?.patientId ?? "none"} hidden={!show} className="flex flex-1 flex-col">
        {children}
      </div>
    </>
  );
}

function StartChooser() {
  return (
    <section
      aria-labelledby="start-title"
      className="mx-auto mt-6 w-full max-w-md rounded-3xl bg-sand/70 p-7 motion-safe:animate-reply-in"
    >
      <h1 id="start-title" className="font-display text-3xl leading-tight">
        Let&apos;s get you set up
      </h1>
      <p className="mt-3 text-lg leading-relaxed">
        Create an account so Tidewell can look out for you, or look around with Maya, our demo parent
        on day 18 after a C-section.
      </p>
      <div className="mt-6 flex flex-col gap-3">
        <Link href="/register" className={btnPrimary}>
          Create an account
        </Link>
        <button type="button" onClick={startDemo} className={btnOutline}>
          Try the demo as Maya
        </button>
        <Link
          href="/login"
          className={`self-center rounded-md py-2 text-lg font-semibold underline underline-offset-4 ${focusRing}`}
        >
          I already have an account
        </Link>
      </div>
    </section>
  );
}

