"""The named objects, built for real.

These need manim, which is a large install and is not there in the normal test run, so the
whole module skips without it. What is worth testing here is not what the pictures look
like, which no assertion can tell you, but the parts each object promises to expose. An
animation reaches for `obj.count` or `strip.pointer` by name, so those names are the API and
a rename that quietly breaks a scene should break a test first.
"""

from __future__ import annotations

import pytest

pytest.importorskip("manim", reason="the drawing half of xraymanim, installed by --extra anim")

from xraymanim.mobjects import (
    ArenaMap,
    CodeStrip,
    DictTable,
    Frame,
    PyObjectBox,
    RefArrow,
)
from xraymanim.primitives import box


def test_an_object_has_a_type_and_a_count_whether_or_not_it_has_a_value():
    """The header is `PyObject`, and the point of the shape is that it is always drawn."""
    empty = PyObjectBox("object")
    assert empty.value is None
    assert "ob_type" in empty.type_name.text
    assert empty.count is not None


def test_the_count_sits_inside_the_object():
    """Outside and it reads as a note about the object rather than a field of it."""
    thing = PyObjectBox("list", "[]", 2)
    left, right = thing.shell.get_left()[0], thing.shell.get_right()[0]
    assert left < thing.count.get_center()[0] < right


def test_a_new_refcount_lands_where_the_old_one_was():
    """Which is what makes `Transform(obj.count, obj.refcount(2))` animate a digit changing."""
    thing = PyObjectBox("list", "[]", 1)
    replacement = thing.refcount(2)
    assert replacement.get_center() == pytest.approx(thing.count.get_center())


def test_owned_and_borrowed_references_are_told_apart_by_the_line():
    here, there = box("a"), box("b").shift([4, 0, 0])
    owned = RefArrow(here, there, owned=True)
    borrowed = RefArrow(here, there, owned=False)
    assert owned.owned and not borrowed.owned
    assert owned.body.line.stroke_width > borrowed.body.line.stroke_width


def test_a_frame_has_a_name_its_locals_and_a_stack():
    frame = Frame("greet", {"name": "'ada'"}, ["'ada'", "print"])
    assert frame.title.text == "greet"
    assert len(frame.locals.submobjects) >= 1
    assert len(frame.stack.submobjects) >= 1


def test_a_frame_with_nothing_in_it_still_draws_both_regions():
    """An empty frame is a real thing, so it should not come out as a box with a hole in it."""
    frame = Frame("main")
    assert frame.locals is not None
    assert frame.stack is not None


def test_the_pointer_moves_and_the_code_stays_put():
    strip = CodeStrip(["RESUME 0", "LOAD_SMALL_INT 42", "STORE_NAME 0"])
    first = strip.strip.get_center().copy()
    started = strip.pointer.get_center().copy()
    strip.point_at(2)
    assert strip.strip.get_center() == pytest.approx(first)
    assert strip.pointer.get_center()[0] > started[0]


def test_asking_where_an_instruction_is_does_not_move_the_pointer():
    """`at` is for animating the pointer somewhere, so it has to leave the strip alone."""
    strip = CodeStrip(["RESUME 0", "LOAD_SMALL_INT 42"])
    where = strip.pointer.get_center().copy()
    strip.at(1)
    assert strip.pointer.get_center() == pytest.approx(where)


def test_a_dict_is_drawn_as_an_index_and_entries_and_not_as_one_table():
    """The split is the lesson. A single table of pairs teaches the wrong thing about order."""
    table = DictTable([("name", "'ada'"), ("age", "36")], index=["-", "0", "-", "1"])
    assert len(table.index.submobjects) == 4
    assert len(table.entries.submobjects) == 2
    assert table.entries.get_center()[0] > table.index.get_center()[0]


def test_an_arena_draws_free_blocks_as_well_as_used_ones():
    """Free memory is still memory the process holds, so it gets a cell rather than a gap."""
    arena = ArenaMap("##..*...", columns=4)
    assert len(arena.cells.submobjects) == 8


def test_an_unknown_block_says_what_the_states_are():
    with pytest.raises(ValueError) as raised:
        ArenaMap("##?.")
    assert "'*'" in str(raised.value) and "'#'" in str(raised.value)
