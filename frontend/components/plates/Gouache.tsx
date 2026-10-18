// Gouache plates for the Night-Feed Picture Book world. Original, code-native artwork: flat painted
// shapes in the world's palette, given pigment edges (a turbulence displacement on the shapes) and
// paper grain (a fine noise layer multiplied over the plate). Editorial, not cartoon: no outlines, no
// faces, no gradients standing in for paint. Every plate has a text alternative.
//
// Motion: elements with class "moon" and "tide" get the one-time moonrise in globals.css, which is
// switched off for reduced motion. Plates dim in night mode (.plate in globals.css).
import { useId } from "react";

const C = {
  wall: "#23463a",
  wallDeep: "#1c3a2f",
  night: "#132119",
  nightSoft: "#1c3427",
  sea: "#2b5244",
  seaLight: "#3f6b58",
  ivory: "#f1e7d2",
  frame: "#e9dec4",
  gold: "#d9b75c",
  goldDeep: "#c99a2e",
  terracotta: "#b45f3e",
  terracottaDeep: "#93482e",
  skin: "#a9724e",
  skinBaby: "#c48c66",
  hair: "#2a1d17",
  robe: "#efe4cc",
  robeShade: "#ddcfb0",
  chair: "#11211a",
  leaf: "#4e7a62",
};

/** Shared filters: pigment edge + paper grain. Ids are scoped per plate so several can coexist. */
function Paint({ id }: { id: string }) {
  return (
    <defs>
      <filter id={`${id}-edge`} x="-4%" y="-4%" width="108%" height="108%">
        <feTurbulence type="fractalNoise" baseFrequency="0.022" numOctaves="2" seed="11" result="n" />
        <feDisplacementMap in="SourceGraphic" in2="n" scale="3" xChannelSelector="R" yChannelSelector="G" />
      </filter>
      <filter id={`${id}-grain`} x="0" y="0" width="100%" height="100%">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="3" stitchTiles="stitch" />
        <feColorMatrix values="0 0 0 0 0.1  0 0 0 0 0.09  0 0 0 0 0.07  0 0 0 0.55 0" />
      </filter>
      <filter id={`${id}-mottle`} x="0" y="0" width="100%" height="100%">
        <feTurbulence type="fractalNoise" baseFrequency="0.012" numOctaves="3" seed="5" />
        <feColorMatrix values="0 0 0 0 1  0 0 0 0 0.97  0 0 0 0 0.9  0 0 0 0.16 0" />
      </filter>
      <radialGradient id={`${id}-glow`}>
        <stop offset="0" stopColor={C.gold} stopOpacity="0.32" />
        <stop offset="1" stopColor={C.gold} stopOpacity="0" />
      </radialGradient>
    </defs>
  );
}

/** Paper grain and uneven pigment over the whole plate. */
function Finish({ id, w, h }: { id: string; w: number; h: number }) {
  return (
    <g aria-hidden="true" pointerEvents="none">
      <rect width={w} height={h} filter={`url(#${id}-mottle)`} style={{ mixBlendMode: "soft-light" }} />
      <rect width={w} height={h} filter={`url(#${id}-grain)`} opacity="0.35" style={{ mixBlendMode: "multiply" }} />
    </g>
  );
}

/** The hero plate: a parent feeding a baby in an armchair by a night window, the moon over the tide. */
export function NightFeedPlate({ className = "" }: { className?: string }) {
  const id = useId().replace(/:/g, "");
  const arch = "M150 452 V212 A150 150 0 0 1 450 212 V452 Z";
  return (
    <svg
      viewBox="0 0 600 760"
      role="img"
      aria-labelledby={`${id}-t`}
      className={`plate ${className}`}
      preserveAspectRatio="xMidYMid slice"
    >
      <title id={`${id}-t`}>
        A painting of a parent feeding a baby in an armchair at night, by a window where the moon rises over the sea.
      </title>
      <Paint id={id} />
      <clipPath id={`${id}-win`}>
        <path d={arch} />
      </clipPath>

      {/* wall */}
      <rect width="600" height="760" fill={C.wall} />
      <g filter={`url(#${id}-edge)`} opacity="0.5">
        <rect x="0" y="0" width="70" height="640" fill={C.wallDeep} />
        <rect x="530" y="0" width="70" height="640" fill={C.wallDeep} />
      </g>

      {/* window: sky, moon, sea */}
      <g clipPath={`url(#${id}-win)`}>
        <rect x="140" y="50" width="320" height="410" fill={C.night} />
        <rect x="140" y="300" width="320" height="70" fill={C.nightSoft} />
        <g fill={C.ivory}>
          <circle cx="196" cy="168" r="1.6" opacity="0.8" />
          <circle cx="236" cy="120" r="1.2" opacity="0.6" />
          <circle cx="410" cy="150" r="1.4" opacity="0.7" />
          <circle cx="262" cy="232" r="1" opacity="0.5" />
          <circle cx="420" cy="262" r="1.1" opacity="0.6" />
        </g>
        <g className="moon">
          <circle cx="352" cy="214" r="74" fill={`url(#${id}-glow)`} />
          <circle cx="352" cy="214" r="40" fill={C.gold} filter={`url(#${id}-edge)`} />
        </g>
        <g className="tide" filter={`url(#${id}-edge)`}>
          <path d="M140 372 C190 362 230 378 280 370 S380 360 460 372 V460 H140 Z" fill={C.sea} />
          <path d="M140 392 C200 384 250 398 300 390 S400 382 460 392 V460 H140 Z" fill={C.seaLight} opacity="0.55" />
        </g>
        {/* the moon's path on the water: short strokes that thin out toward the shore */}
        <g fill={C.gold} opacity="0.55">
          <rect x="333" y="384" width="38" height="2.5" rx="1.25" />
          <rect x="339" y="397" width="27" height="2.5" rx="1.25" />
          <rect x="344" y="410" width="17" height="2" rx="1" />
          <rect x="348" y="422" width="9" height="2" rx="1" />
        </g>
      </g>
      {/* frame and mullions */}
      <g filter={`url(#${id}-edge)`} fill="none" stroke={C.frame} strokeLinecap="round">
        <path d={arch} strokeWidth="16" />
        <path d="M300 64 V452" strokeWidth="7" />
        <path d="M150 300 H450" strokeWidth="7" />
      </g>
      <rect x="128" y="446" width="344" height="20" rx="4" fill={C.frame} filter={`url(#${id}-edge)`} />

      {/* plant on the sill */}
      <g filter={`url(#${id}-edge)`}>
        <ellipse cx="186" cy="404" rx="9" ry="22" fill={C.leaf} transform="rotate(-24 186 404)" />
        <ellipse cx="206" cy="398" rx="9" ry="26" fill={C.leaf} transform="rotate(14 206 398)" />
        <ellipse cx="196" cy="392" rx="8" ry="24" fill="#5e8a71" />
        <path d="M176 418 H218 L212 448 H182 Z" fill={C.terracotta} />
      </g>

      {/* lamp on a side table, its glow */}
      <circle cx="96" cy="520" r="150" fill={`url(#${id}-glow)`} />
      <g filter={`url(#${id}-edge)`}>
        <rect x="46" y="572" width="104" height="86" rx="6" fill={C.chair} />
        <rect x="92" y="526" width="8" height="48" fill={C.frame} />
        <path d="M66 478 H126 L140 530 H52 Z" fill={C.terracotta} />
        <path d="M66 478 H126 L128 486 H64 Z" fill={C.terracottaDeep} />
      </g>

      {/* floor and rug */}
      <rect x="0" y="652" width="600" height="108" fill={C.wallDeep} />
      <ellipse cx="350" cy="712" rx="236" ry="30" fill={C.frame} opacity="0.92" filter={`url(#${id}-edge)`} />

      {/* armchair */}
      <g filter={`url(#${id}-edge)`}>
        <rect x="372" y="430" width="132" height="262" rx="44" fill={C.chair} />
        <rect x="262" y="586" width="236" height="88" rx="30" fill={C.chair} />
        <rect x="246" y="560" width="72" height="104" rx="30" fill={C.chair} />
        <rect x="292" y="668" width="14" height="38" rx="4" fill={C.chair} />
        <rect x="470" y="668" width="14" height="38" rx="4" fill={C.chair} />
      </g>

      {/* parent */}
      <g filter={`url(#${id}-edge)`}>
        {/* legs */}
        <path d="M384 604 C340 600 300 606 268 612 L264 650 C300 646 344 648 392 646 Z" fill={C.robeShade} />
        <path d="M268 612 C256 640 254 680 258 712 L284 712 C284 684 288 650 296 626 Z" fill={C.robeShade} />
        <ellipse cx="270" cy="716" rx="20" ry="8" fill={C.hair} />
        {/* torso */}
        <path d="M352 470 C392 476 410 520 404 566 C400 600 392 616 380 624 L318 624 C318 586 316 540 324 504 C328 486 338 472 352 470 Z" fill={C.robe} />
        {/* head, tilted down to the baby */}
        <rect x="330" y="446" width="20" height="28" rx="8" fill={C.skin} />
        <circle cx="332" cy="434" r="27" fill={C.skin} />
        <path d="M330 404 C356 400 372 418 370 440 C368 458 358 466 352 468 C356 452 352 436 340 428 C330 420 318 418 306 422 C310 410 318 405 330 404 Z" fill={C.hair} />
        <circle cx="366" cy="420" r="15" fill={C.hair} />
        {/* baby, swaddled in an ivory blanket with two terracotta stripes, a fold over the top */}
        <g transform="rotate(-20 300 548)">
          <path d="M252 540 C252 516 286 508 322 512 C352 516 360 534 356 552 C352 572 322 582 292 580 C266 578 252 562 252 540 Z" fill={C.ivory} />
          <path d="M262 528 C292 520 328 522 352 534" stroke={C.terracotta} strokeWidth="4" fill="none" />
          <path d="M256 548 C288 540 330 544 356 556" stroke={C.terracotta} strokeWidth="2.5" fill="none" opacity="0.85" />
          <path d="M252 540 C262 524 284 518 302 520 C292 532 274 540 252 540 Z" fill={C.robeShade} />
        </g>
        <circle cx="258" cy="522" r="15" fill={C.skinBaby} />
        <path d="M246 514 C252 506 266 506 272 514 C264 510 254 510 246 514 Z" fill={C.ivory} />
        {/* arm cradling the baby */}
        <path d="M376 500 C372 548 340 576 280 572" stroke={C.robe} strokeWidth="26" strokeLinecap="round" fill="none" />
        <circle cx="270" cy="568" r="11" fill={C.skin} />
      </g>

      <Finish id={id} w={600} h={760} />
    </svg>
  );
}

type Hour = "night" | "late" | "dawn";
const HOURS: Record<Hour, { sky: string; skyLow: string; sea: string; sun: string; y: number; label: string }> = {
  night: { sky: C.night, skyLow: C.nightSoft, sea: C.sea, sun: C.gold, y: 96, label: "The window at night, the moon high over the sea." },
  late: { sky: "#16271e", skyLow: "#22392c", sea: C.sea, sun: C.gold, y: 150, label: "The window later in the night, the moon lower." },
  dawn: { sky: "#e8d6a8", skyLow: "#efdfb6", sea: "#7d9a86", sun: "#e9a65a", y: 196, label: "The window at dawn, a low sun over a pale sea." },
};

/** One window at three hours of the same night: the strip under "One night with Tidewell". */
export function WindowPlate({ hour, className = "" }: { hour: Hour; className?: string }) {
  const id = useId().replace(/:/g, "");
  const h = HOURS[hour];
  const arch = "M40 330 V120 A110 110 0 0 1 260 120 V330 Z";
  return (
    <svg viewBox="0 0 300 360" role="img" aria-label={h.label} className={`plate ${className}`}>
      <Paint id={id} />
      <clipPath id={`${id}-win`}>
        <path d={arch} />
      </clipPath>
      <rect width="300" height="360" fill={C.wall} />
      <g clipPath={`url(#${id}-win)`}>
        <rect x="30" y="0" width="240" height="340" fill={h.sky} />
        <rect x="30" y="210" width="240" height="50" fill={h.skyLow} />
        <g className="moon">
          <circle cx="182" cy={h.y} r="46" fill={`url(#${id}-glow)`} />
          <circle cx="182" cy={h.y} r="24" fill={h.sun} filter={`url(#${id}-edge)`} />
        </g>
        <g className="tide" filter={`url(#${id}-edge)`}>
          <path d="M30 262 C80 254 120 268 160 260 S230 252 270 262 V340 H30 Z" fill={h.sea} />
        </g>
      </g>
      <g filter={`url(#${id}-edge)`} fill="none" stroke={C.frame} strokeLinecap="round">
        <path d={arch} strokeWidth="12" />
        <path d="M150 12 V330" strokeWidth="5" />
      </g>
      <rect x="26" y="326" width="248" height="14" rx="3" fill={C.frame} filter={`url(#${id}-edge)`} />
      <Finish id={id} w={300} h={360} />
    </svg>
  );
}

/** The mark: a moon over a tide line. Used in the nav, the voice button's idea, and the favicon. */
export function Mark({ className = "size-7" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <circle cx="16" cy="12" r="7" fill="#c99a2e" />
      <path d="M3 21 C7 18.5 11 18.5 16 21 S25 23.5 29 21" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
      <path d="M6 26 C9.5 24 12.5 24 16 26 S22.5 28 26 26" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" opacity="0.55" />
    </svg>
  );
}
