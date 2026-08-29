"""The six things CPython has that come up often enough to deserve a name.

The primitives are shapes. These are nouns. A `PyObjectBox` is not just a box, it is the
three fields every object in CPython starts with, drawn the same way every time so that the
reader stops having to decode the picture and can look at what changed in it.

Each one is a `VGroup`, so it can be moved, faded, transformed and animated like anything
else manim draws, and each one exposes the parts an animation is likely to want to point at
or change. That last bit is what makes them worth having: `obj.count` gives you the refcount
digits directly, so incrementing a refcount on screen is one line rather than a search
through submobjects.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import ClassVar

from manim import DOWN, LEFT, RIGHT, UP, Line, RoundedRectangle, VGroup

from .grammar import (
    BORROWED_STROKE,
    CAPTION_SIZE,
    CORNER,
    GAP,
    LABEL_SIZE,
    LINE,
    MUTED,
    UNIT,
    pen,
)
from .primitives import arrow, column, counter, highlight, label, slots, stream


class PyObjectBox(VGroup):
    """Every object in CPython, drawn as the header it actually has.

    A type pointer and a reference count, which is `PyObject`, plus whatever the object
    holds. Drawing the header even when the lesson is about the payload is the point: the
    reader should come away unable to picture a Python value without those two fields,
    because in CPython there is no such thing.
    """

    def __init__(
        self,
        type_name: str,
        value: str = "",
        refcount: int = 1,
        *,
        tone: str = "durable",
        width: float = 3.8,
        address: str = "",
    ) -> None:
        super().__init__()
        ink = pen(tone)
        self.tone = tone
        height = 1.5 if value else 1.0
        self.shell = RoundedRectangle(
            corner_radius=CORNER, width=width, height=height, **ink.kwargs()
        )
        self.type_name = label(f"ob_type: {type_name}", size=CAPTION_SIZE, mono=True)
        self.count = counter(refcount, name="ob_refcnt", tone=tone)
        self.count.scale(0.85)
        rows = VGroup(self.type_name)
        if value:
            self.value = label(value, size=LABEL_SIZE, mono=True)
            rows.add(self.value)
        else:
            self.value = None
        rows.arrange(DOWN, buff=UNIT, aligned_edge=LEFT)
        # The count goes inside the object, on the right, because that is where it is: a
        # field of the object and not a note somebody wrote next to it. Drawing it outside
        # is how a reader ends up thinking the interpreter keeps counts in a table.
        rows.align_to(self.shell, LEFT).shift(RIGHT * UNIT * 1.5)
        rows.set_y(self.shell.get_y())
        self.count.align_to(self.shell, RIGHT).shift(LEFT * UNIT * 1.5)
        self.count.set_y(self.shell.get_y())
        self.add(self.shell, rows, self.count)
        if address:
            self.add(
                label(address, size=CAPTION_SIZE, mono=True, colour=MUTED).next_to(
                    self.shell, UP, buff=UNIT / 2
                )
            )

    def refcount(self, value: int) -> VGroup:
        """The counter this object would have at a different count, sitting in the same place.

        Returning a new mobject rather than editing this one is how manim wants it: the
        animation is the difference between two states, so both states have to exist, and
        `Transform(obj.count, obj.refcount(2))` then reads as what it does.
        """
        replacement = counter(value, name="ob_refcnt", tone=self.tone)
        replacement.scale(0.85).move_to(self.count.get_center())
        return replacement


class RefArrow(VGroup):
    """One reference, from a name or a field to an object.

    Thick means owned and counted. Thin means borrowed and not counted. The label is the
    thing doing the pointing, so a reader can tell a local variable from a struct field
    without being told which is which.
    """

    def __init__(
        self,
        source: object,
        target: object,
        *,
        owned: bool = True,
        text: str = "",
        tone: str = "input",
        direction: object = RIGHT,
        bend: float = 0.0,
    ) -> None:
        super().__init__()
        self.body = arrow(
            source, target, owned=owned, tone=tone, text=text, direction=direction, bend=bend
        )
        self.owned = owned
        self.add(self.body)


class Frame(VGroup):
    """One `_PyInterpreterFrame`: what a call actually is at runtime.

    A name at the top, the locals underneath as slots because that is what they are, and
    the value stack to the right growing upward. Three regions, always in the same three
    places, so that a frame in the lesson about calls and a frame in the lesson about
    generators are recognisably the same object.
    """

    def __init__(
        self,
        name: str,
        locals_: Mapping[str, str] | None = None,
        stack: Sequence[str] = (),
        *,
        tone: str = "quiet",
        width: float = 5.0,
    ) -> None:
        super().__init__()
        ink = pen(tone)
        entries = dict(locals_ or {})
        height = 1.2 + 0.75 * max(len(entries), len(stack), 1)
        self.shell = RoundedRectangle(
            corner_radius=CORNER, width=width, height=height, **ink.faded(0.15).kwargs()
        )
        self.title = label(name, size=LABEL_SIZE, mono=True)
        self.title.next_to(self.shell.get_top(), DOWN, buff=UNIT)
        rule = Line(
            self.shell.get_left() + DOWN * 0 + RIGHT * UNIT,
            self.shell.get_right() + LEFT * UNIT,
            color=LINE,
            stroke_width=BORROWED_STROKE,
        )
        rule.next_to(self.title, DOWN, buff=UNIT / 2)
        self.add(self.shell, self.title, rule)

        self.locals = slots(
            [f"{key}={value}" for key, value in entries.items()] or ["(no locals)"],
            tone="input",
            width=2.2,
            height=0.62,
            columns=1,
        )
        self.locals.next_to(rule, DOWN, buff=UNIT).align_to(self.shell, LEFT).shift(RIGHT * GAP)
        self.add(self.locals)

        # The stack sits on the floor of the frame and grows upward, which is the rule for
        # every stack in the project. Hanging it from the rule instead makes it grow
        # downward as values are pushed, and a reader who sees that once reads every later
        # picture wrong. An empty stack is the floor with nothing on it, because the stack
        # is still there between two instructions.
        self.stack = column(list(stack) or [""], tone="focus", width=1.9)
        if not stack:
            self.stack.submobjects[0].set_opacity(0.0)
        self.stack.align_to(self.shell, RIGHT).shift(LEFT * GAP)
        self.stack.align_to(self.shell, DOWN).shift(UP * (UNIT + 0.2))
        self.add(self.stack)
        self.add(
            label("locals", size=CAPTION_SIZE, colour=MUTED)
            .next_to(self.shell, DOWN, buff=UNIT / 2)
            .align_to(self.locals, LEFT),
            label("value stack", size=CAPTION_SIZE, colour=MUTED)
            .next_to(self.shell, DOWN, buff=UNIT / 2)
            .align_to(self.stack, RIGHT),
        )


class CodeStrip(VGroup):
    """A run of bytecode, with the instruction pointer that walks along it.

    The strip is a stream, one chip per instruction, and the pointer is the highlight. The
    two are separate mobjects on purpose: an animation moves the pointer and leaves the
    code where it is, which is exactly what the interpreter does.
    """

    def __init__(
        self,
        instructions: Sequence[str],
        *,
        tone: str = "intermediate",
        at: int = 0,
        rows: int = 1,
    ) -> None:
        super().__init__()
        self.strip = stream(instructions, tone=tone, rows=rows)
        self.instructions = list(instructions)
        self.add(self.strip)
        self.pointer = None
        if instructions:
            self.point_at(at)

    def point_at(self, index: int) -> CodeStrip:
        """Move the instruction pointer, and return self so it chains inside a scene."""
        if self.pointer is not None:
            self.remove(self.pointer)
        self.pointer = highlight(self.strip.chips[index])
        self.add(self.pointer)
        return self

    def at(self, index: int) -> object:
        """Where the pointer would be for an instruction, for animating it there."""
        return highlight(self.strip.chips[index])


class DictTable(VGroup):
    """A dict, drawn the way CPython actually stores one since 3.6.

    A small index array of slot numbers on the left, and the entries in insertion order on
    the right. That split is the whole reason dicts keep their order and the reason a
    lookup is two steps rather than one, and a picture that draws a dict as a single table
    of key and value pairs has quietly taught the wrong thing.
    """

    def __init__(
        self,
        entries: Sequence[tuple[str, str]],
        *,
        index: Sequence[str] = (),
        tone: str = "durable",
    ) -> None:
        super().__init__()
        self.index = slots(
            list(index) or ["-"] * 8, tone="quiet", width=0.62, height=0.62, columns=1
        )
        self.entries = slots(
            [f"{key}: {value}" for key, value in entries] or ["(empty)"],
            tone=tone,
            width=2.6,
            height=0.62,
            columns=1,
        )
        # A wide gap between the two arrays, not a hairline. They are two separate pieces
        # of memory, and every picture in this animation draws an arrow from one to the
        # other, which needs somewhere to be drawn.
        self.entries.next_to(self.index, RIGHT, buff=GAP * 3).align_to(self.index, UP)

        # The slot numbers, outside the array rather than in it. Without them a reader can
        # count cells to work out which one is slot 6, and a picture that has to be counted
        # is a picture that gets read wrong. They sit outside because a slot number is not
        # stored anywhere: it is the position, in the same way a list index is.
        self.numbers = VGroup(
            *(
                label(str(number), size=CAPTION_SIZE, colour=MUTED).next_to(
                    cell, LEFT, buff=GAP / 2
                )
                for number, cell in enumerate(self.index.submobjects)
            )
        )
        self.add(self.index, self.entries, self.numbers)
        self.add(
            label("indices", size=CAPTION_SIZE, colour=MUTED).next_to(self.index, UP, buff=UNIT),
            label("entries", size=CAPTION_SIZE, colour=MUTED).next_to(self.entries, UP, buff=UNIT),
        )


class ArenaMap(VGroup):
    """The allocator's memory, one cell per block, coloured by what is in it.

    Free is an outline with nothing in it, used is filled, and the cell under discussion is
    the focus tone. Drawing free memory as an empty box rather than leaving a gap is the
    point: the space is still there, it is still owned by the process, and that is why a
    program that frees everything does not always give memory back.
    """

    #: What a character in the layout string means. One character per block keeps a whole
    #: pool on one line of source, which makes an arena easy to edit and easy to read in a
    #: diff, and that matters more here than a richer description would.
    STATES: ClassVar[dict[str, str]] = {".": "free", "#": "used", "*": "focus"}

    #: The tone each state is drawn in. Free is the quiet tone with no fill at all, which is
    #: what makes an empty block read as space the process still owns rather than as nothing.
    TONES: ClassVar[dict[str, str]] = {"free": "quiet", "used": "durable", "focus": "focus"}

    def __init__(self, layout: str, *, columns: int = 8, label_text: str = "") -> None:
        super().__init__()
        unknown = sorted(set(layout) - set(self.STATES))
        if unknown:
            raise ValueError(
                f"unknown block state {unknown}, expected one of {sorted(self.STATES)}"
            )
        cells = VGroup()
        for position, character in enumerate(layout):
            state = self.STATES[character]
            ink = pen(self.TONES[state])
            if state == "free":
                ink = ink.faded(0.0)
            cell = RoundedRectangle(corner_radius=CORNER / 3, width=0.5, height=0.5, **ink.kwargs())
            row, spot = divmod(position, columns)
            cell.move_to(RIGHT * spot * 0.52 + DOWN * row * 0.52)
            cells.add(cell)
        cells.move_to([0, 0, 0])
        self.cells = cells
        self.add(cells)
        if label_text:
            self.add(
                label(label_text, size=CAPTION_SIZE, colour=MUTED).next_to(cells, DOWN, buff=UNIT)
            )
