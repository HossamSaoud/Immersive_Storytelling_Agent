"""HTML + CSS for the stage. The mood class on .stage is what makes the atmosphere react to the story."""
import html

from .story import StorySession

# mood -> (gradient colour 1, colour 2, pulse speed in seconds)
_MOODS = {
    "calm": ("#16324f", "#2f6f73", 12), "wonder": ("#2b1a5e", "#1f7a8c", 8), "mystery": ("#1b1b3a", "#4a2b63", 10),
    "tense": ("#2a1a1a", "#5c3a21", 4), "danger": ("#3b0d0d", "#8a1c1c", 1.6), "melancholy": ("#1c2431", "#3d4b5c", 14),
    "joy": ("#5a3a10", "#c9822b", 6), "triumph": ("#4a3a0a", "#d4a82a", 5),
}

CSS = "\n".join(
    f".mood-{m} {{ --c1:{a}; --c2:{b}; --pulse:{s}s; }}" for m, (a, b, s) in _MOODS.items()
) + """
.stage { position:relative; padding:28px 32px; border-radius:16px; min-height:340px; color:#eee9df;
  font-family:Georgia,'Times New Roman',serif; font-size:1.12rem; line-height:1.75; overflow:hidden;
  background:linear-gradient(135deg,var(--c1),var(--c2)); box-shadow:inset 0 0 90px rgba(0,0,0,.55);
  transition:background 1.5s; animation:breathe var(--pulse) ease-in-out infinite; }
.stage::before { content:''; position:absolute; inset:0; pointer-events:none;
  background:radial-gradient(circle at 30% 20%,rgba(255,255,255,.10),transparent 55%); animation:drift calc(var(--pulse)*3) linear infinite; }
.stage h2 { margin:0 0 4px; font-weight:400; letter-spacing:.08em; }
.stage .tag { font:.75rem sans-serif; text-transform:uppercase; letter-spacing:.2em; opacity:.6; margin-bottom:18px; }
.stage p { margin:0 0 1em; position:relative; }
.stage .action { font-style:italic; opacity:.65; margin-bottom:.6em; }
.stage details { opacity:.7; margin-bottom:18px; position:relative; }
.stage .prologue { opacity:.95; padding:14px 18px; margin-bottom:22px; border-left:3px solid rgba(255,255,255,.35);
  background:rgba(0,0,0,.18); border-radius:0 10px 10px 0; position:relative; }
.stage .prologue summary { cursor:pointer; font:.75rem sans-serif; text-transform:uppercase; letter-spacing:.2em; margin-bottom:8px; }
.cursor { display:inline-block; width:.5em; height:1.1em; background:#eee9df; vertical-align:text-bottom; animation:blink 1s steps(2) infinite; }
@keyframes breathe { 50% { filter:brightness(1.18); } }
@keyframes drift { to { transform:translateX(12%) translateY(8%); } }
@keyframes blink { 50% { opacity:0; } }
"""


def _paras(text: str) -> str:
    return "".join(f"<p>{html.escape(p)}</p>" for p in text.split("\n\n") if p.strip())


def render(session: StorySession | None, live: str = "", mood: str = "mystery") -> str:
    if session is None:
        return '<div class="stage mood-mystery"><h2>Echoes</h2><p>Name a world, and step inside.</p></div>'
    # while streaming, every committed scene is history; otherwise the last one is "current"
    history = session.scenes if live else session.scenes[:-1]
    past = "".join((f'<p class="action">&rsaquo; {html.escape(s.choice)}</p>' if s.choice else "") + _paras(s.text) for s in history)
    current = ""
    if live:
        current = _paras(live) + '<span class="cursor"></span>'
    elif session.scenes:
        last = session.scenes[-1]
        current = (f'<p class="action">&rsaquo; {html.escape(last.choice)}</p>' if last.choice else "") + _paras(last.text)
    summary = f"<details><summary>The story so far</summary>{past}</details>" if past else ""
    name = session.bible.get("protagonist_name")
    who = f" &middot; you are {html.escape(str(name))}" if name else ""
    prologue = (f'<details class="prologue"{" open" if len(session.scenes) <= 1 else ""}>'
                f"<summary>Prologue &mdash; the world</summary>{_paras(session.prologue)}</details>") if session.prologue else ""
    return (f'<div class="stage mood-{mood}"><h2>{html.escape(session.title)}</h2><div class="tag">{mood}{who}</div>'
            f"{prologue}{summary}{current}</div>")
