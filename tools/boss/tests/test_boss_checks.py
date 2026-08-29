"""The checks that do not run anything.

Most of these build a fake repository with the t05 fight in it, break exactly one thing, and
insist the break is what gets reported. The last one points at the real repository, which is
the check that keeps this file from testing only itself.
"""

from __future__ import annotations

import pytest

from boss import find, problems
from boss.checks import defines, imports, stdlib_only
from boss.fights import REPOSITORY

ANSWER = '''"""A submission."""


def predict(source: str) -> tuple[str, ...]:
    return ()
'''

GRADER = '''"""A grader."""

import ast
import sys
from pathlib import Path
'''

BUILDER = '''"""A lesson builder that sends the reader to grade.py."""
'''


@pytest.fixture
def room(tmp_path):
    """A fake repository with the t05 fight fully assembled in it."""
    fight = find("t05")
    lesson = tmp_path / "lessons" / fight.lesson
    (lesson / "boss").mkdir(parents=True)
    (lesson / "grade.py").write_text(GRADER, encoding="utf-8")
    (lesson / "boss" / "starter.py").write_text(ANSWER, encoding="utf-8")
    (lesson / "build.py").write_text(BUILDER, encoding="utf-8")
    submissions = tmp_path / "tools" / "boss" / "submissions" / fight.code
    submissions.mkdir(parents=True)
    (submissions / "good.py").write_text(ANSWER, encoding="utf-8")
    (submissions / "bad.py").write_text(ANSWER + "\n# and wrong\n", encoding="utf-8")
    (submissions / "expected.txt").write_text("disagrees with CPython\n", encoding="utf-8")
    return tmp_path


def test_an_assembled_fight_has_nothing_wrong_with_it(room):
    assert problems(room) == []


def test_a_missing_file_is_named_along_with_where_it_should_have_been(room):
    find("t05").good(room).unlink()
    found = problems(room)
    assert len(found) == 1
    assert "good submission is missing" in found[0]
    assert "submissions/t05/good.py" in found[0]


def test_a_missing_file_stops_the_checks_that_would_have_read_it(room):
    find("t05").expected(room).unlink()
    # One complaint, not two. The empty expected.txt check reads the file that is not there.
    assert len(problems(room)) == 1


def test_a_submission_without_predict_is_reported(room):
    find("t05").bad(room).write_text("def guess():\n    pass\n", encoding="utf-8")
    assert problems(room) == ["t05: the bad submission does not define predict()"]


def test_the_bad_submission_being_a_copy_of_the_good_one_is_reported(room):
    find("t05").bad(room).write_text(ANSWER, encoding="utf-8")
    assert problems(room) == ["t05: the good and bad submissions are the same file"]


def test_an_empty_expected_report_is_reported(room):
    find("t05").expected(room).write_text("\n\n", encoding="utf-8")
    assert "expected.txt is empty" in problems(room)[0]


def test_a_grader_that_needs_an_install_is_reported(room):
    find("t05").grader(room).write_text("import numpy\nimport ast\n", encoding="utf-8")
    found = problems(room)
    assert len(found) == 1
    assert "imports numpy, which a reader may not have" in found[0]


def test_a_lesson_that_never_mentions_the_grader_is_reported(room):
    find("t05").builder(room).write_text('"""A lesson about something else."""\n', encoding="utf-8")
    assert problems(room) == [
        "t05: lessons/t05-the-tree-becomes-bytecode/build.py never mentions grade.py"
    ]


def test_a_lesson_that_is_not_there_at_all_is_reported(room):
    find("t05").builder(room).unlink()
    assert "there is no lessons/t05-the-tree-becomes-bytecode/build.py" in problems(room)[0]


def test_imports_finds_the_top_level_name_of_each_one():
    source = "import os\nimport os.path\nimport numpy as np\nfrom json.decoder import JSONDecoder\n"
    assert imports(source) == ["os", "os", "numpy", "json"]


def test_imports_ignores_a_relative_one_because_it_names_no_module():
    assert imports("from . import fights\nfrom .run import graded\n") == []


def test_stdlib_only_says_nothing_about_a_file_that_imports_nothing(tmp_path):
    where = tmp_path / "plain.py"
    where.write_text("x = 1\n", encoding="utf-8")
    assert stdlib_only(where, tmp_path) == []


def test_defines_only_looks_at_the_top_level(tmp_path):
    where = tmp_path / "nested.py"
    where.write_text("class Thing:\n    def predict(self):\n        pass\n", encoding="utf-8")
    assert not defines(where, "predict")


def test_the_real_repository_passes():
    assert problems(REPOSITORY) == []
