"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { logout } from "@/lib/api";
import { clearSession, useSession } from "@/lib/session";
import { focusRing } from "@/lib/ui";

// Top-right of the app header: who you are, and a quiet way out. Leaving is never styled as loudly
// as the check-in.
const quiet = `inline-flex min-h-11 items-center whitespace-nowrap rounded-md px-2 text-base font-semibold text-navy/80 underline decoration-navy/30 underline-offset-4 transition-[color,text-decoration-color] duration-150 ease-out hover:text-navy hover:decoration-navy ${focusRing}`;

export default function AccountMenu() {
  const router = useRouter();
  const { session } = useSession();

  if (!session) {
    return (
      <Link href="/login" className={quiet}>
        Sign in
      </Link>
    );
  }

  async function signOut() {
    await logout(); // revokes the token on the server; never throws
    clearSession();
    router.push("/");
  }

  if (session.kind === "demo") {
    return (
      <div className="flex items-center gap-2 motion-safe:animate-fade-in">
        <span className="hidden text-sm text-navy/75 sm:inline">
          Demo as <span className="font-semibold text-navy">Maya</span>
        </span>
        <button
          type="button"
          onClick={() => {
            clearSession();
            router.push("/");
          }}
          className={quiet}
        >
          Exit demo
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 motion-safe:animate-fade-in">
      <span className="hidden max-w-[14ch] truncate text-base text-navy/75 sm:inline" title={session.username}>
        {session.username}
      </span>
      <button type="button" onClick={signOut} className={quiet}>
        Log out
      </button>
    </div>
  );
}
