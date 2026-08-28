"""An Excalidraw scene, built from Python.

The diagrams in this project are real `.excalidraw` files. That is worth a sentence of
justification, because generating a proprietary looking JSON blob is not obviously better
than writing SVG directly.

It is better for one reason: the committed diagram stays editable. Anybody can drag the
`.excalidraw` onto excalidraw.com, move a box, change a label, and hand it back. A
generated SVG is a dead end, and a diagram nobody can edit is a diagram that never gets
fixed. The Python that produced it is still the source of truth and still what you change
for anything systematic, but the escape hatch exists and costs nothing.

Everything is placed explicitly. There is no auto layout here on purpose: automatic graph
layout is the reason most generated diagrams look generated, and a picture that is going to
be looked at by thousands of people is worth positioning by hand.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from pyxray import theme

#: Excalidraw's font ids. 1 is the hand drawn Excalifont, 2 is Nunito, 3 is a code face.
FONT_HAND = 1
FONT_SANS = 2
FONT_CODE = 3

#: Roughness 0 is Excalidraw's architect mode, which draws clean strokes instead of sketchy
#: ones. Sketchy is charming in one picture and tiring by the fortieth, and it makes a
#: diagram of something exact look like somebody is estimating.
ROUGHNESS = 0

#: Excalidraw stores a version and a nonce per element for its collaborative editing. None
#: of that matters to a generated file, but the fields have to be there, and they have to
#: be the same on every build or `nbdiagram check` would fail at random.
VERSION = 1


def _identifier(*parts: object) -> str:
    """A stable id derived from what the element is, not from when it was made.

    Excalidraw only needs ids to be unique within the file. Deriving them from content
    keeps the output byte identical across builds, which is what lets CI compare a
    committed diagram against a fresh one.
    """
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode()).hexdigest()
    return digest[:20]


def wrap(text: str, width: float, size: int, *, mono: bool = False) -> list[str]:
    """Break a label into lines that fit inside a box of the given width.

    Excalidraw wraps bound text at the container edge, so a generated scene has to wrap the
    same way or the committed SVG and the file opened in the editor disagree about where
    the words go. Wrapping is on whitespace only: breaking `_PyTokenizer_Get` across two
    lines would be worse than letting it stick out.

    Text that already fits comes back untouched. That is not just a shortcut. Wrapping
    normalises runs of spaces, and half the labels in this project are monospaced source
    where the padding is doing the aligning, so a label that fits must never go through it.
    """
    if text_width(text, size, mono=mono) <= width:
        return [text]
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and text_width(candidate, size, mono=mono) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def text_width(text: str, size: int, *, mono: bool = False) -> float:
    """About how wide a string will be, so a box can be sized to fit its label.

    An estimate, because the real answer needs the font, and shipping a font metric table
    to save a few pixels of padding is not a trade worth making. The ratios come from
    Nunito and from a typical monospace face.

    They round up on purpose. Whoever opens the SVG is on whichever sans the browser
    decided to substitute, and if the estimate comes in under the truth then boxes clip
    their labels and the image itself is cut off at the right edge, because the image is
    sized from these numbers too. Guessing high costs a few pixels of air.
    """
    if mono:
        return len(text) * size * 0.60
    narrow = sum(1 for character in text if character in "iIljtfr.,:;'`|!()[]{}")
    wide = sum(1 for character in text if character in "mMwWQ@")
    normal = len(text) - narrow - wide
    return (narrow * 0.375 + normal * 0.60 + wide * 0.96) * size


@dataclass
class Element:
    """One Excalidraw element. Kept as a plain dict so the format stays visible."""

    data: dict

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def box(self) -> tuple[float, float, float, float]:
        return (
            self.data["x"],
            self.data["y"],
            self.data["x"] + self.data["width"],
            self.data["y"] + self.data["height"],
        )

    def centre(self) -> tuple[float, float]:
        left, top, right, bottom = self.box
        return ((left + right) / 2, (top + bottom) / 2)

    def port(self, side: str) -> tuple[float, float]:
        """The point on one edge where an arrow should attach."""
        left, top, right, bottom = self.box
        middle_x, middle_y = self.centre()
        return {
            "left": (left, middle_y),
            "right": (right, middle_y),
            "top": (middle_x, top),
            "bottom": (middle_x, bottom),
        }[side]


@dataclass
class Scene:
    """A whole diagram, and the only thing a lesson's diagram script talks to."""

    name: str
    elements: list[Element] = field(default_factory=list)

    def _add(self, data: dict) -> Element:
        element = Element(data)
        self.elements.append(element)
        return element

    def _base(self, kind: str, x: float, y: float, width: float, height: float, **over) -> dict:
        return {
            "id": _identifier(self.name, kind, x, y, width, height, len(self.elements)),
            "type": kind,
            "x": float(x),
            "y": float(y),
            "width": float(width),
            "height": float(height),
            "angle": 0,
            "strokeColor": theme.INK,
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": theme.STROKE_WIDTH,
            "strokeStyle": "solid",
            "roughness": ROUGHNESS,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "roundness": None,
            "seed": 1,
            "version": VERSION,
            "versionNonce": 1,
            "isDeleted": False,
            "boundElements": [],
            "updated": 1,
            "link": None,
            "locked": False,
            **over,
        }

    def text(
        self,
        content: str,
        x: float,
        y: float,
        *,
        size: int = theme.BODY_SIZE,
        colour: str = theme.INK,
        mono: bool = False,
        align: str = "left",
        exact: bool = False,
    ) -> Element:
        """A free floating line of text. For captions and labels outside a box.

        `exact` pins the drawn width to the estimate. It is for source text that something
        is going to be lined up underneath, where the browser picking a slightly different
        monospace face would put every mark in the wrong place.
        """
        width = text_width(content, size, mono=mono)
        height = size * theme.LINE_HEIGHT
        left = {"left": x, "centre": x - width / 2, "right": x - width}[align]
        return self._add(
            self._base(
                "text",
                left,
                y,
                width,
                height,
                customData={"textLength": width} if exact else None,
                strokeColor=colour,
                text=content,
                originalText=content,
                fontSize=size,
                fontFamily=FONT_CODE if mono else FONT_SANS,
                textAlign="left",
                verticalAlign="top",
                containerId=None,
                lineHeight=theme.LINE_HEIGHT,
                autoResize=True,
            )
        )

    def box(
        self,
        label: str,
        x: float,
        y: float,
        *,
        width: float | None = None,
        height: float = 80,
        tone: str = "quiet",
        mono: bool = False,
        size: int = theme.BODY_SIZE,
        shape: str = "rectangle",
        align: str | None = None,
    ) -> Element:
        """A labelled box, which is most of what any of these diagrams are made of.

        The label is a real Excalidraw bound text element rather than a separate floating
        one, so dragging the box in the editor takes its label with it. Getting that
        binding right is the difference between a scene somebody can edit and a scene that
        falls apart the moment they touch it.

        Monospaced labels are left aligned unless a caller says otherwise. Stack a few
        centred rows of code on top of each other and the columns stop lining up, which
        undoes the only reason to set them in a monospaced face in the first place.
        """
        if align is None:
            align = "left" if mono else "center"
        colours = theme.tone(tone)
        if width is None:
            width = max(text_width(label, size, mono=mono) + 2 * theme.PADDING, 120)
        # A caller who names a width means it, so a label that does not fit gets wrapped
        # rather than silently drawn outside its own box. Boxes then grow downwards to hold
        # however many lines that took.
        lines = wrap(label, width - 2 * theme.PADDING, size, mono=mono)
        label = "\n".join(lines)
        text_height = size * theme.LINE_HEIGHT * len(lines)
        height = max(height, text_height + 2 * theme.PADDING)
        container = self._add(
            self._base(
                shape,
                x,
                y,
                width,
                height,
                strokeColor=colours.stroke,
                backgroundColor=colours.fill,
                roundness={"type": 3} if shape == "rectangle" else None,
            )
        )
        inner = self._add(
            self._base(
                "text",
                x + theme.PADDING,
                y + (height - text_height) / 2,
                width - 2 * theme.PADDING,
                text_height,
                text=label,
                originalText=label,
                fontSize=size,
                fontFamily=FONT_CODE if mono else FONT_SANS,
                textAlign=align,
                verticalAlign="middle",
                containerId=container.id,
                lineHeight=theme.LINE_HEIGHT,
                autoResize=False,
            )
        )
        container.data["boundElements"] = [{"id": inner.id, "type": "text"}]
        return container

    def arrow(
        self,
        start: Element | tuple[float, float],
        end: Element | tuple[float, float],
        *,
        label: str = "",
        colour: str = theme.INK,
        dashed: bool = False,
        sides: tuple[str, str] = ("right", "left"),
    ) -> Element:
        """An arrow between two boxes, or between two bare points.

        Bound to the elements at each end when it is given elements, which again is about
        the file staying editable: an unbound arrow does not follow the box it points at.
        """
        start_point = start.port(sides[0]) if isinstance(start, Element) else start
        end_point = end.port(sides[1]) if isinstance(end, Element) else end
        x0, y0 = start_point
        x1, y1 = end_point
        element = self._add(
            self._base(
                "arrow",
                x0,
                y0,
                x1 - x0,
                y1 - y0,
                strokeColor=colour,
                strokeStyle="dashed" if dashed else "solid",
                points=[[0, 0], [x1 - x0, y1 - y0]],
                lastCommittedPoint=None,
                startBinding=(
                    {"elementId": start.id, "focus": 0, "gap": 4}
                    if isinstance(start, Element)
                    else None
                ),
                endBinding=(
                    {"elementId": end.id, "focus": 0, "gap": 4}
                    if isinstance(end, Element)
                    else None
                ),
                startArrowhead=None,
                endArrowhead="arrow",
                elbowed=False,
            )
        )
        for anchor, key in ((start, "startBinding"), (end, "endBinding")):
            if isinstance(anchor, Element) and element.data[key]:
                anchor.data["boundElements"] = [
                    *anchor.data["boundElements"],
                    {"id": element.id, "type": "arrow"},
                ]
        if label:
            self.text(
                label,
                (x0 + x1) / 2,
                min(y0, y1) - theme.CAPTION_SIZE * theme.LINE_HEIGHT - 6,
                size=theme.CAPTION_SIZE,
                colour=theme.MUTED,
                align="centre",
            )
        return element

    def line(
        self,
        points: list[tuple[float, float]],
        *,
        colour: str = theme.LINE,
        dashed: bool = False,
    ) -> Element:
        """A bare polyline, for rules, brackets and anything that is not pointing at something."""
        x0, y0 = points[0]
        xs = [x for x, _ in points]
        ys = [y for _, y in points]
        return self._add(
            self._base(
                "line",
                x0,
                y0,
                max(xs) - min(xs),
                max(ys) - min(ys),
                strokeColor=colour,
                strokeStyle="dashed" if dashed else "solid",
                points=[[x - x0, y - y0] for x, y in points],
                lastCommittedPoint=None,
            )
        )

    def band(
        self,
        points: list[tuple[float, float]],
        *,
        fill: str,
        colour: str = "transparent",
        opacity: int = 100,
    ) -> Element:
        """A closed, filled shape, for joining one row of a diagram to another.

        Excalidraw calls this a line whose last point returns to its first, which is why it
        shares the line type. It exists for ribbons: a solid shape from a piece of source
        down to the label naming it. Two rows in the same order joined by ribbons can never
        cross, which is not true of leader lines, and a reader follows a shape without
        having to trace it.
        """
        closed = [*points, points[0]]
        x0, y0 = closed[0]
        xs = [x for x, _ in closed]
        ys = [y for _, y in closed]
        return self._add(
            self._base(
                "line",
                x0,
                y0,
                max(xs) - min(xs),
                max(ys) - min(ys),
                strokeColor=colour,
                backgroundColor=fill,
                opacity=opacity,
                points=[[x - x0, y - y0] for x, y in closed],
                lastCommittedPoint=None,
                polygon=True,
            )
        )

    def document(self) -> str:
        """The scene as the exact text that belongs in the `.excalidraw` file."""
        scene = {
            "type": "excalidraw",
            "version": 2,
            "source": "https://github.com/tamnd/cpython-internals",
            "elements": [element.data for element in self.elements],
            "appState": {"gridSize": theme.GRID, "viewBackgroundColor": theme.PAPER},
            "files": {},
        }
        return json.dumps(scene, indent=1) + "\n"

    def bounds(self) -> tuple[float, float, float, float]:
        """The box that contains everything, used to size the rendered SVG."""
        if not self.elements:
            return (0, 0, 0, 0)
        boxes = [element.box for element in self.elements]
        return (
            min(box[0] for box in boxes),
            min(box[1] for box in boxes),
            max(box[2] for box in boxes),
            max(box[3] for box in boxes),
        )
