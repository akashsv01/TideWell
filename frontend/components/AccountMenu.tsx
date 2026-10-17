"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { logout } from "@/lib/api";
import { clearSession, useSession } from "@/lib/session";
import { focusRing } from "@/lib/ui";

// Top-right of the app header: who you are, and the way out.
export default function AccountMenu() {
  const router = useRouter();
  const { session } = useSession();
  const pill = `inline-flex min-h-11 items-center rounded-full border-2 border-navy px-4 text-base font-semibold transition-colors duration-150 hover:bg-navy hover:text-white ${focusRing}`;

  if (!session) {
    return (
      <Link href="/login" className={pill}>
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
      <div className="flex items-center gap-3 motion-safe:animate-fade-in">
        <span className="rounded-full bg-sand px-3 py-1 text-sm font-semibold">Demo: Maya</span>
        <button
          type="button"
          onClick={() => {
            clearSession();
            router.push("/");
          }}
          className={pill}
        >
          Exit demo
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3 motion-safe:animate-fade-in">
      <span className="hidden max-w-[12ch] truncate text-base font-semibold sm:inline" title={session.username}>
        {session.username}
      </span>
      <button type="button" onClick={signOut} className={pill}>
        Log out
      </button>
    </div>
  );
}
