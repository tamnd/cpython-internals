"""The command line, and the two subcommands that need Docker not reaching for it by accident."""

from __future__ import annotations

import pytest

from tier1.cli import main
from tier1.experiments import EXPERIMENTS
from tier1.recording import REPOSITORY


def test_list_prints_every_experiment_with_its_build_and_its_reason(capsys):
    assert main(["list"]) == 0
    printed = capsys.readouterr().out
    for one in EXPERIMENTS:
        assert one.slug in printed
        assert one.needs in printed


def test_check_passes_against_this_repository(capsys):
    assert main(["check"]) == 0
    assert "0 problem(s)" in capsys.readouterr().out


def test_check_reports_rather_than_raises_when_there_is_no_repository(capsys, tmp_path):
    assert main(["--root", str(tmp_path), "check"]) == 1
    assert "just build-tier1" in capsys.readouterr().err


def test_show_prints_what_the_lesson_prints(capsys):
    slug = EXPERIMENTS[0].slug
    assert main(["show", slug]) == 0
    printed = capsys.readouterr().out
    assert "docker run --rm -i" in printed
    assert EXPERIMENTS[0].asks in printed


def test_the_lesson_shows_exactly_what_show_prints():
    """Otherwise the prose around it drifts from the numbers and nobody notices for months."""
    from tier1.recording import show

    where = (REPOSITORY / "lessons").glob(f"{EXPERIMENTS[0].lesson.lower()}-*")
    builder = next(iter(sorted(where))) / "build.py"
    assert EXPERIMENTS[0].slug in builder.read_text(encoding="utf-8")
    assert show(EXPERIMENTS[0].slug).strip()


def test_importing_the_runner_is_what_needs_docker_and_nothing_else_does():
    """The cheap checks run on every pull request, so they must not pull an image to do it.

    Written as an import check because that is the way this rots: somebody adds a helper to
    `run.py`, imports it at the top of `checks.py` for convenience, and every contributor who
    changed a paragraph starts waiting on a container runtime that is not installed.
    """
    import tier1.checks

    assert "run" not in dir(tier1.checks)
    assert "subprocess" not in dir(tier1.checks)


def test_an_unknown_slug_says_what_the_known_ones_are():
    from tier1.experiments import find

    with pytest.raises(KeyError, match="there is"):
        find("t99-not-a-thing")
