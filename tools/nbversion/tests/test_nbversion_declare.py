"""Reading the note off a cell, including all the ways a cell might not have one."""

from __future__ import annotations

import json

from nbversion.declare import KEY, NAMESPACE, all_notes, note, notes


def cell(identifier, body=None):
    metadata = {} if body is None else {NAMESPACE: body}
    return {"cell_type": "code", "id": identifier, "metadata": metadata, "source": []}


def notebook(tmp_path, cells, name="t01.ipynb"):
    path = tmp_path / name
    path.write_text(json.dumps({"cells": cells, "nbformat": 4}), encoding="utf-8")
    return path


def test_a_cell_with_a_note_gives_the_sentence_back():
    assert note(cell("t01-01", {KEY: "3.14 prints two lines."})) == "3.14 prints two lines."


def test_a_cell_with_no_metadata_at_all_has_no_note():
    assert note({"cell_type": "code"}) == ""


def test_a_cell_with_metadata_but_not_ours_has_no_note():
    assert note({"metadata": {"collapsed": True}}) == ""


def test_our_namespace_without_the_key_is_not_a_note():
    assert note(cell("t01-01", {"other": "x"})) == ""


def test_a_note_that_is_only_whitespace_is_not_a_note():
    assert note(cell("t01-01", {KEY: "   "})) == ""


def test_a_namespace_that_is_not_a_mapping_is_ignored_rather_than_crashing():
    """A notebook that has been through some other tool, rather than one we wrote."""
    assert note({"metadata": {NAMESPACE: "yes"}}) == ""


def test_a_note_is_stripped():
    assert note(cell("t01-01", {KEY: "  spaced  "})) == "spaced"


def test_reading_a_notebook_gives_only_the_cells_that_carry_a_note(tmp_path):
    path = notebook(
        tmp_path,
        [cell("t01-01"), cell("t01-02", {KEY: "differs"}), cell("t01-03")],
    )
    assert notes(path) == {"t01-02": "differs"}


def test_a_cell_with_a_note_and_no_id_is_skipped(tmp_path):
    """There is nothing to key it on, and every cell we generate has one."""
    path = notebook(tmp_path, [{"metadata": {NAMESPACE: {KEY: "differs"}}}])
    assert notes(path) == {}


def test_a_notebook_with_no_notes_reads_as_an_empty_mapping(tmp_path):
    assert notes(notebook(tmp_path, [cell("t01-01")])) == {}


def test_several_notebooks_are_keyed_by_file_name(tmp_path):
    first = notebook(tmp_path, [cell("t01-01", {KEY: "a"})], name="t01.ipynb")
    second = notebook(tmp_path, [cell("t02-01")], name="t02.ipynb")
    assert all_notes([first, second]) == {"t01.ipynb": {"t01-01": "a"}, "t02.ipynb": {}}
