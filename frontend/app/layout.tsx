import type { Metadata, Viewport } from "next";
import "@fontsource/young-serif";
import "@fontsource-variable/atkinson-hyperlegible-next";
import "./globals.css";
import Script from "next/script";
import NightMode from "@/components/NightMode";
import { DAY_PAGE, NIGHT_BOOT_SCRIPT } from "@/lib/nightBoot";

export const metadata: Metadata = {
  title: { default: "Tidewell", template: "%s | Tidewell" },
  description: "A voice-first care companion for the year after birth.",
};

export const viewport: Viewport = {
  themeColor: DAY_PAGE,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // suppressHydrationWarning: the boot script may add data-night before React hydrates.
    <html lang="en" className="h-full antialiased" suppressHydrationWarning>
      <body className="min-h-full">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[60] focus:rounded-lg focus:bg-navy focus:px-4 focus:py-3 focus:text-white"
        >
          Skip to content
        </a>
        <NightMode />
        {/* Before hydration, so a night-time visit never flashes the light theme. */}
        <Script id="night-boot" strategy="beforeInteractive">
          {NIGHT_BOOT_SCRIPT}
        </Script>
        {children}
      </body>
    </html>
  );
}
