import Link from "next/link";
import AccountMenu from "@/components/AccountMenu";
import BottomNav from "@/components/BottomNav";
import RequirePatient from "@/components/RequirePatient";
import { focusRing } from "@/lib/ui";

// Shared frame for the signed-in screens: wordmark on top, tab bar at the bottom.
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-3xl flex-col px-5">
      <header className="flex h-16 items-center justify-between">
        <Link
          href="/home"
          className={`rounded-md font-display text-2xl text-tide-deep ${focusRing}`}
        >
          Tidewell
        </Link>
        <AccountMenu />
      </header>
      <main id="main" className="flex flex-1 flex-col pb-32">
        <RequirePatient>{children}</RequirePatient>
      </main>
      <BottomNav />
    </div>
  );
}
