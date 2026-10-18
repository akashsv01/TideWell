"use client";

import { setNightPref, useNightPref, type NightPref } from "@/lib/night";
import { focusRing } from "@/lib/ui";

const OPTIONS: { value: NightPref; label: string }[] = [
  { value: "auto", label: "Automatic (10 pm to 6 am)" },
  { value: "on", label: "Always on" },
  { value: "off", label: "Off" },
];

export default function NightModeSetting() {
  const pref = useNightPref();
  return (
    <section aria-labelledby="night-title">
      <h2 id="night-title" className="font-display text-2xl font-semibold">Night mode</h2>
      <p className="mt-2 max-w-[46ch] text-lg leading-relaxed">A dark, low-glare screen for night feeds, so checking in doesn&apos;t wake you up.</p>
      <div className="mt-4 flex flex-wrap gap-2" role="radiogroup" aria-labelledby="night-title">
        {OPTIONS.map((o) => (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={pref === o.value}
            onClick={() => setNightPref(o.value)}
            className={`min-h-12 rounded-full border-2 px-5 text-base font-semibold transition-[background-color,color,transform] duration-150 ease-out motion-safe:active:scale-[0.97] ${pref === o.value ? "border-tide-deep bg-tide-deep text-white" : "border-navy/30 bg-white"} ${focusRing}`}
          >
            {o.label}
          </button>
        ))}
      </div>
    </section>
  );
}
