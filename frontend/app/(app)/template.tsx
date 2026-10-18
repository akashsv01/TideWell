// Remounts on navigation within (app), so page state resets and the soft page-in runs again.
// Next 16 templates still work with cacheComponents (unique key per segment navigation).
export default function AppTemplate({ children }: { children: React.ReactNode }) {
  return <div className="motion-safe:animate-page-in motion-reduce:animate-fade-in">{children}</div>;
}
