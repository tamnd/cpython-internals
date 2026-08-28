from __future__ import annotations

import json

import pytest

from nbbuild import Lesson, Malformed


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
