"""ElevenLabs speech-to-text.

Confirmed API (elevenlabs Python SDK v2):
  client = ElevenLabs(api_key=...)
  resp = client.speech_to_text.convert(model_id="scribe_v2", file=(name, bytes_or_fileobj, mime))
  resp.text -> transcript
Docs: https://github.com/elevenlabs/elevenlabs-python/blob/main/_autodocs/api-reference/speech-to-text.md
"""
from typing import Optional

from elevenlabs import ElevenLabs

from app.config import get_settings

STT_MODEL = "scribe_v2"

# Browser MediaRecorder types -> file extension, so the upload is labelled correctly.
_EXT = {"audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "m4a", "audio/x-m4a": "m4a",
        "audio/aac": "aac", "audio/mpeg": "mp3", "audio/wav": "wav", "audio/x-wav": "wav"}


def transcribe(audio_bytes: bytes, mime: Optional[str] = None) -> str:
    base = (mime or "audio/mpeg").split(";")[0].strip().lower()  # drop ";codecs=opus"
    filename = f"audio.{_EXT.get(base, 'webm')}"
    client = ElevenLabs(api_key=get_settings().elevenlabs_api_key)
    resp = client.speech_to_text.convert(model_id=STT_MODEL, file=(filename, audio_bytes, base))
    return (resp.text or "").strip()
