"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useId, useState } from "react";
import Waves from "@/components/Waves";
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
  const [busy, setBusy] = useState(false);
  const isRegister = mode === "register";

  function problem(): string | null {
    if (!/^[A-Za-z0-9_.-]{3,30}$/.test(username)) {
      return "Usernames are 3 to 30 letters, numbers, dots, dashes or underscores.";
    }
    if (password.length < 8) return "Passwords need at least 8 characters.";
    return null;
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    const p = problem();
    setError(p);
    if (p) return;
    setBusy(true);
    try {
      const res = isRegister ? await register(username, password) : await login(username, password);
      signedIn(res);
      router.push(res.patient_id ? "/home" : "/onboarding");
    } catch (err) {
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
      <header className="mx-auto flex h-16 w-full max-w-md items-center px-5">
        <Link href="/" className={`rounded-md font-display text-2xl text-tide-deep ${focusRing}`}>
          Tidewell
        </Link>
      </header>
      <main id="main" className="mx-auto flex w-full max-w-md flex-1 flex-col px-5 pb-10">
        <form onSubmit={onSubmit} noValidate className="mt-6 flex flex-col motion-safe:animate-reply-in">
          <h1 className="font-display text-4xl leading-tight">
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
            aria-invalid={error ? true : undefined}
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
              aria-describedby={isRegister ? `${ids}-hint` : undefined}
              aria-invalid={error ? true : undefined}
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
            <p role="alert" className="mt-5 rounded-2xl bg-white p-4 text-lg text-alert ring-2 ring-alert/30">
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
      </main>
      <Waves
        className="relative h-24 motion-safe:animate-rise"
        layers={[
          { color: "#efe3c8", amp: 8, cycles: 2, top: 60, seconds: 34 },
          { color: "#13828a", amp: 10, cycles: 3, top: 86, seconds: 26, reverse: true },
          { color: "#0b2545", amp: 11, cycles: 2, top: 112, seconds: 20 },
        ]}
      />
    </div>
  );
}
