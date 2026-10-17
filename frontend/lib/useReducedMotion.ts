"use client";

import { useSyncExternalStore } from "react";

// For motion that CSS `motion-safe:` can't reach (JS-driven chart animations).
const QUERY = "(prefers-reduced-motion: reduce)";

function subscribe(cb: () => void) {
  const mq = window.matchMedia(QUERY);
  mq.addEventListener("change", cb);
  return () => mq.removeEventListener("change", cb);
}

export function useReducedMotion(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => window.matchMedia(QUERY).matches,
    () => true // server render: assume reduced, so nothing animates before hydration
  );
}
