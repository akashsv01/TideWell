"use client";

import { useEffect, useRef } from "react";
import type { MutableRefObject } from "react";
import { MicIcon, StopIcon } from "@/components/icons";
import Waves, { type WaveLayer } from "@/components/Waves";
import { focusRing } from "@/lib/ui";

// The check-in button. A round basin of water: it breathes while idle, rises and ripples with
// your voice while recording, and runs faster while Tidewell thinks. With reduced motion it is a
// still picture and the water stays at a fixed level.

export type OrbState = "idle" | "recording" | "busy";

const water: WaveLayer[] = [
  { color: "#13828a", amp: 7, cycles: 2, top: 8, seconds: 9, opacity: 0.85 },
  { color: "#0e6a70", amp: 6, cycles: 3, top: 16, seconds: 7, reverse: true },
];

const REST_LEVEL = 0.42;
const BUSY_LEVEL = 0.62;

const clock = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

type Props = {
  state: OrbState;
  seconds: number;
  levelRef: MutableRefObject<number>;
  onClick: () => void;
};

export default function Orb({ state, seconds, levelRef, onClick }: Props) {
  const waterRef = useRef<HTMLSpanElement>(null);
  const recording = state === "recording";

  // Water height follows the voice while recording. Written straight to the element each frame.
  useEffect(() => {
    const el = waterRef.current;
    if (!el) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!recording || reduce) {
      el.style.setProperty("--level", String(state === "busy" ? BUSY_LEVEL : REST_LEVEL));
      return;
    }
    let raf = 0;
    const tick = () => {
      el.style.setProperty("--level", String(0.45 + Math.min(1, levelRef.current) * 0.4));
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [recording, state, levelRef]);

  const label = recording ? "Tap to finish" : state === "busy" ? "Thinking" : "Tap to talk";

  return (
    <button
      type="button"
      onClick={onClick}
      aria-disabled={state === "busy"}
      className={`group relative flex flex-col items-center rounded-[2.5rem] px-6 pb-3 pt-4 ${focusRing}`}
    >
      <span
        className={`relative grid size-60 place-items-center ${state === "idle" ? "motion-safe:animate-breathe" : ""}`}
      >
        {recording && (
          <>
            <span className="absolute size-48 rounded-full border-2 border-tide motion-safe:animate-ripple" />
            <span
              className="absolute size-48 rounded-full border-2 border-tide motion-safe:animate-ripple"
              style={{ animationDelay: "1.3s" }}
            />
          </>
        )}
        <span
          data-state={state}
          className="orb relative size-48 overflow-hidden rounded-full bg-navy shadow-[0_18px_40px_-12px_rgba(11,37,69,0.55)] ring-4 ring-white motion-safe:group-active:scale-95 motion-safe:transition-transform"
        >
          <span
            ref={waterRef}
            className="absolute inset-0 transition-transform duration-300 ease-out"
            style={{ transform: "translateY(calc((1 - var(--level, 0.42)) * 100%))" }}
          >
            <Waves layers={water} className="absolute inset-0" />
          </span>
          <span className="absolute inset-0 grid place-items-center text-white">
            {recording ? <StopIcon className="size-12" /> : <MicIcon className="size-14" />}
          </span>
        </span>
      </span>
      <span className="mt-1 text-2xl font-semibold text-navy">{label}</span>
      <span aria-hidden="true" className="h-7 text-xl font-semibold tabular-nums text-tide-deep">
        {recording ? clock(seconds) : ""}
      </span>
    </button>
  );
}
