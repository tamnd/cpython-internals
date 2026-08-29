"""The command line, checked through its exit codes and what it prints."""

from __future__ import annotations

import pytest

from boss.cli import main
from boss.fights import REPOSITORY


@pytest.fixture
def room(tmp_path):
    """A fake repository with a fight that is missing everything."""
    (tmp_path / "lessons").mkdir()
    return tmp_path


def test_list_names_the_command_a_reader_would_actually_type(capsys):
    assert main(["list"]) == 0
    printed = capsys.readouterr().out
    assert "t05-the-tree-becomes-bytecode" in printed
    assert "python lessons/t05-the-tree-becomes-bytecode/grade.py answer.py" in printed


def test_check_passes_on_the_real_repository(capsys):
    assert main(["check"]) == 0
    assert "0 problem(s)" in capsys.readouterr().out


def test_check_fails_when_the_fight_is_not_there(capsys, room):
    assert main(["--root", str(room), "check"]) == 1
    said = capsys.readouterr()
    assert "the grader is missing" in said.err


def test_verify_runs_both_submissions_and_says_how_many_times(capsys):
    assert main(["verify"]) == 0
    assert "t05: 2 grading run(s) over 1 seed(s), 0 problem(s)" in capsys.readouterr().out


def test_verify_can_be_pointed_at_one_fight_by_name(capsys):
    assert main(["verify", "t05"]) == 0
    assert "t05:" in capsys.readouterr().out


def test_asking_for_a_fight_that_does_not_exist_is_a_different_exit_code(capsys):
    assert main(["verify", "t99"]) == 2
    assert "there is no t99 fight" in capsys.readouterr().err


def test_grade_passes_the_graders_own_exit_code_back(capsys):
    fight_good = REPOSITORY / "tools" / "boss" / "submissions" / "t05" / "good.py"
    assert main(["grade", "t05", str(fight_good)]) == 0
    assert "agree with CPython" in capsys.readouterr().out


def test_grade_prints_the_report_when_the_submission_is_wrong(capsys):
    bad = REPOSITORY / "tools" / "boss" / "submissions" / "t05" / "bad.py"
    assert main(["grade", "t05", str(bad)]) == 1
    assert "disagrees with CPython" in capsys.readouterr().out
