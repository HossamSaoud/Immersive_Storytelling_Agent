"""The four story agents. Each is one small function: build a prompt (prompts.py), call a model (llm.py), tidy the result.

  plan       Planner   request              -> StorySession holding the story bible
  narrate    Narrator  session + action     -> one scene of prose (or a rewrite of a rejected draft)
  critique   Critic    session + draft      -> {score, coherent, issues, fix}
  direct     Director  session + scene      -> {mood, choices}

They share state only through StorySession (story.py), so any of them can be swapped or tested on its own.
How they are chained - draft, review, rewrite - is in pipeline.py.
"""
from . import config, llm, prompts
from .story import MOODS, Scene, StorySession


def plan(topic: str) -> StorySession:
    bible = llm.chat_json("planner", prompts.planner_system(config.MAX_SCENES), prompts.planner_user(topic))
    return StorySession(topic=topic, bible=bible)


def narrate(session: StorySession, choice: str, draft: str = "", notes: str = "") -> str:
    """Write the next scene. Pass the rejected `draft` and the critic's `notes` to rewrite instead."""
    return llm.chat(
        "narrator",
        prompts.narrator_system(session.is_last),
        prompts.narrator_user(session, choice, config.MAX_SCENES, draft, notes),
    )


def critique(session: StorySession, scene_text: str, choice: str) -> dict:
    """Returns {score: 1-10, coherent: bool, issues: [str], fix: str}. Raises if the critic call itself fails."""
    out = llm.chat_json(
        "critic",
        prompts.critic_system(session.is_last),
        prompts.critic_user(session, scene_text, choice),
        temperature=0.2,  # reviews should be steady, not creative
    )
    return {
        "score": int(out.get("score", 0)),
        "coherent": out.get("coherent") is True,  # bool("false") is True, so accept only a real JSON true
        "issues": [str(i) for i in out.get("issues", [])],
        "fix": str(out.get("fix", "")),
    }


def direct(session: StorySession, scene_text: str) -> dict:
    """Returns {mood, choices}. The final scene gets no choices - the story is over."""
    out = llm.chat_json(
        "director", prompts.director_system(), prompts.director_user(session, scene_text), temperature=0.6,
    )
    if out.get("mood") not in MOODS:
        out["mood"] = "mystery"
    out["choices"] = [] if session.is_last else [str(c) for c in out.get("choices", [])][:3]
    return out


def commit(session: StorySession, text: str, direction: dict, choice: str) -> None:
    """Add an approved scene to the story's memory."""
    session.scenes.append(Scene(text=text, mood=direction["mood"], choice=choice))
    session.choices = direction["choices"]
