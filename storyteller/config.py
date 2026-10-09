"""All settings, read from environment variables (.env). No secrets in code.

HOW TO SWITCH MODELS (edit .env only, no code):
  LLM_PROVIDER=groq              openai | groq | huggingface | ollama  (picks endpoint, key variable, default model)
  STORY_MODEL=<name>             one model for every agent
  CRITIC_MODEL=<name>            or give one agent its own: PLANNER_ / NARRATOR_ / CRITIC_ / DIRECTOR_ / SAFETY_MODEL
Any other OpenAI-compatible server: set LLM_BASE_URL (and OPENAI_API_KEY).
"""
import os

from dotenv import load_dotenv

load_dotenv()

PROVIDERS = {  # name: (base URL or None for OpenAI, env var holding the key, default model)
    "openai": (None, "OPENAI_API_KEY", "gpt-4o-mini"),
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "openai/gpt-oss-120b"),
    "huggingface": ("https://router.huggingface.co/v1", "HF_API_KEY", "google/gemma-4-31B-it"),
    "ollama": ("http://localhost:11434/v1", None, "llama3.2"),
}

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
if LLM_PROVIDER not in PROVIDERS:
    raise ValueError(f"LLM_PROVIDER={LLM_PROVIDER!r} is not one of {sorted(PROVIDERS)}")
_base_url, _key_env, _default_model = PROVIDERS[LLM_PROVIDER]

LLM_BASE_URL = os.getenv("LLM_BASE_URL") or _base_url
API_KEY = (_key_env and os.getenv(_key_env)) or os.getenv("OPENAI_API_KEY") or "local"

STORY_MODEL = os.getenv("STORY_MODEL") or _default_model
MODELS = {role: os.getenv(f"{role.upper()}_MODEL") or STORY_MODEL
          for role in ("planner", "narrator", "critic", "director", "safety")}

MAX_SCENES = int(os.getenv("MAX_SCENES", "5"))
MAX_REVISIONS = int(os.getenv("MAX_REVISIONS", "2"))  # rewrites the critic may demand per scene
CRITIC_MIN_SCORE = int(os.getenv("CRITIC_MIN_SCORE", "8"))  # 1-10; a scene needs this to be shown
