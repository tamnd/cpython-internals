"""The visual grammar, in one place, for every picture the project makes.

There are going to be three kinds of picture here and they have to look like one project.
Static structure diagrams are Excalidraw scenes rendered to SVG and committed. Live charts
are matplotlib, drawn in the notebook from data the reader's own interpreter just produced.
Animations are manim. Three different tools, three different rendering models, and if each
one picks its own colours the material looks like a pile of blog posts.

So the palette, the type scale, the spacing and the meaning of each colour are decided
here, and all three import it. Nothing downstream is allowed to invent a colour.

The palette is Excalidraw's own, for a practical reason rather than a taste one: the
structure diagrams are real Excalidraw scenes, and a reader who opens one to edit it should
find the colours already on the picker rather than having to eyedrop them.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Stroke and body text. Near black rather than black, which is what every drawing tool
#: worth using picks by default, and it is easier to read against white.
INK = "#1e1e1e"
#: Captions, axis labels, anything the eye should reach second.
MUTED = "#5c5f66"
#: Rules, gridlines, box borders that are not carrying meaning.
LINE = "#ced4da"
PAPER = "#ffffff"


@dataclass(frozen=True)
class Tone:
    """A role, and the colours that stand for it.

    Colour carries meaning in these diagrams: what the reader wrote, what CPython built and
    threw away, what survived. A tone is that role, which is why they are named after the
    job rather than the hue. Renaming `blue` to `input` is the difference between a palette
    and a visual grammar.
    """

    name: str
    stroke: str
    fill: str

    def matplotlib(self) -> dict[str, str]:
        """The same tone as matplotlib keyword arguments, so a chart matches a diagram."""
        return {"edgecolor": self.stroke, "facecolor": self.fill}


TONES: dict[str, Tone] = {
    # What the reader wrote. Everything else in the picture was derived from this.
    "input": Tone("input", "#1971c2", "#a5d8ff"),
    # Something CPython builds and then discards. Most of the pipeline is this.
    "intermediate": Tone("intermediate", "#6741d9", "#d0bfff"),
    # Something that survives: cached, marshalled, written to disk.
    "durable": Tone("durable", "#099268", "#96f2d7"),
    # The stage under discussion. The same picture gets reused across a lesson with the
    # focus moved, which is worth far more than drawing a new picture each time.
    "focus": Tone("focus", "#e8590c", "#ffd8a8"),
    # An error, a refusal, or something that deliberately does not happen.
    "warning": Tone("warning", "#e03131", "#ffc9c9"),
    # Scaffolding: captions, notes, groupings, anything that is not the subject.
    "quiet": Tone("quiet", "#495057", "#e9ecef"),
}

#: The order tones are handed out when something needs several and none of them mean
#: anything in particular, such as the tokens along one line of source.
CYCLE = ["input", "intermediate", "durable", "focus", "warning", "quiet"]


def tone(name: str) -> Tone:
    if name not in TONES:
        raise KeyError(f"unknown tone {name!r}, expected one of {sorted(TONES)}")
    return TONES[name]


def cycle(index: int) -> Tone:
    """The index-th tone, wrapping. For colouring a list whose length is not known."""
    return TONES[CYCLE[index % len(CYCLE)]]


#: Type. Two families and three sizes, which is enough for any diagram worth drawing and
#: few enough that nothing has to be decided twice.
SANS = "Nunito, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, Liberation Mono, monospace"

TITLE_SIZE = 24
BODY_SIZE = 20
CAPTION_SIZE = 16
LINE_HEIGHT = 1.25

#: Spacing. Everything is a multiple of the grid, so a diagram edited by hand in Excalidraw
#: snaps back onto the same rhythm as the generated ones.
GRID = 20
PADDING = 16
GAP = 60

STROKE_WIDTH = 2
CORNER_RADIUS = 12
