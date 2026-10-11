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


def chat(role: str, system: str, user: str, temperature: float = 0.8, as_json: bool = False, max_tokens: int = 2048, trace: list | None = None):
    """Ask `role`'s model. Returns the text, or a dict when as_json=True."""
    claude = config.LLM_PROVIDER == "anthropic"  # its endpoint rejects `temperature` and json_object, and thinks by default; extract_json copes without
    model = config.MODELS[role]
    resp = client().chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=max_tokens,
        **({} if claude else {"temperature": temperature}),
        **({"response_format": {"type": "json_object"}} if as_json and not claude else {}),
        **({"extra_body": {"thinking": {"type": "disabled" if "haiku" in model else "between_tools"}}} if claude else {}),  # Haiku and Sonnet name "no thinking" differently
    )
    if trace is not None and resp.usage:  # the page's "Behind the scenes" list
        trace.append(f"{role} ({model}): {resp.usage.prompt_tokens} tokens in, {resp.usage.completion_tokens} out")
    text = (resp.choices[0].message.content or "").strip()
    return extract_json(text) if as_json else text
