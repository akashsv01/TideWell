import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import get_settings
from app.routes import agents, appointments, auth, checkin, clinician, epds, patients, wearables

# Show app logs (check-in timings, safety fallbacks) next to uvicorn's access log.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s: %(message)s")


async def _watch_loop() -> None:
    """The Watch agent re-analyses every active patient every 30 minutes (catches silence too)."""
    from app.agents import watch

    while True:
        await asyncio.sleep(1800)
        try:
            n = await asyncio.to_thread(watch.sweep)
            logging.getLogger("tidewell.watch").info("sweep analysed %d patients", n)
        except Exception:  # noqa: BLE001
            logging.getLogger("tidewell.watch").exception("sweep failed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(_watch_loop()) if db.enabled() else None
    yield
    if task:
        task.cancel()
    db.close()


app = FastAPI(title="Tidewell API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().frontend_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(patients.router)
app.include_router(appointments.router)
app.include_router(clinician.router)
app.include_router(checkin.router)
app.include_router(auth.router)
app.include_router(epds.router)
app.include_router(agents.router)
app.include_router(wearables.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "database": "configured" if db.enabled() else "not configured (mock data)"}
