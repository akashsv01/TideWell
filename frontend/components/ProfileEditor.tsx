"use client";

import { useEffect, useId, useState } from "react";
import { Choices, choice } from "@/components/Onboarding";
import { ApiError, getProfile, updateProfile } from "@/lib/api";
import { COMPLICATIONS, DELIVERY, FEEDING, LANGUAGES, fromE164, profileProblem, toE164, todayIso, yearAgoIso } from "@/lib/profile";
import type { DeliveryType, FeedingType, Language, Profile, ProfileOut } from "@/lib/types";
import { btnPrimary, focusRing } from "@/lib/ui";

// "Your details" in Settings: the onboarding answers, all on one page, saved with PUT /profile.
// For the demo it shows Maya's details read-only.

const field = `mt-2 min-h-14 w-full rounded-2xl border-2 border-navy bg-white px-4 text-lg ${focusRing}`;
type SaveState = "idle" | "saving" | "saved" | "error";

export default function ProfileEditor({ patientId, demo }: { patientId: string; demo: boolean }) {
  const ids = useId();
  const [loaded, setLoaded] = useState<ProfileOut | null>(null);
  const [failed, setFailed] = useState(false);
  const [p, setP] = useState<Profile | null>(null);
  const [phone, setPhone] = useState("");
  const [state, setState] = useState<SaveState>("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getProfile(demo ? patientId : undefined).then(
      (prof) => {
        if (cancelled) return;
        setLoaded(prof);
        setP(prof);
        setPhone(fromE164(prof.support_person_phone));
      },
      () => {
        if (!cancelled) setFailed(true);
      }
    );
    return () => {
      cancelled = true;
    };
  }, [patientId, demo]);

  if (failed) {
    return <p role="alert" className="text-lg text-alert">We couldn&apos;t load your details. Refresh to try again.</p>;
  }
  if (!p || !loaded) {
    return <p role="status" className="text-lg">Loading your details…</p>;
  }

  const set = <K extends keyof Profile>(k: K, v: Profile[K]) => {
    setP({ ...p, [k]: v });
    setState("idle");
  };

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!p || state === "saving") return;
    const problem = profileProblem(p, phone);
    setError(problem);
    if (problem) return;
    setState("saving");
    try {
      const next: Profile = {
        ...p,
        support_person_phone: toE164(phone),
        support_sms_consent: Boolean(phone.trim() && p.support_sms_consent),
      };
      const saved = await updateProfile(next);
      setLoaded(saved);
      setP(saved);
      setState("saved");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "We couldn't save. Check your connection and try again.");
      setState("error");
    }
  }

  return (
    <form onSubmit={save} noValidate className="space-y-7">
      <p className="text-lg leading-relaxed">
        Day {loaded.day_postpartum} after giving birth.{" "}
        {demo ? "These are Maya's details. Create your own account to change them." : "Change anything that is out of date."}
      </p>
      <fieldset disabled={demo} className="space-y-7 disabled:opacity-80">
        <div>
          <label htmlFor={`${ids}-name`} className="text-lg font-semibold">Name</label>
          <input id={`${ids}-name`} value={p.name ?? ""} onChange={(e) => set("name", e.target.value || null)} maxLength={80} className={field} />
        </div>
        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label htmlFor={`${ids}-date`} className="text-lg font-semibold">Baby&apos;s birth date</label>
            <input id={`${ids}-date`} type="date" min={yearAgoIso()} max={todayIso()} value={p.delivery_date} onChange={(e) => set("delivery_date", e.target.value)} className={field} />
          </div>
          <div>
            <label htmlFor={`${ids}-weeks`} className="text-lg font-semibold">Weeks of pregnancy</label>
            <input id={`${ids}-weeks`} type="number" inputMode="numeric" min={20} max={45} value={p.gestation_weeks ?? ""} onChange={(e) => set("gestation_weeks", e.target.value ? Number(e.target.value) : null)} className={field} />
          </div>
        </div>
        <Section title="How you gave birth">
          <Choices legend="How you gave birth" name={`${ids}-delivery`} value={p.delivery_method} onChange={(v) => set("delivery_method", v as DeliveryType)} options={DELIVERY} />
        </Section>
        <Section title="Feeding">
          <Choices legend="Feeding" name={`${ids}-feeding`} value={p.feeding_type} onChange={(v) => set("feeding_type", v as FeedingType)} options={FEEDING} />
        </Section>
        <Section title="Ever diagnosed with depression or anxiety">
          <Choices legend="Depression or anxiety" name={`${ids}-mental`} value={p.history_mental_health ? "yes" : "no"} onChange={(v) => set("history_mental_health", v === "yes")} options={[{ value: "yes", label: "Yes" }, { value: "no", label: "No" }]} />
        </Section>
        <Section title="Pregnancy complications">
          <div className="space-y-3">
            {COMPLICATIONS.map((c) => {
              const id = `${ids}-c-${c.value.replace(/\W/g, "")}`;
              const on = p.history_pregnancy_complications.includes(c.value);
              return (
                <div key={c.value}>
                  <input id={id} type="checkbox" checked={on} onChange={(e) => set("history_pregnancy_complications", e.target.checked ? [...p.history_pregnancy_complications, c.value] : p.history_pregnancy_complications.filter((v) => v !== c.value))} className="peer sr-only" />
                  <label htmlFor={id} className={choice}>{c.label}</label>
                </div>
              );
            })}
          </div>
        </Section>
        <Section title="Language">
          <div className="grid grid-cols-2 gap-3">
            {LANGUAGES.map((l) => (
              <div key={l.value}>
                <input id={`${ids}-l-${l.value}`} type="radio" name={`${ids}-lang`} checked={p.language_preference === l.value} onChange={() => set("language_preference", l.value as Language)} className="peer sr-only" />
                <label htmlFor={`${ids}-l-${l.value}`} lang={l.value} className={`${choice} justify-center`}>{l.label}</label>
              </div>
            ))}
          </div>
        </Section>
        <Section title="Support person">
          <div className="grid gap-5 sm:grid-cols-2">
            <div>
              <label htmlFor={`${ids}-sn`} className="text-lg font-semibold">First name</label>
              <input id={`${ids}-sn`} value={p.support_person_name ?? ""} onChange={(e) => set("support_person_name", e.target.value || null)} maxLength={80} className={field} />
            </div>
            <div>
              <label htmlFor={`${ids}-sp`} className="text-lg font-semibold">Phone</label>
              <input id={`${ids}-sp`} type="tel" inputMode="tel" value={phone} onChange={(e) => { setPhone(e.target.value); setState("idle"); }} className={field} />
            </div>
          </div>
          {phone.trim() && (
            <div className="mt-4">
              <input id={`${ids}-sms`} type="checkbox" checked={p.support_sms_consent} onChange={(e) => set("support_sms_consent", e.target.checked)} className="peer sr-only" />
              <label htmlFor={`${ids}-sms`} className={`${choice} items-start`}>
                It is okay for Tidewell to text this person if my check-ins show I need emergency care.
              </label>
            </div>
          )}
        </Section>
      </fieldset>

      {!demo && (
        <div aria-live="polite" className="space-y-4">
          {error && <p role="alert" className="rounded-2xl bg-white p-4 text-lg text-alert ring-2 ring-alert/30">{error}</p>}
          <button type="submit" aria-disabled={state === "saving"} className={btnPrimary}>
            {state === "saving" ? "Saving" : "Save my details"}
          </button>
          {state === "saved" && (
            <p role="status" className="text-lg font-semibold text-tide-deep motion-safe:animate-fade-in">
              Saved. Tidewell will use these from your next check-in.
            </p>
          )}
        </div>
      )}
    </form>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-3 text-lg font-semibold">{title}</p>
      {children}
    </div>
  );
}
