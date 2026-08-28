"""Pointing a lesson at a diagram that has already been drawn.

A lesson's `build.py` needs the markdown for an image, not the code that draws it. It could
import the `diagrams.py` sitting next to it, but that would redraw every scene and then hit
the `SystemExit` at the bottom of the script, so the link is looked up on disk instead.

That is the better check anyway. It fails when the committed SVG is missing or misnamed,
which is the mistake that actually happens, and it costs nothing at build time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from nbbuild.lesson import repository_root

from .cli import DIRECTORY

#: Where a notebook has to point for a diagram to appear in Colab. Colab has no idea which
#: repository the notebook came from, so a relative path is a broken image for every reader
#: who arrived through the badge. The raw host serves SVG as `image/svg+xml`, so an absolute
#: link to it renders on GitHub and in Colab alike.
RAW = "https://raw.githubusercontent.com/tamnd/cpython-internals/main"


@dataclass
class Diagrams:
    """The diagrams belonging to one lesson, seen from the lesson's side."""

    slug: str
    root: Path = field(default_factory=repository_root)

    @property
    def directory(self) -> Path:
        return self.root / "lessons" / self.slug / DIRECTORY

    def url(self, name: str) -> str:
        return f"{RAW}/lessons/{self.slug}/{DIRECTORY}/{name}.svg"

    def figure(self, name: str, alt: str) -> str:
        """The markdown for one diagram, checked against the file on disk.

        The alt text is not decoration. It is what a screen reader says and what shows up
        when the image does not load, so it should say what the picture shows rather than
        repeat the title.
        """
        if not (self.directory / f"{name}.svg").exists():
            raise KeyError(f"{self.slug} has no diagram called {name!r}")
        return f"![{alt}]({self.url(name)})"
