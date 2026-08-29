"""The numbers the animations put on screen, checked against the interpreter running them.

An animation is a claim about CPython that nobody can run. A reader watching a05 cannot
pause it and check that the count really is 2, and a reader watching a04 has no way to know
whether the eight slots on screen are the eight slots CPython made or eight slots somebody
drew because the picture looked better that way. So the claims are checked here instead, and
the constants are read straight out of the scene files rather than copied, because a copy is
a second place to be wrong.

The scene files are parsed rather than imported. Importing one needs manim, these facts do
not, and a check on CPython that only runs when an optional drawing library is installed is
a check that will be quietly skipped in exactly the job where it matters.
"""

from __future__ import annotations

import ast
import ctypes
import dis
import gc
import sys
from pathlib import Path

import pytest

ANIM = Path(__file__).resolve().parents[2] / "anim"


def constant(module: str, name: str) -> object:
    """One module level constant from a scene file, without importing the scene file."""
    tree = ast.parse((ANIM / f"{module}.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{module}.py has no constant called {name}")


class DictKeys(ctypes.Structure):
    """The header of `_dictkeysobject`, up to the point where the index array starts.

    Read against `Objects/dict.c` and `Include/internal/pycore_dict.h`. The three one byte
    fields are followed by a pad byte, which is why `dk_version` lands where it does, and
    `dk_indices` is the flexible array that follows this header in memory.
    """

    _fields_ = (
        ("dk_refcnt", ctypes.c_ssize_t),
        ("dk_log2_size", ctypes.c_uint8),
        ("dk_log2_index_bytes", ctypes.c_uint8),
        ("dk_kind", ctypes.c_uint8),
        ("dk_version", ctypes.c_uint32),
        ("dk_usable", ctypes.c_ssize_t),
        ("dk_nentries", ctypes.c_ssize_t),
    )


class DictObject(ctypes.Structure):
    """`PyDictObject`, which is the object header and then four fields."""

    _fields_ = (
        ("ob_refcnt", ctypes.c_ssize_t),
        ("ob_type", ctypes.c_void_p),
        ("ma_used", ctypes.c_ssize_t),
        ("_ma_watcher_tag", ctypes.c_uint64),
        ("ma_keys", ctypes.c_void_p),
        ("ma_values", ctypes.c_void_p),
    )


def index_array(mapping: dict) -> list[int]:
    """The slot array of a real dict, one number per slot, with -1 for an empty slot.

    This is the array a lookup reads first, and it is the thing a04 draws. There is no
    supported way to see it from Python, so this walks the structs, which is the same thing
    the animation's source note says it did.
    """
    header = DictObject.from_address(id(mapping))
    keys = DictKeys.from_address(header.ma_keys)
    slots = 1 << keys.dk_log2_size
    width = (1 << keys.dk_log2_index_bytes) // slots
    signed = {1: ctypes.c_int8, 2: ctypes.c_int16, 4: ctypes.c_int32, 8: ctypes.c_int64}[width]
    start = header.ma_keys + ctypes.sizeof(DictKeys)
    return [signed.from_address(start + position * width).value for position in range(slots)]


@pytest.fixture(scope="module")
def sample():
    """The dict a04 draws. Integer keys, so nothing here moves when the hash seed changes."""
    return {1: "one", 5: "five", 9: "nine"}


def test_the_slot_array_a04_draws_is_the_one_cpython_made(sample):
    """The eight slots on screen, against the eight slots in memory.

    If CPython ever changes how it lays a small dict out, this fails and the animation gets
    fixed, rather than going on showing a picture of a version nobody runs.
    """
    assert index_array(sample) == list(constant("a04_how_a_dict_finds_a_key", "INDICES"))


def test_the_entries_a04_draws_are_in_insertion_order(sample):
    drawn = constant("a04_how_a_dict_finds_a_key", "ENTRIES")
    assert [(str(key), repr(value)) for key, value in sample.items()] == [
        tuple(pair) for pair in drawn
    ]


def test_the_collision_a04_is_about_is_a_real_collision(sample):
    """Two of the three keys want the same slot, which is the reason for the animation."""
    mask = len(index_array(sample)) - 1
    wanted = [hash(key) & mask for key in sample]
    assert wanted == [1, 5, 1]


def test_a05_has_its_refcounts_right():
    """2 while both names are bound, 1 after `del`, and the pair still there either way.

    The counts are read out of the header rather than through `sys.getrefcount`, because
    passing an object to a function is itself a reference and the animation is about counting
    references exactly.
    """

    class Node:
        __slots__ = ("other",)

    a = Node()
    b = Node()
    a.other = b
    b.other = a
    both = (id(a), id(b))
    assert [ctypes.c_ssize_t.from_address(at).value for at in both] == [2, 2]

    was = gc.isenabled()
    gc.disable()
    try:
        del a, b
        assert [ctypes.c_ssize_t.from_address(at).value for at in both] == [1, 1]
    finally:
        if was:
            gc.enable()


def test_a05_needs_the_collector_to_free_the_pair():
    """One count each and nothing that can reach them, so only the collector gets them."""

    class Node:
        __slots__ = ("other",)

    gc.collect()
    a = Node()
    b = Node()
    a.other = b
    b.other = a
    del a, b
    assert gc.collect() == 2


def test_this_is_the_interpreter_the_animations_are_about():
    """A guard on the struct layouts above, which are read from a particular source tree."""
    assert sys.version_info[:2] >= (3, 14)


# a06 puts two instruction listings on screen and says one is eleven long and the other is
# six. Both of those are what CPython emits for this source and neither is a summary of it,
# so both are checked here instruction by instruction.

A06 = "a06_the_block_nothing_points_at"

#: The three line version the lesson writes, and the one line version the animation draws,
#: which has to fit in a box four units wide.
INDENTED = "if False:\n    x = 1\ny = 2\n"
ONE_LINE = "if False: x = 1\ny = 2\n"


def opnames(instructions):
    """Just the instruction names, which is the half a06 puts on screen."""
    return [one.opname for one in instructions]


def drawn(name):
    """A listing from the scene file, with the arguments stripped back off again."""
    return [line.split(" ")[0] for line in constant(A06, name)]


def test_a06_draws_the_same_program_the_lesson_writes():
    """The animation saves a line by putting the body on the if. It has to be the same code."""
    assert compile(INDENTED, "x", "exec").co_code == compile(ONE_LINE, "x", "exec").co_code


def test_the_eleven_instructions_a06_starts_with_are_what_the_code_generator_emits():
    compiler = pytest.importorskip("pyxray.compiler")
    assert drawn("GENERATED") == opnames(compiler.stages(ONE_LINE).codegen)


def test_the_six_instructions_a06_ends_with_are_what_the_optimizer_leaves():
    compiler = pytest.importorskip("pyxray.compiler")
    assert drawn("FINAL") == opnames(compiler.stages(ONE_LINE).optimized)


def test_the_three_blocks_a06_cuts_are_the_eleven_instructions_and_nothing_else():
    """Cut, not rewritten. Every instruction on screen after the cut was on screen before it."""
    blocks = drawn("ENTRY") + drawn("BODY") + drawn("AFTER")
    assert blocks == drawn("GENERATED")


def test_the_block_a06_deletes_is_the_body_of_the_if():
    assert drawn("BODY") == ["LOAD_CONST", "STORE_NAME"]


def test_the_folding_a06_shows_only_ever_removes_instructions():
    """Each redraw of the entry block is the one before it with something taken out or swapped."""
    assert len(drawn("FOLDED")) == len(drawn("ENTRY")) - 1
    assert len(drawn("JUMPING")) == len(drawn("FOLDED"))


def test_nothing_a06_ends_with_can_store_into_x():
    """The last caption's claim, which is about the instructions and not about the name."""
    code = compile(ONE_LINE, "x", "exec")
    stores = {one.argval for one in dis.get_instructions(code) if one.opname.startswith("STORE")}
    assert stores == {"y"}


def test_the_name_a06_deletes_is_still_in_the_names_table():
    """Why the caption is worded the way it is.

    `x` survives in `co_names` even though every instruction that mentioned it is gone.
    Names are collected while the code is generated and nothing goes back to tidy the table
    up afterwards, so a caption saying x never reached the file would be wrong.
    """
    assert compile(ONE_LINE, "x", "exec").co_names == ("x", "y")
