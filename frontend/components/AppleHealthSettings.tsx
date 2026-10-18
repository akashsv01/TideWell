"use client";

import { useEffect, useState } from "react";
import { createHealthCode, disconnectHealth, downloadHealthGuide, getHealthStatus } from "@/lib/api";
import type { HealthStatus } from "@/lib/types";
import { btnOutline, btnPrimary, focusRing } from "@/lib/ui";

// Settings > Connect Apple Health. The iPhone app (Health Auto Export) needs a web address and a
// connection code. The code is shown once (only its hash is stored) and is never put in the PDF guide.
// A new code disconnects the old phone; Disconnect stops it entirely.

const ago = (iso?: string | null) => {
  if (!iso) return null;
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60_000);
  if (mins < 2) return "just now";
  if (mins < 60) return `${mins} minutes ago`;
  const h = Math.round(mins / 60);
  return h < 24 ? `${h} ${h === 1 ? "hour" : "hours"} ago` : new Date(iso).toLocaleString();
};

export default function AppleHealthSettings({ patientId }: { patientId: string }) {
  const [status, setStatus] = useState<HealthStatus | null>(null);
  const [code, setCode] = useState<{ code: string; ingest_url: string } | null>(null);
  const [copied, setCopied] = useState<"url" | "code" | null>(null);
  const [busy, setBusy] = useState<"code" | "pdf" | "off" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = () => getHealthStatus(patientId).then(setStatus, () => {});
  useEffect(() => {
    let cancelled = false;
    getHealthStatus(patientId).then((s) => !cancelled && setStatus(s), () => {});
    return () => {
      cancelled = true;
    };
  }, [patientId]);

  async function act(kind: "code" | "pdf" | "off") {
    setBusy(kind);
    setError(null);
    try {
      if (kind === "code") {
        setCode(await createHealthCode());
        setCopied(null);
      } else if (kind === "pdf") {
        await downloadHealthGuide();
      } else {
        await disconnectHealth();
        setCode(null);
      }
      if (kind !== "pdf") await refresh();
    } catch {
      setError(kind === "pdf" ? "We couldn't download the guide. Try again." : "That didn't work. Try again.");
    } finally {
      setBusy(null);
    }
  }

  async function copy(what: "url" | "code", text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(what);
    } catch {
      setCopied(null);
    }
  }

  const synced = ago(status?.last_sync);
  return (
    <section id="apple-health" aria-labelledby="ah-title" className="scroll-mt-20">
      <h2 id="ah-title" className="font-display text-2xl font-semibold">Connect Apple Health</h2>
      <p className="mt-2 max-w-[50ch] text-lg leading-relaxed">
        Send sleep, blood pressure and resting heart rate from your iPhone, so you don&apos;t have to type them.
        It uses the Health Auto Export app on your iPhone; the guide walks you through it once.
      </p>
      <p className="mt-3 text-base text-navy/85" aria-live="polite">
        {!status
          ? "Checking…"
          : status.connected
            ? `Connected. Last sync: ${synced ?? "waiting for your iPhone"}.`
            : "Not connected yet."}
      </p>

      <div className="mt-4 flex flex-wrap gap-3">
        <button type="button" onClick={() => act("pdf")} aria-disabled={busy !== null} className={btnPrimary}>
          {busy === "pdf" ? "Preparing" : "Download iPhone setup guide (PDF)"}
        </button>
        <button type="button" onClick={() => act("code")} aria-disabled={busy !== null} className={btnOutline}>
          {status?.connected ? "Make a new connection code" : "Create connection code"}
        </button>
        {status?.connected && (
          <button
            type="button"
            onClick={() => act("off")}
            aria-disabled={busy !== null}
            className={`rounded-md px-2 text-lg font-semibold underline underline-offset-4 ${focusRing}`}
          >
            Disconnect
          </button>
        )}
      </div>
      {error && <p role="alert" className="mt-3 text-lg text-alert">{error}</p>}

      {code && (
        <div className="mt-5 space-y-4 rounded-2xl bg-white p-5 shadow-paper ring-1 ring-navy/10 motion-safe:animate-reply-in">
          <p className="text-base font-semibold text-alert">
            Copy the code now: it is shown only once. Treat it like a password.
          </p>
          <Field label="Web address (URL)" value={code.ingest_url} copied={copied === "url"} onCopy={() => copy("url", code.ingest_url)} />
          <Field
            label="Header: Authorization"
            value={`Bearer ${code.code}`}
            copied={copied === "code"}
            onCopy={() => copy("code", `Bearer ${code.code}`)}
          />
          <p className="text-sm text-navy/75">
            Paste these into the REST API automation in Health Auto Export (step 4 of the guide). Making a new code
            disconnects the old phone.
          </p>
        </div>
      )}
    </section>
  );
}

function Field({ label, value, copied, onCopy }: { label: string; value: string; copied: boolean; onCopy: () => void }) {
  return (
    <div>
      <p className="text-sm font-semibold text-navy/80">{label}</p>
      <div className="mt-1 flex flex-wrap items-center gap-2">
        <code className="min-w-0 flex-1 rounded-xl bg-foam px-3 py-2 font-mono text-sm [overflow-wrap:anywhere]">{value}</code>
        <button
          type="button"
          onClick={onCopy}
          className={`min-h-11 rounded-full border-2 border-navy px-4 text-base font-semibold ${focusRing}`}
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
    </div>
  );
}
