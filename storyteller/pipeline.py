"""How one scene is made: the narrator <-> critic loop, the app's quality gate.

    narrator drafts -> critic scores it -> good enough? -- yes --> director adds mood + choices -> shown to the player
                                              |
                                              no -> narrator rewrites with the critic's notes (up to MAX_REVISIONS times)

The player never sees a rejected draft. If none passes, the highest-scoring draft is used. If the critic itself
errors, the current draft is used: a broken reviewer must not break the story.
"""
from . import agents, config

INCOHERENCE_PENALTY = 3  # a draft the critic calls incoherent ranks this many points below its score


def write_scene(session, choice: str):
    """Yields status lines for the UI, then finally one (scene text, director's {mood, choices}, summary) tuple."""
    yield "The narrator is writing..."
    draft = agents.narrate(session, choice)
    best, best_rank, n = draft, -1, 0
    while True:
        n += 1
        yield f"The critic is reviewing draft {n}..."
        try:
            verdict = agents.critique(session, draft, choice)
        except Exception as e:
            print(f"[critic] review failed: {e}")
            best, verdict = draft, None
            break
        session.trace.append(f"critic verdict on draft {n}: {verdict['score']}/10, " + ("consistent" if verdict["coherent"] else "has a contradiction")
                             + "; notes: " + " | ".join(verdict["issues"][:3]))
        rank = verdict["score"] - (0 if verdict["coherent"] else INCOHERENCE_PENALTY)
        if rank > best_rank:
            best, best_rank = draft, rank
        if (verdict["coherent"] and verdict["score"] >= config.CRITIC_MIN_SCORE) or n > config.MAX_REVISIONS:
            break
        yield f"The critic wants changes (score {verdict['score']}/10). Rewriting..."
        notes = "\n".join(f"- {issue}" for issue in verdict["issues"]) + f"\n{verdict['fix']}"
        draft = agents.narrate(session, choice, draft=draft, notes=notes)

    yield "Setting the stage..."
    drafts = f"{n} draft{'s' * (n > 1)}"
    summary = ("Critic unavailable" if verdict is None
               else f"Critic-approved: {best_rank}/10 after {drafts}" if best_rank >= config.CRITIC_MIN_SCORE
               else f"Best of {drafts} (critic score {max(best_rank, 0)}/10)")
    yield best, agents.direct(session, best), summary
