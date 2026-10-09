from storyteller import config
from storyteller.llm import extract_json
from storyteller.render import render
from storyteller.story import Scene, StorySession


def test_extract_json_handles_fences():
    assert extract_json('Sure!\n```json\n{"a": 1}\n```') == {"a": 1}


def test_session_last_scene(monkeypatch):
    monkeypatch.setattr(config, "MAX_SCENES", 2)
    s = StorySession("t", {"title": "T"})
    assert not s.is_last
    s.scenes.append(Scene("x", "calm", ""))
    assert s.is_last and s.mood == "calm"


def test_render_escapes_html_and_sets_mood():
    s = StorySession("t", {"title": "T"}, [Scene("<script>alert(1)</script>", "danger", "")])
    html = render(s, mood="danger")
    assert "mood-danger" in html and "<script>" not in html


def _session(monkeypatch, max_scenes=3):  # a 3-scene story with the standard quality gate
    monkeypatch.setattr(config, "MAX_SCENES", max_scenes)
    monkeypatch.setattr(config, "MAX_REVISIONS", 2)
    monkeypatch.setattr(config, "CRITIC_MIN_SCORE", 8)
    return StorySession("t", {"title": "T", "arc": ["a", "b", "c"]})


def _run(gen):
    statuses = []
    while True:
        try:
            statuses.append(next(gen))
        except StopIteration as done:
            return statuses, done.value


def test_critic_rejects_then_approves(monkeypatch):
    from storyteller import agents, pipeline
    s = _session(monkeypatch)
    drafts = iter(["weak", "better"])
    verdicts = iter([{"score": 4, "coherent": False, "issues": ["x"], "fix": "f"},
                     {"score": 9, "coherent": True, "issues": [], "fix": ""}])
    monkeypatch.setattr(agents, "narrate", lambda *a, **k: next(drafts))
    monkeypatch.setattr(agents, "critique", lambda *a, **k: next(verdicts))
    monkeypatch.setattr(agents, "direct", lambda *a, **k: {"mood": "calm", "choices": []})
    statuses, (text, _, review) = _run(pipeline.write_scene(s, ""))
    assert text == "better" and "approved" in review and any("Rewriting" in x for x in statuses)


def test_critic_gives_up_with_best_draft(monkeypatch):
    from storyteller import agents, pipeline
    s = _session(monkeypatch)
    scores = iter([5, 7, 6])
    drafts = iter(["d1", "d2", "d3"])
    monkeypatch.setattr(agents, "narrate", lambda *a, **k: next(drafts))
    monkeypatch.setattr(agents, "critique", lambda *a, **k: {"score": next(scores), "coherent": True, "issues": [], "fix": ""})
    monkeypatch.setattr(agents, "direct", lambda *a, **k: {"mood": "calm", "choices": []})
    _, (text, _, review) = _run(pipeline.write_scene(s, ""))
    assert text == "d2" and "Best of 3" in review  # stops after MAX_REVISIONS and keeps the highest-scoring draft


def test_broken_critic_does_not_break_story(monkeypatch):
    from storyteller import agents, pipeline
    s = _session(monkeypatch)
    monkeypatch.setattr(agents, "narrate", lambda *a, **k: "draft")
    monkeypatch.setattr(agents, "critique", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
    monkeypatch.setattr(agents, "direct", lambda *a, **k: {"mood": "calm", "choices": []})
    _, (text, _, review) = _run(pipeline.write_scene(s, ""))
    assert text == "draft" and review == "Critic unavailable"


def test_render_shows_prologue_and_name():
    s = StorySession("t", {"title": "T", "protagonist_name": "Mara <b>", "prologue": "You are in <i>Brinehaven</i>."}, [])
    html = render(s, "...", "calm")
    assert "you are Mara &lt;b&gt;" in html and "Prologue" in html and "<i>" not in html


def test_provider_and_per_agent_model_switching(monkeypatch):
    import importlib
    for k in ("LLM_BASE_URL", "STORY_MODEL", "CRITIC_MODEL", "GROQ_API_KEY"):
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


def test_critic_incoherent_string_is_not_coherent(monkeypatch):
    from storyteller import agents, llm
    s = StorySession("t", {"title": "T"})
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: {"score": 9, "coherent": "false", "issues": [], "fix": ""})
    assert agents.critique(s, "text", "")["coherent"] is False


def test_commit_remembers_choices_for_retry():
    from storyteller import agents
    s = StorySession("t", {"title": "T"})
    agents.commit(s, "x", {"mood": "calm", "choices": ["a", "b"]}, "")
    assert s.choices == ["a", "b"]
