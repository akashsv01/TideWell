"use client";

import { useRef, useState } from "react";
import UrgentCard from "@/components/UrgentCard";
import { ApiError, ask } from "@/lib/api";
import { usePatientId } from "@/lib/session";
import type { AskResult, RedFlagLevel } from "@/lib/types";
import { btnPrimary, focusRing } from "@/lib/ui";

// Ask Tidewell: pregnancy and postpartum questions only (the backend declines anything else).
// Answers come from a web search locked to trusted health sites (CDC, NIH, WHO, ACOG...), with the
// page and the exact passage each answer relies on, or from Tidewell's curated guidelines.

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

  if (urgent) return <UrgentCard level={urgent} onBack={() => setUrgent(null)} />;

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col">
      <h1 className="font-display text-4xl leading-tight">Ask Tidewell</h1>
      <p className="mt-3 max-w-[48ch] text-lg leading-relaxed text-navy/85">
        Questions about pregnancy, recovery, feeding, sleep, mood or your baby. Answers come from trusted
        sources like the CDC, NIH and ACOG, and show where they came from. Tidewell does not diagnose.
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
              <div className={`max-w-[92%] rounded-3xl rounded-bl-lg p-5 motion-safe:animate-reply-in ${t.a.source === "off_topic" ? "bg-white ring-1 ring-navy/15" : "bg-sand/70"}`}>
                <p className="text-lg leading-relaxed">{t.a.answer}</p>
                {t.a.citations.length > 0 && (
                  <div className="mt-4">
                    <p className="text-sm font-semibold uppercase tracking-wide text-navy/70">
                      {t.a.source === "web" ? "From trusted sites" : "From Tidewell's guidelines"}
                    </p>
                    <ol className="mt-2 space-y-2">
                      {t.a.citations.map((c, j) => (
                        <li key={c.url + j}>
                          <a
                            href={c.url}
                            target="_blank"
                            rel="noreferrer"
                            className={`group block rounded-2xl bg-white p-3 ring-1 ring-navy/10 transition-[background-color] duration-150 ease-out hover:bg-foam ${focusRing}`}
                          >
                            <span className="flex items-baseline gap-2">
                              <span aria-hidden="true" className="grid size-6 shrink-0 place-items-center rounded-full bg-tide-deep text-xs font-bold text-white">{j + 1}</span>
                              <span className="min-w-0">
                                <span className="block font-semibold underline-offset-2 [overflow-wrap:anywhere] group-hover:underline">{c.title}</span>
                                {c.site && <span className="block text-sm text-navy/70">{c.site}<span className="sr-only"> (opens in a new tab)</span></span>}
                              </span>
                            </span>
                            {c.quote && <span className="mt-2 block border-l-4 border-tide pl-3 text-base italic text-navy/85">&ldquo;{c.quote}&rdquo;</span>}
                          </a>
                        </li>
                      ))}
                    </ol>
                  </div>
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
