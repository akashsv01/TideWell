"use client";

import { useRef, useState } from "react";
import { readCuffPhoto } from "@/lib/api";
import { focusRing } from "@/lib/ui";

// Take or pick a photo of the blood pressure monitor; Gemini reads the display and fills the
// fields. The parent checks the numbers before saving (nothing is saved here).
export default function CuffPhotoButton({ patientId, onRead }: { patientId: string; onRead: (sys: number, dia: number) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [state, setState] = useState<"idle" | "reading" | "done" | "error">("idle");

  async function onFile(f: File | undefined) {
    if (!f) return;
    setState("reading");
    try {
      const r = await readCuffPhoto(patientId, f);
      if (r.bp_sys && r.bp_dia) {
        onRead(r.bp_sys, r.bp_dia);
        setState("done");
      } else setState("error");
    } catch {
      setState("error");
    }
    if (input.current) input.current.value = "";
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      <input ref={input} type="file" accept="image/*" capture="environment" className="sr-only" id="cuff-photo" onChange={(e) => onFile(e.target.files?.[0])} />
      <label
        htmlFor="cuff-photo"
        className={`inline-flex min-h-12 cursor-pointer items-center gap-2 rounded-full border-2 border-navy bg-white px-5 text-base font-semibold transition-[background-color,transform] duration-150 ease-out hover:bg-sand motion-safe:active:scale-[0.97] ${focusRing}`}
      >
        <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden="true">
          <path d="M4 8h3l2-3h6l2 3h3v11H4z" /><circle cx="12" cy="13" r="3.5" />
        </svg>
        {state === "reading" ? "Reading the photo…" : "Read from a cuff photo"}
      </label>
      <span role="status" className="text-base">
        {state === "done" && "Filled in from your photo. Check the numbers, then save."}
        {state === "error" && "Couldn't read that photo. Try again in good light, or type the numbers."}
      </span>
    </div>
  );
}
