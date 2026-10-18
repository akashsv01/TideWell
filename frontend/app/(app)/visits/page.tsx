import type { Metadata } from "next";
import VisitsList from "@/components/VisitsList";

export const metadata: Metadata = { title: "Your visits" };

export default function VisitsPage() {
  return <VisitsList />;
}
