"""Gradio front end - the only file that knows about the web UI. Run: python app.py

One click -> take_turn() -> safety check -> (plan the story on the first turn) -> pipeline.write_scene() (narrator <-> critic).
Each yield re-renders the page, which is how status lines like "The critic is reviewing..." appear live.
"""
import gradio as gr

from storyteller import agents, config, pipeline
from storyteller.render import CSS, render

EXAMPLES = [
    "An unexpected journey through a futuristic city",
    "A lighthouse keeper who receives a letter from the sea",
    "A heist in a library that rearranges itself at night",
]


def out(session, status="", writing=False):
    """One UI update: (state, stage, status, 3 choice buttons, free-text row). The buttons come from session.choices."""
    choices = [] if writing or session is None else session.choices
    buttons = [gr.update(value=choices[i], visible=True) if i < len(choices) else gr.update(visible=False) for i in range(3)]
    return (session, render(session, writing), status, *buttons, gr.update(visible=bool(choices)))


def explain(e: Exception) -> str:
    """A player-readable reason for a failed model call."""
    if config.API_KEY == "local" and config.LLM_PROVIDER != "ollama":
        return f"No API key found for provider '{config.LLM_PROVIDER}'. Add it to .env and restart the app."
    if getattr(e, "status_code", None) == 429:
        return "The model provider's rate limit was reached (free tiers have daily token caps). Wait a while, or switch provider or model in .env, then try again."
    return f"The storyteller hit a problem ({type(e).__name__}: {str(e)[:160]}). Please try again."


def take_turn(session, text):
    """Begin (session None, text = the story request) or continue (text = a chosen or typed action)."""
    text, before = (text or "").strip(), session
    if not text:
        yield out(session)
        return
    try:
        if not agents.is_allowed(text):
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


with gr.Blocks(css=CSS, title="Echoes - Immersive Storyteller") as demo:
    gr.Markdown("# Echoes\nAn interactive story that listens, adapts, and changes its atmosphere as you play.")
    session = gr.State(None)
    with gr.Row():
        topic = gr.Textbox(label="Your story request", placeholder=EXAMPLES[0], scale=4)
        begin = gr.Button("Begin", variant="primary", scale=1)
    gr.Examples(EXAMPLES, topic)
    stage = gr.HTML(render(None))
    status = gr.Markdown()
    with gr.Row():
        b = [gr.Button(visible=False) for _ in range(3)]
    with gr.Row(visible=False) as free_row:
        free = gr.Textbox(label="...or do something else", placeholder="Type your own action and press Enter")

    outputs = [session, stage, status, *b, free_row]
    begin.click(start, [topic], outputs)
    topic.submit(start, [topic], outputs)
    for btn in b:
        btn.click(take_turn, [session, btn], outputs)
    free.submit(take_turn, [session, free], outputs).then(lambda: "", None, free)

if __name__ == "__main__":
    demo.queue().launch(inbrowser=True)
