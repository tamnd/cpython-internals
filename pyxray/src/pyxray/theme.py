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
#: The boundary of a control: the edge of a button, the edge of a box you can type in.
#: A separate value from LINE because the two have different jobs. A rule under a column
#: heading is decoration and can be faint. The edge of a button is the only thing telling
#: somebody there is a button there, and WCAG asks for 3:1 against whatever is behind it.
#: LINE is 1.5:1 against white, which is right for a rule and not enough for a button.
#: This one is 3.3:1 against white and 5.2:1 against the dark page, so it does both themes
#: without a second value.
EDGE = "#868e96"
PAPER = "#ffffff"

#: The same four neutrals for a dark page. Only the neutrals move between themes. The six
#: tones below keep their colours, because they are pale fills with dark text on them and a
#: chip carries its own background wherever it is put. Giving them a second set of values
#: would mean a second palette to keep in step with the diagrams, and an SVG committed to a
#: repository has one set of colours in it.
DARK_INK = "#e9ecef"
DARK_MUTED = "#adb5bd"
DARK_LINE = "#495057"
DARK_PAPER = "#1a1b1e"


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

    @property
    def text(self) -> str:
        """The colour to put words in when they sit on this tone's fill.

        It is INK for every tone, and it is a method rather than a constant because the
        answer is not obvious and the reason is worth having somewhere. The tempting choice
        is the stroke, since that is the tone's dark colour and it looks tidy. Measured, it
        is between 2.7:1 and 3.8:1 against its own fill on five of the six tones, where
        readable text needs 4.5:1. Getting there would mean strokes close to black, which
        would leave the diagrams drawing six lines you cannot tell apart.

        So the tone carries meaning through the fill and the border, and the words on top
        of it are INK, which is 10:1 or better on all six. The Excalidraw diagrams have
        always done this, because bound text in a box takes the default stroke colour. This
        makes the widgets agree with them instead of quietly disagreeing.
        """
        return INK


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


#: What WCAG AA asks for. Ordinary text needs the first number against whatever is behind
#: it. Large text, and the boundary of a control, need the second. These are here rather
#: than in the test so the numbers and the palette live in the same file, and so anything
#: else that wants to check a colour is checking against the same bar.
BODY_TEXT = 4.5
LARGE_TEXT = 3.0


def luminance(colour: str) -> float:
    """How bright a hex colour is, on the scale WCAG measures contrast on.

    Not the same as how bright it looks on a monitor. The channel values coming out of a
    hex string are gamma encoded, so each one gets straightened out first, and then the
    three are weighted, because the eye gets most of its brightness from green and very
    little from blue.
    """
    text = colour.lstrip("#")
    if len(text) != 6:
        raise ValueError(f"expected a six digit hex colour, got {colour!r}")
    channels = []
    for start in (0, 2, 4):
        value = int(text[start : start + 2], 16) / 255
        channels.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast(one: str, other: str) -> float:
    """The contrast ratio between two colours, between 1 and 21.

    Order does not matter. Black on white and white on black are the same number, which is
    why this sorts the two brightnesses rather than trusting the caller to pass a
    foreground first.
    """
    bright, dim = sorted((luminance(one), luminance(other)), reverse=True)
    return (bright + 0.05) / (dim + 0.05)
