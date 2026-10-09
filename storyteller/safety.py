"""Safety guard. Runs on the initial request AND on every free-text player action.

Layer 1: OpenAI's moderation endpoint (free) - only when the provider is OpenAI, the only one that offers it.
Layer 2: an LLM yes/no judge (prompt in prompts.py) for every other provider, or if the endpoint errors.
The planner and narrator prompts also carry content rules, so this is defence in depth, not a single gate.
"""
from . import config, llm, prompts

REFUSAL = "I can't weave a story around that. Try another idea - a mystery, a voyage, a strange city?"


def is_allowed(text: str) -> bool:
    if config.LLM_PROVIDER == "openai":
        try:
            return not llm.client().moderations.create(model="omni-moderation-latest", input=text).results[0].flagged
        except Exception:
            pass  # fall through to the LLM judge
    verdict = llm.chat_json("safety", prompts.SAFETY_SYSTEM, text, temperature=0)
    return bool(verdict.get("allowed", False))
