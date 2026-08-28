from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

import nbbuild
from nbbuild import cli

SCRIPT = """
import sys
from pathlib import Path

sys.path.insert(0, {package!r})
from nbbuild import Lesson

lesson = Lesson({slug!r}, {stem!r}, root=Path(__file__).resolve().parents[2])
lesson.md("# Title")
raise SystemExit(lesson.save())
"""

LESSONS = [("t01-first", "t01"), ("t02-second", "t02")]


@pytest.fixture
def checkout(tmp_path):
    """A throwaway checkout with two builders in it, run as real subprocesses.

    The builders import nbbuild off the path this test process found it on, because a
    subprocess started with plain `sys.executable` does not inherit the editable install.
    """
    package = str(Path(nbbuild.__file__).resolve().parents[1])
    (tmp_path / "pyproject.toml").write_text("")
    for slug, stem in LESSONS:
        directory = tmp_path / "lessons" / slug
        directory.mkdir(parents=True)
        (directory / "build.py").write_text(
            textwrap.dedent(SCRIPT).format(package=package, slug=slug, stem=stem)
        )
    return tmp_path / "lessons"


def test_builders_are_found_in_lesson_order(checkout):
    """Path order is also reading order for t01, t02, so a failing run stays readable."""
    assert [path.parent.name for path in cli.builders(checkout)] == ["t01-first", "t02-second"]


def test_a_directory_with_no_builders_reports_that_rather_than_passing_silently(tmp_path, capsys):
    assert cli.main(["build", "--root", str(tmp_path)]) == 0
    assert "no build.py" in capsys.readouterr().err


def test_build_writes_every_notebook(checkout):
    assert cli.main(["build", "--root", str(checkout)]) == 0
    assert (checkout / "t01-first" / "t01.ipynb").exists()
    assert (checkout / "t02-second" / "t02.ipynb").exists()


def test_check_passes_straight_after_a_build(checkout):
    cli.main(["build", "--root", str(checkout)])
    assert cli.main(["check", "--root", str(checkout)]) == 0


def test_check_fails_before_anything_has_been_built(checkout):
    assert cli.main(["check", "--root", str(checkout)]) == 1


def test_check_reports_every_lesson_that_drifted_rather_than_stopping_at_the_first(
    checkout, capsys
):
    cli.main(["build", "--root", str(checkout)])
    for slug, stem in LESSONS:
        path = checkout / slug / f"{stem}.ipynb"
        path.write_text(path.read_text().replace("Title", "Edited"))
    assert cli.main(["check", "--root", str(checkout)]) == 1
    assert "2 lesson(s): 2 failed" in capsys.readouterr().out


def test_the_command_requires_a_subcommand():
    """Exiting 2 for misuse, so CI cannot mistake a typo for a check that found nothing."""
    with pytest.raises(SystemExit) as caught:
        cli.main([])
    assert caught.value.code == 2
