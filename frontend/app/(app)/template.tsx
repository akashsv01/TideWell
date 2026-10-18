// Remounts on navigation within (app), so page state resets and a soft page-in runs again.
// The animation has no fill-mode, so the page is visible even if the animation never plays
// (Next 16 keeps visited segments mounted while hidden); it passes the flex layout through.
export default function AppTemplate({ children }: { children: React.ReactNode }) {
  return <div className="flex flex-1 flex-col motion-safe:animate-page-in">{children}</div>;
}
