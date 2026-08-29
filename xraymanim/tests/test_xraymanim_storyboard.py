"""One test per rule, each one breaking exactly one thing in a storyboard that was fine."""

from __future__ import annotations

from dataclasses import replace

from xraymanim.grammar import CAP_SECONDS
from xraymanim.storyboard import Beat, Storyboard

CLEAN = Storyboard(
    slug="a99-a-demo",
    title="A demo that only exists in the tests",
    lesson="T99",
    shapes=("box", "arrow", "PyObjectBox"),
    beats=(
        Beat("Something happens.", 4.0),
        Beat("Then something else happens.", 4.0),
        Beat("Then it stops.", 4.0),
    ),
)


def test_a_clean_storyboard_has_nothing_wrong_with_it():
    assert CLEAN.problems() == []


def test_the_length_is_the_sum_of_the_beats():
    assert CLEAN.seconds == 12.0


def test_the_captions_come_back_in_order():
    assert CLEAN.captions[0] == "Something happens."
    assert len(CLEAN.captions) == len(CLEAN.beats)


def test_a_slug_that_is_not_numbered():
    broken = replace(CLEAN, slug="a-demo")
    assert broken.problems() == ["a-demo: the slug should look like a01-what-it-shows"]


def test_an_empty_title():
    assert "the title is empty" in " ".join(replace(CLEAN, title="  ").problems())


def test_an_em_dash_in_the_title():
    broken = replace(CLEAN, title="A demo \u2014 in the tests")
    assert "em dash" in " ".join(broken.problems())


def test_no_lesson():
    assert "which lesson" in " ".join(replace(CLEAN, lesson="").problems())


def test_two_beats_is_a_slide():
    """The line between an animation and a slide, and the slide should be a still picture."""
    broken = replace(CLEAN, beats=CLEAN.beats[:2])
    assert "slide rather than an animation" in " ".join(broken.problems())


def test_an_empty_caption():
    broken = replace(CLEAN, beats=(Beat("", 4.0), *CLEAN.beats))
    assert "the caption is empty" in " ".join(broken.problems())


def test_a_caption_with_a_line_break_in_it():
    broken = replace(CLEAN, beats=(Beat("One line.\nTwo lines.", 4.0), *CLEAN.beats))
    assert "line break" in " ".join(broken.problems())


def test_a_caption_that_wraps_onto_the_picture():
    broken = replace(CLEAN, beats=(Beat("Words. " * 20, 4.0), *CLEAN.beats))
    assert "wraps onto the picture" in " ".join(broken.problems())


def test_an_en_dash_in_a_caption():
    broken = replace(CLEAN, beats=(Beat("One \u2013 two.", 4.0), *CLEAN.beats))
    assert "en dash" in " ".join(broken.problems())


def test_a_beat_that_takes_no_time():
    broken = replace(CLEAN, beats=(Beat("Instantly.", 0.0), *CLEAN.beats))
    assert "longer than no time at all" in " ".join(broken.problems())


def test_over_the_cap():
    """The rule the whole storyboard exists to enforce, so it gets an explicit test."""
    long = tuple(Beat(f"Beat {number}.", 10.0) for number in range(10))
    broken = replace(CLEAN, beats=long)
    assert broken.seconds > CAP_SECONDS
    assert "second cap" in " ".join(broken.problems())


def test_declaring_no_shapes():
    assert "which shapes it draws" in " ".join(replace(CLEAN, shapes=()).problems())


def test_a_shape_the_visual_system_does_not_have():
    broken = replace(CLEAN, shapes=("box", "sparkle"))
    assert "'sparkle' is not in the visual system" in " ".join(broken.problems())
