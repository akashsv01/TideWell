"""Care Navigator agent: a Gemini tool-calling loop over app/ai/tools.py (fake data in Phase 1).

Callers must run red_flags.check() first and never reach this agent on a red flag.
Gemini API (google-genai): generate_content(config=GenerateContentConfig(tools=[types.Tool(...)]));
read response.function_calls, append response.candidates[0].content (keeps thought signatures), then a
role="user" Content of types.Part.from_function_response(name=..., response=...). After the tool budget
is spent, a final call with FunctionCallingConfig(mode="NONE") forces a text reply.
Docs: https://github.com/googleapis/python-genai (Function Calling)
"""
import json
import logging
from dataclasses import dataclass, field

from google.genai import types

from app.ai import tools
from app.ai._gemini import generate
from app.ai.prompts import CARE_NAVIGATOR_SYSTEM_PROMPT
from app.schemas import CheckinMetrics

log = logging.getLogger(__name__)

MAX_TOOL_CALLS = 4
FALLBACK_REPLY = "Thank you for checking in with me today. I've noted how you're feeling. How are you doing right now?"


@dataclass
class AgentReply:
    text: str
    tools_called: list[str] = field(default_factory=list)


class CareNavigator:
    def run(self, patient_id: str, transcript: str, metrics: CheckinMetrics) -> AgentReply:
        prompt = (
            f"Today is {tools.TODAY.strftime('%A %B %d, %Y')}.\n"  # Phase 3: date.today()
            f"Today's check-in (spoken): {transcript}\n"
            f"Extracted metrics: {metrics.model_dump_json(exclude_defaults=True)}\n"
            "Check the risk tiers before choosing the next step."
        )
        contents: list[types.Content] = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        called: list[str] = []
        config = types.GenerateContentConfig(
            system_instruction=CARE_NAVIGATOR_SYSTEM_PROMPT, tools=[tools.GEMINI_TOOL], temperature=0.4
        )
        try:
            while True:
                if len(called) >= MAX_TOOL_CALLS:
                    config = config.model_copy(update={"tool_config": types.ToolConfig(
                        function_calling_config=types.FunctionCallingConfig(mode="NONE"))})
                resp = generate(contents, config)
                calls = resp.function_calls or []
                if not calls:
                    return AgentReply((resp.text or "").strip() or FALLBACK_REPLY, called)
                contents.append(resp.candidates[0].content)
                parts = []
                for fc in calls:
                    if len(called) >= MAX_TOOL_CALLS:
                        result = {"error": "tool budget for this turn is used up; answer now"}
                    else:
                        called.append(fc.name)
                        try:
                            result = {"result": tools.call_tool(fc.name, fc.args, patient_id)}
                        except Exception as e:  # noqa: BLE001 - let the model recover
                            result = {"error": f"{type(e).__name__}: {e}"}
                    parts.append(types.Part.from_function_response(name=fc.name, response=json.loads(json.dumps(result, default=str))))
                contents.append(types.Content(role="user", parts=parts))  # API rejects role="tool"
        except Exception as e:  # noqa: BLE001 - a check-in must never crash on the agent
            log.warning("CareNavigator failed (%s: %s); using fallback reply", type(e).__name__, e)
            return AgentReply(FALLBACK_REPLY, called)
