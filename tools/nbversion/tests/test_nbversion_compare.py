"""The four verdicts, and which of them stop the build.

The one that is easy to leave out is `stale`. It is tempting to treat a note as harmless
once the difference goes away, and it is not: a reader who checks a note against their own
interpreter, finds it wrong, and concludes the notes are decoration has been actively
misled by the thing that was supposed to help them.
"""

from __future__ import annotations

from nbversion.compare import DECLARED, MISSING, STALE, UNDECLARED, cells, notebooks, summary
from nbversion.record import Recording


def recording(cells_, python="3.15", name="t01.ipynb"):
    return Recording(notebook=name, python=python, cells=cells_)


def kinds(findings):
    return [one.kind for one in findings]


def test_two_identical_recordings_have_nothing_to_say():
    one = recording({"t01-01": "hi"})
    assert cells(one, recording({"t01-01": "hi"}, python="3.14"), {}) == []


def test_a_difference_nobody_declared_is_a_failure():
    left, right = recording({"t01-01": "3"}), recording({"t01-01": "4"}, python="3.14")
    found = cells(left, right, {})
    assert kinds(found) == [UNDECLARED]
    assert found[0].failed


def test_a_declared_difference_is_reported_and_passes():
    left, right = recording({"t01-01": "3"}), recording({"t01-01": "4"}, python="3.14")
    found = cells(left, right, {"t01-01": "3.14 counts differently."})
    assert kinds(found) == [DECLARED]
    assert not found[0].failed
    assert found[0].detail == "3.14 counts differently."


def test_a_note_on_a_cell_that_no_longer_differs_is_a_failure():
    left, right = recording({"t01-01": "3"}), recording({"t01-01": "3"}, python="3.14")
    found = cells(left, right, {"t01-01": "3.14 counts differently."})
    assert kinds(found) == [STALE]
    assert found[0].failed


def test_a_note_on_a_cell_that_is_not_in_the_recording_is_ignored():
    """Notes are read from the notebook, which has markdown cells the recording does not."""
    left, right = recording({"t01-01": "3"}), recording({"t01-01": "3"}, python="3.14")
    assert cells(left, right, {"t01-99": "about a cell that was deleted"}) == []


def test_a_cell_recorded_on_only_one_side_is_a_failure():
    left = recording({"t01-01": "3", "t01-02": "4"})
    found = cells(left, recording({"t01-01": "3"}, python="3.14"), {})
    assert kinds(found) == [MISSING]
    assert "3.15" in found[0].detail


def test_the_diff_of_an_undeclared_difference_shows_both_versions():
    left, right = recording({"t01-01": "three"}), recording({"t01-01": "four"}, python="3.14")
    detail = cells(left, right, {})[0].detail
    assert "-three" in detail
    assert "+four" in detail
    assert "3.15" in detail and "3.14" in detail


def test_cells_are_reported_in_id_order():
    left = recording({"t01-03": "a", "t01-01": "b", "t01-02": "c"})
    right = recording({"t01-03": "x", "t01-01": "y", "t01-02": "z"}, python="3.14")
    assert [one.cell for one in cells(left, right, {})] == ["t01-01", "t01-02", "t01-03"]


def test_a_notebook_recorded_on_only_one_side_is_a_failure():
    found = notebooks({"t01.ipynb": recording({})}, {}, {})
    assert kinds(found) == [MISSING]
    assert found[0].notebook == "t01.ipynb"


def test_notebooks_are_compared_by_name_not_by_position():
    left = {"t02.ipynb": recording({"t02-01": "a"}, name="t02.ipynb")}
    right = {"t02.ipynb": recording({"t02-01": "b"}, python="3.14", name="t02.ipynb")}
    found = notebooks(left, right, {})
    assert kinds(found) == [UNDECLARED]
    assert found[0].notebook == "t02.ipynb"


def test_the_notes_for_one_notebook_do_not_apply_to_another():
    left = {
        "t01.ipynb": recording({"c": "a"}, name="t01.ipynb"),
        "t02.ipynb": recording({"c": "a"}, name="t02.ipynb"),
    }
    right = {
        "t01.ipynb": recording({"c": "b"}, python="3.14", name="t01.ipynb"),
        "t02.ipynb": recording({"c": "b"}, python="3.14", name="t02.ipynb"),
    }
    found = notebooks(left, right, {"t01.ipynb": {"c": "declared here only"}})
    assert kinds(found) == [DECLARED, UNDECLARED]


def test_a_finding_prints_the_notebook_and_the_cell():
    left, right = recording({"t01-01": "3"}), recording({"t01-01": "4"}, python="3.14")
    assert cells(left, right, {"t01-01": "note"})[0].line().startswith("t01.ipynb:t01-01  declared")


def test_the_summary_of_nothing_says_so():
    assert summary([]) == "no differences"


def test_the_summary_counts_each_kind():
    left = recording({"a": "1", "b": "1", "c": "1"})
    right = recording({"a": "2", "b": "2", "c": "1"}, python="3.14")
    found = cells(left, right, {"a": "declared", "c": "stale"})
    assert summary(found) == "1 declared, 1 undeclared, 1 stale"
