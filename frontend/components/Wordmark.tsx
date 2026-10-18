import Link from "next/link";
import { Mark } from "@/components/plates/Gouache";
import { focusRing } from "@/lib/ui";

// The one Tidewell lockup: the moon-over-tide Mark beside the Alegreya wordmark. Every page header
// uses this, so the name looks the same on the landing page, sign in, onboarding and the app.
export default function Wordmark({ href = "/" }: { href?: string }) {
  return (
    <Link
      href={href}
      className={`flex shrink-0 items-center gap-2 rounded-md font-display text-2xl font-semibold leading-none text-navy ${focusRing}`}
    >
      <Mark className="size-8 text-tide-deep" />
      Tidewell
    </Link>
  );
}
