"""The generated sections of BP-AST, checked against the interpreter running the tests.

Sections 1, 2 and 5 of the blueprint are transcribed from `Parser/Python.asdl` by machine,
so they cannot contain a typo. What they can contain is a claim that was true of the pinned
grammar and is not true of the `ast` module in front of the reader, and that is what these
tests are for. Every one of them reads the grammar from the pinned tree and compares it
against `ast` directly.

Section 8 of the blueprint names these tests by their function names, so renaming one here
means changing `render.py` and rebuilding. That is intentional. A conformance section that
points at a test which does not exist is the failure mode this whole arrangement is meant
to avoid.
"""

from __future__ import annotations

import ast

import pytest

from bpc.model import BUILTIN_TYPES

pytestmark = pytest.mark.usefixtures("pinned_interpreter")


def test_every_type_in_the_grammar_is_a_class_in_ast(asdl):
    """Section 1's first column, one name at a time."""
    for one in asdl.definitions:
        node = getattr(ast, one.name, None)
        assert node is not None, f"the grammar declares {one.name} and ast has no such class"
        assert isinstance(node, type)
        assert issubclass(node, ast.AST)


def test_every_constructor_in_the_grammar_is_a_class_in_ast(asdl):
    """Section 2's first column, and that each one inherits from the type it belongs to."""
    for one in asdl.definitions:
        for two in one.constructors:
            node = getattr(ast, two.name, None)
            assert node is not None, f"the grammar declares {two.name} and ast has no such class"
            assert issubclass(node, getattr(ast, one.name))


def test_the_field_order_is_the_order_the_grammar_declares(asdl):
    """`_fields` is positional, so a reordering here breaks every hand built tree."""
    for one in asdl.definitions:
        if not one.sum:
            names = tuple(field.name for field in one.fields)
            assert getattr(ast, one.name)._fields == names
            continue
        assert getattr(ast, one.name)._fields == ()
        for two in one.constructors:
            names = tuple(field.name for field in two.fields)
            assert getattr(ast, two.name)._fields == names


def test_the_attributes_are_the_ones_the_grammar_declares(asdl):
    """Attributes are inherited from the type, so every constructor of a sum shares them."""
    for one in asdl.definitions:
        names = tuple(field.name for field in one.attributes)
        assert getattr(ast, one.name)._attributes == names
        for two in one.constructors:
            assert getattr(ast, two.name)._attributes == names


def test_the_defaults_are_the_ones_section_5_describes(asdl):
    """Leaving a field out: `None`, an empty list, `Load()`, or `TypeError`."""
    for one in asdl.definitions:
        for two in one.constructors:
            for field in two.fields:
                if field.kind == "required" and field.type != "expr_context":
                    continue
                node = getattr(ast, two.name)(**_minimum(two))
                got = getattr(node, field.name)
                if field.type == "expr_context":
                    assert isinstance(got, ast.Load)
                elif field.sequence:
                    assert got == []
                else:
                    assert got is None


def test_an_attribute_is_never_required_and_optional_ones_still_default(asdl):
    """Attributes come off the type, so this runs once per type that has any."""
    for one in asdl.definitions:
        if not one.attributes:
            continue
        name = one.constructors[0].name if one.sum else one.name
        node = getattr(ast, name)(**_minimum(one.constructors[0] if one.sum else one))
        for field in one.attributes:
            if field.optional:
                assert getattr(node, field.name) is None
            else:
                assert not hasattr(node, field.name)


def test_a_missing_line_number_is_refused_by_compile_rather_than_by_the_constructor():
    """Where INV-AST-008 is actually enforced, which is not where a reader expects."""
    built = ast.Module(body=[ast.Pass()], type_ignores=[])
    with pytest.raises(TypeError, match="lineno"):
        compile(built, "<test>", "exec")
    positioned = ast.Module(body=[ast.Pass(lineno=1, col_offset=0)], type_ignores=[])
    assert compile(positioned, "<test>", "exec").co_firstlineno == 1


def test_a_required_field_left_out_raises_and_names_itself():
    """The other half of the rule above, which needs a node rather than a loop."""
    with pytest.raises(TypeError, match="name"):
        ast.FunctionDef()
    with pytest.raises(TypeError, match="args"):
        ast.FunctionDef(name="f")


def test_a_sequence_default_is_not_shared_between_nodes():
    """An empty list per node, not one empty list handed out over and over."""
    first, second = ast.Module(), ast.Module()
    first.body.append(ast.Pass())
    assert second.body == []


def test_the_only_sequences_of_optional_are_the_two_section_6_names(asdl):
    """`expr?* keys` and `expr?* kw_defaults`, the reason `Field.marks` exists at all."""
    found = [
        (one.name, field.name)
        for one in asdl.definitions
        for field in one.fields
        if field.elements_optional
    ]
    found += [
        (two.name, field.name)
        for one in asdl.definitions
        for two in one.constructors
        for field in two.fields
        if field.elements_optional
    ]
    assert sorted(found) == [("Dict", "keys"), ("arguments", "kw_defaults")]


def test_a_none_key_in_a_dict_display_is_how_double_star_unpacking_is_written():
    """The first of the two, which has no node of its own and uses the gap instead."""
    node = ast.parse("{1: 2, **d}").body[0].value
    assert node.keys[0].value == 1
    assert node.keys[1] is None
    assert [type(one).__name__ for one in node.values] == ["Constant", "Name"]


def test_kw_defaults_lines_up_with_kwonlyargs_and_holds_none_for_the_gaps():
    """The second of the two, where the gap means an argument with no default."""
    args = ast.parse("def f(*, a, b=1): pass").body[0].args
    assert [one.arg for one in args.kwonlyargs] == ["a", "b"]
    assert args.kw_defaults[0] is None
    assert isinstance(args.kw_defaults[1], ast.Constant)


def test_defaults_is_right_aligned_against_args_and_has_no_gaps():
    """The contrast that makes `kw_defaults` worth a section of its own."""
    args = ast.parse("def f(a, b=1): pass").body[0].args
    assert [one.arg for one in args.args] == ["a", "b"]
    assert len(args.defaults) == 1


def test_every_field_type_is_a_definition_in_the_grammar_or_one_of_the_four(asdl):
    """What lets section 2 print a type name without saying where to look it up."""
    names = {one.name for one in asdl.definitions} | set(BUILTIN_TYPES)
    for one in asdl.definitions:
        fields = list(one.fields) + list(one.attributes)
        fields += [field for two in one.constructors for field in two.fields]
        for field in fields:
            assert field.type in names, f"{one.name}.{field.name} has type {field.type}"


def _minimum(constructor) -> dict[str, object]:
    """The smallest set of arguments that builds this node, so the rest can be inspected."""
    return {
        field.name: _value(field.type)
        for field in constructor.fields
        if field.kind == "required" and field.type != "expr_context"
    }


def _value(name: str) -> object:
    if name == "identifier":
        return "x"
    if name == "string":
        return "x"
    if name == "int":
        return 0
    if name == "constant":
        return None
    return getattr(ast, name)
