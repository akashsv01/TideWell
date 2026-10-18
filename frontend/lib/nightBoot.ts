// Night-mode constants shared by the server root layout and the client code (lib/night.ts).
// Kept out of the "use client" module so the server can read them as plain values.

export const NIGHT_KEY = "tidewell.night";
export const NIGHT_PAGE = "#07131f";
export const DAY_PAGE = "#f4f9f9";

/** Runs in <head> before first paint so a night-time visit never flashes the light theme.
 *  Same rule as isNightNow(): "on", or "auto" between 10 pm and 6 am. */
export const NIGHT_BOOT_SCRIPT = `try{var p=localStorage.getItem("${NIGHT_KEY}");var h=new Date().getHours();if(p==="on"||(p!=="off"&&(h>=22||h<6)))document.documentElement.setAttribute("data-night","")}catch(e){}`;
