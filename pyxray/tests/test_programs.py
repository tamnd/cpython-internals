"""Tests for the three canonical programs.

These three get reused by every lesson from here on, which means a quiet edit to one of
them would change the disassembly printed in a lesson written a year earlier. So the point
of this file is less "does the code work" and more "is it still the same program", and the
assertions are written to fail loudly and say what moved.

The other half of the file checks the claims each program makes about itself. `L2` says it
is carrying a generator, a closure, a dict and an exception table, and if somebody tidies
one of those away while refactoring, the lesson that was going to point at it breaks
silently. Each claim in `Program.exercises` has an assertion here holding it up.
"""

from __future__ import annotations

import types

import pytest

from pyxray import bytecode, heap, programs

NAMES = ("a", "b", "c")

#: What a program is allowed to grow to before it stops fitting on a screen next to a
#: disassembly, which is the whole reason these three are small.
BUDGET = {"L0": 1, "L1": 10, "L2": 65}


@pytest.mark.parametrize("program", programs.ALL, ids=lambda p: p.name)
def test_each_program_gives_back_the_answer_written_next_to_it(program):
    assert program.run() == program.answer


@pytest.mark.parametrize("program", programs.ALL, ids=lambda p: p.name)
def test_each_program_stays_small_enough_to_read(program):
    assert program.lines <= BUDGET[program.name]


@pytest.mark.parametrize("program", programs.ALL, ids=lambda p: p.name)
def test_the_code_objects_say_which_program_they_came_from(program):
    # A traceback out of a lesson should name L1 rather than "<string>", which is what
    # every other exec'd snippet in the notebook also says.
    assert program.code().co_filename == f"<{program.name}>"


@pytest.mark.parametrize("program", programs.ALL, ids=lambda p: p.name)
def test_loading_twice_gives_two_separate_sets_of_objects(program):
    # Lessons measure reference counts on these. Caching the namespace would mean one
    # lesson counting the references another lesson left behind.
    assert program.load() is not program.load()


def test_the_three_have_the_names_the_prose_uses():
    assert [program.name for program in programs.ALL] == ["L0", "L1", "L2"]


def test_lookup_does_not_care_about_case():
    assert programs.get("l1") is programs.L1
    assert programs.get(" L2 ") is programs.L2


def test_asking_for_one_that_does_not_exist_says_what_there_is():
    with pytest.raises(KeyError, match="L0, L1, L2"):
        programs.get("L9")


def test_the_summary_mentions_all_three():
    text = programs.summary()
    assert all(program.name in text for program in programs.ALL)


def test_describe_ends_with_the_source_so_a_cell_can_print_just_that():
    assert programs.L0.describe().endswith(programs.L0.source)


# L0, one line.


def test_l0_has_no_multiply_left_in_it():
    # This is the payoff of T01 and it is the reason L0 is `6 * 7` and not `x = 1 + 2`.
    # The multiplication happened while the file was being compiled, so there is nothing
    # arithmetic left for the interpreter to do.
    assert "BINARY_OP" not in bytecode.opnames(programs.L0.code())


def test_l0_pushes_the_answer_as_a_small_integer():
    assert "LOAD_SMALL_INT" in bytecode.opnames(programs.L0.code())


def test_l0_still_carries_the_six_that_nothing_loads():
    # The operands were folded away but one of them is still sitting in the constants,
    # unreferenced, which is a good first question to hand a reader.
    code = programs.L0.code()
    assert 6 in code.co_consts
    assert 42 not in code.co_consts


def test_l0_binds_its_name_the_module_level_way():
    # Not STORE_FAST and not STORE_GLOBAL. Module level binding is its own thing and this
    # is the first place a reader meets it.
    assert "STORE_NAME" in bytecode.opnames(programs.L0.code())


# L1, the loop.


def test_l1_has_a_loop_with_a_jump_that_goes_backwards():
    names = bytecode.opnames(programs.L1.target())
    assert "FOR_ITER" in names
    assert any(jump.backwards for jump in bytecode.jumps(programs.L1.target()))


def test_l1_calls_a_builtin_rather_than_a_function_in_the_file():
    # `range` is looked up as a global and turns out to be a builtin, which is a different
    # call path to a Python function and the reason the specialization lessons use it.
    assert "LOAD_GLOBAL" in bytecode.opnames(programs.L1.target())


def test_l1_does_its_arithmetic_at_run_time():
    # The opposite of L0, and deliberately so. Nothing here can be folded, because the
    # numbers are not known until the loop runs.
    assert "BINARY_OP" in bytecode.opnames(programs.L1.target())


def test_one_call_is_enough_to_specialize_the_loop():
    # This is why L1 is the program for the interpreter lessons: a single call warms the
    # two instructions inside the loop, so a reader sees specialization without having to
    # be told to run something ten thousand times first.
    fib = programs.L1.target()
    before = set(bytecode.opnames(fib, adaptive=True))
    fib(*programs.L1.args)
    after = set(bytecode.opnames(fib, adaptive=True))
    assert {"BINARY_OP_ADD_INT", "FOR_ITER_RANGE"} <= after - before


def test_l1_stays_in_the_fast_integer_path():
    # `fib(30)` is 832040, which fits in a machine word, so the addition stays on the
    # fast path the whole way. That is on purpose: the lesson that shows the slow path
    # should be able to reach for a bigger argument and get it.
    assert programs.L1.answer.bit_length() < 63


# L2, the linked structure.


def test_l2_instances_keep_their_attributes_in_a_dict():
    node = programs.L2.load().Node("a")
    assert node.__dict__ == {"name": "a", "next": None}


def test_l2_walks_forward_with_a_generator():
    namespace = programs.L2.load()
    walker = namespace.forward(namespace.chain(NAMES))
    assert isinstance(walker, types.GeneratorType)
    assert [node.name for node in walker] == list(NAMES)


def test_l2_puts_its_counter_in_a_cell():
    # `nonlocal count` is what makes this a cell rather than a local, and a cell is the
    # thing T04 spends a lesson on.
    namespace = programs.L2.load()
    assert namespace.labeller.__code__.co_cellvars == ("prefix", "count")
    assert "count" in namespace.labeller("n").__code__.co_freevars


def test_l2_labels_count_up_across_calls():
    label = programs.L2.load().labeller("n")
    node = programs.L2.load().Node("a")
    assert [label(node), label(node)] == ["n1:a", "n2:a"]


def test_l2_has_an_exception_table_rather_than_instructions():
    # try, except and finally do not compile to opcodes that mark the block. They compile
    # to a side table of ranges, which is a thing readers reliably guess wrong.
    namespace = programs.L2.load()
    assert namespace.index.__code__.co_exceptiontable


def test_l2_inlines_its_comprehension():
    # Comprehensions stopped getting a scope of their own in 3.12, so `chain` has no
    # nested code object and the loop variable is one of its own locals.
    namespace = programs.L2.load()
    nested = [
        const for const in namespace.chain.__code__.co_consts if isinstance(const, types.CodeType)
    ]
    assert nested == []


def test_l2_builds_no_cycle_unless_you_ask_for_one():
    # A module that left a cycle lying around would turn up in somebody else's lesson
    # about garbage, so the ring is opt in.
    namespace = programs.L2.load()
    assert heap.cycles(namespace.chain(NAMES)) == []


def test_l2_builds_a_real_cycle_when_you_do():
    namespace = programs.L2.load()
    found = heap.cycles(namespace.chain(NAMES, ring=True))
    assert len(found) == 1
    assert len(found[0].members) == len(NAMES)


def test_l2_stops_walking_a_ring_at_the_limit():
    # The ring has no end, so the limit is the only thing that stops the walk. Seven steps
    # round three nodes is `a b c a b c a`, which is what the labels should say.
    namespace = programs.L2.load()
    walked = namespace.index(namespace.chain(NAMES, ring=True), 7)
    assert list(walked) == ["n1:a", "n2:b", "n3:c", "n4:a", "n5:b", "n6:c", "n7:a"]


def test_l2_runs_out_of_chain_before_it_runs_out_of_limit():
    # The other branch of the same try. An open chain raises StopIteration on the fourth
    # `next`, which is caught, and the finally still closes the generator.
    namespace = programs.L2.load()
    walked = namespace.index(namespace.chain(NAMES), 10)
    assert list(walked) == ["n1:a", "n2:b", "n3:c"]
