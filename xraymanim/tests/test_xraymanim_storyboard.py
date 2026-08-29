"""One test per rule, each one breaking exactly one thing in a storyboard that was fine."""

from __future__ import annotations

from dataclasses import replace

from xraymanim.grammar import CAP_SECONDS
from xraymanim.storyboard import ALT_LIMIT, Beat, Storyboard

CLEAN = Storyboard(
    slug="a99-a-demo",
    title="A demo that only exists in the tests",
    lesson="T99",
    shapes=("box", "arrow", "PyObjectBox"),
    alt="a box with an arrow leaving it, and a second box that the arrow arrives at",
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


def test_no_alt_text_at_all():
    assert "write alt text" in replace(CLEAN, alt="").problems()[0]


def test_alt_text_that_is_only_whitespace_counts_as_none():
    assert "write alt text" in replace(CLEAN, alt="   ").problems()[0]


def test_a_line_break_in_the_alt_text():
    """A screen reader does nothing useful with it and the markdown image swallows it."""
    broken = replace(CLEAN, alt="a box with an arrow leaving it,\nand a second box")
    assert "line break" in broken.problems()[0]


def test_an_em_dash_in_the_alt_text():
    dashed = replace(CLEAN, alt="a box with an arrow leaving it \u2014 and a second box below")
    assert "em dash" in dashed.problems()[0]


def test_alt_text_that_is_the_title_again():
    """The title is read out next to the picture already, so this is one sentence twice."""
    lazy = replace(CLEAN, alt=CLEAN.title)
    assert "the title again" in lazy.problems()[0]


def test_alt_text_that_ignores_the_case_of_the_title():
    lazy = replace(CLEAN, alt=CLEAN.title.upper())
    assert "the title again" in lazy.problems()[0]


def test_alt_text_that_is_a_label_rather_than_a_description():
    assert "rather than a description" in replace(CLEAN, alt="two boxes").problems()[0]


def test_alt_text_that_is_a_paragraph():
    essay = replace(CLEAN, alt="a box, " * 40)
    assert f"over {ALT_LIMIT}" in essay.problems()[0]


def test_alt_text_that_opens_by_saying_it_is_an_animation():
    """The reader knows. It is being read to them because they cannot see the picture."""
    told = replace(CLEAN, alt="An animation of a box with an arrow leaving it, and a second box")
    assert "already knows" in told.problems()[0]


def test_only_the_first_redundant_opening_is_reported():
    told = replace(CLEAN, alt="Image of a box with an arrow leaving it, and a second box below")
    assert len(told.problems()) == 1


def test_a_description_that_happens_to_mention_an_animation_later_is_fine():
    fine = replace(CLEAN, alt="a box that the animation fills in, with an arrow leaving it")
    assert fine.problems() == []
