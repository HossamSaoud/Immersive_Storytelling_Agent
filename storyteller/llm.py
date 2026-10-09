"""The ONLY file that talks to a model provider. Everything else calls chat()/chat_json() with a role name.

A "role" is one of the agents ("planner", "narrator", "critic", "director", "safety"); config.MODELS maps each role
to a model name, so switching a model never touches agent code.
"""
import json
import re
from functools import lru_cache

from openai import OpenAI

from . import config


@lru_cache(maxsize=1)
def client() -> OpenAI:
    """One OpenAI-compatible client for whichever provider config.py selected."""
    return OpenAI(base_url=config.LLM_BASE_URL, api_key=config.API_KEY)


def extract_json(text: str) -> dict:
    """Parse a JSON object, tolerating code fences or chatter around it (smaller models do this)."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON object in model output: {text[:200]!r}")
        return json.loads(match.group(0))


def _messages(system: str, user: str) -> list[dict]:
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def chat_json(role: str, system: str, user: str, temperature: float = 0.8) -> dict:
    """Ask `role`'s model for a JSON object."""
    resp = client().chat.completions.create(
        model=config.MODELS[role], messages=_messages(system, user),
        response_format={"type": "json_object"}, temperature=temperature,
    )
    return extract_json(resp.choices[0].message.content)


def chat(role: str, system: str, user: str, temperature: float = 0.95) -> str:
    """Ask `role`'s model for plain text."""
    resp = client().chat.completions.create(
        model=config.MODELS[role], messages=_messages(system, user), temperature=temperature,
    )
    return (resp.choices[0].message.content or "").strip()
