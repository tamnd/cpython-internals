"""The stepper, checked against the code object it was stepping through."""

from __future__ import annotations

import sys

import pytest

from pyxray import stepper


def add(a, b):
    total = a + b
    return total


def total_of(items):
    total = 0
    for item in items:
        total = total + item
    return total


def test_the_function_still_returns_what_it_would_have_returned():
    assert stepper.run(add, 2, 3).result == 5


def test_keyword_arguments_get_through():
    assert stepper.run(add, a=2, b=40).result == 42


def test_every_recorded_offset_is_a_real_instruction():
    offsets = {item.offset for item in stepper.run(add, 1, 2).moments}
    real = {item.offset for item in __import__("dis").get_instructions(add)}
    assert offsets <= real


def test_the_first_thing_that_happens_is_the_function_starting():
    first = stepper.run(add, 1, 2).moments[0]
    assert first.kind == "start"
    assert first.opname == "RESUME"


def test_a_loop_shows_up_as_the_same_offsets_coming_round_again():
    moments = stepper.run(total_of, [1, 2, 3]).moments
    body = [moment for moment in moments if moment.opname == "BINARY_OP"]
    assert len(body) == 3


def test_the_stack_never_gets_taller_than_the_code_object_said_it_would():
    recording = stepper.run(total_of, [1, 2, 3])
    assert recording.deepest <= total_of.__code__.co_stacksize


def test_a_run_that_touches_every_path_reaches_exactly_the_declared_height():
    recording = stepper.run(total_of, [1, 2, 3])
    assert recording.deepest == total_of.__code__.co_stacksize


def test_end_for_is_never_reported_and_that_is_deliberate():
    # END_FOR is marked no_save_ip in Python/bytecodes.c, so it does not update the
    # recorded instruction pointer and instrumentation never sees it as the current
    # instruction. A reader counting rows against a disassembly will notice, so it is
    # pinned here rather than left as a surprise.
    names = {moment.opname for moment in stepper.run(total_of, [1, 2]).moments}
    assert "END_FOR" not in names
    assert "POP_ITER" in names


def test_the_table_shows_the_height_either_side():
    rendered = stepper.run(add, 1, 2).table()
    assert "0 -> 2" in rendered
    assert "RETURN_VALUE" in rendered


def test_the_monitoring_slot_is_given_back_even_when_the_function_raises():
    def explodes():
        raise ValueError("as intended")

    with pytest.raises(ValueError):
        stepper.run(explodes)
    assert all(sys.monitoring.get_tool(tool_id) is None for tool_id in stepper.FREE_TOOL_IDS)


def test_nothing_is_left_monitored_afterwards():
    stepper.run(add, 1, 2)
    assert all(sys.monitoring.get_tool(tool_id) is None for tool_id in stepper.FREE_TOOL_IDS)


def test_the_frame_chain_has_the_caller_in_it():
    names = [name for name, _line in stepper.chain()]
    assert names[0] == "test_the_frame_chain_has_the_caller_in_it"
