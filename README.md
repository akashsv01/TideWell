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
cp .env.example .env.local          # optional: API URL, mock mode, Clerk keys
npm run dev                         # http://localhost:3000
```

If a CSS change doesn't show up in `npm run dev`, restart the dev server (Tailwind's Turbopack loader can serve a stale stylesheet).

## Accounts and the demo

- **New user:** "Get started" runs onboarding, which creates a patient record. That browser remembers the patient id, so check-ins, trends and replies are personal to them (days postpartum, delivery, history, last week's sleep/mood/BP).
- **Demo:** "Try the demo" switches to Maya (day 18, C-section, rising BP). Maya cannot be deleted; `python scripts/seed_maya.py` resets her.
- **Sign-in (optional):** put Clerk keys in `frontend/.env.local` (`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`) and restart. Sign-up then leads to onboarding, and the patient is linked to the login (`patients.clerk_user_id`), so it follows the user across devices. Without keys the app runs signed-out. Known gap: the backend trusts the login id the frontend sends; verify the Clerk session token in `GET /me` before real use.
- **Delete my data** (Settings) removes the patient's rows and Backboard memories.

## Deploy

- **Backend → Render:** New > Blueprint > this repo (uses `render.yaml`). Fill the secret env vars when asked, set `FRONTEND_ORIGINS` to your Vercel URL, then run `python scripts/seed_maya.py` once from the Render shell.
- **Frontend → Vercel:** import the repo, set Root Directory to `frontend`, and add `NEXT_PUBLIC_API_URL` (your Render URL) plus the Clerk keys if you use sign-in.
- **Gemini quota:** free-tier keys allow ~20 requests/day per model and a check-in uses 3–4. Use a paid key or hackathon credits for the demo; the backend falls back to `GEMINI_FAST_MODEL` when the main model is out of quota.
