"use client";

import { useEffect } from "react";
import { isNightNow, useNightPref } from "@/lib/night";
import { DAY_PAGE, NIGHT_PAGE } from "@/lib/nightBoot";

// Applies night mode to <html>; re-checks every minute so "auto" switches at 10 pm and 6 am.
export default function NightMode() {
  const pref = useNightPref();

  useEffect(() => {
    const apply = () => {
      const on = isNightNow(pref);
      document.documentElement.toggleAttribute("data-night", on);
      document.querySelector('meta[name="theme-color"]')?.setAttribute("content", on ? NIGHT_PAGE : DAY_PAGE);
    };
    apply();
    const id = setInterval(apply, 60_000);
    return () => clearInterval(id);
  }, [pref]);

  return null;
}
