"""Care Navigator agent. Phase 0 stub. Phase 1: Gemini + tools + Backboard memory.

Callers must run red_flags.check() first and never reach this agent on a red flag.
"""
from app.schemas import CheckinMetrics


class CareNavigator:
    def run(self, patient_id: str, transcript: str, metrics: CheckinMetrics) -> str:
        # TODO(phase1): Gemini tool-calling loop (see extract.py header) + memory.chat()
        return "Thanks for checking in today. I've noted how you're feeling. I'll have more for you soon."
