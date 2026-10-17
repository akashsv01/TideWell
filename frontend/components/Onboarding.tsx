"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { onboard } from "@/lib/api";
import { getClerkUserId, setPatientId } from "@/lib/identity";
import type { DeliveryType } from "@/lib/types";
import { btnOutline, btnPrimary, focusRing } from "@/lib/ui";

// Five short steps. Each screen asks one thing, in plain words.
// TODO (Person 4): confirm the condition list, the consent wording and the category keys.

const TOTAL = 5;

const CONDITIONS = [
  { value: "gestational_hypertension", label: "High blood pressure or preeclampsia in pregnancy" },
  { value: "gestational_diabetes", label: "Gestational diabetes" },
  { value: "depression_anxiety", label: "Depression or anxiety, now or in the past" },
];

const todayIso = () => new Date().toISOString().slice(0, 10);
const yearAgoIso = () => {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 1);
  return d.toISOString().slice(0, 10);
};

const digits = (s: string) => s.replace(/\D/g, "");

const choice =
  "flex min-h-14 cursor-pointer items-center gap-3 rounded-2xl border-2 border-navy/25 bg-white px-4 py-3 text-lg transition-colors peer-checked:border-tide-deep peer-checked:bg-tide-deep peer-checked:text-white peer-focus-visible:ring-4 peer-focus-visible:ring-navy peer-focus-visible:ring-offset-2 peer-focus-visible:ring-offset-foam";

export default function Onboarding() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [birthDate, setBirthDate] = useState("");
  const [delivery, setDelivery] = useState<DeliveryType | "">("");
  const [conditions, setConditions] = useState<string[]>([]);
  const [breastfeeding, setBreastfeeding] = useState<"yes" | "no" | "">("");
  const [phone, setPhone] = useState("");
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const firstRender = useRef(true);

  // After each step change, move focus to the new heading so screen readers start there.
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    headingRef.current?.focus();
  }, [step]);

  function validate(): string | null {
    if (step === 0) {
      if (!birthDate) return "Choose the date your baby was born.";
      if (birthDate > todayIso()) return "That date is in the future. Choose the day your baby was born.";
      if (birthDate < yearAgoIso()) return "Tidewell is for the first year after birth. Choose a date in the last 12 months.";
    }
    if (step === 1 && !delivery) return "Choose how you gave birth.";
    if (step === 2 && !breastfeeding) return "Choose yes or no for breastfeeding.";
    if (step === 3 && phone.trim()) {
      if (digits(phone).length < 10) return "Enter the full phone number, including area code.";
      if (!consent) return "Tick the box to say it is okay to text this person, or clear the number to skip.";
    }
    return null;
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const problem = validate();
    setError(problem);
    if (problem) return;
    if (step < TOTAL - 1) {
      setStep(step + 1);
      return;
    }
    setSaving(true);
    try {
      const res = await onboard({
        // No patient_id: the backend creates a new patient (or, when signed in, updates the one
        // linked to this login). Every screen then uses the id it returns.
        clerk_user_id: getClerkUserId(),
        birth_date: birthDate,
        delivery_type: delivery as DeliveryType,
        conditions,
        breastfeeding: breastfeeding === "yes",
        support_phone: phone.trim() ? `+1${digits(phone).slice(-10)}` : null,
        support_consent: Boolean(phone.trim() && consent),
        language: "en",
      });
      setPatientId(res.patient_id);
      router.push("/home");
    } catch {
      setError("We couldn't save your answers. Check your connection and try again.");
      setSaving(false);
    }
  }

  function back() {
    setError(null);
    setStep((s) => Math.max(0, s - 1));
  }

  const heading = [
    "When was your baby born?",
    "How did you give birth?",
    "A few things that help us look out for you",
    "Who should we tell if you need urgent care?",
    "Ready to start",
  ][step];

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
          className="h-full rounded-full bg-tide-deep transition-[width] duration-500 ease-out"
          style={{ width: `${((step + 1) / TOTAL) * 100}%` }}
        />
      </div>

      <main id="main" className="flex flex-1 flex-col">
        <form key={step} onSubmit={onSubmit} noValidate className="mt-8 flex flex-1 flex-col motion-safe:animate-step-in">
          <h1 ref={headingRef} tabIndex={-1} className="font-display text-3xl leading-tight focus:outline-none">
            {heading}
          </h1>

          <div className="mt-6 flex-1">
            {step === 0 && (
              <div>
                <label htmlFor="birth" className="text-lg font-semibold">
                  Date of birth
                </label>
                <p id="birth-hint" className="mt-1 text-base text-navy/80">
                  We use this to know how far along your recovery is.
                </p>
                <input
                  id="birth"
                  type="date"
                  value={birthDate}
                  onChange={(e) => setBirthDate(e.target.value)}
                  aria-describedby="birth-hint"
                  aria-invalid={error ? true : undefined}
                  className={`mt-3 min-h-14 w-full rounded-2xl border-2 border-navy bg-white px-4 text-lg ${focusRing}`}
                />
              </div>
            )}

            {step === 1 && (
              <fieldset>
                <legend className="sr-only">How did you give birth?</legend>
                <div className="space-y-3">
                  {(
                    [
                      ["vaginal", "Vaginal birth"],
                      ["c-section", "C-section"],
                    ] as const
                  ).map(([value, label]) => (
                    <div key={value}>
                      <input
                        id={`delivery-${value}`}
                        type="radio"
                        name="delivery"
                        value={value}
                        checked={delivery === value}
                        onChange={() => setDelivery(value)}
                        className="peer sr-only"
                      />
                      <label htmlFor={`delivery-${value}`} className={choice}>
                        {label}
                      </label>
                    </div>
                  ))}
                </div>
              </fieldset>
            )}

            {step === 2 && (
              <div className="space-y-8">
                <fieldset>
                  <legend className="text-lg font-semibold">Did any of these happen? Pick any that apply, or none.</legend>
                  <div className="mt-3 space-y-3">
                    {CONDITIONS.map((c) => (
                      <div key={c.value}>
                        <input
                          id={`cond-${c.value}`}
                          type="checkbox"
                          checked={conditions.includes(c.value)}
                          onChange={(e) =>
                            setConditions((prev) =>
                              e.target.checked ? [...prev, c.value] : prev.filter((v) => v !== c.value)
                            )
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
                <fieldset>
                  <legend className="text-lg font-semibold">Are you breastfeeding?</legend>
                  <div className="mt-3 grid grid-cols-2 gap-3">
                    {(
                      [
                        ["yes", "Yes"],
                        ["no", "No"],
                      ] as const
                    ).map(([value, label]) => (
                      <div key={value}>
                        <input
                          id={`bf-${value}`}
                          type="radio"
                          name="breastfeeding"
                          value={value}
                          checked={breastfeeding === value}
                          onChange={() => setBreastfeeding(value)}
                          className="peer sr-only"
                        />
                        <label htmlFor={`bf-${value}`} className={`${choice} justify-center`}>
                          {label}
                        </label>
                      </div>
                    ))}
                  </div>
                </fieldset>
              </div>
            )}

            {step === 3 && (
              <div>
                <p className="text-lg leading-relaxed">
                  Pick someone you trust: a partner, a parent, a friend. This is optional, and you can skip it.
                </p>
                <label htmlFor="phone" className="mt-6 block text-lg font-semibold">
                  Their phone number
                </label>
                <input
                  id="phone"
                  type="tel"
                  inputMode="tel"
                  autoComplete="off"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  aria-invalid={error ? true : undefined}
                  className={`mt-2 min-h-14 w-full rounded-2xl border-2 border-navy bg-white px-4 text-lg ${focusRing}`}
                />
                {phone.trim() && (
                  <div className="mt-5">
                    <input
                      id="consent"
                      type="checkbox"
                      checked={consent}
                      onChange={(e) => setConsent(e.target.checked)}
                      className="peer sr-only"
                    />
                    <label htmlFor="consent" className={`${choice} items-start`}>
                      It is okay for Tidewell to text this person if my check-ins show I need urgent care.
                    </label>
                  </div>
                )}
              </div>
            )}

            {step === 4 && (
              <dl className="divide-y divide-navy/10 rounded-3xl bg-sand/70 px-5 text-lg">
                <Row term="Baby born" value={birthDate ? new Date(`${birthDate}T00:00:00`).toLocaleDateString("en-US", { dateStyle: "long" }) : ""} />
                <Row term="Birth" value={delivery === "c-section" ? "C-section" : "Vaginal birth"} />
                <Row
                  term="Pregnancy"
                  value={
                    conditions.length
                      ? CONDITIONS.filter((c) => conditions.includes(c.value)).map((c) => c.label).join("; ")
                      : "Nothing to flag"
                  }
                />
                <Row term="Breastfeeding" value={breastfeeding === "yes" ? "Yes" : "No"} />
                <Row term="Urgent contact" value={phone.trim() ? phone.trim() : "None"} />
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
              {step === TOTAL - 1 ? (saving ? "Saving" : "Start my first check-in") : step === 3 && !phone.trim() ? "Skip this step" : "Continue"}
            </button>
            {step > 0 ? (
              <button type="button" onClick={back} className={btnOutline}>
                Back
              </button>
            ) : (
              <Link href="/" className={btnOutline}>
                Back
              </Link>
            )}
          </div>
        </form>
      </main>
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
