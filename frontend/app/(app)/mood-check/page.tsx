import type { Metadata } from "next";
import MoodCheck from "@/components/MoodCheck";

export const metadata: Metadata = { title: "Daily mood check" };

export default function MoodCheckPage() {
  return <MoodCheck />;
}
