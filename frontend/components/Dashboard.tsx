"use client";

import { useCallback, useEffect, useId, useState } from "react";
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
import DayEditor from "@/components/DayEditor";
import { AlertIcon } from "@/components/icons";
import Waves from "@/components/Waves";
import { getOverview, getTrends } from "@/lib/api";
import { bpRise, moodSentence, shortDay, sleepSentence } from "@/lib/insights";
import { todayIso } from "@/lib/profile";
import { usePatientId } from "@/lib/session";
import { deliveryFromDayPostpartum, fillDailySeries } from "@/lib/tideSeries";
import { useReducedMotion } from "@/lib/useReducedMotion";
import type { Overview, TrendPoint } from "@/lib/types";
import { focusRing } from "@/lib/ui";

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

const enter = (i: number) => ({
  className: "motion-safe:animate-section-in",
  style: { animationDelay: `${i * 60}ms` },
});

function valued(points: TrendPoint[], key: keyof TrendPoint): number {
  return points.filter((p) => p[key] != null).length;
}

function ChartEmpty({ show, light = false }: { show: boolean; light?: boolean }) {
  if (!show) return null;
  return (
    <p
      className={`pointer-events-none absolute inset-0 flex items-center justify-center text-lg ${light ? "text-white/80" : "text-navy/70"}`}
    >
      Nothing logged yet
    </p>
  );
}

export default function Dashboard() {
  const patientId = usePatientId();
  const reduce = useReducedMotion();
  const drawIn = { isAnimationActive: !reduce, animationDuration: 500, animationEasing: "ease-out" } as const;
  const [raw, setRaw] = useState<TrendPoint[] | null>(null);
  const [ov, setOv] = useState<Overview | null>(null);
  const [failed, setFailed] = useState(false);
  // Empty until the client picks today (new Date() during prerender breaks cacheComponents).
  const [logDay, setLogDay] = useState("");
  const gradientId = `tide-${useId().replace(/:/g, "")}`;

  const load = useCallback(() => {
    if (!patientId) return;
    getOverview(patientId).then(setOv, () => {});
    getTrends(patientId).then(setRaw, () => {});
  }, [patientId]);

  useEffect(() => {
    if (!patientId) return;
    let cancelled = false;
    getOverview(patientId).then(
      (o) => !cancelled && setOv(o),
      () => {}
    );
    getTrends(patientId).then(
      (data) => {
        if (!cancelled) setRaw(data);
      },
      () => {
        if (!cancelled) setFailed(true);
      }
    );
    return () => {
      cancelled = true;
    };
  }, [patientId]);

  // /dashboard#log (and the home-page link) should land on the daily log section.
  useEffect(() => {
    if (!raw || !ov) return;
    if (typeof window === "undefined" || window.location.hash !== "#log") return;
    requestAnimationFrame(() => {
      document.getElementById("log")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, [raw, ov]);

  function editDay(day: string) {
    setLogDay(day);
    requestAnimationFrame(() => {
      document.getElementById("log")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  if (failed) {
    return (
      <p role="alert" className="rounded-3xl bg-white p-5 text-lg text-alert ring-2 ring-alert/30">
        We couldn&apos;t load your tide just now. Check your connection and refresh the page.
      </p>
    );
  }
  if (!raw || !ov || !patientId) {
    return (
      <p role="status" className="py-16 text-center text-xl">
        Reading the tide…
      </p>
    );
  }

  const deliveryDate = deliveryFromDayPostpartum(ov.day_postpartum);
  const points = fillDailySeries(raw, deliveryDate);
  const loggedAny = raw.length > 0;
  const today = todayIso();
  const selectedDay = logDay || today;
  const editorDay =
    selectedDay < deliveryDate ? deliveryDate : selectedDay > today ? today : selectedDay;

  const rise = bpRise(points);
  const lastMood = [...points].reverse().find((p) => p.mood !== null)?.mood ?? null;
  const summary = [moodSentence(points), sleepSentence(points)].filter(Boolean).join(" ");
  const lastWeek = points.slice(-7);
  const headacheDays = lastWeek.filter((p) => p.headache).length;
  const hasIncision = ov.delivery_method === "c-section" || points.some((p) => p.incision_pain != null);
  const epds = points.filter((p) => p.epds_score != null);
  const item10 = epds.some((p) => p.item_10_alert);

  const moodN = valued(points, "mood");
  const bpN = valued(points, "bp_sys");
  const sleepN = valued(points, "sleep_hrs");
  const painN = valued(points, "pain");
  const showDots = (n: number) => (n > 0 && n < 3 ? { r: 4 } : false);

  const facts = [
    `Day ${ov.day_postpartum} after ${ov.delivery_method === "c-section" ? "a C-section" : "a vaginal birth"}`,
    ov.feeding_type === "breastfeeding"
      ? "Breastfeeding"
      : ov.feeding_type === "mixed"
        ? "Breast and formula"
        : ov.feeding_type === "formula"
          ? "Formula feeding"
          : null,
    ov.history_mental_health ? "Mood history noted" : null,
    ...ov.history_pregnancy_complications.map((c) => c.charAt(0).toUpperCase() + c.slice(1)),
  ].filter(Boolean);

  // Table: only days that have some logged data (plus EPDS-only days).
  const tableRows = [...raw].reverse();

  return (
    <div className="space-y-12">
      <header {...enter(0)}>
        <h1 className="font-display text-4xl leading-tight">
          {ov.name ? `${ov.name}'s tide` : "Your tide"}
        </h1>
        {facts.length > 0 && (
          <ul className="mt-4 flex flex-wrap gap-2" aria-label="About you">
            {facts.map((f) => (
              <li key={f} className="rounded-full bg-sand/80 px-3 py-1 text-base font-semibold">
                {f}
              </li>
            ))}
          </ul>
        )}
        <p className="mt-4 text-lg text-navy/80">
          {!loggedAny
            ? "Nothing logged yet — your charts are ready when you are."
            : points.length === 1
              ? "Your first day of check-ins."
              : `Your last ${points.length} days.`}
        </p>
        {summary && <p className="mt-2 max-w-[44ch] text-xl leading-relaxed">{summary}</p>}
      </header>

      <section
        aria-labelledby="mood-title"
        className="-mx-5 overflow-hidden bg-navy text-white motion-safe:animate-section-in sm:mx-0 sm:rounded-3xl"
        style={enter(1).style}
      >
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
          <div className="relative mt-4 h-56">
            <ChartEmpty show={moodN === 0} light />
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
                  {...drawIn}
                  type="monotone"
                  dataKey="mood"
                  name="Mood"
                  stroke="#6fd0d4"
                  strokeWidth={3}
                  fill={`url(#${gradientId})`}
                  connectNulls={false}
                  dot={showDots(moodN)}
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
          className="flex gap-4 rounded-3xl border-l-8 border-chart-amber bg-sand/70 p-5 motion-safe:animate-section-in sm:p-6"
          style={enter(2).style}
        >
          <AlertIcon className="mt-1 size-7 shrink-0 text-navy" />
          <div>
            <h2 id="bp-callout-title" className="font-display text-2xl">
              Your blood pressure has gone up
            </h2>
            <p className="mt-2 text-lg leading-relaxed">
              Your last four readings were {rise.readings.map((r) => `${r.sys}/${r.dia}`).join(", ")}.{" "}
              {rise.atOrAbove140
                ? "After birth, a reading of 140/90 or higher is a reason to call your care team."
                : "It is worth mentioning at your next visit."}
            </p>
          </div>
        </section>
      )}

      <section aria-labelledby="bp-title" {...enter(3)}>
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
        <div className="relative mt-4 h-56">
          <ChartEmpty show={bpN === 0} />
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
              <Line
                {...drawIn}
                type="monotone"
                dataKey="bp_sys"
                name="Top number"
                stroke={TEAL}
                strokeWidth={2.5}
                connectNulls={false}
                dot={showDots(bpN)}
                activeDot={{ r: 6, stroke: "#f4f9f9", strokeWidth: 2 }}
              />
              <Line
                {...drawIn}
                type="monotone"
                dataKey="bp_dia"
                name="Bottom number"
                stroke={AMBER}
                strokeWidth={2.5}
                connectNulls={false}
                dot={showDots(bpN)}
                activeDot={{ r: 6, stroke: "#f4f9f9", strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-1 text-base text-navy/80">The dashed line marks 140 on the top number.</p>
      </section>

      <section aria-labelledby="headache-title" {...enter(4)}>
        <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
          <h2 id="headache-title" className="font-display text-2xl">
            Headaches
          </h2>
          <p className="text-lg">
            {headacheDays === 0 ? "None in the last 7 days" : `${headacheDays} of the last ${lastWeek.length} days`}
          </p>
        </div>
        <ol className="mt-4 flex gap-1.5" aria-label="Headache by day, oldest first">
          {points.map((p) => (
            <li key={p.day} className="flex flex-1 flex-col items-center gap-1.5">
              <span
                className={`block h-8 w-full max-w-7 rounded-full transition-colors duration-150 ${p.headache ? "bg-chart-amber" : "bg-navy/10"}`}
                title={`${shortDay(p.day)}: ${p.headache ? "headache" : "no headache"}`}
              />
              <span className="sr-only">
                {shortDay(p.day)}: {p.headache ? "headache" : "no headache"}
              </span>
            </li>
          ))}
        </ol>
        <p className="mt-2 text-base text-navy/80">Amber marks a day you mentioned a headache.</p>
      </section>

      {epds.length > 0 && (
        <section aria-labelledby="epds-title" {...enter(5)}>
          <h2 id="epds-title" className="font-display text-2xl">
            Weekly mood check
          </h2>
          <p className="text-base text-navy/80">
            Out of 30. Higher means a harder week. 10 or more is worth raising with your care team.
          </p>
          <ul className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {epds.map((p) => (
              <li key={p.day} className="rounded-2xl bg-sand/70 p-4">
                <p className="text-base text-navy/80">
                  {p.day_postpartum != null ? `Day ${p.day_postpartum}` : shortDay(p.day)}
                </p>
                <p className="font-display text-3xl tabular-nums">
                  {p.epds_score}
                  <span className="text-xl text-navy/70"> / 30</span>
                </p>
              </li>
            ))}
          </ul>
          {item10 && (
            <p className="mt-4 flex gap-3 rounded-2xl border-l-8 border-alert bg-white p-4 text-lg ring-1 ring-alert/20">
              <AlertIcon className="mt-1 size-6 shrink-0 text-alert" />
              <span>
                A recent mood check mentioned thoughts of self-harm. If they come back, call or text{" "}
                <a href="tel:988" className="font-semibold underline underline-offset-4">
                  988
                </a>{" "}
                any time.
              </span>
            </p>
          )}
        </section>
      )}

      <div className="grid gap-12 motion-safe:animate-section-in sm:grid-cols-2 sm:gap-8" style={enter(6).style}>
        <section aria-labelledby="sleep-title">
          <h2 id="sleep-title" className="font-display text-2xl">
            Sleep
          </h2>
          <p className="text-base text-navy/80">Hours a night</p>
          <div className="relative mt-3 h-44">
            <ChartEmpty show={sleepN === 0} />
            <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 320, height: 176 }}>
              <BarChart data={points} margin={{ top: 8, right: 4, bottom: 0, left: -20 }}>
                <CartesianGrid vertical={false} stroke={GRID} />
                <XAxis {...xAxisProps} tick={AXIS} />
                <YAxis domain={[0, 10]} ticks={[0, 5, 10]} tick={AXIS} tickLine={false} axisLine={false} />
                <Tooltip cursor={{ fill: "rgba(11,37,69,0.06)" }} content={<ChartTip units={{ Sleep: " hours" }} />} {...tipMotion} />
                <Bar {...drawIn} dataKey="sleep_hrs" name="Sleep" fill={TEAL} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section aria-labelledby="pain-title">
          <h2 id="pain-title" className="font-display text-2xl">
            Pain
          </h2>
          <p className="text-base text-navy/80">
            0 is none, 10 is the worst{hasIncision ? ". Amber is your incision." : ""}
          </p>
          <div className="relative mt-3 h-44">
            <ChartEmpty show={painN === 0} />
            <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 320, height: 176 }}>
              <LineChart data={points} margin={{ top: 8, right: 4, bottom: 0, left: -20 }}>
                <CartesianGrid vertical={false} stroke={GRID} />
                <XAxis {...xAxisProps} tick={AXIS} />
                <YAxis domain={[0, 10]} ticks={[0, 5, 10]} tick={AXIS} tickLine={false} axisLine={false} />
                <Tooltip content={<ChartTip units={{ Pain: " / 10", Incision: " / 10" }} />} {...tipMotion} />
                <Line
                  {...drawIn}
                  type="monotone"
                  dataKey="pain"
                  name="Pain"
                  stroke={TEAL}
                  strokeWidth={2.5}
                  connectNulls={false}
                  dot={showDots(painN)}
                  activeDot={{ r: 6, stroke: "#f4f9f9", strokeWidth: 2 }}
                />
                {hasIncision && (
                  <Line
                    {...drawIn}
                    type="monotone"
                    dataKey="incision_pain"
                    name="Incision"
                    stroke={AMBER}
                    strokeWidth={2.5}
                    connectNulls={false}
                    dot={showDots(valued(points, "incision_pain"))}
                    activeDot={{ r: 6, stroke: "#f4f9f9", strokeWidth: 2 }}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>

      {tableRows.length > 0 && (
        <details className="group">
          <summary
            className={`inline-flex min-h-12 cursor-pointer items-center rounded-full border-2 border-navy px-5 font-semibold transition-transform duration-150 ease-out motion-safe:active:scale-[0.97] ${focusRing}`}
          >
            View the numbers
          </summary>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[48rem] border-collapse text-left text-base">
              <caption className="sr-only">Daily check-in numbers</caption>
              <thead>
                <tr className="border-b-2 border-navy/20">
                  <th scope="col" className="py-2 pr-4 font-semibold">
                    Date
                  </th>
                  <th scope="col" className="py-2 pr-4 font-semibold">
                    Day
                  </th>
                  <th scope="col" className="py-2 pr-4 font-semibold">
                    Mood
                  </th>
                  <th scope="col" className="py-2 pr-4 font-semibold">
                    Blood pressure
                  </th>
                  <th scope="col" className="py-2 pr-4 font-semibold">
                    Sleep
                  </th>
                  <th scope="col" className="py-2 pr-4 font-semibold">
                    Pain
                  </th>
                  <th scope="col" className="py-2 pr-4 font-semibold">
                    Incision
                  </th>
                  <th scope="col" className="py-2 pr-4 font-semibold">
                    Headache
                  </th>
                  <th scope="col" className="py-2 pr-4 font-semibold">
                    Mood check
                  </th>
                  <th scope="col" className="py-2 font-semibold">
                    <span className="sr-only">Edit</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {tableRows.map((p) => (
                  <tr key={p.day} className="border-b border-navy/10">
                    <th scope="row" className="py-2 pr-4 font-normal">
                      {shortDay(p.day)}
                    </th>
                    <td className="py-2 pr-4 tabular-nums">{p.day_postpartum ?? "–"}</td>
                    <td className="py-2 pr-4 tabular-nums">{p.mood ?? "–"}</td>
                    <td className="py-2 pr-4 tabular-nums">
                      {p.bp_sys !== null && p.bp_dia !== null ? `${p.bp_sys}/${p.bp_dia}` : "–"}
                    </td>
                    <td className="py-2 pr-4 tabular-nums">{p.sleep_hrs !== null ? `${p.sleep_hrs} h` : "–"}</td>
                    <td className="py-2 pr-4 tabular-nums">{p.pain ?? "–"}</td>
                    <td className="py-2 pr-4 tabular-nums">{p.incision_pain ?? "–"}</td>
                    <td className="py-2 pr-4">{p.headache ? "Yes" : "–"}</td>
                    <td className="py-2 pr-4 tabular-nums">
                      {p.epds_score != null ? `${p.epds_score} / 30` : "–"}
                    </td>
                    <td className="py-2">
                      <button
                        type="button"
                        onClick={() => editDay(p.day)}
                        className={`rounded-md px-2 py-1 text-base font-semibold underline underline-offset-4 transition-transform duration-150 ease-out motion-safe:active:scale-[0.97] ${focusRing}`}
                      >
                        Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}

      <DayEditor
        patientId={patientId}
        demo={ov.demo}
        deliveryDate={deliveryDate}
        deliveryMethod={ov.delivery_method}
        points={raw}
        day={editorDay}
        onDayChange={setLogDay}
        onSaved={load}
      />

      <p className="text-base text-navy/80">Tidewell does not diagnose. Share these numbers with your care team.</p>
    </div>
  );
}
