"use client";

import { useSyncExternalStore } from "react";

// Night mode for 3 a.m. feeds: a dark, low-glare theme. "auto" turns it on from 10 pm to 6 am.
// Applied as <html data-night>, which swaps the colour tokens in globals.css.
export type NightPref = "auto" | "on" | "off";

const KEY = "tidewell.night";
const listeners = new Set<() => void>();
let pref: NightPref | null = null;

export function getNightPref(): NightPref {
  if (pref === null) {
    try {
      const v = window.localStorage.getItem(KEY);
      pref = v === "on" || v === "off" ? v : "auto";
    } catch {
      pref = "auto";
    }
  }
  return pref;
}

export function setNightPref(p: NightPref) {
  pref = p;
  try {
    window.localStorage.setItem(KEY, p);
  } catch {
    /* memory only */
  }
  listeners.forEach((l) => l());
}

export function isNightNow(p: NightPref, d = new Date()): boolean {
  if (p !== "auto") return p === "on";
  const h = d.getHours();
  return h >= 22 || h < 6;
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
}

export function useNightPref(): NightPref {
  return useSyncExternalStore(subscribe, getNightPref, () => "auto");
}
