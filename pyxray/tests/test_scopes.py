"""Tests for the scope table.

Every claim T04 makes about where a name lives is checked here against the interpreter
running the tests, so the lesson fails rather than going quietly wrong if a future CPython
changes its mind. That matters more here than in most of this package, because the whole
lesson rests on the idea that the compiler decided something before the program ran, and a
lesson which asserts that from prose alone is just a person being confident.
"""

from __future__ import annotations

import pytest

from pyxray import scopes

PUZZLE = """\
answer = 42

def show():
    print(answer)

def broken():
    print(answer)
    answer = 1
"""

CLOSURE = """\
def outer():
    total = 0
    def inner():
        nonlocal total
        total += 1
    return inner
"""


def block(source: str, name: str) -> scopes.Block:
    return next(candidate for candidate in scopes.table(source) if candidate.name == name)


def test_the_module_block_is_called_what_dis_calls_it():
    # symtable says "top" and dis says "<module>". Two names for one block is a thing the
    # reader should not have to hold, and the disassembly is the one they will see more of.
    assert block(PUZZLE, "<module>").kind == "module"


def test_every_def_gets_its_own_block():
    assert [candidate.name for candidate in scopes.table(PUZZLE)] == [
        "<module>",
        "show",
        "broken",
    ]


def test_annotation_blocks_are_hidden_unless_you_ask():
    # Since PEP 649 every def gets an __annotate__ block whether or not anything is
    # annotated, so a file of four functions grows four empty blocks nobody asked about.
    names = [candidate.name for candidate in scopes.table(PUZZLE, annotations=True)]
    assert names.count("__annotate__") == 2
    assert "__annotate__" not in [candidate.name for candidate in scopes.table(PUZZLE)]


def test_the_same_name_is_global_in_one_function_and_local_in_the_next():
    # This is the whole lesson in one assertion. Both functions contain the identical line
    # `print(answer)` and the decision about it is different.
    assert block(PUZZLE, "show")["answer"].scope == "global"
    assert block(PUZZLE, "broken")["answer"].scope == "local"


def test_a_later_assignment_changes_the_opcode_on_an_earlier_line():
    # The reader's objection to the puzzle is that the print comes first, so how can a line
    # underneath it matter. It matters because the decision is made per block, not per line.
    assert block(PUZZLE, "show")["answer"].reads == ("LOAD_GLOBAL",)
    assert block(PUZZLE, "broken")["answer"].reads == ("LOAD_FAST_CHECK",)


def test_the_puzzle_really_does_raise():
    namespace: dict[str, object] = {}
    exec(PUZZLE, namespace)
    namespace["show"]()
    with pytest.raises(UnboundLocalError):
        namespace["broken"]()


def test_a_name_read_but_never_assigned_is_global():
    assert block(PUZZLE, "show")["print"].scope == "global"
    assert block(PUZZLE, "show")["print"].why == "it is never assigned in this block"


def test_a_global_statement_wins_over_the_assignment_under_it():
    source = "def f():\n    global answer\n    answer = 1\n"
    binding = block(source, "f")["answer"]
    assert binding.scope == "global"
    assert binding.writes == ("STORE_GLOBAL",)


def test_a_global_statement_inside_a_function_changes_the_module_outside_it():
    # Genuinely surprising and genuinely checkable. Adding the three line function below
    # turns the module's own STORE_NAME into a STORE_GLOBAL.
    plain = "answer = 42\n"
    declared = "answer = 42\ndef f():\n    global answer\n"
    assert block(plain, "<module>")["answer"].writes == ("STORE_NAME",)
    assert block(declared, "<module>")["answer"].writes == ("STORE_GLOBAL",)


def test_an_outer_function_holding_a_shared_name_owns_a_cell():
    binding = block(CLOSURE, "outer")["total"]
    assert binding.scope == "cell"
    assert "MAKE_CELL" in binding.reads


def test_the_inner_function_sees_the_same_name_as_free():
    binding = block(CLOSURE, "inner")["total"]
    assert binding.scope == "free"
    assert binding.reads == ("LOAD_DEREF",)


def test_a_cell_and_a_free_variable_are_read_by_the_same_opcode():
    # The difference between them is who owns the box, not how you open it.
    inner = block(CLOSURE, "inner")["total"]
    assert "LOAD_DEREF" in inner.reads
    assert scopes.SCOPES["cell"] != scopes.SCOPES["free"]


def test_reading_an_enclosing_name_without_nonlocal_is_still_free():
    source = (
        "def outer():\n    total = 0\n    def inner():\n        return total\n    return inner\n"
    )
    assert block(source, "inner")["total"].scope == "free"
    assert block(source, "inner")["total"].why == "assigned in a function around this one"


def test_a_class_body_looks_names_up_while_it_runs():
    source = "class Table:\n    size = 20\n    width = size * 2\n"
    binding = block(source, "Table")["size"]
    assert binding.scope == "name"
    assert binding.reads == ("LOAD_NAME",)


def test_the_same_two_lines_get_frame_slots_inside_a_function():
    # Identical source, one indent level apart, and a different opcode comes out. This is
    # the _PyST_IsFunctionLike branch in _PyCompile_ResolveNameop, visible from Python.
    source = "def build():\n    size = 20\n    width = size * 2\n"
    assert block(source, "build")["size"].reads == ("LOAD_FAST_BORROW",)


def test_a_parameter_is_local_and_says_so():
    binding = block("def f(x):\n    return x\n", "f")["x"]
    assert binding.scope == "local"
    assert binding.why == "it is a parameter"


def test_every_scope_the_table_produces_is_one_of_the_documented_five():
    source = PUZZLE + CLOSURE + "class K:\n    y = 1\n"
    for candidate in scopes.table(source):
        for binding in candidate.bindings:
            assert binding.scope in scopes.SCOPES


def test_every_binding_has_a_reason_written_as_a_sentence():
    for candidate in scopes.table(PUZZLE + CLOSURE):
        for binding in candidate.bindings:
            assert binding.why
            assert binding.why[0].islower()


def test_blocks_come_back_in_reading_order_with_parents_before_children():
    names = [candidate.name for candidate in scopes.table(CLOSURE)]
    assert names == ["<module>", "outer", "inner"]
    assert [candidate.depth for candidate in scopes.table(CLOSURE)] == [0, 1, 2]


def test_names_within_a_block_are_sorted_so_the_table_is_stable():
    names = [binding.name for binding in block(PUZZLE, "<module>").bindings]
    assert names == sorted(names)


def test_looking_up_a_name_that_is_not_there_says_which_block():
    with pytest.raises(KeyError, match="broken"):
        block(PUZZLE, "broken")["nonsense"]


def test_looking_up_a_block_that_is_not_there_says_so():
    with pytest.raises(KeyError, match="no block"):
        scopes.find(PUZZLE, "nonsense", "answer")


def test_find_gives_back_the_one_row_you_asked_for():
    assert scopes.find(PUZZLE, "broken", "answer").scope == "local"


def test_an_attribute_is_not_mistaken_for_a_name():
    # STORE_ATTR carries an attribute in its argument, and counting it as a write would put
    # a row in the table for something that is not a variable at all.
    source = "def f(thing):\n    thing.size = 1\n    return thing.size\n"
    assert [binding.name for binding in block(source, "f").bindings] == ["thing"]


def test_the_null_marker_on_a_call_does_not_hide_the_name():
    # LOAD_GLOBAL prints `print + NULL` when the call sequence wants a spare stack slot.
    # Reading that literally loses every function a block calls.
    assert block("def f():\n    print(1)\n", "f")["print"].reads == ("LOAD_GLOBAL",)


COMPREHENSION_IN_A_CLASS = """\
class K:
    rows = [1, 2]
    factor = 3
    doubled = [r * factor for r in rows]
"""


def test_a_comprehension_in_a_class_body_really_does_raise():
    with pytest.raises(NameError, match="factor"):
        exec(COMPREHENSION_IN_A_CLASS, {})


def test_the_first_iterable_of_a_comprehension_is_read_by_the_class_body():
    # `rows` is evaluated before the comprehension starts, so it gets the class body's own
    # lookup and works. This is the half of the line that people expect to work.
    assert block(COMPREHENSION_IN_A_CLASS, "K")["rows"].reads == ("LOAD_NAME",)


def test_a_name_used_inside_a_comprehension_body_skips_the_class_body():
    # And this is the half that does not. Same block, three lines apart, different opcode,
    # and LOAD_GLOBAL will not find a class attribute no matter how recently it was assigned.
    assert block(COMPREHENSION_IN_A_CLASS, "K")["factor"].reads == ("LOAD_GLOBAL",)


def test_opcodes_gives_the_instructions_of_one_block():
    listing = scopes.opcodes(PUZZLE, "broken")
    assert ("LOAD_FAST_CHECK", "answer") in listing
    assert ("STORE_FAST", "answer") in listing


def test_opcodes_can_be_asked_for_the_module():
    assert ("STORE_NAME", "show") in scopes.opcodes(PUZZLE, "<module>")


def test_opcodes_complains_about_a_block_that_was_never_compiled():
    with pytest.raises(KeyError, match="nonsense"):
        scopes.opcodes(PUZZLE, "nonsense")


def test_show_prints_every_block_and_every_name():
    text = scopes.show(PUZZLE)
    assert "<module>" in text
    assert "broken" in text
    assert "LOAD_FAST_CHECK" in text


def test_the_five_scopes_are_documented_in_the_order_a_reader_meets_them():
    assert list(scopes.SCOPES) == ["local", "cell", "free", "global", "name"]
