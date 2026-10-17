"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { startDemo, useSession } from "@/lib/session";
import { btnPrimary, focusRing } from "@/lib/ui";

// Welcome-page buttons: create an account, sign in, or look around as the demo parent.
export default function WelcomeActions({ tone = "light" }: { tone?: "light" | "dark" }) {
  const router = useRouter();
  const { session } = useSession();
  const link = `rounded-md py-2 text-lg font-semibold underline underline-offset-4 ${
    tone === "dark" ? "text-white focus:outline-none focus-visible:ring-4 focus-visible:ring-white" : focusRing
  }`;

  function tryDemo() {
    startDemo();
    router.push("/home");
  }

  return (
    <div className="flex flex-wrap items-center gap-x-8 gap-y-4">
      {session?.kind === "user" ? (
        <Link href="/home" className={btnPrimary}>
          Continue to check-in
        </Link>
      ) : (
        <Link href="/register" className={btnPrimary}>
          Get started
        </Link>
      )}
      {!session && (
        <Link href="/login" className={link}>
          I have an account
        </Link>
      )}
      {session?.kind !== "user" && (
        <button type="button" onClick={tryDemo} className={link}>
          Try the demo
        </button>
      )}
    </div>
  );
}
