import type { Metadata, Viewport } from "next";
import "@fontsource/young-serif";
import "@fontsource-variable/atkinson-hyperlegible-next";
import "./globals.css";
import { ClerkProvider } from "@clerk/nextjs";
import ClerkBridge from "@/components/ClerkBridge";
import { AUTH_ENABLED } from "@/lib/auth";

export const metadata: Metadata = {
  title: { default: "Tidewell", template: "%s | Tidewell" },
  description: "A voice-first care companion for the year after birth.",
};

export const viewport: Viewport = {
  themeColor: "#f4f9f9",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[60] focus:rounded-lg focus:bg-navy focus:px-4 focus:py-3 focus:text-white"
        >
          Skip to content
        </a>
        {AUTH_ENABLED ? (
          <ClerkProvider signInUrl="/sign-in" signUpUrl="/sign-up">
            <ClerkBridge />
            {children}
          </ClerkProvider>
        ) : (
          children
        )}
      </body>
    </html>
  );
}
