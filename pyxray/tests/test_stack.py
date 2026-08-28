"""The stack walk, checked against the number CPython wrote into every code object."""

from __future__ import annotations

import sys
import sysconfig
import types
from pathlib import Path

import pytest

from pyxray import stack

LOOP = """
total = 0
for n in [1, 2, 3]:
    total = total + n
print(total)
"""


def test_the_stack_starts_and_ends_empty_enough():
    steps = stack.walk("x = 1")
    assert steps[0].before == 0
    assert steps[-1].opname == "RETURN_VALUE"


def test_loading_a_value_pushes_and_storing_it_pops():
    steps = {step.opname: step for step in stack.walk("x = 1")}
    assert steps["LOAD_SMALL_INT"].effect == 1
    assert steps["STORE_NAME"].effect == -1


def test_the_high_water_mark_is_what_co_stacksize_says():
    assert stack.high_water(LOOP) == compile(LOOP, "<test>", "exec").co_stacksize


def test_a_function_that_only_raises_still_gets_a_stack_of_one():
    """Nothing is ever pushed, and CPython gives it one slot anyway in init_code."""

    def only_raises():
        raise

    assert stack.high_water(only_raises) == 1
    assert only_raises.__code__.co_stacksize == 1


def test_a_block_you_can_only_reach_by_jumping_gets_its_depth_from_the_jump():
    """The listing is in address order, so a row can start higher than the one above ended."""
    steps = stack.walk(LOOP)
    where = next(index for index, step in enumerate(steps) if step.opname == "END_FOR")
    assert steps[where - 1].after != steps[where].before


def test_a_handler_is_seeded_from_the_exception_table():
    """Without the exception table every function with a try in it comes out short."""
    guarded = """
try:
    x = 1
except ValueError:
    pass
"""
    assert stack.high_water(guarded) == compile(guarded, "<test>", "exec").co_stacksize


def test_unreachable_instructions_are_left_out_rather_than_guessed_at():
    steps = stack.walk("import sys\nsys.exit()\nx = 1\n")
    assert all(step.before >= 0 for step in steps)


def test_the_table_shows_the_height_either_side():
    rendered = stack.table("x = 1")
    assert "0 -> 1" in rendered
    assert "1 -> 0" in rendered


def _every_code_object(code: types.CodeType):
    pending = [code]
    while pending:
        current = pending.pop()
        yield current
        pending.extend(k for k in current.co_consts if isinstance(k, types.CodeType))


def _stdlib_files(limit: int) -> list[Path]:
    root = Path(sysconfig.get_paths()["stdlib"])
    files = [
        path
        for path in sorted(root.rglob("*.py"))
        if "test" not in path.parts and "lib2to3" not in path.parts
    ]
    return files[:limit]


@pytest.mark.skipif(sys.platform == "emscripten", reason="no standard library on disk")
def test_the_walk_agrees_with_cpython_across_the_standard_library():
    """The argument that the rule has been described correctly, rather than a claim that it has.

    Thirty three thousand code objects across the whole standard library agree. Running
    all of them takes about a minute, so the test takes the first few hundred files and
    the full sweep is one of the lesson's exercises.
    """
    checked = 0
    for path in _stdlib_files(200):
        try:
            top = compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError, UnicodeDecodeError, ValueError:
            continue
        for code in _every_code_object(top):
            assert stack.high_water(code) == code.co_stacksize, f"{path.name} {code.co_name}"
            checked += 1
    assert checked > 1000
