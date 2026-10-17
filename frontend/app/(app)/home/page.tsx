import type { Metadata } from "next";
import CheckinPanel from "@/components/CheckinPanel";

export const metadata: Metadata = { title: "Check in" };

export default function HomePage() {
  return (
    <div className="mx-auto flex w-full max-w-md flex-1 flex-col items-center">
      <h1 className="mt-2 text-center font-display text-4xl leading-tight">How are you today?</h1>
      <div className="mt-6 flex w-full flex-1 flex-col">
        <CheckinPanel />
      </div>
      <p className="mt-10 text-center text-base text-navy/80">
        Tidewell does not diagnose. If this is an emergency, call 911.
      </p>
    </div>
  );
}
