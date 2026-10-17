import Waves from "@/components/Waves";

// The hero illustration: a phone mid check-in. The orb's water drifts, the voice bars move, and
// Tidewell's reply rises in, rests, and fades on a 9 s loop. Pure CSS (transform + opacity), so it
// stays smooth while the page loads; with reduced motion it is a still picture.

const BARS = [0.55, 0.9, 0.7, 1, 0.6, 0.85, 0.5, 0.75, 0.95, 0.65, 0.8, 0.55];

export default function HeroDevice() {
  return (
    <div aria-hidden="true" className="relative mx-auto w-full max-w-[20rem] select-none">
      {/* soft glow + floating shapes behind the phone */}
      <div className="absolute -inset-10 rounded-full bg-tide-light/25 blur-3xl" />
      <div className="float-slow absolute -left-6 top-10 size-16 rounded-[45%_55%_60%_40%] bg-sand" />
      <div
        className="float-slow absolute -right-4 bottom-24 size-10 rounded-full bg-tide/30"
        style={{ animationDelay: "-3s" }}
      />

      <div className="relative rounded-[2.75rem] bg-navy p-3 shadow-[0_30px_60px_-20px_rgba(11,37,69,0.55)]">
        <div className="overflow-hidden rounded-[2.2rem] bg-foam px-5 pb-6 pt-7">
          <div className="flex items-center justify-between text-[0.8rem] font-semibold text-navy/70">
            <span className="font-display text-base text-tide-deep">Tidewell</span>
            <span>Day 18</span>
          </div>
          <p className="mt-4 text-center font-display text-xl leading-tight text-navy">How are you today?</p>

          {/* the orb */}
          <div className="relative mx-auto mt-5 grid size-40 place-items-center">
            <span className="absolute size-36 rounded-full border-2 border-tide/60 motion-safe:animate-ripple" />
            <span
              className="absolute size-36 rounded-full border-2 border-tide/60 motion-safe:animate-ripple"
              style={{ animationDelay: "1.3s" }}
            />
            <span className="relative size-32 overflow-hidden rounded-full bg-navy ring-4 ring-white">
              <span className="absolute inset-0" style={{ transform: "translateY(42%)" }}>
                <Waves
                  className="absolute inset-0"
                  layers={[
                    { color: "#13828a", amp: 7, cycles: 2, top: 8, seconds: 9, opacity: 0.85 },
                    { color: "#0e6a70", amp: 6, cycles: 3, top: 16, seconds: 7, reverse: true },
                  ]}
                />
              </span>
              {/* voice bars */}
              <span className="absolute inset-0 flex items-center justify-center gap-[3px]">
                {BARS.map((h, i) => (
                  <span
                    key={i}
                    className="voice-bar block w-[3px] rounded-full bg-white"
                    style={{ height: `${h * 38}px`, animationDelay: `${(i % 6) * -0.17}s` }}
                  />
                ))}
              </span>
            </span>
          </div>
          <p className="mt-2 text-center text-sm font-semibold text-navy">Listening…</p>

          {/* the reply */}
          <div className="bubble-cycle mt-4 rounded-2xl bg-sand/90 p-3.5 text-[0.82rem] leading-snug text-navy">
            Four hours of sleep and another headache is a lot. Your blood pressure has crept up this
            week, so let&apos;s get it checked. Would Tuesday at 10 work?
          </div>
        </div>
      </div>
    </div>
  );
}
