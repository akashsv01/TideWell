"use client";

// Small preference store for "Spoken replies". Backed by localStorage when it is available,
// and by memory when it is not (private windows, blocked storage).

const KEY = "tidewell.spokenReplies";
const listeners = new Set<() => void>();
let value: boolean | null = null;

export function getSpokenReplies(): boolean {
  if (value === null) {
    try {
      value = window.localStorage.getItem(KEY) !== "off";
    } catch {
      value = true;
    }
  }
  return value;
}

export function setSpokenReplies(on: boolean) {
  value = on;
  try {
    window.localStorage.setItem(KEY, on ? "on" : "off");
  } catch {
    /* keep the in-memory value */
  }
  listeners.forEach((l) => l());
}

export function subscribeSpokenReplies(cb: () => void) {
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
}

/** Value used while rendering on the server. */
export const spokenRepliesServerValue = () => true;
