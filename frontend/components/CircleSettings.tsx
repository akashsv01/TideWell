"use client";

import { useState } from "react";
import { createCircle, revokeCircle } from "@/lib/api";
import { btnOutline, btnPrimary } from "@/lib/ui";

// Care Circle: a private, read-only link for the support person (status + how to help, no details).
// Creating a new link replaces the old one; "Turn off" revokes it.
export default function CircleSettings({ patientId }: { patientId: string }) {
  const [link, setLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);

  async function make() {
    setBusy(true);
    try {
      const r = await createCircle(patientId);
      setLink(`${window.location.origin}${r.path}`);
      setCopied(false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="circle-title">
      <h2 id="circle-title" className="font-display text-2xl font-semibold">Care Circle</h2>
      <p className="mt-2 max-w-[46ch] text-lg leading-relaxed">
        Share a private link with someone who helps you. They see how you&apos;re doing this week and how
        they can help, never what you said or your mood answers.
      </p>
      <div className="mt-4 flex flex-wrap gap-3" aria-live="polite">
        <button type="button" onClick={make} aria-disabled={busy} className={btnPrimary}>
          {link ? "Make a new link" : "Create a link"}
        </button>
        {link && (
          <button type="button" onClick={() => revokeCircle(patientId).then(() => setLink(null))} className={btnOutline}>
            Turn off sharing
          </button>
        )}
      </div>
      {link && (
        <div className="mt-4 flex flex-wrap items-center gap-3 rounded-2xl bg-white p-4 ring-1 ring-navy/10 motion-safe:animate-reply-in">
          <code className="min-w-0 flex-1 break-all text-base">{link}</code>
          <button
            type="button"
            onClick={() => navigator.clipboard?.writeText(link).then(() => setCopied(true))}
            className="min-h-11 rounded-full border-2 border-navy px-4 font-semibold transition-transform duration-150 ease-out motion-safe:active:scale-[0.97]"
          >
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      )}
    </section>
  );
}
