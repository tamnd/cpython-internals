"""The grammar is a translation of `pyxray.theme`, so the tests mostly check it stays one."""

from __future__ import annotations

import pytest

from pyxray import theme
from xraymanim import grammar


def test_a_pen_carries_the_theme_colours():
    """A tone renamed in pyxray has to show up here, rather than being copied and frozen."""
    made = grammar.pen("input")
    assert (made.stroke, made.fill) == (theme.TONES["input"].stroke, theme.TONES["input"].fill)


def test_an_unknown_tone_says_what_the_tones_are():
    with pytest.raises(KeyError) as raised:
        grammar.pen("purple")
    assert "durable" in str(raised.value)


def test_a_pen_hands_manim_a_stroke_a_fill_and_a_width():
    keywords = grammar.pen("focus").kwargs()
    assert set(keywords) == {"stroke_color", "fill_color", "fill_opacity", "stroke_width"}
    assert keywords["stroke_width"] == grammar.STROKE


def test_fading_keeps_the_colours_and_changes_only_the_opacity():
    solid = grammar.pen("durable")
    ghost = solid.faded(0.2)
    assert (ghost.stroke, ghost.fill) == (solid.stroke, solid.fill)
    assert ghost.fill_opacity == 0.2


def test_the_cycle_wraps():
    assert grammar.cycle(0).name == grammar.cycle(len(theme.CYCLE)).name


def test_every_shape_is_a_primitive_or_a_named_object():
    assert grammar.SHAPES == grammar.PRIMITIVES + grammar.MOBJECTS
    assert len(set(grammar.SHAPES)) == len(grammar.SHAPES)


def test_there_are_nine_shapes_and_six_named_objects():
    """The counts are in the issue, in the README and in the visual system document.

    Pinning them here is not pedantry. The number is quoted in prose in three places, and a
    tenth primitive added quietly is how those three places start disagreeing.
    """
    assert len(grammar.PRIMITIVES) == 9
    assert len(grammar.MOBJECTS) == 6


def test_a_font_is_picked_from_what_is_installed():
    assert grammar.mono_font(["Nunito", "Menlo"]) == "Menlo"
    assert grammar.sans_font(["Menlo", "Arial"]) == "Arial"


def test_no_preferred_font_means_manims_own_default():
    """An empty answer, not a name. Naming a font that is not there is a silent substitution."""
    assert grammar.mono_font([]) == ""
    assert grammar.sans_font(["Comic Sans MS"]) == ""
