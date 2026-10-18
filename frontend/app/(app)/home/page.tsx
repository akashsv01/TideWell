import type { Metadata } from "next";
import Link from "next/link";
import CheckinPanel from "@/components/CheckinPanel";
import TodayCard from "@/components/TodayCard";
import { focusRing } from "@/lib/ui";

export const metadata: Metadata = { title: "Check in" };

export default function HomePage() {
  return (
    <div className="mx-auto flex w-full max-w-md flex-1 flex-col items-center">
      <h1 className="mt-2 text-center font-display text-4xl font-semibold leading-tight">How are you today?</h1>
      <div className="mt-4 flex w-full flex-col">
        <CheckinPanel />
      </div>
      <div className="mt-10 w-full">
        <TodayCard />
      </div>
      <p className="mt-8 text-center text-lg">
        <Link
          href="/dashboard#log"
          className={`rounded-md font-semibold underline underline-offset-4 transition-transform duration-150 ease-out motion-safe:active:scale-[0.97] ${focusRing}`}
        >
          Or log today&apos;s numbers
        </Link>
      </p>
      <p className="mt-10 text-center text-base text-navy/80">
        Tidewell does not diagnose. If this is an emergency, call 911.
      </p>
    </div>
  );
}
