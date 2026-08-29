"""Executing a notebook and writing down what it printed.

Half of these start a real kernel, which makes them slow. They are not mocked because the
thing being tested is what a kernel does with a cell, and a mock has no opinion about that.
"""

from __future__ import annotations

import json

import pytest
from version_fixtures import code, markdown, notebook, recorded

from nbversion.record import Recording, load_all, run, version, write

pytest.importorskip("nbclient")
pytest.importorskip("ipykernel")


def test_the_version_is_the_two_numbers_that_matter():
    import sys

    assert version() == f"{sys.version_info.major}.{sys.version_info.minor}"


def test_a_recording_round_trips_through_json(tmp_path):
    one = Recording(notebook="t01.ipynb", python="3.15", cells={"a": "hi"})
    path = write(one, tmp_path)
    assert Recording.load(path) == one


def test_the_file_is_named_after_the_notebook(tmp_path):
    path = write(Recording(notebook="t07.ipynb", python="3.15", cells={}), tmp_path)
    assert path.name == "t07.json"


def test_the_directory_is_made_if_it_is_not_there(tmp_path):
    write(Recording(notebook="t01.ipynb", python="3.15", cells={}), tmp_path / "deep" / "down")
    assert (tmp_path / "deep" / "down" / "t01.json").exists()


def test_the_json_is_sorted_so_a_diff_is_about_the_outputs(tmp_path):
    path = write(Recording("t01.ipynb", "3.15", {"b": "2", "a": "1"}), tmp_path)
    body = json.loads(path.read_text(encoding="utf-8"))
    assert list(body["cells"]) == ["a", "b"]


def test_loading_a_directory_keys_the_recordings_by_notebook(tmp_path):
    recorded(tmp_path, "3.15", {"a": "1"}, name="t01.ipynb")
    recorded(tmp_path, "3.15", {"b": "2"}, name="t02.ipynb")
    assert sorted(load_all(tmp_path)) == ["t01.ipynb", "t02.ipynb"]


def test_loading_a_directory_with_nothing_in_it_finds_nothing(tmp_path):
    assert load_all(tmp_path) == {}


def test_running_a_notebook_records_what_each_cell_printed(tmp_path):
    path = notebook(
        tmp_path / "t01.ipynb",
        [code("print(6 * 7)\n", identifier="one"), code("print('hello')\n", identifier="two")],
    )
    one = run(path)
    assert one.cells == {"one": "42", "two": "hello"}


def test_markdown_cells_are_not_recorded(tmp_path):
    path = notebook(
        tmp_path / "t01.ipynb", [markdown("# Title\n"), code("print(1)\n", identifier="one")]
    )
    assert list(run(path).cells) == ["one"]


def test_a_cell_that_prints_nothing_records_the_empty_string(tmp_path):
    path = notebook(tmp_path / "t01.ipynb", [code("x = 1\n", identifier="one")])
    assert run(path).cells == {"one": ""}


def test_state_carries_between_cells(tmp_path):
    path = notebook(
        tmp_path / "t01.ipynb",
        [code("value = 42\n", identifier="one"), code("print(value)\n", identifier="two")],
    )
    assert run(path).cells["two"] == "42"


def test_a_cell_that_raises_is_recorded_rather_than_stopping_the_run(tmp_path):
    """`nbcheck run` is what fails on an accidental exception. Stopping here as well would
    mean one broken lesson hides every version difference in every lesson after it."""
    path = notebook(
        tmp_path / "t01.ipynb",
        [
            code("raise ValueError('nope')\n", identifier="one"),
            code("print(1)\n", identifier="two"),
        ],
    )
    one = run(path)
    assert one.cells["one"] == "ValueError: nope"
    assert one.cells["two"] == "1"


def test_an_address_in_the_output_is_normalised_away(tmp_path):
    path = notebook(tmp_path / "t01.ipynb", [code("print(object())\n", identifier="one")])
    assert run(path).cells["one"] == "<object object at 0xADDRESS>"


def test_the_recording_says_which_interpreter_made_it(tmp_path):
    path = notebook(tmp_path / "t01.ipynb", [code("print(1)\n", identifier="one")])
    assert run(path).python == version()


def test_the_notebook_on_disk_is_not_written_back_to(tmp_path):
    path = notebook(tmp_path / "t01.ipynb", [code("print(1)\n", identifier="one")])
    before = path.read_text(encoding="utf-8")
    run(path)
    assert path.read_text(encoding="utf-8") == before


def test_the_kernel_starts_in_the_notebooks_own_directory(tmp_path):
    (tmp_path / "lesson").mkdir()
    (tmp_path / "lesson" / "data.txt").write_text("42", encoding="utf-8")
    path = notebook(
        tmp_path / "lesson" / "reads.ipynb",
        [code("print(open('data.txt').read())\n", identifier="one")],
    )
    assert run(path).cells["one"] == "42"
