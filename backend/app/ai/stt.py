"""ElevenLabs speech-to-text.

Confirmed API (elevenlabs Python SDK v2):
  client = ElevenLabs(api_key=...)
  resp = client.speech_to_text.convert(model_id="scribe_v2", file=(name, bytes_or_fileobj, mime))
  resp.text -> transcript
Docs: https://github.com/elevenlabs/elevenlabs-python/blob/main/_autodocs/api-reference/speech-to-text.md
"""
from elevenlabs import ElevenLabs

from app.config import get_settings

STT_MODEL = "scribe_v2"


def transcribe(audio_bytes: bytes, filename: str = "audio.mp3", mime: str = "audio/mpeg") -> str:
    client = ElevenLabs(api_key=get_settings().elevenlabs_api_key)
    resp = client.speech_to_text.convert(model_id=STT_MODEL, file=(filename, audio_bytes, mime))
    return (resp.text or "").strip()
