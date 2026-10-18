import { shortDay } from "@/lib/insights";

// Hover and keyboard tooltip shared by all charts. Text uses ink color. The swatch carries identity.

type Row = { name?: string | number; value?: unknown; color?: string; unit?: string };

type Props = {
  active?: boolean;
  payload?: ReadonlyArray<Row>;
  label?: string | number;
  units?: Record<string, string>;
};

export default function ChartTip({ active, payload, label, units }: Props) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-navy/15 bg-white px-3 py-2 text-sm text-navy shadow-lift">
      <p className="font-semibold">{shortDay(String(label))}</p>
      <ul className="mt-1 space-y-0.5">
        {payload.map((row) => (
          <li key={String(row.name)} className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className="size-2.5 rounded-full"
              style={{ background: row.color }}
            />
            {row.name}: {String(row.value)}
            {units?.[String(row.name)] ?? ""}
          </li>
        ))}
      </ul>
    </div>
  );
}
