from __future__ import annotations

import gc
import sys

import pytest

from pyxray import obj


class Plain:
    """A type with a __dict__, so instances are tracked by the collector."""


def test_a_freshly_bound_object_has_exactly_one_reference():
    """The number a beginner expects, which is the whole reason refcount subtracts one."""
    value = Plain()
    assert obj.refcount(value) == 1


def test_binding_a_second_name_makes_it_two():
    first = Plain()
    second = first
    assert obj.refcount(first) == 2
    del second
    assert obj.refcount(first) == 1


def test_putting_an_object_in_a_list_counts_as_a_reference():
    value = Plain()
    holder = [value, value]
    assert obj.refcount(value) == 3
    holder.clear()
    assert obj.refcount(value) == 1


GLOBAL_VALUE = Plain()


def test_the_answer_does_not_depend_on_where_the_variable_lives():
    """The point of the whole correction. A global and a local both hold one reference.

    Before 3.14 both call sites cost one reference and a constant subtraction worked. Then
    `LOAD_FAST_BORROW` arrived, locals stopped costing anything, and a fixed correction
    started reporting 0 for a local and 1 for a global holding the same single reference.
    """
    local_value = Plain()
    assert obj.refcount(local_value) == 1
    assert obj.refcount(GLOBAL_VALUE) == 1


def test_reading_through_an_attribute_costs_a_reference_and_is_accounted_for():
    """`LOAD_ATTR` hands over a new reference, unlike `LOAD_FAST_BORROW`, and it is counted.

    The read happens inside a helper on purpose. Writing it directly in the assert would
    have pytest rewrite the expression and stash the attribute in a temporary of its own,
    which is a third reference that has nothing to do with what the test is about.
    """

    class Box:
        pass

    def read(container):
        return obj.refcount(container.thing)

    box = Box()
    box.thing = Plain()
    assert read(box) == 1


def test_the_raw_number_is_still_available_and_still_disagrees():
    """The lesson needs both numbers on screen to explain why they differ."""
    local_value = Plain()
    assert obj.raw_refcount(local_value) == 1
    assert obj.raw_refcount(GLOBAL_VALUE) == 2


def test_a_borrowing_load_is_what_makes_the_difference():
    """If this ever fails, the correction in refcount needs revisiting rather than the test."""
    import dis

    def uses_a_local(value):
        return obj.refcount(value)

    names = [i.opname for i in dis.get_instructions(uses_a_local)]
    assert "LOAD_FAST_BORROW" in names
    assert uses_a_local(Plain()) == 1


def test_a_call_the_module_cannot_inspect_falls_back_rather_than_raising():
    assert obj._caller_load_cost(None) == 1


@pytest.mark.parametrize("value", [None, True, False, Ellipsis, NotImplemented, int, str, object])
def test_the_singletons_and_the_types_are_immortal(value):
    assert obj.is_immortal(value)
    assert obj.refcount(value) is None


def test_an_ordinary_object_is_not_immortal():
    assert not obj.is_immortal(Plain())
    assert not obj.is_immortal([1, 2, 3])


def test_immortal_objects_report_no_count_rather_than_a_parked_one():
    """Printing 3221225472 beside a paragraph on reference counting teaches the wrong model."""
    assert obj.refcount(None) is None
    assert obj.header(None).describe().count("reference(s)") == 0


def test_header_reports_the_identity_and_the_size_the_interpreter_reports():
    value = [1, 2, 3]
    head = obj.header(value)
    assert head.address == id(value)
    assert head.type_name == "list"
    assert head.size == sys.getsizeof(value)


def test_a_list_is_tracked_and_an_int_is_not():
    """The collector is opt in per type, and this is where a reader first meets that."""
    assert obj.header([]).gc_tracked
    assert obj.header([]).gc_trackable
    assert not obj.header(1000000).gc_tracked
    assert not obj.header(1000000).gc_trackable


def test_a_tuple_of_immutables_gets_untracked_but_stays_trackable():
    """A tuple that cannot form a cycle is dropped from the collector, yet its type still can."""
    value = (1, 2, 3)
    gc.collect()
    assert obj.header(value).gc_trackable
    assert not obj.header(value).gc_tracked


def test_describe_reads_as_a_sentence():
    text = obj.header([]).describe()
    assert text.startswith("list at 0x")
    assert "tracked by the cycle collector" in text
    assert "\n" not in text


def test_small_integers_are_shared_and_large_ones_are_not():
    assert obj.shares_identity(5)
    assert not obj.shares_identity(10**9)


def test_the_small_integer_range_is_probed_not_assumed():
    low, high = obj.small_int_range()
    assert low == -5, "the negative bound has not moved since the cache was introduced"
    assert obj.shares_identity(high)
    assert not obj.shares_identity(high + 1)
    assert obj.shares_identity(low)
    assert not obj.shares_identity(low - 1)


def test_the_upper_bound_moved_in_3_15():
    """See issue 33. Every tutorial that hard coded 256 became wrong without being told."""
    _, high = obj.small_int_range()
    expected = 1024 if sys.version_info >= (3, 15) else 256
    assert high == expected


def test_the_canonical_257_example_is_version_dependent():
    """`257 is 257` is the example every beginner is shown, and on 3.15 it flipped."""
    _, high = obj.small_int_range()
    assert obj.shares_identity(257) == (high >= 257)


def test_the_compiler_shares_equal_constants_inside_one_code_object():
    """The classic identity demo is contaminated by the compiler, not by the integer cache.

    Two occurrences of a large integer in one compiled unit are the same object because
    the compiler stored one constant, which has nothing to do with the small integer
    cache. This is why the cache probe builds its integers with `int(str(n))`.
    """
    code = compile("a = 10**9\nb = 10**9\n", "<test>", "exec")
    scope: dict = {}
    exec(code, scope)
    assert scope["a"] is scope["b"]
    assert not obj.shares_identity(10**9)


def test_an_identifier_shaped_literal_is_interned():
    assert obj.is_interned("append")


def test_a_string_built_at_runtime_is_not_interned():
    built = "".join(["ap", "pend"])
    assert not obj.is_interned(built)
    assert built == "append"


def test_asking_whether_a_string_is_interned_does_not_intern_it():
    """A probe that changes what it measures would answer True forever after the first call."""
    built = "".join(["ap", "pend"])
    assert not obj.is_interned(built)
    assert not obj.is_interned(built)
    assert not obj.is_interned(built)


def test_interning_a_built_string_makes_the_original_the_interned_one():
    built = "".join(["not", "_a_literal_anywhere"])
    kept = sys.intern(built)
    assert kept is built
    assert obj.is_interned(built)


def test_the_empty_string_answers_rather_than_raising():
    # There is exactly one empty string in the process, so the usual trick of building an
    # equal copy and seeing which object comes back has nothing to compare against. That
    # is the answer rather than a failure, and it used to raise instead. See #51.
    empty = ""
    assert obj.is_interned(empty)
    assert "".join([empty, empty]) is empty


def test_referrers_finds_a_container_and_skips_the_frame():
    value = Plain()
    holder = {"key": value}
    names = obj.referrers(value)
    assert any(name.startswith("dict at 0x") for name in names)
    assert not any(name.startswith("frame at 0x") for name in names)
    assert names == sorted(names)
    del holder


def test_is_immortal_falls_back_when_the_interpreter_offers_no_direct_question(monkeypatch):
    """The fallback path is what runs on 3.11 and earlier, and it still has to be right."""
    monkeypatch.delattr(sys, "_is_immortal", raising=False)
    assert obj.is_immortal(None)
    assert not obj.is_immortal(Plain())
