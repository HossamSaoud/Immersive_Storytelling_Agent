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
        "You are the story architect for an interactive story told as a live chat: a character in trouble messages the reader, and the reader's replies steer them. " + CONTENT_RULES + " "
        "The reader must never feel lost, so build a concrete, understandable world. Reply with JSON: "
        "{title, genre, tone, "
        "world (the background in 3-4 sentences: where and when this is, how this world works, what is unusual or at stake in it), "
        "setting (the specific place the story opens, vivid, 2 sentences), "
        "protagonist_name (the character who is messaging the reader: a memorable first name), "
        "protagonist (who that character is: age/role, backstory, personality, and what they want right now, 2-3 sentences; the reader is NOT this person), "
        "supporting_cast (2-3 PEOPLE or creatures, never objects: {name, role, relationship_to_you}, each with a distinct name), "
        "central_conflict (the problem, who or what opposes you, and what is lost if you fail), "
        "motifs (3 recurring images/sounds/smells), "
        "prologue (100-150 words addressed to the reader as 'you': why only you can hear this character (a radio, a phone, a "
        "signal), where the character is, what just happened and what is at stake - clear, no riddles), "
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
        else "End on your last message asking the reader what to do, but do NOT list options. "
    )
    return (
        "You write one chunk of a live text chat. You ARE the character (protagonist_name in the bible) messaging the reader, "
        "who is your only contact. Write in first person, present tense, as 5-8 SHORT chat messages (each 1-2 sentences, "
        "natural and a little breathless), separated by a blank line. Total 60-120 words. Tell the reader what you see, "
        "hear and feel and what just happened. Address the reader directly, react to what they told you, and never repeat "
        "the prologue. Introduce any new person or place with a name and a clear tag. Stay consistent with the story bible "
        "and the history. No narration, no stage directions, no headings, no lists, no emoji. " + ending + CONTENT_RULES
    )


def narrator_user(s: StorySession, choice: str, draft: str = "", notes: str = "") -> str:
    action = (
        f'The reader just replied: "{choice}"\nAct on it and show the consequences.' if choice
        else "Open the chat: the reader has just read the prologue. Send your first messages as the character, putting "
             "yourself in the first concrete moment of danger or decision."
    )
    rewrite = (f"\n\nYour previous draft was rejected by an editor.\nDRAFT:\n{draft}\n\nEDITOR NOTES:\n{notes}\n\n"
               "Write an improved version of the scene that fixes every note. Output only the scene.") if draft else ""
    return f"{_context(s)}\n{action}{rewrite}"


def critic_system(is_last: bool) -> str:
    return (
        "You are a strict fiction editor reviewing a chunk of a live-chat story (a character messaging the reader) BEFORE the reader sees it. "
        "Judge it on: (1) continuity - names, places, objects, facts and tone match the story bible and history, with no "
        "contradictions or characters/items appearing from nowhere; (2) causality - events follow logically, and the "
        "reader's reply is honored with visible consequences; (3) arc - it delivers this scene's beat"
        + (" and fully resolves the conflict (it is the final scene)" if is_last else " and ends on an open moment")
        + "; (4) voice - first person from the character, present tense, short natural chat messages, concrete detail; "
        "(5) clarity - a reader who knows only the prologue and the history can tell who is speaking, where they are, what is happening and why, and every new character, place or term is introduced and "
        "explained on first mention; penalize vague, confusing or riddle-like passages and unexplained jargon; "
        "(6) format - 5-8 short messages separated by blank lines, no headings, option lists or narration, roughly 60-120 words. "
        "Be critical: 8+ means publishable as is. Reply JSON: "
        "{score: integer 1-10, coherent: true|false (false if any contradiction or logic gap), "
        "issues: [short, specific problems], fix: one paragraph telling the writer exactly what to change}."
    )


def critic_user(s: StorySession, scene_text: str, choice: str) -> str:
    return f"{_context(s)}\nPLAYER'S ACTION: {choice or '(story opening)'}\n\nSCENE TO REVIEW:\n{scene_text}"


def painter_system() -> str:
    return (
        "You are an illustrator. Reply with ONE self-contained SVG and nothing else: xmlns and viewBox='0 0 800 300', a wide "
        "atmospheric scene built from gradients and simple shapes, no text, no scripts, no external links, under 2500 characters."
    )


def painter_user(s: StorySession, scene_text: str) -> str:
    return f"Story: {s.title} ({s.bible.get('tone', '')}). Mood: {s.mood}.\nIllustrate this scene:\n{scene_text}"


def director_system() -> str:
    return (
        "You are the stage director of an interactive story. Given the scene, reply with JSON: "
        f"{{mood: one of {MOODS}, "
        "choices: exactly 2 short, clearly different replies the reader could send the character (max 8 words each, e.g. 'Go toward the light')}."
    )


def director_user(s: StorySession, scene_text: str) -> str:
    return f"Story: {s.title} ({s.bible.get('tone', '')})\nScene:\n{scene_text}"
