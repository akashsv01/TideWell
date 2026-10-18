"use client";

import { MoonIcon, SunIcon } from "@/components/icons";
import { setNightPref, useNightShown } from "@/lib/night";
import { focusRing } from "@/lib/ui";

// Day/night switch for the header. A tap picks day or night explicitly; Settings > Night mode
// can hand it back to "Automatic (10 pm to 6 am)". Colours crossfade briefly (globals.css).
export default function ThemeToggle() {
  const night = useNightShown();

  function toggle() {
    const html = document.documentElement;
    html.setAttribute("data-theme-fade", "");
    setNightPref(night ? "off" : "on");
    window.setTimeout(() => html.removeAttribute("data-theme-fade"), 350);
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={night}
      aria-label="Night mode"
      title={night ? "Switch to day mode" : "Switch to night mode"}
      className={`relative grid size-11 place-items-center rounded-full border-2 border-navy/20 text-navy transition-[background-color,border-color,transform] duration-150 ease-out hover:border-navy/50 motion-safe:active:scale-[0.94] ${focusRing}`}
    >
      <SunIcon
        className={`absolute size-5 transition-[opacity,transform] duration-200 ease-out ${night ? "rotate-45 scale-75 opacity-0" : "opacity-100"}`}
      />
      <MoonIcon
        className={`absolute size-5 transition-[opacity,transform] duration-200 ease-out ${night ? "opacity-100" : "-rotate-45 scale-75 opacity-0"}`}
      />
    </button>
  );
}
