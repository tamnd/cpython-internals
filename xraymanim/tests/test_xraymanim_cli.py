"""The command, and the one bit of it that a page depends on.

`alt` exists so that the markdown for showing an animation is generated rather than typed,
because the checker compares what is on the page against the catalogue and typing it is a
slow way of finding out you should have copied it. So the thing worth testing here is that
what the command prints is what the checker accepts.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from xraymanim import cli
from xraymanim.catalogue import ANIMATIONS
from xraymanim.render import figure, markdown

ROOT = Path(__file__).resolve().parents[2]


def test_alt_prints_one_line_per_animation(capsys):
    assert cli.main(["alt"]) == 0
    assert len(capsys.readouterr().out.strip().splitlines()) == len(ANIMATIONS)


def test_alt_for_one_animation_prints_only_that_one(capsys):
    assert cli.main(["alt", "a01-seven-stages"]) == 0
    printed = capsys.readouterr().out
    assert "a01-seven-stages.gif" in printed
    assert "a02" not in printed


def test_what_alt_prints_is_what_the_page_already_says(capsys):
    """The loop closed. If these ever disagree, one of the two is wrong and both look fine."""
    cli.main(["alt"])
    page = (ROOT / "anim" / "README.md").read_text(encoding="utf-8")
    for line in capsys.readouterr().out.strip().splitlines():
        assert line in page, line


def test_the_markdown_links_the_raw_file_rather_than_a_relative_path():
    """A notebook opened in Colab has the notebook and nothing else, so relative paths break."""
    assert markdown("a01-seven-stages", "some words").startswith("![some words](https://")


def test_check_passes_on_the_repository(capsys):
    assert cli.main(["check", "--root", str(ROOT)]) == 0


def test_list_says_how_long_the_whole_set_takes(capsys):
    assert cli.main(["list"]) == 0
    assert "minutes to watch" in capsys.readouterr().out


def test_figure_hands_a_lesson_the_catalogue_alt_text():
    """A lesson does not get to describe an animation differently from the page showing it."""
    storyboard = ANIMATIONS[0]
    assert figure(storyboard.slug) == markdown(storyboard.slug, storyboard.alt)


def test_figure_refuses_an_animation_nobody_has_rendered(tmp_path):
    """A missing GIF should fail the lesson build, not publish a notebook with a hole in it."""
    with pytest.raises(FileNotFoundError):
        figure(ANIMATIONS[0].slug, root=tmp_path)


def test_figure_refuses_a_slug_that_is_not_an_animation():
    with pytest.raises(KeyError):
        figure("a99-never-made")


def test_the_lesson_that_shows_a06_is_the_lesson_a06_was_written_for():
    """Both ends of the link, so a lesson cannot quietly borrow another lesson's animation."""
    build = ROOT / "lessons" / "t05-the-tree-becomes-bytecode" / "build.py"
    shown = [one for one in ANIMATIONS if one.slug in build.read_text(encoding="utf-8")]
    assert [one.lesson for one in shown] == ["T05"]
