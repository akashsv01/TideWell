"use client";

import { useSyncExternalStore } from "react";
import { DEMO_PATIENT_ID } from "@/lib/config";

// Who is using Tidewell on this device. Two separate modes:
//   user: signed in with a username and password. `token` goes in the Authorization header; the
//         backend only serves this account's own patient record.
//   demo: Maya, the shared demo patient. No login, no token, nothing of yours is touched.
// Stored in localStorage (memory when storage is blocked). Logging out clears it and revokes the
// token on the server.

export type Session =
  | { kind: "user"; token: string; username: string; patientId: string | null }
  | { kind: "demo"; patientId: string };

const KEY = "tidewell.session";
const listeners = new Set<() => void>();
let current: Session | null | undefined; // undefined = not read yet

function read(): Session | null {
  if (current === undefined) {
    try {
      const raw = window.localStorage.getItem(KEY);
      current = raw ? (JSON.parse(raw) as Session) : null;
    } catch {
      current = null;
    }
  }
  return current;
}

function write(next: Session | null) {
  current = next;
  try {
    if (next) window.localStorage.setItem(KEY, JSON.stringify(next));
    else window.localStorage.removeItem(KEY);
  } catch {
    /* keep the in-memory value */
  }
  listeners.forEach((l) => l());
}

export function getSession(): Session | null {
  return read();
}

export function signedIn(auth: { token: string; username: string; patient_id: string | null }) {
  write({ kind: "user", token: auth.token, username: auth.username, patientId: auth.patient_id });
}

export function setOwnPatient(patientId: string | null) {
  const s = read();
  if (s?.kind === "user") write({ ...s, patientId });
}

export function startDemo() {
  write({ kind: "demo", patientId: DEMO_PATIENT_ID });
}

export function clearSession() {
  write(null);
}

export function authToken(): string | null {
  const s = read();
  return s?.kind === "user" ? s.token : null;
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
}

/** `ready` is false during server rendering, before localStorage can be read. */
export function useSession(): { session: Session | null; ready: boolean } {
  const session = useSyncExternalStore(subscribe, getSession, () => null);
  const ready = useSyncExternalStore(subscribe, () => true, () => false);
  return { session, ready };
}

/** The patient whose data this device is showing, or null. */
export function usePatientId(): string | null {
  const { session } = useSession();
  return session?.patientId ?? null;
}
