"use client";

import Wordmark from "@/components/Wordmark";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useId, useState } from "react";
import { NIGHT_FEED_BACKDROP, NightFeedPlate } from "@/components/plates/Gouache";
import { ApiError, login, register } from "@/lib/api";
import { signedIn } from "@/lib/session";
import { btnPrimary, focusRing } from "@/lib/ui";

type Mode = "login" | "register";

const input = `mt-2 min-h-14 w-full rounded-2xl border-2 border-navy bg-white px-4 text-lg ${focusRing}`;

export default function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const ids = useId();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [badField, setBadField] = useState<"username" | "password" | null>(null);
  const [busy, setBusy] = useState(false);
  const isRegister = mode === "register";

  // Say what is missing first; the format rules only matter when creating an account.
  function problem(): [string, "username" | "password"] | null {
    if (!username) return ["Enter your username.", "username"];
    if (!password) return ["Enter your password.", "password"];
    if (isRegister && !/^[A-Za-z0-9_.-]{3,30}$/.test(username)) {
      return ["Usernames are 3 to 30 letters, numbers, dots, dashes or underscores.", "username"];
    }
    if (isRegister && password.length < 8) return ["Passwords need at least 8 characters.", "password"];
    return null;
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    const p = problem();
    setError(p ? p[0] : null);
    setBadField(p ? p[1] : null);
    if (p) {
      document.getElementById(`${ids}-${p[1] === "username" ? "u" : "p"}`)?.focus();
      return;
    }
    setBusy(true);
    try {
      const res = isRegister ? await register(username, password) : await login(username, password);
      signedIn(res);
      router.push(res.patient_id ? "/home" : "/onboarding");
    } catch (err) {
      setBadField(null);
      setError(
        err instanceof ApiError
          ? err.status === 409
            ? "That username is taken. Try another one."
            : err.status === 401
              ? "That username and password don't match."
              : err.message
          : "We couldn't reach Tidewell. Check your connection and try again."
      );
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-dvh flex-col bg-foam text-navy">
      <header className="mx-auto flex h-16 w-full max-w-5xl items-center px-5 sm:px-8 md:h-20">
        <Wordmark href="/" />
      </header>
      <main id="main" className="mx-auto grid w-full max-w-5xl flex-1 gap-12 px-5 pb-12 sm:px-8 lg:grid-cols-[minmax(0,28rem)_1fr] lg:items-start">
        <form onSubmit={onSubmit} noValidate className="mt-4 flex flex-col motion-safe:animate-reply-in lg:mt-10">
          <h1 className="font-display text-4xl font-semibold leading-tight">
            {isRegister ? "Create your account" : "Welcome back"}
          </h1>
          <p className="mt-3 text-lg leading-relaxed text-navy/85">
            {isRegister
              ? "Your check-ins and trends are saved to your own private record."
              : "Sign in to pick up where you left off."}
          </p>

          <label htmlFor={`${ids}-u`} className="mt-8 text-lg font-semibold">
            Username
          </label>
          <input
            id={`${ids}-u`}
            value={username}
            onChange={(e) => setUsername(e.target.value.trim())}
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            aria-invalid={badField === "username" ? true : undefined}
            aria-describedby={badField === "username" ? `${ids}-err` : undefined}
            className={input}
          />

          <label htmlFor={`${ids}-p`} className="mt-5 text-lg font-semibold">
            Password
          </label>
          <div className="relative">
            <input
              id={`${ids}-p`}
              type={show ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={isRegister ? "new-password" : "current-password"}
              aria-describedby={[isRegister ? `${ids}-hint` : "", badField === "password" ? `${ids}-err` : ""].join(" ").trim() || undefined}
              aria-invalid={badField === "password" ? true : undefined}
              className={`${input} pr-24`}
            />
            <button
              type="button"
              onClick={() => setShow((s) => !s)}
              aria-pressed={show}
              className={`absolute right-2 top-1/2 mt-1 -translate-y-1/2 rounded-xl px-3 py-2 text-base font-semibold underline underline-offset-4 ${focusRing}`}
            >
              {show ? "Hide" : "Show"}
            </button>
          </div>
          {isRegister && (
            <p id={`${ids}-hint`} className="mt-2 text-base text-navy/80">
              At least 8 characters. A short sentence is easy to remember.
            </p>
          )}

          {error && (
            <p id={`${ids}-err`} role="alert" className="mt-5 rounded-2xl bg-white p-4 text-lg text-alert ring-2 ring-alert/30">
              {error}
            </p>
          )}

          <button type="submit" aria-disabled={busy} className={`${btnPrimary} mt-8`}>
            {busy ? (isRegister ? "Creating your account" : "Signing in") : isRegister ? "Create account" : "Sign in"}
          </button>

          <p className="mt-6 text-center text-lg">
            {isRegister ? "Already have an account? " : "New to Tidewell? "}
            <Link
              href={isRegister ? "/login" : "/register"}
              className={`rounded font-semibold underline underline-offset-4 ${focusRing}`}
            >
              {isRegister ? "Sign in" : "Create an account"}
            </Link>
          </p>
        </form>
        {/* The same night-feed picture as the landing page, on wide screens only; on phones the form
            is the whole page. */}
        <div
          aria-hidden="true"
          className="plate hidden h-[36rem] overflow-hidden rounded-[10px] shadow-lift ring-1 ring-navy/10 lg:block"
          style={{ background: NIGHT_FEED_BACKDROP }}
        >
          <NightFeedPlate className="block size-full" />
        </div>
      </main>
    </div>
  );
}
