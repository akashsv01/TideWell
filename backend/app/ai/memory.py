"""Backboard memory: one Backboard assistant (+ current thread) per patient.

Confirmed API (backboard-sdk 1.5.x, async; signatures checked via inspect):
  client = BackboardClient(api_key=...)
  await client.create_assistant(name=..., system_prompt=...)              -> Assistant.assistant_id
  await client.create_thread(assistant_id)                                 -> Thread.thread_id
  await client.add_message(thread_id, content=..., memory="Auto", send_to_llm="false")
                                                                           -> stores + extracts memory, no LLM call
  await client.search_memories(assistant_id, query=..., limit=5)           -> {"memories": [{"content", "score"}], ...}
  await client.get_thread(thread_id)                                       -> Thread.messages[].content
Memory lives on the ASSISTANT (not the thread) and memory="Auto" must be passed every turn.
Verified live 2026-10-17: Backboard's free credit covers Memory & RAG but NOT LLM chat
(send_message returns a billing notice as .content). So Backboard stores/searches memory and
Gemini writes the reply. With paid Backboard credit, send_message(..., llm_provider="google") also works.
Docs: https://docs.backboard.io/sdk/first-message  |  https://docs.backboard.io/sdk/memory

Sync wrappers (chat, recall, get_or_create) are for P2's FastAPI routes; async versions are
prefixed with "a" (achat, arecall, aget_or_create) for async routes.
"""
import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Coroutine, Optional, TypeVar
from uuid import UUID

from backboard import BackboardClient

from app.ai.prompts import CARE_NAVIGATOR_SYSTEM_PROMPT
from app.config import BACKEND_DIR, get_settings

log = logging.getLogger(__name__)
T = TypeVar("T")

# --- Mapping store -------------------------------------------------------------
# Stored on the patient row (patients.backboard_assistant_id / backboard_thread_id) when the database
# is configured and the patient exists; otherwise in a local JSON file (tests, smoke test, no DB).
_STORE = BACKEND_DIR / ".data" / "backboard_ids.json"


def _read_all() -> dict:
    return json.loads(_STORE.read_text()) if _STORE.exists() else {}


def _db_patient(patient_id: str) -> Optional[UUID]:
    from app import db

    if not db.enabled():
        return None
    try:
        return UUID(patient_id)
    except ValueError:
        return None


def get_mapping(patient_id: str) -> dict:
    """{"assistant_id": ..., "thread_id": ...} for a patient, or {} if none yet."""
    pid = _db_patient(patient_id)
    if pid is not None:
        from app import store

        found = store.get_backboard_ids(pid)
        if found:
            return found
    return _read_all().get(patient_id, {})


def save_mapping(patient_id: str, mapping: dict) -> None:
    pid = _db_patient(patient_id)
    if pid is not None:
        from app import store

        if store.set_backboard_ids(pid, mapping["assistant_id"], mapping.get("thread_id")):
            return
    data = _read_all()
    data[patient_id] = mapping
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(data, indent=2))


# --- Async core -------------------------------------------------------------------
def _client() -> BackboardClient:
    return BackboardClient(api_key=get_settings().backboard_api_key)


async def aget_or_create(patient_id: str, new_thread: bool = False) -> str:
    """Return the patient's Backboard assistant_id, creating the assistant and a thread if needed.
    new_thread=True starts a fresh thread; memory still carries over because it lives on the assistant."""
    m = get_mapping(patient_id)
    client = _client()
    if not m.get("assistant_id"):
        a = await client.create_assistant(name=f"tidewell-{patient_id}", system_prompt=CARE_NAVIGATOR_SYSTEM_PROMPT)
        m = {"assistant_id": str(a.assistant_id)}
    if new_thread or not m.get("thread_id"):
        t = await client.create_thread(m["assistant_id"])
        m["thread_id"] = str(t.thread_id)
    save_mapping(patient_id, m)
    return m["assistant_id"]


async def achat(patient_id: str, message: str, context: Optional[str] = None) -> str:
    """Memory-grounded reply: search past memories, store this message in Backboard (no LLM),
    and have Gemini write the reply. `context` is the patient's chart summary (see checkin.py).
    Not the full Care Navigator (that is agent.py)."""
    await aget_or_create(patient_id)
    m = get_mapping(patient_id)
    client = _client()
    memories, _ = await asyncio.gather(
        arecall(patient_id, message),
        client.add_message(m["thread_id"], content=message, memory="Auto", send_to_llm="false"),
    )
    return await asyncio.to_thread(_gemini_reply, message, memories, context)


def _gemini_reply(message: str, memories: list[str], context: Optional[str] = None) -> str:
    from google.genai import types

    from app.ai._gemini import generate

    remembered = "\n".join(f"- {x}" for x in memories) or "- (nothing yet)"
    chart = f"About this person (from their chart and recent check-ins):\n{context}\n\n" if context else ""
    r = generate(
        contents=f"{chart}What you remember about this person from past conversations:\n{remembered}\n\nThey say: {message}",
        config=types.GenerateContentConfig(system_instruction=CARE_NAVIGATOR_SYSTEM_PROMPT, temperature=0.4),
    )
    return (r.text or "").strip()


def _memory_texts(raw: Any) -> list[str]:
    """search_memories returns a dict whose exact shape is undocumented; accept common shapes."""
    if isinstance(raw, dict):
        items = raw.get("memories") or raw.get("results") or raw.get("data") or []
    else:
        items = raw or []
    out = []
    for it in items:
        if isinstance(it, dict):
            text = it.get("content") or it.get("memory") or it.get("text")
        else:
            text = getattr(it, "content", None)
        if text:
            out.append(str(text))
    return out


async def arecall(patient_id: str, query: str, limit: int = 5) -> list[str]:
    """Memories relevant to `query`. Falls back to the thread's recent messages if search fails or is empty."""
    m = get_mapping(patient_id)
    if not m.get("assistant_id"):
        return []
    client = _client()
    try:
        found = _memory_texts(await client.search_memories(m["assistant_id"], query=query, limit=limit))
        if found:
            return found
    except Exception as e:  # noqa: BLE001
        log.warning("search_memories failed (%s); falling back to recent messages", e)
    if not m.get("thread_id"):
        return []
    thread = await client.get_thread(m["thread_id"])
    return [f"{msg.role}: {msg.content}" for msg in (thread.messages or [])[-limit:] if msg.content]


# --- Sync wrappers (safe from plain scripts and from sync or async FastAPI routes) --------
_pool = ThreadPoolExecutor(max_workers=4)


def _run(coro: Coroutine[Any, Any, T]) -> T:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return _pool.submit(asyncio.run, coro).result()  # already inside an event loop


def get_or_create(patient_id: str, new_thread: bool = False) -> str:
    return _run(aget_or_create(patient_id, new_thread))


def chat(patient_id: str, message: str, context: Optional[str] = None) -> str:
    return _run(achat(patient_id, message, context))


def recall(patient_id: str, query: str, limit: int = 5) -> list[str]:
    return _run(arecall(patient_id, query, limit))


async def aforget(patient_id: str) -> None:
    """Delete the patient's Backboard memories (delete-my-data). Ids must be read before the
    patient row is deleted."""
    m = get_mapping(patient_id)
    if m.get("assistant_id"):
        await _client().reset_memories(m["assistant_id"])
    data = _read_all()
    if data.pop(patient_id, None) is not None:
        _STORE.write_text(json.dumps(data, indent=2))


def forget(patient_id: str) -> None:
    _run(aforget(patient_id))
