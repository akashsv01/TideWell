"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { switchToDemo } from "@/lib/api";
import { startDemo, useSession } from "@/lib/session";
import { btnMoon, focusRing } from "@/lib/ui";

// Welcome-page buttons: create an account, sign in, or look around as the demo parent.
export default function WelcomeActions({ tone = "light" }: { tone?: "light" | "dark" }) {
  const router = useRouter();
  const { session } = useSession();
  const link = `inline-flex min-h-12 items-center whitespace-nowrap rounded-md text-base font-semibold sm:text-lg underline underline-offset-4 transition-transform duration-150 ease-out motion-safe:active:scale-[0.97] ${
    tone === "dark" ? "text-white focus:outline-none focus-visible:ring-4 focus-visible:ring-white" : focusRing
  }`;

  async function tryDemo() {
    if (session?.kind === "user") await switchToDemo();
    else startDemo();
    router.push("/home");
  }

  return (
    // The primary action, then the two quiet options together on one line underneath it, starting at
    // the button's left edge. On phones the button takes the full width and the options centre under it.
    <div className="flex flex-col items-stretch gap-3 sm:items-start">
      {session?.kind === "user" ? (
        <Link href="/home" className={`${btnMoon} w-full sm:w-auto`}>
          Continue to check-in
        </Link>
      ) : (
        <Link href="/register" className={`${btnMoon} w-full sm:w-auto`}>
          Start today
        </Link>
      )}
      <div className="flex flex-wrap items-center justify-center gap-x-6 sm:justify-start">
        {!session && (
          <Link href="/login" className={link}>
            I have an account
          </Link>
        )}
        {session?.kind !== "demo" && (
          <button type="button" onClick={tryDemo} className={link}>
            Try the demo
          </button>
        )}
      </div>
    </div>
  );
}
