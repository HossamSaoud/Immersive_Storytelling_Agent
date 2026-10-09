"""Gradio front end - the only file that knows about the web UI. Run: python app.py

Flow per click:  start()/choose()  ->  safety check  ->  play()  ->  pipeline.write_scene()  (narrator <-> critic loop)
Each yield below re-renders the page, which is how the status lines ("The critic is reviewing...") appear live.
"""
import gradio as gr

from storyteller import agents, config, pipeline, safety
from storyteller.render import CSS, render

EXAMPLES = [
    "An unexpected journey through a futuristic city",
    "A lighthouse keeper who receives a letter from the sea",
    "A heist in a library that rearranges itself at night",
]


def out(session, stage, status="", choices=()):
    buttons = [gr.update(value=choices[i], visible=True) if i < len(choices) else gr.update(visible=False) for i in range(3)]
    return (session, stage, status, *buttons, gr.update(visible=bool(choices)))


def explain(e: Exception) -> str:
    """A player-readable reason for a failed model call."""
    if config.API_KEY == "local" and config.LLM_PROVIDER != "ollama":
        return f"No API key found for provider '{config.LLM_PROVIDER}'. Add it to .env and restart the app."
    if getattr(e, "status_code", None) == 429:
        return "The model provider's rate limit was reached (free tiers have daily token caps). Wait a while, or switch provider or model in .env, then try again."
    return f"The storyteller hit a problem ({type(e).__name__}: {str(e)[:160]}). Please try again."


def play(session, choice):
    """One turn: narrator drafts, critic reviews (and sends back weak drafts), then the approved scene is shown."""
    writer = pipeline.write_scene(session, choice)
    while True:
        try:
            status = next(writer)
        except StopIteration as done:
            text, direction, review = done.value
            break
        yield out(session, render(session, "...", session.mood), status)
    agents.commit(session, text, direction, choice)  # mood change re-tints the stage here
    choices = direction["choices"]
    status = f"*{review}*"
    if session.is_last and not choices:
        status += "  \nThe end. Start a new story above."
    yield out(session, render(session), status, choices)


def start(topic):
    topic = (topic or "").strip()
    if not topic:
        yield out(None, render(None), "Give me a topic first.")
        return
    try:
        if not safety.is_allowed(topic):
            yield out(None, render(None), safety.REFUSAL)
            return
        yield out(None, render(None), "Weaving your world...")
        session = agents.plan(topic)
        yield from play(session, "")
    except Exception as e:
        print(f"[app] start failed: {e!r}")
        yield out(None, render(None), explain(e))


def choose(session, choice):
    choice = (choice or "").strip()
    if session is None or not choice:
        yield out(session, render(session, "", session.mood if session else "mystery"), choices=session.choices if session else [])
        return
    try:
        if not safety.is_allowed(choice):
            yield out(session, render(session), safety.REFUSAL, session.choices)
            return
        yield from play(session, choice)
    except Exception as e:  # the scene was not committed, so the player can simply retry
        print(f"[app] choose failed: {e!r}")
        yield out(session, render(session), explain(e), session.choices)


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
        btn.click(choose, [session, btn], outputs)
    free.submit(choose, [session, free], outputs).then(lambda: "", None, free)

if __name__ == "__main__":
    demo.queue().launch(inbrowser=True)
