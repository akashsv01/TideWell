import { SignUp } from "@clerk/nextjs";
import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { AUTH_ENABLED } from "@/lib/auth";

export const metadata: Metadata = { title: "Create your account" };

export default function SignUpPage() {
  if (!AUTH_ENABLED) redirect("/onboarding");
  return (
    <main id="main" className="flex min-h-dvh items-center justify-center bg-foam p-4">
      <div className="motion-safe:animate-step-in">
        <SignUp signInUrl="/sign-in" fallbackRedirectUrl="/onboarding" />
      </div>
    </main>
  );
}
