from __future__ import annotations

import dis
import sys

import pytest

from pyxray import compiler

NESTED = """\
def outer(a):
    b = a
    def inner():
        return b
    return inner
"""


LAMBDA = "f = lambda x: x + 1\n"


def scope_named(root, name):
    for scope in root.walk():
        if scope.name == name:
            return scope
    raise AssertionError(f"no scope named {name!r} in\n{root.tree()}")


def only_function(root):
    """The one function scope under this root, found by kind rather than by name.

    Lambdas are the reason. The scope CPython builds for one changed name in 3.15, so a
    test that says `<lambda>` out loud is a test that only passes on one interpreter.
    """
    found = [scope for scope in root.walk() if scope.kind == "function"]
    assert len(found) == 1, f"expected one function scope, got {[s.name for s in found]}"
    return found[0]


def test_the_module_scope_is_called_top_and_has_no_line():
    """CPython names the outermost table 'top' and gives it line 0, because it has no def."""
    root = compiler.symbols("answer = 6 * 7\n")
    assert root.name == "top"
    assert root.kind == "module"
    assert root.line == 0
    assert not root.nested


def test_a_module_level_name_is_both_local_and_global():
    """This looks like a contradiction and is the most useful thing the table will tell you.

    A name bound at module level is stored in the module's own namespace, so it is local
    to that scope. It is also the thing every function in the file will reach for when it
    reads that name, so it is a global. Both answers are true at once, and reporting only
    one of them is where most explanations of Python scope go wrong.
    """
    answer = compiler.symbols("answer = 6 * 7\n").lookup("answer")
    assert "local" in answer
    assert "global" in answer
    assert "assigned" in answer


def test_a_name_that_is_never_bound_is_global_and_not_local():
    root = compiler.symbols("print(value)\n")
    assert "global" in root.lookup("print")
    assert "local" not in root.lookup("print")
    assert "assigned" not in root.lookup("value")


def test_a_parameter_is_a_parameter_and_a_local():
    outer = scope_named(compiler.symbols(NESTED), "outer")
    assert "parameter" in outer.lookup("a")
    assert "local" in outer.lookup("a")
    assert "global" not in outer.lookup("a")


def test_a_closure_variable_is_free_in_the_scope_that_reads_it():
    """The single decision that makes closures work, made here, before any code is generated.

    `b` is written in `outer` and read in `inner`. The table marks it free in `inner`,
    meaning do not look for a local slot, read it out of the box the enclosing frame
    handed over.
    """
    inner = scope_named(compiler.symbols(NESTED), "inner")
    assert "free" in inner.lookup("b")
    assert "local" not in inner.lookup("b")


@pytest.mark.skipif("cell" not in compiler.questions(), reason="Symbol.is_cell is new in 3.15")
def test_a_closure_variable_is_a_cell_in_the_scope_that_owns_it():
    """The other half of the same decision: `outer` has to put `b` in a box, not a slot."""
    assert "cell" in scope_named(compiler.symbols(NESTED), "outer").lookup("b")


def test_only_3_15_can_be_asked_whether_a_name_is_a_cell():
    """`Symbol.is_cell` is new in 3.15, and on 3.14 a cell is indistinguishable from a local.

    Worth knowing before trusting the flags in a lesson written on one version and read on
    another. On 3.14 `is_local` answers yes for both cases, so the box is invisible from
    Python even though the compiler has already decided to build one.
    """
    assert ("cell" in compiler.questions()) == (sys.version_info >= (3, 15))
    outer = scope_named(compiler.symbols(NESTED), "outer")
    assert "local" in outer.lookup("b") or "cell" in outer.lookup("b")


def test_the_global_statement_takes_a_name_out_of_the_local_scope():
    source = "def f():\n    global counter\n    counter = 1\n"
    counter = scope_named(compiler.symbols(source), "f").lookup("counter")
    assert "declared global" in counter
    assert "global" in counter
    assert "local" not in counter


def test_the_nonlocal_statement_makes_a_name_free_rather_than_local():
    source = "def outer():\n    n = 0\n    def inner():\n        nonlocal n\n        n = 1\n"
    inner = scope_named(compiler.symbols(source), "inner")
    assert "nonlocal" in inner.lookup("n")
    assert "free" in inner.lookup("n")
    assert "local" not in inner.lookup("n")


def test_an_import_is_recorded_as_an_import():
    assert "imported" in compiler.symbols("import json\n").lookup("json")


def test_a_class_body_is_its_own_scope():
    root = compiler.symbols("class C:\n    z = 1\n")
    body = scope_named(root, "C")
    assert body.kind == "class"
    assert "local" in body.lookup("z")
    assert "namespace" in root.lookup("C")


def test_a_lambda_gets_a_function_scope_of_its_own():
    body = only_function(compiler.symbols(LAMBDA))
    assert body.kind == "function"
    assert "parameter" in body.lookup("x")


def test_the_lambda_scope_was_renamed_in_3_15():
    """It was `lambda` through 3.14 and is `<lambda>` from 3.15, matching `co_name`.

    Python/symtable.c:2506-2513@v3.15.0rc1#anon_lambda now passes `_Py_STR(anon_lambda)`,
    which is defined as the string `<lambda>`. Anything that looks the scope up by name
    across versions has to know this, which is exactly why it is written down as a test
    rather than as a comment.
    """
    name = only_function(compiler.symbols(LAMBDA)).name
    assert name == ("<lambda>" if sys.version_info >= (3, 15) else "lambda")
    assert (lambda x: x).__name__ == "<lambda>"


def test_nested_means_inside_a_function_and_not_merely_indented():
    """A lambda written at module level is not nested, and a class body is not either.

    The flag is about whether there is an enclosing function whose locals this block could
    capture, which is the only thing the compiler needs it for. A lambda at the top of a
    file has nothing to capture, so it answers no despite sitting inside another scope.
    """
    assert not only_function(compiler.symbols(LAMBDA)).nested
    assert not scope_named(compiler.symbols("class C:\n    z = 1\n"), "C").nested
    assert scope_named(compiler.symbols(NESTED), "inner").nested


def test_a_comprehension_no_longer_gets_its_own_scope():
    """Comprehensions were inlined in 3.12, and the symbol table is where you can see it.

    Before that change every list comprehension built a whole function scope and called
    it, which is why the loop variable could not leak and why comprehensions were slower
    than the loop they replaced. Now `x` is an ordinary local of the enclosing function.
    """
    root = compiler.symbols("def f(y):\n    return [x for x in y]\n")
    body = scope_named(root, "f")
    assert [child.kind for child in body.children if child.kind == "function"] == []
    assert "local" in body.lookup("x")


def test_every_def_builds_an_annotation_scope_even_with_no_annotations():
    """PEP 649 arrived in 3.14 and left a fingerprint on code that has nothing to annotate.

    Annotations are now evaluated lazily by a generated `__annotate__` function, and the
    symbol table builds a scope for it whether or not the def has a single annotation on
    it. It is the first thing that looks wrong in the output here, so the test exists to
    say that it is expected.
    """
    root = compiler.symbols("def f(a):\n    return a\n")
    annotation = scope_named(root, "__annotate__")
    assert annotation.kind == "annotation"
    assert sys.version_info >= (3, 14)


def test_looking_up_a_name_this_scope_never_sees_returns_none():
    """`symtable.SymbolTable.lookup` raises KeyError, which makes the obvious question hard."""
    root = compiler.symbols("answer = 6 * 7\n")
    assert root.lookup("nothing_here") is None


def test_walk_yields_the_outermost_scope_first():
    root = compiler.symbols(NESTED)
    names = [scope.name for scope in root.walk()]
    assert names[0] == "top"
    assert names.index("outer") < names.index("inner")


def test_the_tree_puts_every_name_on_its_own_line():
    text = compiler.symbols(NESTED).tree()
    assert "function 'inner'" in text
    assert any(line.strip().startswith("b: ") for line in text.splitlines())
    assert str(compiler.symbols(NESTED)) == text


def test_a_symbol_prints_as_a_name_and_its_answers():
    answer = compiler.symbols("answer = 6 * 7\n").lookup("answer")
    assert str(answer).startswith("answer: ")
    assert "local" in str(answer)


def test_a_symbol_with_no_flags_says_so_rather_than_printing_nothing():
    assert str(compiler.Symbol("x", ())) == "x: no flags set"


@pytest.mark.skipif(
    not compiler.available(),
    reason="this interpreter does not export _testinternalcapi",
)
def test_the_table_decides_which_load_instruction_gets_generated():
    """The whole reason this stage exists, shown end to end.

    The compiler cannot pick an opcode for `a` until it knows what `a` is. Local means a
    numbered slot in the frame and one of the LOAD_FAST family. Global means a dictionary
    lookup by name and LOAD_GLOBAL. The answer comes from the symbol table, so the two
    should agree, and here they do.
    """
    result = compiler.stages("def f(a):\n    return a + b\n")
    body = scope_named(result.scope, "f")
    assert "local" in body.lookup("a")
    assert "global" in body.lookup("b")

    inner = next(c for c in result.code.co_consts if hasattr(c, "co_code"))
    loads = {item.opname for item in dis.get_instructions(inner)}
    assert any(name.startswith("LOAD_FAST") for name in loads)
    assert any(name.startswith("LOAD_GLOBAL") for name in loads)


@pytest.mark.skipif(
    not compiler.available(),
    reason="this interpreter does not export _testinternalcapi",
)
def test_the_pipeline_carries_the_symbol_table_alongside_the_other_stages():
    result = compiler.stages("answer = 6 * 7\n")
    assert result.scope.lookup("answer") is not None
    assert "1 scope," in result.summary()
