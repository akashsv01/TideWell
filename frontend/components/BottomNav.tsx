"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChartIcon, GearIcon, WaveIcon } from "@/components/icons";
import { focusRing } from "@/lib/ui";

const items = [
  { href: "/home", label: "Check in", Icon: WaveIcon },
  { href: "/dashboard", label: "My tide", Icon: ChartIcon },
  { href: "/settings", label: "Settings", Icon: GearIcon },
];

export default function BottomNav() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Main"
      className="fixed inset-x-0 bottom-0 z-20 border-t border-navy/10 bg-foam/95 pb-[env(safe-area-inset-bottom)] backdrop-blur"
    >
      <ul className="mx-auto flex max-w-md">
        {items.map(({ href, label, Icon }) => {
          const current = pathname === href;
          return (
            <li key={href} className="flex-1">
              <Link
                href={href}
                aria-current={current ? "page" : undefined}
                className={`mx-1 my-1 flex min-h-16 flex-col items-center justify-center gap-1 rounded-2xl text-sm font-semibold transition-colors duration-150 ${focusRing} ${
                  current ? "bg-tide-deep text-white" : "text-navy/75 hover:bg-navy/5"
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
