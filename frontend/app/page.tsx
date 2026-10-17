import Link from "next/link";
import Waves, { type WaveLayer } from "@/components/Waves";
import { btnPrimary, focusRing, focusRingLight } from "@/lib/ui";

// Welcome screen. Clerk sign-in will replace the "I already have an account" link later.

const shoreline: WaveLayer[] = [
  { color: "#efe3c8", amp: 9, cycles: 2, top: 70, seconds: 34, opacity: 1 },
  { color: "#13828a", amp: 11, cycles: 3, top: 98, seconds: 26, reverse: true },
  { color: "#0b2545", amp: 12, cycles: 2, top: 128, seconds: 20 },
];

const promises = [
  {
    title: "Say it out loud",
    body: "Tap once and talk for a minute. No forms to fill in on a hard day.",
  },
  {
    title: "Watch the pattern",
    body: "Mood, sleep, pain and blood pressure, drawn as a tide you can read at a glance.",
  },
  {
    title: "Know when to call",
    body: "Warning signs get a clear answer and a phone number, never a chat.",
  },
];

export default function Welcome() {
  return (
    <div className="flex min-h-dvh flex-col bg-foam text-navy">
      <main id="main" className="flex flex-1 flex-col">
        <div className="mx-auto w-full max-w-2xl px-6 pt-8 sm:pt-14">
          <p className="font-display text-2xl text-tide-deep">Tidewell</p>
          <h1 className="mt-14 max-w-[12ch] font-display text-5xl leading-[1.05] sm:text-6xl">
            How are you, really?
          </h1>
          <p className="mt-6 max-w-[34ch] text-xl leading-relaxed">
            Tidewell is a voice companion for the first year after birth. Talk for a minute a day.
            It keeps track of the pattern and tells you when something is worth a call.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-x-8 gap-y-4">
            <Link href="/onboarding" className={btnPrimary}>
              Get started
            </Link>
            <Link
              href="/home"
              className={`rounded-md py-2 text-lg font-semibold underline underline-offset-4 ${focusRing}`}
            >
              I already have an account
            </Link>
          </div>
        </div>

        <div className="mt-12 flex flex-1 flex-col">
          <Waves layers={shoreline} className="relative h-28 motion-safe:animate-rise sm:h-36" />
          <div className="-mt-px flex-1 bg-navy px-6 pb-10 pt-4 text-white">
            <div className="mx-auto w-full max-w-2xl">
              <ul className="space-y-7">
                {promises.map((p) => (
                  <li key={p.title}>
                    <h2 className="font-display text-2xl">{p.title}</h2>
                    <p className="mt-1 max-w-[40ch] text-lg leading-relaxed text-white/85">
                      {p.body}
                    </p>
                  </li>
                ))}
              </ul>
              <p className="mt-10 text-base text-white/80">
                Tidewell does not diagnose. In an emergency, call{" "}
                <a href="tel:911" className={`rounded font-semibold underline ${focusRingLight}`}>
                  911
                </a>
                .
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
