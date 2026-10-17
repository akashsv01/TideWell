"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { AUTH_ENABLED } from "@/lib/auth";
import { chooseDemoAccount, usePatientId } from "@/lib/identity";
import { btnPrimary, focusRing } from "@/lib/ui";

// Welcome screen buttons. With sign-in enabled, new people create an account first and then
// answer the onboarding questions; without it, onboarding alone creates their patient record.
export default function WelcomeActions() {
  const router = useRouter();
  const { patientId } = usePatientId();
  const link = `rounded-md py-2 text-lg font-semibold underline underline-offset-4 ${focusRing}`;

  function tryDemo() {
    chooseDemoAccount();
    router.push("/home");
  }

  return (
    <div className="mt-8 flex flex-wrap items-center gap-x-8 gap-y-4">
      {patientId ? (
        <Link href="/home" className={btnPrimary}>
          Continue to check-in
        </Link>
      ) : (
        <Link href={AUTH_ENABLED ? "/sign-up" : "/onboarding"} className={btnPrimary}>
          Get started
        </Link>
      )}
      {AUTH_ENABLED && !patientId && (
        <Link href="/sign-in" className={link}>
          I already have an account
        </Link>
      )}
      <button type="button" onClick={tryDemo} className={link}>
        Try the demo
      </button>
    </div>
  );
}
