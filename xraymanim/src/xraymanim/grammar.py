"""The visual grammar for the animations, with no manim in it.

Everything an animation decides before it draws anything lives here: what a colour means,
how big the type is, how far apart two boxes sit, how long a step lasts, and the list of
shapes an animation is allowed to use. None of that needs a renderer, so none of it imports
one. That split is the reason most of this package can be tested in a few milliseconds
without cairo, ffmpeg or a video file.

The colours are not chosen here. They come from `pyxray.theme`, which is also what the
Excalidraw diagrams and the matplotlib charts read, so a box that means "the reader wrote
this" is the same blue in a still picture and in a moving one. What this module adds is the
translation into the units manim thinks in, which are not pixels.
"""

from __future__ import annotations

from dataclasses import dataclass

from pyxray import theme

#: The page. Manim's default is a dark background, and the rest of the project is not, so
#: every scene sets this. A reader who opens a lesson should not have one picture in six
#: invert itself.
PAPER = theme.PAPER
INK = theme.INK
MUTED = theme.MUTED
LINE = theme.LINE


@dataclass(frozen=True)
class Pen:
    """A tone, in the shape manim wants it.

    `pyxray.theme.Tone` carries a stroke and a fill. Manim also needs to be told how opaque
    the fill is, separately from the colour, and the answer is not always 1: a box drawn
    behind other boxes reads better at partial opacity, and an outline with no fill at all
    is how this project draws something that has been freed.
    """

    name: str
    stroke: str
    fill: str
    fill_opacity: float = 1.0

    def kwargs(self) -> dict[str, object]:
        """The keyword arguments for any manim `VMobject` that takes a stroke and a fill."""
        return {
            "stroke_color": self.stroke,
            "fill_color": self.fill,
            "fill_opacity": self.fill_opacity,
            "stroke_width": STROKE,
        }

    def faded(self, opacity: float = 0.35) -> Pen:
        """The same tone, pushed into the background."""
        return Pen(self.name, self.stroke, self.fill, opacity)


def pen(name: str, *, fill_opacity: float = 1.0) -> Pen:
    """The pen for a tone name, which is one of the six roles in `pyxray.theme`."""
    tone = theme.tone(name)
    return Pen(tone.name, tone.stroke, tone.fill, fill_opacity)


def cycle(index: int) -> Pen:
    """The index-th tone, wrapping, for a list whose length is not known in advance."""
    tone = theme.cycle(index)
    return Pen(tone.name, tone.stroke, tone.fill)


#: Type. Manim sizes text in points against a frame eight units tall, so these are not the
#: numbers in `pyxray.theme` even though they are the same three sizes and the same ratio
#: between them. A caption has to be readable on a phone, which is why the smallest size
#: here is proportionally larger than the smallest size in a diagram.
TITLE_SIZE = 34
BODY_SIZE = 26
LABEL_SIZE = 22
CAPTION_SIZE = 20

#: Fonts. Preference order, and the first one actually installed wins. Naming a font that
#: is not there is not an error in Pango, it is a silent substitution, so an animation
#: rendered on a laptop and an animation rendered in CI would quietly differ. Asking for
#: what is present makes that visible instead.
SANS_FAMILIES = ("Nunito", "Helvetica Neue", "Arial", "DejaVu Sans", "Liberation Sans")
MONO_FAMILIES = ("SF Mono", "Menlo", "Consolas", "DejaVu Sans Mono", "Liberation Mono")

#: Geometry, in manim units. The frame is 8 units tall and about 14.2 wide, so a unit is
#: roughly a centimetre on a phone held at arm's length. Everything is a multiple of `UNIT`
#: for the same reason the diagrams snap to a 20 pixel grid: a picture where nothing lines
#: up looks careless even when the reader cannot say why.
UNIT = 0.25
BOX_WIDTH = 2.6
BOX_HEIGHT = 1.0
GAP = 0.5
CORNER = 0.12
STROKE = 2.4

#: How thick an arrow is. The difference is the grammar: a strong arrow is a reference that
#: owns what it points at, a thin one is borrowed. A reader who learns that once can then
#: read a picture they have never seen.
OWNED_STROKE = 4.0
BORROWED_STROKE = 2.0

#: Timing. A beat is one step of the thing being explained. Hold is the pause after
#: something has changed, which is the part everybody cuts and everybody should not: the
#: reader needs time to look at the new state before it moves again.
BEAT = 0.8
HOLD = 1.2
FADE = 0.4

#: The hard limit on one animation, in seconds. Ninety seconds is not a style preference.
#: It is the length past which somebody watching a concept explained will scrub, and once
#: they scrub they have stopped following the argument. An animation that needs longer is
#: two animations.
CAP_SECONDS = 90.0

#: The nine shapes. An animation may draw these and nothing else, and adding a tenth is an
#: amendment to VISUAL-SYSTEM.md rather than a new function in a scene file. Without that
#: rule the fortieth animation invents its own way of drawing a pointer and the reader has
#: to learn the notation twice.
PRIMITIVES = (
    "box",
    "arrow",
    "slots",
    "column",
    "stream",
    "tree",
    "graph",
    "counter",
    "highlight",
)

#: The six named things, each one built out of the primitives above. These are the nouns of
#: CPython that come up often enough to be worth a name rather than a recipe.
MOBJECTS = (
    "PyObjectBox",
    "RefArrow",
    "Frame",
    "CodeStrip",
    "DictTable",
    "ArenaMap",
)

#: Both lists together, which is what a storyboard declares against.
SHAPES = PRIMITIVES + MOBJECTS


def mono_font(available: object = None) -> str:
    """The monospace family to ask Pango for, chosen from what is installed.

    `available` is there for the tests, and for the case where manim is not installed at
    all. Passing nothing asks the system. An empty answer means no preferred family was
    found, and an empty string tells manim to use its own default, which is better than
    naming a font that is not there.
    """
    installed = _installed() if available is None else set(available)
    for family in MONO_FAMILIES:
        if family in installed:
            return family
    return ""


def sans_font(available: object = None) -> str:
    """The sans family, chosen the same way as `mono_font`."""
    installed = _installed() if available is None else set(available)
    for family in SANS_FAMILIES:
        if family in installed:
            return family
    return ""


def _installed() -> set[str]:
    """Every font family Pango can see, or nothing at all if manim is not installed."""
    try:
        import manimpango
    except ImportError:
        return set()
    return set(manimpango.list_fonts())
