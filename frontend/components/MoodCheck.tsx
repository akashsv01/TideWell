"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import BackLink from "@/components/BackLink";
import UrgentCard from "@/components/UrgentCard";
import { epdsFollowup, getEpdsQuestions, getTodaysEpds, submitEpds } from "@/lib/api";
import { usePatientId } from "@/lib/session";
import type { EpdsQuestions, EpdsResult, RedFlagLevel } from "@/lib/types";
import { btnOutline, btnPrimary, focusRing } from "@/lib/ui";

// Weekly mood check (EPDS). One question per screen; tapping an answer moves on. Scoring and the
// question 10 safety rule run on the backend (app/epds.py). This never diagnoses.

type Phase = "questions" | "sending" | "followup" | "done" | "error";

const BAND_TEXT: Record<EpdsResult["band"], string> = {
  low: "Your answers this week don't point to anything that needs action. Keep checking in.",
  watch: "Your answers suggest this week has been hard. It is worth mentioning to your care team at your next visit, and Tidewell will check in on your mood again soon.",
  amber: "Your answers suggest you may be struggling. Please talk to your doctor, midwife or care team soon. Support helps, and you don't have to wait for your next visit.",
};

export default function MoodCheck() {
  const patientId = usePatientId();
  const [qs, setQs] = useState<EpdsQuestions | null>(null);
  const [answers, setAnswers] = useState<number[]>([]);
  const [i, setI] = useState(0);
  const [phase, setPhase] = useState<Phase>("questions");
  const [result, setResult] = useState<EpdsResult | null>(null);
  const [urgent, setUrgent] = useState<RedFlagLevel | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);

  const [editing, setEditing] = useState(false);

  useEffect(() => {
    getEpdsQuestions().then(setQs, () => setPhase("error"));
  }, []);

  // Taken today already? Reopen with those answers selected, so they can be changed.
  useEffect(() => {
    if (!patientId) return;
    getTodaysEpds(patientId).then(
      (t) => {
        if (t.taken && t.answers?.length === 10) {
          setAnswers(t.answers);
          setEditing(true);
        }
      },
      () => {}
    );
  }, [patientId]);

  useEffect(() => {
    headingRef.current?.focus();
  }, [i, phase]);

  async function choose(option: number) {
    if (!qs || !patientId || phase !== "questions") return;
    const next = [...answers.slice(0, i), option];
    setAnswers(next);
    if (i < qs.questions.length - 1) {
      setI(i + 1);
      return;
    }
    setPhase("sending");
    try {
      const r = await submitEpds(patientId, next);
      setResult(r);
      if (r.level === "emergency") setUrgent("emergency");
      else if (r.needs_followup) setPhase("followup");
      else setPhase("done");
    } catch {
      setPhase("error");
    }
  }

  async function answerFollowup(answer: "yes" | "no" | "unsure") {
    if (!patientId) return;
    try {
      const r = await epdsFollowup(patientId, answer);
      setUrgent(r.level);
    } catch {
      setUrgent("emergency"); // if we can't tell, show the emergency resources
    }
  }

  if (urgent) return <UrgentCard level={urgent} onBack={() => { setUrgent(null); if (result) setPhase("done"); }} />;

  if (phase === "error") {
    return (
      <p role="alert" className="rounded-2xl bg-white p-5 text-lg text-alert ring-2 ring-alert/30">
        We couldn&apos;t load the mood check. Check your connection and try again.
      </p>
    );
  }
  if (!qs) return <p role="status" className="py-16 text-center text-xl">Loading…</p>;

  if (phase === "followup") {
    return (
      <section className="w-full max-w-xl motion-safe:animate-reply-in">
        <h1 ref={headingRef} tabIndex={-1} className="font-display text-4xl font-semibold leading-tight focus:outline-none">
          One more question
        </h1>
        <p className="mt-4 text-xl leading-relaxed">{qs.followup_question}</p>
        <div className="mt-6 flex flex-col gap-3">
          <button type="button" onClick={() => answerFollowup("yes")} className={btnOutline}>Yes</button>
          <button type="button" onClick={() => answerFollowup("unsure")} className={btnOutline}>I&apos;m not sure</button>
          <button type="button" onClick={() => answerFollowup("no")} className={btnOutline}>No</button>
        </div>
      </section>
    );
  }

  if (phase === "done" && result) {
    return (
      <section className="w-full max-w-xl motion-safe:animate-reply-in">
        <BackLink href="/home">Check in</BackLink>
        <h1 ref={headingRef} tabIndex={-1} className="mt-4 font-display text-4xl font-semibold leading-tight focus:outline-none">
          Thank you for checking in
        </h1>
        <div className="mt-6 rounded-2xl bg-white p-6 shadow-paper ring-1 ring-navy/10">
          <p className={result.band === "low" ? "text-xl" : "font-display text-2xl font-semibold leading-snug"}>
            Your score this week is <span className="tabular-nums">{result.score} out of 30</span>.
          </p>
          <p className="mt-1 text-base text-navy/80">Lower is better. 10 or more is worth raising with your care team.</p>
          <p className="mt-4 text-lg leading-relaxed">{BAND_TEXT[result.band]}</p>
        </div>
        <p className="mt-4 text-base text-navy/80">
          This is a screening check, not a diagnosis. You can see your weekly scores on My tide.
        </p>
        <div className="mt-6 flex flex-col gap-3">
          <Link href="/dashboard" className={btnPrimary}>See my tide</Link>
          <Link href="/home" className={btnOutline}>Back to check-in</Link>
        </div>
        <p className="mt-8 text-sm text-navy/70">{qs.citation}</p>
      </section>
    );
  }

  const q = qs.questions[i];
  const sending = phase === "sending";
  return (
    <section className="w-full">
      <div className="flex items-center justify-between gap-4">
        <BackLink href="/home">Check in</BackLink>
        <p className="text-base text-navy/80">
          Weekly mood check, question {i + 1} of {qs.questions.length}
        </p>
      </div>
      <div aria-hidden="true" className="mt-2 h-2 overflow-hidden rounded-full bg-navy/10">
        <div
          className="h-full origin-left rounded-full bg-tide-deep transition-transform duration-300 ease-out"
          style={{ transform: `scaleX(${(i + 1) / qs.questions.length})` }}
        />
      </div>
      <div key={i} className="max-w-xl motion-safe:animate-step-in motion-reduce:animate-fade-in">
        {editing && i === 0 && (
          <p className="mt-6 rounded-xl bg-sand/60 p-3 text-base">You already did today&apos;s check. Your answers are selected; change any of them.</p>
        )}
        <p className="mt-6 text-lg text-navy/85">In the past 7 days:</p>
        <h1 ref={headingRef} tabIndex={-1} className="mt-1 font-display text-3xl font-semibold leading-tight focus:outline-none">
          {q.text}
        </h1>
        <div role="group" aria-label="Choose one answer" className="mt-6 flex flex-col gap-3">
          {q.options.map((o, idx) => (
            <button
              key={o}
              type="button"
              onClick={() => choose(idx)}
              aria-pressed={answers[i] === idx}
              aria-disabled={sending}
              className={`min-h-14 rounded-2xl border-2 px-4 py-3 text-left text-lg transition-[background-color,border-color,color,transform] duration-150 ease-out motion-safe:active:scale-[0.98] ${
                answers[i] === idx ? "border-tide-deep bg-tide-deep text-white" : "border-navy/25 bg-white hover:border-navy/60"
              } ${focusRing}`}
            >
              {o}
            </button>
          ))}
        </div>
      </div>
      <div className="mt-6 flex items-center justify-between">
        {i > 0 ? (
          <button type="button" onClick={() => setI(i - 1)} className={`rounded-md py-2 text-lg font-semibold underline underline-offset-4 ${focusRing}`}>
            Back
          </button>
        ) : (
          <Link href="/home" className={`rounded-md py-2 text-lg font-semibold underline underline-offset-4 ${focusRing}`}>
            Not now
          </Link>
        )}
        {sending && <p role="status" className="text-lg">Saving…</p>}
      </div>
    </section>
  );
}
