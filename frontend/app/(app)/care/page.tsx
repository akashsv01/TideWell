import type { Metadata } from "next";
import CarePanel from "@/components/CarePanel";

export const metadata: Metadata = { title: "Care" };

export default function CarePage() {
  return <CarePanel />;
}
