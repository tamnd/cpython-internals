"""The handful of pictures this project draws over and over.

A lesson should not be laying out boxes by hand. It should say "this is a pipeline, here
are the stages, highlight the third one", and get back a picture that looks like every
other pipeline in the material. That consistency is the whole point: a reader who has
learned to read one of these has learned to read all of them.

Anything a lesson needs that is genuinely one of a kind gets drawn with the `Scene`
primitives directly. That is fine and expected. What is not fine is a second, slightly
different pipeline figure.
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import pairwise

from pyxray import theme

from .scene import Element, Scene, text_width


def pipeline(
    name: str,
    stages: Sequence[tuple[str, str]],
    *,
    highlight: int | None = None,
    title: str = "",
    caption: str = "",
) -> Scene:
    """Stages left to right with arrows between them, the workhorse of the whole project.

    Each stage is a label and a second line naming the CPython source that does it, because
    the single most useful thing a diagram here can do is tell the reader where to go and
    look. Passing an empty string as the second line leaves it off.
    """
    scene = Scene(name)
    y = 0.0
    if title:
        scene.text(title, 0, y, size=theme.TITLE_SIZE)
        y += theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    # One width for every stage. Sizing each box to its own label makes the row look like a
    # ransom note and quietly suggests the wide stages are the important ones.
    width = max(text_width(label, theme.BODY_SIZE) for label, _ in stages) + 2 * theme.PADDING
    width = max(width, 140)
    boxes = []
    x = 0.0
    for index, (label, source) in enumerate(stages):
        tone = "focus" if index == highlight else ("input" if index == 0 else "intermediate")
        box = scene.box(label, x, y, width=width, height=80, tone=tone)
        boxes.append(box)
        if source:
            scene.text(
                source,
                x + width / 2,
                y + 80 + 10,
                size=theme.CAPTION_SIZE,
                colour=theme.MUTED,
                mono=True,
                align="centre",
            )
        x += width + theme.GAP

    for before, after in pairwise(boxes):
        scene.arrow(before, after)

    if caption:
        bottom = max(element.box[3] for element in scene.elements)
        scene.text(caption, 0, bottom + theme.GRID, size=theme.CAPTION_SIZE, colour=theme.MUTED)
    return scene


def flow(
    name: str,
    steps: Sequence[str],
    *,
    title: str = "",
    tones: Sequence[str] | None = None,
    labels: Sequence[str] = (),
) -> Scene:
    """The same idea running down the page, for a chain too long to fit across one.

    The arrow labels matter more here than in a pipeline, because a vertical chain is
    usually describing a decision or a handoff rather than a sequence of stages.
    """
    scene = Scene(name)
    y = 0.0
    if title:
        scene.text(title, 0, y, size=theme.TITLE_SIZE)
        y += theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    width = max(text_width(step, theme.BODY_SIZE) for step in steps) + 2 * theme.PADDING
    width = max(width, 200)
    boxes = []
    for index, step in enumerate(steps):
        tone = tones[index] if tones else ("input" if index == 0 else "intermediate")
        boxes.append(scene.box(step, 0, y, width=width, height=70, tone=tone))
        y += 70 + theme.GAP

    for index, (before, after) in enumerate(pairwise(boxes)):
        label = labels[index] if index < len(labels) else ""
        arrow = scene.arrow(before, after, sides=("bottom", "top"))
        if label:
            _, top, right, bottom = arrow.box
            scene.text(
                label,
                right + 12,
                (top + bottom) / 2 - theme.CAPTION_SIZE * theme.LINE_HEIGHT / 2,
                size=theme.CAPTION_SIZE,
                colour=theme.MUTED,
            )
    return scene


def stack(name: str, cells: Sequence[str], *, title: str = "", note: str = "") -> Scene:
    """A stack with the top drawn at the top, which is how everybody describes one.

    Half the stack diagrams in circulation are drawn the other way up from the way the
    accompanying text talks about them, and readers quietly lose an hour to it.
    """
    scene = Scene(name)
    y = 0.0
    if title:
        scene.text(title, 0, y, size=theme.TITLE_SIZE)
        y += theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    width = max((text_width(cell, theme.BODY_SIZE, mono=True) for cell in cells), default=120)
    width = max(width + 2 * theme.PADDING, 160)
    for index, cell in enumerate(reversed(list(cells))):
        tone = "focus" if index == 0 else "intermediate"
        scene.box(cell, 0, y, width=width, height=52, tone=tone, mono=True)
        if index == 0:
            scene.text(
                "top",
                width + 16,
                y + 52 / 2 - theme.CAPTION_SIZE * theme.LINE_HEIGHT / 2,
                size=theme.CAPTION_SIZE,
                colour=theme.MUTED,
            )
        y += 52
    if note:
        scene.text(note, 0, y + theme.GRID, size=theme.CAPTION_SIZE, colour=theme.MUTED)
    return scene


def table(
    name: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    *,
    title: str = "",
    caption: str = "",
    tones: Sequence[str] | None = None,
) -> Scene:
    """A trace table: a few columns of monospaced text, one row per step.

    Nearly every lesson wants to walk something one step at a time and show what changed,
    and the honest way to do that is a table. Cells are monospaced and left aligned so the
    columns line up, which is the only reason to draw a table rather than write a
    paragraph. A row can be tinted to mark the step where it goes wrong.
    """
    scene = Scene(name)
    y = 0.0
    if title:
        scene.text(title, 0, y, size=theme.TITLE_SIZE)
        y += theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    pad = 14
    height = 40
    widths = [
        max(text_width(cell, theme.CAPTION_SIZE, mono=True) for cell in column) + 2 * pad
        for column in zip(headers, *rows, strict=True)
    ]
    edges = [sum(widths[:index]) for index in range(len(widths) + 1)]

    for index, heading in enumerate(headers):
        scene.text(heading, edges[index] + pad, y, size=theme.CAPTION_SIZE, colour=theme.MUTED)
    y += theme.CAPTION_SIZE * theme.LINE_HEIGHT + 6
    scene.line([(0, y), (edges[-1], y)], colour=theme.LINE)

    for row_index, row in enumerate(rows):
        tone = theme.tone(tones[row_index]) if tones else None
        if tone:
            scene.band(
                [(0, y), (edges[-1], y), (edges[-1], y + height), (0, y + height)], fill=tone.fill
            )
        for index, cell in enumerate(row):
            scene.text(
                cell,
                edges[index] + pad,
                y + (height - theme.CAPTION_SIZE * theme.LINE_HEIGHT) / 2,
                size=theme.CAPTION_SIZE,
                mono=True,
            )
        y += height
        scene.line([(0, y), (edges[-1], y)], colour=theme.LINE)

    if caption:
        scene.text(caption, 0, y + theme.GRID, size=theme.CAPTION_SIZE, colour=theme.MUTED)
    return scene


#: A node is either a bare string, which is a leaf, or a label and its children. Allowing
#: both keeps the call sites readable: an AST is mostly leaves, and writing `("Mult", [])`
#: forty times is noise around the shape you are trying to show.
Node = str | tuple[str, "Sequence[Node]"]


def _parts(node: Node) -> tuple[str, Sequence[Node]]:
    return (node, ()) if isinstance(node, str) else node


def tree(
    name: str,
    root: Node,
    *,
    title: str = "",
    caption: str = "",
    height: float = 52,
) -> Scene:
    """A tree drawn downwards, with each parent centred over its children.

    Written for the syntax tree, which is the picture the front end lessons keep needing,
    and `ast.dump` is a poor substitute: it is correct, and reading the shape of a tree out
    of nested brackets is work the reader should not have to do.

    Layout is the usual two passes. Measure the width each subtree needs, then place them
    left to right and put every parent over the middle of its own children. Nothing here
    tries to be clever about crossing edges, because a syntax tree cannot have any.
    """
    scene = Scene(name)
    top = 0.0
    if title:
        scene.text(title, 0, top, size=theme.TITLE_SIZE)
        top += theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    gap_x = 20
    gap_y = 44

    def own_width(node: Node) -> float:
        label, _ = _parts(node)
        return text_width(label, theme.CAPTION_SIZE, mono=True) + 2 * theme.PADDING

    def span(node: Node) -> float:
        _, children = _parts(node)
        if not children:
            return own_width(node)
        below = sum(span(child) for child in children) + gap_x * (len(children) - 1)
        return max(own_width(node), below)

    def place(node: Node, left: float, depth: int) -> Element:
        label, children = _parts(node)
        width = own_width(node)
        y = top + depth * (height + gap_y)
        if not children:
            tone = "durable"
            box = scene.box(
                label,
                left + (span(node) - width) / 2,
                y,
                width=width,
                height=height,
                tone=tone,
                mono=True,
                size=theme.CAPTION_SIZE,
                align="center",
            )
            return box

        cursor = left
        placed = []
        for child in children:
            placed.append(place(child, cursor, depth + 1))
            cursor += span(child) + gap_x

        middle = (placed[0].centre()[0] + placed[-1].centre()[0]) / 2
        tone = "input" if depth == 0 else "intermediate"
        box = scene.box(
            label,
            middle - width / 2,
            y,
            width=width,
            height=height,
            tone=tone,
            mono=True,
            size=theme.CAPTION_SIZE,
            align="center",
        )
        for child in placed:
            scene.line([box.port("bottom"), child.port("top")], colour=theme.LINE)
        return box

    place(root, 0, 0)

    if caption:
        bottom = max(element.box[3] for element in scene.elements)
        scene.text(caption, 0, bottom + theme.GRID, size=theme.CAPTION_SIZE, colour=theme.MUTED)
    return scene


def spans(
    name: str,
    text: str,
    marks: Sequence[tuple[int, int, str]],
    *,
    title: str = "",
    caption: str = "",
) -> Scene:
    """A line of source with its pieces named underneath, joined by ribbons.

    This is the picture that makes tokenizing click, and character art cannot do it: the
    marks have to line up under proportional glyph positions and each one wants its own
    colour. Each mark is a start column, an end column and a name.

    The naming is the hard part. A token name is nearly always wider than the token it
    names, so labels parked under their spans either overlap or drift off the thing they
    point at. Leader lines fix the overlap and then cross each other. Ribbons fix both:
    the spans run left to right and so do the labels, so a shape joining the two rows can
    never cross another one, and a solid shape reads at a glance where a thin line has to
    be traced.
    """
    scene = Scene(name)
    y = 0.0
    if title:
        scene.text(title, 0, y, size=theme.TITLE_SIZE)
        y += theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    character = text_width("x", theme.BODY_SIZE, mono=True)
    scene.text(text, 0, y, size=theme.BODY_SIZE, mono=True, exact=True)
    rule = y + theme.BODY_SIZE * theme.LINE_HEIGHT + 6
    chip_top = rule + 72
    chip_height = 36
    tones = [theme.cycle(index) for index in range(len(marks))]

    # Ribbons first, so the underline and the chip border both sit on top of them.
    cursor = 0.0
    places = []
    for (_, _, label), tone in zip(marks, tones, strict=True):
        width = text_width(label, theme.CAPTION_SIZE) + 2 * theme.PADDING
        places.append((cursor, width, tone))
        cursor += width + 8

    for (start, end, _), (left, width, tone) in zip(marks, places, strict=True):
        scene.band(
            [
                (start * character, rule),
                (end * character, rule),
                (left + width, chip_top),
                (left, chip_top),
            ],
            fill=tone.fill,
            opacity=40,
        )

    # A solid bar under each span, so the reader can see exactly which characters were
    # taken, including the four spaces at the front that INDENT is made of.
    for (start, end, _), (_, _, tone) in zip(marks, places, strict=True):
        scene.line([(start * character, rule), (end * character, rule)], colour=tone.stroke)

    for (_, _, label), (left, width, tone) in zip(marks, places, strict=True):
        scene.box(
            label,
            left,
            chip_top,
            width=width,
            height=chip_height,
            tone=tone.name,
            size=theme.CAPTION_SIZE,
            align="center",
        )

    if caption:
        bottom = max(element.box[3] for element in scene.elements)
        scene.text(caption, 0, bottom + theme.GRID, size=theme.CAPTION_SIZE, colour=theme.MUTED)
    return scene


def compare(
    name: str,
    left: tuple[str, Sequence[str]],
    right: tuple[str, Sequence[str]],
    *,
    title: str = "",
    verdict: str = "",
) -> Scene:
    """Two columns side by side, for showing that two things which look alike are not.

    Written for the tabs and spaces section, where the entire point is that one line
    measures the same under both counts and the other does not.
    """
    scene = Scene(name)
    y = 0.0
    if title:
        scene.text(title, 0, y, size=theme.TITLE_SIZE)
        y += theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    everything = [*left[1], *right[1], left[0], right[0]]
    width = max(text_width(item, theme.BODY_SIZE, mono=True) for item in everything)
    width = max(width + 2 * theme.PADDING, 220)
    column = width + theme.GAP

    for index, (heading, rows) in enumerate((left, right)):
        x = index * column
        scene.text(heading, x + width / 2, y, size=theme.BODY_SIZE, align="centre")
        top = y + theme.BODY_SIZE * theme.LINE_HEIGHT + 12
        for row_index, row in enumerate(rows):
            tone = "quiet" if row_index else ("input" if index == 0 else "durable")
            scene.box(row, x, top, width=width, height=52, tone=tone, mono=True)
            top += 52 + 8

    if verdict:
        bottom = max(element.box[3] for element in scene.elements)
        scene.box(
            verdict,
            0,
            bottom + theme.GRID,
            width=column + width,
            height=60,
            tone="warning",
        )
    return scene
