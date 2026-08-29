"""Running a whole lesson in the browser, rather than asking whether the pieces exist.

`checks.py` asks fifteen narrow questions: is `_testinternalcapi` there, does `sys.monitoring`
fire, can a thread start. Useful, and one step short of the thing the project promises. The
promise on the front page is that a chapter runs in a browser tab, and the only way to know
that is to run the chapter.

So this takes a lesson's notebook, drops the markdown, rewrites the one line of the install
cell that cannot run here, and runs the code cells in order in one Pyodide runtime, keeping
what each one printed. A cell that
raises is recorded with the line it raised on. A cell that takes the runtime down means the
rest of that lesson never ran, and is recorded that way rather than being retried in a fresh
runtime, because a cell that ran in a different interpreter than the cells above it has not
been tested, it has been let off.

pyxray is mounted off the disk rather than installed. No network, no wheel, and the thing
being tested is the source in this checkout rather than whatever is published today.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .browser import DRIVER, Missing, ready
from .result import FATAL, OK, RAISED, SKIPPED

#: The lesson driver, next to the checks driver and for the same reason: it is not Python.
LESSON_DRIVER = DRIVER.parent / "lesson.mjs"

#: What goes on `sys.path` inside the runtime, relative to the top of the repository. The
#: source directories rather than an install, so this needs no network and tests what is in
#: the checkout. Anything a lesson imports has to be listed here or already in the stdlib.
PATHS = ("pyxray/src", "tools/refcheck/src")

#: Where the lessons are.
LESSONS = Path("lessons")

#: The start of a line this cannot run. `%pip` is an IPython magic and is a syntax error to
#: `exec`, and the install it does is for Colab: here the package is already on the path,
#: which is the whole reason this needs no network.
MAGIC = ("%", "!")

#: What a magic line becomes. `pass` rather than nothing, because the magic in a lesson lives
#: inside an `except ImportError:` block and deleting the line would leave an empty one.
INSTEAD = "pass  # an install, which this runner does not need and cannot do"


@dataclass(frozen=True)
class Cell:
    """One code cell, and what it did in the browser."""

    name: str
    status: str
    printed: str = ""
    error: str = ""

    @property
    def worked(self) -> bool:
        return self.status == OK

    def as_dict(self) -> dict:
        body = {"name": self.name, "status": self.status}
        if self.printed:
            body["printed"] = self.printed
        if self.error:
            body["error"] = self.error
        return body

    @classmethod
    def from_dict(cls, body: dict) -> Cell:
        return cls(
            name=str(body["name"]),
            status=str(body["status"]),
            printed=str(body.get("printed", "")),
            error=str(body.get("error", "")),
        )


@dataclass(frozen=True)
class Lesson:
    """One lesson's run, cell by cell."""

    slug: str
    cells: list[Cell] = field(default_factory=list)

    @property
    def ran(self) -> bool:
        return all(one.worked for one in self.cells)

    @property
    def failures(self) -> list[Cell]:
        return [one for one in self.cells if not one.worked]

    def as_dict(self) -> dict:
        return {"slug": self.slug, "cells": [one.as_dict() for one in self.cells]}

    @classmethod
    def from_dict(cls, body: dict) -> Lesson:
        return cls(
            slug=str(body["slug"]),
            cells=[Cell.from_dict(one) for one in body.get("cells", [])],
        )


@dataclass(frozen=True)
class Ran:
    """Every lesson that was run, and the runtime that ran them."""

    python: str = ""
    runtime: str = "pyodide"
    lessons: list[Lesson] = field(default_factory=list)

    def as_json(self) -> str:
        body = {
            "runtime": self.runtime,
            "python": self.python,
            "lessons": [one.as_dict() for one in self.lessons],
        }
        return json.dumps(body, indent=2) + "\n"

    @classmethod
    def from_json(cls, text: str) -> Ran:
        body = json.loads(text)
        return cls(
            python=str(body.get("python", "")),
            runtime=str(body.get("runtime", "pyodide")),
            lessons=[Lesson.from_dict(one) for one in body.get("lessons", [])],
        )

    @classmethod
    def load(cls, path: Path) -> Ran:
        return cls.from_json(path.read_text(encoding="utf-8"))

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.as_json(), encoding="utf-8")


def defanged(source: str) -> str:
    """The cell with its magic lines turned into `pass`, indentation and all else intact.

    The whole cell used to be dropped, and that was wrong in a way worth writing down. A
    lesson's first cell is the install, and it also does `import sys` and prints the version
    banner. Dropping it took `sys` with it, and a cell twenty lines later failed with a
    NameError that had nothing to do with the browser. Running the cell with one line
    replaced tests what a reader gets, minus the one line a reader in a browser skips.
    """
    lines = []
    for line in source.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(MAGIC):
            lines.append(" " * (len(line) - len(stripped)) + INSTEAD)
        else:
            lines.append(line)
    return "\n".join(lines) + "\n"


def cells(notebook: Path) -> list[dict]:
    """The code cells of a notebook, in order, with their magic lines defanged."""
    body = json.loads(notebook.read_text(encoding="utf-8"))
    found = []
    for cell in body.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        if not source.strip():
            continue
        found.append({"name": str(cell.get("id", "")), "source": defanged(source)})
    return found


def notebooks(root: Path, only: list[str] | None = None) -> list[Path]:
    """Every lesson notebook, or the ones whose directory starts with one of `only`."""
    found = []
    for where in sorted((root / LESSONS).iterdir()):
        if not where.is_dir():
            continue
        if only and not any(where.name.startswith(one.lower()) for one in only):
            continue
        book = where / f"{where.name.split('-')[0]}.ipynb"
        if book.is_file():
            found.append(book)
    return found


def run(root: Path, only: list[str] | None = None, timeout: int = 1800) -> Ran:
    """Run each lesson start to finish in its own Pyodide runtime."""
    problem = ready()
    if problem:
        raise Missing(problem)
    plan = {
        "root": str(root.resolve()),
        "paths": list(PATHS),
        "lessons": [
            {"slug": one.parent.name, "cells": cells(one)} for one in notebooks(root, only)
        ],
    }
    with tempfile.TemporaryDirectory() as room:
        inbox = Path(room) / "plan.json"
        outbox = Path(room) / "out.json"
        inbox.write_text(json.dumps(plan), encoding="utf-8")
        finished = subprocess.run(
            ["node", str(LESSON_DRIVER), str(inbox), str(outbox)],
            cwd=LESSON_DRIVER.parent,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if not outbox.exists():
            tail = (finished.stderr or finished.stdout).strip().splitlines()
            raise Missing("the driver wrote nothing: " + (tail[-1] if tail else "no output"))
        return Ran.from_json(outbox.read_text(encoding="utf-8"))


#: Cells that do not run in the browser and are not going to, with the decision about each
#: one. A cell in here is reported and does not fail the build. A cell not in here that fails
#: does, which is the whole arrangement: a gap stays visible in the report instead of being
#: deleted, and a new one stops the build.
ACCEPTED: dict[str, str] = {}

#: How each status reads in the report, so the two tables agree on their words.
WORDS = {
    OK: "ran",
    RAISED: "raised",
    FATAL: "took the runtime down",
    SKIPPED: "never reached",
}


def summary(ran: Ran) -> str:
    """One line saying how many lessons ran end to end in the browser."""
    whole = sum(1 for one in ran.lessons if one.ran)
    cells_run = sum(len(one.cells) for one in ran.lessons)
    return (
        f"{len(ran.lessons)} lesson(s) on Pyodide {ran.python}: {whole} ran end to end, "
        f"{cells_run} cell(s) in total"
    )


def markdown(ran: Ran) -> str:
    """The report a person reads, which is one row per lesson and the detail underneath."""
    lines = [
        "# Do the lessons run in a browser",
        "",
        "Generated by `just build-probe`. Do not edit by hand, the change will be overwritten.",
        "",
        f"{summary(ran)}.",
        "",
        "The checks in `report.md` next to this ask whether a surface exists. This runs the "
        "lessons themselves: every code cell of every notebook, in order, in one Pyodide "
        "runtime, with `pyxray` mounted off the disk rather than installed. The install cell "
        "is the one thing changed, and only its `%pip` line, which a reader in a browser does "
        "not need either.",
        "",
        "| Lesson | Cells | In the browser |",
        "|---|---|---|",
    ]
    for lesson in ran.lessons:
        bad = lesson.failures
        said = "runs end to end" if not bad else f"{len(bad)} of {len(lesson.cells)} did not run"
        lines.append(f"| {lesson.slug} | {len(lesson.cells)} | {said} |")
    trouble = [one for one in ran.lessons if one.failures]
    if trouble:
        lines += ["", "## What did not run"]
        for lesson in trouble:
            for cell in lesson.failures:
                if cell.status == SKIPPED:
                    continue
                lines += ["", f"**{lesson.slug}, cell {cell.name}.** {cell.error}"]
                if cell.name in ACCEPTED:
                    lines += ["", ACCEPTED[cell.name]]
            after = sum(1 for one in lesson.failures if one.status == SKIPPED)
            if after:
                many = "The cell" if after == 1 else f"The {after} cells"
                lines += [
                    "",
                    f"{many} after it in {lesson.slug} never ran. Nothing is retried in a "
                    "fresh runtime, because a cell that ran in a different interpreter than "
                    "the cells above it has not been tested, it has been let off.",
                ]
    return "\n".join(lines) + "\n"


def regressions(ran: Ran, accepted: dict[str, str] | None = None) -> list[str]:
    """Every cell that did not run, minus the ones somebody has written a decision about.

    A cell that fails in the browser is not automatically a bug in this repository. Pyodide
    is a single threaded WebAssembly build and some of what the lessons show is not there.
    What is not acceptable is a cell failing and nobody having said so, which is what this
    catches. Write the decision in `ACCEPTED` above, keyed by cell, next to the code rather
    than in a data file, so it goes through review like everything else.
    """
    allowed = ACCEPTED if accepted is None else accepted
    found = []
    for lesson in ran.lessons:
        # A cell that never ran because an accepted one took the runtime down is collateral
        # rather than a second finding. Reporting all eleven of them would bury the one line
        # that matters and would make accepting a failure look like it did nothing.
        excused = False
        for cell in lesson.cells:
            if cell.worked:
                continue
            if cell.name in allowed:
                excused = True
                continue
            if cell.status == SKIPPED and excused:
                continue
            found.append(f"{lesson.slug} {cell.name}: {cell.error or WORDS[cell.status]}")
    return found
