"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { logout } from "@/lib/api";
import { clearSession, useSession } from "@/lib/session";
import { focusRing } from "@/lib/ui";

const pill =
  `inline-flex min-h-11 items-center rounded-full border-2 border-navy px-4 text-base font-semibold transition-[color,background-color,border-color,transform] duration-150 ease-out hover:bg-navy hover:text-white motion-safe:active:scale-[0.97] ${focusRing}`;

const solid =
  `inline-flex min-h-11 items-center rounded-full bg-tide-deep px-5 text-base font-semibold text-white transition-[color,background-color,transform] duration-150 ease-out hover:bg-navy motion-safe:active:scale-[0.97] ${focusRing}`;

/** Landing-page header: account-aware Sign in / Open Tidewell / Demo continue. */
export default function LandingNav() {
  const router = useRouter();
  const { session, ready } = useSession();

  async function signOut() {
    await logout();
    clearSession();
    router.refresh();
  }

  return (
    <header className="mx-auto flex h-20 w-full max-w-6xl items-center justify-between px-5 sm:px-8">
      <Link href="/" className={`rounded-md font-display text-2xl text-tide-deep ${focusRing}`}>
        Tidewell
      </Link>
      <nav aria-label="Account" className="flex items-center gap-3">
        {!ready ? (
          <span className="min-h-11 w-28" aria-hidden="true" />
        ) : session?.kind === "user" ? (
          <>
            <span className="hidden max-w-[14ch] truncate text-base font-semibold sm:inline" title={session.username}>
              {session.username}
            </span>
            <Link href="/home" className={solid}>
              Open Tidewell
            </Link>
            <button type="button" onClick={signOut} className={pill}>
              Log out
            </button>
          </>
        ) : session?.kind === "demo" ? (
          <>
            <span className="rounded-full bg-sand px-3 py-1 text-sm font-semibold">Demo: Maya</span>
            <Link href="/home" className={solid}>
              Continue
            </Link>
          </>
        ) : (
          <>
            <Link href="/login" className={`hidden rounded-full px-4 py-2 text-base font-semibold sm:inline-block ${focusRing}`}>
              Sign in
            </Link>
            <Link href="/register" className={solid}>
              Get started
            </Link>
          </>
        )}
      </nav>
    </header>
  );
}
