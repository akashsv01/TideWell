"use client";

import { useEffect, useState } from "react";
import UrgentCard from "@/components/UrgentCard";
import { getHealthAlerts, markHealthAlertsSeen } from "@/lib/api";
import { useSession } from "@/lib/session";
import type { RedFlagLevel } from "@/lib/types";

// Shows the urgent card when the iPhone sent an unsafe blood pressure reading (the backend checks
// each one the moment it arrives). Checks when the app opens, every minute while it is open, and
// when the tab comes back into view. "Go back" marks the alert as seen so it shows once.
const EVERY_MS = 60_000;

export default function HealthAlertWatcher() {
  const { session } = useSession();
  const patientId = session?.kind === "user" ? session.patientId : null;
  const [level, setLevel] = useState<RedFlagLevel | null>(null);
  const [reading, setReading] = useState<string | null>(null);

  useEffect(() => {
    if (!patientId) return;
    let cancelled = false;
    const check = () => {
      if (document.visibilityState !== "visible") return;
      getHealthAlerts(patientId).then(
        ({ alerts }) => {
          if (cancelled || alerts.length === 0) return;
          const worst = alerts.find((a) => a.level === "emergency") ?? alerts[0];
          setLevel(worst.level);
          setReading(worst.bp_sys && worst.bp_dia ? `${worst.bp_sys}/${worst.bp_dia}` : null);
        },
        () => {} // offline or signed out: try again next time
      );
    };
    check();
    const id = setInterval(check, EVERY_MS);
    document.addEventListener("visibilitychange", check);
    return () => {
      cancelled = true;
      clearInterval(id);
      document.removeEventListener("visibilitychange", check);
    };
  }, [patientId]);

  if (!level || !patientId) return null;
  return (
    <UrgentCard
      level={level}
      context={`Your blood pressure cuff sent a reading${reading ? ` of ${reading}` : ""} through Apple Health.`}
      onBack={() => {
        setLevel(null);
        markHealthAlertsSeen(patientId).catch(() => {});
      }}
    />
  );
}
