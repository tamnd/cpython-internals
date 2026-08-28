from __future__ import annotations

from notebook_fixtures import BADGE, INSTALL, clean_cells, code, markdown, write

from nbcheck import load
from nbcheck.rules import check


def problems(path, root, rule=None):
    found = check(load(path), root)
    return [problem for problem in found if rule is None or problem.rule == rule]


def test_a_notebook_that_follows_every_rule_reports_nothing(clean, root):
    assert problems(clean, root) == []


def test_a_missing_badge_is_caught(clean, root):
    cells = clean_cells()
    cells[0] = markdown("# A lesson\n")
    write(clean, cells)
    assert [p.rule for p in problems(clean, root)] == ["badge"]


def test_a_badge_pointing_at_another_notebook_is_caught(clean, root):
    """The easiest mistake in the project: copy the previous lesson and forget the link."""
    cells = clean_cells()
    cells[0] = markdown(BADGE.replace("lessons/t01/t01.ipynb", "lessons/t02/t02.ipynb"))
    write(clean, cells)
    found = problems(clean, root, "badge")
    assert len(found) == 1
    assert "lessons/t01/t01.ipynb" in found[0].message


def test_a_relative_notebook_path_and_an_absolute_root_still_line_up(clean, root, monkeypatch):
    """How the command is actually used: walked paths are relative, the root flag is not."""
    monkeypatch.chdir(root)
    relative = clean.relative_to(root)
    assert check(load(relative), root) == []


def test_a_badge_below_the_fold_does_not_count(clean, root):
    cells = clean_cells()
    cells.insert(0, markdown("# A lesson\n"))
    write(clean, cells)
    assert [p.rule for p in problems(clean, root, "badge")] == ["badge"]


def test_a_notebook_with_no_cells_is_caught_rather_than_crashing(clean, root):
    write(clean, [])
    assert "no cells" in problems(clean, root, "badge")[0].message


def test_a_notebook_that_starts_with_code_is_caught(clean, root):
    write(clean, [code("import pyxray\n\npyxray.show()\n")])
    assert "must be markdown" in problems(clean, root, "badge")[0].message


def test_a_notebook_with_no_install_cell_is_caught(clean, root):
    """Colab has no pyxray, so a notebook without this raises ImportError on cell two."""
    cells = [cell for cell in clean_cells() if "pip install" not in str(cell["source"])]
    write(clean, cells)
    assert "no cell installs pyxray" in problems(clean, root, "setup")[0].message


def test_installing_from_pypi_rather_than_this_repository_is_caught(clean, root):
    cells = clean_cells()
    cells[2] = code("%pip install -q pyxray\n")
    write(clean, cells)
    assert "tamnd/cpython-internals" in problems(clean, root, "setup")[0].message


def test_a_notebook_that_never_prints_the_build_banner_is_caught(clean, root):
    cells = clean_cells()
    cells[4] = code("import pyxray\n")
    write(clean, cells)
    assert "pyxray.show()" in problems(clean, root, "banner")[0].message


def test_a_banner_buried_below_the_third_code_cell_is_caught(clean, root):
    """It has to come before the observations, or the reader attributes them to the wrong build."""
    cells = clean_cells()
    cells[4] = code("import pyxray\n")
    cells.extend([markdown("a"), code("x = 1"), markdown("b"), code("pyxray.show()")])
    write(clean, cells)
    assert [p.rule for p in problems(clean, root, "banner")] == ["banner"]


def test_a_notebook_with_no_code_at_all_is_caught(clean, root):
    write(clean, [markdown(BADGE), markdown("just prose")])
    rules = {p.rule for p in problems(clean, root)}
    assert "banner" in rules


def test_a_code_cell_with_no_markdown_before_it_is_caught(clean, root):
    """This is the rule that separates a lesson from a script with comments in it."""
    cells = clean_cells()
    cells.append(code("print('and one more thing')\n"))
    write(clean, cells)
    found = problems(clean, root, "introduced")
    assert len(found) == 1
    assert found[0].cell == len(cells)


def test_an_empty_cell_is_caught_and_does_not_also_need_an_introduction(clean, root):
    cells = clean_cells()
    cells.append(code(""))
    write(clean, cells)
    rules = [p.rule for p in problems(clean, root)]
    assert rules == ["empty"]


def test_a_stored_output_is_caught(clean, root):
    """Committed output goes stale silently, and the reader has no way to tell."""
    cells = clean_cells()
    cells[6] = code(
        "answer = 6 * 7\nprint(answer)\n",
        outputs=[{"output_type": "stream", "name": "stdout", "text": ["42\n"]}],
        count=1,
    )
    write(clean, cells)
    found = problems(clean, root, "outputs")
    assert len(found) == 1
    assert "strip it" in found[0].message


def test_an_execution_count_left_behind_is_caught_even_with_no_output(clean, root):
    cells = clean_cells()
    cells[6] = code("answer = 6 * 7\n", count=3)
    write(clean, cells)
    assert "execution count" in problems(clean, root, "outputs")[0].message


def test_an_em_dash_in_prose_is_caught(clean, root):
    cells = clean_cells()
    cells[5] = markdown("And here is the line \u2014 the whole lesson is about it.\n")
    write(clean, cells)
    assert "em dash" in problems(clean, root, "punctuation")[0].message


def test_an_en_dash_in_prose_is_caught(clean, root):
    cells = clean_cells()
    cells[5] = markdown("Stages one \u2013 seven.\n")
    write(clean, cells)
    assert "en dash" in problems(clean, root, "punctuation")[0].message


def test_punctuation_in_code_is_left_alone(clean, root):
    """A dash inside a string literal is data, not prose, and the rule must not guess."""
    cells = clean_cells()
    cells[6] = code('print("\u2014")\n')
    write(clean, cells)
    assert problems(clean, root, "punctuation") == []


def test_a_cell_with_no_id_is_caught(clean, root):
    """nbformat 4.5 made ids part of the format, and a file without them fails validation."""
    cells = clean_cells()
    del cells[3]["id"]
    write(clean, cells)
    assert "no id" in problems(clean, root, "id")[0].message


def test_two_cells_sharing_an_id_are_caught(clean, root):
    """The usual cause is a cell duplicated by hand rather than in an editor."""
    cells = clean_cells()
    cells[5]["id"] = cells[3]["id"]
    write(clean, cells)
    found = problems(clean, root, "id")
    assert len(found) == 1
    assert "already used by cell 4" in found[0].message


def test_a_kernel_colab_does_not_have_is_caught(clean, root):
    write(clean, clean_cells(), kernel="python314")
    assert "only offers python3" in problems(clean, root, "kernel")[0].message


def test_a_problem_prints_the_file_the_cell_and_the_rule(clean, root):
    cells = clean_cells()
    cells.append(code("print('extra')\n"))
    write(clean, cells)
    text = str(problems(clean, root, "introduced")[0])
    assert "t01.ipynb:cell 8" in text
    assert text.endswith("[introduced]")


def test_a_problem_with_no_cell_still_prints_the_file(clean, root):
    write(clean, clean_cells(), kernel="deno")
    text = str(problems(clean, root, "kernel")[0])
    assert "t01.ipynb:" in text
    assert ":cell" not in text


def test_the_install_cell_is_allowed_to_be_the_only_use_of_the_repository_name(clean, root):
    assert INSTALL.count("tamnd/cpython-internals") == 1
