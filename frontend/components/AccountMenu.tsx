"use client";

import { UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { AUTH_ENABLED } from "@/lib/auth";
import { isDemo, useClerkUserId, usePatientId } from "@/lib/identity";
import { focusRing } from "@/lib/ui";

// Top-right of the app header: a "Demo" badge when viewing Maya, and the Clerk account button
// (or a sign-in link) when sign-in is enabled.
export default function AccountMenu() {
  const { patientId } = usePatientId();
  const { clerkUserId, loaded } = useClerkUserId();

  return (
    <div className="flex items-center gap-3">
      {isDemo(patientId) && (
        <span className="rounded-full bg-sand px-3 py-1 text-sm font-semibold motion-safe:animate-fade-in">
          Demo: Maya
        </span>
      )}
      {AUTH_ENABLED &&
        loaded &&
        (clerkUserId ? (
          <UserButton />
        ) : (
          <Link
            href="/sign-in"
            className={`rounded-md text-base font-semibold underline underline-offset-4 ${focusRing}`}
          >
            Sign in
          </Link>
        ))}
    </div>
  );
}
