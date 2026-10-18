import LandingNav from "@/components/LandingNav";
import TideSample from "@/components/TideSample";
import WelcomeActions from "@/components/WelcomeActions";
import { Mark, NightFeedPlate, WindowPlate } from "@/components/plates/Gouache";
import { focusRingLight } from "@/lib/ui";

// Public home page, built as a picture book you are awake inside at 3 a.m. The first viewport is an
// open spread: a gouache plate on the left page, the offer and the action on the right. Below, one
// night in three moments, the risk in one sourced sentence, a sample tide on a clean surface, and
// four promises. Content is visible from the first frame; the only motion is the moonrise.

const night = [
  {
    hour: "night" as const,
    time: "11:42 pm",
    title: "Talk for a minute",
    body: "Tap the moon and say how you are: sleep, pain, mood, a blood pressure reading. No forms on a hard night.",
  },
  {
    hour: "late" as const,
    time: "11:43 pm",
    title: "Safety comes first",
    body: "Before any AI replies, fixed rules check what you said for warning signs. If one shows up, you get the number to call, right away.",
  },
  {
    hour: "dawn" as const,
    time: "7:10 am",
    title: "Your tide, in the morning",
    body: "Tidewell adds last night to the picture and says plainly what changed, so you and your care team can read it at a glance.",
  },
];

const promises = [
  ["It listens and remembers", "Your check-ins, in your words, private to your account."],
  ["It never diagnoses", "No guesses about conditions, and never advice to start or stop a medicine."],
  ["It is clear in an emergency", "Warning signs get a fixed, pre-written answer with the number to call."],
  ["It is yours to delete", "One tap in Settings removes your account and everything in it."],
];

const container = "mx-auto w-full max-w-6xl px-5 sm:px-8";

export default function Welcome() {
  return (
    <div className="flex min-h-dvh flex-col bg-foam text-navy">
      <LandingNav />

      <main id="main" className="flex flex-1 flex-col">
        {/* ---------- the open spread ---------- */}
        <section aria-labelledby="hero-title" className={`${container} pb-20 pt-2`}>
          <div className="grid overflow-hidden rounded-[10px] bg-white shadow-lift ring-1 ring-navy/10 lg:grid-cols-2">
            <div className="relative h-72 sm:h-96 lg:h-auto lg:min-h-[640px]">
              <NightFeedPlate className="plate-hero absolute inset-0 size-full" />
            </div>
            {/* the right page: the gutter shadow falls on its inner edge */}
            <div className="relative flex flex-col justify-center px-6 py-12 sm:px-12 lg:py-16">
              <span
                aria-hidden="true"
                className="pointer-events-none absolute inset-y-0 left-0 hidden w-10 bg-gradient-to-r from-navy/10 to-transparent lg:block"
              />
              <h1 id="hero-title" className="max-w-[12ch] font-display text-5xl font-semibold leading-[1.02] tracking-[-0.01em] sm:text-6xl lg:text-7xl">
                How are you, really?
              </h1>
              <p className="mt-6 max-w-[40ch] text-xl leading-relaxed text-navy/90">
                Talk to Tidewell for a minute a day in the year after birth. It listens for warning signs,
                keeps your sleep, mood and blood pressure in one picture, and tells you plainly when to call your
                doctor.
              </p>
              <div className="mt-9">
                <WelcomeActions />
              </div>
              <p className="mt-10 border-t border-navy/10 pt-5 text-base text-navy/75">
                Warning signs checked first <span aria-hidden="true">·</span> Never diagnoses{" "}
                <span aria-hidden="true">·</span> Delete your data any time
              </p>
            </div>
          </div>
        </section>

        {/* ---------- the risk, in one sourced sentence ---------- */}
        <section aria-labelledby="why-title" className="bg-tide-deep text-white">
          <div className={`${container} grid gap-8 py-20 lg:grid-cols-[1fr_2fr] lg:py-24`}>
            <h2 id="why-title" className="font-display text-3xl font-semibold leading-tight sm:text-4xl">
              The riskiest stretch gets the least attention.
            </h2>
            <div>
              <p className="max-w-[34ch] font-display text-3xl leading-snug text-white sm:text-4xl">
                <span className="text-tide-light">53%</span> of pregnancy-related deaths in the US happened between a
                week and a year after birth. <span className="text-tide-light">84%</span> were judged preventable.
              </p>
              <p className="mt-6 max-w-[52ch] text-lg leading-relaxed text-white/85">
                Many new parents see a doctor only once in that year, around six weeks. Tidewell is for the nights in
                between.
              </p>
              <p className="mt-6 text-sm text-white/70">
                Source: CDC Maternal Mortality Review Committees, deaths from 2017 to 2019.
              </p>
            </div>
          </div>
        </section>

        {/* ---------- one night, three moments ---------- */}
        <section aria-labelledby="how-title" className={`${container} py-24`}>
          <h2 id="how-title" className="max-w-[18ch] font-display text-4xl font-semibold leading-tight sm:text-5xl">
            One night with Tidewell.
          </h2>
          <p className="mt-4 max-w-[48ch] text-xl leading-relaxed text-navy/85">
            One minute when you need it, nothing to fill in, and a clearer picture by morning.
          </p>
          <ol className="mt-14 grid gap-12 md:grid-cols-3 md:gap-8">
            {night.map((s) => (
              <li key={s.time} className="grid grid-cols-[6.5rem_1fr] items-start gap-5 md:block">
                <WindowPlate hour={s.hour} className="h-auto w-full max-w-[300px] rounded-[6px]" />
                <div>
                  <p className="font-display text-2xl text-tide-deep tabular md:mt-6">
                    <time>{s.time}</time>
                  </p>
                  <h3 className="mt-1 text-xl font-semibold">{s.title}</h3>
                  <p className="mt-2 max-w-[36ch] text-lg leading-relaxed text-navy/85">{s.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        {/* ---------- the tide: a sample on a clean surface ---------- */}
        <section aria-labelledby="tide-title" className="border-y border-navy/10 bg-sand/40">
          <div className={`${container} grid items-start gap-12 py-24 lg:grid-cols-[2fr_3fr]`}>
            <div>
              <h2 id="tide-title" className="font-display text-4xl font-semibold leading-tight sm:text-5xl">
                Your tide.
              </h2>
              <p className="mt-5 max-w-[40ch] text-xl leading-relaxed text-navy/90">
                Mood, sleep, pain and blood pressure in one picture, with a sentence about what changed. Take it to
                your next visit as a one-page summary.
              </p>
              <dl className="mt-10 divide-y divide-navy/10 border-y border-navy/10">
                {[
                  ["Voice first", "Talk, or type if you'd rather. Replies can be read aloud."],
                  ["A weekly mood check", "Ten questions from the Edinburgh Postnatal Depression Scale. A screening, never a diagnosis."],
                  ["It remembers you", "Day 18 after your C-section, Tuesday's headache: you never start over."],
                ].map(([t, d]) => (
                  <div key={t} className="py-4">
                    <dt className="text-lg font-semibold">{t}</dt>
                    <dd className="mt-1 text-lg leading-relaxed text-navy/85">{d}</dd>
                  </div>
                ))}
              </dl>
            </div>
            <TideSample />
          </div>
        </section>

        {/* ---------- what it is and isn't ---------- */}
        <section aria-labelledby="trust-title" className={`${container} grid gap-12 py-24 lg:grid-cols-2`}>
          <div>
            <h2 id="trust-title" className="max-w-[16ch] font-display text-4xl font-semibold leading-tight sm:text-5xl">
              A bridge between visits, not a doctor.
            </h2>
            <p className="mt-5 max-w-[42ch] text-xl leading-relaxed text-navy/85">
              Tidewell helps you notice what&apos;s changing and say it clearly. Your doctor, midwife or care team makes
              the decisions.
            </p>
          </div>
          <ul className="divide-y divide-navy/10 border-y border-navy/10">
            {promises.map(([t, b]) => (
              <li key={t} className="grid gap-1 py-5 sm:grid-cols-[14rem_1fr] sm:gap-6">
                <span className="text-lg font-semibold">{t}</span>
                <span className="text-lg leading-relaxed text-navy/85">{b}</span>
              </li>
            ))}
          </ul>
        </section>

        {/* ---------- closing night page ---------- */}
        <section aria-labelledby="cta-title" className="mt-auto bg-night text-white">
          <div className={`${container} pb-12 pt-20`}>
            <Mark className="size-12 text-white/80" />
            <h2 id="cta-title" className="mt-6 max-w-[18ch] font-display text-4xl font-semibold leading-tight sm:text-5xl">
              Start tonight. Setup takes two minutes.
            </h2>
            <p className="mt-4 max-w-[46ch] text-xl leading-relaxed text-white/85">
              Make an account, answer a few questions about your birth, then do your first check-in. Or look around
              with Maya, our demo parent.
            </p>
            <div className="mt-8">
              <WelcomeActions tone="dark" />
            </div>
            <footer className="mt-20 flex flex-col gap-3 border-t border-white/15 pt-8 text-base text-white/75 sm:flex-row sm:items-center sm:justify-between">
              <p className="flex items-center gap-2 font-display text-xl text-white">
                <Mark className="size-6 text-white/80" /> Tidewell
              </p>
              <p>
                Tidewell does not diagnose. In an emergency call{" "}
                <a href="tel:911" className={`rounded font-semibold text-white underline ${focusRingLight}`}>911</a>.
                Thoughts of harming yourself: call or text{" "}
                <a href="tel:988" className={`rounded font-semibold text-white underline ${focusRingLight}`}>988</a>.
              </p>
            </footer>
          </div>
        </section>
      </main>
    </div>
  );
}
