"""The half that needs anywidget, which is the half most likely to rot quietly.

Everything else in this package works with nothing installed, so it is exercised by every
run. This file is the only place the live path is touched at all, which is why CI installs
the extra rather than leaving it to whoever happens to have anywidget on their machine.

The tests here are all the same shape: change a trait the way a click would, and check that
what comes back is what Python would have computed on its own. Nothing here opens a browser,
because the thing worth testing is that the browser is not being asked to decide anything.
"""

from __future__ import annotations

import pytest

from xraywidgets import Disassembler

pytest.importorskip("anywidget", reason="the live version needs the `live` extra")


@pytest.fixture
def live():
    return Disassembler("total = sum(values)").live()


def test_the_live_widget_starts_showing_what_the_static_one_shows(live):
    assert live.view["html"] == Disassembler("total = sum(values)").view()["html"]


def test_every_toggle_is_a_trait_the_front_end_can_write(live):
    for name in ("adaptive", "caches", "depths", "exceptions"):
        assert live.has_trait(name)


def test_turning_a_toggle_on_gets_a_new_picture_back(live):
    before = live.view["html"]
    live.caches = True
    assert live.view["html"] != before
    assert live.view["html"] == Disassembler("total = sum(values)", caches=True).view()["html"]


def test_turning_a_toggle_back_off_gets_the_first_picture_back(live):
    first = live.view["html"]
    live.depths = True
    live.depths = False
    assert live.view["html"] == first


def test_typing_new_code_recomputes_the_rows(live):
    live.code = "x = 1"
    assert [one["opname"] for one in live.view["rows"]] == [
        one["opname"] for one in Disassembler("x = 1").state()["rows"]
    ]


def test_typing_half_a_line_shows_a_message_and_keeps_the_widget_on_screen(live):
    live.code = "def ("
    assert "did not compile" in live.view["error"]
    assert 'data-flag="caches"' in live.view["html"]


def test_typing_the_rest_of_the_line_brings_the_table_back(live):
    live.code = "def ("
    live.code = "def f(): pass"
    assert live.view["error"] == ""
    assert live.view["rows"]


def test_the_live_picture_has_working_buttons_and_somewhere_to_type(live):
    assert "disabled" not in live.view["html"]
    assert 'data-role="code"' in live.view["html"]


def test_the_stylesheet_goes_over_with_it(live):
    assert "--xw-ink" in live._css


def test_the_front_end_module_goes_over_with_it(live):
    assert "export default" in live._esm
