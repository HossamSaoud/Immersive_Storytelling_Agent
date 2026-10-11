# Engineering decisions

Why the code is shaped the way it is. Each entry: **decision**, **why**, **what it costs**, and where to change it.

## 1. A pipeline of small agents, not one big prompt

A story request goes through five single-purpose steps, each one small function in `storyteller/agents.py`:

| Agent | Input | Output | Why it is separate |
|---|---|---|---|
| Planner | the player's request | JSON "story bible" (world, named protagonist, cast, conflict, message channel, prologue, one plot beat per scene) | Decides the facts *once*, so later scenes can't drift or contradict each other. |
| Narrator | bible + history + player reply | one chunk of 5-8 short chat messages, in the character's voice | The creative step; runs at high temperature. |
| Critic | the draft + the same context | JSON `{score, coherent, issues, fix}` | A model reviewing a finished draft catches contradictions it would not avoid while writing. Runs at low temperature. |
| Director | the approved scene | JSON `{mood, sound, choices}` (two choices) | Cheap structured output the UI needs; keeps the narrator focused on prose. |
| Safety judge (`is_allowed`) | story request | JSON `{allowed}` | See decision 7. |

*Cost:* 3+ model calls per scene (narrator, critic, director, plus rewrites) instead of 1.
*Where:* `agents.py` (the steps), `pipeline.py` (how narrator and critic are chained).

## 2. The story bible is the story's memory

All agents read the same `StorySession` (`story.py`): the bible plus the list of scenes written so far. Agents never
talk to each other directly. This makes each agent testable alone and makes the data flow visible: planner writes
`bible`, narrator reads it, `add_scene()` appends scenes and remembers the choices, critic and director read both.
The bible has a fixed `arc` with one beat per scene, so a 5-scene story always has a beginning, a middle and a real
ending (the last beat must resolve the conflict).
*Cost:* the full history is re-sent every scene. Fine for 5 scenes; longer stories need summarization.

## 3. The player never sees an unreviewed scene (narrator <-> critic loop)

`pipeline.write_scene()`: draft -> critic scores 1-10 and flags incoherence -> if below `CRITIC_MIN_SCORE` (8) or
incoherent, the narrator rewrites using the critic's issues and fix, up to `MAX_REVISIONS` (2) times -> the best draft
is shown. Details that matter:
- An incoherent draft is ranked 3 points lower than its score (`INCOHERENCE_PENALTY`), so a flowery but contradictory
  draft can't beat a plain consistent one.
- If the critic call fails (network, bad JSON), the current draft is shown, unless an earlier draft was already
  scored, in which case that best one is kept. A quality feature must not be able to break the product.
- The loop is a generator. It yields status lines ("The critic is reviewing draft 2...") so the UI is not a blank
  wait, then yields the finished scene as its last item.

*Cost:* latency (no token streaming - a scene appears once approved) and extra calls. Streaming was removed
deliberately: you cannot show text that might be rejected.
*Where:* thresholds in `.env` (`CRITIC_MIN_SCORE`, `MAX_REVISIONS`); criteria in `prompts.py` (`critic_system`).

## 4. Reader orientation is a first-class requirement

Early output was atmospheric but confusing. Fixes, all visible in the code:
- The planner must produce a **world** description, a **named protagonist**, **named supporting cast** and a **prologue**
  that states plainly where/when/who/why. The prologue is shown above the story.
- The narrator must introduce each new character with a name and role, explain unusual terms on first use, and has a
  budget of 80-150 words (the chat format keeps chunks short, so the critic is told a few words of context is enough).
- The critic has a **clarity** criterion that penalizes vague, riddle-like or unexplained passages.
*Cost:* the prologue is not itself reviewed by the critic; a weak one means restarting the story.

## 5. All prompts live in one file (`prompts.py`)

Prompts are the part of the app you most often tune and the part most likely to hide bugs. One file means: one place to
read the app's whole "personality", clean diffs when wording changes, and agent code that is only orchestration. Prompts
are plain functions returning strings (no template engine) so they can be read and unit-tested like any code.

## 6. Models are configuration, not code

`llm.py` is the only file that talks to a provider, and agents call it with a **role** (`"critic"`), never a model
name. `config.py` maps roles to models and providers to endpoints:
- `LLM_PROVIDER=anthropic|openai|groq|huggingface|ollama` picks the endpoint, key variable and default model.
- `STORY_MODEL` sets one model for every agent; `PLANNER_MODEL`, `NARRATOR_MODEL`, `CRITIC_MODEL`, `DIRECTOR_MODEL`,
  `SAFETY_MODEL` override single agents (e.g. a stronger model as critic).
- `LLM_BASE_URL` points at any other OpenAI-compatible server.
- `OPENAI_API_KEY` is used as a fallback key only for the OpenAI provider or when `LLM_BASE_URL` is set. It is never
  sent to Groq, Claude or Hugging Face, so a leftover key cannot leak to the wrong company.
Every supported provider speaks the OpenAI chat API, so there is one client and no per-provider code paths.
*Cost:* only features common to that API are used (chat + JSON mode). Provider-specific features (e.g. image or voice
models) were left out.

## 7. Safety in layers

1. **Safety judge** on the story request the player types. Uses OpenAI's moderation endpoint when the
   provider is OpenAI (free, purpose-built), otherwise an LLM yes/no judge (`SAFETY_SYSTEM`).
2. **Content rules** inside the planner, narrator and director prompts, so unsafe text is also discouraged at generation time.
Later turns are the app's own two buttons (there is no free-text box), so they are not screened again. An earlier
version screened them and the judge sometimes refused harmless buttons. If a model call fails or the request is
refused, the page stays as it was (the last reply buttons come back) so the player can retry.

## 8. JSON from models is parsed defensively

`llm.extract_json()` accepts fenced or chatter-wrapped JSON because smaller models do that, and rejects anything that is
not a JSON object. Then `agents.py` corrects what is slightly wrong instead of crashing:
- the mood must be in `MOODS`; the ambience must be in `SOUNDS` or it becomes silence;
- choices are truncated to 2 and emptied on the final scene; on any other scene, missing or malformed choices are replaced
  by "Keep going" / "Wait and see", so the story never dead-ends early;
- the critic's score may be `8`, `8.5` or `"8/10"` (anything unreadable counts as 0); `issues` and `choices` must be lists.

## 9. Mood drives the interface, not generated media

The director picks a mood from a fixed list (`story.MOODS`) and an ambience from another (`story.SOUNDS`); `render.py` maps the
mood to colours and animation speed with CSS, and `audio.js` synthesises music and ambience in the browser with Web Audio. No extra
model call, no files, no keys. It is instant, free, offline and visibly reactive. The cost is that it sounds synthetic. Voice narration and image generation were built and then
removed: they needed paid or unreliable services and did not improve understanding of the story.

## 10. Plain, dependency-light tooling

Gradio for the UI (generators give live status updates with no JavaScript), the official `openai` SDK for every
provider, `python-dotenv` for configuration, `pytest` for tests. No agent framework: the whole workflow is about 100
lines of ordinary Python in `pipeline.py` and `agents.py`, which is easier to read and debug than a framework graph.

## 11. What the tests cover

`tests/test_core.py` runs without any network: JSON extraction, session logic, HTML escaping, mood/name/prologue rendering, the critic loop
(reject-then-approve, give up and keep the best draft, incoherent-draft ranking, broken critic), the strict `coherent`
flag, provider switching, the director's ambience fallback, the channel shown on the page, messy model output (odd scores,
non-list choices, a JSON array), that the OpenAI key is never sent to another provider, and one UI turn (success, and failure
with the choices restored). Model calls are
replaced with fakes (`monkeypatch`), so the tests check *our* control flow, not a model's output. Output *quality* is
checked by running the app, not by unit tests.

## 12. Secrets

Keys live only in `.env` (git-ignored). `.env.example` is the committed template. Keys are read once in `config.py`.
When a turn fails, the player sees only the error type (`app.explain`); the details go to the console, so a provider's
error text is never shown on the page.

## 13. The story is a chat with a character, through an invented channel

Modelled on the phone game *Lifeline*: a character messages the reader, who steers with two replies. The narrator writes the character in
first person as 5-8 short messages (`narrator_system`); `render.py` shows them as chat bubbles and your reply as a bubble on the right.
The planner also invents a `channel` (diary, frost on a window, notes in a card catalogue...) and gets three random ideas per request
(`prompts.CHANNELS`) so stories do not all start as a radio call. The narrator keeps that medium's voice; the critic checks it.
*Cost:* the medium changes the wording only, not the look of the page. Lifeline's real-time waiting is not implemented.

## 14. Claude is used through its OpenAI-compatible endpoint

With `LLM_PROVIDER=anthropic` the same client is used, with these adjustments in `llm.py` and `config.py`: an optional
`anthropic-workspace-id` header (`ANTHROPIC_WORKSPACE_ID`) for keys that are not workspace-scoped; no `temperature` and no `json_object`
format (the endpoint rejects them, and `extract_json` copes); hidden thinking is turned off because it used up the token cap and cut the JSON
short (Haiku and Sonnet name "off" differently); every call is capped at 2,048 output tokens.
Model choice per job (`config.ROLE_MODELS`): Sonnet plans, writes and judges; Haiku directs and screens. A Haiku critic nitpicked every draft
into a rewrite, so it cost more than a Sonnet critic that approves on the first draft.

## Known limits

- Critic and narrator are the same kind of model by default, so they share blind spots (use `CRITIC_MODEL` to vary).
- Review is per scene; there is no whole-story consistency check at the end.
- State exists only in the browser session (no save/resume).
