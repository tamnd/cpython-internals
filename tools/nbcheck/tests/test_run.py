"""Executing a notebook for real.

These start a kernel, so they are the slowest thing in the repository by a wide margin.
They are still here rather than mocked, because the only failure worth catching is the one
where a real kernel refuses a cell, and a mock cannot have that opinion.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from notebook_fixtures import code, markdown, write

from nbcheck import execute
from nbcheck.run import Failure, _readable

pytest.importorskip("nbclient")
pytest.importorskip("ipykernel")


def test_a_notebook_where_every_cell_runs_returns_nothing(root):
    path = write(
        root / "fine.ipynb", [markdown("hello"), code("x = 6 * 7\n"), code("assert x == 42\n")]
    )
    assert execute(path) is None


def test_the_first_cell_that_raises_is_the_one_reported(root):
    path = write(
        root / "broken.ipynb",
        [code("x = 1\n"), code("raise ValueError('the fourth cell problem')\n"), code("y = 2\n")],
    )
    failure = execute(path)
    assert failure is not None
    assert failure.cell == 2
    assert "the fourth cell problem" in failure.error


def test_state_carries_between_cells_the_way_a_reader_would_expect(root):
    path = write(root / "state.ipynb", [code("value = 42\n"), code("assert value == 42\n")])
    assert execute(path) is None


def test_the_kernel_starts_in_the_notebooks_own_directory(root):
    """A relative path that works for the reader has to work here, or CI proves nothing."""
    (root / "lesson").mkdir()
    (root / "lesson" / "data.txt").write_text("42", encoding="utf-8")
    path = write(
        root / "lesson" / "reads.ipynb",
        [code("assert open('data.txt').read() == '42'\n")],
    )
    assert execute(path) is None


def test_nothing_is_written_back_to_the_file(root):
    path = write(root / "untouched.ipynb", [code("print('hello')\n")])
    before = path.read_text(encoding="utf-8")
    execute(path)
    assert path.read_text(encoding="utf-8") == before


def test_a_cell_that_runs_too_long_is_a_failure_and_not_a_hang(root):
    path = write(root / "slow.ipynb", [code("import time\ntime.sleep(30)\n")])
    failure = execute(path, timeout=2)
    assert failure is not None


def test_a_failure_prints_the_file_the_cell_and_the_line_that_ran():
    failure = Failure(
        path=Path("lessons/t01/t01.ipynb"),
        cell=4,
        error="ValueError: no",
        source="\nvalue = compute()\nprint(value)\n",
    )
    text = str(failure)
    assert "lessons/t01/t01.ipynb:cell 4" in text
    assert "running: value = compute()" in text
    assert "print(value)" not in text


def test_a_failure_with_no_cell_still_prints_the_file():
    text = str(Failure(path=Path("a.ipynb"), cell=None, error="the kernel died"))
    assert text == "a.ipynb: the kernel died"


def test_the_readable_error_keeps_the_last_line_that_says_anything():
    message = "Traceback...\n  File ...\n    raise\n\nValueError: the actual problem\n\n"
    assert _readable(message) == "ValueError: the actual problem"


def test_an_error_with_nothing_in_it_still_says_something():
    assert _readable("\n\n  \n") == "the cell failed with no message"
