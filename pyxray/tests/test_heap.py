from __future__ import annotations

import gc
import sys

import pytest

from pyxray import heap


class Node:
    """A container with one outgoing reference, which is all a cycle needs."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.other: Node | None = None


def test_label_names_the_type_and_the_address():
    value = Node("a")
    text = heap.label(value)
    assert text.startswith("Node at 0x")
    assert hex(id(value)) in text


def test_a_graph_with_no_cycle_reports_none():
    first = Node("first")
    second = Node("second")
    first.other = second
    assert heap.cycles(first) == []


def test_two_objects_pointing_at_each_other_are_one_cycle():
    first = Node("first")
    second = Node("second")
    first.other = second
    second.other = first

    found = heap.cycles(first)
    assert len(found) == 1
    assert len(found[0].members) == 2


def test_an_object_pointing_at_itself_counts():
    """The smallest cycle there is, and the one the CPython docs open with."""
    alone = []
    alone.append(alone)
    found = heap.cycles(alone)
    assert len(found) == 1
    assert found[0].members == (heap.label(alone),)


def test_a_longer_loop_is_found_whole():
    ring = [Node(str(n)) for n in range(5)]
    for index, node in enumerate(ring):
        node.other = ring[(index + 1) % 5]

    found = heap.cycles(ring[0])
    assert len(found) == 1
    assert len(found[0].members) == 5


def test_two_separate_cycles_are_reported_separately():
    left = Node("left")
    left.other = left
    right = Node("right")
    right.other = right
    holder = [left, right]

    found = heap.cycles(holder)
    assert len(found) == 2


def test_describe_reads_as_a_loop():
    first = Node("first")
    second = Node("second")
    first.other = second
    second.other = first

    text = heap.cycles(first)[0].describe()
    assert text.count("->") == 2
    assert text.split(" -> ")[0] == text.split(" -> ")[-1]


def test_the_walk_stops_at_a_class_rather_than_escaping_into_the_module():
    """Following __class__ would reach the module, then everything it imported."""
    value = Node("alone")
    seen = heap.reachable(value)
    assert not any(isinstance(item, type) for item in seen.values())


def test_a_walk_that_escapes_is_refused_rather_than_left_to_run():
    with pytest.raises(ValueError, match="route out into the interpreter"):
        heap.reachable([Node(str(n)) for n in range(20)], limit=5)


def test_untracked_objects_are_not_walked_into():
    """An int cannot hold a reference, so it can never be on a cycle or a path to one."""
    holder = [1, 2, "three"]
    seen = heap.reachable(holder)
    assert list(seen.values()) == [holder]


def test_the_cycle_report_does_not_keep_the_cycle_alive():
    """A tool for finding objects that outlive their names must not become one of them."""
    watcher = heap.Deaths()
    first = watcher.watch("first", Node("first"))
    second = Node("second")
    first.other = second
    second.other = first

    assert len(heap.cycles(first)) == 1
    del first, second
    gc.collect()
    assert not watcher.alive("first")


def test_a_plain_object_dies_the_moment_its_last_name_goes():
    watcher = heap.Deaths()
    value = watcher.watch("value", Node("value"))
    assert watcher.alive("value")
    assert watcher.gone == []

    del value
    assert not watcher.alive("value")
    assert watcher.gone == ["value"]


def test_a_cycle_outlives_its_names_and_needs_the_collector():
    """The whole reason the cycle collector exists, in five lines."""
    watcher = heap.Deaths()
    first = watcher.watch("first", Node("first"))
    second = watcher.watch("second", Node("second"))
    first.other = second
    second.other = first

    del first, second
    assert watcher.alive("first"), "reference counting cannot free a cycle"

    gc.collect()
    assert not watcher.alive("first")
    assert sorted(watcher.gone) == ["first", "second"]


def test_deaths_are_recorded_in_the_order_they_happen():
    watcher = heap.Deaths()
    first = watcher.watch("first", Node("first"))
    second = watcher.watch("second", Node("second"))

    del second
    del first
    assert watcher.gone == ["second", "first"]


def test_report_lines_up_one_name_per_line():
    watcher = heap.Deaths()
    kept = watcher.watch("kept", Node("kept"))
    dropped = watcher.watch("dropped", Node("dropped"))
    del dropped

    lines = watcher.report().splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("kept") and lines[0].endswith("alive")
    assert lines[1].startswith("dropped") and lines[1].endswith("freed")
    assert kept is not None


def test_watching_something_that_cannot_be_weakly_referenced_explains_itself():
    watcher = heap.Deaths()
    with pytest.raises(TypeError, match="cannot be weakly referenced"):
        watcher.watch("number", 42)


def test_an_untracked_object_has_no_generation():
    assert heap.generation_of(42) is None
    assert heap.generation_of("text") is None


def test_a_new_container_starts_in_generation_zero():
    gc.collect()
    value = Node("fresh")
    assert heap.generation_of(value) == 0


def test_surviving_a_collection_moves_it_up():
    gc.collect()
    value = Node("survivor")
    assert heap.generation_of(value) == 0
    gc.collect(0)
    assert heap.generation_of(value) == 1


def test_allocated_blocks_is_a_number_or_an_honest_none():
    count = heap.allocated()
    assert count is None or count > 0


def test_allocating_raises_the_block_count():
    if heap.allocated() is None:
        pytest.skip("this build has no small object allocator to ask")
    before = heap.allocated()
    kept = [Node(str(n)) for n in range(500)]
    after = heap.allocated()
    assert after > before
    assert len(kept) == 500


def test_sizes_reports_what_getsizeof_reports():
    rows = heap.sizes([[], {}, "a"])
    assert [size for _, size in rows] == [sys.getsizeof([]), sys.getsizeof({}), sys.getsizeof("a")]
    assert rows[0][0].startswith("list at 0x")
