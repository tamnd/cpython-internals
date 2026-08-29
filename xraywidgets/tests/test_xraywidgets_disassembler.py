"""The disassembler widget, checked against `dis` rather than against itself.

The point of most of these is agreement. The widget is only worth having if a reader can put
`dis.dis` next to it and see the same thing, so the tests compare the two directly instead of
freezing whatever the widget happens to print today.
"""

from __future__ import annotations

import dis
import re
import sys

import pytest

from pyxray import bytecode
from xraywidgets import Disassembler
from xraywidgets.disassembler import FLAGS

#: A `try` with two arms, so there is a real exception table to look at.
GUARDED = """
try:
    risky()
except ValueError:
    handled()
finally:
    always()
"""


def opnames(widget: Disassembler) -> list[str]:
    return [one["opname"] for one in widget.state()["rows"] if one["kind"] == "instruction"]


def test_the_instructions_are_the_ones_dis_gives():
    code = "total = sum(values)"
    assert opnames(Disassembler(code)) == [one.opname for one in dis.get_instructions(code)]


def test_a_widget_with_no_toggles_on_has_one_row_per_instruction():
    widget = Disassembler("total = sum(values)")
    assert all(one["kind"] == "instruction" for one in widget.state()["rows"])


def test_the_cache_rows_count_the_bytes_dis_hides():
    widget = Disassembler("total = sum(values)", caches=True)
    caches = [one for one in widget.state()["rows"] if one["kind"] == "cache"]
    expected = [one.caches for one in bytecode.disassemble("total = sum(values)") if one.caches]
    assert [one["bytes"] // 2 for one in caches] == expected


def test_turning_caches_on_does_not_change_the_instructions():
    code = "total = sum(values)"
    assert opnames(Disassembler(code)) == opnames(Disassembler(code, caches=True))


def test_the_stack_column_only_exists_when_it_is_turned_on():
    column = '<th scope="col">Stack</th>'
    assert column not in Disassembler("x = 1").render()
    assert column in Disassembler("x = 1", depths=True).render()


def test_the_stack_heights_are_the_ones_pyxray_walked():
    from pyxray import stack

    code = "total = sum(values)"
    widget = Disassembler(code, depths=True)
    walked = {one.offset: (one.before, one.after) for one in stack.walk(code)}
    for row in widget.state()["rows"]:
        if row["offset"] in walked:
            assert (row["before"], row["after"]) == walked[row["offset"]]


def test_an_instruction_the_walk_never_reached_gets_a_dash_and_not_a_zero():
    widget = Disassembler("x = 1", depths=True)
    assert widget.depth({"before": None, "after": None}) == "-"


def test_the_exception_table_is_the_one_the_code_object_carries():
    widget = Disassembler(GUARDED, exceptions=True)
    assert len(widget.state()["handlers"]) == len(bytecode.exception_table(GUARDED))
    assert widget.state()["handlers"][0]["start"] == bytecode.exception_table(GUARDED)[0].start


def test_the_exception_table_is_left_out_until_it_is_asked_for():
    assert Disassembler(GUARDED).state()["handlers"] == []


def test_code_that_cannot_raise_says_so_rather_than_showing_an_empty_list():
    markup = Disassembler("x = 1", exceptions=True).render()
    assert "no exception table" in markup


def test_a_handler_is_described_as_a_sentence_and_not_five_numbers():
    handler = Disassembler(GUARDED, exceptions=True).state()["handlers"][0]
    assert "jump to" in handler["text"]
    assert str(handler["target"]) in handler["text"]


def test_broken_code_is_a_message_and_not_a_traceback():
    widget = Disassembler("def (")
    assert "did not compile" in widget.state()["error"]
    assert widget.state()["rows"] == []
    assert "did not compile" in widget.render()


def test_broken_code_still_shows_the_toggles_so_the_widget_does_not_vanish():
    markup = Disassembler("def (").render()
    for name, _ in FLAGS:
        assert f'data-flag="{name}"' in markup


def test_the_source_the_reader_typed_is_shown_back_escaped():
    assert "&lt;" in Disassembler("ok = 1 < 2").render()
    assert "<script" not in Disassembler("<script>alert(1)</script>").render()


def test_the_version_is_written_next_to_the_table():
    assert ".".join(str(part) for part in sys.version_info[:3]) in Disassembler("x = 1").render()


def test_every_flag_is_a_field_you_can_set_in_the_constructor():
    widget = Disassembler("x = 1", **{name: True for name, _ in FLAGS})
    assert all(one["on"] for one in widget.state()["flags"])


def test_the_toggles_come_back_in_the_order_they_are_listed():
    names = [one["name"] for one in Disassembler("x = 1").state()["flags"]]
    assert names == [name for name, _ in FLAGS]


def test_a_specialized_opcode_is_labelled_with_a_word_and_not_only_a_colour():
    def warm(values):
        return sum(values)

    for _ in range(200):
        warm([1, 2, 3])
    widget = Disassembler(warm.__code__, adaptive=True)
    if not any(one["specialized"] for one in widget.state()["rows"]):
        pytest.skip("this build did not specialize anything in that loop")
    assert "specialized" in widget.render()


def test_the_widget_takes_a_function_and_not_only_a_string():
    def add(left, right):
        return left + right

    assert "BINARY_OP" in opnames(Disassembler(add))


def test_a_jump_says_where_it_goes():
    widget = Disassembler("x = 1 if flag else 2")
    jumps = [one for one in widget.state()["rows"] if one["jump_target"] is not None]
    assert jumps
    assert f"jumps to {jumps[0]['jump_target']}" in widget.render()


def test_the_still_picture_has_its_buttons_switched_off():
    assert "disabled" in Disassembler("x = 1").render()


def test_the_live_markup_has_them_switched_on_and_somewhere_to_type():
    html = Disassembler("x = 1").view()["html"]
    assert "disabled" not in html
    assert 'data-role="code"' in html


def test_the_live_markup_drops_the_line_about_being_static():
    assert ".live()" not in Disassembler("x = 1").view()["html"]


def test_the_front_end_module_reads_the_traits_python_actually_syncs():
    module = Disassembler.esm()
    for name, _ in FLAGS:
        assert name in module or "data-flag" in module
    assert "change:view" in module


def test_the_front_end_module_works_out_no_bytecode_of_its_own():
    """No opcode name appears in the JavaScript, in a rule or in a table or anywhere else.

    This is the one that keeps the promise in the module docstring honest. The day somebody
    adds `if (op.startsWith("LOAD"))` to the front end there are two implementations of what
    a disassembly means, and only one of them is tested.
    """
    module = Disassembler.esm()
    named = {one for one in re.findall(r"\b[A-Z][A-Z_]{3,}\b", module)}
    assert named & set(dis.opmap) == set()


def test_the_headings_line_up_with_the_cells():
    for depths in (False, True):
        widget = Disassembler("total = sum(values)", depths=depths)
        markup = str(widget.markup(widget.state()))
        body = markup.split("<tbody>")[1]
        for row in re.findall(r"<tr>(.*?)</tr>", body):
            assert row.count("<td") == len(widget.headings())
