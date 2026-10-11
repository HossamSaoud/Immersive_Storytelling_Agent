"""The ONLY file that talks to a model provider. Agents call chat() with a role ("critic"), never a model name;
config.MODELS maps each role to a model, so switching models never touches agent code."""
import json
import re
from functools import lru_cache

from openai import OpenAI

from . import config


@lru_cache(maxsize=1)
def client() -> OpenAI:
    headers = {"anthropic-workspace-id": config.WORKSPACE_ID} if config.WORKSPACE_ID else None
    return OpenAI(base_url=config.LLM_BASE_URL, api_key=config.API_KEY, default_headers=headers)


def extract_json(text: str) -> dict:
    """Parse a JSON object, tolerating code fences or chatter around it (smaller models do this)."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON object in model output: {text[:200]!r}")
        return json.loads(match.group(0))


def chat(role: str, system: str, user: str, temperature: float = 0.8, as_json: bool = False, max_tokens: int = 2048):
    """Ask `role`'s model. Returns the text, or a dict when as_json=True."""
    resp = client().chat.completions.create(
        model=config.MODELS[role],
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=temperature,
        max_tokens=max_tokens,
        **({"response_format": {"type": "json_object"}} if as_json else {}),
    )
    text = (resp.choices[0].message.content or "").strip()
    return extract_json(text) if as_json else text
