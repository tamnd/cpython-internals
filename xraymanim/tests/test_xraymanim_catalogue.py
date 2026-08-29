"""The catalogue is the plan for every animation, so the tests hold the plan itself up."""

from __future__ import annotations

import pytest

from xraymanim import catalogue


@pytest.mark.parametrize("storyboard", catalogue.ANIMATIONS, ids=lambda item: item.slug)
def test_every_animation_in_the_catalogue_is_clean(storyboard):
    assert storyboard.problems() == []


def test_the_slugs_are_unique():
    slugs = [storyboard.slug for storyboard in catalogue.ANIMATIONS]
    assert len(set(slugs)) == len(slugs)


def test_they_are_numbered_in_order():
    """A reader who has seen a04 has seen a01 to a03, so the numbering is the course order."""
    numbers = [int(storyboard.slug[1:3]) for storyboard in catalogue.ANIMATIONS]
    assert numbers == sorted(numbers)
    assert numbers == list(range(1, len(numbers) + 1))


def test_looking_one_up():
    assert catalogue.find("a01-seven-stages").lesson == "T01"


def test_looking_up_something_that_is_not_there_says_what_is():
    with pytest.raises(KeyError) as raised:
        catalogue.find("a99-nothing")
    assert "a01-seven-stages" in str(raised.value)


def test_the_file_and_the_class_are_derived_from_the_slug():
    assert catalogue.module_name("a01-seven-stages") == "a01_seven_stages"
    assert catalogue.class_name("a01-seven-stages") == "A01SevenStages"


def test_the_whole_set_is_a_sitting_worth_of_watching():
    """Not a correctness rule, a design one. If this ever gets large the set needs splitting."""
    assert catalogue.seconds() == sum(item.seconds for item in catalogue.ANIMATIONS)
