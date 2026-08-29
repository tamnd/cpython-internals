"""What every widget promises: it renders with nothing installed, and it says so."""

from __future__ import annotations

import pytest

from xraywidgets.base import STATIC, Widget
from xraywidgets.html import Raw, element
from xraywidgets.style import PREFIX


class Toy(Widget):
    """A widget with one number in it, for testing the parts that are not any one widget."""

    slug = "toy"

    def state(self) -> dict[str, object]:
        return {"answer": 42}

    def markup(self, state: dict[str, object], *, live: bool = False) -> Raw:
        return element("p", state["answer"], class_="live" if live else "still")


def test_a_widget_renders_to_html_with_nothing_installed():
    assert "42" in Toy().render()


def test_the_stylesheet_travels_with_the_widget():
    assert "<style>" in Toy().render()


def test_the_outer_element_says_which_widget_it_is():
    assert 'data-widget="toy"' in Toy().render()


def test_the_outer_element_carries_the_prefix_class():
    assert f'class="{PREFIX}"' in Toy().render()


def test_jupyter_gets_the_still_picture():
    assert Toy()._repr_html_() == Toy().render()


def test_the_still_picture_is_the_one_with_the_controls_off():
    assert 'class="still"' in Toy().render()


def test_the_view_carries_the_state_and_the_markup_for_the_live_one():
    view = Toy().view()
    assert view["answer"] == 42
    assert view["html"] == '<p class="live">42</p>'


def test_a_widget_with_no_front_end_file_says_which_file_is_missing():
    with pytest.raises(FileNotFoundError, match=r"toy\.js"):
        Toy.esm()


def test_the_widgets_that_do_have_a_front_end_file_can_read_it():
    for path in STATIC.glob("*.js"):
        assert path.read_text(encoding="utf-8").strip()


def test_the_base_class_makes_a_subclass_say_what_it_shows():
    class Empty(Widget):
        slug = "empty"

    with pytest.raises(NotImplementedError):
        Empty().state()
    with pytest.raises(NotImplementedError):
        Empty().markup({})


def test_the_notice_tells_a_reader_where_the_moving_version_is():
    assert ".live()" in str(Toy().notice())
