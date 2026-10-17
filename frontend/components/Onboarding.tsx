"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ApiError, onboard } from "@/lib/api";
import {
  COMPLICATIONS,
  CONSENT_TEXT,
  DELIVERY,
  FEEDING,
  LANGUAGES,
  digits,
  profileProblem,
  toE164,
  todayIso,
  yearAgoIso,
} from "@/lib/profile";
import { setOwnPatient, useSession } from "@/lib/session";
import type { DeliveryType, FeedingType, Language, Profile } from "@/lib/types";
import { btnOutline, btnPrimary, focusRing } from "@/lib/ui";

// One question per screen, in plain words. Consent comes first, before any health question.
// Everything here becomes the baseline profile (backend Profile), editable later in Settings.

const STEPS = [
  "Before we start",
  "A little about you",
  "When was your baby born?",
  "How many weeks pregnant were you?",
  "How did you give birth?",
  "How are you feeding your baby?",
  "Have you ever had depression or anxiety?",
  "Did any of these happen in your pregnancy?",
  "Who should we tell if you need urgent care?",
  "Ready to start",
] as const;
const TOTAL = STEPS.length;

export const choice =
  "flex min-h-14 cursor-pointer items-center gap-3 rounded-2xl border-2 border-navy/25 bg-white px-4 py-3 text-lg transition-colors duration-150 peer-checked:border-tide-deep peer-checked:bg-tide-deep peer-checked:text-white peer-focus-visible:ring-4 peer-focus-visible:ring-navy peer-focus-visible:ring-offset-2 peer-focus-visible:ring-offset-foam";
const field = `mt-3 min-h-14 w-full rounded-2xl border-2 border-navy bg-white px-4 text-lg ${focusRing}`;

export default function Onboarding() {
  const router = useRouter();
  const { session, ready } = useSession();
  const [step, setStep] = useState(0);
  const [direction, setDirection] = useState<1 | -1>(1);
  const [consent, setConsent] = useState(false);
  const [name, setName] = useState("");
  const [deliveryDate, setDeliveryDate] = useState("");
  const [weeks, setWeeks] = useState("");
  const [method, setMethod] = useState<DeliveryType | "">("");
  const [feeding, setFeeding] = useState<FeedingType | "">("");
  const [mental, setMental] = useState<"yes" | "no" | "">("");
  const [complications, setComplications] = useState<string[]>([]);
  const [language, setLanguage] = useState<Language>("en");
  const [supportName, setSupportName] = useState("");
  const [phone, setPhone] = useState("");
  const [smsConsent, setSmsConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const firstRender = useRef(true);

  // Onboarding saves to your account, so it needs one. The demo has its own fixed profile.
  useEffect(() => {
    if (ready && session?.kind !== "user") router.replace("/register");
  }, [ready, session, router]);

  // After each step change, move focus to the new heading so screen readers start there.
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    headingRef.current?.focus();
  }, [step]);

  const profile: Profile = {
    consent_granted: consent,
    delivery_date: deliveryDate,
    gestation_weeks: weeks ? Number(weeks) : null,
    delivery_method: method as DeliveryType,
    feeding_type: feeding as FeedingType,
    history_mental_health: mental === "yes",
    history_pregnancy_complications: complications,
    language_preference: language,
    support_person_name: supportName.trim() || null,
    support_person_phone: toE164(phone),
    support_sms_consent: Boolean(phone.trim() && smsConsent),
    name: name.trim() || null,
  };

  function validate(): string | null {
    switch (step) {
      case 0:
        return consent ? null : "Tick the box to continue. Tidewell can't keep your check-ins without your permission.";
      case 2:
        if (!deliveryDate) return "Choose the date your baby was born.";
        if (deliveryDate > todayIso()) return "That date is in the future. Choose the day your baby was born.";
        if (deliveryDate < yearAgoIso()) return "Tidewell is for the first year after birth. Choose a date in the last 12 months.";
        return null;
      case 3:
        if (!weeks) return null; // optional
        return Number(weeks) >= 20 && Number(weeks) <= 45 ? null : "Enter a number of weeks between 20 and 45, or leave it blank.";
      case 4:
        return method ? null : "Choose how you gave birth.";
      case 5:
        return feeding ? null : "Choose how you are feeding your baby.";
      case 6:
        return mental ? null : "Choose yes or no. Either answer is okay.";
      case 8:
        if (!phone.trim()) return null;
        if (digits(phone).length < 10) return "Enter the full phone number, including area code.";
        if (!supportName.trim()) return "Add their first name.";
        if (!smsConsent) return "Tick the box to say it is okay to text this person, or clear the number to skip.";
        return null;
      case 9:
        return profileProblem(profile, phone);
      default:
        return null;
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (saving) return;
    const problem = validate();
    setError(problem);
    if (problem) return;
    if (step < TOTAL - 1) {
      setDirection(1);
      setStep(step + 1);
      return;
    }
    setSaving(true);
    try {
      const res = await onboard(profile);
      setOwnPatient(res.patient_id);
      router.push("/home");
    } catch (err) {
      setError(
        err instanceof ApiError && err.status !== 401
          ? `We couldn't save your answers: ${err.message}`
          : "We couldn't save your answers. Check your connection and try again."
      );
      setSaving(false);
    }
  }

  function back() {
    setError(null);
    setDirection(-1);
    setStep((s) => Math.max(0, s - 1));
  }

  const skippable = (step === 3 && !weeks) || (step === 7 && !complications.length) || (step === 8 && !phone.trim());

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-md flex-col px-5 pb-10">
      <header className="flex h-16 items-center justify-between">
        <Link href="/" className={`rounded-md font-display text-2xl text-tide-deep ${focusRing}`}>
          Tidewell
        </Link>
        <p className="text-base font-semibold">
          Step {step + 1} of {TOTAL}
        </p>
      </header>
      <div aria-hidden="true" className="h-2 overflow-hidden rounded-full bg-navy/10">
        <div
          className="h-full origin-left rounded-full bg-tide-deep transition-transform duration-300 ease-out"
          style={{ transform: `scaleX(${(step + 1) / TOTAL})` }}
        />
      </div>

      <main id="main" className="flex flex-1 flex-col">
        <form
          key={step}
          onSubmit={onSubmit}
          noValidate
          className={`mt-8 flex flex-1 flex-col ${direction < 0 ? "motion-safe:animate-step-back" : "motion-safe:animate-step-in"} motion-reduce:animate-fade-in`}
        >
          <h1 ref={headingRef} tabIndex={-1} className="font-display text-3xl leading-tight focus:outline-none">
            {STEPS[step]}
          </h1>

          <div className="mt-6 flex-1">
            {step === 0 && (
              <div className="space-y-5">
                <p className="text-lg leading-relaxed">
                  A few questions help Tidewell look out for you. It takes about two minutes. Tidewell is
                  not a doctor and does not diagnose. If something feels like an emergency, call 911.
                </p>
                <div>
                  <input id="consent" type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="peer sr-only" />
                  <label htmlFor="consent" className={`${choice} items-start`}>
                    {CONSENT_TEXT}
                  </label>
                </div>
              </div>
            )}

            {step === 1 && (
              <div>
                <label htmlFor="name" className="text-lg font-semibold">
                  First name or nickname <span className="font-normal text-navy/80">(optional)</span>
                </label>
                <input id="name" value={name} onChange={(e) => setName(e.target.value)} autoComplete="given-name" maxLength={80} className={field} />
                <fieldset className="mt-8">
                  <legend className="text-lg font-semibold">Language for your check-ins</legend>
                  <div className="mt-3 grid grid-cols-2 gap-3">
                    {LANGUAGES.map((l) => (
                      <div key={l.value}>
                        <input id={`lang-${l.value}`} type="radio" name="language" value={l.value} checked={language === l.value} onChange={() => setLanguage(l.value)} className="peer sr-only" />
                        <label htmlFor={`lang-${l.value}`} className={`${choice} justify-center`} lang={l.value}>
                          {l.label}
                        </label>
                      </div>
                    ))}
                  </div>
                </fieldset>
              </div>
            )}

            {step === 2 && (
              <div>
                <label htmlFor="birth" className="text-lg font-semibold">
                  Date of birth
                </label>
                <p id="birth-hint" className="mt-1 text-base text-navy/80">
                  We use this to know how far along your recovery is.
                </p>
                <input id="birth" type="date" value={deliveryDate} min={yearAgoIso()} max={todayIso()} onChange={(e) => setDeliveryDate(e.target.value)} aria-describedby="birth-hint" aria-invalid={error ? true : undefined} className={field} />
              </div>
            )}

            {step === 3 && (
              <div>
                <label htmlFor="weeks" className="text-lg font-semibold">
                  Weeks of pregnancy at birth <span className="font-normal text-navy/80">(optional)</span>
                </label>
                <p id="weeks-hint" className="mt-1 text-base text-navy/80">
                  A full-term pregnancy is about 39 to 40 weeks. Skip this if you are not sure.
                </p>
                <input id="weeks" type="number" inputMode="numeric" min={20} max={45} value={weeks} onChange={(e) => setWeeks(e.target.value)} aria-describedby="weeks-hint" aria-invalid={error ? true : undefined} className={field} />
              </div>
            )}

            {step === 4 && (
              <Choices legend="How did you give birth?" name="delivery" value={method} onChange={(v) => setMethod(v as DeliveryType)} options={DELIVERY} />
            )}

            {step === 5 && (
              <Choices legend="How are you feeding your baby?" name="feeding" value={feeding} onChange={(v) => setFeeding(v as FeedingType)} options={FEEDING} />
            )}

            {step === 6 && (
              <div className="space-y-4">
                <p className="text-lg leading-relaxed">
                  Before or during pregnancy. This helps Tidewell check in on your mood more carefully. It
                  stays private.
                </p>
                <Choices legend="Have you ever had depression or anxiety?" name="mental" value={mental} onChange={(v) => setMental(v as "yes" | "no")} options={[{ value: "yes", label: "Yes" }, { value: "no", label: "No" }]} />
              </div>
            )}

            {step === 7 && (
              <fieldset>
                <legend className="text-lg font-semibold">Pick any that apply, or none.</legend>
                <div className="mt-3 space-y-3">
                  {COMPLICATIONS.map((c) => (
                    <div key={c.value}>
                      <input
                        id={`cond-${c.value}`}
                        type="checkbox"
                        checked={complications.includes(c.value)}
                        onChange={(e) =>
                          setComplications((prev) => (e.target.checked ? [...prev, c.value] : prev.filter((v) => v !== c.value)))
                        }
                        className="peer sr-only"
                      />
                      <label htmlFor={`cond-${c.value}`} className={choice}>
                        {c.label}
                      </label>
                    </div>
                  ))}
                </div>
              </fieldset>
            )}

            {step === 8 && (
              <div>
                <p className="text-lg leading-relaxed">
                  Pick someone you trust: a partner, a parent, a friend. This is optional, and you can skip it.
                </p>
                <label htmlFor="sname" className="mt-6 block text-lg font-semibold">
                  Their first name
                </label>
                <input id="sname" value={supportName} onChange={(e) => setSupportName(e.target.value)} maxLength={80} autoComplete="off" className={field} />
                <label htmlFor="phone" className="mt-5 block text-lg font-semibold">
                  Their phone number
                </label>
                <input id="phone" type="tel" inputMode="tel" autoComplete="off" value={phone} onChange={(e) => setPhone(e.target.value)} aria-invalid={error ? true : undefined} className={field} />
                {phone.trim() && (
                  <div className="mt-5">
                    <input id="sms" type="checkbox" checked={smsConsent} onChange={(e) => setSmsConsent(e.target.checked)} className="peer sr-only" />
                    <label htmlFor="sms" className={`${choice} items-start`}>
                      It is okay for Tidewell to text this person if my check-ins show I need emergency care.
                    </label>
                  </div>
                )}
              </div>
            )}

            {step === 9 && (
              <dl className="divide-y divide-navy/10 rounded-3xl bg-sand/70 px-5 text-lg">
                <Row term="Name" value={name.trim() || "Not given"} />
                <Row term="Baby born" value={deliveryDate ? new Date(`${deliveryDate}T00:00:00`).toLocaleDateString("en-US", { dateStyle: "long" }) : ""} />
                <Row term="Weeks of pregnancy" value={weeks || "Not given"} />
                <Row term="Birth" value={DELIVERY.find((d) => d.value === method)?.label ?? ""} />
                <Row term="Feeding" value={FEEDING.find((f) => f.value === feeding)?.label ?? ""} />
                <Row term="Depression or anxiety before" value={mental === "yes" ? "Yes" : "No"} />
                <Row term="Pregnancy" value={complications.length ? COMPLICATIONS.filter((c) => complications.includes(c.value)).map((c) => c.label).join("; ") : "Nothing to flag"} />
                <Row term="Urgent contact" value={phone.trim() ? `${supportName.trim()}, ${phone.trim()}` : "None"} />
                <Row term="Language" value={LANGUAGES.find((l) => l.value === language)?.label ?? ""} />
              </dl>
            )}

            {error && (
              <p role="alert" className="mt-5 rounded-2xl bg-white p-4 text-lg text-alert ring-2 ring-alert/30">
                {error}
              </p>
            )}
          </div>

          <div className="mt-8 flex flex-col gap-3">
            <button type="submit" aria-disabled={saving} className={btnPrimary}>
              {step === TOTAL - 1 ? (saving ? "Saving" : "Start my first check-in") : skippable ? "Skip this step" : "Continue"}
            </button>
            {step > 0 && (
              <button type="button" onClick={back} className={btnOutline}>
                Back
              </button>
            )}
          </div>
        </form>
      </main>
    </div>
  );
}

export function Choices({
  legend,
  name,
  value,
  onChange,
  options,
}: {
  legend: string;
  name: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string; hint?: string }[];
}) {
  return (
    <fieldset>
      <legend className="sr-only">{legend}</legend>
      <div className="space-y-3">
        {options.map((o) => (
          <div key={o.value}>
            <input id={`${name}-${o.value}`} type="radio" name={name} value={o.value} checked={value === o.value} onChange={() => onChange(o.value)} className="peer sr-only" />
            <label htmlFor={`${name}-${o.value}`} className={`${choice} justify-between`}>
              <span>{o.label}</span>
              {o.hint && <span className="text-base opacity-80">{o.hint}</span>}
            </label>
          </div>
        ))}
      </div>
    </fieldset>
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
