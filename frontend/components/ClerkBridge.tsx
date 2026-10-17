"use client";

import { useUser } from "@clerk/nextjs";
import { useEffect } from "react";
import { setClerkUserId } from "@/lib/identity";

// Rendered inside <ClerkProvider> only when sign-in is enabled. Copies the signed-in user's id
// into the identity store, so the rest of the app never has to call Clerk hooks directly.
export default function ClerkBridge() {
  const { isLoaded, user } = useUser();
  const id = user?.id ?? null;

  useEffect(() => {
    if (isLoaded) setClerkUserId(id);
  }, [isLoaded, id]);

  return null;
}
