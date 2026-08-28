"""Pictures, drawn with characters, so that they work everywhere.

A diagram in a lesson has to survive being read on GitHub, in Colab, in a terminal, in a
plain text editor and by a screen reader. That rules out almost everything except text,
and text turns out to be enough for the shapes that matter here: a row of boxes with
arrows, a bar chart, and a stretch of source with its tokens marked underneath.

The rule for everything in this module is that the picture is generated from the same data
the prose is talking about. A diagram drawn by hand is a diagram that goes stale on the
day somebody changes the code, and nobody notices for a year.
"""

from __future__ import annotations

from collections.abc import Sequence

#: The characters used to mark spans in a ribbon, in order. Digits first because a reader
#: matches "3" to "3" faster than "c" to "c", and letters after because ten is not enough.
MARKS = "123456789abcdefghijklmnopqrstuvwxyz"


def boxes(labels: Sequence[str], *, highlight: int | None = None, arrow: str = "->") -> str:
    """A row of labelled boxes joined by arrows.

    The workhorse diagram of the whole project, because almost everything in CPython is one
    stage handing something to the next one. The highlighted box is drawn with a double
    border so a lesson can reuse the same picture and point at a different part of it.
    """
    if not labels:
        return ""
    top, middle, bottom = [], [], []
    for index, label in enumerate(labels):
        width = len(label) + 2
        heavy = index == highlight
        corner, edge, side = ("+", "=", "|") if heavy else ("+", "-", "|")
        top.append(f"{corner}{edge * width}{corner}")
        middle.append(f"{side} {label} {side}")
        bottom.append(f"{corner}{edge * width}{corner}")
    gap = " " * (len(arrow) + 2)
    joiner = f" {arrow} "
    return "\n".join(
        [
            gap.join(top),
            joiner.join(middle),
            gap.join(bottom),
        ]
    )


def stack(labels: Sequence[str], *, title: str = "") -> str:
    """A stack drawn bottom up, because that is the way people picture one.

    Used for the value stack, the indent stack and the frame stack, all of which get
    explained badly in most material by being drawn upside down from how they are
    described.
    """
    width = max((len(str(item)) for item in labels), default=4)
    width = max(width, len(title), 4)
    lines = [f"  {title}"] if title else []
    lines.append(f"  +{'-' * (width + 2)}+")
    for item in reversed(list(labels)):
        lines.append(f"  | {item!s:<{width}} |")
    lines.append(f"  +{'-' * (width + 2)}+")
    return "\n".join(lines)


def bars(rows: Sequence[tuple[str, int]], *, note: Sequence[str] = (), fill: str = "#") -> str:
    """A horizontal bar chart, for anything measured in columns or counts.

    Written for the indentation trace, where the point being made is entirely visual: the
    bars step right, then step back left, and the shape of that is the shape of the code.
    """
    if not rows:
        return ""
    label_width = max(len(label) for label, _ in rows)
    notes = list(note) + [""] * (len(rows) - len(note))
    lines = []
    for (label, value), extra in zip(rows, notes, strict=True):
        bar = fill * value if value else "|"
        lines.append(f"  {label:<{label_width}}  {bar:<20} {value:>3}  {extra}".rstrip())
    return "\n".join(lines)


def ribbon(text: str, spans: Sequence[tuple[int, int, str, str]]) -> str:
    """One line of source with its tokens marked underneath and listed below.

    Each span is a start column, an end column, a name and the matching text. Spans are
    marked with a repeated character rather than an arrow, because arrows collide as soon
    as two tokens are adjacent, and adjacent tokens are the normal case.
    """
    if not text:
        return "(empty)"
    marks = [" "] * len(text)
    legend = []
    for index, (start, end, name, value) in enumerate(spans):
        if start >= len(text) or end <= start:
            continue
        mark = MARKS[index % len(MARKS)]
        for column in range(start, min(end, len(text))):
            marks[column] = mark
        legend.append(f"  {mark}  {name:<16} {value!r}")
    return "\n".join([text, "".join(marks).rstrip(), "", *legend])


def flow(steps: Sequence[str], *, indent: int = 0) -> str:
    """A vertical chain of steps with arrows between them, for pipelines too long for a row."""
    pad = " " * indent
    lines = []
    for index, step in enumerate(steps):
        if index:
            lines.append(f"{pad}  |")
            lines.append(f"{pad}  v")
        lines.append(f"{pad}{step}")
    return "\n".join(lines)


def table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    """A plain aligned table, since half of what a lesson wants to show is a table.

    Not a markdown table. This is for printed output, where the reader is looking at a
    monospace font and a markdown pipe table is noise.
    """
    columns = [list(map(str, column)) for column in zip(headers, *rows, strict=False)]
    widths = [max(len(cell) for cell in column) for column in columns]
    line = "  ".join(f"{head:<{width}}" for head, width in zip(headers, widths, strict=True))
    rule = "  ".join("-" * width for width in widths)
    body = [
        "  ".join(f"{cell!s:<{width}}" for cell, width in zip(row, widths, strict=True)).rstrip()
        for row in rows
    ]
    return "\n".join([line.rstrip(), rule, *body])
