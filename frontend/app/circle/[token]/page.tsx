import type { Metadata } from "next";
import { Suspense } from "react";
import CircleViewPanel from "@/components/CircleViewPanel";

export const metadata: Metadata = { title: "Care Circle", robots: { index: false } };

// The token is read on the client (useParams), so the shell stays static.
export function generateStaticParams() {
  return [{ token: "preview" }];
}

export default function CirclePage() {
  return (
    <Suspense fallback={<p className="p-10 text-xl">Loading…</p>}>
      <CircleViewPanel />
    </Suspense>
  );
}
