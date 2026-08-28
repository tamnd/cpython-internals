"""All the diagrams belonging to one lesson.

A lesson's `diagrams.py` builds a gallery, adds scenes to it, and calls `save`. That is the
whole interface. It takes the same `--check` argument as a lesson builder, so `nbdiagram
check` and a person running the script by hand are doing exactly the same thing rather than
two things that agree most of the time.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

from nbbuild.lesson import repository_root

from .cli import DIRECTORY, write
from .link import RAW
from .scene import Scene


@dataclass
class Gallery:
    """The diagrams for one lesson, and where they belong on disk."""

    slug: str
    root: Path = field(default_factory=repository_root)
    scenes: list[Scene] = field(default_factory=list)

    @property
    def directory(self) -> Path:
        return self.root / "lessons" / self.slug / DIRECTORY

    def add(self, scene: Scene) -> Scene:
        if any(existing.name == scene.name for existing in self.scenes):
            raise ValueError(f"two diagrams in {self.slug} are called {scene.name!r}")
        self.scenes.append(scene)
        return scene

    def image(self, name: str, alt: str) -> str:
        """The markdown for embedding one diagram in a notebook cell.

        Lessons call this rather than writing the URL out, because the URL has a host and a
        branch in it and typing that by hand into forty cells is how half of them end up
        pointing at the wrong lesson.
        """
        if not any(scene.name == name for scene in self.scenes):
            raise KeyError(f"{self.slug} has no diagram called {name!r}")
        return f"![{alt}]({RAW}/lessons/{self.slug}/{DIRECTORY}/{name}.svg)"

    def save(self, argv: list[str] | None = None) -> int:
        arguments = sys.argv[1:] if argv is None else argv
        check = "--check" in arguments
        problems = []
        for scene in self.scenes:
            problems.extend(write(scene, self.directory, check=check))
        for problem in problems:
            print(problem)
        if problems:
            return 1
        verb = "checked" if check else "wrote"
        print(f"{verb} {len(self.scenes)} diagram(s) for {self.slug}")
        return 0
