"use client";

import { useEffect, useRef } from "react";
import { focusRingLight } from "@/lib/ui";

// Full-screen video room. The room is a Daily page shown in an iframe; the camera and microphone
// permissions are handed to it with the `allow` attribute. Leaving closes the overlay (the call
// ends for this person only) and puts focus back where it was.
export default function VideoVisit({ url, who, onLeave }: { url: string; who: string; onLeave: () => void }) {
  const leaveRef = useRef<HTMLButtonElement>(null);
  const leaveCb = useRef(onLeave);
  useEffect(() => {
    leaveCb.current = onLeave;
  });

  useEffect(() => {
    const before = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    leaveRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") leaveCb.current();
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = overflow;
      before?.focus?.();
    };
  }, []);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Video visit with ${who}`}
      className="fixed inset-0 z-50 flex flex-col bg-navy text-white motion-safe:animate-backdrop-in"
    >
      <div className="flex min-h-16 items-center justify-between gap-4 px-5">
        <p className="font-display text-xl">Visit with {who}</p>
        <button
          ref={leaveRef}
          type="button"
          onClick={onLeave}
          className={`inline-flex min-h-12 items-center rounded-full bg-white px-6 text-lg font-semibold text-navy hover:bg-foam ${focusRingLight}`}
        >
          Leave visit
        </button>
      </div>
      <iframe
        src={url}
        title={`Video visit with ${who}`}
        allow="camera; microphone; fullscreen; display-capture; autoplay"
        className="w-full flex-1 border-0 bg-black"
      />
    </div>
  );
}
