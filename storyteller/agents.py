"""The model-backed steps. Each is one small function: build a prompt (prompts.py), call a model (llm.py), tidy the result.

  is_allowed  Safety    request / typed action -> bool
  plan        Planner   request                -> StorySession holding the story bible
  narrate     Narrator  session + action       -> one scene of prose (or a rewrite of a rejected draft)
  critique    Critic    session + draft        -> {score, coherent, issues, fix}
  direct      Director  session + scene        -> {mood, choices}

They share state only through StorySession (story.py). How narrate and critique are chained is in pipeline.py.
"""
from . import config, llm, prompts
from .story import MOODS, StorySession

REFUSAL = "I can't weave a story around that. Try another idea - a mystery, a voyage, a strange city?"


def is_allowed(text: str) -> bool:
    """OpenAI's free moderation endpoint when the provider is OpenAI, otherwise (or if it errors) an LLM yes/no judge."""
    if config.LLM_PROVIDER == "openai":
        try:
            return not llm.client().moderations.create(model="omni-moderation-latest", input=text).results[0].flagged
        except Exception:
            pass
    return bool(llm.chat("safety", prompts.SAFETY_SYSTEM, text, temperature=0, as_json=True).get("allowed", False))


def plan(topic: str) -> StorySession:
    bible = llm.chat("planner", prompts.planner_system(), prompts.planner_user(topic), as_json=True)
    return StorySession(topic=topic, bible=bible)


def narrate(session: StorySession, choice: str, draft: str = "", notes: str = "") -> str:
    """Write the next scene. Pass the rejected `draft` and the critic's `notes` to rewrite instead."""
    return llm.chat("narrator", prompts.narrator_system(session.is_last),
                    prompts.narrator_user(session, choice, draft, notes), temperature=0.95)


def critique(session: StorySession, scene_text: str, choice: str) -> dict:
    """Returns {score: 1-10, coherent, issues, fix}. Raises if the critic call itself fails."""
    out = llm.chat("critic", prompts.critic_system(session.is_last),
                   prompts.critic_user(session, scene_text, choice), temperature=0.2, as_json=True)
    return {
        "score": int(out.get("score", 0)),
        "coherent": out.get("coherent") is True,  # bool("false") is True, so accept only a real JSON true
        "issues": [str(i) for i in out.get("issues", [])],
        "fix": str(out.get("fix", "")),
    }


def direct(session: StorySession, scene_text: str) -> dict:
    """Returns {mood, choices}. The final scene gets no choices - the story is over."""
    out = llm.chat("director", prompts.director_system(), prompts.director_user(session, scene_text),
                   temperature=0.6, as_json=True)
    return {
        "mood": out.get("mood") if out.get("mood") in MOODS else "mystery",
        "choices": [] if session.is_last else [str(c) for c in out.get("choices", [])][:3],
    }
