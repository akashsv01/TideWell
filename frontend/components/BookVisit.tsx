"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ApiError, bookVisit, getSlots, listProviders } from "@/lib/api";
import { CalendarIcon, PinIcon, VideoIcon } from "@/components/icons";
import { usePatientId } from "@/lib/session";
import type { Provider, Slot, Visit, VisitMode, VisitUrgency } from "@/lib/types";
import { btnOutline, btnPrimary, focusRing } from "@/lib/ui";
import { dayLabel, downloadIcs, groupByDay, modeLabel, timeLabel, whenLabel } from "@/lib/visits";

// Book a visit in a few short steps: who, in person or video, when, confirm.
// Query: ?urgency=amber|watch|routine  &reason=...  &kind=blood_pressure (suggests that provider first)

type Step = "provider" | "mode" | "time" | "confirm" | "done";

const choiceCard =
  "flex min-h-14 w-full cursor-pointer flex-col gap-0.5 rounded-2xl border-2 border-navy/25 bg-white px-4 py-3 text-lg transition-colors peer-checked:border-tide-deep peer-checked:bg-tide-deep peer-checked:text-white peer-focus-visible:ring-4 peer-focus-visible:ring-navy peer-focus-visible:ring-offset-2 peer-focus-visible:ring-offset-foam";

const URGENCIES: VisitUrgency[] = ["amber", "watch", "routine"];

export default function BookVisit() {
  const params = useSearchParams();
  const router = useRouter();
  const leave = () => (window.history.length > 1 ? router.back() : router.push("/care"));
  const patientId = usePatientId();
  const kind = params.get("kind");
  const preferMode: VisitMode | null = params.get("mode") === "virtual" ? "virtual" : null; // from Care's Video tab
  const rawUrgency = params.get("urgency");

  const [step, setStep] = useState<Step>("provider");
  const [providers, setProviders] = useState<Provider[] | null>(null);
  const [providerId, setProviderId] = useState("");
  const [mode, setMode] = useState<VisitMode | "">("");
  const [urgency, setUrgency] = useState<VisitUrgency>(
    URGENCIES.includes(rawUrgency as VisitUrgency) ? (rawUrgency as VisitUrgency) : "routine"
  );
  const [loaded, setLoaded] = useState<{ key: string; list: Slot[] } | null>(null);
  const [slot, setSlot] = useState("");
  const slotRef = useRef(slot); // the picked time, readable from the refresh timer
  useEffect(() => {
    slotRef.current = slot;
  }, [slot]);
  const [reason, setReason] = useState(params.get("reason")?.slice(0, 500) ?? "");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [visit, setVisit] = useState<Visit | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const firstRender = useRef(true);

  // Next keeps a page you have visited mounted (hidden), so this form could come back still showing "booked".
  // Effects are cleaned up when the page is hidden, so reset there: the next visit starts at the first step.
  useEffect(() => {
    return () => {
      setStep("provider");
      setProviderId("");
      setMode("");
      setUrgency(URGENCIES.includes(rawUrgency as VisitUrgency) ? (rawUrgency as VisitUrgency) : "routine");
      setLoaded(null);
      setSlot("");
      setReason(params.get("reason")?.slice(0, 500) ?? "");
      setError(null);
      setSaving(false);
      setVisit(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const slotsKey = `${providerId}|${mode}|${urgency}`;
  const slots = loaded?.key === slotsKey ? loaded.list : null; // null while loading
  const provider = providers?.find((p) => p.id === providerId) ?? null;
  const twoModes = (provider?.modes.length ?? 2) > 1 && !(preferMode && provider?.modes.includes(preferMode));
  const steps: Step[] = twoModes ? ["provider", "mode", "time", "confirm"] : ["provider", "time", "confirm"];

  useEffect(() => {
    let cancelled = false;
    listProviders().then(
      (list) => {
        if (cancelled) return;
        setProviders([...list].sort((a, b) => Number(b.kind === kind) - Number(a.kind === kind)));
      },
      () => !cancelled && setError("We couldn't load the list of providers. Check your connection and try again.")
    );
    return () => {
      cancelled = true;
    };
  }, [kind]);

  // Load open times on the time step, and keep them fresh while choosing or confirming: every 15 s
  // and when the tab comes back into view. Times other people book disappear (the backend hides them);
  // a cancelled time comes back. If the time you picked was just taken, say so and go back to choose.
  useEffect(() => {
    if ((step !== "time" && step !== "confirm") || !providerId || !mode) return;
    let cancelled = false;
    const refresh = () =>
      getSlots(urgency, { providerId, mode }).then(
        (s) => {
          if (cancelled) return;
          setLoaded({ key: slotsKey, list: s });
          const picked = slotRef.current;
          if (picked && !s.some((x) => x.slot === picked)) {
            setSlot("");
            setError("Someone just booked that time. Please choose another.");
            setStep("time");
          }
        },
        () => {
          if (!cancelled && step === "time") {
            setLoaded((l) => (l?.key === slotsKey ? l : { key: slotsKey, list: [] }));
            setError("We couldn't load open times. Check your connection and try again.");
          }
        }
      );
    refresh();
    const id = setInterval(refresh, 15_000);
    const onShow = () => document.visibilityState === "visible" && refresh();
    document.addEventListener("visibilitychange", onShow);
    return () => {
      cancelled = true;
      clearInterval(id);
      document.removeEventListener("visibilitychange", onShow);
    };
  }, [step, providerId, mode, urgency, slotsKey]);

  // Move focus to the new heading after each step so screen readers start there.
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    headingRef.current?.focus();
  }, [step]);

  function next() {
    setError(null);
    if (step === "provider") {
      if (!provider) return setError("Choose who you would like to see.");
      if (provider.modes.length === 1) {
        setMode(provider.modes[0]);
        return setStep("time");
      }
      if (preferMode && provider.modes.includes(preferMode)) {
        setMode(preferMode);
        return setStep("time");
      }
      return setStep("mode");
    }
    if (step === "mode") {
      if (!mode) return setError("Choose in person or video.");
      return setStep("time");
    }
    if (step === "time") {
      if (!slot) return setError("Choose a time.");
      return setStep("confirm");
    }
  }

  function back() {
    setError(null);
    if (step === "mode") setStep("provider");
    else if (step === "time") setStep(twoModes ? "mode" : "provider");
    else if (step === "confirm") setStep("time");
  }

  function pickProvider(p: Provider) {
    setProviderId(p.id);
    setSlot("");
    setMode(p.modes.length === 1 ? p.modes[0] : p.modes.includes(mode as VisitMode) ? mode : "");
  }

  async function confirm(e: React.FormEvent) {
    e.preventDefault();
    if (saving || !patientId || !provider || !mode || !slot) return;
    setSaving(true);
    setError(null);
    try {
      const v = await bookVisit({ patientId, providerId: provider.id, mode, slot, reason: reason.trim(), urgency });
      setVisit(v);
      setStep("done");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setSlot("");
        setError(err.message ? `${err.message[0].toUpperCase()}${err.message.slice(1)}.` : "That time was just taken. Please choose another.");
        setStep("time");
      } else {
        setError(err instanceof ApiError ? err.message : "We couldn't book this visit. Check your connection and try again.");
      }
    } finally {
      setSaving(false);
    }
  }

  const heading = {
    provider: "Who would you like to see?",
    mode: "How would you like to meet?",
    time: "Choose a time",
    confirm: "Check and confirm",
    done: "Your visit is booked",
  }[step];
  const position = steps.indexOf(step) + 1;

  return (
    <div className="mx-auto w-full max-w-md">
      {step !== "done" && (
        <p className="text-base font-semibold text-tide-deep">
          Step {position} of {steps.length}
        </p>
      )}
      <form
        key={step}
        onSubmit={step === "confirm" ? confirm : (e) => (e.preventDefault(), next())}
        noValidate
        className="mt-2 flex flex-col motion-safe:animate-step-in"
      >
        <h1 ref={headingRef} tabIndex={-1} className="font-display text-3xl leading-tight focus:outline-none">
          {heading}
        </h1>

        {step === "provider" && (
          <fieldset className="mt-6">
            <legend className="sr-only">Provider</legend>
            {!providers && !error && <p className="text-lg text-navy/80">Loading providers.</p>}
            <div className="space-y-3">
              {providers?.map((p) => (
                <div key={p.id}>
                  <input
                    id={`prov-${p.id}`}
                    type="radio"
                    name="provider"
                    checked={providerId === p.id}
                    onChange={() => pickProvider(p)}
                    className="peer sr-only"
                  />
                  <label htmlFor={`prov-${p.id}`} className={choiceCard}>
                    <span className="font-semibold">{p.name}</span>
                    <span>{p.specialty}</span>
                    <span className="text-base opacity-90">
                      {p.modes.length === 2 ? "In person or video" : modeLabel(p.modes[0])}
                      {p.kind === kind ? " · Suggested for you" : ""}
                    </span>
                  </label>
                </div>
              ))}
            </div>
            {provider?.bio && <p className="mt-4 text-base text-navy/80">{provider.bio}</p>}
            <p className="mt-4 text-base text-navy/80">
              These providers are made up for the demo. Real clinics will replace them.
            </p>
          </fieldset>
        )}

        {step === "mode" && provider && (
          <fieldset className="mt-6">
            <legend className="sr-only">Visit type</legend>
            <div className="space-y-3">
              {provider.modes.map((m) => (
                <div key={m}>
                  <input
                    id={`mode-${m}`}
                    type="radio"
                    name="mode"
                    checked={mode === m}
                    onChange={() => {
                      setMode(m);
                      setSlot("");
                    }}
                    className="peer sr-only"
                  />
                  <label htmlFor={`mode-${m}`} className={choiceCard}>
                    <span className="flex items-center gap-2 font-semibold">
                      {m === "virtual" ? <VideoIcon className="size-6" /> : <PinIcon className="size-6" />}
                      {modeLabel(m)}
                    </span>
                    <span className="text-base">
                      {m === "virtual"
                        ? "Talk by video from home. You only need a phone or computer."
                        : `${provider.clinic ?? ""}${provider.address ? `, ${provider.address}` : ""}`}
                    </span>
                  </label>
                </div>
              ))}
            </div>
          </fieldset>
        )}

        {step === "time" && (
          <div className="mt-6 space-y-6">
            <p className="text-base text-navy/80">Times are in Eastern time.</p>
            {slots === null && !error && <p className="text-lg text-navy/80">Looking for open times.</p>}
            {slots?.length === 0 && !error && (
              <p className="rounded-2xl bg-sand/70 p-4 text-lg">
                No times are open in this window.
                {urgency !== "routine" && (
                  <>
                    {" "}
                    <button
                      type="button"
                      onClick={() => setUrgency("routine")}
                      className={`rounded font-semibold underline underline-offset-2 ${focusRing}`}
                    >
                      Show later times
                    </button>
                  </>
                )}
              </p>
            )}
            {slots && groupByDay(slots).map((g) => (
              <fieldset key={g.day}>
                <legend className="text-lg font-semibold">{g.day}</legend>
                <div className="mt-3 grid grid-cols-2 gap-3">
                  {g.slots.map((s) => (
                    <div key={s}>
                      <input
                        id={`slot-${s}`}
                        type="radio"
                        name="slot"
                        checked={slot === s}
                        onChange={() => setSlot(s)}
                        className="peer sr-only"
                      />
                      <label htmlFor={`slot-${s}`} className={`${choiceCard} items-center justify-center`}>
                        {timeLabel(s)}
                      </label>
                    </div>
                  ))}
                </div>
              </fieldset>
            ))}
            {slots && slots.length > 0 && urgency !== "routine" && (
              <button
                type="button"
                onClick={() => setUrgency("routine")}
                className={`rounded text-lg font-semibold underline underline-offset-4 ${focusRing}`}
              >
                Show later times
              </button>
            )}
          </div>
        )}

        {step === "confirm" && provider && mode && (
          <div className="mt-6">
            <dl className="divide-y divide-navy/10 rounded-3xl bg-sand/70 px-5 text-lg">
              <Row term="With" value={`${provider.name}, ${provider.specialty}`} />
              <Row term="When" value={whenLabel(slot)} />
              <Row
                term="Where"
                value={
                  mode === "virtual"
                    ? "Video visit. You join from Your visits, under Care."
                    : `${provider.clinic ?? ""}${provider.address ? `, ${provider.address}` : ""}`
                }
              />
            </dl>
            <label htmlFor="reason" className="mt-6 block text-lg font-semibold">
              What would you like to talk about?
            </label>
            <textarea
              id="reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              maxLength={500}
              rows={3}
              className={`mt-2 w-full rounded-2xl border-2 border-navy bg-white px-4 py-3 text-lg ${focusRing}`}
            />
          </div>
        )}

        {step === "done" && visit && (
          <div className="mt-6">
            <p className="flex items-center gap-2 text-lg font-semibold text-tide-deep">
              {visit.mode === "virtual" ? <VideoIcon className="size-6" /> : <PinIcon className="size-6" />}
              {modeLabel(visit.mode)}
            </p>
            <p className="mt-2 font-display text-2xl">{visit.provider.name}</p>
            <p className="mt-1 text-xl">{dayLabel(visit.slot)}</p>
            <p className="text-xl font-semibold">{timeLabel(visit.slot, true)}</p>
            <p className="mt-4 max-w-[40ch] text-lg leading-relaxed">
              {visit.mode === "virtual"
                ? "Open Your visits (under Care) and tap Join video visit. The room opens 15 minutes before."
                : `${visit.provider.clinic ?? ""}${visit.provider.address ? `, ${visit.provider.address}` : ""}. Bring your home blood pressure readings if you have them.`}
            </p>
          </div>
        )}

        {error && (
          <p role="alert" className="mt-5 rounded-2xl bg-white p-4 text-lg text-alert ring-2 ring-alert/30">
            {error}
          </p>
        )}

        <div className="mt-8 flex flex-col gap-3">
          {step === "done" ? (
            <>
              <Link href="/visits" className={btnPrimary}>
                See my visits
              </Link>
              {visit && (
                <button type="button" onClick={() => downloadIcs(visit)} className={`${btnOutline} gap-2`}>
                  <CalendarIcon className="size-6" />
                  Add to calendar
                </button>
              )}
            </>
          ) : (
            <>
              <button type="submit" aria-disabled={saving} className={btnPrimary}>
                {step === "confirm" ? (saving ? "Booking" : "Book this visit") : "Continue"}
              </button>
              {step === "provider" ? (
                <button type="button" onClick={leave} className={btnOutline}>
                  Back
                </button>
              ) : (
                <button type="button" onClick={back} className={btnOutline}>
                  Back
                </button>
              )}
            </>
          )}
        </div>
      </form>
    </div>
  );
}

function Row({ term, value }: { term: string; value: string }) {
  return (
    <div className="py-4">
      <dt className="text-base text-navy/80">{term}</dt>
      <dd className="mt-0.5 font-semibold">{value}</dd>
    </div>
  );
}
