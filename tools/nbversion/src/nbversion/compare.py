"""Putting two recordings side by side and deciding which differences are allowed.

The rule is that a difference has to be declared, and a declaration has to correspond to a
difference. Both directions matter. Without the first, a lesson can quietly start teaching
something that is only true on one interpreter. Without the second, notes pile up for
differences upstream fixed years ago, and a reader who checks one and finds it wrong stops
believing the rest of them.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import unified_diff

from .record import Recording

#: A cell differs and the author said it would. Reported, not a failure.
DECLARED = "declared"

#: A cell differs and nothing in the notebook says so.
UNDECLARED = "undeclared"

#: A cell carries a note and the two interpreters now agree.
STALE = "stale"

#: The two recordings do not describe the same set of cells, so there is nothing to compare.
MISSING = "missing"

FAILURES = (UNDECLARED, STALE, MISSING)


@dataclass(frozen=True)
class Finding:
    """One thing worth saying about one cell."""

    notebook: str
    cell: str
    kind: str
    detail: str = ""

    @property
    def failed(self) -> bool:
        return self.kind in FAILURES

    def line(self) -> str:
        where = f"{self.notebook}:{self.cell}"
        return f"{where}  {self.kind}" + (f"  {self.detail}" if self.detail else "")


def diff(first: str, second: str, *, names: tuple[str, str], context: int = 2) -> str:
    """The difference between two normalised outputs, as something a person can read."""
    lines = unified_diff(
        first.splitlines(),
        second.splitlines(),
        fromfile=names[0],
        tofile=names[1],
        lineterm="",
        n=context,
    )
    return "\n".join(lines)


def cells(first: Recording, second: Recording, declared: dict[str, str]) -> list[Finding]:
    """Compare one notebook's two recordings."""
    found = []
    for cell in sorted(set(first.cells) | set(second.cells)):
        if cell not in first.cells or cell not in second.cells:
            present = first.python if cell in first.cells else second.python
            found.append(
                Finding(
                    first.notebook,
                    cell,
                    MISSING,
                    f"recorded on {present} only, so the two runs saw different notebooks",
                )
            )
            continue
        differs = first.cells[cell] != second.cells[cell]
        note = declared.get(cell, "")
        if differs and note:
            found.append(Finding(first.notebook, cell, DECLARED, note))
        elif differs:
            found.append(
                Finding(
                    first.notebook,
                    cell,
                    UNDECLARED,
                    diff(
                        first.cells[cell],
                        second.cells[cell],
                        names=(first.python, second.python),
                    ),
                )
            )
        elif note:
            found.append(
                Finding(
                    first.notebook,
                    cell,
                    STALE,
                    f"the note says {note!r} but both interpreters print the same thing",
                )
            )
    return found


def notebooks(
    first: dict[str, Recording],
    second: dict[str, Recording],
    declared: dict[str, dict[str, str]],
) -> list[Finding]:
    """Compare two directories of recordings."""
    found = []
    for name in sorted(set(first) | set(second)):
        if name not in first or name not in second:
            side = "second" if name in first else "first"
            found.append(
                Finding(name, "-", MISSING, f"there is no recording of it in the {side} run")
            )
            continue
        found.extend(cells(first[name], second[name], declared.get(name, {})))
    return found


def summary(findings: list[Finding]) -> str:
    """One line saying how it went, for the end of the output."""
    counted = {kind: 0 for kind in (DECLARED, UNDECLARED, STALE, MISSING)}
    for one in findings:
        counted[one.kind] += 1
    parts = [f"{counted[kind]} {kind}" for kind in counted if counted[kind]]
    return ", ".join(parts) if parts else "no differences"
