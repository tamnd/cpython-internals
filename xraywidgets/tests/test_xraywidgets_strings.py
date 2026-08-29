"""Every word on screen comes from one file, and this checks the file is usable."""

from __future__ import annotations

import re

import pytest

from xraywidgets.strings import STRINGS, text

#: The placeholders in a string, so a caller can be checked against them.
SLOT = re.compile(r"\{(\w+)\}")


def test_a_string_comes_back_with_its_slots_filled():
    assert text("common.python", version="3.15.0") == "Python 3.15.0"


def test_an_unknown_key_raises_rather_than_rendering_the_key():
    with pytest.raises(KeyError, match="no string called"):
        text("disassembler.nothing_like_this_at_all")


def test_a_near_miss_gets_told_what_it_probably_meant():
    with pytest.raises(KeyError, match=r"disassembler\.offset"):
        text("disassembler.ofset")


def test_every_key_is_dotted_and_starts_with_something_that_owns_it():
    for key in STRINGS:
        owner, _, rest = key.partition(".")
        assert rest, key
        assert owner in {"common", "disassembler"}, key


def test_no_string_has_a_dash_that_should_have_been_a_hyphen():
    for key, value in STRINGS.items():
        assert "\u2014" not in value, key
        assert "\u2013" not in value, key


def test_no_string_has_a_newline_in_the_middle_of_it():
    for key, value in STRINGS.items():
        assert "\n" not in value, key


def test_every_string_can_be_formatted_with_its_own_placeholders():
    for key, value in STRINGS.items():
        filled = text(key, **{name: 0 for name in SLOT.findall(value)})
        assert "{" not in filled, key
