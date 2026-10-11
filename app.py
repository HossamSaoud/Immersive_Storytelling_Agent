"""Gradio front end - the only file that knows about the web UI. Run: python app.py

One click -> take_turn() -> safety check (first request only) -> (plan the story on the first turn) -> pipeline.write_scene() (narrator <-> critic).
Sound and music are played by storyteller/audio.js in the browser; the page just hands it the mood and ambience.
Each yield re-renders the page, which is how status lines like "The critic is reviewing..." appear live.
"""
from pathlib import Path

import gradio as gr

from storyteller import agents, config, pipeline
from storyteller.render import CSS, render

AUDIO_JS = (Path(__file__).parent / "storyteller" / "audio.js").read_text(encoding="utf-8")
SOUND = "(on) => window.echoes(on)"  # re-reads the stage's mood and ambience after every turn

EXAMPLES = [
    "An astronaut stranded on an alien moon",
    "A lighthouse keeper cut off by a storm and a stranger on the rocks",
    "A night-shift nurse locked in a hospital that is slowly changing",
]


def out(session, status="", writing=False):
    """One UI update: (state, stage, status, 2 reply buttons). The buttons come from session.choices."""
    choices = [] if writing or session is None else session.choices
    buttons = [gr.update(value=choices[i], visible=True) if i < len(choices) else gr.update(visible=False) for i in range(2)]
    return (session, render(session, writing), status, *buttons)


def explain(e: Exception) -> str:
    """A player-readable reason for a failed model call."""
    if config.API_KEY == "local" and config.LLM_PROVIDER != "ollama":
        return f"No API key found for provider '{config.LLM_PROVIDER}'. Add it to .env and restart the app."
    if getattr(e, "status_code", None) == 429:
        return "The model provider's rate limit was reached (free tiers have daily token caps). Wait a while, or switch provider or model in .env, then try again."
    return f"The storyteller hit a problem ({type(e).__name__}). Please try again; the details are in the console."


def take_turn(session, text):
    """Begin (session None, text = the story request) or continue (text = a chosen or typed action)."""
    text, before = (text or "").strip(), session
    if not text:
        yield out(session)
        return
    try:
        if session is None and not agents.is_allowed(text):  # later turns are our own buttons, so only the request is screened
            yield out(session, agents.REFUSAL)
            return
        if session is None:
            yield out(None, "Weaving your world...")
            session, text = agents.plan(text), ""
        for item in pipeline.write_scene(session, text):
            if isinstance(item, str):
                yield out(session, item, writing=True)
            else:
                scene, direction, review = item
        session.add_scene(scene, direction, text)  # the mood change re-tints the stage here
        end = "" if direction["choices"] else "  \nThe end. Start a new story above."
        yield out(session, f"*{review}*{end}")
    except Exception as e:  # nothing was committed, so the player can simply retry
        print(f"[app] turn failed: {e!r}")
        yield out(before, explain(e))


def start(topic):
    yield from take_turn(None, topic)


with gr.Blocks(css=CSS, js=AUDIO_JS, title="Echoes - Immersive Storyteller") as demo:
    gr.Markdown("# Echoes\nA stranger messages you for help. Your replies decide what happens to them.")
    session = gr.State(None)
    sound = gr.Checkbox(True, label="Sound and music (changes with the scene)")
    with gr.Row():
        topic = gr.Textbox(label="Your story request", placeholder=EXAMPLES[0], scale=4)
        begin = gr.Button("Begin", variant="primary", scale=1)
    gr.Examples(EXAMPLES, topic)
    stage = gr.HTML(render(None))
    status = gr.Markdown()
    with gr.Row():
        b = [gr.Button(visible=False) for _ in range(2)]

    outputs = [session, stage, status, *b]
    begin.click(start, [topic], outputs).then(None, sound, None, js=SOUND)
    topic.submit(start, [topic], outputs).then(None, sound, None, js=SOUND)
    sound.change(None, sound, None, js=SOUND)
    for btn in b:
        btn.click(take_turn, [session, btn], outputs).then(None, sound, None, js=SOUND)

if __name__ == "__main__":
    demo.queue().launch(inbrowser=True)
