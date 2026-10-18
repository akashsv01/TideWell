"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChartIcon, ChatIcon, GearIcon, HeartPlusIcon, WaveIcon } from "@/components/icons";
import { focusRing } from "@/lib/ui";

// The five app sections. Phones get a tab bar at the bottom (thumb reach, one hand); from md up the
// same links sit in the header as a running line under the wordmark (TopNav).
const items = [
  { href: "/home", label: "Check in", Icon: WaveIcon },
  { href: "/dashboard", label: "My tide", Icon: ChartIcon },
  { href: "/care", label: "Care", Icon: HeartPlusIcon },
  { href: "/ask", label: "Ask", Icon: ChatIcon },
  { href: "/settings", label: "Settings", Icon: GearIcon },
];

function isCurrent(pathname: string, href: string) {
  return (
    pathname === href ||
    (href === "/care" && pathname.startsWith("/visits")) ||
    (href === "/home" && pathname === "/mood-check")
  );
}

/** Header navigation from md up. */
export function TopNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Main" className="hidden border-b border-navy/10 md:block">
      <ul className="-mb-px flex gap-1">
        {items.map(({ href, label }) => {
          const current = isCurrent(pathname, href);
          return (
            <li key={href}>
              <Link
                href={href}
                aria-current={current ? "page" : undefined}
                className={`inline-flex min-h-12 items-center border-b-2 px-4 text-base font-semibold transition-[color,border-color] duration-150 ease-out ${focusRing} ${
                  current ? "border-tide-deep text-navy" : "border-transparent text-navy/70 hover:border-navy/25 hover:text-navy"
                }`}
              >
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

/** Tab bar on phones only. */
export default function BottomNav() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Main"
      className="fixed inset-x-0 bottom-0 z-20 border-t border-navy/10 bg-foam/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden"
    >
      <ul className="mx-auto flex max-w-md">
        {items.map(({ href, label, Icon }) => {
          const current = isCurrent(pathname, href);
          return (
            <li key={href} className="flex-1">
              <Link
                href={href}
                aria-current={current ? "page" : undefined}
                className={`mx-0.5 my-1 flex min-h-16 flex-col items-center justify-center gap-1 rounded-xl text-sm font-semibold transition-[color,background-color,transform] duration-150 ease-out motion-safe:active:scale-[0.97] ${focusRing} ${
                  current ? "bg-tide-deep/10 text-tide-deep" : "text-navy/70 hover:bg-navy/5"
                }`}
              >
                <Icon className="size-6" />
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
