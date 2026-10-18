"use client";

import { useRouter, useSearchParams } from "next/navigation";
import UrgentCard from "@/components/UrgentCard";

// /urgent preview for design review (?level=urgent shows the "call today" tier), with a way back
// (history, or the home page if opened directly).
export default function UrgentPreview() {
  const router = useRouter();
  const level = useSearchParams().get("level") === "urgent" ? "urgent" : "emergency";
  return (
    <UrgentCard
      level={level}
      supportAlerted
      onBack={() => (window.history.length > 1 ? router.back() : router.push("/"))}
    />
  );
}
