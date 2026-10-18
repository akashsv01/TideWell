// Night-mode constants shared by the server root layout and the client code (lib/night.ts).
// Kept out of the "use client" module so the server can read them as plain values.
// (No inline boot script: React 19 reports any <script> rendered by a component as an error.)

export const NIGHT_KEY = "tidewell.night";
export const NIGHT_PAGE = "#07131f";
export const DAY_PAGE = "#f4f9f9";
