"""ElevenLabs text-to-speech.

Confirmed API (elevenlabs Python SDK v2):
  client.text_to_speech.convert(voice_id=..., text=..., model_id="eleven_multilingual_v2",
                                output_format="mp3_44100_128") -> Iterator[bytes]
Default voice: premade "Sarah" (EXAVITQu4vr4xnSDxMaL); override with ELEVENLABS_VOICE_ID.
Docs: https://github.com/elevenlabs/elevenlabs-python/blob/main/reference.md
"""
from elevenlabs import ElevenLabs

from app.config import get_settings

TTS_MODEL = "eleven_multilingual_v2"
OUTPUT_FORMAT = "mp3_44100_128"


def speak(text: str) -> bytes:
    s = get_settings()
    client = ElevenLabs(api_key=s.elevenlabs_api_key)
    chunks = client.text_to_speech.convert(
        voice_id=s.elevenlabs_voice_id,
        text=text,
        model_id=TTS_MODEL,
        output_format=OUTPUT_FORMAT,
    )
    return b"".join(chunks)
