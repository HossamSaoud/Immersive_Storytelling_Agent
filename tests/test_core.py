"""Network-free tests: model calls are replaced with fakes, so these check OUR logic, not a model's output."""
import importlib

import pytest

from storyteller import agents, config, llm, pipeline
from storyteller.llm import extract_json
from storyteller.render import render
from storyteller.story import StorySession


@pytest.fixture
def story(monkeypatch):
    """A 3-scene story with the standard quality gate (pass = coherent and score >= 8, up to 2 rewrites)."""
    for name, value in (("MAX_SCENES", 3), ("MAX_REVISIONS", 2), ("CRITIC_MIN_SCORE", 8)):
        monkeypatch.setattr(config, name, value)
    monkeypatch.setattr(agents, "direct", lambda *a, **k: {"mood": "calm", "choices": []})
    return StorySession("t", {"title": "T", "arc": ["a", "b", "c"]})


def run_scene(monkeypatch, story, drafts, verdicts):
    """Feed the pipeline fake drafts and critic verdicts (a verdict that is an Exception is raised)."""
    drafts, verdicts = iter(drafts), iter(verdicts)

    def critique(*a, **k):
        v = next(verdicts)
        if isinstance(v, Exception):
            raise v
        return {"score": v[0], "coherent": v[1], "issues": ["x"], "fix": "f"}

    monkeypatch.setattr(agents, "narrate", lambda *a, **k: next(drafts))
    monkeypatch.setattr(agents, "critique", critique)
    *statuses, (text, _, review) = pipeline.write_scene(story, "")
    return statuses, text, review


def test_extract_json_handles_fences():
    assert extract_json('Sure!\n```json\n{"a": 1}\n```') == {"a": 1}


def test_session_tracks_last_scene_mood_and_choices(story):
    assert not story.is_last and story.mood == "mystery"
    story.add_scene("x", {"mood": "danger", "choices": ["a", "b"]}, "")
    story.add_scene("y", {"mood": "calm", "choices": ["c"]}, "a")
    assert story.is_last and story.mood == "calm" and story.choices == ["c"]


def test_render_escapes_html_and_shows_mood_name_and_prologue():
    s = StorySession("t", {"title": "T", "protagonist_name": "Mara <b>", "prologue": "You are in <i>Brinehaven</i>."})
    s.add_scene("<script>alert(1)</script>", {"mood": "danger", "choices": []}, "")
    html = render(s)
    assert "mood-danger" in html and "chatting with Mara &lt;b&gt;" in html and "Prologue" in html
    assert "<script>" not in html and "<i>" not in html


def test_critic_rejects_then_approves(monkeypatch, story):
    statuses, text, review = run_scene(monkeypatch, story, ["weak", "better"], [(4, False), (9, True)])
    assert text == "better" and "approved" in review and any("Rewriting" in x for x in statuses)


def test_critic_gives_up_and_keeps_best_draft(monkeypatch, story):
    _, text, review = run_scene(monkeypatch, story, ["d1", "d2", "d3"], [(5, True), (7, True), (6, True)])
    assert text == "d2" and "Best of 3" in review  # stops after MAX_REVISIONS rewrites


def test_incoherent_draft_ranks_below_a_plainer_coherent_one(monkeypatch, story):
    _, text, _ = run_scene(monkeypatch, story, ["flowery", "plain", "meh"], [(9, False), (7, True), (5, True)])
    assert text == "plain"


def test_broken_critic_does_not_break_story(monkeypatch, story):
    _, text, review = run_scene(monkeypatch, story, ["draft"], [RuntimeError("down")])
    assert text == "draft" and review == "Critic unavailable"


def test_critic_incoherent_string_is_not_coherent(monkeypatch, story):
    monkeypatch.setattr(llm, "chat", lambda *a, **k: {"score": 9, "coherent": "false"})
    assert agents.critique(story, "text", "")["coherent"] is False


def test_provider_and_per_agent_model_switching(monkeypatch):
    for k in ("LLM_BASE_URL", "STORY_MODEL", "CRITIC_MODEL"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: None)  # ignore the developer's own .env
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("CRITIC_MODEL", "big-model")
    cfg = importlib.reload(config)
    try:
        assert cfg.LLM_BASE_URL == "https://api.groq.com/openai/v1" and cfg.API_KEY == "gsk_test"
        assert cfg.MODELS["critic"] == "big-model" and cfg.MODELS["narrator"] == "openai/gpt-oss-120b"
    finally:
        monkeypatch.undo()
        importlib.reload(config)


def test_first_turn_plans_story_and_commits_scene(monkeypatch, story):
    import app
    scene = ("Scene one.", {"mood": "tense", "choices": ["a", "b"]}, "ok")
    monkeypatch.setattr(agents, "is_allowed", lambda t: True)
    monkeypatch.setattr(agents, "plan", lambda t: story)
    monkeypatch.setattr(pipeline, "write_scene", lambda s, c: iter(["working", scene]))
    *_, last = app.take_turn(None, "a fox")
    assert last[0] is story and story.mood == "tense" and story.choices == ["a", "b"] and last[3]["visible"]


def test_failed_turn_keeps_session_and_choices_for_retry(monkeypatch, story):
    import app
    story.choices = ["go"]
    monkeypatch.setattr(agents, "is_allowed", lambda t: True)
    monkeypatch.setattr(pipeline, "write_scene", lambda s, c: (_ for _ in ()).throw(RuntimeError("down")))
    *_, last = app.take_turn(story, "go")
    assert last[0] is story and not story.scenes and last[3]["visible"] and "problem" in last[2]


def test_paint_returns_svg_data_uri_or_nothing(monkeypatch, story):
    monkeypatch.setattr(llm, "chat", lambda *a, **k: "Here:\n<svg viewBox='0 0 1 1'></svg>")
    assert agents.paint(story, "x").startswith("data:image/svg+xml;base64,")
    monkeypatch.setattr(llm, "chat", lambda *a, **k: "sorry, no")
    assert agents.paint(story, "x") == ""


def test_render_shows_what_the_agents_did(story):
    story.trace += ["critic (m): 5 tokens in, 2 out", "<b>x</b>"]
    html = render(story)
    assert "Behind the scenes" in html and "critic (m): 5 tokens in" in html and "<b>x</b>" not in html
