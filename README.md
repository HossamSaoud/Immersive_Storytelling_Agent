# Echoes - an Immersive Storytelling Agent

Type a topic and step inside the story. Echoes writes it in second person, lets you steer it with
choices (or your own words), and **re-tints and animates the whole stage to match each scene's mood**. Every scene is
reviewed by a **critic agent** before you see it, so the story stays coherent.

## Setup & run

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # macOS/Linux: cp .env.example .env   -> then pick a provider and add its key
python app.py                     # opens http://127.0.0.1:7860
python -m pytest                  # optional: run tests
```

## Switching models (edit `.env` only)

| I want | Set in `.env` |
|---|---|
| OpenAI | `LLM_PROVIDER=openai` and `OPENAI_API_KEY=...` |
| Free hosted (Groq) | `LLM_PROVIDER=groq` and `GROQ_API_KEY=...` |
| Hugging Face router | `LLM_PROVIDER=huggingface` and `HF_API_KEY=...` |
| Local (Ollama) | `LLM_PROVIDER=ollama` (after `ollama pull llama3.2`), no key |
| A specific model | `STORY_MODEL=<model name>` (all agents) |
| A different model for one agent | `PLANNER_MODEL`, `NARRATOR_MODEL`, `CRITIC_MODEL`, `DIRECTOR_MODEL` or `SAFETY_MODEL` |
| Any other OpenAI-compatible server | `LLM_BASE_URL=...` and `OPENAI_API_KEY=...` |

Each provider has a sensible default model (see `storyteller/config.py`). Restart the app after changing `.env`.

## Interpretation of "immersive"

A static story is read; an immersive one is *inhabited*. Echoes does that through four layers:
1. **Presence** - second person, present tense, concrete sensory detail: you are the protagonist.
2. **Agency** - three suggested actions per scene plus a free-text box; the narrator must show the consequences of what you did.
3. **Atmosphere** - a director agent labels each scene with a mood (calm, tense, danger, wonder...). The UI's colours and pulse speed change with it (danger pulses fast and red; calm breathes slowly).
4. **Coherence** - a critic agent checks every scene for continuity, cause and effect, and immersion before it is shown; weak drafts are rewritten with the critic's notes.

## Where to look first

```
app.py                  Web UI (Gradio). One click -> take_turn(): safety check -> pipeline -> re-render.
storyteller/
  prompts.py            EVERY prompt the app sends to a model. Edit here to change how stories read.
  agents.py             The model-backed steps, one small function each: is_allowed, plan, narrate, critique, direct
  pipeline.py           How one scene is made: narrator drafts -> critic scores -> rewrite if weak -> director
  story.py              StorySession: the shared memory (story bible, scenes so far, current choices)
  render.py             HTML/CSS stage; the mood class drives colours and animation
  llm.py                The only file that calls a model provider
  config.py             Settings from .env: providers, per-agent models, story length, critic thresholds
tests/                  Network-free tests (parsing, session, HTML escaping, the critic loop, a full UI turn)
ENGINEERING_DECISIONS.md  Why it is built this way, with trade-offs
```

Flow per request: **Safety** -> **Planner** (story bible: world, named protagonist, cast, conflict, prologue, one beat per scene)
-> for each scene: **Narrator** drafts -> **Critic** scores it (1-10, coherent?, issues, fix); below `CRITIC_MIN_SCORE` it goes back
to the narrator with the notes, up to `MAX_REVISIONS` times, and the best draft wins -> **Director** (mood, 3 choices) -> shown.
The story ends after `MAX_SCENES` (default 5); the final beat forces a resolution.

## Design decisions & trade-offs

See **[ENGINEERING_DECISIONS.md](ENGINEERING_DECISIONS.md)** for the full reasoning. In short: separate agents instead of one prompt,
a critic gate so the player never sees an unreviewed scene, all prompts in one file, models as configuration, layered safety, mood-driven CSS
instead of generated media, and no agent framework.

## AI-assisted development

I used Claude Code to scaffold and write the code. The following were my own decisions: the interpretation of immersion (the four layers above),
the planner/narrator/director split, mood-driven UI, the scene limit, the safety layering, and the choice of an OpenAI-compatible abstraction.
I reviewed and tested the generated code (unit tests plus live end-to-end runs against Groq's `openai/gpt-oss-120b`).

## External services, models, libraries

Any OpenAI-compatible provider: OpenAI (`gpt-4o-mini`, `omni-moderation-latest`), Groq (`openai/gpt-oss-120b`), Hugging Face router, or Ollama (Llama 3.2). Libraries: Gradio, openai, python-dotenv, pytest. No third-party assets (fonts: system serif).

## Known limitations / next steps

- Local small models produce blander prose and sometimes weaker JSON; the parser tolerates fences but not all failures.
- Story state is in-browser-session only (no save/resume); the narrator re-reads the full history each scene (fine for 5 scenes, needs summarization for longer ones).
- The critic adds latency (several LLM calls before a scene appears) and can only judge what the model can; it may still pass subtle inconsistencies.
- Next: ambient audio per mood, persistent characters/inventory state, user-selectable genre/length, critic checks across the whole story (not just per scene).

## Demonstration

_Add the link to your screen recording here before submitting._
