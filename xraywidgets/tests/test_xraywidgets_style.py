"""The stylesheet, and the reason it is generated: no colour is written twice.

The test that matters here is the last one. It reads the sheet looking for hex colours that
are not inside a custom property definition, which is what stops somebody pasting a nice
blue into a rule six months from now and quietly forking the palette away from the diagrams.
"""

from __future__ import annotations

import re

from pyxray import theme
from xraywidgets.style import DARK, LAYOUT, PREFIX, TONE_RULES, stylesheet

#: Any hex colour, so the sheet can be checked for ones written by hand.
COLOUR = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def test_every_tone_in_the_theme_has_a_rule():
    for name in theme.TONES:
        assert f".{PREFIX}-{name} {{" in TONE_RULES


def test_the_palette_is_read_from_the_theme():
    sheet = stylesheet()
    assert f"--{PREFIX}-ink: {theme.INK};" in sheet
    assert f"--{PREFIX}-focus-stroke: {theme.TONES['focus'].stroke};" in sheet


def test_dark_mode_only_moves_the_neutrals():
    for name in theme.TONES:
        assert f"--{PREFIX}-{name}-stroke" not in DARK


def test_dark_mode_swaps_the_page_and_the_text():
    assert f"--{PREFIX}-paper:" in DARK
    assert f"--{PREFIX}-ink:" in DARK


def test_the_layout_half_writes_its_colours_as_properties():
    written = [one for one in COLOUR.findall(LAYOUT) if one != theme.INK]
    assert written == []


def test_the_sheet_names_everything_after_the_package():
    for rule in re.findall(r"^\.[a-z-]+", stylesheet(), flags=re.MULTILINE):
        assert rule.startswith(f".{PREFIX}")


def test_the_sheet_is_valid_enough_to_have_balanced_braces():
    sheet = stylesheet()
    assert sheet.count("{") == sheet.count("}")
