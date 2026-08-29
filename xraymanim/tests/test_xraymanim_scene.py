"""The beat tally, which is the thing that makes a storyboard a plan rather than a comment.

Needs manim, because `Explainer` is a manim `Scene`. It does not render anything: `tear_down`
is called directly, which is the whole point of keeping the check in a method with no
drawing in it.
"""

from __future__ import annotations

import math

import pytest

pytest.importorskip("manim", reason="the drawing half of xraymanim, installed by --extra anim")

from manim import config

from xraymanim.scene import Explainer
from xraymanim.storyboard import Beat, Storyboard

DEMO = Storyboard(
    slug="a99-a-demo",
    title="A demo that only exists in the tests",
    lesson="T99",
    shapes=("box",),
    beats=(Beat("One.", 4.0), Beat("Two.", 4.0), Beat("Three.", 4.0)),
)


class Demo(Explainer):
    storyboard = DEMO

    def construct(self) -> None:  # pragma: no cover - nothing here renders
        pass


@pytest.fixture
def scene():
    made = Demo()
    made.played = 0
    return made


def test_a_scene_that_played_its_beats_is_fine(scene):
    scene.played = 3
    scene.tear_down()


def test_a_scene_that_skipped_a_beat_fails_the_render(scene):
    scene.played = 2
    with pytest.raises(AssertionError) as raised:
        scene.tear_down()
    assert "played 2 beat(s) but its storyboard has 3" in str(raised.value)


def test_the_whole_scene_is_not_a_slice():
    """The default upper bound is infinity, not -1.

    Reading it as a sentinel is not a hypothetical mistake, it is the one that was made
    here: `upto_animation_number >= 0` is true for infinity, so the tally was switched off
    in every render including the real ones, and a scene could quietly stop playing its
    plan. This test is the reason that cannot come back.
    """
    assert config.upto_animation_number == math.inf
    assert not Explainer.rendering_a_slice()


@pytest.mark.parametrize(
    ("field", "value"),
    [("from_animation_number", 4), ("upto_animation_number", 4)],
)
def test_a_slice_switches_the_tally_off(field, value, monkeypatch):
    """`manim render -n 4,4` stops construct early on purpose, so the tally means nothing."""
    monkeypatch.setattr(config, field, value)
    assert Explainer.rendering_a_slice()
