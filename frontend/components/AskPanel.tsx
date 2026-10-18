"use client";

import { useRef, useState } from "react";
import UrgentCard from "@/components/UrgentCard";
import { ApiError, ask } from "@/lib/api";
import { usePatientId } from "@/lib/session";
import type { AskResult, RedFlagLevel } from "@/lib/types";
import { btnPrimary, focusRing } from "@/lib/ui";

// Ask Tidewell: the Care Navigator agent. It can look at your tide, search trusted guidance
// (CDC, NIH, WHO, ACOG...) and the care team's suggestions, then answers with its sources.

type Turn = { q: string; a?: AskResult; error?: string };

const STARTERS = [
  "Is my blood pressure something to worry about?",
  "How much bleeding is normal at this stage?",
  "Can I take ibuprofen while breastfeeding?",
  "Why am I so tired, and what helps?",
];

export default function AskPanel() {
  const patientId = usePatientId();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [urgent, setUrgent] = useState<RedFlagLevel | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  async function send(question: string) {
    const text = question.trim();
    if (!text || busy || !patientId) return;
    setQ("");
    setBusy(true);
    setTurns((t) => [...t, { q: text }]);
    try {
      const a = await ask(patientId, text);
      if (a.red_flag && a.red_flag_level) setUrgent(a.red_flag_level);
      setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { ...x, a } : x)));
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "We couldn't reach Tidewell. Try again.";
      setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { ...x, error: msg } : x)));
    } finally {
      setBusy(false);
      requestAnimationFrame(() => endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }));
    }
  }

  if (urgent) return <UrgentCard level={urgent} />;

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col">
      <h1 className="font-display text-4xl leading-tight">Ask Tidewell</h1>
      <p className="mt-3 max-w-[48ch] text-lg leading-relaxed text-navy/85">
        Questions about recovery, feeding, mood or your numbers. Answers come from trusted sources like
        the CDC and NIH, and say where they came from. Tidewell does not diagnose.
      </p>

      <div aria-live="polite" className="mt-8 space-y-6">
        {turns.length === 0 && (
          <ul className="grid gap-3 sm:grid-cols-2" aria-label="Example questions">
            {STARTERS.map((s) => (
              <li key={s}>
                <button
                  type="button"
                  onClick={() => send(s)}
                  className={`w-full rounded-2xl bg-white p-4 text-left text-lg ring-1 ring-navy/10 transition-[background-color,transform] duration-150 ease-out hover:bg-sand/60 motion-safe:active:scale-[0.98] ${focusRing}`}
                >
                  {s}
                </button>
              </li>
            ))}
          </ul>
        )}
        {turns.map((t, i) => (
          <div key={i} className="space-y-3">
            <p className="ml-auto w-fit max-w-[85%] rounded-3xl rounded-br-lg bg-tide-deep px-5 py-3 text-lg text-white motion-safe:animate-reply-in">
              {t.q}
            </p>
            {t.a && (
              <div className="max-w-[92%] rounded-3xl rounded-bl-lg bg-sand/70 p-5 motion-safe:animate-reply-in">
                <p className="text-lg leading-relaxed">{t.a.answer}</p>
                {t.a.citations.length > 0 && (
                  <p className="mt-3 text-base text-navy/80">
                    Sources:{" "}
                    {t.a.citations.map((c, j) => (
                      <span key={c.url}>
                        {j > 0 && ", "}
                        <a href={c.url} target="_blank" rel="noreferrer" className={`rounded font-semibold underline underline-offset-2 ${focusRing}`}>
                          {c.title}
                        </a>
                      </span>
                    ))}
                  </p>
                )}
                {t.a.tools_called.length > 0 && (
                  <p className="mt-2 text-sm text-navy/70">Checked: {[...new Set(t.a.tools_called)].map((x) => x.replace(/_/g, " ")).join(", ")}</p>
                )}
              </div>
            )}
            {t.error && <p role="alert" className="rounded-2xl bg-white p-4 text-lg text-alert ring-2 ring-alert/30">{t.error}</p>}
          </div>
        ))}
        {busy && (
          <p role="status" className="flex items-center gap-3 text-lg text-navy/80">
            <span className="flex gap-1" aria-hidden="true">
              {[0, 1, 2].map((d) => (
                <span key={d} className="size-2 rounded-full bg-tide-deep motion-safe:animate-pulse" style={{ animationDelay: `${d * 150}ms` }} />
              ))}
            </span>
            Looking that up…
          </p>
        )}
        <div ref={endRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(q);
        }}
        className="sticky bottom-24 mt-8 flex gap-3 rounded-3xl bg-foam/95 py-3 backdrop-blur"
      >
        <label htmlFor="ask-q" className="sr-only">Your question</label>
        <input
          id="ask-q"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Type your question"
          maxLength={1000}
          className={`min-h-14 flex-1 rounded-full border-2 border-navy bg-white px-5 text-lg ${focusRing}`}
        />
        <button type="submit" aria-disabled={busy || !q.trim()} className={btnPrimary}>
          Ask
        </button>
      </form>
    </div>
  );
}
