from __future__ import annotations

import json

import pytest

from nbbuild import Lesson, Malformed
from nbversion.declare import DIFFERS, NAMESPACE, VARIES


@pytest.fixture
def root(tmp_path):
    """A throwaway checkout, so a test never writes over a real lesson."""
    (tmp_path / "pyproject.toml").write_text("")
    (tmp_path / "lessons").mkdir()
    return tmp_path


def test_a_notebook_is_valid_json_with_the_cells_in_the_order_they_were_added(root):
    lesson = Lesson("t99-example", "t99", root=root)
    lesson.md("# Title")
    lesson.code("print(1)")
    book = json.loads(lesson.document())
    assert [cell["cell_type"] for cell in book["cells"]] == ["markdown", "code"]
    assert book["nbformat_minor"] == 5


def test_every_cell_gets_an_id_because_nbformat_45_refuses_a_notebook_without_them(root):
    """A missing id is a warning, and warnings are errors here, so it fails the whole run."""
    lesson = Lesson("t99-example", "t99", root=root)
    for _ in range(11):
        lesson.md("text")
    ids = [cell["id"] for cell in json.loads(lesson.document())["cells"]]
    assert ids[0] == "t99-01"
    assert ids[-1] == "t99-11"
    assert len(set(ids)) == len(ids)


def test_a_code_cell_carries_no_output_and_no_execution_count(root):
    """Outputs are never committed. A stored output is a screenshot that goes stale."""
    lesson = Lesson("t99-example", "t99", root=root)
    lesson.code("print(1)")
    cell = json.loads(lesson.document())["cells"][0]
    assert cell["outputs"] == []
    assert cell["execution_count"] is None


def test_a_plain_code_cell_carries_no_version_note(root):
    lesson = Lesson("t99-example", "t99", root=root)
    lesson.code("print(1)")
    assert json.loads(lesson.document())["cells"][0]["metadata"] == {}


def test_a_version_note_goes_in_the_cells_own_metadata(root):
    lesson = Lesson("t99-example", "t99", root=root)
    lesson.code("print(1)", differs="On 3.14 this prints nothing.")
    cell = json.loads(lesson.document())["cells"][0]
    assert cell["metadata"] == {NAMESPACE: {DIFFERS: "On 3.14 this prints nothing."}}


def test_a_version_note_also_comes_out_as_something_the_reader_can_see(root):
    """The metadata is for CI. A reader on Colab never opens it, so the note is said twice."""
    lesson = Lesson("t99-example", "t99", root=root)
    lesson.code("print(1)", differs="On 3.14 this prints nothing.")
    cells = json.loads(lesson.document())["cells"]
    assert [cell["cell_type"] for cell in cells] == ["code", "markdown"]
    assert cells[1]["source"] == ["> **Version note.** On 3.14 this prints nothing."]


def test_a_quiet_version_note_is_declared_without_a_cell_under_it(root):
    """For the lessons where one paragraph up top covers a difference a dozen cells show."""
    lesson = Lesson("t99-example", "t99", root=root)
    lesson.code("print(1)", differs="Offsets are 2 lower on 3.14.", quiet=True)
    cells = json.loads(lesson.document())["cells"]
    assert [cell["cell_type"] for cell in cells] == ["code"]
    assert cells[0]["metadata"] == {NAMESPACE: {DIFFERS: "Offsets are 2 lower on 3.14."}}


def test_a_version_note_goes_through_the_same_punctuation_check_as_the_prose(root):
    lesson = Lesson("t99-example", "t99", root=root)
    with pytest.raises(Malformed, match="em dash"):
        lesson.code("print(1)", differs="On 3.14 \u2014 nothing.")


def test_a_machine_note_goes_under_the_other_key(root):
    """Same sentence to a reader, different question to the checker."""
    lesson = Lesson("t99-example", "t99", root=root)
    lesson.code("print(1)", varies="How many files your standard library has.")
    cells = json.loads(lesson.document())["cells"]
    assert cells[0]["metadata"] == {
        NAMESPACE: {VARIES: "How many files your standard library has."}
    }
    assert cells[1]["source"] == ["> **Version note.** How many files your standard library has."]


def test_a_machine_note_can_be_quiet_too(root):
    lesson = Lesson("t99-example", "t99", root=root)
    lesson.code("print(1)", varies="Depends on the build.", quiet=True)
    cells = json.loads(lesson.document())["cells"]
    assert [cell["cell_type"] for cell in cells] == ["code"]


def test_a_machine_note_goes_through_the_punctuation_check_as_well(root):
    lesson = Lesson("t99-example", "t99", root=root)
    with pytest.raises(Malformed, match="em dash"):
        lesson.code("print(1)", varies="Your build \u2014 not the version.")


def test_a_cell_cannot_be_both_kinds_of_note(root):
    """One of the two is wrong, and guessing which would put the wrong thing in metadata."""
    lesson = Lesson("t99-example", "t99", root=root)
    with pytest.raises(Malformed, match="both differs and varies"):
        lesson.code("print(1)", differs="version", varies="machine")
    assert json.loads(lesson.document())["cells"] == []


def test_source_keeps_its_newlines_the_way_the_format_wants_them(root):
    lesson = Lesson("t99-example", "t99", root=root)
    lesson.code("one\ntwo")
    assert json.loads(lesson.document())["cells"][0]["source"] == ["one\n", "two"]


def test_the_badge_points_at_this_lesson_rather_than_the_one_it_was_copied_from(root):
    """The single easiest mistake in the project, removed by generating it from the path."""
    lesson = Lesson("t02-text-becomes-tokens", "t02", root=root)
    assert lesson.badge.endswith("lessons/t02-text-becomes-tokens/t02.ipynb)")


def test_a_citation_becomes_a_link_labelled_with_the_whole_citation(root):
    lesson = Lesson("t99-example", "t99", root=root)
    text = lesson.cite("Python/ceval.c:1213-1220@v3.15.0rc1#_PyEval_EvalFrameDefault")
    assert text.startswith("[Python/ceval.c:1213-1220@v3.15.0rc1#_PyEval_EvalFrameDefault](")
    assert "github.com/python/cpython" in text


def test_a_term_becomes_a_link_into_the_glossary(root):
    lesson = Lesson("t99-example", "t99", root=root)
    assert lesson.term("code object").endswith("/GLOSSARY.md#code-object)")


def test_a_term_can_be_worded_to_fit_the_sentence(root):
    lesson = Lesson("t99-example", "t99", root=root)
    assert lesson.term("oparg", "the argument byte").startswith("[the argument byte](")


def test_a_term_nobody_defined_fails_while_the_lesson_is_being_built(root):
    # Better than shipping a link that lands at the top of the glossary and looks fine.
    lesson = Lesson("t99-example", "t99", root=root)
    with pytest.raises(KeyError):
        lesson.term("monad")


@pytest.mark.parametrize("dash", ["\u2014", "\u2013"])
def test_prose_containing_a_dash_the_project_does_not_use_is_rejected(root, dash):
    """Invisible in a diff, so it is caught here rather than in review, where it never was."""
    lesson = Lesson("t99-example", "t99", root=root)
    with pytest.raises(Malformed):
        lesson.md(f"one thing {dash} another")


def test_an_empty_cell_is_rejected(root):
    lesson = Lesson("t99-example", "t99", root=root)
    with pytest.raises(Malformed):
        lesson.md("   \n\n  ")


def test_saving_writes_the_notebook_and_says_where_it_went(root, capsys):
    lesson = Lesson("t99-example", "t99", root=root)
    lesson.md("# Title")
    assert lesson.save([]) == 0
    assert lesson.path.exists()
    assert "t99.ipynb" in capsys.readouterr().out


def test_checking_passes_when_the_committed_notebook_matches_the_builder(root):
    lesson = Lesson("t99-example", "t99", root=root)
    lesson.md("# Title")
    lesson.save([])
    assert lesson.save(["--check"]) == 0


def test_checking_fails_when_somebody_edited_the_notebook_instead_of_the_builder(root, capsys):
    """The whole reason the command exists: generated and committed drifts unless checked."""
    lesson = Lesson("t99-example", "t99", root=root)
    lesson.md("# Title")
    lesson.save([])
    lesson.path.write_text(lesson.path.read_text().replace("Title", "Edited by hand"))
    assert lesson.save(["--check"]) == 1
    assert "does not match its builder" in capsys.readouterr().out


def test_checking_a_notebook_that_was_never_built_fails_rather_than_passing_quietly(root):
    lesson = Lesson("t99-example", "t99", root=root)
    lesson.md("# Title")
    assert lesson.save(["--check"]) == 1


def test_checking_never_writes_anything(root):
    lesson = Lesson("t99-example", "t99", root=root)
    lesson.md("# Title")
    lesson.save(["--check"])
    assert not lesson.path.exists()


def test_building_the_same_lesson_twice_produces_the_identical_file(root):
    """If the output were not stable, `nbbuild check` would fail at random."""

    def build():
        lesson = Lesson("t99-example", "t99", root=root)
        lesson.md("# Title")
        lesson.code("print(1)")
        return lesson.document()

    assert build() == build()


def test_the_file_ends_with_a_newline_like_every_other_text_file_in_the_repo(root):
    lesson = Lesson("t99-example", "t99", root=root)
    lesson.md("# Title")
    assert lesson.document().endswith("}\n")
