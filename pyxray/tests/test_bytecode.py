from __future__ import annotations

import dis
import types
from itertools import pairwise

import pytest

from pyxray import bytecode
from pyxray._opcodes import base_name, cache_entries, is_specialized


def add(a, b):
    return a + b


class Holder:
    def method(self):
        return 1


def test_a_source_string_is_compiled_for_you():
    """A lesson has to be able to disassemble "x = 1 + 2" before compile() is introduced."""
    code = bytecode.code_of("x = 1 + 2")
    assert isinstance(code, types.CodeType)
    assert code.co_filename == "<pyxray>"


def test_code_comes_out_of_a_function_a_method_and_a_code_object():
    assert bytecode.code_of(add) is add.__code__
    assert bytecode.code_of(Holder().method) is Holder.method.__code__
    assert bytecode.code_of(add.__code__) is add.__code__


def test_something_with_no_code_object_gets_a_readable_error():
    with pytest.raises(TypeError, match="cannot get a code object from int"):
        bytecode.code_of(42)


def test_the_instruction_stream_matches_what_dis_reports():
    """This module presents dis differently, it does not disagree with it."""
    ours = bytecode.disassemble(add)
    theirs = list(dis.get_instructions(add, show_caches=False))
    assert [i.opname for i in ours] == [i.opname for i in theirs]
    assert [i.offset for i in ours] == [i.offset for i in theirs]
    assert [i.arg for i in ours] == [i.arg for i in theirs]


def test_constant_folding_is_visible_in_the_instruction_names():
    """1 + 2 never gets added at runtime, and this is the shortest proof of that."""
    assert "BINARY_OP" not in bytecode.opnames("x = 1 + 2")
    assert "BINARY_OP" in bytecode.opnames("x = a + b")

    code = bytecode.code_of("x = 1 + 2")
    load = next(i for i in bytecode.disassemble(code) if i.opname.startswith("LOAD_"))
    loaded = load.arg if load.opname == "LOAD_SMALL_INT" else code.co_consts[load.arg]
    assert loaded == 3, "the addition was already done at compile time"


def test_offsets_step_over_the_inline_caches():
    """The bytes a reader forgets when they count offsets by hand."""
    rows = bytecode.disassemble(add)
    for current, following in pairwise(rows):
        assert following.offset - current.offset == current.total_size


def test_total_size_is_two_bytes_plus_two_per_cache():
    rows = bytecode.disassemble(add)
    assert all(item.total_size == 2 + 2 * item.caches for item in rows)
    assert any(item.caches > 0 for item in rows), "a + b should carry a specializing cache"


def test_the_offsets_and_sizes_account_for_every_byte_of_co_code():
    rows = bytecode.disassemble(add)
    assert sum(item.total_size for item in rows) == len(add.__code__.co_code)


def test_a_freshly_compiled_function_shows_no_specialized_opcodes():
    """Specialization is something the interpreter does after running, not the compiler."""
    code = bytecode.code_of("def f(a, b):\n    return a + b\n")
    assert not any(item.specialized for item in bytecode.disassemble(code))


def test_the_adaptive_view_is_a_different_question_from_the_plain_one():
    def hot(a, b):
        return a + b

    for _ in range(200):
        hot(1, 2)

    plain = bytecode.opnames(hot)
    adaptive = bytecode.opnames(hot, adaptive=True)
    assert len(plain) == len(adaptive)
    assert plain == [base_name(name) for name in adaptive]


def test_base_opname_points_at_what_the_compiler_emitted():
    rows = bytecode.disassemble(add)
    for item in rows:
        assert item.specialized == is_specialized(item.opname)
        if not item.specialized:
            assert item.base_opname == item.opname


def test_caches_agree_with_the_table_cpython_generates_for_itself():
    for item in bytecode.disassemble(add):
        assert item.caches == cache_entries(item.opname)


def test_the_table_has_one_line_per_instruction():
    rows = bytecode.disassemble(add)
    text = bytecode.table(add)
    assert len(text.splitlines()) == len(rows)
    assert rows[0].opname in text


def test_the_table_can_show_the_cache_count():
    with_caches = bytecode.table(add, show_caches=True)
    assert "cache" in with_caches
    assert "cache" not in bytecode.table(add, show_caches=False)


def test_diff_reports_both_lengths_and_marks_the_rows_that_differ():
    left, right = "x = 1 + 2", "x = int(input())"
    text = bytecode.diff(left, right, labels=("constant", "computed"))
    assert text.startswith("constant")
    assert "computed" in text.splitlines()[0]
    counts = (len(bytecode.opnames(left)), len(bytecode.opnames(right)))
    assert text.splitlines()[-1] == f"{counts[0]} instructions vs {counts[1]}"
    assert "| " in text, "the two are not the same, so some row has to be marked"


def test_diff_of_something_with_itself_marks_nothing():
    text = bytecode.diff(add, add)
    assert "| " not in text


def test_constants_include_nested_code_objects_by_name():
    rows = bytecode.constants("def outer():\n    return 1\n")
    assert ("code", "<code outer>") in [(kind, text) for _, kind, text in rows]
    assert [index for index, _, _ in rows] == list(range(len(rows)))


def test_the_line_table_covers_the_whole_code_object():
    rows = bytecode.line_table(add)
    assert rows[0][0] == 0
    assert rows[-1][1] == len(add.__code__.co_code)
    assert any(line == add.__code__.co_firstlineno + 1 for _, _, line in rows)


def test_the_line_table_is_the_decoded_form_of_co_lines():
    assert bytecode.line_table(add) == list(add.__code__.co_lines())


LOOP = """
total = 0
for n in [1, 2, 3]:
    total = total + n
"""


def test_the_same_argument_means_different_things_to_different_instructions():
    """This is the thing that stops a reader cold, so it gets its own function."""
    assert bytecode.argument_meaning("LOAD_CONST") == "an index into co_consts"
    assert bytecode.argument_meaning("LOAD_NAME") == "an index into co_names"
    assert bytecode.argument_meaning("CALL") == "how many arguments are on the stack"


def test_an_instruction_with_no_argument_says_so():
    assert "never read" in bytecode.argument_meaning("POP_TOP")


def test_an_instruction_that_does_not_exist_is_an_error_and_not_a_guess():
    with pytest.raises(KeyError, match="LOAD_NONSENSE"):
        bytecode.argument_meaning("LOAD_NONSENSE")


def test_every_hand_written_note_is_about_an_instruction_that_still_exists():
    """The one hand written table in this module, so it gets checked against the real one."""
    missing = [name for name in bytecode.ARGUMENT_NOTES if name not in dis.opmap]
    assert missing == []


def test_a_forward_jump_counts_on_from_after_the_caches():
    forward = next(jump for jump in bytecode.jumps(LOOP) if not jump.backwards)
    assert forward.target == forward.resumes_at + 2 * forward.arg


def test_a_backward_jump_counts_back_from_the_same_place():
    backward = next(jump for jump in bytecode.jumps(LOOP) if jump.backwards)
    assert backward.target == backward.resumes_at - 2 * backward.arg


def test_every_jump_lands_where_dis_says_it_does():
    landings = {
        item.offset: item.jump_target
        for item in bytecode.disassemble(LOOP)
        if item.jump_target is not None
    }
    assert {jump.offset: jump.target for jump in bytecode.jumps(LOOP)} == landings


def test_the_jump_table_writes_the_arithmetic_out():
    assert " * 2 = " in bytecode.jump_table(LOOP)


def test_a_loop_jumps_both_ways():
    directions = {jump.backwards for jump in bytecode.jumps(LOOP)}
    assert directions == {True, False}


#: A `try` with both an `except` and a `finally`, which is the smallest piece of Python that
#: produces more than one handler row. The `finally` body is compiled twice, once for the
#: path where nothing went wrong and once for the path where something did.
GUARDED = """
try:
    risky()
except ValueError:
    handled()
finally:
    always()
"""


def test_code_that_cannot_raise_has_no_exception_table():
    assert bytecode.exception_table("x = 1") == []


def test_a_try_produces_handlers():
    assert bytecode.exception_table(GUARDED)


def test_the_handlers_are_the_ones_dis_parses():
    parsed = dis._parse_exception_table(bytecode.code_of(GUARDED))
    ours = bytecode.exception_table(GUARDED)
    assert [(one.start, one.end, one.target) for one in ours] == [
        (one.start, one.end, one.target) for one in parsed
    ]


def test_a_handler_covers_the_offsets_between_its_ends():
    first = bytecode.exception_table(GUARDED)[0]
    assert first.covers(first.start)
    assert first.covers(first.end - 1)
    assert not first.covers(first.end)
    assert not first.covers(first.start - 1)


def test_the_protected_range_holds_the_call_that_can_raise():
    first = bytecode.exception_table(GUARDED)[0]
    inside = [item.opname for item in bytecode.disassemble(GUARDED) if first.covers(item.offset)]
    assert "CALL" in inside


def test_a_handler_target_is_a_real_offset_in_the_code():
    offsets = {item.offset for item in bytecode.disassemble(GUARDED)}
    for handler in bytecode.exception_table(GUARDED):
        assert handler.target in offsets


def test_the_handlers_come_back_in_offset_order():
    starts = [one.start for one in bytecode.exception_table(GUARDED)]
    assert starts == sorted(starts)
