// Small inline icons. All are decorative: the text next to them carries the meaning.

type IconProps = { className?: string };

const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
  focusable: false,
};

export function MicIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3" />
    </svg>
  );
}

export function StopIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <rect x="7" y="7" width="10" height="10" rx="2" fill="currentColor" />
    </svg>
  );
}

export function WaveIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M3 9c2.2 0 2.2-2 4.5-2S9.800 9 12 9s2.200-2 4.500-2S18.800 9 21 9M3 15c2.2 0 2.2-2 4.500-2S9.800 15 12 15s2.200-2 4.500-2S18.800 15 21 15" />
    </svg>
  );
}

export function ChartIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M4 19V5M4 19h16M8 15l3.500-4 3 2.500L20 7" />
    </svg>
  );
}

export function GearIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3v2.500M12 18.500V21M3 12h2.500M18.500 12H21M5.600 5.600l1.800 1.800M16.600 16.600l1.800 1.800M5.600 18.400l1.800-1.800M16.600 7.400l1.800-1.800" />
    </svg>
  );
}

export function AlertIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M12 4 3 19.500h18L12 4ZM12 10v4.500M12 17.200v.1" />
    </svg>
  );
}

export function CalendarIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M4 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7ZM4 10h16M8 3v4M16 3v4" />
    </svg>
  );
}

export function VideoIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M3 8a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8ZM15 10.500l6-3.500v10l-6-3.500" />
    </svg>
  );
}

export function PinIcon({ className }: IconProps) {
  return (
    <svg {...base} className={className}>
      <path d="M12 21s-6.500-5.600-6.500-11a6.500 6.500 0 0 1 13 0c0 5.400-6.500 11-6.500 11ZM12 12.200a2.200 2.200 0 1 0 0-4.400 2.200 2.200 0 0 0 0 4.400Z" />
    </svg>
  );
}
