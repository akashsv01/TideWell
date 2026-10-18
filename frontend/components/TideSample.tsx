// An annotated sample of "Your tide" for the landing page. Clinical information on a clean paper
// surface: hairline grid, tabular numbers, two series that separate by lightness, and three
// numbered notes that point at the chart. The data is made up and labelled as a sample.

const days = [12, 13, 14, 15, 16, 17, 18];
const bp = [124, 126, 129, 132, 136, 141, 146]; // top number
const sleep = [5.5, 4.8, 4.2, 5.1, 3.9, 4.4, 4.0]; // hours
const headache = [false, false, false, false, true, true, true];

const W = 560;
const H = 260;
const L = 44;
const R = 44;
const T = 18;
const B = 40;
const x = (i: number) => L + (i * (W - L - R)) / (days.length - 1);
const yBp = (v: number) => T + ((160 - v) / (160 - 100)) * (H - T - B);
const ySleep = (v: number) => H - B - (v / 10) * (H - T - B) * 0.55;

export default function TideSample() {
  const line = bp.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${yBp(v).toFixed(1)}`).join(" ");
  const notes = [
    { n: 1, at: [x(6), yBp(146)], text: "Top number rose five days in a row and passed 140. Tidewell suggested a visit within 1 to 3 days." },
    { n: 2, at: [x(4), H - B + 14], text: "Headaches on three days running, shown as a mark under each day." },
    { n: 3, at: [x(4), ySleep(3.9)], text: "Sleep under five hours most nights. It says so, plainly, in the morning." },
  ];
  return (
    <figure className="rounded-[10px] bg-white p-5 shadow-paper ring-1 ring-navy/10 sm:p-7">
      <figcaption className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="font-display text-2xl font-semibold">Maya&apos;s tide, days 12 to 18</span>
        <span className="rounded-full bg-sand px-3 py-1 text-sm font-semibold">Sample data</span>
      </figcaption>
      <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-base text-navy/80">
        <span className="flex items-center gap-2">
          <span aria-hidden="true" className="h-1 w-6 rounded-full bg-chart-teal" /> Blood pressure, top number
        </span>
        <span className="flex items-center gap-2">
          <span aria-hidden="true" className="h-3 w-3 rounded-sm bg-chart-amber/60" /> Sleep, hours
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="mt-4 h-auto w-full" role="img" aria-label="Sample chart: blood pressure top number rising from 124 to 146 over seven days, sleep between 3.9 and 5.5 hours, headaches on the last three days.">
        {[100, 120, 140, 160].map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={yBp(v)} y2={yBp(v)} stroke="currentColor" strokeOpacity={v === 140 ? 0.55 : 0.1} strokeDasharray={v === 140 ? "5 4" : undefined} />
            <text x={L - 8} y={yBp(v) + 4} textAnchor="end" fontSize="13" fill="currentColor" fillOpacity="0.7" className="tabular">
              {v}
            </text>
          </g>
        ))}
        {sleep.map((v, i) => (
          <rect key={i} x={x(i) - 9} y={ySleep(v)} width="18" height={H - B - ySleep(v)} rx="3" className="fill-chart-amber" fillOpacity="0.45" />
        ))}
        <path d={line} fill="none" className="stroke-chart-teal" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        {bp.map((v, i) => (
          <circle key={i} cx={x(i)} cy={yBp(v)} r="4" className="fill-chart-teal" />
        ))}
        {days.map((d, i) => (
          <g key={d}>
            {headache[i] && <circle cx={x(i)} cy={H - B + 14} r="5" className="fill-terracotta" />}
            <text x={x(i)} y={H - 6} textAnchor="middle" fontSize="13" fill="currentColor" fillOpacity="0.7" className="tabular">
              Day {d}
            </text>
          </g>
        ))}
        {notes.map((n) => (
          <g key={n.n} transform={`translate(${n.at[0] + 14} ${n.at[1] - 14})`}>
            <circle r="11" className="fill-navy" />
            <text y="4.5" textAnchor="middle" fontSize="13" fontWeight="700" className="fill-foam">
              {n.n}
            </text>
          </g>
        ))}
      </svg>
      <ol className="mt-5 space-y-3 border-t border-navy/10 pt-5">
        {notes.map((n) => (
          <li key={n.n} className="flex gap-3 text-base leading-relaxed">
            <span aria-hidden="true" className="mt-0.5 grid size-6 shrink-0 place-items-center rounded-full bg-navy text-sm font-bold text-foam">
              {n.n}
            </span>
            <span>{n.text}</span>
          </li>
        ))}
      </ol>
      <p className="mt-4 text-sm text-navy/70">The dashed line marks 140, the top number to call about after birth.</p>
    </figure>
  );
}
