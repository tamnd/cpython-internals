"""Tests for nbcheck's command line.

Named test_command rather than test_cli because pytest imports test modules by basename,
and refcheck's tests already have a test_cli. Two of them collide, and the error names
neither package.
"""

from __future__ import annotations

import pytest
from notebook_fixtures import clean_cells, code, write

from nbcheck.cli import main


def test_a_clean_notebook_exits_zero(clean, root, capsys):
    assert main(["lint", str(clean), "--root", str(root)]) == 0
    assert "1 notebook(s): 0 problem(s)" in capsys.readouterr().out


def test_a_notebook_with_a_problem_exits_one(clean, root, capsys):
    cells = clean_cells()
    cells.append(code("print('extra')\n"))
    write(clean, cells)
    assert main(["lint", str(clean), "--root", str(root)]) == 1
    captured = capsys.readouterr()
    assert "1 notebook(s): 1 problem(s)" in captured.out
    assert "[introduced]" in captured.err


def test_a_directory_is_walked(clean, root, capsys):
    write(root / "lessons" / "t02" / "t02.ipynb", clean_cells())
    main(["lint", str(root / "lessons"), "--root", str(root)])
    assert "2 notebook(s)" in capsys.readouterr().out


def test_a_file_that_is_not_a_notebook_exits_one_rather_than_raising(root, capsys):
    path = root / "notes.ipynb"
    path.write_text("not json", encoding="utf-8")
    assert main(["lint", str(path), "--root", str(root)]) == 1
    assert "not valid JSON" in capsys.readouterr().err


def test_finding_no_notebooks_is_reported_but_is_not_a_failure(root, capsys):
    """An empty lessons directory is the state the repository starts in, not a broken one."""
    (root / "lessons").mkdir()
    assert main(["lint", str(root / "lessons")]) == 0
    assert "no notebooks found" in capsys.readouterr().err


def test_no_subcommand_is_a_usage_error_and_not_a_pass(capsys):
    """Exit 2 rather than 0, because CI must not read a misused command as a clean run."""
    with pytest.raises(SystemExit) as caught:
        main([])
    assert caught.value.code == 2


def test_an_unknown_subcommand_is_a_usage_error(capsys):
    with pytest.raises(SystemExit) as caught:
        main(["frobnicate"])
    assert caught.value.code == 2


def test_the_default_path_is_the_lessons_directory():
    from nbcheck.cli import DEFAULT_ROOTS

    assert DEFAULT_ROOTS == ["lessons"]


def test_run_reports_when_there_is_nothing_to_run(root, capsys):
    (root / "lessons").mkdir()
    assert main(["run", str(root / "lessons")]) == 0
    assert "no notebooks found" in capsys.readouterr().err
