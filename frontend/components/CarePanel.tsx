"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, bookCare, dismissCare, downloadSummary, getNearby, getRisk, saveLocation } from "@/lib/api";
import { useSession } from "@/lib/session";
import type { Nearby, Place, RiskResult, Tier } from "@/lib/types";
import { btnOutline, btnPrimary, focusRing } from "@/lib/ui";

// Care: what the Watch agent sees, what the Booking agent proposes (book with one tap), upcoming
// visits, and the nearest maternity care: OB-GYNs, midwives and hospitals from the official NPI
// Registry (plus OpenStreetMap emergency-room tags), by your location or ZIP code.

const TIER_STYLE: Record<Tier, { label: string; cls: string }> = {
  green: { label: "Steady", cls: "bg-[#e3f1e8] text-[#2f5d3f]" },
  watch: { label: "Watching", cls: "bg-tide-light/30 text-tide-deep" },
  amber: { label: "Visit soon", cls: "bg-chart-amber/20 text-[#7a4a10]" },
  red: { label: "Get care now", cls: "bg-alert/15 text-alert" },
};
const CATEGORY: Record<string, string> = {
  high_blood_pressure: "Blood pressure", depression_anxiety: "Mood", post_cesarean: "C-section recovery",
  sleep: "Sleep", disengagement: "Check-ins",
};
const when = (iso: string) =>
  new Date(iso).toLocaleString("en-US", { weekday: "long", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

export default function CarePanel() {
  const { session } = useSession();
  const patientId = session?.patientId ?? null;
  const demo = session?.kind === "demo";
  const [risk, setRisk] = useState<RiskResult | null>(null);
  const [near, setNear] = useState<Nearby | null>(null);
  const [zip, setZip] = useState("");
  const [locMsg, setLocMsg] = useState<string | null>(null);
  const [pick, setPick] = useState<{ slot: string; fac: number } | null>(null);
  const [booking, setBooking] = useState<"idle" | "busy" | "done" | "error">("idle");
  const [pdfBusy, setPdfBusy] = useState(false);

  const load = useCallback(() => {
    if (!patientId) return;
    getRisk(patientId).then(setRisk, () => setRisk(null));
    getNearby(patientId).then(setNear, () => setNear({ places: [], label: null, nearest_er: null, needs_location: true }));
  }, [patientId]);

  useEffect(load, [load]);

  async function setLocation(coords?: { lat: number; lon: number }) {
    if (!patientId) return;
    setLocMsg("Finding care near you…");
    try {
      await saveLocation(patientId, coords ?? { postal_code: zip.trim() });
      setLocMsg(null);
      load();
    } catch (e) {
      setLocMsg(e instanceof ApiError ? e.message : "We couldn't save your location.");
    }
  }

  function useMyLocation() {
    if (!navigator.geolocation) return setLocMsg("Location isn't available here. Enter your ZIP code instead.");
    navigator.geolocation.getCurrentPosition(
      (p) => setLocation({ lat: p.coords.latitude, lon: p.coords.longitude }),
      () => setLocMsg("Location permission was declined. Enter your ZIP code instead."),
      { enableHighAccuracy: false, timeout: 10000 }
    );
  }

  async function book() {
    const req = risk?.care_request;
    if (!req?.id || !pick) return;
    setBooking("busy");
    try {
      await bookCare(req.id, pick.slot, pick.fac);
      setBooking("done");
      load();
    } catch {
      setBooking("error");
    }
  }

  const req = risk?.care_request;
  return (
    <div className="space-y-12">
      <header>
        <h1 className="font-display text-4xl leading-tight">Care</h1>
        <p className="mt-3 max-w-[50ch] text-lg leading-relaxed text-navy/85">
          Tidewell&apos;s Watch agent looks over your check-ins after every update. When something needs a
          doctor, it finds care near you and suggests times. Nothing is booked until you choose.
        </p>
      </header>

      {/* Watch agent */}
      <section aria-labelledby="watch-title" className="motion-safe:animate-section-in">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="watch-title" className="font-display text-2xl">What Tidewell is watching</h2>
          {risk && <span className={`rounded-full px-3 py-1 text-base font-semibold ${TIER_STYLE[risk.overall].cls}`}>{TIER_STYLE[risk.overall].label}</span>}
        </div>
        {!risk ? (
          <p role="status" className="mt-4 text-lg">Checking…</p>
        ) : (
          <ul className="mt-4 grid gap-3 sm:grid-cols-2">
            {risk.tiers.map((t) => (
              <li key={t.category} className="rounded-2xl bg-white p-4 ring-1 ring-navy/10">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-lg font-semibold">{CATEGORY[t.category] ?? t.category}</span>
                  <span className={`rounded-full px-2.5 py-0.5 text-sm font-semibold ${TIER_STYLE[t.tier].cls}`}>{TIER_STYLE[t.tier].label}</span>
                </div>
                <p className="mt-2 text-base leading-relaxed text-navy/85">{t.reasons.join(". ")}.</p>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Booking agent proposal */}
      {req && req.tier !== "red" && booking !== "done" && (
        <section aria-labelledby="book-title" className="rounded-3xl border-l-8 border-chart-amber bg-sand/70 p-6 motion-safe:animate-reply-in">
          <h2 id="book-title" className="font-display text-2xl">Suggested visit</h2>
          <p className="mt-2 text-lg leading-relaxed">{req.patient_message}</p>
          {req.facilities.length > 0 && (
            <fieldset className="mt-5">
              <legend className="text-lg font-semibold">Where</legend>
              <div className="mt-2 space-y-2">
                {req.facilities.map((f, i) => (
                  <label key={f.name} className={`flex cursor-pointer items-start gap-3 rounded-2xl bg-white p-4 ring-2 transition-colors duration-150 ${(pick?.fac ?? 0) === i ? "ring-tide-deep" : "ring-transparent"}`}>
                    <input type="radio" name="fac" checked={(pick?.fac ?? 0) === i} onChange={() => setPick((p) => ({ slot: p?.slot ?? "", fac: i }))} className="mt-1.5 size-5 accent-[#0e6a70]" />
                    <span>
                      <span className="block text-lg font-semibold">{f.name}</span>
                      <span className="block text-base text-navy/80">{f.kind_label} · {f.distance_km} km{f.address ? ` · ${f.address}` : ""}</span>
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
          )}
          <fieldset className="mt-5">
            <legend className="text-lg font-semibold">When</legend>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {req.slots.map((s) => (
                <button
                  key={s}
                  type="button"
                  aria-pressed={pick?.slot === s}
                  onClick={() => setPick((p) => ({ slot: s, fac: p?.fac ?? 0 }))}
                  className={`min-h-12 rounded-2xl border-2 px-4 text-left text-lg transition-[background-color,border-color,color,transform] duration-150 ease-out motion-safe:active:scale-[0.98] ${pick?.slot === s ? "border-tide-deep bg-tide-deep text-white" : "border-navy/25 bg-white"} ${focusRing}`}
                >
                  {when(s)}
                </button>
              ))}
            </div>
          </fieldset>
          <div className="mt-6 flex flex-wrap gap-3">
            {demo ? (
              <p className="text-lg">This is Maya&apos;s demo, so booking is turned off. Create an account to book your own.</p>
            ) : (
              <>
                <button type="button" onClick={book} aria-disabled={!pick?.slot || booking === "busy"} className={btnPrimary}>
                  {booking === "busy" ? "Booking" : "Book this visit"}
                </button>
                <button type="button" onClick={() => req.id && dismissCare(req.id).then(load)} className={btnOutline}>
                  Not now
                </button>
              </>
            )}
          </div>
          {booking === "error" && <p role="alert" className="mt-3 text-lg text-alert">We couldn&apos;t book that. Try another time.</p>}
          <p className="mt-4 text-sm text-navy/70">Demo scheduler: times are illustrative. Call the clinic to confirm.</p>
        </section>
      )}

      {booking === "done" && (
        <p role="status" className="rounded-3xl bg-[#e3f1e8] p-5 text-lg font-semibold text-[#2f5d3f] motion-safe:animate-reply-in">
          Booked. Your doctor will see Tidewell&apos;s summary of why. It&apos;s also in your visit summary.
        </p>
      )}

      {risk && risk.appointments.length > 0 && (
        <section aria-labelledby="appt-title">
          <h2 id="appt-title" className="font-display text-2xl">Upcoming visits</h2>
          <ul className="mt-3 space-y-2">
            {risk.appointments.map((a) => (
              <li key={a.id} className="rounded-2xl bg-white p-4 ring-1 ring-navy/10">
                <p className="text-lg font-semibold">{when(a.slot)}</p>
                <p className="text-base text-navy/80">{a.facility_name ?? "Clinic"}{a.facility_phone ? ` · ${a.facility_phone}` : ""}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section aria-labelledby="pdf-title" className="flex flex-wrap items-center justify-between gap-4 rounded-3xl bg-navy p-6 text-white">
        <div>
          <h2 id="pdf-title" className="font-display text-2xl">Visit summary</h2>
          <p className="mt-1 text-lg text-white/85">One page for your doctor: your numbers, what was flagged, and questions to ask.</p>
        </div>
        <button
          type="button"
          onClick={async () => {
            if (!patientId) return;
            setPdfBusy(true);
            try { await downloadSummary(patientId); } finally { setPdfBusy(false); }
          }}
          aria-disabled={pdfBusy}
          className={`inline-flex min-h-12 items-center rounded-full bg-white px-6 font-semibold text-navy transition-transform duration-150 ease-out motion-safe:active:scale-[0.97] focus:outline-none focus-visible:ring-4 focus-visible:ring-tide-light`}
        >
          {pdfBusy ? "Preparing" : "Download PDF"}
        </button>
      </section>

      {/* Nearby care */}
      <section aria-labelledby="near-title">
        <h2 id="near-title" className="font-display text-2xl">Care near you</h2>
        {near?.label && <p className="mt-1 text-base text-navy/80">Near {near.label}</p>}
        {near?.needs_location && !demo && (
          <div className="mt-4 rounded-3xl bg-white p-5 ring-1 ring-navy/10">
            <p className="text-lg">Share your location or enter a ZIP code to see the closest hospitals, OB-GYNs and midwives.</p>
            <div className="mt-4 flex flex-wrap gap-3">
              <button type="button" onClick={useMyLocation} className={btnPrimary}>Use my location</button>
              <form onSubmit={(e) => { e.preventDefault(); if (zip.trim()) setLocation(); }} className="flex gap-2">
                <label htmlFor="zip" className="sr-only">ZIP code</label>
                <input id="zip" value={zip} onChange={(e) => setZip(e.target.value)} inputMode="numeric" placeholder="ZIP code" maxLength={10} className={`min-h-14 w-36 rounded-full border-2 border-navy bg-white px-5 text-lg ${focusRing}`} />
                <button type="submit" className={btnOutline}>Search</button>
              </form>
            </div>
            {locMsg && <p role="status" className="mt-3 text-lg">{locMsg}</p>}
          </div>
        )}
        {near?.nearest_er && <ErCard place={near.nearest_er} />}
        {near && near.places.length > 0 && (
          <ul className="mt-4 grid gap-3 sm:grid-cols-2">
            {near.places.map((p) => (
              <li key={`${p.name}-${p.address}`} className="flex flex-col rounded-2xl bg-white p-4 ring-1 ring-navy/10">
                <span className="text-lg font-semibold">{p.name}</span>
                <span className="text-base text-navy/80">{p.kind_label} · {p.distance_km} km</span>
                {p.address && <span className="text-base text-navy/80">{p.address}</span>}
                <span className="mt-3 flex flex-wrap gap-2">
                  <a href={p.directions_url} target="_blank" rel="noreferrer" className={`rounded-full border-2 border-navy px-4 py-1.5 text-base font-semibold ${focusRing}`}>Directions</a>
                  {p.phone && <a href={`tel:${p.phone.replace(/[^\d+]/g, "")}`} className={`rounded-full border-2 border-navy px-4 py-1.5 text-base font-semibold ${focusRing}`}>Call</a>}
                </span>
              </li>
            ))}
          </ul>
        )}
        {near && !near.needs_location && near.places.length === 0 && (
          <p className="mt-4 text-lg">We couldn&apos;t load places right now. In an emergency, call 911.</p>
        )}
        <p className="mt-3 text-sm text-navy/70">
          Doctors, midwives and hospitals from the US NPI Registry (CMS), with OpenStreetMap. Listings can be out of
          date: call ahead to check they can see you. In an emergency, call 911.
        </p>
      </section>
    </div>
  );
}

function ErCard({ place }: { place: Place }) {
  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-3xl border-l-8 border-alert bg-white p-5 ring-1 ring-alert/20">
      <div>
        <p className="text-base font-semibold text-alert">{place.kind === "emergency" ? "Nearest emergency room" : "Nearest hospital"}</p>
        <p className="text-lg font-semibold">{place.name}</p>
        <p className="text-base text-navy/80">{place.distance_km} km{place.phone ? ` · ${place.phone}` : ""}</p>
      </div>
      <a href={place.directions_url} target="_blank" rel="noreferrer" className={`inline-flex min-h-12 items-center rounded-full bg-alert px-5 font-semibold text-white ${focusRing}`}>
        Directions
      </a>
    </div>
  );
}
