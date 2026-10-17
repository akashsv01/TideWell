import { SignIn } from "@clerk/nextjs";
import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { AUTH_ENABLED } from "@/lib/auth";

export const metadata: Metadata = { title: "Sign in" };

export default function SignInPage() {
  if (!AUTH_ENABLED) redirect("/home");
  return (
    <main id="main" className="flex min-h-dvh items-center justify-center bg-foam p-4">
      <div className="motion-safe:animate-step-in">
        <SignIn signUpUrl="/sign-up" fallbackRedirectUrl="/home" />
      </div>
    </main>
  );
}
