"""Running the lessons in a browser: what gets rewritten, what counts as a failure, and why.

None of this boots Pyodide. Booting twelve runtimes takes minutes and needs Node and an npm
install, and it happens in CI and in `just build-probe`. What is worth testing quickly is the
reading: which lines of a cell get rewritten before it runs, and which failures stop a build.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wasmprobe.lessons import (
    ACCEPTED,
    INSTEAD,
    Cell,
    Lesson,
    Ran,
    cells,
    defanged,
    markdown,
    notebooks,
    regressions,
    summary,
)
from wasmprobe.result import FATAL, OK, RAISED, SKIPPED

#: The top of the repository, four levels up from this file.
REPOSITORY = Path(__file__).resolve().parents[3]

#: The committed run, which several tests below read rather than produce.
COMMITTED = REPOSITORY / "probes" / "pyodide" / "lessons.json"


def ran(*cells: Cell, slug: str = "t99-a-lesson") -> Ran:
    return Ran(python="3.14.2", lessons=[Lesson(slug=slug, cells=list(cells))])


def test_a_magic_line_becomes_pass_and_keeps_its_indentation():
    source = "try:\n    import pyxray\nexcept ImportError:\n    %pip install -q pyxray\n"
    assert defanged(source) == f"try:\n    import pyxray\nexcept ImportError:\n    {INSTEAD}\n"


def test_the_rest_of_the_install_cell_still_runs():
    """The bug this was written for. Dropping the whole cell dropped its `import sys` too, and
    a cell twenty lines later failed with a NameError that had nothing to do with the browser.
    """
    source = "import sys\n%pip install -q pyxray\nprint(sys.version)\n"
    there = defanged(source)
    assert "import sys" in there
    assert "print(sys.version)" in there
    assert "%pip" not in there


def test_a_shell_line_is_treated_the_same_way():
    assert defanged("!python -V\n") == INSTEAD + "\n"


def test_a_cell_with_no_magic_comes_back_unchanged():
    source = "x = 1\nprint(x)\n"
    assert defanged(source) == source


def test_only_the_code_cells_come_out_and_the_empty_ones_do_not(tmp_path):
    book = tmp_path / "t99.ipynb"
    book.write_text(
        json.dumps(
            {
                "cells": [
                    {"cell_type": "markdown", "id": "t99-1", "source": ["# A heading\n"]},
                    {"cell_type": "code", "id": "t99-2", "source": ["print(1)\n"]},
                    {"cell_type": "code", "id": "t99-3", "source": ["\n   \n"]},
                ]
            }
        ),
        encoding="utf-8",
    )
    assert [one["name"] for one in cells(book)] == ["t99-2"]


def test_the_lesson_notebooks_are_found_and_only_narrows_them_down():
    everything = notebooks(REPOSITORY)
    assert len(everything) > 10
    assert all(one.suffix == ".ipynb" for one in everything)
    picked = notebooks(REPOSITORY, ["t05"])
    assert [one.parent.name for one in picked] == ["t05-the-tree-becomes-bytecode"]


def test_a_run_survives_being_written_and_read_back(tmp_path):
    before = ran(Cell("t99-1", OK, printed="hello\n"), Cell("t99-2", RAISED, error="ValueError"))
    before.write(tmp_path / "lessons.json")
    assert Ran.load(tmp_path / "lessons.json") == before


def test_a_lesson_where_every_cell_worked_ran_end_to_end():
    assert ran(Cell("t99-1", OK), Cell("t99-2", OK)).lessons[0].ran


def test_the_summary_counts_lessons_and_cells():
    assert summary(ran(Cell("t99-1", OK), Cell("t99-2", RAISED, error="no"))) == (
        "1 lesson(s) on Pyodide 3.14.2: 0 ran end to end, 2 cell(s) in total"
    )


def test_a_cell_that_failed_with_nobody_having_said_why_is_a_regression():
    found = regressions(ran(Cell("t99-1", OK), Cell("t99-2", RAISED, error="ValueError: no")))
    assert found == ["t99-a-lesson t99-2: ValueError: no"]


def test_a_cell_somebody_has_written_a_decision_about_is_not():
    run = ran(Cell("t99-1", RAISED, error="ValueError: no"))
    assert regressions(run, accepted={"t99-1": "It cannot work there and here is why."}) == []


def test_the_cells_an_accepted_failure_took_with_it_are_not_counted_again():
    """Otherwise accepting one failure looks like it did nothing, and the eleven lines of
    collateral underneath it bury the one line that says what actually went wrong.
    """
    run = ran(
        Cell("t99-1", OK),
        Cell("t99-2", FATAL, error="Maximum call stack size exceeded"),
        Cell("t99-3", SKIPPED, error="the runtime went down first"),
        Cell("t99-4", SKIPPED, error="the runtime went down first"),
    )
    assert regressions(run, accepted={"t99-2": "It takes the tab down. Issue 105."}) == []


def test_a_cell_that_never_ran_with_no_accepted_failure_above_it_is_still_a_regression():
    run = ran(Cell("t99-1", FATAL, error="boom"), Cell("t99-2", SKIPPED, error="never mind"))
    assert regressions(run, accepted={}) == [
        "t99-a-lesson t99-1: boom",
        "t99-a-lesson t99-2: never mind",
    ]


def test_one_lesson_being_excused_does_not_excuse_the_next_one():
    run = Ran(
        python="3.14.2",
        lessons=[
            Lesson("t98-one", [Cell("t98-1", FATAL, error="boom")]),
            Lesson("t99-two", [Cell("t99-1", SKIPPED, error="the runtime went down first")]),
        ],
    )
    assert regressions(run, accepted={"t98-1": "Known."}) == [
        "t99-two t99-1: the runtime went down first"
    ]


def test_the_report_names_the_cell_the_decision_and_how_much_it_took_with_it():
    run = ran(
        Cell("t99-1", OK),
        Cell("t99-2", FATAL, error="Maximum call stack size exceeded"),
        Cell("t99-3", SKIPPED, error="the runtime went down first"),
    )
    body = markdown(run)
    assert "| t99-a-lesson | 3 | 2 of 3 did not run |" in body
    assert "Maximum call stack size exceeded" in body
    assert "The cell after it" in body
    assert body.endswith("\n")


def test_a_run_with_nothing_wrong_has_no_trouble_section():
    assert "What did not run" not in markdown(ran(Cell("t99-1", OK)))


@pytest.mark.skipif(not COMMITTED.is_file(), reason="no committed run to read")
def test_every_lesson_in_the_repository_is_in_the_committed_run():
    """A lesson added without rerunning the probe is a lesson nobody has run in a browser."""
    there = {one.slug for one in Ran.load(COMMITTED).lessons}
    assert {one.parent.name for one in notebooks(REPOSITORY)} == there


@pytest.mark.skipif(not COMMITTED.is_file(), reason="no committed run to read")
def test_every_accepted_cell_is_a_cell_that_actually_failed():
    """A decision about a cell that now works is a decision hiding a check that stopped
    running. They are cheap to write and nobody ever goes back to delete them.
    """
    run = Ran.load(COMMITTED)
    failed = {one.name for lesson in run.lessons for one in lesson.failures}
    assert set(ACCEPTED) <= failed
