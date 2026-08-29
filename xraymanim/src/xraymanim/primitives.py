"""The nine shapes an animation is allowed to draw.

Every picture in this project is made of these and nothing else. That is a real constraint
and it is the point: a reader who learns in the first animation that a thick arrow owns
what it points at can read the fortieth animation without being taught again. A scene file
that needs a shape which is not here has found a gap in the visual system, and the fix is
to amend VISUAL-SYSTEM.md and add it here, not to draw something local and move on.

Nothing here places itself. Every function returns a `VGroup` sitting at the origin and the
caller says where it goes, for the same reason the Excalidraw diagrams have no auto layout:
automatic placement is why generated pictures look generated.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Arrow,
    Line,
    Rectangle,
    RoundedRectangle,
    SurroundingRectangle,
    Text,
    VGroup,
)

from .grammar import (
    BODY_SIZE,
    BORROWED_STROKE,
    BOX_HEIGHT,
    BOX_WIDTH,
    CAPTION_SIZE,
    CORNER,
    GAP,
    INK,
    LABEL_SIZE,
    LINE,
    MUTED,
    OWNED_STROKE,
    STROKE,
    UNIT,
    Pen,
    mono_font,
    pen,
    sans_font,
)


def label(text: str, *, size: int = BODY_SIZE, mono: bool = False, colour: str = INK) -> Text:
    """A piece of text in the project's type, which is the only way text gets made here.

    Going through one function means a font substitution shows up in one place rather than
    in thirty scene files, and it means nothing accidentally renders in manim's default
    white on a white page.
    """
    font = mono_font() if mono else sans_font()
    if not font:
        return Text(text, font_size=size, color=colour)
    return Text(text, font=font, font_size=size, color=colour)


def box(
    text: str,
    *,
    tone: str = "quiet",
    width: float = BOX_WIDTH,
    height: float = BOX_HEIGHT,
    mono: bool = False,
    size: int = BODY_SIZE,
    note: str = "",
) -> VGroup:
    """Primitive 1, the box: anything that has a memory address.

    If it is drawn as a box it is a thing you could take the address of. Values that are
    not objects, like an index or a count, are drawn as bare text so the distinction stays
    visible, which matters a lot once the lessons get to what a name actually holds.
    """
    ink: Pen = pen(tone)
    shape = RoundedRectangle(corner_radius=CORNER, width=width, height=height, **ink.kwargs())
    caption = label(text, size=size, mono=mono)
    caption.scale_to_fit_width(min(caption.width, width - 2 * UNIT))
    group = VGroup(shape, caption.move_to(shape.get_center()))
    if note:
        under = label(note, size=CAPTION_SIZE, colour=MUTED)
        group.add(under.next_to(shape, DOWN, buff=UNIT))
    group.shape = shape
    group.caption = caption
    return group


def arrow(
    start: object,
    end: object,
    *,
    owned: bool = True,
    tone: str = "quiet",
    text: str = "",
    direction: object = RIGHT,
) -> VGroup:
    """Primitive 2, the arrow: a reference from one thing to another.

    Weight carries the meaning. A thick arrow is a reference that owns what it points at
    and is counted in the refcount. A thin one is borrowed and is not. That single
    distinction is most of what goes wrong when somebody writes C against CPython, so it
    gets a visual difference rather than a footnote.
    """
    ink = pen(tone)
    tail = start.get_edge_center(direction) if hasattr(start, "get_edge_center") else start
    head = end.get_edge_center(-direction) if hasattr(end, "get_edge_center") else end
    line = Arrow(
        tail,
        head,
        buff=UNIT / 2,
        color=ink.stroke,
        stroke_width=OWNED_STROKE if owned else BORROWED_STROKE,
        max_tip_length_to_length_ratio=0.18,
    )
    group = VGroup(line)
    if text:
        # The label goes beside the middle of the arrow, offset at a right angle to it,
        # rather than above its bounding box. For a diagonal arrow those are not the same
        # place, and the bounding box answer puts the words on top of the line.
        along = line.get_end() - line.get_start()
        sideways = np.array([-along[1], along[0], 0.0])
        length = float(np.linalg.norm(sideways))
        sideways = np.array([0.0, 1.0, 0.0]) if length == 0 else sideways / length
        if sideways[1] < 0:
            sideways = -sideways
        caption = label(text, size=CAPTION_SIZE, colour=MUTED)
        caption.move_to(line.get_center() + sideways * (caption.height / 2 + UNIT))
        group.add(caption)
    group.line = line
    return group


def slots(
    values: Sequence[str],
    *,
    tone: str = "quiet",
    width: float = 1.1,
    height: float = 0.7,
    columns: int = 0,
    mono: bool = True,
) -> VGroup:
    """Primitive 3, the slot grid: an array, a table, anything indexed by a number.

    Slots touch. The shared edges are the thing being said: these cells are next to each
    other in memory, which is why the index arithmetic works and why growing the array
    means copying it.
    """
    ink = pen(tone)
    across = columns or len(values)
    cells = VGroup()
    for index, value in enumerate(values):
        cell = Rectangle(width=width, height=height, **ink.kwargs())
        row, column = divmod(index, across)
        cell.move_to(RIGHT * column * width + DOWN * row * height)
        text = label(value, size=LABEL_SIZE, mono=mono)
        if text.width > width - UNIT:
            text.scale_to_fit_width(width - UNIT)
        cells.add(VGroup(cell, text.move_to(cell.get_center())))
    cells.move_to([0, 0, 0])
    return cells


def column(cells: Sequence[str], *, tone: str = "focus", width: float = 2.2) -> VGroup:
    """Primitive 4, the stack column: a stack, always growing upward.

    Upward, every time, in every lesson. CPython's value stack grows toward higher
    addresses and the call stack is usually drawn growing down, and picking one direction
    and never changing it is worth more than matching either convention.
    """
    ink = pen(tone)
    group = VGroup()
    for index, value in enumerate(cells):
        cell = Rectangle(width=width, height=0.6, **ink.kwargs())
        cell.move_to(UP * index * 0.6)
        group.add(VGroup(cell, label(value, size=LABEL_SIZE, mono=True).move_to(cell.get_center())))
    floor = Line(LEFT * width / 2, RIGHT * width / 2, color=LINE, stroke_width=STROKE)
    floor.move_to(DOWN * 0.3)
    group.add(floor)
    group.floor = floor
    return group


def stream(
    items: Sequence[str], *, tone: str = "input", gap: float = GAP / 2, rows: int = 1
) -> VGroup:
    """Primitive 5, the stream: tokens, instructions, bytes, anything consumed in order.

    Chips with air between them, not a grid. The gap says these arrive one at a time and
    that the thing reading them has a position in the sequence, which is the difference
    between a token stream and an array of tokens.

    A long stream can be wrapped onto several rows. That is still one stream and it is still
    read in order, left to right and then down, the same way a paragraph is. Wrapping beats
    the alternative, which is shrinking the text until nobody can read the opcode names.

    The chips are also kept in a flat list on the returned group, because the caller almost
    always wants the fourth chip and should not have to know which row it landed on.
    """
    ink = pen(tone)
    made = []
    for value in items:
        text = label(value, size=LABEL_SIZE, mono=True)
        chip = RoundedRectangle(
            corner_radius=CORNER / 2,
            width=max(text.width + 2 * UNIT, 0.8),
            height=0.62,
            **ink.kwargs(),
        )
        made.append(VGroup(chip, text.move_to(chip.get_center())))
    group = VGroup()
    per_row = -(-len(made) // max(rows, 1)) or 1
    for start in range(0, len(made), per_row):
        line = VGroup(*made[start : start + per_row])
        line.arrange(RIGHT, buff=gap)
        group.add(line)
    group.arrange(DOWN, buff=gap, aligned_edge=LEFT)
    group.chips = made
    return group


def tree(node: object, *, tone: str = "intermediate", spread: float = 2.3) -> VGroup:
    """Primitive 6, the tree: the syntax tree, the type hierarchy, anything with parents.

    Laid out by counting leaves, so siblings never overlap and a subtree keeps its shape
    when the tree around it grows. Children hang below their parent, which is the direction
    every Python program that walks an AST goes.
    """
    ink = pen(tone)
    group = VGroup()

    def parts(item: object) -> tuple[str, Sequence]:
        return (item, ()) if isinstance(item, str) else (item[0], item[1])

    def leaves(item: object) -> int:
        _, children = parts(item)
        return max(1, sum(leaves(child) for child in children))

    def place(item: object, left: float, depth: int) -> VGroup:
        text, children = parts(item)
        span = leaves(item) * spread
        here = box(text, tone=tone, width=2.1, height=0.6, size=LABEL_SIZE, mono=True)
        here.move_to([left + span / 2, -depth * 1.15, 0])
        group.add(here)
        offset = left
        for child in children:
            drawn = place(child, offset, depth + 1)
            group.add(
                Line(
                    here.get_edge_center(DOWN),
                    drawn.get_edge_center(UP),
                    color=ink.stroke,
                    stroke_width=BORROWED_STROKE,
                )
            )
            offset += leaves(child) * spread
        return here

    root = place(node, 0, 0)
    group.root = root
    group.move_to([0, 0, 0])
    return group


def graph(
    nodes: dict[str, Sequence[float]],
    edges: Sequence[tuple[str, str]],
    *,
    tone: str = "durable",
    width: float = 1.6,
) -> VGroup:
    """Primitive 7, the graph: the control flow graph, the object graph, anything cyclic.

    Positions are given, never computed. A control flow graph laid out automatically is a
    control flow graph nobody can read, and the graphs here are small enough that placing
    them by hand takes a minute and is worth it every time.
    """
    drawn = {name: box(name, tone=tone, width=width, height=0.7, size=LABEL_SIZE) for name in nodes}
    for name, position in nodes.items():
        drawn[name].move_to([position[0], position[1], 0])
    group = VGroup()
    for source, target in edges:
        group.add(arrow(drawn[source], drawn[target], owned=False, tone=tone, direction=DOWN))
    group.add(*drawn.values())
    group.nodes = drawn
    return group


def counter(value: int, *, name: str = "refcount", tone: str = "focus") -> VGroup:
    """Primitive 8, the counter: a refcount, a version tag, anything that goes up and down.

    A number with its name under it, because a bare number floating next to a box is the
    thing readers most often misread. Two of these on screen at once, one refcount and one
    version tag, have to be told apart at a glance.
    """
    ink = pen(tone)
    digits = label(str(value), size=BODY_SIZE, mono=True, colour=ink.stroke)
    ring = RoundedRectangle(
        corner_radius=CORNER, width=0.9, height=0.62, **ink.faded(0.25).kwargs()
    )
    group = VGroup(ring, digits.move_to(ring.get_center()))
    group.add(label(name, size=CAPTION_SIZE, colour=MUTED).next_to(ring, DOWN, buff=UNIT / 2))
    group.digits = digits
    group.ring = ring
    return group


def highlight(target: object, *, tone: str = "focus") -> SurroundingRectangle:
    """Primitive 9, the highlight: the thing happening right now.

    One highlight on screen at a time. Two is the animation telling the reader to look in
    two places, which is the same as telling them nothing.
    """
    ink = pen(tone)
    return SurroundingRectangle(
        target,
        color=ink.stroke,
        buff=UNIT / 2,
        corner_radius=CORNER,
        stroke_width=OWNED_STROKE,
    )
