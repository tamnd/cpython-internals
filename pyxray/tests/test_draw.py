from __future__ import annotations

import pytest

from pyxray import draw


def test_a_row_of_boxes_lines_the_borders_up_with_the_labels():
    text = draw.boxes(["text", "tokens"])
    top, middle, bottom = text.splitlines()
    assert len(top) == len(middle) == len(bottom)
    assert "| text |" in middle
    assert "->" in middle


def test_the_highlighted_box_is_drawn_differently_from_the_others():
    """A lesson reuses the same picture and points at a different part of it each time."""
    text = draw.boxes(["a", "b", "c"], highlight=1)
    assert "+===+" in text
    assert "+---+" in text


def test_a_row_with_nothing_in_it_draws_nothing_rather_than_a_broken_box():
    assert draw.boxes([]) == ""


def test_a_stack_is_drawn_with_the_top_at_the_top():
    """Everybody describes a stack top down and half of all diagrams draw it the other way."""
    text = draw.stack(["bottom", "middle", "top"])
    rows = [line for line in text.splitlines() if "|" in line]
    assert "top" in rows[0]
    assert "bottom" in rows[-1]


def test_a_stack_can_carry_a_title():
    assert "the value stack" in draw.stack([1, 2], title="the value stack")


def test_bars_are_as_long_as_the_number_and_a_zero_gets_a_tick_instead():
    """A zero length bar is invisible, and an invisible row reads as a missing row."""
    text = draw.bars([("line 1", 0), ("line 2", 4)])
    first, second = text.splitlines()
    assert "|" in first
    assert "####" in second


def test_bars_carry_a_note_column_for_what_happened_on_that_row():
    text = draw.bars([("line 1", 0), ("line 2", 4)], note=["", "INDENT"])
    assert text.splitlines()[1].endswith("INDENT")


def test_bars_with_no_rows_draw_nothing():
    assert draw.bars([]) == ""


def test_a_ribbon_marks_each_span_and_lists_what_the_marks_mean():
    text = draw.ribbon("a + b", [(0, 1, "NAME", "a"), (2, 3, "OP", "+"), (4, 5, "NAME", "b")])
    lines = text.splitlines()
    assert lines[0] == "a + b"
    assert lines[1] == "1 2 3"
    assert "1  NAME" in text


def test_a_ribbon_marks_adjacent_spans_with_different_characters():
    """Adjacent tokens are the normal case, so the marks have to be distinguishable."""
    text = draw.ribbon("ab", [(0, 1, "NAME", "a"), (1, 2, "NAME", "b")])
    assert text.splitlines()[1] == "12"


def test_a_ribbon_ignores_spans_that_start_past_the_end_of_the_line():
    text = draw.ribbon("ab", [(0, 1, "NAME", "a"), (9, 10, "NAME", "off the end")])
    assert text.splitlines()[1] == "1"


def test_a_ribbon_of_nothing_says_so():
    assert draw.ribbon("", []) == "(empty)"


def test_a_flow_puts_an_arrow_between_every_pair_of_steps():
    text = draw.flow(["one", "two", "three"])
    assert text.count("v") == 2
    assert text.splitlines()[0] == "one"


def test_a_flow_of_one_step_has_no_arrows():
    assert draw.flow(["only"]) == "only"


def test_a_table_pads_every_column_to_its_widest_cell():
    text = draw.table(["name", "n"], [["short", 1], ["much longer", 22]])
    _, rule, first, second = text.splitlines()
    assert len(rule) >= len("much longer")
    assert first.startswith("short      ")
    assert second.startswith("much longer")


def test_a_table_with_no_rows_still_prints_its_header():
    text = draw.table(["a", "b"], [])
    assert text.splitlines()[0] == "a  b"


@pytest.mark.parametrize("count", [1, 10, 40])
def test_a_ribbon_has_a_distinct_mark_for_every_span_up_to_the_alphabet_running_out(count):
    spans = [(index, index + 1, "N", "x") for index in range(count)]
    text = draw.ribbon("x" * count, spans)
    marks = text.splitlines()[1]
    assert len(set(marks)) == min(count, len(draw.MARKS))
