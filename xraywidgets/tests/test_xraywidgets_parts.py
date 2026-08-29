"""The shared markup, and the one rule it enforces: colour never speaks on its own."""

from __future__ import annotations

import pytest

from xraywidgets.parts import chip, error, head, source, table, toggles
from xraywidgets.style import PREFIX


def test_a_chip_carries_its_words():
    assert ">specialized<" in str(chip("specialized", "focus"))


def test_a_chip_without_words_is_refused():
    with pytest.raises(ValueError, match="colour is never the only signal"):
        chip("   ", "focus")


def test_an_unknown_tone_is_refused_here_rather_than_showing_up_grey():
    with pytest.raises(KeyError):
        chip("words", "chartreuse")


def test_a_chip_names_its_tone_in_a_class():
    assert f"{PREFIX}-warning" in str(chip("careful", "warning"))


def test_a_title_is_left_off_when_there_is_none():
    assert "title=" not in str(chip("words"))


def test_the_source_is_a_box_when_it_is_not_live():
    markup = str(source("x = 1"))
    assert markup.startswith("<div")
    assert "textarea" not in markup


def test_the_source_is_something_you_can_type_in_when_it_is_live():
    markup = str(source("x = 1", live=True))
    assert markup.startswith("<textarea")
    assert 'data-role="code"' in markup


def test_the_source_box_grows_with_the_code():
    assert 'rows="4"' in str(source("a\nb\nc\nd", live=True))


def test_source_code_is_escaped():
    assert "&lt;" in str(source("x = 1 < 2", live=True))


def test_toggles_are_real_buttons_that_say_whether_they_are_on():
    markup = str(toggles([("caches", "Inline caches", True)], live=True))
    assert 'type="button"' in markup
    assert 'aria-pressed="true"' in markup
    assert 'data-flag="caches"' in markup


def test_a_static_toggle_says_it_does_not_work():
    assert "disabled" in str(toggles([("caches", "Inline caches", False)]))


def test_a_live_toggle_does_not_say_that():
    assert "disabled" not in str(toggles([("caches", "Inline caches", False)], live=True))


def test_the_table_has_a_real_header_row():
    markup = str(table(["Offset", "Instruction"], []))
    assert "<thead>" in markup
    assert 'scope="col"' in markup


def test_the_head_puts_the_notes_after_the_title():
    markup = str(head("Bytecode", "Python 3.15.0", "9 instructions"))
    assert markup.index("Bytecode") < markup.index("Python") < markup.index("9 instructions")


def test_an_error_says_what_went_wrong():
    assert "invalid syntax" in str(error("That did not compile: invalid syntax"))
