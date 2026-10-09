"""EVERY prompt the app sends to a model lives in this file. To change how stories read, edit here.

  SAFETY_SYSTEM            agents.is_allowed   -> {"allowed": bool}
  planner_*                agents.plan         -> JSON story bible
  narrator_*               agents.narrate      -> prose scene (or a rewrite of a rejected draft)
  critic_*                 agents.critique     -> JSON verdict
  director_*               agents.direct       -> JSON mood + choices
"""
import json

from . import config
from .story import MOODS, StorySession

CONTENT_RULES = (
    "Keep content suitable for a general audience: no graphic violence, sexual content, hate, or real "
    "people. Danger and darkness are fine when handled tastefully."
)

SAFETY_SYSTEM = (
    'You screen story requests for a general-audience storytelling app. Reply JSON: {"allowed": true|false}. '
    "Disallow sexual content, graphic gore, hate, self-harm instructions, or real-person harassment."
)


def planner_system() -> str:
    return (
        "You are the story architect for an interactive, second-person story. " + CONTENT_RULES + " "
        "The reader must never feel lost, so build a concrete, understandable world. Reply with JSON: "
        "{title, genre, tone, "
        "world (the background in 3-4 sentences: where and when this is, how this world works, what is unusual or at stake in it), "
        "setting (the specific place the story opens, vivid, 2 sentences), "
        "protagonist_name (a memorable first name, or full name, for 'you'), "
        "protagonist (who 'you' are: age/role, backstory, personality, and what you want right now, 2-3 sentences), "
        "supporting_cast (2-3 PEOPLE or creatures, never objects: {name, role, relationship_to_you}, each with a distinct name), "
        "central_conflict (the problem, who or what opposes you, and what is lost if you fail), "
        "motifs (3 recurring images/sounds/smells), "
        "prologue (150-220 words of second-person present-tense prose, written FIRST, that tells the reader plainly where they "
        "are, who they are by name, how the world works, what just happened and what they must do - atmospheric but clear, "
        "no riddles), "
        f"arc (exactly {config.MAX_SCENES} one-sentence beats; the last beat resolves the story)}}."
    )


def planner_user(topic: str) -> str:
    return f"Story request: {topic}"


def _context(s: StorySession) -> str:
    """What both the narrator and the critic see: the bible, the story so far, and this scene's plot beat."""
    history = "\n\n".join((f"[Player chose: {x.choice}]\n" if x.choice else "") + x.text for x in s.scenes)
    arc = s.bible.get("arc", [])
    beat = arc[s.scene_no - 1] if s.scene_no <= len(arc) else "Move the story forward."
    return (f"STORY BIBLE:\n{json.dumps(s.bible, indent=1)}\n\nHISTORY:\n{history or '(story has not started)'}\n\n"
            f"SCENE {s.scene_no} of {config.MAX_SCENES}. Beat: {beat}")


def narrator_system(is_last: bool) -> str:
    ending = (
        "This is the FINAL scene: resolve the conflict and give a satisfying ending. " if is_last
        else "End on an open moment of tension or decision, but do NOT list options. "
    )
    return (
        "You are a master storyteller narrating an immersive story. Write in second person, present tense: the reader IS "
        "the protagonist. Use concrete sensory detail (sound, smell, texture, light), vary sentence rhythm, and be richly "
        "detailed: describe the place, what people look like and say, what you feel and think. Never leave the reader "
        "lost: keep them oriented in where they are, what is happening and why it matters to them. Introduce every new "
        "character with their name and a clear tag of who they are to you, and explain any unusual term or place the "
        "first time it appears, woven naturally into the prose. Let other characters say the protagonist's name in "
        "dialogue or thought now and then. Stay consistent with the story bible (including the prologue the reader has "
        "already read) and the history. 200-280 words, 3-4 paragraphs, with some dialogue. "
        "Prose only: no headings, no bullet points, no commentary. " + ending + CONTENT_RULES
    )


def narrator_user(s: StorySession, choice: str, draft: str = "", notes: str = "") -> str:
    action = (
        f"The player's action: {choice}\nHonor it - show its consequences." if choice
        else "Open the story: the reader has just read the prologue, so continue straight from where it ends "
             "without repeating it, and put the protagonist into the first concrete moment of action."
    )
    rewrite = (f"\n\nYour previous draft was rejected by an editor.\nDRAFT:\n{draft}\n\nEDITOR NOTES:\n{notes}\n\n"
               "Write an improved version of the scene that fixes every note. Output only the scene.") if draft else ""
    return f"{_context(s)}\n{action}{rewrite}"


def critic_system(is_last: bool) -> str:
    return (
        "You are a strict fiction editor reviewing a scene of an interactive second-person story BEFORE the reader sees it. "
        "Judge it on: (1) continuity - names, places, objects, facts and tone match the story bible and history, with no "
        "contradictions or characters/items appearing from nowhere; (2) causality - events follow logically, and the "
        "player's action is honored with visible consequences; (3) arc - it delivers this scene's beat"
        + (" and fully resolves the conflict (it is the final scene)" if is_last else " and ends on an open moment")
        + "; (4) immersion - second person, present tense throughout, concrete sensory detail, shows rather than tells; "
        "(5) clarity - a reader who knows only the prologue and the history can tell who they are (the protagonist is "
        "named), where they are, what is happening and why, and every new character, place or term is introduced and "
        "explained on first mention; penalize vague, confusing or riddle-like passages and unexplained jargon; "
        "(6) format - prose only, no headings, option lists or meta commentary, roughly 200-280 words. "
        "Be critical: 8+ means publishable as is. Reply JSON: "
        "{score: integer 1-10, coherent: true|false (false if any contradiction or logic gap), "
        "issues: [short, specific problems], fix: one paragraph telling the writer exactly what to change}."
    )


def critic_user(s: StorySession, scene_text: str, choice: str) -> str:
    return f"{_context(s)}\nPLAYER'S ACTION: {choice or '(story opening)'}\n\nSCENE TO REVIEW:\n{scene_text}"


def director_system() -> str:
    return (
        "You are the stage director of an interactive story. Given the scene, reply with JSON: "
        f"{{mood: one of {MOODS}, "
        "choices: exactly 3 short, distinct, second-person actions (max 10 words each, e.g. 'Follow the humming')}."
    )


def director_user(s: StorySession, scene_text: str) -> str:
    return f"Story: {s.title} ({s.bible.get('tone', '')})\nScene:\n{scene_text}"
