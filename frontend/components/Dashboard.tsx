"use client";

import Link from "next/link";
import { useCallback, useEffect, useId, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import ChartTip from "@/components/ChartTip";
import DayEditor from "@/components/DayEditor";
import { MomentPlate } from "@/components/plates/Gouache";
import { AlertIcon } from "@/components/icons";
import { getOverview, getTrends } from "@/lib/api";
import { bpRise, moodSentence, shortDay, sleepSentence } from "@/lib/insights";
import { todayIso } from "@/lib/profile";
import { usePatientId } from "@/lib/session";
import { deliveryFromDayPostpartum, fillDailySeries } from "@/lib/tideSeries";
import { useNightShown } from "@/lib/night";
import { useReducedMotion } from "@/lib/useReducedMotion";
import type { Overview, TrendPoint } from "@/lib/types";
import { btnPrimary, focusRing } from "@/lib/ui";

// Chart colors. Teal and amber were checked together for color-blind separation.
// Day and night pairs match --color-chart-teal / --color-chart-amber in globals.css (recharts
// draws with SVG attributes, so the component picks the pair rather than reading the token).
const CHART = {
  day: { teal: "#2d5a48", amber: "#b3801f", dotRing: "#fffdf8" },
  night: { teal: "#8cc2a6", amber: "#e2b453", dotRing: "#18261f" },
};
const GRID = "rgba(11,37,69,0.12)";
const AXIS = { fill: "#1b2a22", fontSize: 13 } as const;

const xAxisProps = {
  dataKey: "day",
  tickFormatter: shortDay,
  minTickGap: 28,
  tickLine: false,
  axisLine: false,
  interval: "preserveStartEnd" as const,
};

const tipMotion = { isAnimationActive: false } as const;

function valued(points: TrendPoint[], key: keyof TrendPoint): number {
  return points.filter((p) => p[key] != null).length;
}

function ChartEmpty({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <p className="pointer-events-none absolute inset-0 flex items-center justify-center text-lg text-navy/70">
      Nothing logged yet
    </p>
  );
}

export default function Dashboard() {
  const patientId = usePatientId();
  const reduce = useReducedMotion();
  const palette = CHART[useNightShown() ? "night" : "day"];
  const TEAL = palette.teal;
  const AMBER = palette.amber;
  const drawIn = {
    isAnimationActive: !reduce,
    animationDuration: 500,
    animationEasing: "ease-out",
  } as const;
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
      <p role="alert" className="rounded-2xl bg-white p-5 text-lg text-alert ring-2 ring-alert/30">
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
  // Mood is the mood check (EPDS, out of 30) when one exists; otherwise the 0-10 check-in mood.
  const epdsMode = points.some((p) => p.epds_score != null);
  const moodKey = epdsMode ? "epds_score" : "mood";
  const lastMood = [...points].reverse().find((p) => p.mood != null)?.mood ?? null;
  const summary = [moodSentence(points), sleepSentence(points)].filter(Boolean).join(" ");
  const lastWeek = points.slice(-7);
  const headacheDays = lastWeek.filter((p) => p.headache).length;
  const hasIncision = ov.delivery_method === "c-section" || points.some((p) => p.incision_pain != null);
  const epds = points.filter((p) => p.epds_score != null);
  const latestEpds = epds[epds.length - 1] ?? null;
  const item10 = epds.some((p) => p.item_10_alert);

  const moodN = valued(points, "mood");
  const bpN = valued(points, "bp_sys");
  const sleepN = valued(points, "sleep_hrs");
  const painN = valued(points, "pain");
  const hrN = valued(points, "resting_hr");
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
  ].filter(Boolean) as string[];
  const loggedDays = raw.length;

  // Table: only days that have some logged data (plus EPDS-only days).
  const tableRows = [...raw].reverse();

  return (
    <div className="space-y-12">
      <header>
        <h1 className="font-display text-4xl font-semibold leading-tight">Your tide</h1>
        <p className="mt-3 text-lg text-navy/80">
          {facts.length > 0 && <span>{facts.join(". ")}. </span>}
          {!loggedAny ? "Nothing logged yet." : `${loggedDays} ${loggedDays === 1 ? "day" : "days"} logged so far.`}
        </p>
        {summary && <p className="mt-4 max-w-[52ch] text-xl leading-relaxed">{summary}</p>}
      </header>

      {!loggedAny ? (
        <section
          aria-labelledby="empty-title"
          className="flex items-start gap-6 rounded-2xl bg-white p-6 shadow-paper ring-1 ring-navy/10 sm:p-8"
        >
          <div className="min-w-0 flex-1">
            <h2 id="empty-title" className="font-display text-2xl font-semibold">
              Your charts start with your first check-in
            </h2>
            <p className="mt-2 max-w-[52ch] text-lg leading-relaxed">
              Talk to Tidewell for a minute, or type your numbers into the form below. Mood, sleep, pain and blood
              pressure appear here, day by day.
            </p>
            <Link href="/home" className={`${btnPrimary} mt-5`}>
              Check in now
            </Link>
          </div>
          {/* the morning tide in a notebook: what this page becomes; never beside clinical numbers */}
          <div aria-hidden="true" className="hidden w-28 shrink-0 overflow-hidden rounded-md sm:block">
            <MomentPlate moment="morning" className="block h-auto w-full" />
          </div>
        </section>
      ) : (
        <>
          <section aria-labelledby="mood-title">
            <h2 id="mood-title" className="font-display text-2xl font-semibold">
              {epdsMode ? "Weekly mood check" : "Mood"}
            </h2>
            <p className="text-base text-navy/80">
              {epdsMode
                ? "Scored out of 30. Lower is better. A score of 10 or more is worth raising with your care team."
                : "From your check-ins, 0 to 10. Higher is better."}
            </p>
            {epdsMode && latestEpds && (
              <p className="mt-4 max-w-[52ch] text-xl leading-relaxed">
                Your latest mood check
                {latestEpds.day_postpartum != null ? `, on day ${latestEpds.day_postpartum},` : ""} scored{" "}
                <strong className="font-semibold tabular-nums">{latestEpds.epds_score} out of 30</strong>.{" "}
                {(latestEpds.epds_score ?? 0) >= 10
                  ? "That is in the range worth raising with your care team."
                  : "That is under 10."}
              </p>
            )}
            {!epdsMode && lastMood !== null && (
              <p className="mt-4 text-xl">
                Latest: <strong className="font-semibold tabular-nums">{lastMood} out of 10</strong>
              </p>
            )}
            {(epdsMode ? epds.length >= 2 : true) && (
              <div className="relative mt-4 h-56 rounded-2xl bg-white p-3 shadow-paper ring-1 ring-navy/10">
                <ChartEmpty show={!epdsMode && moodN === 0} />
                <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 320, height: 200 }}>
                  <AreaChart data={epdsMode ? epds : points} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
                    <defs>
                      <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={TEAL} stopOpacity={0.22} />
                        <stop offset="100%" stopColor={TEAL} stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid vertical={false} stroke={GRID} />
                    {epdsMode && (
                      <ReferenceArea
                        y1={10}
                        y2={30}
                        fill="#b3801f"
                        fillOpacity={0.1}
                        label={{
                          value: "10 or more: talk to your care team",
                          position: "insideTopRight",
                          fill: "#1b2a22",
                          fontSize: 13,
                        }}
                      />
                    )}
                    <XAxis {...xAxisProps} tick={AXIS} />
                    <YAxis
                      domain={epdsMode ? [0, 30] : [0, 10]}
                      ticks={epdsMode ? [0, 10, 20, 30] : [0, 5, 10]}
                      tick={AXIS}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip content={<ChartTip units={{ "Mood check": " / 30", Mood: " / 10" }} />} {...tipMotion} />
                    <Area
                      {...drawIn}
                      type="monotone"
                      dataKey={moodKey}
                      name={epdsMode ? "Mood check" : "Mood"}
                      stroke={TEAL}
                      strokeWidth={2.5}
                      fill={`url(#${gradientId})`}
                      connectNulls={epdsMode}
                      dot={
                        epdsMode
                          ? {
                              r: 4.5,
                              fill: TEAL,
                              stroke: palette.dotRing,
                              strokeWidth: 2,
                            }
                          : showDots(moodN)
                      }
                      activeDot={{
                        r: 6,
                        fill: TEAL,
                        stroke: palette.dotRing,
                        strokeWidth: 2,
                      }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
            {item10 && (
              <div
                role="note"
                className="mt-4 flex gap-3 rounded-2xl bg-white p-4 text-lg shadow-paper ring-2 ring-alert/40"
              >
                <AlertIcon className="mt-1 size-6 shrink-0 text-alert" />
                <p>
                  A recent mood check mentioned thoughts of self-harm. If they come back, call or text{" "}
                  <a href="tel:988" className={`rounded font-semibold underline underline-offset-4 ${focusRing}`}>
                    988
                  </a>{" "}
                  any time.
                </p>
              </div>
            )}
          </section>

          {rise && (
            <section
              aria-labelledby="bp-callout-title"
              className="flex gap-4 rounded-2xl bg-white p-5 shadow-paper ring-2 ring-navy/25 sm:p-6"
            >
              <AlertIcon className="mt-1 size-7 shrink-0 text-navy" />
              <div>
                <h2 id="bp-callout-title" className="font-display text-2xl font-semibold">
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

          <section aria-labelledby="bp-title">
            <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
              <h2 id="bp-title" className="font-display text-2xl font-semibold">
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
            <div className="relative mt-4 h-60 rounded-2xl bg-white p-3 shadow-paper ring-1 ring-navy/10">
              <ChartEmpty show={bpN === 0} />
              <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 320, height: 224 }}>
                <LineChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
                  <CartesianGrid vertical={false} stroke={GRID} />
                  <XAxis {...xAxisProps} tick={AXIS} />
                  <YAxis domain={[60, 160]} ticks={[60, 90, 120, 150]} tick={AXIS} tickLine={false} axisLine={false} />
                  <ReferenceLine
                    y={140}
                    stroke="#1b2a22"
                    strokeDasharray="5 4"
                    label={{
                      value: "140",
                      position: "insideTopLeft",
                      fill: "#1b2a22",
                      fontSize: 13,
                      dy: -14,
                    }}
                  />
                  {/* BP is measured every few days, not daily: join the readings and mark each one. */}
                  <Tooltip
                    content={
                      <ChartTip
                        units={{
                          "Top number": " mmHg",
                          "Bottom number": " mmHg",
                        }}
                      />
                    }
                    {...tipMotion}
                  />
                  <Line
                    {...drawIn}
                    type="monotone"
                    dataKey="bp_sys"
                    name="Top number"
                    stroke={TEAL}
                    strokeWidth={2.5}
                    connectNulls
                    dot={{ r: 3.5 }}
                    activeDot={{
                      r: 6,
                      stroke: palette.dotRing,
                      strokeWidth: 2,
                    }}
                  />
                  <Line
                    {...drawIn}
                    type="monotone"
                    dataKey="bp_dia"
                    name="Bottom number"
                    stroke={AMBER}
                    strokeWidth={2.5}
                    connectNulls
                    dot={{ r: 3.5 }}
                    activeDot={{
                      r: 6,
                      stroke: palette.dotRing,
                      strokeWidth: 2,
                    }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="mt-1 text-base text-navy/80">The dashed line marks 140 on the top number.</p>
          </section>

          <section aria-labelledby="headache-title">
            <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
              <h2 id="headache-title" className="font-display text-2xl font-semibold">
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

          <div className="grid gap-12 sm:grid-cols-2 sm:gap-8">
            <section aria-labelledby="sleep-title">
              <h2 id="sleep-title" className="font-display text-2xl font-semibold">
                Sleep
              </h2>
              <p className="text-base text-navy/80">Hours a night</p>
              <div className="relative mt-3 h-48 rounded-2xl bg-white p-3 shadow-paper ring-1 ring-navy/10">
                <ChartEmpty show={sleepN === 0} />
                <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 320, height: 176 }}>
                  <BarChart data={points} margin={{ top: 8, right: 4, bottom: 0, left: -20 }}>
                    <CartesianGrid vertical={false} stroke={GRID} />
                    <XAxis {...xAxisProps} tick={AXIS} />
                    <YAxis domain={[0, 10]} ticks={[0, 5, 10]} tick={AXIS} tickLine={false} axisLine={false} />
                    <Tooltip
                      cursor={{ fill: "rgba(11,37,69,0.06)" }}
                      content={<ChartTip units={{ Sleep: " hours" }} />}
                      {...tipMotion}
                    />
                    <Bar {...drawIn} dataKey="sleep_hrs" name="Sleep" fill={TEAL} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>

            <section aria-labelledby="pain-title">
              <h2 id="pain-title" className="font-display text-2xl font-semibold">
                Pain
              </h2>
              <p className="text-base text-navy/80">
                0 is none, 10 is the worst
                {hasIncision ? ". Amber is your incision." : ""}
              </p>
              <div className="relative mt-3 h-48 rounded-2xl bg-white p-3 shadow-paper ring-1 ring-navy/10">
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
                      activeDot={{
                        r: 6,
                        stroke: palette.dotRing,
                        strokeWidth: 2,
                      }}
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
                        activeDot={{
                          r: 6,
                          stroke: palette.dotRing,
                          strokeWidth: 2,
                        }}
                      />
                    )}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </section>
          </div>

          {hrN > 0 && (
            <section aria-labelledby="hr-title">
              <h2 id="hr-title" className="font-display text-2xl font-semibold">
                Resting heart rate
              </h2>
              <p className="text-base text-navy/80">Beats a minute, from Apple Health</p>
              <div className="relative mt-3 h-48 rounded-2xl bg-white p-3 shadow-paper ring-1 ring-navy/10">
                <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 320, height: 176 }}>
                  <LineChart data={points} margin={{ top: 8, right: 4, bottom: 0, left: -20 }}>
                    <CartesianGrid vertical={false} stroke={GRID} />
                    <XAxis {...xAxisProps} tick={AXIS} />
                    <YAxis domain={[40, 110]} ticks={[50, 70, 90, 110]} tick={AXIS} tickLine={false} axisLine={false} />
                    <Tooltip content={<ChartTip units={{ "Resting heart rate": " bpm" }} />} {...tipMotion} />
                    <Line
                      {...drawIn}
                      type="monotone"
                      dataKey="resting_hr"
                      name="Resting heart rate"
                      stroke={TEAL}
                      strokeWidth={2.5}
                      connectNulls
                      dot={showDots(hrN)}
                      activeDot={{
                        r: 6,
                        stroke: palette.dotRing,
                        strokeWidth: 2,
                      }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </section>
          )}
        </>
      )}

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
                    <td className="py-2 pr-4 tabular-nums">{p.epds_score != null ? `${p.epds_score} / 30` : "–"}</td>
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
