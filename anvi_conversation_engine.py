"""
ANVIQO CONVERSATIONAL INTELLIGENCE ENGINE

LLM = language and conversational synthesis only.
Existing ANVIQO/V5 modules remain the source of plant evidence.

Safety:
- No PLC writes.
- No SCADA control.
- No invented plant facts.
- Human decision required.
"""

import json
import os
import urllib.request
import urllib.error


MODEL = os.getenv("ANVI_LLM_MODEL", "gpt-5.5")


SYSTEM_PROMPT = """
You are ANVI, the conversational intelligence layer of ANVIQO.

ANVIQO is an industrial plant intelligence system.

You communicate naturally with technicians, engineers, supervisors
and management.

The existing ANVIQO evidence and V5 intelligence layers are the
source of plant facts.

NEVER invent:
- instrument tags
- PLC addresses
- readings
- alarms
- events
- failures
- plant history
- maintenance history
- plant conditions

If evidence is missing, say so.

If data is DEMO SIMULATION, explicitly say so.

If information comes from a HUMAN FIELD REPORT, identify it as such
and do not automatically treat it as proven causation.

Separate:
1. VERIFIED FACT
2. POSSIBLE EXPLANATION
3. RECOMMENDED CHECK

You may explain technical concepts, summarize evidence, connect
related evidence, explain reasoning, discuss possible causes as
hypotheses, and suggest safe inspection steps.

Never claim that ANVI executed a repair or control action.

Never execute PLC or SCADA control through conversation.

Human approval remains mandatory.

Answer naturally and helpfully rather than sounding like a database.

If evidence is insufficient, be honest about uncertainty.
"""


def _safe_json(value):
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    except Exception:
        return str(value)


def _build_prompt(question, evidence=None, conversation=None):

    return f"""
USER QUESTION:
{question}

ANVI EVIDENCE:
{_safe_json(evidence or {})}

RECENT CONVERSATION:
{_safe_json(conversation or [])}

Answer naturally using the evidence.

Do not invent missing plant information.

If the evidence is insufficient:
- explain what is known
- explain what is unknown
- explain what information/check would be useful next
"""


def _openai_request(question, evidence=None, conversation=None):

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return None, "OPENAI_API_KEY is not configured."

    payload = {
        "model": MODEL,
        "instructions": SYSTEM_PROMPT,
        "input": _build_prompt(
            question,
            evidence=evidence,
            conversation=conversation,
        ),
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))

        text = body.get("output_text")

        if text:
            return text.strip(), None

        # Defensive extraction if output_text is unavailable.
        output = body.get("output", [])

        parts = []

        for item in output:
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    parts.append(content.get("text", ""))

        text = "\n".join(x for x in parts if x).strip()

        if text:
            return text, None

        return None, "The model returned no text."

    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            detail = str(exc)

        return None, f"OpenAI HTTP {exc.code}: {detail}"

    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def conversational_answer(
    question,
    evidence=None,
    conversation=None,
):

    question = str(question or "").strip()

    if not question:
        return {
            "answer": "Please ask ANVI a question.",
            "domain": "conversation",
            "read_only": True,
        }

    answer, error = _openai_request(
        question,
        evidence=evidence,
        conversation=conversation,
    )

    if answer:

        return {
            "answer": answer,
            "domain": "conversation",
            "llm_available": True,
            "model": MODEL,
            "read_only": True,
            "human_decision_required": True,
        }

    return {
        "answer": (
            "ANVI's conversational intelligence is not currently "
            f"available. {error}"
        ),
        "domain": "conversation",
        "llm_available": False,
        "read_only": True,
        "human_decision_required": True,
    }


if __name__ == "__main__":

    print("ANVI CONVERSATIONAL ENGINE")
    print("---------------------------")
    print("Model:", MODEL)

    if os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY: CONFIGURED")
    else:
        print("OPENAI_API_KEY: NOT CONFIGURED")

    print("Engine import test: OK")
