# TideWell

Tidewell is a voice-first companion for the "fourth trimester," the year after giving birth, when new parents get the least medical support and face the most risk. Each day the parent does a short voice check-in. The backend transcribes it with ElevenLabs and runs a rule-based red-flag safety check before any AI is involved; urgent symptoms get a fixed, pre-written "get care now" response. Safe check-ins go to a Gemini "Care Navigator" agent with long-term memory (Backboard). Gemini also extracts structured metrics, which are stored in Tiger Data (Postgres + TimescaleDB + pgvector), and the reply is spoken back with ElevenLabs. Tidewell never diagnoses.

## Layout

- `backend/`: FastAPI (Python 3.11+). AI wrappers live in `app/ai/`, the API contract in `app/schemas.py`.
- `frontend/`: Next.js (owned by Person 3).

## Run the backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp .env.example .env          # then fill in your keys (never commit .env)
python scripts/smoke_test.py  # PASS/FAIL/SKIPPED per AI service
uvicorn app.main:app --reload # http://localhost:8000/health
```
