// Shared class strings so buttons and focus rings look the same everywhere.

export const focusRing =
  "focus:outline-none focus-visible:ring-4 focus-visible:ring-navy focus-visible:ring-offset-2 focus-visible:ring-offset-foam";

/** Focus ring for use on navy backgrounds. */
export const focusRingLight =
  "focus:outline-none focus-visible:ring-4 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-navy";

const buttonBase =
  "inline-flex min-h-14 items-center justify-center rounded-full px-8 text-lg font-semibold transition-[color,background-color,border-color,transform] duration-150 ease-out motion-safe:active:scale-[0.97] aria-disabled:opacity-60";

export const btnPrimary = `${buttonBase} bg-tide-deep text-white hover:bg-navy ${focusRing}`;
export const btnOutline = `${buttonBase} border-2 border-navy text-navy hover:bg-navy hover:text-white ${focusRing}`;

/** The moon: the one primary action on a page of the picture book (landing). Ink text on gold
 *  stays dark in night mode on purpose (contrast 5.9:1). */
export const btnMoon = `${buttonBase} bg-gold text-[#1b2a22] shadow-[0_2px_4px_rgb(27_42_34/0.12),0_12px_28px_-14px_rgb(27_42_34/0.45)] hover:bg-[#d8ab43] ${focusRing}`;
