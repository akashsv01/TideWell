import type { Metadata } from "next";
import ClinicianPortal from "@/components/ClinicianPortal";

export const metadata: Metadata = { title: "Clinician view" };

export default function ClinicianPage() {
  return <ClinicianPortal />;
}
