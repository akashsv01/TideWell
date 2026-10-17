"""Backboard memory wrapper (one Backboard assistant per Tidewell user).

Confirmed API (backboard-sdk, async):
  client = BackboardClient(api_key=...)
  a = await client.create_assistant(name=..., system_prompt=...)        -> a.assistant_id
  t = await client.create_thread(assistant_id)                          -> t.thread_id
  r = await client.send_message(content, thread_id=..., assistant_id=..., memory="Auto",
                                llm_provider="google", model_name=...) -> r.content, r.memory_operation_id
  await client.get_memory_operation_status(operation_id)                -> "COMPLETED" | "IN_PROGRESS" | "ERROR"
Memory is stored per ASSISTANT, not per thread, and memory="Auto" must be passed on every turn.
Docs: https://docs.backboard.io/sdk/first-message  |  https://docs.backboard.io/sdk/memory
"""
import asyncio
import json
from typing import Optional

from backboard import BackboardClient

from app.config import BACKEND_DIR, get_settings

SYSTEM_PROMPT = (
    "You are Tidewell, a warm, calm postpartum care companion. You remember what the parent has told you. "
    "You never diagnose. Keep replies short and kind."
)
LLM_PROVIDER = "google"

# TODO(phase1): move this user -> assistant/thread map into Tiger Data.
_STORE = BACKEND_DIR / ".backboard_users.json"


def _load() -> dict:
    return json.loads(_STORE.read_text()) if _STORE.exists() else {}


def _save(data: dict) -> None:
    _STORE.write_text(json.dumps(data, indent=2))


def _client() -> BackboardClient:
    return BackboardClient(api_key=get_settings().backboard_api_key)


async def get_or_create_assistant(user_id: str) -> str:
    data = _load()
    if aid := data.get(user_id, {}).get("assistant_id"):
        return aid
    a = await _client().create_assistant(name=f"tidewell-{user_id}", system_prompt=SYSTEM_PROMPT)
    data[user_id] = {"assistant_id": str(a.assistant_id)}
    _save(data)
    return str(a.assistant_id)


async def get_or_create_thread(user_id: str, new: bool = False) -> str:
    """Return the user's current thread. new=True starts a fresh thread (memory still carries over)."""
    assistant_id = await get_or_create_assistant(user_id)
    data = _load()
    if not new and (tid := data[user_id].get("thread_id")):
        return tid
    t = await _client().create_thread(assistant_id)
    data[user_id]["thread_id"] = str(t.thread_id)
    _save(data)
    return str(t.thread_id)


async def chat(user_id: str, message: str, thread_id: Optional[str] = None, wait_for_memory: bool = False) -> str:
    client = _client()
    assistant_id = await get_or_create_assistant(user_id)
    thread_id = thread_id or await get_or_create_thread(user_id)
    r = await client.send_message(
        message,
        thread_id=thread_id,
        memory="Auto",
        llm_provider=LLM_PROVIDER,
        model_name=get_settings().gemini_model,
    )
    if wait_for_memory and getattr(r, "memory_operation_id", None):
        for _ in range(30):  # memory extraction is async on Backboard's side
            status = await client.get_memory_operation_status(r.memory_operation_id)
            if str(getattr(status, "status", status)).upper() != "IN_PROGRESS":
                break
            await asyncio.sleep(1)
    return r.content or ""
