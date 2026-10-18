import HeroDevice from "@/components/HeroDevice";
import LandingNav from "@/components/LandingNav";
import Reveal from "@/components/Reveal";
import Waves, { type WaveLayer } from "@/components/Waves";
import WelcomeActions from "@/components/WelcomeActions";
import { focusRingLight } from "@/lib/ui";

// Public home page. Organic, calm, ocean-toned: flowing wave shapes, one primary action per
// screen, motion that is slow and quiet (entrances once, decorative loops off with reduced motion).

const shoreline: WaveLayer[] = [
  { color: "#efe3c8", amp: 9, cycles: 2, top: 70, seconds: 34, opacity: 1 },
  { color: "#13828a", amp: 11, cycles: 3, top: 98, seconds: 26, reverse: true },
  { color: "#0b2545", amp: 12, cycles: 2, top: 128, seconds: 20 },
];

const steps = [
  { n: "1", title: "Talk for a minute", body: "Tap once and say how you are. Sleep, pain, mood, a blood pressure reading. No forms on a hard day." },
  { n: "2", title: "Safety comes first", body: "Before any AI replies, fixed rules check for warning signs. If one shows up, you get a clear next step right away." },
  { n: "3", title: "See your tide", body: "Tidewell notes the numbers, remembers last week, and draws the pattern so you and your care team can read it at a glance." },
];

const Icon = ({ d, className = "size-7" }: { d: string; className?: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
    <path d={d} />
  </svg>
);

const ICONS = {
  mic: "M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3ZM5 11a7 7 0 0 0 14 0M12 18v3",
  shield: "M12 3 4.5 6v5.5c0 4.6 3.2 8.4 7.5 9.5 4.3-1.1 7.5-4.9 7.5-9.5V6L12 3Zm-3 9 2 2 4-4",
  heart: "M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10Z",
  memory: "M8 7V5a4 4 0 0 1 8 0v2M5 7h14v4a7 7 0 0 1-14 0V7Zm7 6v3",
  lock: "M7 11V8a5 5 0 0 1 10 0v3M5.5 11h13v9h-13zM12 15v2",
  wave: "M3 12c2-2 4-2 6 0s4 2 6 0 4-2 6 0M3 17c2-2 4-2 6 0s4 2 6 0 4-2 6 0M3 7c2-2 4-2 6 0s4 2 6 0 4-2 6 0",
};

export default function Welcome() {
  return (
    <div className="flex min-h-dvh flex-col bg-foam text-navy">
      <LandingNav />

      <main id="main" className="flex flex-1 flex-col">
        {/* ---------------- hero ---------------- */}
        <section className="relative overflow-hidden">
          <div className="pointer-events-none absolute -right-32 -top-24 size-[28rem] rounded-full bg-tide-light/20 blur-3xl" aria-hidden="true" />
          <div className="mx-auto grid w-full max-w-6xl items-center gap-14 px-5 pb-16 pt-6 sm:px-8 lg:grid-cols-[1.1fr_0.9fr] lg:pb-24 lg:pt-10">
            <div className="motion-safe:animate-reply-in">
              <p className="inline-flex items-center gap-2 rounded-full bg-sand/80 px-4 py-1.5 text-sm font-semibold">
                <span className="size-2 rounded-full bg-tide-deep" aria-hidden="true" />
                For the first year after birth
              </p>
              <h1 className="mt-6 max-w-[13ch] font-display text-5xl leading-[1.04] text-balance sm:text-6xl lg:text-7xl">
                How are you, really?
              </h1>
              <p className="mt-6 max-w-[38ch] text-xl leading-relaxed text-navy/90">
                Tidewell is a voice companion for new parents. Talk for a minute a day. It remembers how
                you&apos;ve been, watches the pattern, and tells you clearly when something is worth a call.
              </p>
              <div className="mt-9">
                <WelcomeActions />
              </div>
              <ul className="mt-10 flex flex-wrap gap-x-6 gap-y-2 text-base text-navy/85">
                <li className="flex items-center gap-2"><Icon d={ICONS.shield} className="size-5 text-tide-deep" />Warning signs checked first</li>
                <li className="flex items-center gap-2"><Icon d={ICONS.heart} className="size-5 text-tide-deep" />Never diagnoses</li>
                <li className="flex items-center gap-2"><Icon d={ICONS.lock} className="size-5 text-tide-deep" />Delete your data any time</li>
              </ul>
            </div>
            <div className="motion-safe:animate-reply-in" style={{ animationDelay: "120ms" }}>
              <HeroDevice />
            </div>
          </div>
        </section>

        {/* ---------------- the problem ---------------- */}
        <Waves layers={shoreline} className="relative h-24 sm:h-28" />
        <section aria-labelledby="why-title" className="relative -mt-px bg-navy text-white">
          <div className="mx-auto w-full max-w-6xl px-5 pb-20 pt-6 sm:px-8">
            <Reveal>
              <h2 id="why-title" className="max-w-[22ch] font-display text-4xl leading-tight sm:text-5xl">
                The riskiest stretch gets the least attention.
              </h2>
            </Reveal>
            <div className="mt-12 grid gap-10 sm:grid-cols-2">
              <Reveal delay={80}>
                <p className="font-display text-7xl text-tide-light">53%</p>
                <p className="mt-3 max-w-[34ch] text-lg leading-relaxed text-white/90">
                  of pregnancy-related deaths in the US happened between a week and a year after birth.
                </p>
              </Reveal>
              <Reveal delay={160}>
                <p className="font-display text-7xl text-tide-light">84%</p>
                <p className="mt-3 max-w-[34ch] text-lg leading-relaxed text-white/90">
                  of them were judged preventable. Many new parents see a doctor only once, around six weeks.
                </p>
              </Reveal>
            </div>
            <p className="mt-10 text-sm text-white/70">Source: CDC Maternal Mortality Review Committees, deaths from 2017 to 2019.</p>
          </div>
        </section>

        {/* ---------------- how it works ---------------- */}
        <section aria-labelledby="how-title" className="mx-auto w-full max-w-6xl px-5 py-24 sm:px-8">
          <Reveal>
            <p className="text-base font-semibold uppercase tracking-wider text-tide-deep">How it works</p>
            <h2 id="how-title" className="mt-3 max-w-[20ch] font-display text-4xl leading-tight sm:text-5xl">
              One minute a day. Nothing to fill in.
            </h2>
          </Reveal>
          <ol className="mt-14 grid gap-6 md:grid-cols-3">
            {steps.map((s, i) => (
              <Reveal as="li" key={s.n} delay={i * 90} className="relative rounded-[2rem] bg-white p-7 shadow-[0_10px_30px_-18px_rgba(11,37,69,0.35)] ring-1 ring-navy/5">
                <span className="grid size-12 place-items-center rounded-2xl bg-tide-deep font-display text-xl text-white">{s.n}</span>
                <h3 className="mt-6 font-display text-2xl">{s.title}</h3>
                <p className="mt-3 text-lg leading-relaxed text-navy/85">{s.body}</p>
              </Reveal>
            ))}
          </ol>
        </section>

        {/* ---------------- features (bento) ---------------- */}
        <section aria-labelledby="features-title" className="bg-sand/45">
          <div className="mx-auto w-full max-w-6xl px-5 py-24 sm:px-8">
            <Reveal>
              <h2 id="features-title" className="max-w-[22ch] font-display text-4xl leading-tight sm:text-5xl">
                Built around how recovery actually goes.
              </h2>
            </Reveal>
            <div className="mt-14 grid gap-5 md:grid-cols-6">
              <Reveal className="rounded-[2rem] bg-navy p-8 text-white md:col-span-4">
                <Icon d={ICONS.wave} className="size-8 text-tide-light" />
                <h3 className="mt-5 font-display text-3xl">Your tide</h3>
                <p className="mt-3 max-w-[40ch] text-lg leading-relaxed text-white/90">
                  Mood, sleep, pain, headaches and blood pressure drawn as one calm picture, with a plain
                  sentence about what changed. Take it to your next visit.
                </p>
                <svg viewBox="0 0 400 110" className="mt-6 h-28 w-full" aria-hidden="true">
                  <defs>
                    <linearGradient id="tide-fill" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%" stopColor="#6fd0d4" stopOpacity="0.45" />
                      <stop offset="100%" stopColor="#6fd0d4" stopOpacity="0" />
                    </linearGradient>
                  </defs>
                  <path d="M0 40 C40 30 70 45 110 42 S180 60 220 58 S300 78 340 80 S385 88 400 92 L400 110 L0 110 Z" fill="url(#tide-fill)" />
                  <path className="draw-line" pathLength={1} d="M0 40 C40 30 70 45 110 42 S180 60 220 58 S300 78 340 80 S385 88 400 92" fill="none" stroke="#6fd0d4" strokeWidth="4" strokeLinecap="round" />
                </svg>
              </Reveal>
              <Reveal delay={90} className="rounded-[2rem] bg-white p-8 ring-1 ring-navy/5 md:col-span-2">
                <Icon d={ICONS.mic} className="size-8 text-tide-deep" />
                <h3 className="mt-5 font-display text-2xl">Voice first</h3>
                <p className="mt-3 text-lg leading-relaxed text-navy/85">Talk, or type if you&apos;d rather. Replies are read aloud in a calm voice.</p>
              </Reveal>
              <Reveal delay={60} className="rounded-[2rem] bg-white p-8 ring-1 ring-navy/5 md:col-span-2">
                <Icon d={ICONS.shield} className="size-8 text-tide-deep" />
                <h3 className="mt-5 font-display text-2xl">Safety layer</h3>
                <p className="mt-3 text-lg leading-relaxed text-navy/85">
                  CDC warning signs are checked by fixed rules before any AI. Emergencies get 911 and 988; urgent signs get &ldquo;call your provider today.&rdquo;
                </p>
              </Reveal>
              <Reveal delay={120} className="rounded-[2rem] bg-white p-8 ring-1 ring-navy/5 md:col-span-2">
                <Icon d={ICONS.heart} className="size-8 text-tide-deep" />
                <h3 className="mt-5 font-display text-2xl">Weekly mood check</h3>
                <p className="mt-3 text-lg leading-relaxed text-navy/85">
                  Ten gentle questions, once a week, from the Edinburgh Postnatal Depression Scale. A screening, never a diagnosis.
                </p>
              </Reveal>
              <Reveal delay={180} className="rounded-[2rem] bg-tide-deep p-8 text-white md:col-span-2">
                <Icon d={ICONS.memory} className="size-8 text-tide-light" />
                <h3 className="mt-5 font-display text-2xl">Remembers you</h3>
                <p className="mt-3 text-lg leading-relaxed text-white/90">
                  It knows it&apos;s day 18 after your C-section and that Tuesday&apos;s headache came back, so you don&apos;t have to start over.
                </p>
              </Reveal>
            </div>
          </div>
        </section>

        {/* ---------------- is / isn't ---------------- */}
        <section aria-labelledby="trust-title" className="mx-auto w-full max-w-6xl px-5 py-24 sm:px-8">
          <div className="grid gap-12 lg:grid-cols-2">
            <Reveal>
              <h2 id="trust-title" className="max-w-[16ch] font-display text-4xl leading-tight sm:text-5xl">
                A bridge between visits, not a doctor.
              </h2>
              <p className="mt-5 max-w-[42ch] text-lg leading-relaxed text-navy/85">
                Tidewell helps you notice what&apos;s changing and say it clearly. Your doctor, midwife or
                care team makes the decisions.
              </p>
            </Reveal>
            <ul className="space-y-4">
              {[
                ["It listens and remembers", "Your check-ins, in your words, kept private to your account."],
                ["It never diagnoses", "No guesses about conditions, and never advice to start or stop a medicine."],
                ["It is clear in an emergency", "Warning signs get a fixed, pre-written answer with the numbers to call."],
                ["It is yours to delete", "One tap in Settings removes your account and everything in it."],
              ].map(([t, b], i) => (
                <Reveal as="li" key={t} delay={i * 70} className="flex gap-4 rounded-3xl bg-white p-5 ring-1 ring-navy/5">
                  <span className="mt-1 grid size-8 shrink-0 place-items-center rounded-full bg-tide-deep text-white">
                    <Icon d="M5 12.5 10 17l9-10" className="size-4" />
                  </span>
                  <span>
                    <span className="block text-lg font-semibold">{t}</span>
                    <span className="mt-1 block text-lg leading-relaxed text-navy/85">{b}</span>
                  </span>
                </Reveal>
              ))}
            </ul>
          </div>
        </section>

        {/* ---------------- closing CTA ---------------- */}
        <section aria-labelledby="cta-title" className="mt-auto">
          <Waves layers={shoreline} className="relative h-28 sm:h-36" />
          <div className="-mt-px bg-navy px-5 pb-12 pt-6 text-white sm:px-8">
            <div className="mx-auto w-full max-w-6xl">
              <Reveal className="max-w-2xl">
                <h2 id="cta-title" className="font-display text-4xl leading-tight sm:text-5xl">
                  Start tonight. It takes two minutes.
                </h2>
                <p className="mt-4 text-xl leading-relaxed text-white/90">
                  Set up your account, answer a few questions, and do your first check-in. Or look around
                  with Maya, our demo parent.
                </p>
                <div className="mt-8">
                  <WelcomeActions tone="dark" />
                </div>
              </Reveal>
              <footer className="mt-16 flex flex-col gap-3 border-t border-white/15 pt-8 text-base text-white/80 sm:flex-row sm:items-center sm:justify-between">
                <p className="font-display text-xl text-white">Tidewell</p>
                <p>
                  Tidewell does not diagnose. In an emergency call{" "}
                  <a href="tel:911" className={`rounded font-semibold text-white underline ${focusRingLight}`}>911</a>
                  . Thoughts of harming yourself: call or text{" "}
                  <a href="tel:988" className={`rounded font-semibold text-white underline ${focusRingLight}`}>988</a>.
                </p>
              </footer>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
