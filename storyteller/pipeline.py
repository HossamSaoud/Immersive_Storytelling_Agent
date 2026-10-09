"""How one scene gets made: the narrator <-> critic loop. This is the heart of the app's quality control.

    narrator drafts -> critic scores it -> good enough? -- yes --> director adds mood + choices -> shown to the player
                                              |
                                              no -> narrator rewrites using the critic's notes (up to MAX_REVISIONS times)

The player never sees a rejected draft. If no draft passes, the highest-scoring one is used. If the critic itself
errors out, the current draft is used - a broken reviewer must not break the story.
"""
from typing import Generator

from . import agents, config

# What write_scene() hands back once finished: the scene text, the director's {mood, choices}, a one-line verdict.
SceneResult = tuple[str, dict, str]

INCOHERENCE_PENALTY = 3  # a draft the critic calls incoherent ranks as if it scored this much lower


def _passes(verdict: dict) -> bool:
    return verdict["coherent"] and verdict["score"] >= config.CRITIC_MIN_SCORE


def _notes_for_rewrite(verdict: dict) -> str:
    return "\n".join(f"- {issue}" for issue in verdict["issues"]) + f"\n{verdict['fix']}"


def write_scene(session, choice: str) -> Generator[str, None, SceneResult]:
    """Run the loop. Yields human-readable status lines for the UI; the generator's return value is a SceneResult."""
    yield "The narrator is writing..."
    draft = agents.narrate(session, choice)

    best_text, best_rank, verdict = draft, -1, None
    for draft_no in range(1, config.MAX_REVISIONS + 2):  # the first draft plus up to MAX_REVISIONS rewrites
        yield f"The critic is reviewing draft {draft_no}..."
        try:
            verdict = agents.critique(session, draft, choice)
        except Exception as e:  # broken critic: ship the draft rather than fail the turn
            print(f"[critic] review failed: {e}")
            best_text, verdict = draft, None
            break

        rank = verdict["score"] - (0 if verdict["coherent"] else INCOHERENCE_PENALTY)
        if rank > best_rank:
            best_text, best_rank = draft, rank
        if _passes(verdict):
            best_text = draft
            break
        if draft_no > config.MAX_REVISIONS:
            break  # out of rewrites: keep the best draft seen
        yield f"The critic wants changes (score {verdict['score']}/10). Rewriting..."
        draft = agents.narrate(session, choice, draft=draft, notes=_notes_for_rewrite(verdict))

    yield "Setting the stage..."
    direction = agents.direct(session, best_text)
    return best_text, direction, _summary(verdict, best_rank, draft_no)


def _summary(verdict: dict | None, best_rank: int, drafts: int) -> str:
    plural = "s" if drafts > 1 else ""
    if verdict is None:
        return "Critic unavailable"
    if best_rank >= config.CRITIC_MIN_SCORE:
        return f"Critic-approved: {best_rank}/10 after {drafts} draft{plural}"
    return f"Best of {drafts} draft{plural} (critic score {max(best_rank, 0)}/10)"
