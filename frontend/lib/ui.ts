// Shared class strings so buttons and focus rings look the same everywhere.

export const focusRing =
  "focus:outline-none focus-visible:ring-4 focus-visible:ring-navy focus-visible:ring-offset-2 focus-visible:ring-offset-foam";

/** Focus ring for use on navy backgrounds. */
export const focusRingLight =
  "focus:outline-none focus-visible:ring-4 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-navy";

const buttonBase =
  "inline-flex min-h-14 items-center justify-center rounded-full px-8 text-lg font-semibold transition-colors motion-safe:active:scale-[0.98] aria-disabled:opacity-60";

export const btnPrimary = `${buttonBase} bg-tide-deep text-white hover:bg-navy ${focusRing}`;
export const btnOutline = `${buttonBase} border-2 border-navy text-navy hover:bg-navy hover:text-white ${focusRing}`;
