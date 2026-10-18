# TideWell

Tidewell is a voice-first companion for the "fourth trimester," the year after giving birth, when new parents get the least medical support and face the most risk. Each day the parent does a short voice check-in. The backend transcribes it with ElevenLabs and runs a rule-based red-flag safety check before any AI is involved; urgent symptoms get a fixed, pre-written "get care now" response. Safe check-ins go to a Gemini "Care Navigator" agent with long-term memory (Backboard). Gemini also extracts structured metrics, which are stored in Tiger Data (Postgres + TimescaleDB + pgvector), and the reply is spoken back with ElevenLabs. Tidewell never diagnoses.

## Layout

- `backend/`: FastAPI (Python 3.11+). AI pipeline in `app/ai/` (see `app/ai/README.md`), API contract in `app/schemas.py`, SQL in `app/store.py` and `migrations/`.
- `frontend/`: Next.js 16 + Tailwind 4.
- `clinical_assets/`: guideline chunks, thresholds and scripts (Person 4).

## Run locally

Backend (terminal 1):

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate              # Windows; `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp .env.example .env                # fill in your keys (never commit .env)
python scripts/migrate.py           # once, and after pulling new migrations
python scripts/seed_maya.py         # demo patient; re-run any time to reset Maya
python scripts/smoke_test.py        # PASS/FAIL/SKIPPED per AI service
uvicorn app.main:app --reload       # http://localhost:8000/health  ·  docs at /docs
```

Frontend (terminal 2):

```bash
cd frontend
npm install
cp .env.example .env.local          # optional: API URL, mock mode
npm run dev                         # http://localhost:3000
```

If a CSS change doesn't show up in `npm run dev`, restart the dev server (Tailwind's Turbopack loader can serve a stale stylesheet).

## Accounts and the demo

- **Accounts:** username + password (`/register`, `/login`, Log out). Passwords are stored as scrypt hashes; sessions are server-side tokens (only a SHA-256 is stored) that logout revokes. Tables: `users`, `sessions`, `patients.user_id` (migration 003).
- **Onboarding** collects the baseline profile (consent, delivery date, weeks, delivery method, feeding, mental health history, pregnancy complications, language, support person + SMS consent). Edit it any time in Settings > Your details.
- **Daily data:** check-ins (mood, pain, incision pain, sleep, headache, BP) and the weekly EPDS mood check (from day 7; score and question 10 alert) feed the tide.
- **Access:** every patient route checks the session. The demo patient Maya (day 18, C-section, rising BP) is open to everyone and read-only in Settings; any other record is visible only to its own account.
- **Delete my account and data** (Settings) removes the account, every row and the Backboard memories. Maya cannot be deleted; `python scripts/seed_maya.py` resets her.

## AI agents and care

- **Watch agent** (`backend/app/agents/watch.py`): after every check-in, daily log and mood check, and every 30 minutes, it assesses each patient (blood pressure, mood, C-section recovery, sleep, check-in gaps) using the thresholds in `clinical_assets/`. Gemini writes the clinician note only when something needs action.
- **Booking agent** (`backend/app/agents/booking.py`): amber or red becomes a care request with the nearest OB-GYN, midwife or hospital (red: nearest ER) and proposed times. The patient books with one tap on the Care page; the note goes to the clinician.
- **Care Navigator** (`backend/app/ai/agent.py`, the Ask tab): Gemini tool-calling over the patient's trends, risk, memory, nearby care and trusted guidance.
- **Trusted guidance** (`backend/app/ai/guidelines.py`): Gemini Google Search grounding limited to trusted health sites (CDC, NIH, WHO, ACOG, and the `guidelines.json` sources), with citations; `guidelines.json` is the offline fallback. Grounding needs Gemini quota (a paid key or credits).
- **Nearby care**: OpenStreetMap (Nominatim + Overpass), from browser location or ZIP code, no API key needed.
- Also: visit summary PDF, BP cuff photo reading (Gemini vision), Care Circle read-only link for the support person, night mode (10 pm to 6 am), clinician view at `/clinician` with Tiger Data query timing.
- Scripts: `python scripts/seed_synthetic.py --n 300` (clinic-scale demo data), `python scripts/test_agents.py` (end-to-end check of the agents, in-process).

## Deploy

- **Backend → Render:** New > Blueprint > this repo (uses `render.yaml`). Fill the secret env vars when asked, set `FRONTEND_ORIGINS` to your Vercel URL, then run `python scripts/seed_maya.py` once from the Render shell.
- **Frontend → Vercel:** import the repo, set Root Directory to `frontend`, and add `NEXT_PUBLIC_API_URL` (your Render URL).
- **Gemini quota:** free-tier keys allow ~20 requests/day per model and a check-in uses 3–4. Use a paid key or hackathon credits for the demo; the backend falls back to `GEMINI_FAST_MODEL` when the main model is out of quota.
