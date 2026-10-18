import Link from "next/link";
import { focusRing } from "@/lib/ui";

// The way back from a sub-screen (Your visits, Book a visit, Mood check): always at the top left,
// always naming where it goes.
export default function BackLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className={`group -ml-1 inline-flex min-h-11 w-fit items-center gap-1 rounded-md pr-2 text-lg font-semibold text-navy/85 transition-colors duration-150 ease-out hover:text-navy ${focusRing}`}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true" className="size-6 shrink-0 transition-transform duration-150 ease-out group-hover:-translate-x-0.5">
        <path d="m15 6-6 6 6 6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {children}
    </Link>
  );
}
