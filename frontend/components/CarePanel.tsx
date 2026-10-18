"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ApiError, bookCare, clearLocation, dismissCare, downloadSummary, getNearby, getNearbyByZip, getRisk, saveLocation } from "@/lib/api";
import { AlertIcon, PinIcon, VideoIcon } from "@/components/icons";
import PlaceBooking from "@/components/PlaceBooking";
import { useSession } from "@/lib/session";
import type { Nearby, Place, RiskResult, Tier } from "@/lib/types";
import { btnOutline, btnPrimary, focusRing } from "@/lib/ui";

// Care, top to bottom: what Tidewell is watching (status in sentences, the most serious first); its
// suggested visit (why, where, when); your
// upcoming visits; care near you (OB-GYNs, midwives and hospitals from the NPI Registry, each bookable,
// plus video visits with Tidewell's providers); and the visit summary PDF.

// Status is said in a sentence, never a badge. The more serious the tier, the larger it is set.
const TIER_SAYS: Record<Tier, string> = {
  green: "Steady.",
  watch: "Keeping an eye on this.",
  amber: "Worth a visit in the next few days.",
  red: "Needs care now.",
};
const OVERALL_SAYS: Record<Tier, string> = {
  green: "Everything Tidewell checks looks steady right now.",
  watch: "Nothing needs a visit yet. Tidewell is keeping an eye on a few things.",
  amber: "Tidewell suggests a visit in the next few days.",
  red: "Tidewell suggests getting care now. If it feels like an emergency, call 911.",
};
const CATEGORY: Record<string, string> = {
  high_blood_pressure: "Blood pressure", depression_anxiety: "Mood", post_cesarean: "C-section recovery",
  sleep: "Sleep", disengagement: "Check-ins",
};
const when = (iso: string) =>
  new Date(iso).toLocaleString("en-US", { weekday: "long", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

const day = (iso: string) => new Date(iso).toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });

const PLACES_FIRST = 5; // nearest first; the rest are behind a More button

// Which Tidewell provider fits what the Watch agent is watching (Book a visit suggests them first).
const PROVIDER_KIND: Record<string, string> = {
  high_blood_pressure: "blood_pressure", depression_anxiety: "mental_health", post_cesarean: "obstetrics",
  sleep: "midwifery", disengagement: "midwifery",
};
const RANK: Record<Tier, number> = { red: 3, amber: 2, watch: 1, green: 0 };

/** /visits/book, pre-set from the Watch agent: the provider kind for the most serious category,
 *  how soon, and the reasons as the visit note. */
function bookHref(risk: RiskResult | null, mode?: "virtual"): string {
  const top = risk?.tiers.filter((t) => t.tier !== "green").sort((a, b) => RANK[b.tier] - RANK[a.tier])[0];
  if (!top) return mode ? `/visits/book?mode=${mode}` : "/visits/book";
  const q = new URLSearchParams({
    urgency: top.tier === "amber" || top.tier === "red" ? "amber" : "watch",
    reason: top.reasons.join(". ").slice(0, 300),
  });
  if (PROVIDER_KIND[top.category]) q.set("kind", PROVIDER_KIND[top.category]);
  if (mode) q.set("mode", mode);
  return `/visits/book?${q}`;
}

export default function CarePanel() {
  const { session } = useSession();
  const patientId = session?.patientId ?? null;
  const demo = session?.kind === "demo";
  const [risk, setRisk] = useState<RiskResult | null>(null);
  const [near, setNear] = useState<Nearby | null>(null);
  const [zip, setZip] = useState("");
  const [locMsg, setLocMsg] = useState<string | null>(null);
  const [editingLoc, setEditingLoc] = useState(false);
  const [finding, setFinding] = useState(false);
  const [expandedFor, setExpandedFor] = useState<Nearby | null>(null); // a new search is a new object, so it starts collapsed
  const [pick, setPick] = useState<{ slot: string; fac: number } | null>(null);
  const [booking, setBooking] = useState<"idle" | "busy" | "done" | "error">("idle");
  const [bookError, setBookError] = useState<string | null>(null);
  const [bookingAt, setBookingAt] = useState<string | null>(null); // which nearby place is being booked
  const [careMode, setCareMode] = useState<"in_person" | "video">("in_person");

  // Tabs: left and right arrows move between In person and Video (WAI-ARIA tabs pattern).
  function onTabKey(e: React.KeyboardEvent) {
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    e.preventDefault();
    const next = careMode === "in_person" ? "video" : "in_person";
    setCareMode(next);
    document.getElementById(`tab-${next}`)?.focus();
  }
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
    setFinding(true);
    try {
      if (demo) {
        // The demo can look elsewhere for this visit, but never saves.
        if (!coords) setNear(await getNearbyByZip(zip.trim()));
      } else {
        await saveLocation(patientId, coords ?? { postal_code: zip.trim() });
        setNear(await getNearby(patientId));
      }
      setLocMsg(null);
      setEditingLoc(false);
      setZip("");
    } catch (e) {
      setLocMsg(e instanceof ApiError ? e.message : "We couldn't find care for that location.");
    } finally {
      setFinding(false);
    }
  }

  async function forgetLocation() {
    if (!patientId) return;
    setLocMsg(null);
    setEditingLoc(false);
    if (!demo) {
      try {
        await clearLocation(patientId);
      } catch {
        setLocMsg("We couldn't clear your location. Try again.");
        return;
      }
    }
    setNear(demo ? await getNearby(patientId).catch(() => null) : { places: [], label: null, nearest_er: null, needs_location: true });
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
    setBookError(null);
    try {
      await bookCare(req.id, pick.slot, pick.fac);
      setBooking("done");
      load();
    } catch (e) {
      setBookError(e instanceof ApiError ? e.message : null);
      setBooking("error");
    }
  }

  const req = risk?.care_request;
  return (
    <div className="space-y-12">
      <header>
        <h1 className="font-display text-4xl font-semibold leading-tight">Care</h1>
        <p className="mt-3 max-w-[52ch] text-lg leading-relaxed text-navy/85">
          After every check-in, Tidewell compares your numbers with guideline limits. When something needs a
          doctor, it finds care near you and suggests times. Nothing is booked until you choose.
        </p>
      </header>

      {/* What Tidewell is watching */}
      <section aria-labelledby="watch-title">
        {!risk ? (
          <h2 id="watch-title" role="status" className="text-lg">Checking your latest numbers…</h2>
        ) : (
          <>
            <h2
              id="watch-title"
              className={`max-w-[48ch] font-display font-semibold leading-snug ${RANK[risk.overall] >= 2 ? "text-3xl" : "text-2xl"}`}
            >
              {OVERALL_SAYS[risk.overall]}
            </h2>
            <ul className="mt-5 divide-y divide-navy/10 rounded-2xl bg-white shadow-paper ring-1 ring-navy/10">
              {[...risk.tiers].sort((a, b) => RANK[b.tier] - RANK[a.tier]).map((t) => {
                const serious = RANK[t.tier] >= 2;
                return (
                  <li key={t.category} className="flex gap-3 p-5">
                    {serious ? (
                      <AlertIcon className={`mt-1 size-6 shrink-0 ${t.tier === "red" ? "text-alert" : "text-navy"}`} />
                    ) : (
                      <span aria-hidden="true" className="size-6 shrink-0" />
                    )}
                    <div className="min-w-0">
                      <h3 className={serious ? "text-xl font-semibold" : "text-lg font-semibold"}>
                        {CATEGORY[t.category] ?? t.category}
                      </h3>
                      <p className={`mt-1 leading-relaxed ${serious ? "text-lg" : "text-base text-navy/80"}`}>
                        <span className={serious ? "font-semibold" : ""}>{TIER_SAYS[t.tier]}</span>{" "}
                        {t.reasons.join(". ")}.
                      </p>
                    </div>
                  </li>
                );
              })}
            </ul>
          </>
        )}
      </section>

      {/* Booking agent proposal */}
      {req && req.tier !== "red" && booking !== "done" && (
        <section aria-labelledby="book-title" className="rounded-2xl bg-white p-6 shadow-lift ring-1 ring-navy/10 motion-safe:animate-reply-in sm:p-8">
          <h2 id="book-title" className="font-display text-3xl font-semibold">Suggested visit</h2>
          <p className="mt-1 text-base text-navy/80">
            Tidewell suggested this{req.created_at ? ` on ${day(req.created_at)}` : ""}, from your check-ins.
          </p>
          {req.outdated && (
            <p className="mt-3 rounded-xl bg-sand/60 p-3 text-base">
              Your numbers look steadier now than when this was suggested. You can still book, or tap Not now.
            </p>
          )}
          <h3 className="mt-5 text-lg font-semibold">Why</h3>
          <ul className="mt-2 list-disc space-y-1 pl-6 text-lg leading-relaxed">
            {req.reasons.map((r) => <li key={r}>{r}</li>)}
          </ul>
          <p className="mt-3 text-base text-navy/80">
            Tidewell compares your check-ins, blood pressure, mood check and sleep with guideline limits. For example,
            ACOG says a blood pressure of 140/90 or higher after birth should be checked within a few days. Tidewell
            never books without you.
          </p>
          {req.facilities.length > 0 && (
            <fieldset className="mt-5">
              <legend className="text-lg font-semibold">Where</legend>
              <div className="mt-2 space-y-2">
                {req.facilities.map((f, i) => (
                  <label key={f.name} className={`flex cursor-pointer items-start gap-3 rounded-xl bg-foam/70 p-4 ring-2 transition-colors duration-150 ${(pick?.fac ?? 0) === i ? "ring-tide-deep" : "ring-navy/10"}`}>
                    <input type="radio" name="fac" checked={(pick?.fac ?? 0) === i} onChange={() => setPick((p) => ({ slot: p?.slot ?? "", fac: i }))} className="mt-1.5 size-5 accent-tide-deep" />
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
          {booking === "error" && <p role="alert" className="mt-3 text-lg text-alert">{bookError ?? "We couldn't book that. Try another time."}</p>}
          <p className="mt-4 text-base">
            Rather talk from home?{" "}
            <Link href={bookHref(risk, "virtual")} className={`rounded font-semibold underline underline-offset-4 ${focusRing}`}>
              Book a video visit instead
            </Link>
          </p>
          <p className="mt-4 text-sm text-navy/70">Demo scheduler: times are illustrative. Call the clinic to confirm.</p>
        </section>
      )}

      {booking === "done" && (
        <p role="status" className="rounded-2xl bg-white p-5 text-lg font-semibold shadow-paper ring-2 ring-tide-deep/40 motion-safe:animate-reply-in">
          Booked. Your doctor will see Tidewell&apos;s summary of why. It&apos;s also in your visit summary.
        </p>
      )}

      {/* Upcoming visits: everything booked, whichever way */}
      {risk && !demo && (
        <section aria-labelledby="appt-title">
          <h2 id="appt-title" className="font-display text-2xl font-semibold">Your upcoming visits</h2>
          {risk.appointments.length === 0 ? (
            <p className="mt-2 text-lg text-navy/85">
              Nothing booked yet. Book a suggested visit above, a place near you below, or a video visit.
            </p>
          ) : (
            <ul className="mt-3 space-y-2">
              {risk.appointments.map((a) => (
                <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-white p-4 shadow-paper ring-1 ring-navy/10">
                  <span>
                    <span className="block text-lg font-semibold">{when(a.slot)}</span>
                    <span className="block text-base text-navy/80">
                      {a.mode === "virtual" ? "Video visit · " : "In person · "}
                      {a.facility_name ?? "Clinic"}
                      {a.facility_phone ? ` · ${a.facility_phone}` : ""}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          )}
          <Link href="/visits" className={`${btnOutline} mt-4`}>
            {risk.appointments.length > 0 ? "Join, add to calendar or cancel" : "See past and cancelled visits"}
          </Link>
        </section>
      )}

      {/* Book a visit: two clear paths, in person near you or by video from home */}
      <section aria-labelledby="near-title">
        <h2 id="near-title" className="font-display text-2xl font-semibold">Book a visit</h2>
        <p className="mt-1 text-lg text-navy/85">See someone in person near you, or by video from home.</p>

        <div role="tablist" aria-label="How would you like to be seen?" className="mt-4 grid grid-cols-2 gap-2 rounded-full bg-navy/5 p-1.5" onKeyDown={onTabKey}>
          {(["in_person", "video"] as const).map((m) => (
            <button
              key={m}
              id={`tab-${m}`}
              type="button"
              role="tab"
              aria-selected={careMode === m}
              aria-controls={`panel-${m}`}
              aria-label={m === "in_person" ? "In person, near you" : "Video, from home"}
              tabIndex={careMode === m ? 0 : -1}
              onClick={() => setCareMode(m)}
              className={`flex min-h-12 items-center justify-center gap-2 rounded-full px-3 text-base font-semibold transition-[background-color,color] duration-150 sm:text-lg ${careMode === m ? "bg-tide-deep text-white" : "text-navy/80 hover:bg-navy/5"} ${focusRing}`}
            >
              {m === "in_person" ? <PinIcon className="size-5 shrink-0" /> : <VideoIcon className="size-5 shrink-0" />}
              <span className="sm:hidden">{m === "in_person" ? "In person" : "Video"}</span>
              <span className="hidden sm:inline">{m === "in_person" ? "In person, near you" : "Video, from home"}</span>
            </button>
          ))}
        </div>

        {careMode === "in_person" ? (
          <div id="panel-in_person" role="tabpanel" aria-labelledby="tab-in_person" className="motion-safe:animate-fade-in">
            {near && !near.needs_location && !editingLoc && (
              <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2">
                <p className="text-lg text-navy/85">Near {near.label ?? "you"}</p>
                <button type="button" onClick={() => { setEditingLoc(true); setLocMsg(null); }} className={`rounded-md py-1 text-lg font-semibold underline underline-offset-4 ${focusRing}`}>
                  Change
                </button>
                <button type="button" onClick={forgetLocation} className={`rounded-md py-1 text-lg font-semibold underline underline-offset-4 ${focusRing}`}>
                  {demo ? "Reset" : "Clear"}
                </button>
              </div>
            )}
            {(near?.needs_location || editingLoc) && (
              <div className="mt-4 rounded-2xl bg-white p-5 shadow-paper ring-1 ring-navy/10 motion-safe:animate-reply-in">
                <p className="text-lg">
                  {editingLoc ? "Search somewhere else." : "Share your location or enter a ZIP code to see the closest hospitals, OB-GYNs and midwives you can book."}
                  {demo && " (The demo doesn't save it.)"}
                </p>
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <form onSubmit={(e) => { e.preventDefault(); if (zip.trim() && !finding) setLocation(); }} className="flex gap-2">
                    <label htmlFor="zip" className="sr-only">ZIP code</label>
                    <input id="zip" value={zip} onChange={(e) => setZip(e.target.value)} inputMode="numeric" autoComplete="postal-code" placeholder="ZIP code" maxLength={10} className={`min-h-14 w-36 rounded-full border-2 border-navy bg-white px-5 text-lg ${focusRing}`} />
                    <button type="submit" aria-disabled={finding || !zip.trim()} className={btnPrimary}>Search</button>
                  </form>
                  {!demo && <button type="button" onClick={useMyLocation} className={btnOutline}>Use my location</button>}
                  {editingLoc && (
                    <button type="button" onClick={() => { setEditingLoc(false); setLocMsg(null); }} className={`rounded-md px-2 py-2 text-lg font-semibold underline underline-offset-4 ${focusRing}`}>
                      Cancel
                    </button>
                  )}
                </div>
                {locMsg && <p role="status" className="mt-3 text-lg">{locMsg}</p>}
              </div>
            )}

            {near?.nearest_er && (
              <ErCard
                place={near.nearest_er}
                open={bookingAt === "__er__"}
                onToggle={() => setBookingAt(bookingAt === "__er__" ? null : "__er__")}
              >
                {bookingAt === "__er__" && patientId && (
                  <PlaceBooking place={near.nearest_er} patientId={patientId} demo={demo} onBooked={load} onClose={() => setBookingAt(null)} />
                )}
              </ErCard>
            )}

            {near && near.places.length > 0 && (
              <ul className="mt-4 divide-y divide-navy/10 rounded-2xl bg-white shadow-paper ring-1 ring-navy/10">
                {(expandedFor === near ? near.places : near.places.slice(0, PLACES_FIRST)).map((p) => {
                  const key = `${p.name}-${p.address}`;
                  const open = bookingAt === key;
                  return (
                    <li key={key} className="flex flex-col p-4 sm:p-5">
                      <span className="text-lg font-semibold">{p.name}</span>
                      <span className="text-base text-navy/80">{p.kind_label} · {p.distance_km} km</span>
                      {p.address && <span className="text-base text-navy/80">{p.address}</span>}
                      <span className="flex flex-wrap gap-2 pt-3">
                        <button
                          type="button"
                          aria-expanded={open}
                          onClick={() => setBookingAt(open ? null : key)}
                          className={`rounded-full border-2 border-tide-deep bg-tide-deep px-4 py-1.5 text-base font-semibold text-white ${focusRing}`}
                        >
                          {open ? "Close" : "Book a visit"}
                        </button>
                        <a href={p.directions_url} target="_blank" rel="noreferrer" className={`rounded-full border-2 border-navy px-4 py-1.5 text-base font-semibold ${focusRing}`}>Directions</a>
                        {p.phone && <a href={`tel:${p.phone.replace(/[^\d+]/g, "")}`} className={`rounded-full border-2 border-navy px-4 py-1.5 text-base font-semibold ${focusRing}`}>Call</a>}
                      </span>
                      {open && patientId && (
                        <PlaceBooking place={p} patientId={patientId} demo={demo} onBooked={load} onClose={() => setBookingAt(null)} />
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
            {near && near.places.length > PLACES_FIRST && expandedFor !== near && (
              <button type="button" onClick={() => setExpandedFor(near)} className={`mt-4 min-h-12 rounded-full border-2 border-navy px-6 text-lg font-semibold ${focusRing}`}>
                More places ({near.places.length - PLACES_FIRST})
              </button>
            )}
            {near && !near.needs_location && near.places.length === 0 && (
              <p className="mt-4 text-lg">We couldn&apos;t load places right now. In an emergency, call 911.</p>
            )}
            <p className="mt-4 text-sm text-navy/70">
              Doctors, midwives and hospitals from the US NPI Registry (CMS), with OpenStreetMap. Booking uses a demo
              scheduler, so times are illustrative: call ahead to confirm. In an emergency, call 911.
            </p>
          </div>
        ) : (
          <div id="panel-video" role="tabpanel" aria-labelledby="tab-video" className="mt-4 rounded-2xl bg-white p-6 shadow-paper ring-1 ring-navy/10 motion-safe:animate-fade-in">
            <p className="text-lg leading-relaxed">
              Talk to a Tidewell doctor, midwife, lactation consultant or counselor by video. You only need a phone or computer.
            </p>
            <ol className="mt-4 list-decimal space-y-2 pl-6 marker:font-semibold">
              {[
                "Choose who you'd like to see and a time.",
                "The video room opens 15 minutes before your visit. Join from Your upcoming visits.",
                "Your provider gets a link by email and joins you there.",
              ].map((t) => (
                <li key={t} className="text-lg leading-relaxed">
                  {t}
                </li>
              ))}
            </ol>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link href={bookHref(risk, "virtual")} className={btnPrimary}>Choose a provider and time</Link>
              <Link href="/visits" className={btnOutline}>Your visits</Link>
            </div>
            <p className="mt-4 text-sm text-navy/70">These providers are made up for the demo. Real clinics will replace them.</p>
          </div>
        )}
      </section>

      <section aria-labelledby="pdf-title" className="flex flex-wrap items-center justify-between gap-4 rounded-2xl bg-navy p-6 text-white sm:p-8">
        <div>
          <h2 id="pdf-title" className="font-display text-2xl font-semibold">Visit summary</h2>
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
    </div>
  );
}

function ErCard({ place, open, onToggle, children }: { place: Place; open: boolean; onToggle: () => void; children?: React.ReactNode }) {
  const emergency = place.kind === "emergency";
  return (
    <div className="mt-4 rounded-2xl bg-white p-5 shadow-paper ring-2 ring-alert/35">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold">
            {emergency ? "Nearest emergency room" : "Nearest hospital"}: {place.name}
          </h3>
          <p className="text-base text-navy/80">{place.distance_km} km{place.phone ? ` · ${place.phone}` : ""}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" aria-expanded={open} onClick={onToggle} className={`inline-flex min-h-12 items-center rounded-full bg-tide-deep px-5 font-semibold text-white ${focusRing}`}>
            {open ? "Close" : "Book a visit"}
          </button>
          <a href={place.directions_url} target="_blank" rel="noreferrer" className={`inline-flex min-h-12 items-center rounded-full border-2 border-navy px-5 font-semibold ${focusRing}`}>
            Directions
          </a>
          {/* No listed number: fall back to 911, which is right for an emergency room */}
          <a href={`tel:${place.phone ? place.phone.replace(/[^\d+]/g, "") : "911"}`} className={`inline-flex min-h-12 items-center rounded-full border-2 border-navy px-5 font-semibold ${focusRing}`}>
            {place.phone ? "Call" : "Call 911"}
          </a>
        </div>
      </div>
      <p className="mt-2 text-sm text-navy/75">For a check-up you can book. In an emergency, don&apos;t book: go now or call 911.</p>
      {children}
    </div>
  );
}
