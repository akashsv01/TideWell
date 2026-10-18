# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

A parent in the 12 months after giving birth. Often tired, short on time, holding a baby, checking in at odd
hours (3 a.m. feeds are a real usage scene). Their job: a one-minute check-in, mostly by voice, so warning signs
after birth (blood pressure, mood, bleeding, infection) are noticed early and they are guided to the right care.

Secondary audiences that exist in the product: the care team (clinician view, visit summary PDF) and a support
person (read-only Care Circle link).

## Product Purpose

Tidewell is a voice-first companion for the year after birth. The parent talks for a minute; Tidewell extracts
mood, sleep, pain, bleeding and blood pressure, runs fixed safety rules first, replies in plain language, and keeps
a day-by-day record ("My tide"). A Watch agent compares the trend against guideline thresholds and, when needed,
suggests a visit and finds care nearby. Success: a warning sign reaches care sooner, without the parent having to
interpret numbers alone.

## Positioning

Not a symptom checker and not a diary: it listens daily, remembers the trend, and acts on it. Fixed safety rules run
before any AI and show fixed wording; the AI never diagnoses.

## Operating Context

- Daily check-in by voice (or typed), one minute; weekly 10-question mood check (EPDS, scored out of 30).
- Day editing for typed numbers; BP cuff photo reading; Apple Health import from an iPhone (or labelled sample data).
- Care: Watch agent tiers, suggested visit with reasons, booking in person at nearby real clinics (NPI Registry) or by
  video with demo providers, upcoming visits, visit summary PDF.
- Ask: pregnancy/postpartum questions answered from trusted sources with citations; off-topic questions declined.
- Night mode for night feeds; English and Spanish preference.
- Hackathon project (Technica 2026), deployed on Vercel (web) and Render (API, video server).

## Capabilities and Constraints

- Safety screens (urgent/emergency cards) use fixed, pre-written wording and must stay instantly readable.
- Demo patient "Maya" is shared and read-only; made-up video providers are labelled as demo.
- Booking at nearby clinics uses a demo scheduler; times are illustrative and must be labelled as such.
- Next.js 16 (cacheComponents), Tailwind 4 tokens in globals.css, FastAPI backend.

## Brand Commitments

- Name: Tidewell. The tide / ebb-and-flow metaphor is binding ("My tide", waves, the water-filled voice orb).

## Evidence on Hand

- Real product flows and data shapes (seeded demo patient Maya, 300 synthetic patients for the clinician view).
- No testimonials, partner clinics, press, usage numbers or clinical validation exist. Do not fabricate any.

## Product Principles

1. One minute, one hand: the daily path must work tired, at night, one-handed.
2. Safety first and fixed: rules before AI, plain fixed wording on urgent screens, never diagnose.
3. Show the why: every suggestion carries its reasons and source.
4. Honest demo: label made-up providers, sample data and illustrative times.

## Accessibility & Inclusion

Large type and touch targets, high contrast in day and night, keyboard access, reduced motion respected; plain
language for a stressed, sleep-deprived reader.
