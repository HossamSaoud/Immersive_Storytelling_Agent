"""All settings, read from environment variables (.env). No secrets in code.

HOW TO SWITCH MODELS (edit .env only, no code):
  1. Pick a provider:           LLM_PROVIDER=groq        (openai | groq | huggingface | ollama)
  2. Optionally pick a model:   STORY_MODEL=openai/gpt-oss-120b      (used by every agent)
  3. Optionally give one agent its own model, e.g. a stronger editor:  CRITIC_MODEL=...
     Per-agent settings: PLANNER_MODEL, NARRATOR_MODEL, CRITIC_MODEL, DIRECTOR_MODEL, SAFETY_MODEL
Any other OpenAI-compatible server works too: set LLM_BASE_URL (and OPENAI_API_KEY) and leave LLM_PROVIDER alone.
"""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Provider:
    base_url: str | None   # None = the official OpenAI endpoint
    key_env: str | None    # name of the env var holding this provider's API key (None = no key needed)
    model: str             # default model if STORY_MODEL is not set


PROVIDERS = {
    "openai": Provider(None, "OPENAI_API_KEY", "gpt-4o-mini"),
    "groq": Provider("https://api.groq.com/openai/v1", "GROQ_API_KEY", "openai/gpt-oss-120b"),
    "huggingface": Provider("https://router.huggingface.co/v1", "HF_API_KEY", "google/gemma-4-31B-it"),
    "ollama": Provider("http://localhost:11434/v1", None, "llama3.2"),
}

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
if LLM_PROVIDER not in PROVIDERS:
    raise ValueError(f"LLM_PROVIDER={LLM_PROVIDER!r} is not one of {sorted(PROVIDERS)}")
_provider = PROVIDERS[LLM_PROVIDER]

LLM_BASE_URL = os.getenv("LLM_BASE_URL") or _provider.base_url
API_KEY = (os.getenv(_provider.key_env) if _provider.key_env else None) or os.getenv("OPENAI_API_KEY") or "local"

# One model per agent. Everything falls back to STORY_MODEL, which falls back to the provider's default.
STORY_MODEL = os.getenv("STORY_MODEL") or _provider.model
MODELS = {role: os.getenv(f"{role.upper()}_MODEL") or STORY_MODEL
          for role in ("planner", "narrator", "critic", "director", "safety")}

# Story shape and quality gate
MAX_SCENES = int(os.getenv("MAX_SCENES", "5"))
MAX_REVISIONS = int(os.getenv("MAX_REVISIONS", "2"))  # rewrites the critic may demand per scene
CRITIC_MIN_SCORE = int(os.getenv("CRITIC_MIN_SCORE", "8"))  # 1-10; a scene must reach this to be shown
