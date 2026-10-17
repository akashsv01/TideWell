"use client";

import { useEffect, useId, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import ChartTip from "@/components/ChartTip";
import { AlertIcon } from "@/components/icons";
import Waves from "@/components/Waves";
import { getTrends } from "@/lib/api";
import { usePatientId } from "@/lib/identity";
import { bpRise, moodSentence, shortDay, sleepSentence } from "@/lib/insights";
import type { TrendPoint } from "@/lib/types";

// Chart colors. Teal and amber were checked together for color-blind separation.
const TEAL = "#06909a";
const AMBER = "#c4761b";
const GRID = "rgba(11,37,69,0.12)";
const AXIS = { fill: "#0b2545", fontSize: 13 } as const;
const AXIS_LIGHT = { fill: "#e3f1f2", fontSize: 13 } as const;

const xAxisProps = {
  dataKey: "day",
  tickFormatter: shortDay,
  minTickGap: 28,
  tickLine: false,
  axisLine: false,
  interval: "preserveStartEnd" as const,
};

const tipMotion = { isAnimationActive: false } as const;

export default function Dashboard() {
  const { patientId } = usePatientId();
  const [points, setPoints] = useState<TrendPoint[] | null>(null);
  const [failed, setFailed] = useState(false);
  const gradientId = `tide-${useId().replace(/:/g, "")}`;

  useEffect(() => {
    if (!patientId) return;
    let cancelled = false;
    getTrends(patientId).then(
      (data) => {
        if (!cancelled) setPoints(data);
      },
      () => {
        if (!cancelled) setFailed(true);
      }
    );
    return () => {
      cancelled = true;
    };
  }, [patientId]);

  if (failed) {
    return (
      <p role="alert" className="rounded-3xl bg-white p-5 text-lg text-alert ring-2 ring-alert/30">
        We couldn&apos;t load your tide just now. Check your connection and refresh the page.
      </p>
    );
  }
  if (!points) {
    return (
      <p role="status" className="py-16 text-center text-xl">
        Reading the tide…
      </p>
    );
  }
  if (points.length === 0) {
    return (
      <p className="rounded-3xl bg-sand/70 p-6 text-xl leading-relaxed">
        Nothing to show yet. Your tide appears after your first check-in.
      </p>
    );
  }

  const rise = bpRise(points);
  const lastMood = [...points].reverse().find((p) => p.mood !== null)?.mood ?? null;
  const summary = [moodSentence(points), sleepSentence(points)].filter(Boolean).join(" ");

  return (
    <div className="space-y-12">
      <header>
        <h1 className="font-display text-4xl leading-tight">Your last {points.length} days</h1>
        {summary && <p className="mt-3 max-w-[44ch] text-xl leading-relaxed">{summary}</p>}
      </header>

      {/* The tide: mood over time, on a navy basin with a gentle wave along the top. */}
      <section aria-labelledby="mood-title" className="-mx-5 overflow-hidden bg-navy text-white sm:mx-0 sm:rounded-3xl">
        <Waves
          className="relative h-8"
          layers={[
            { color: "#13828a", amp: 8, cycles: 3, top: 110, seconds: 30, opacity: 0.5 },
            { color: "#0b2545", amp: 8, cycles: 2, top: 130, seconds: 22, reverse: true },
          ]}
        />
        <div className="-mt-px px-5 pb-6 sm:px-8">
          <div className="flex items-baseline justify-between gap-4">
            <h2 id="mood-title" className="font-display text-2xl">
              Mood
            </h2>
            {lastMood !== null && <p className="text-lg text-white/85">Latest: {lastMood} out of 10</p>}
          </div>
          <div className="mt-4 h-56">
            <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 320, height: 224 }}>
              <AreaChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
                <defs>
                  <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#6fd0d4" stopOpacity={0.55} />
                    <stop offset="100%" stopColor="#6fd0d4" stopOpacity={0.04} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.14)" />
                <XAxis {...xAxisProps} tick={AXIS_LIGHT} />
                <YAxis domain={[0, 10]} ticks={[0, 5, 10]} tick={AXIS_LIGHT} tickLine={false} axisLine={false} />
                <Tooltip content={<ChartTip units={{ Mood: " / 10" }} />} {...tipMotion} />
                <Area
                  type="monotone"
                  dataKey="mood"
                  name="Mood"
                  stroke="#6fd0d4"
                  strokeWidth={3}
                  fill={`url(#${gradientId})`}
                  dot={false}
                  activeDot={{ r: 6, fill: "#6fd0d4", stroke: "#0b2545", strokeWidth: 2 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      {rise && (
        <section
          aria-labelledby="bp-callout-title"
          className="flex gap-4 rounded-3xl border-l-8 border-chart-amber bg-sand/70 p-5 sm:p-6"
        >
          <AlertIcon className="mt-1 size-7 shrink-0 text-navy" />
          <div>
            <h2 id="bp-callout-title" className="font-display text-2xl">
              Your blood pressure has gone up
            </h2>
            <p className="mt-2 text-lg leading-relaxed">
              Your last four readings were{" "}
              {rise.readings.map((r) => `${r.sys}/${r.dia}`).join(", ")}.{" "}
              {rise.atOrAbove140
                ? "After birth, a reading of 140/90 or higher is a reason to call your care team."
                : "It is worth mentioning at your next visit."}
            </p>
          </div>
        </section>
      )}

      <section aria-labelledby="bp-title">
        <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
          <h2 id="bp-title" className="font-display text-2xl">
            Blood pressure
          </h2>
          <ul className="flex gap-5 text-base" aria-label="Legend">
            <li className="flex items-center gap-2">
              <span aria-hidden="true" className="h-1 w-6 rounded-full" style={{ background: TEAL }} />
              Top number
            </li>
            <li className="flex items-center gap-2">
              <span aria-hidden="true" className="h-1 w-6 rounded-full" style={{ background: AMBER }} />
              Bottom number
            </li>
          </ul>
        </div>
        <div className="mt-4 h-56">
          <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 320, height: 224 }}>
            <LineChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
              <CartesianGrid vertical={false} stroke={GRID} />
              <XAxis {...xAxisProps} tick={AXIS} />
              <YAxis domain={[60, 160]} ticks={[60, 90, 120, 150]} tick={AXIS} tickLine={false} axisLine={false} />
              <ReferenceLine
                y={140}
                stroke="#0b2545"
                strokeDasharray="5 4"
                label={{ value: "140", position: "insideTopLeft", fill: "#0b2545", fontSize: 13, dy: -14 }}
              />
              <Tooltip content={<ChartTip units={{ "Top number": " mmHg", "Bottom number": " mmHg" }} />} {...tipMotion} />
              <Line type="monotone" dataKey="bp_sys" name="Top number" stroke={TEAL} strokeWidth={2.5} dot={false} activeDot={{ r: 6, stroke: "#f4f9f9", strokeWidth: 2 }} />
              <Line type="monotone" dataKey="bp_dia" name="Bottom number" stroke={AMBER} strokeWidth={2.5} dot={false} activeDot={{ r: 6, stroke: "#f4f9f9", strokeWidth: 2 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-1 text-base text-navy/80">The dashed line marks 140 on the top number.</p>
      </section>

      <div className="grid gap-12 sm:grid-cols-2 sm:gap-8">
        <section aria-labelledby="sleep-title">
          <h2 id="sleep-title" className="font-display text-2xl">
            Sleep
          </h2>
          <p className="text-base text-navy/80">Hours a night</p>
          <div className="mt-3 h-44">
            <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 320, height: 176 }}>
              <BarChart data={points} margin={{ top: 8, right: 4, bottom: 0, left: -20 }}>
                <CartesianGrid vertical={false} stroke={GRID} />
                <XAxis {...xAxisProps} tick={AXIS} />
                <YAxis domain={[0, 10]} ticks={[0, 5, 10]} tick={AXIS} tickLine={false} axisLine={false} />
                <Tooltip cursor={{ fill: "rgba(11,37,69,0.06)" }} content={<ChartTip units={{ Sleep: " hours" }} />} {...tipMotion} />
                <Bar dataKey="sleep_hrs" name="Sleep" fill={TEAL} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section aria-labelledby="pain-title">
          <h2 id="pain-title" className="font-display text-2xl">
            Pain
          </h2>
          <p className="text-base text-navy/80">0 is none, 10 is the worst</p>
          <div className="mt-3 h-44">
            <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 320, height: 176 }}>
              <LineChart data={points} margin={{ top: 8, right: 4, bottom: 0, left: -20 }}>
                <CartesianGrid vertical={false} stroke={GRID} />
                <XAxis {...xAxisProps} tick={AXIS} />
                <YAxis domain={[0, 10]} ticks={[0, 5, 10]} tick={AXIS} tickLine={false} axisLine={false} />
                <Tooltip content={<ChartTip units={{ Pain: " / 10" }} />} {...tipMotion} />
                <Line type="monotone" dataKey="pain" name="Pain" stroke={TEAL} strokeWidth={2.5} dot={false} activeDot={{ r: 6, stroke: "#f4f9f9", strokeWidth: 2 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>

      <details className="group">
        <summary className="inline-flex min-h-12 cursor-pointer items-center rounded-full border-2 border-navy px-5 font-semibold focus:outline-none focus-visible:ring-4 focus-visible:ring-navy focus-visible:ring-offset-2 focus-visible:ring-offset-foam">
          View the numbers
        </summary>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[30rem] border-collapse text-left text-base">
            <caption className="sr-only">Daily check-in numbers</caption>
            <thead>
              <tr className="border-b-2 border-navy/20">
                <th scope="col" className="py-2 pr-4 font-semibold">Date</th>
                <th scope="col" className="py-2 pr-4 font-semibold">Mood</th>
                <th scope="col" className="py-2 pr-4 font-semibold">Blood pressure</th>
                <th scope="col" className="py-2 pr-4 font-semibold">Sleep</th>
                <th scope="col" className="py-2 font-semibold">Pain</th>
              </tr>
            </thead>
            <tbody>
              {[...points].reverse().map((p) => (
                <tr key={p.day} className="border-b border-navy/10">
                  <th scope="row" className="py-2 pr-4 font-normal">{shortDay(p.day)}</th>
                  <td className="py-2 pr-4 tabular-nums">{p.mood ?? "–"}</td>
                  <td className="py-2 pr-4 tabular-nums">
                    {p.bp_sys !== null && p.bp_dia !== null ? `${p.bp_sys}/${p.bp_dia}` : "–"}
                  </td>
                  <td className="py-2 pr-4 tabular-nums">{p.sleep_hrs !== null ? `${p.sleep_hrs} h` : "–"}</td>
                  <td className="py-2 tabular-nums">{p.pain ?? "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>

      <p className="text-base text-navy/80">
        Tidewell does not diagnose. Share these numbers with your care team.
      </p>
    </div>
  );
}
