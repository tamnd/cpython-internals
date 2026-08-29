"""The escaping and the attribute rules, which is the part that has to be right."""

from __future__ import annotations

import pytest

from xraywidgets.html import Raw, element, escape, join, raw


def test_text_is_escaped():
    assert str(element("p", "<script>alert(1)</script>")) == (
        "<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>"
    )


def test_quotes_are_escaped_in_attributes_too():
    assert 'title="a &quot;quoted&quot; word"' in str(element("p", "x", title='a "quoted" word'))


def test_raw_is_not_escaped_twice():
    inner = element("b", "6 < 7")
    assert str(element("p", inner)) == "<p><b>6 &lt; 7</b></p>"


def test_raw_lets_a_caller_pass_markup_through():
    assert (
        str(element("style", raw("a > b { color: red }"))) == "<style>a > b { color: red }</style>"
    )


def test_a_trailing_underscore_is_taken_off_the_attribute_name():
    assert 'class="x"' in str(element("p", "text", class_="x"))


def test_underscores_become_hyphens():
    markup = str(element("p", "text", data_flag="caches", aria_label="a label"))
    assert 'data-flag="caches"' in markup
    assert 'aria-label="a label"' in markup


def test_none_and_false_attributes_are_left_out():
    assert str(element("p", "text", title=None, hidden=False)) == "<p>text</p>"


def test_true_is_written_bare():
    assert str(element("button", "press", disabled=True)) == "<button disabled>press</button>"


def test_void_tags_close_themselves():
    assert str(element("br")) == "<br>"


def test_a_void_tag_with_children_is_a_mistake():
    with pytest.raises(ValueError, match="br"):
        element("br", "text")


def test_join_keeps_the_pieces_in_order():
    assert str(join(["a", element("b", "c")])) == "a<b>c</b>"


def test_join_escapes_plain_strings():
    assert str(join(["<"])) == "&lt;"


def test_escape_leaves_ordinary_text_alone():
    assert escape("plain words") == "plain words"


def test_raw_is_a_string_so_it_can_go_anywhere_a_string_can():
    assert isinstance(raw("x"), Raw)
    assert isinstance(raw("x"), str)
