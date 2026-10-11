"""Plain data for one playthrough. The session is the agents' shared memory."""
from dataclasses import dataclass, field

from . import config

MOODS = ["calm", "wonder", "mystery", "tense", "danger", "melancholy", "joy", "triumph"]


@dataclass
class Scene:
    text: str
    mood: str
    choice: str  # what the player did to get here ("" for the opening scene)
    image: str = ""  # data: URI of the scene's illustration ("" if none)


@dataclass
class StorySession:
    topic: str
    bible: dict  # planner output: title, world, protagonist_name, cast, conflict, prologue, arc (one beat per scene)
    scenes: list[Scene] = field(default_factory=list)
    choices: list[str] = field(default_factory=list)  # buttons offered after the last scene

    @property
    def title(self) -> str:
        return self.bible.get("title", "Untitled")

    @property
    def prologue(self) -> str:
        return str(self.bible.get("prologue", ""))

    @property
    def scene_no(self) -> int:  # 1-based number of the scene about to be written
        return len(self.scenes) + 1

    @property
    def is_last(self) -> bool:
        return self.scene_no >= config.MAX_SCENES

    @property
    def mood(self) -> str:
        return self.scenes[-1].mood if self.scenes else "mystery"

    def add_scene(self, text: str, direction: dict, choice: str, image: str = "") -> None:
        self.scenes.append(Scene(text, direction["mood"], choice, image))
        self.choices = direction["choices"]
