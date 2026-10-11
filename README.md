# Echoes - an Immersive Storytelling Agent

Type a topic and a character in trouble starts messaging you, a bit like the phone game *Lifeline*. You are the only one who can
reach them, and you steer the story by choosing one of two replies. Each story invents its own odd way for the messages to arrive (a diary
that writes back, frost on a window, notes in a card catalogue...). The stage **re-tints to match each scene's mood**, and the
browser plays matching **ambient sound and music**. Every scene is reviewed by a **critic agent** before you see it, so the story stays coherent.

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
| Claude (default: Sonnet plans, writes and judges; Haiku directs and screens) | `LLM_PROVIDER=anthropic`, `CLAUDE_API_KEY=...` (plus `ANTHROPIC_WORKSPACE_ID=...` if the key is not workspace-scoped) |
| Hugging Face router | `LLM_PROVIDER=huggingface` and `HF_API_KEY=...` |
| Local (Ollama) | `LLM_PROVIDER=ollama` (after `ollama pull llama3.2`), no key |
| A specific model | `STORY_MODEL=<model name>` (all agents) |
| A different model for one agent | `PLANNER_MODEL`, `NARRATOR_MODEL`, `CRITIC_MODEL`, `DIRECTOR_MODEL` or `SAFETY_MODEL` |
| Any other OpenAI-compatible server | `LLM_BASE_URL=...` and `OPENAI_API_KEY=...` |

Each provider has a sensible default model (see `storyteller/config.py`). Restart the app after changing `.env`.

## Interpretation of "immersive"

A static story is read; an immersive one is *inhabited*. Echoes does that through four layers:
1. **Presence** - a named character talks to *you* in first person, in short chat messages, through a medium that fits their world.
2. **Agency** - two reply options per scene; the narrator must show the consequences of the one you chose.
3. **Atmosphere** - a director agent labels each scene with a mood (calm, tense, danger, wonder...) and a background ambience (wind, rain, sea, fire...). The UI's colours and pulse speed change with the mood, and the browser plays synthesised music and ambience to match (tense scenes get a low drone and a heartbeat). The *Sound and music* checkbox turns it off.
4. **Coherence** - a critic agent checks every scene for continuity, cause and effect, and immersion before it is shown; weak drafts are rewritten with the critic's notes.

## Where to look first

```
app.py                  Web UI (Gradio). One click -> take_turn(): safety check (first request only) -> pipeline -> re-render.
storyteller/
  prompts.py            EVERY prompt the app sends to a model. Edit here to change how stories read.
  agents.py             The model-backed steps, one small function each: is_allowed, plan, narrate, critique, direct
  pipeline.py           How one scene is made: narrator drafts -> critic scores -> rewrite if weak -> director
  story.py              StorySession: the shared memory (story bible, scenes so far, current choices)
  render.py             HTML/CSS stage (chat bubbles); the mood class drives colours, data-mood / data-sound drive the audio
  audio.js              Web Audio synthesis of the music and ambience (runs in the browser, no files or keys)
  llm.py                The only file that calls a model provider
  config.py             Settings from .env: providers, per-agent models, story length, critic thresholds
tests/                  Network-free tests (parsing, session, HTML escaping, the critic loop, a full UI turn)
ENGINEERING_DECISIONS.md  Why it is built this way, with trade-offs
```

Flow per request: **Safety** -> **Planner** (story bible: world, named protagonist, cast, conflict, message channel, prologue, one beat per scene)
-> for each scene: **Narrator** (the character's 5-8 chat messages) drafts -> **Critic** scores it (1-10, coherent?, issues, fix); below `CRITIC_MIN_SCORE` it goes back
to the narrator with the notes, up to `MAX_REVISIONS` times, and the best draft wins -> **Director** (mood, ambience, 2 reply choices) -> shown.
The story ends after `MAX_SCENES` (default 5); the final beat forces a resolution.

## Design decisions & trade-offs

See **[ENGINEERING_DECISIONS.md](ENGINEERING_DECISIONS.md)** for the full reasoning. In short: separate agents instead of one prompt,
a critic gate so the player never sees an unreviewed scene, all prompts in one file, models as configuration, layered safety, mood-driven CSS and browser-synthesised sound
instead of generated media, and no agent framework.

## AI-assisted development

I used Claude Code to scaffold and write the code. The following were my own decisions: the interpretation of immersion (the four layers above),
the planner/narrator/director split, mood-driven UI, the scene limit, the safety layering, and the choice of an OpenAI-compatible abstraction.
I reviewed and tested the generated code (unit tests plus live end-to-end runs against Groq's `openai/gpt-oss-120b`).

## External services, models, libraries

Any OpenAI-compatible provider: Anthropic Claude (`claude-sonnet-5-5`, `claude-haiku-5-5`), OpenAI (`gpt-4o-mini`, `omni-moderation-latest`), Groq (`openai/gpt-oss-120b`), Hugging Face router, or Ollama (Llama 3.2). Libraries: Gradio, openai, python-dotenv, pytest. Sound uses the browser's Web Audio API. No third-party assets.

## Known limitations / next steps

- Local small models produce blander prose and sometimes weaker JSON; the parser tolerates fences but not all failures.
- Story state is in-browser-session only (no save/resume); the narrator re-reads the full history each scene (fine for 5 scenes, needs summarization for longer ones).
- The critic adds latency (several LLM calls before a scene appears) and can only judge what the model can; it may still pass subtle inconsistencies.
- The music and ambience are synthesised, so they sound artificial, not like recordings. Lifeline's real-time waiting between messages is not implemented.
- Next: recorded audio, persistent characters/inventory state, user-selectable genre/length, critic checks across the whole story (not just per scene).
