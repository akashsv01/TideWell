# Tidewell redesign: Night-Feed Picture Book (app screens pass)

Branch `redesign-wip`. Everything in this pass is **uncommitted**, sitting on top of the earlier WIP commit `a0752b3` (landing, tokens, plates, check-in). That earlier commit is already on `origin/redesign-wip`. Nothing has been merged to `main`.

Screenshots: `before/` (original UI) and `after/` (this build). They are Playwright captures at exact viewports: desktop 1440x900, tablet 768x1024, mobile 390x844.

---

## Round 2 (your six notes)

1. **The hero image is no longer cropped.** The night-feed plate is now always shown whole. The space around it is filled with the plate's own wall and floor colours, so it reads as the same room at every width. Checked at 320, 360, 390, 600, 768, 1024 and 1440: no horizontal overflow at any of them (`after/landing-<width>.png`).
2. **"Start tonight" is now "Start today" everywhere:** the header button, the hero button, the closing heading, and DESIGN.md, the sidecar and the direction contract.
3. **Hero actions and trust line.**
   - The layout is now: the gold "Start today" button, then "I have an account" and "Try the demo" together on one line underneath, starting at the button's left edge. On phones the button is full width and the two links centre under it.
   - The dotted line is now a short checked list:
     - "Fixed safety checks run before any AI reply."
     - "Supports your care team. It does not diagnose."
     - "Your data is yours to delete at any time."
4. **One Tidewell lockup on every page.** A single `Wordmark` component (the Mark plus Alegreya "Tidewell") is now used on the landing page, the app shell, sign in, register, onboarding, the clinician view and Care Circle. Sign in and register (wide screens) show the same night-feed picture as the landing page.
5. **New illustrations for "One night with Tidewell"**, replacing the moon and sun windows. The text is unchanged.
   - **Talk for a minute:** a hand holding a phone by lamplight, with the moon button on its screen and the voice rising as tide lines.
   - **Safety comes first:** a pinned checklist with three ticked items and a call button.
   - **Your tide, in the morning:** an open notebook with the tide line drawn across it, beside a cup of tea.
   The morning plate is also used in the empty "Your tide" card. The window plates are removed.
6. **Visible checkboxes.** Consent, pregnancy complications and the support-person text consent (in onboarding and in Settings) now show a real box that fills with a tick when chosen. Space still toggles them, and the consent error clears as soon as the box is ticked (`after/onboarding-consent-unchecked-mobile.png`, `…-checked-mobile.png`, `onboarding-complications-mobile.png`).

These were verified with a third temporary account, which was deleted through Settings afterwards; signing in with it now fails. tsc, eslint, `next build` and the detector all pass. No console errors on any route.

---

## (a) Roast of the original UI, with evidence

**Landing**
- Sections rendered blank until a scroll-reveal fired (`Reveal` started at opacity 0), so a fast scroll or a screenshot showed empty bands (`before/02`–`05`).
- The closing CTA column was misaligned: x≈76 against x≈94, because the padding sat on the wrong wrapper.
- The hero was the generic split template, a headline beside a phone mockup (`before/01`).
- A hero-metric block (53% / 84% big numbers) appeared, then a "HOW IT WORKS" eyebrow over numbered 1/2/3 same-size cards, then an icon-card bento (`before/02`–`04`).
- The first phone viewport showed no product at all (`before/07`).
- The tab icon was the default Next.js favicon.

**App shell**
- On phone and tablet the primary action, the voice orb, was pushed below the fold by two cards (`before/11`, `before/17`).
- The orb "breathed" forever.
- The mobile tab bar floated in the middle of desktop screens.
- "Log out" was a bordered pill as loud as a primary action, on every screen (`before/11`–`16`).
- Ask had its own centred `max-w-2xl` column, unlike every other screen (`before/14`).

**Care** (`before/13`)
- A "Visit soon" badge appeared 4 times in one viewport: once overall and once on each card.
- Jargon: "Tidewell's Watch agent".
- Machine-shaped reasons: "Blood pressure 145/90 is 140/90 or higher.", "Mood check score 13/30 (13 or more).", "Incision pain 10/10."
- A border-left accent on the suggested visit, and identical cards in a 2-column grid.

**My tide** (`before/12`, `before/18`)
- The title "pratham's tide" used the lowercase username as a possessive.
- "Your last 3 days." sat next to a summary that said "this week".
- Sleep showed as "5.0 hours".
- The chart was labelled "Mood", but it plotted the EPDS score, where higher is worse. The visual says "up is good", so the chart read backwards.
- One data point sat in a huge dark panel.
- The history chips were heavy.
- Additional finding (verified this pass): `/overview` and `/trends` are fetched twice per load **only in dev** (React StrictMode). The production build fetches each once, so this is not a product bug.

**Clinician** (`before/19`)
- Database timings were shown to clinicians as hero numbers ("Risk overview query 145.3 ms").
- Tier shown as UPPERCASE colour pills.
- Additional finding: raw category keys reached the UI ("high_blood_pressure: …").

**Login** (`before/10`): an empty submit stated the username format rule instead of "Enter your username".

**Visits** (`before/16`): "whenever you want a second opinion" misdescribed what the page is for.

**Additional findings this pass (original UI)**
- Unicode arrows in the circular buttons (`before/11`) and in the urgent card's "← Go back".
- Kickers above headings in Book a visit, Mood check, Visits and Care Circle.
- Login, Care Circle and onboarding still carried the old teal/navy wave strip (`#13828a`, `#0b2545`), which is off-palette in the new world.
- Night mode: chart lines and legend swatches used fixed day colours, so the blood pressure "top number" line was near-invisible on the night background. This is fixed now.
- The idle orb's water still drifted forever. The earlier pass had removed the breathing but not the wave drift. This is fixed now.

**Opinion, not a defect:** Atkinson's slashed zero makes "10" read a little like "1θ". It is kept on purpose for legibility.

---

## (b) What changed in this pass

**Shell** (`app/(app)/layout.tsx`, `BottomNav.tsx`, `AccountMenu.tsx`, new `BackLink.tsx`)
- Header: the Mark plus the Alegreya wordmark.
- From md up, a running top nav under the header with a forest underline on the current page. Phones get the tab bar only (`md:hidden`).
- "Log out" and "Exit demo" are quiet underlined text buttons. On phones, "Demo as Maya" collapses to just "Exit demo".
- One content width (768px column) for every app screen. Ask's own centred column is gone.
- Sub-screens (Your visits, Book a visit, Mood check) have a top-left back link that names where it goes.
- `scrollbar-gutter: stable`, so tabs don't jump sideways.

**Screens**
- **My tide:**
  - Title "Your tide".
  - The history facts are now one sentence ("Day 19 after a C-section. Breastfeeding. …"), not chips.
  - "18 days logged so far." replaces "Your last N days".
  - Sleep reads "about 4 hours a night over the past week" (no ".0").
  - The mood section is now **"Weekly mood check: scored out of 30. Lower is better. A score of 10 or more is worth raising with your care team."** It shows the latest score in a sentence and shades the 10–30 band "10 or more: talk to your care team".
  - Every chart sits on a paper surface. The dark mood panel and per-section stagger entrances are removed.
  - Night-aware chart colours.
  - A new user sees one empty-state card ("Your charts start with your first check-in", "Check in now") instead of four empty chart frames.
- **Care:**
  - Status is now a sentence heading, set larger when serious ("Tidewell suggests a visit in the next few days."), not a badge.
  - Each area is a row with a sentence ("Worth a visit in the next few days. Latest blood pressure was 144/92, at or above the 140/90 limit. …"), most serious first, with an alert icon and larger type.
  - The suggested visit is on a lifted paper card with no border-left.
  - The intro is "After every check-in, Tidewell compares your numbers with guideline limits…", with no "Watch agent".
  - The emergency-room card is on paper with a red ring, not a border-left.
  - The place list is a divided list, not a card grid.
  - Video steps are a plain numbered list.
- **Backend copy** (`backend/app/agents/watch.py`): the reasons are now plain sentences, for example "Latest blood pressure was 145/90, at or above the 140/90 limit" and "Latest mood check scored 13 out of 30, where a follow-up is advised (13 or more)".
- **Ask:**
  - Shared width.
  - The starters are a single paper list under "Not sure how to start? Try one of these."
  - Answers are on paper.
  - Citation quotes have no border-left.
- **Visits:**
  - The empty state reads "No upcoming visits. When you want to see a doctor, midwife or counselor, book a visit in person near you or by video from home. If Tidewell suggests a visit, it shows on the Care page with the reasons." It has a small window vignette.
  - Visit cards lead with the date and time, then "Video visit with Dr. …".
- **Book a visit:**
  - Back link plus "Step 1 of 4" on one row.
  - The demo label "These providers are made up for the demo…" now sits **above** the provider cards.
  - Paper confirm and done states.
- **Mood check:**
  - Back link plus "Weekly mood check, question 1 of 10".
  - The result is a sentence: "Your score this week is 17 out of 30. Lower is better…".
- **Login / register:**
  - "Enter your username." and "Enter your password." first, with focus moved to the field.
  - Format rules apply only when creating an account.
  - The field is marked `aria-invalid` and linked to the error.
  - The Mark in the header and a night-window plate on wide screens. The old wave strip is removed.
- **Onboarding:** the Mark, a wider column, larger headings, a paper summary.
- **Clinician:**
  - Tiers are said in words ("Needs care now.", "Visit soon.").
  - Reasons are readable ("Blood pressure: …" with no snake_case) and joined as sentences.
  - Synthetic and app-created accounts are labelled.
  - Patient and check-in counts are one sentence.
  - The DB timings moved into a collapsed "Technical details for the demo (not clinical)".
- **Care Circle:** the status is a sentence on paper. The inactive link has a heading and an explanation. The wave strip is removed.
- **Urgent cards:**
  - Wording unchanged.
  - The headings are now the largest type in the app (Alegreya 36px).
  - The "call today" tier moved from a gold field to forest. Emergency stays red.
  - A drawn chevron replaces "←".
  - `/urgent?level=urgent` previews the "call today" tier, and the preview now has a way back.
- **Voice orb:** still while idle; the water moves only while recording or thinking. The mic disc is a fixed ivory, so it stays visible at night.
- **Today card:** a drawn alert icon replaces the gold status dot (gold is reserved for the moon and the one primary action).

**Favicon and assets:** `app/icon.svg` is the Mark (gold moon and ivory tide on forest). `app/favicon.ico` and the five unused default SVGs in `frontend/public/` are deleted; nothing referenced them.

**DESIGN.md and `.impeccable/design.json`:** written by the impeccable documenter from the shipped code.

---

## (c) Before / after pairs

| Screen | Before | After |
|---|---|---|
| Check in (tablet) | `before/11-home-tablet.jpg` | `after/home-tablet.png` |
| Check in (phone) | `before/17-home-mobile.jpg` | `after/home-mobile.png` |
| My tide (tablet) | `before/12-tide-tablet.jpg` | `after/tide-tablet.png` |
| My tide (phone) | `before/18-tide-mobile.jpg` | `after/tide-mobile.png` |
| Care (tablet) | `before/13-care-tablet.jpg` | `after/care-tablet.png` |
| Ask (tablet) | `before/14-ask-tablet.jpg` | `after/ask-tablet.png` |
| Settings (tablet) | `before/15-settings-tablet.jpg` | `after/settings-tablet.png` |
| Visits (tablet) | `before/16-visits-tablet.jpg` | `after/visits-tablet.png` |
| Login error | `before/10-login-error.jpg` | `after/login-error-mobile.png` |
| Clinician | `before/19-clinician-mobile.jpg` | `after/clinician-desktop.png` |
| Landing | `before/01-landing-desktop.jpg` | `after/landing-desktop.png` |

Also captured:
- Every app screen at all three widths.
- Night mode: `home-`, `care-` and `tide-night-desktop.png`.
- States: empty Tide, Care and Visits; check-in reply; Tide error state; mood result; both urgent tiers.
- Flows: booking confirm and done; in-person booking.
- Keyboard focus on the nav.

---

## (d) Test report

**Passed**
- `npx tsc --noEmit`, `npx eslint components lib app`, `npx next build` (19 routes).
- `backend/.venv/Scripts/python scripts/test_agents.py`: ALL PASS.
- `impeccable detect --json` on every changed UI file: `[]`.
- Public CTAs: Start tonight goes to /register, I have an account to /login, Try the demo to /home as Maya. /clinician, /circle/[token], /urgent and the auth pages all render.
- Login:
  - An empty submit shows "Enter your username." with focus on the field.
  - No password shows "Enter your password."
  - Wrong credentials show "That username and password don't match."
- Register, then all 10 onboarding steps, then /home.
- Refresh keeps the session: Settings still says "Signed in as …" after a reload.
- Logout clears the session and goes to /. Afterwards /home, /care and /settings show the sign-in chooser.
- Typed check-in: the reply renders and the spoken reply plays.
- Day editor: saved BP 122/78 and sleep 5.5; after a reload the form shows the same values and the header says "1 day logged so far."
- Mood check: 10 answers, then the follow-up question, then the fixed-wording urgent card, then Go back, then the result sentence.
- Ask: the answer comes back with a cited source.
- Care booking:
  - Video: Book a visit, provider, time, confirm, "Your visit is booked".
  - In person: ZIP 20742, a nearby OB-GYN, a time, "Booked … times here are illustrative".
  - Both bookings show in Your visits.
- Settings: the name saves and persists after a reload. Delete my account goes to /, and the old login no longer works.
- Night mode toggles on and off; checked on Check in, Care and My tide.
- Keyboard: the Tab order is Skip link, wordmark, Night mode, Log out, the five nav links, then Tap to talk. Every stop shows a focus ring.
- Reduced motion: 0 running animations on the landing. With motion allowed, the idle orb now has none either; the earlier capture found 2 infinite ones.
- No console errors on any app route. The expected network noise is a 401 on a wrong login and a 404 on the `/circle/preview` placeholder token.
- No horizontal overflow on 24 app captures at 1440, 768 and 390.
- Empty, loading, error and success states captured.

**Failed (pre-existing, not caused by this pass)**
- `pytest tests`: 6 failed, 116 passed.
  - 5 are in `tests/test_api_mock.py`: the onboard tests, trends shape, and typed-vitals red flag.
  - They fail the same way with the original `watch.py` restored.
  - The 6th, `test_extract[relative-no-numbers]`, needs a live Gemini call.

**Blocked / not run**
- Signing in as "pratham". I used two clearly named temporary local accounts instead (`zz_redesign_temp_…`). Both are deleted: one through Settings > Delete, and one through the backend's own delete functions after I lost its random password.
- Real voice recording, which needs a microphone. The typed path was tested instead.
- A production-build run against the API: the backend's CORS allows only :3000. That run still showed the Tide error state and single fetches.
- A capture of the empty Tide vignette (it is in code).

---

## (e) Limitations, plainly

- **Other people's test data shows in the clinician view.** "Patient" (Day 10, 165/100) and "Admin Test" were created by someone else. They now carry the label "(account created in the app, may be a test)". I did not delete them; that is your call.
- **Old stored reasons.** Watch assessments stored before the rewording still read the old way ("Severe-range blood pressure…", "(13 or more)") until the agent re-assesses those patients. I did not rewrite database rows.
- **Small vignettes.** The window vignettes use the same gouache filters as the landing plates, but at 96–112px the grain barely shows. The finish reviewer called them flat. Making them larger, or cropping from the hero plate, is the fix if you want more texture.
- **Finish review.** The finish reviewer ran two rounds, the budget. Round 2 scored the night mic contrast, kickers, content width and demo label as resolved. After round 2 I fixed three more items; I have checked them in screenshots, but the reviewer has not scored them:
  - the "call today" urgent tier on a forest field with the large heading (`after/urgent-today-mobile.png`);
  - the clinician reasons joining as sentences;
  - the repeated category labels.
  The documenter's drift notes are fixed too: the gold status dot, the mint confirmation fills, `shadow-xl`, and the dead night CSS.
- **Seed key.** The direction contract's seed key `6cef850d` came from the earlier session's concept roll, and I can't re-derive it here.
- **Formatting.** `Dashboard.tsx` was briefly reformatted by Prettier defaults. I rebased my changes back onto the original style; the remaining diff in that file is real restructuring.
- **Line endings.** Git warns that LF will become CRLF in several files. That is existing repository behaviour.
- **`.impeccable/config.json` has no `buildPath`.** Image generation isn't available here, so there was no choice to record.
