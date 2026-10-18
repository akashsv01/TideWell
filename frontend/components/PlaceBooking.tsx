"use client";

import { useEffect, useRef, useState } from "react";
import { ApiError, bookPlace, getPlaceSlots } from "@/lib/api";
import type { Place, Slot } from "@/lib/types";
import { btnOutline, btnPrimary, focusRing } from "@/lib/ui";
import { groupByDay, timeLabel, whenLabel } from "@/lib/visits";

// Book an in-person visit at one place from Care near you. Open times come from the demo scheduler
// (backend GET /care/place-slots) and leave out anything already booked there, by anyone. While this is
// open the list refreshes every 15 s, so a time someone else books disappears and a cancelled one comes back.

const FIRST_DAYS = 2; // the next two clinic days; the rest behind "More times"

export default function PlaceBooking({
  place,
  patientId,
  demo,
  onBooked,
  onClose,
}: {
  place: Place;
  patientId: string;
  demo: boolean;
  onBooked: () => void;
  onClose: () => void;
}) {
  const [slots, setSlots] = useState<Slot[] | null>(null);
  const [slot, setSlot] = useState("");
  const [reason, setReason] = useState("");
  const [all, setAll] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [booked, setBooked] = useState<string | null>(null);
  const slotRef = useRef(slot);
  useEffect(() => {
    slotRef.current = slot;
  }, [slot]);

  useEffect(() => {
    if (booked) return;
    let cancelled = false;
    const refresh = () =>
      getPlaceSlots(place.name).then(
        (s) => {
          if (cancelled) return;
          setSlots(s);
          if (slotRef.current && !s.some((x) => x.slot === slotRef.current)) {
            setSlot("");
            setError("Someone just booked that time. Please choose another.");
          }
        },
        () => !cancelled && setError("We couldn't load open times. Check your connection and try again.")
      );
    refresh();
    const id = setInterval(refresh, 15_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [place.name, booked]);

  async function confirm() {
    if (!slot || busy) return;
    setBusy(true);
    setError(null);
    try {
      await bookPlace(patientId, place, slot, reason.trim());
      setBooked(slot);
      onBooked();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setSlot("");
        setSlots((s) => s?.filter((x) => x.slot !== slot) ?? s);
      }
      setError(e instanceof ApiError ? e.message : "We couldn't book that. Check your connection and try again.");
    } finally {
      setBusy(false);
    }
  }

  if (demo) {
    return (
      <div className="mt-4 rounded-2xl bg-sand/70 p-4">
        <p className="text-lg">This is Maya&apos;s demo, so booking a clinic is turned off. Create an account to book.</p>
        <button type="button" onClick={onClose} className={`mt-2 rounded font-semibold underline underline-offset-4 ${focusRing}`}>Close</button>
      </div>
    );
  }

  if (booked) {
    return (
      <div role="status" className="mt-4 rounded-2xl bg-white p-4 shadow-paper ring-2 ring-tide-deep/40 motion-safe:animate-reply-in">
        <p className="text-lg font-semibold">Booked: {whenLabel(booked)}</p>
        <p className="mt-1 text-base">
          It&apos;s in Your upcoming visits. Call {place.phone ?? "the clinic"} to confirm; times here are illustrative.
        </p>
      </div>
    );
  }

  const days = slots ? groupByDay(slots) : [];
  const shown = all ? days : days.slice(0, FIRST_DAYS);
  return (
    <div className="mt-4 rounded-2xl bg-foam p-4 motion-safe:animate-reply-in" aria-label={`Book a visit at ${place.name}`}>
      <p className="text-base font-semibold">Choose a time (Eastern time)</p>
      {slots === null && !error && <p role="status" className="mt-2 text-base">Looking for open times…</p>}
      {slots?.length === 0 && <p className="mt-2 text-base">No open times in the next week. Please call the clinic.</p>}
      {shown.map((g) => (
        <fieldset key={g.day} className="mt-3">
          <legend className="text-base font-semibold text-navy/85">{g.day}</legend>
          <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {g.slots.map((s) => (
              <button
                key={s}
                type="button"
                aria-pressed={slot === s}
                onClick={() => {
                  setSlot(s);
                  setError(null);
                }}
                className={`min-h-11 rounded-xl border-2 px-3 text-base font-semibold transition-[background-color,border-color,color] duration-150 ${slot === s ? "border-tide-deep bg-tide-deep text-white" : "border-navy/25 bg-white"} ${focusRing}`}
              >
                {timeLabel(s)}
              </button>
            ))}
          </div>
        </fieldset>
      ))}
      {days.length > FIRST_DAYS && !all && (
        <button type="button" onClick={() => setAll(true)} className={`mt-3 rounded font-semibold underline underline-offset-4 ${focusRing}`}>
          More times
        </button>
      )}
      <label htmlFor={`reason-${place.name}`} className="mt-4 block text-base font-semibold">
        Reason (optional)
      </label>
      <input
        id={`reason-${place.name}`}
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        maxLength={500}
        placeholder="For example: blood pressure check"
        className={`mt-1 min-h-12 w-full rounded-xl border-2 border-navy/40 bg-white px-3 text-base ${focusRing}`}
      />
      {error && <p role="alert" className="mt-3 text-base text-alert">{error}</p>}
      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" onClick={confirm} aria-disabled={!slot || busy} className={`${btnPrimary} min-h-12 px-6 text-base`}>
          {busy ? "Booking" : slot ? `Book ${timeLabel(slot)}` : "Choose a time"}
        </button>
        <button type="button" onClick={onClose} className={`${btnOutline} min-h-12 px-6 text-base`}>Cancel</button>
      </div>
    </div>
  );
}
