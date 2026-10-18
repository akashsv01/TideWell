import type { Metadata } from "next";
import { Suspense } from "react";
import BookVisit from "@/components/BookVisit";

export const metadata: Metadata = { title: "Book a visit" };

export default function BookVisitPage() {
  return (
    <Suspense fallback={null}>
      <BookVisit />
    </Suspense>
  );
}
