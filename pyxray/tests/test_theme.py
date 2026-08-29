"""The palette checking its own contrast, so nobody has to take it on trust.

Issue 69 asked for the widget contrast to be measured rather than assumed, and for the
measurement to end up as a test rather than a spreadsheet, because a spreadsheet goes stale
the first time somebody picks a prettier blue. The ratios are computable from the hex
values, so this file computes them.

Every threshold here is one of the two numbers WCAG AA asks for. `theme.BODY_TEXT` is 4.5:1
and applies to words. `theme.LARGE_TEXT` is 3:1 and applies to headings and to the boundary
of a control, which is what the standard calls non text contrast.

The failure message on each assertion prints the ratio and both colours. That is deliberate.
Somebody who changes a tone and breaks this wants to know how far off they are, not that a
boolean came back false.
"""

from __future__ import annotations

import pytest

from pyxray import theme

#: The two pages a widget can end up on. Named so a parametrised failure says which theme
#: broke instead of printing a hex string at somebody.
PAGES = [("light", theme.PAPER), ("dark", theme.DARK_PAPER)]

#: The foreground neutrals, paired with the page they appear on. Ink is the body text and
#: muted is the notes and the column headings, and both are ordinary text, so both are held
#: to the body threshold.
NEUTRALS = [
    ("ink on the light page", theme.INK, theme.PAPER),
    ("ink on the dark page", theme.DARK_INK, theme.DARK_PAPER),
    ("muted on the light page", theme.MUTED, theme.PAPER),
    ("muted on the dark page", theme.DARK_MUTED, theme.DARK_PAPER),
]


def ratio(front: str, back: str) -> float:
    return theme.contrast(front, back)


def test_black_on_white_is_the_number_the_standard_uses():
    assert round(theme.contrast("#000000", "#ffffff"), 2) == 21.0


def test_a_colour_against_itself_has_no_contrast():
    assert theme.contrast(theme.INK, theme.INK) == 1.0


def test_the_order_of_the_two_colours_does_not_matter():
    assert theme.contrast(theme.INK, theme.PAPER) == theme.contrast(theme.PAPER, theme.INK)


def test_the_hash_is_optional():
    assert theme.luminance("#ffffff") == theme.luminance("ffffff")


def test_a_colour_that_is_not_six_hex_digits_is_refused():
    with pytest.raises(ValueError, match="six digit hex"):
        theme.luminance("#fff")


def test_green_counts_for_more_than_blue():
    """The weighting is the whole reason this is not just an average of the channels."""
    assert theme.luminance("#00ff00") > theme.luminance("#ff0000") > theme.luminance("#0000ff")


@pytest.mark.parametrize("name", sorted(theme.TONES))
def test_words_on_a_chip_are_readable(name):
    """The chip text against the chip, which is the pair issue 69 asked about first."""
    tone = theme.tone(name)
    measured = ratio(tone.text, tone.fill)
    assert measured >= theme.BODY_TEXT, (
        f"{name}: text {tone.text} on fill {tone.fill} is {measured:.2f}:1, "
        f"needs {theme.BODY_TEXT}:1"
    )


@pytest.mark.parametrize("name", sorted(theme.TONES))
def test_a_tone_stroke_is_a_visible_line_on_the_diagram_page(name):
    """The strokes draw box borders and arrows on white, which is non text contrast."""
    tone = theme.tone(name)
    measured = ratio(tone.stroke, theme.PAPER)
    assert measured >= theme.LARGE_TEXT, (
        f"{name}: stroke {tone.stroke} on paper is {measured:.2f}:1, needs {theme.LARGE_TEXT}:1"
    )


@pytest.mark.parametrize(("what", "front", "back"), NEUTRALS)
def test_the_neutral_text_is_readable_on_its_own_page(what, front, back):
    measured = ratio(front, back)
    assert measured >= theme.BODY_TEXT, (
        f"{what}: {front} on {back} is {measured:.2f}:1, needs {theme.BODY_TEXT}:1"
    )


@pytest.mark.parametrize(("theme_name", "page"), PAGES)
def test_the_focus_outline_is_visible_on_both_pages(theme_name, page):
    """The one thing telling a keyboard user where they are, so it has to clear both.

    The outline sits two pixels off the control, so what it is drawn against is the page
    and not the control's own background.
    """
    outline = theme.tone("focus").stroke
    measured = ratio(outline, page)
    assert measured >= theme.LARGE_TEXT, (
        f"the focus outline {outline} on the {theme_name} page is {measured:.2f}:1, "
        f"needs {theme.LARGE_TEXT}:1"
    )


@pytest.mark.parametrize(("theme_name", "page"), PAGES)
def test_the_edge_of_a_control_is_visible_on_both_pages(theme_name, page):
    """One grey for both themes. If this stops holding, dark mode needs its own value."""
    measured = ratio(theme.EDGE, page)
    assert measured >= theme.LARGE_TEXT, (
        f"the control edge {theme.EDGE} on the {theme_name} page is {measured:.2f}:1, "
        f"needs {theme.LARGE_TEXT}:1"
    )


@pytest.mark.parametrize("name", sorted(theme.TONES))
def test_a_chip_keeps_its_border_apart_from_the_dark_page(name):
    """A chip on the dark page is a pale shape, and its border must not vanish into it.

    On the light page the fill is what separates the chip from the paper and the border is
    decoration. On the dark page it is the other way around, and the border is the outline
    of a shape that is much brighter than what is behind it, so this checks the fill rather
    than the border.
    """
    tone = theme.tone(name)
    measured = ratio(tone.fill, theme.DARK_PAPER)
    assert measured >= theme.LARGE_TEXT, (
        f"{name}: fill {tone.fill} on the dark page is {measured:.2f}:1, needs {theme.LARGE_TEXT}:1"
    )


def test_every_tone_puts_its_words_in_ink():
    """Not a taste check. Anything on a fill is written as a literal, so it cannot move.

    The fills do not change between themes, so a tone's text colour must not be read from a
    CSS variable that does. `Tone.text` returning INK is what lets `style.py` write the
    value straight into the sheet. A tone that answered something else would need the same
    argument made again for that colour.
    """
    assert {tone.text for tone in theme.TONES.values()} == {theme.INK}


def test_the_faint_rule_colour_is_not_used_where_a_control_edge_is_needed():
    """Records why EDGE exists at all, so nobody merges the two back together.

    LINE is right for a rule under a column heading and is nowhere near the bar for the
    edge of a button. This asserts that it fails, which is the thing worth knowing.
    """
    assert ratio(theme.LINE, theme.PAPER) < theme.LARGE_TEXT
    assert ratio(theme.DARK_LINE, theme.DARK_PAPER) < theme.LARGE_TEXT


def test_the_stroke_would_not_have_worked_as_chip_text():
    """The measurement that decided `Tone.text`, kept so the decision is not re argued.

    Five of the six tones put their own stroke on their own fill at under 4.5:1. Deleting
    this test is fine the day somebody finds six strokes that are both readable on a pale
    fill and still tell each other apart as lines on white. Until then it is the evidence.
    """
    failing = [
        name
        for name, tone in theme.TONES.items()
        if ratio(tone.stroke, tone.fill) < theme.BODY_TEXT
    ]
    assert sorted(failing) == ["durable", "focus", "input", "intermediate", "warning"]
