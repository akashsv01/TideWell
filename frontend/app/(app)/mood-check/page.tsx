import type { Metadata } from "next";
import MoodCheck from "@/components/MoodCheck";

export const metadata: Metadata = { title: "Weekly mood check" };

export default function MoodCheckPage() {
  return <MoodCheck />;
}
