"use client";

import { useSyncExternalStore } from "react";
import { DEMO_PATIENT_ID } from "@/lib/config";

// Who is using Tidewell on this device: the patient id the backend gave us at onboarding (or
// found for this login via GET /me), plus the Clerk user id when sign-in is enabled.
// Backed by localStorage when available and by memory when it is not (private windows).
//
// The stored id remembers which login it belongs to ("owner"), so when someone else signs in on
// the same device, or the user signs out, the previous person's data is never shown.

const KEY = "tidewell.patientId";
const OWNER_KEY = "tidewell.patientOwner"; // Clerk user id the patient id belongs to ("" = no login)
const listeners = new Set<() => void>();
let patientId: string | null | undefined; // undefined = not read yet
let owner: string | null = null;
let clerkUserId: string | null = null;
let clerkLoaded = false; // true once ClerkBridge has reported (only matters when sign-in is enabled)

function load(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function save(key: string, value: string | null) {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    /* keep the in-memory value */
  }
}

function read(): string | null {
  if (patientId === undefined) {
    patientId = load(KEY);
    owner = load(OWNER_KEY);
  }
  return patientId;
}

function emit() {
  listeners.forEach((l) => l());
}

export function getPatientId(): string | null {
  return read();
}

export function setPatientId(id: string | null) {
  read();
  patientId = id;
  owner = id ? (clerkUserId ?? "") : null;
  save(KEY, id);
  save(OWNER_KEY, owner);
  emit();
}

export function chooseDemoAccount() {
  setPatientId(DEMO_PATIENT_ID);
}

export const isDemo = (id: string | null) => id === DEMO_PATIENT_ID;

export function getClerkUserId(): string | null {
  return clerkUserId;
}

/** Called by ClerkBridge once Clerk has loaded, and whenever the signed-in user changes. */
export function setClerkUserId(id: string | null) {
  read();
  clerkUserId = id;
  clerkLoaded = true;
  const belongsToSomeoneElse = patientId && owner && owner !== (id ?? "");
  const signedInOverAnonymous = patientId && id && !owner;
  if (belongsToSomeoneElse || signedInOverAnonymous) setPatientId(null);
  else emit();
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
}

/** The current patient id, or null if this device has not onboarded or signed in yet.
 *  `ready` is false during server rendering, before localStorage can be read. */
export function usePatientId(): { patientId: string | null; ready: boolean } {
  const id = useSyncExternalStore(subscribe, getPatientId, () => null);
  const ready = useSyncExternalStore(subscribe, () => true, () => false);
  return { patientId: id, ready };
}

export function useClerkUserId(): { clerkUserId: string | null; loaded: boolean } {
  const id = useSyncExternalStore(subscribe, getClerkUserId, () => null);
  const loaded = useSyncExternalStore(subscribe, () => clerkLoaded, () => false);
  return { clerkUserId: id, loaded };
}
