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
.stage .chat { display:flex; flex-direction:column; position:relative; }
.stage .msg { max-width:78%; margin:0 0 8px; padding:9px 14px; border-radius:18px 18px 18px 4px; background:rgba(255,255,255,.14);
  font:1rem/1.45 system-ui,sans-serif; }
.stage .me { margin-left:auto; border-radius:18px 18px 4px 18px; background:#2f7df6; color:#fff; }
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


def _scene(scene) -> str:
    reply = f'<div class="msg me">{html.escape(scene.choice)}</div>' if scene.choice else ""
    return reply + "".join(f'<div class="msg">{html.escape(m)}</div>' for m in scene.text.split("\n\n") if m.strip())


def render(session: StorySession | None, writing: bool = False) -> str:
    """The whole stage. While `writing`, every committed scene is history and a blinking cursor stands in for the next."""
    if session is None:
        return '<div class="stage mood-mystery"><h2>Echoes</h2><p>Name a world, and step inside.</p></div>'
    scenes = session.scenes
    past = "".join(_scene(s) for s in (scenes if writing else scenes[:-1]))
    current = '<div class="msg"><span class="cursor"></span></div>' if writing else (f'<div class="current">{_scene(scenes[-1])}</div>' if scenes else "")
    name = session.bible.get("protagonist_name")
    channel = session.bible.get("channel")
    medium = channel.get("medium") if isinstance(channel, dict) else None
    who = (f" &middot; {html.escape(str(name))}" + (f", via {html.escape(str(medium))}" if medium else "")) if name else ""
    prologue = (f'<details class="prologue"{" open" if len(scenes) <= 1 else ""}>'
                f"<summary>Prologue &mdash; the world</summary>{_paras(session.prologue)}</details>") if session.prologue else ""
    summary = f"<details><summary>Earlier messages</summary><div class=\"chat\">{past}</div></details>" if past else ""
    return (f'<div class="stage mood-{session.mood}" data-mood="{session.mood}" data-sound="{session.sound}"><h2>{html.escape(session.title)}</h2>'
            f'<div class="tag">{session.mood}{who}</div>{prologue}{summary}<div class="chat">{current}</div></div>')
