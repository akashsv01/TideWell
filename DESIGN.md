---
name: Tidewell
description: A voice-first care companion for the year after birth, set as a night-feed picture book.
colors:
  navy: "#1b2a22"
  tide: "#3c6a55"
  tide-deep: "#23463a"
  tide-light: "#d9b75c"
  foam: "#f7f1e4"
  sand: "#ece2ca"
  white: "#fffdf8"
  alert: "#a3261c"
  gold: "#c99a2e"
  gold-hover: "#d8ab43"
  gold-soft: "#efdfae"
  terracotta: "#b45f3e"
  forest: "#1f3d32"
  night: "#142019"
  chart-teal: "#2d5a48"
  chart-amber: "#b3801f"
  night-page: "#101a15"
  night-surface: "#18261f"
  night-panel: "#0b130f"
  night-ink: "#efe7d5"
typography:
  display:
    fontFamily: "Alegreya Variable, Alegreya, ui-serif, Georgia, serif"
    fontSize: "clamp(3rem, 6vw, 4.5rem)"
    fontWeight: 600
    lineHeight: 1.02
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Alegreya Variable, Alegreya, ui-serif, Georgia, serif"
    fontSize: "2.25rem"
    fontWeight: 600
    lineHeight: 1.25
  title:
    fontFamily: "Alegreya Variable, Alegreya, ui-serif, Georgia, serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1.33
  body:
    fontFamily: "Atkinson Hyperlegible Next Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 400
    lineHeight: 1.625
  label:
    fontFamily: "Atkinson Hyperlegible Next Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.5
rounded:
  plate: "6px"
  spread: "10px"
  control: "12px"
  surface: "16px"
  full: "9999px"
spacing:
  gutter-phone: "20px"
  gutter: "32px"
  row-y: "16px"
  surface-pad: "24px"
  section-y: "96px"
components:
  button-primary:
    backgroundColor: "{colors.tide-deep}"
    textColor: "{colors.white}"
    rounded: "{rounded.full}"
    padding: "0 32px"
    height: "56px"
  button-primary-hover:
    backgroundColor: "{colors.navy}"
  button-moon:
    backgroundColor: "{colors.gold}"
    textColor: "{colors.navy}"
    rounded: "{rounded.full}"
    padding: "0 32px"
    height: "56px"
  button-moon-hover:
    backgroundColor: "{colors.gold-hover}"
  button-outline:
    textColor: "{colors.navy}"
    rounded: "{rounded.full}"
    padding: "0 32px"
    height: "56px"
  button-outline-hover:
    backgroundColor: "{colors.navy}"
    textColor: "{colors.white}"
  input-field:
    backgroundColor: "{colors.white}"
    textColor: "{colors.navy}"
    rounded: "{rounded.surface}"
    padding: "0 16px"
    height: "56px"
  paper-surface:
    backgroundColor: "{colors.white}"
    textColor: "{colors.navy}"
    rounded: "{rounded.surface}"
    padding: "24px"
  nav-tab-active:
    textColor: "{colors.tide-deep}"
    rounded: "{rounded.control}"
    height: "64px"
  urgent-emergency-field:
    backgroundColor: "{colors.alert}"
  urgent-today-field:
    backgroundColor: "{colors.tide-deep}"
---

# Design System: Tidewell

## Overview

**Creative North Star: "The Night-Feed Picture Book"**

Tidewell is the picture book a parent is awake inside at 3 a.m.: a quiet room, a window, and the moon that pulls the tide. Two fields carry the world. Warm ivory paper is the page, deep forest green is the night outside. Muted gold is the moon. Editorial gouache plates (pigment edges, paper grain, a terracotta lamp and blanket) add the warmth. They stay sophisticated, never cartoonish, and they never carry information.

The illustration and the information are kept apart. Anything a tired person has to read and act on (check-ins, the tide chart, care advice, clinician summaries, safety messages) sits on plain paper surfaces with hairline dividers, set in Atkinson Hyperlegible Next at a generous size. Alegreya, upright and large, sets the headings. The landing page plays the world at full volume, an open spread with the plate on one page and the words on the other. The signed-in app keeps the same materials at a lower volume: one content column, paper cards, the moon as the voice button.

Token names are historical and kept on purpose so every component inherits the world: `navy` is ink, `tide` is mid forest, `tide-deep` is forest, `tide-light` is gold on dark fields, `foam` is the ivory page, `sand` is deeper ivory, `white` is paper. Read tokens by role, not by name.

**Key Characteristics:**
- Two fields (ivory paper, forest night); gold is the moon only.
- Gouache plates for warmth; health facts never sit on illustration.
- Large, legible type; the type scale rises with urgency.
- Status said in sentences, never in badges.
- One mark everywhere: a gold moon over two tide lines.
- Night mode is the same room with the lamp off, not an inversion.

## Colors

A warm, low-saturation palette of ivory and forest, with one muted gold and terracotta kept inside the pictures.

### Primary
- **Deep Forest** (`tide-deep`): the default action fill (white text), the dark landing sections, the "call your care team today" safety field, the active nav underline, and the mark's tide lines in the app header.
- **Forest Ink** (`navy`): body text, outline-button strokes and hover fill, input strokes, and the focus ring. Opacity steps (`/85`, `/80`, `/70`) set secondary text; `/10` makes hairlines and the paper ring.
- **Mid Forest** (`tide`): the lighter forest used in the waves and as a ring colour on dark buttons.

### Secondary
- **Moon Gold** (`gold`): the moon in the mark and plates, the voice orb, and the one primary action on the landing page ("Start today"), with ink text. Hover lifts to `gold-hover`.
- **Gold on Dark** (`tide-light`): figures and emphasis set on forest fields, such as the sourced statistics on the landing page.
- **Soft Gold** (`gold-soft`): text selection only.

### Tertiary
- **Lamp Terracotta** (`terracotta`): only inside illustrations and the annotated sample tide (the headache markers). Never status, never UI chrome.

### Neutral
- **Ivory Page** (`foam`): the page background, and the bottom tab bar at 95% opacity with backdrop blur.
- **Deeper Ivory** (`sand`): quiet fills, row hover (`sand/50`), the sample-tide section band (`sand/40`).
- **Paper** (`white`): every surface that holds health information.
- **Alert Crimson** (`alert`): the emergency field and its call button. Nothing else in the UI is red.
- **Chart Forest / Chart Amber** (`chart-teal`, `chart-amber`): the two chart series. They separate by lightness, so the pair still reads under red-green colour blindness.

### Night mode
Set by `html[data-night]`. The page goes to `night-page` with a faint gold moonlight gradient at the top, paper surfaces to `night-surface`, ink (`navy`) panels to `night-panel` with a hairline gold inset, and text to `night-ink`. Forest buttons stay forest (`#2c5444`) under white text. Gold stays gold, and ink text on gold stays dark (5.9:1). Plates dim (`brightness 0.86, saturate 0.9`) so they never out-shine the information. Charts switch to a night pair in the dashboard (`#8cc2a6` / `#e2b453`). Body text holds at 12:1 or better on the page.

### Named Rules
**The One Moon Rule.** Gold is the moon: the mark, the plates, the voice orb, and at most one primary action per page (the landing "Start today"). Gold never marks status, a category, or a count. Every other primary action is forest.

**The Lamp Stays in the Picture Rule.** Terracotta lives in illustrations. If it appears on a control, a badge, or a status line, it is wrong.

**The Two Reds Rule.** Crimson means call 911 now. "Call today" is forest, never amber or red.

## Typography

**Display Font:** Alegreya Variable (with Alegreya, ui-serif, Georgia)
**Body Font:** Atkinson Hyperlegible Next Variable (with ui-sans-serif, system-ui)

**Character:** A bookish, calligraphic serif set large and upright for headings, paired with a sans built for low-vision legibility for everything a tired person has to read. Atkinson's slashed zero is kept on purpose: no font-feature override turns it off, so 0 and O never get confused in blood pressure readings and times.

### Hierarchy
- **Display** (600, 48px rising to 72px at lg, line-height 1.02, -0.01em): the landing hero question only.
- **Headline** (600, 36px, rising to 48px on landing sections, leading-tight): screen titles ("Your patients", "Get care now"), landing section heads.
- **Title** (600, 24px): card and section titles inside app screens, the wordmark. Risk sentences in Care step up to 30px when the risk is high.
- **Body** (400, 18px, line-height 1.625): the default reading size across the app. Landing lead paragraphs use 20px. Measures are capped at 34 to 52ch.
- **Label** (600, 16px): nav tabs, row subtitles, chart captions. 14px is the floor, used for footnotes and the phone tab-bar labels.

### Named Rules
**The Urgency Scale Rule.** Type size follows how much it matters. A routine status is a 20px sentence; elevated risk in Care, a red circle status, and the safety cards move up to display-face 30 to 36px headlines. Never shrink an urgent message to fit.

**The Legible Floor Rule.** Body copy is 18px. Nothing a parent must act on goes below 16px.

## Layout

The landing page uses a 1152px container (`max-w-6xl`) with 20px gutters on phones and 32px from sm up, 96px section rhythm, and asymmetric two-column grids at lg. Its first viewport is an open spread: the plate fills one page (288px tall on phones, 384px at sm, at least 640px at lg) and the text page sits beside it on paper, with a soft gutter shadow. Below lg the plate becomes a band above the text.

App screens share one content width, a 768px column (`max-w-3xl`), and never widen it per screen. The header is 64px tall (80px at md) and carries the mark and wordmark, the night toggle, and the account menu. From md up a tab row sits under the header. On phones a fixed bottom tab bar replaces it, and the main area pads 128px at the bottom to clear it. Sub-screens open with a BackLink at the top left that names where it goes.

Information is set as lists. Rows inside a paper surface pad 16px vertically and 20px horizontally, separated by hairlines rather than gaps.

## Elevation & Depth

Depth is soft, warm, and low. Paper surfaces rest a little above the ivory page under a forest-tinted shadow and a 1px ink hairline ring. Lift is reserved for the landing spread, the voice orb, and the gold action. Shadows always blur; there is no zero-blur offset block anywhere in the world.

### Shadow Vocabulary
- **Paper** (`box-shadow: 0 1px 2px rgb(27 42 34 / 0.06), 0 8px 24px -12px rgb(27 42 34 / 0.18)`): every health-information surface, together with `ring-1` at `navy/10`.
- **Lift** (`box-shadow: 0 2px 4px rgb(27 42 34 / 0.08), 0 18px 40px -18px rgb(27 42 34 / 0.32)`): the landing spread, the voice orb, menus.
- **Moon** (`box-shadow: 0 2px 4px rgb(27 42 34 / 0.12), 0 12px 28px -14px rgb(27 42 34 / 0.45)`): the gold primary action only.

### Named Rules
**The Paper Rule.** Health facts sit on paper: background `white`, Paper shadow, an ink/10 ring, 16px corners, and hairline dividers (`navy/10`) between rows. Never put them on an illustration or a tinted card.

## Shapes

Shapes are soft and bookish. Actions are fully round pills. Paper surfaces and form fields use 16px corners, the voice orb is a circle, and the bottom tab-bar items and safety-card buttons use 12px. The plates keep the corners of printed pages: 10px on the landing spread and 6px on the small window plates. Borders are either 2px ink strokes on controls or hairline ink/10 rules. There are no accent stripes.

## Components

### Buttons
Calm, large, and unmistakable.
- **Shape:** full pill, at least 56px tall, 32px side padding, 18px semibold label.
- **Primary (forest):** `tide-deep` fill with white text; hover goes to ink. Use this for every primary action except the one gold moon.
- **Moon (gold):** `gold` fill, ink text, Moon shadow, hover `gold-hover`. Use it once, for the landing primary only.
- **Outline:** a 2px ink stroke and ink text; hover fills with ink and turns the text white.
- **Hover / Focus / Press:** colours transition over 150ms on the strong ease-out curve. Pressing scales to 0.97 when motion is allowed. The focus ring is 4px ink with a 2px ivory offset (white on dark fields). Disabled buttons drop to 60% opacity with a not-allowed cursor.
- **Text links:** underlined, offset 0.2em, thickness 0.08em, for the quieter alternatives ("I have an account", "Type instead").

### Cards / Containers
- **Corner Style:** 16px.
- **Background:** paper (`white`); `night-surface` at night.
- **Shadow Strategy:** Paper (see Elevation), plus a 1px ink/10 ring.
- **Border:** none beyond the ring; rows divide with ink/10 hairlines.
- **Internal Padding:** 24px for a single block, 16px by 20px per list row. Rows that link somewhere end in a drawn chevron that nudges 2px on hover, and the row tints `sand/50`.

### Inputs / Fields
- **Style:** a 2px ink stroke, paper fill, 18px text, at least 56px tall. Stacked form fields use 16px corners. Single-line inline entries (Ask, ZIP code) use full pills.
- **Focus:** the shared 4px ink focus ring with an ivory offset. The caret is forest.
- **Error:** said in a sentence beside the field, never with colour alone.

### Navigation
- **Header:** the mark (a gold moon over two forest tide lines) and the Alegreya wordmark at 24px semibold.
- **Top tabs (md+):** 16px semibold labels at ink/70. The active tab gets a 2px forest underline and full ink; hover shows an ink/25 underline.
- **Bottom bar (phones only):** fixed, ivory at 95% with backdrop blur and a hairline top border, 64px tall items with a drawn 24px icon over a 14px label. The active item gets a forest/10 fill and forest text. It respects the safe-area inset.
- **BackLink:** a drawn chevron and a named destination, 18px semibold, at the top left of every sub-screen.

### Icons
Drawn inline SVG only (the shared set in `components/icons.tsx` plus inline chevrons). Strokes are 2px and round-capped, sized 24px in navigation and rows, coloured with currentColor.

### Voice Orb (signature)
The voice button is the moon: a 192px gold circle with a 4px paper ring and the Lift shadow, holding layered forest water. The water moves only while recording or busy (faster while Tidewell is thinking) and is still otherwise.

### Safety Cards (signature)
A full-screen field fades in over 150ms: crimson for emergency, forest for "call your care team today". On it sits a 448px-wide paper card with 16px corners that settles from 0.97 scale over 200ms (a plain fade under reduced motion). The 36px Alegreya headline is crimson for emergency and ink for the today tier. Body copy is 18px. The call actions are 56px buttons with 12px corners, and a "Go back" link sits under them. The wording is fixed, must match `backend/app/ai/red_flags.py`, and never contains generated text. Focus moves to the card itself, not to a call button.

### Motion
- **Moonrise:** on the landing plate the moon rises 14px over 700ms on ease-out, and the tide line breathes once (2.4s, starting after 300ms). After that the plate is still.
- **Page enter:** 220ms, 8px rise, no fill-mode, so content stays visible even if the animation never runs.
- **UI transitions:** 150 to 300ms on `cubic-bezier(0.23, 1, 0.32, 1)`.
- **Theme switch:** a 300ms colour crossfade only.
- **Reduced motion:** under `prefers-reduced-motion: reduce` every animation and transition collapses to nothing.

## Do's and Don'ts

### Do:
- **Do** read tokens by role: `navy` is ink, `tide-deep` is forest, `foam` is the ivory page, `white` is paper.
- **Do** put every health fact on a paper surface (paper fill, Paper shadow, ink/10 ring, 16px corners) with hairline dividers between rows.
- **Do** say status in a full sentence, and raise the type size as urgency rises.
- **Do** use forest for primary actions in the app, and keep gold for the moon and the single landing primary.
- **Do** keep one 768px content column for every app screen, and open each sub-screen with a BackLink.
- **Do** draw icons as inline SVG with 2px round strokes in currentColor.
- **Do** let illustrations dim at night and stay still under reduced motion.
- **Do** keep Atkinson's slashed zero.

### Don't:
- **Don't** use badges, pills, or coloured dots to carry status.
- **Don't** use gold or terracotta for status, categories, or warnings.
- **Don't** put an eyebrow or kicker label above headings.
- **Don't** use border-left accent stripes on cards or callouts.
- **Don't** use unicode symbols or emoji as icons.
- **Don't** set information on top of illustration.
- **Don't** use zero-blur offset shadows.
- **Don't** reword the safety cards or put generated text in them.
- **Don't** invert colours for night mode; dark surfaces have their own layers.
