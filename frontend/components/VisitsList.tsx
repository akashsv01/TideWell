"use client";

import Link from "next/link";
import BackLink from "@/components/BackLink";
import { useCallback, useEffect, useState } from "react";
import { ApiError, cancelVisit, joinVisit, listVisits } from "@/lib/api";
import { CalendarIcon, PinIcon, VideoIcon } from "@/components/icons";
import VideoVisit from "@/components/VideoVisit";
import { usePatientId, useSession } from "@/lib/session";
import type { Visit } from "@/lib/types";
import { btnPrimary, focusRing } from "@/lib/ui";
import { dayLabel, downloadIcs, isUpcoming, modeLabel, timeLabel } from "@/lib/visits";

// "Your visits": upcoming first, with Join for video visits once the room is open.

export default function VisitsList() {
  const patientId = usePatientId();
  const [visits, setVisits] = useState<Visit[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [call, setCall] = useState<{ url: string; who: string } | null>(null);

  const load = useCallback(() => {
    if (!patientId) return Promise.resolve();
    return listVisits(patientId).then(
      (v) => {
        setVisits(v);
        setError(null);
      },
      () => setError("We couldn't load your visits. Check your connection and try again.")
    );
  }, [patientId]);

  useEffect(() => {
    load();
  }, [load]);

  const replace = (updated: Visit) =>
    setVisits((vs) => (vs ?? []).map((v) => (v.appointment_id === updated.appointment_id ? updated : v)));

  const upcoming = (visits ?? []).filter((v) => isUpcoming(v));
  const earlier = (visits ?? []).filter((v) => !isUpcoming(v)).reverse();

  return (
    <div className="flex flex-col gap-8">
      <BackLink href="/care">Care</BackLink>
      <div className="-mt-4 flex flex-wrap items-center justify-between gap-4">
        <h1 className="font-display text-4xl font-semibold">Your visits</h1>
        <Link href="/visits/book" className={btnPrimary}>
          Book a visit
        </Link>
      </div>

      {error && (
        <p role="alert" className="rounded-2xl bg-white p-5 text-lg text-alert ring-2 ring-alert/30">
          {error}{" "}
          <button type="button" onClick={load} className={`rounded font-semibold underline ${focusRing}`}>
            Try again
          </button>
        </p>
      )}

      {visits === null && !error && <p className="text-lg text-navy/80">Loading your visits.</p>}

      {visits && upcoming.length === 0 && (
        <section aria-label="No upcoming visits" className="flex items-start gap-6 rounded-2xl bg-white p-6 shadow-paper ring-1 ring-navy/10">
          <div className="min-w-0 flex-1">
            <p className="font-display text-2xl font-semibold">No upcoming visits</p>
            <p className="mt-2 max-w-[48ch] text-lg leading-relaxed">
              When you want to see a doctor, midwife or counselor, book a visit in person near you or by video from
              home. If Tidewell suggests a visit, it shows on the Care page with the reasons.
            </p>
          </div>
        </section>
      )}

      {upcoming.length > 0 && (
        <ul aria-label="Upcoming visits" className="flex flex-col gap-4">
          {upcoming.map((v) => (
            <li key={v.appointment_id}>
              <VisitCard
                visit={v}
                onChanged={replace}
                onJoinInApp={(url, who) => setCall({ url, who })}
              />
            </li>
          ))}
        </ul>
      )}

      {earlier.length > 0 && (
        <details className="rounded-2xl bg-white p-5 shadow-paper ring-1 ring-navy/10">
          <summary className={`cursor-pointer rounded text-lg font-semibold ${focusRing}`}>
            Past and cancelled ({earlier.length})
          </summary>
          <ul className="mt-4 divide-y divide-navy/10">
            {earlier.map((v) => (
              <li key={v.appointment_id} className="py-3 text-lg">
                <p className="font-semibold">{v.provider.name}</p>
                <p className="text-navy/80">
                  {dayLabel(v.slot)}, {timeLabel(v.slot)} · {modeLabel(v.mode)}
                  {v.status === "cancelled" ? " · Cancelled" : ""}
                </p>
              </li>
            ))}
          </ul>
        </details>
      )}

      {call && <VideoVisit url={call.url} who={call.who} onLeave={() => setCall(null)} />}
    </div>
  );
}

function VisitCard({
  visit: v,
  onChanged,
  onJoinInApp,
}: {
  visit: Visit;
  onChanged: (v: Visit) => void;
  onJoinInApp: (url: string, who: string) => void;
}) {
  const { session } = useSession();
  const [now, setNow] = useState<number | null>(null);
  const [busy, setBusy] = useState<"join" | "doctor" | "cancel" | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [link, setLink] = useState<string | null>(null);

  // Re-check every 30 seconds so the Join button wakes up when the room opens.
  useEffect(() => {
    const tick = () => setNow(Date.now());
    tick();
    const id = setInterval(tick, 30_000);
    return () => clearInterval(id);
  }, []);

  const virtual = v.mode === "virtual";
  const win = v.join;
  const inWindow =
    now !== null && win?.opens_at && win.closes_at
      ? now >= new Date(win.opens_at).getTime() && now <= new Date(win.closes_at).getTime()
      : false;
  const canJoin = Boolean(win?.can_join) || inWindow;
  const hintId = `hint-${v.appointment_id}`;

  async function join(asDoctor: boolean) {
    if (busy || (!asDoctor && !canJoin)) return;
    setBusy(asDoctor ? "doctor" : "join");
    setMessage(null);
    setLink(null);
    try {
      const info = await joinVisit(v.appointment_id, asDoctor);
      if (info.embeddable && !asDoctor) {
        onJoinInApp(info.url, v.provider.name);
      } else if (!window.open(info.url, "_blank", "noopener")) {
        setLink(info.url); // the browser blocked the new tab: offer a plain link
      }
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : "We couldn't open the video room. Try again.");
    } finally {
      setBusy(null);
    }
  }

  async function cancel() {
    setBusy("cancel");
    setMessage(null);
    try {
      onChanged(await cancelVisit(v.appointment_id));
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : "We couldn't cancel this visit. Try again.");
      setBusy(null);
    }
  }

  return (
    <article aria-label={`Visit with ${v.provider.name}`} className="rounded-2xl bg-white p-5 shadow-paper ring-1 ring-navy/10 sm:p-6">
      <h2 className="font-display text-2xl font-semibold">
        {dayLabel(v.slot)}, {timeLabel(v.slot, true)}
      </h2>
      <p className="mt-2 flex items-center gap-2 text-lg font-semibold">
        {virtual ? <VideoIcon className="size-5 shrink-0" /> : <PinIcon className="size-5 shrink-0" />}
        {modeLabel(v.mode)} with {v.provider.name}
      </p>
      <p className="text-lg text-navy/80">{v.provider.specialty}</p>
      {!virtual && v.provider.address && (
        <p className="mt-1 text-lg">
          {v.provider.clinic}, {v.provider.address}
        </p>
      )}
      {v.reason && <p className="mt-2 text-lg text-navy/80">For: {v.reason}</p>}

      <div className="mt-5 flex flex-wrap items-center gap-3">
        {virtual && (
          <button
            type="button"
            onClick={() => join(false)}
            aria-disabled={!canJoin || busy !== null}
            aria-describedby={!canJoin && win?.opens_at ? hintId : undefined}
            className={`${btnPrimary} min-h-12 px-6`}
          >
            {busy === "join" ? "Opening" : "Join video visit"}
          </button>
        )}
        <button
          type="button"
          onClick={() => downloadIcs(v)}
          className={`inline-flex min-h-12 items-center gap-2 rounded-full border-2 border-navy px-5 font-semibold ${focusRing}`}
        >
          <CalendarIcon className="size-5" />
          Add to calendar
        </button>
        {!confirming ? (
          <button
            type="button"
            onClick={() => setConfirming(true)}
            className={`inline-flex min-h-12 items-center rounded-full px-4 font-semibold underline underline-offset-4 ${focusRing}`}
          >
            Cancel visit
          </button>
        ) : (
          <span className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={cancel}
              aria-disabled={busy === "cancel"}
              className={`inline-flex min-h-12 items-center rounded-full bg-alert px-5 font-semibold text-white ${focusRing}`}
            >
              {busy === "cancel" ? "Cancelling" : "Yes, cancel this visit"}
            </button>
            <button
              type="button"
              onClick={() => setConfirming(false)}
              className={`inline-flex min-h-12 items-center rounded-full px-4 font-semibold underline underline-offset-4 ${focusRing}`}
            >
              Keep it
            </button>
          </span>
        )}
      </div>

      {virtual && !canJoin && win?.opens_at && (
        <p id={hintId} className="mt-3 text-base text-navy/80">
          The video room opens at {timeLabel(win.opens_at)}, 15 minutes before the visit.
        </p>
      )}
      {virtual && session?.kind === "demo" && (
        <p className="mt-3 text-base text-navy/80">
          Trying the demo?{" "}
          <button
            type="button"
            onClick={() => join(true)}
            aria-disabled={busy !== null}
            className={`rounded font-semibold underline underline-offset-2 ${focusRing}`}
          >
            Open the doctor&apos;s side
          </button>{" "}
          on another device to see both ends of the call.
        </p>
      )}
      {link && (
        <p className="mt-3 text-lg">
          <a href={link} target="_blank" rel="noreferrer" className={`rounded font-semibold underline ${focusRing}`}>
            Open the video room
          </a>
        </p>
      )}
      {message && (
        <p role="alert" className="mt-3 text-lg text-alert">
          {message}
        </p>
      )}
    </article>
  );
}
