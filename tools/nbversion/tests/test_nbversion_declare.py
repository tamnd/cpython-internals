"""Reading the note off a cell, including all the ways a cell might not have one.

Two keys live in the namespace, and reading one must never pick up the other. A `varies`
note read as a `differs` note would be checked against the two recordings and go stale on
whichever machine happened to run them.
"""

from __future__ import annotations

import json

from nbversion.declare import DIFFERS, NAMESPACE, VARIES, all_notes, note, notes


def cell(identifier, body=None):
    metadata = {} if body is None else {NAMESPACE: body}
    return {"cell_type": "code", "id": identifier, "metadata": metadata, "source": []}


def notebook(tmp_path, cells, name="t01.ipynb"):
    path = tmp_path / name
    path.write_text(json.dumps({"cells": cells, "nbformat": 4}), encoding="utf-8")
    return path


def test_a_cell_with_a_note_gives_the_sentence_back():
    assert note(cell("t01-01", {DIFFERS: "3.14 prints two lines."})) == "3.14 prints two lines."


def test_a_cell_with_no_metadata_at_all_has_no_note():
    assert note({"cell_type": "code"}) == ""


def test_a_cell_with_metadata_but_not_ours_has_no_note():
    assert note({"metadata": {"collapsed": True}}) == ""


def test_our_namespace_without_the_key_is_not_a_note():
    assert note(cell("t01-01", {"other": "x"})) == ""


def test_a_note_that_is_only_whitespace_is_not_a_note():
    assert note(cell("t01-01", {DIFFERS: "   "})) == ""


def test_a_namespace_that_is_not_a_mapping_is_ignored_rather_than_crashing():
    """A notebook that has been through some other tool, rather than one we wrote."""
    assert note({"metadata": {NAMESPACE: "yes"}}) == ""


def test_a_note_is_stripped():
    assert note(cell("t01-01", {DIFFERS: "  spaced  "})) == "spaced"


def test_reading_a_notebook_gives_only_the_cells_that_carry_a_note(tmp_path):
    path = notebook(
        tmp_path,
        [cell("t01-01"), cell("t01-02", {DIFFERS: "differs"}), cell("t01-03")],
    )
    assert notes(path) == {"t01-02": "differs"}


def test_a_cell_with_a_note_and_no_id_is_skipped(tmp_path):
    """There is nothing to key it on, and every cell we generate has one."""
    path = notebook(tmp_path, [{"metadata": {NAMESPACE: {DIFFERS: "differs"}}}])
    assert notes(path) == {}


def test_a_notebook_with_no_notes_reads_as_an_empty_mapping(tmp_path):
    assert notes(notebook(tmp_path, [cell("t01-01")])) == {}


def test_several_notebooks_are_keyed_by_file_name(tmp_path):
    first = notebook(tmp_path, [cell("t01-01", {DIFFERS: "a"})], name="t01.ipynb")
    second = notebook(tmp_path, [cell("t02-01")], name="t02.ipynb")
    assert all_notes([first, second]) == {"t01.ipynb": {"t01-01": "a"}, "t02.ipynb": {}}


def test_the_two_kinds_of_note_do_not_read_as_each_other():
    machine = cell("t01-01", {VARIES: "Depends how your Python was built."})
    assert note(machine) == ""
    assert note(machine, VARIES) == "Depends how your Python was built."


def test_reading_a_notebook_for_varies_skips_the_differs_cells(tmp_path):
    path = notebook(
        tmp_path,
        [cell("t01-01", {DIFFERS: "version"}), cell("t01-02", {VARIES: "machine"})],
    )
    assert notes(path) == {"t01-01": "version"}
    assert notes(path, VARIES) == {"t01-02": "machine"}


def test_all_notes_takes_the_kind_too(tmp_path):
    path = notebook(tmp_path, [cell("t01-01", {VARIES: "machine"})], name="t01.ipynb")
    assert all_notes([path], VARIES) == {"t01.ipynb": {"t01-01": "machine"}}
