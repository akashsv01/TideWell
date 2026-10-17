// Decorative layered waves. Each layer is a sine path drawn twice as wide as its box and
// slid left forever, so the loop is seamless. With reduced motion the layers stay still.

export type WaveLayer = {
  color: string;
  /** Height of the wave crest, in viewBox units (the viewBox is 2000 x 200). */
  amp: number;
  /** Whole wave cycles that fit in the visible width. */
  cycles: number;
  /** Where the middle of the wave sits, 0 (top) to 200 (bottom). */
  top: number;
  /** Seconds for one slide across. Bigger is calmer. */
  seconds: number;
  reverse?: boolean;
  opacity?: number;
};

function wavePath({ amp, cycles, top }: WaveLayer) {
  const total = cycles * 2;
  const steps = total * 20;
  let d = `M0 200 L0 ${top.toFixed(1)}`;
  for (let i = 1; i <= steps; i++) {
    const x = (2000 * i) / steps;
    const y = top + Math.sin((i / steps) * total * Math.PI * 2) * amp;
    d += ` L${x.toFixed(1)} ${y.toFixed(1)}`;
  }
  return `${d} L2000 200 Z`;
}

export default function Waves({
  layers,
  className = "",
}: {
  layers: WaveLayer[];
  className?: string;
}) {
  return (
    <div aria-hidden="true" className={`pointer-events-none overflow-hidden ${className}`}>
      {layers.map((layer, i) => (
        <svg
          key={i}
          viewBox="0 0 2000 200"
          preserveAspectRatio="none"
          focusable="false"
          className="wave-layer absolute bottom-0 left-0 h-full w-[200%] motion-safe:animate-drift"
          style={{
            animationDuration: `${layer.seconds}s`,
            animationDirection: layer.reverse ? "reverse" : "normal",
            opacity: layer.opacity ?? 1,
          }}
        >
          <path d={wavePath(layer)} fill={layer.color} />
        </svg>
      ))}
    </div>
  );
}
