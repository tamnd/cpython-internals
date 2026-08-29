"""The grammar as plain data, and the line numbers hung off it.

The line numbers are the part worth testing hardest. Everything else in `bpc` is a
rearrangement of what `asdl.py` already worked out, but the walk that attaches lines is
`bpc`'s own guess about a file it did not parse, and a citation pointing at the wrong line
is the one failure this tool could produce that nobody would notice.
"""

from __future__ import annotations

import pytest

from bpc.model import BUILTIN_TYPES, Field, Grammar, GrammarError, load_asdl, parse


def test_the_module_is_the_one_the_grammar_names(asdl):
    assert asdl.name == "Python"
    assert asdl.path == "Parser/Python.asdl"


def test_the_definitions_are_in_the_order_the_file_writes_them(asdl):
    lines = [one.line for one in asdl.definitions]
    assert lines == sorted(lines)
    assert asdl.definitions[0].name == "mod"


def test_every_definition_is_reachable_by_name(asdl):
    for one in asdl.definitions:
        assert asdl.definition(one.name) is one
    with pytest.raises(KeyError):
        asdl.definition("NotAType")


def test_the_line_a_definition_is_cited_at_has_that_name_and_an_equals(asdl, tree):
    """The self checking property the whole citation scheme rests on."""
    text = (tree / "Parser" / "Python.asdl").read_text(encoding="utf-8").splitlines()
    for one in asdl.definitions:
        line = text[one.line - 1]
        assert one.name in line, f"{one.name} is not on line {one.line}: {line!r}"
        assert "=" in line


def test_a_type_used_as_a_field_type_does_not_capture_the_definition(asdl):
    """`arg` is a field type of `arguments` before it is a definition of its own.

    A forward scan for the first `arg` token lands on line 116, inside `arguments`, and
    every citation for the type would then point at another type's field list. Requiring
    an `=` after the name is what keeps them apart, and this is the test that says so.
    """
    assert asdl.definition("arguments").line < asdl.definition("arg").line
    assert asdl.definition("arg").line == 119


def test_the_line_a_constructor_is_cited_at_has_that_name(asdl, tree):
    text = (tree / "Parser" / "Python.asdl").read_text(encoding="utf-8").splitlines()
    for one in asdl.definitions:
        for two in one.constructors:
            assert two.name in text[two.line - 1]


def test_a_constructor_is_inside_the_definition_that_declares_it(asdl):
    for one in asdl.definitions:
        for two in one.constructors:
            assert one.line <= two.line <= one.end_line


def test_a_sum_has_constructors_and_a_product_has_fields(asdl):
    for one in asdl.definitions:
        assert one.sum == bool(one.constructors)
        assert one.kind == ("sum" if one.sum else "product")
        if not one.sum:
            assert one.fields


def test_the_node_count_is_one_per_constructor_and_one_per_product(asdl):
    expected = sum(len(one.constructors) or 1 for one in asdl.definitions)
    assert asdl.node_count == expected


def test_every_field_kind_is_one_of_the_four_words(asdl):
    words = {"required", "optional", "sequence", "sequence of optional"}
    for one in asdl.definitions:
        fields = list(one.fields) + list(one.attributes)
        fields += [field for two in one.constructors for field in two.fields]
        for field in fields:
            assert field.kind in words


def test_notation_writes_the_field_back_the_way_the_grammar_wrote_it():
    assert Field("expr", "returns", optional=True, sequence=False, marks="?").notation == (
        "expr? returns"
    )
    assert Field("stmt", "body", optional=False, sequence=True, marks="*").notation == (
        "stmt* body"
    )
    assert Field("expr", "keys", optional=False, sequence=True, marks="?*").notation == (
        "expr?* keys"
    )
    assert Field("identifier", "name", optional=False, sequence=False).notation == (
        "identifier name"
    )


def test_a_field_with_both_quantifiers_is_a_sequence_first():
    """`seq` wins over `opt`, because the value is a list before it is anything else."""
    field = Field("expr", "keys", optional=False, sequence=True, marks="?*")
    assert field.elements_optional
    assert field.kind == "sequence of optional"
    assert not Field("expr", "body", optional=False, sequence=True, marks="*").elements_optional


def test_the_four_builtin_types_are_the_ones_that_are_not_defined(asdl):
    declared = {one.name for one in asdl.definitions}
    assert not (BUILTIN_TYPES & declared)
    for field in asdl.definition("arg").fields:
        assert field.builtin == (field.type in BUILTIN_TYPES)


def test_a_constructor_signature_reads_like_the_grammar(asdl):
    node = next(one for one in asdl.definition("stmt").constructors if one.name == "Return")
    assert node.signature == "Return(expr? value)"
    pass_node = next(one for one in asdl.definition("stmt").constructors if one.name == "Pass")
    assert pass_node.signature == "Pass"


def test_the_attributes_belong_to_the_type_not_the_constructor(asdl):
    stmt = asdl.definition("stmt")
    assert [one.name for one in stmt.attributes] == [
        "lineno",
        "col_offset",
        "end_lineno",
        "end_col_offset",
    ]
    assert not asdl.definition("boolop").attributes


def test_a_tree_without_the_grammar_says_which_file_is_missing(tmp_path):
    with pytest.raises(GrammarError, match=r"asdl\.py"):
        parse(tmp_path)


def test_a_tree_with_asdl_but_no_grammar_says_so(tmp_path, tree):
    (tmp_path / "Parser").mkdir()
    (tmp_path / "Parser" / "asdl.py").write_text(
        (tree / "Parser" / "asdl.py").read_text(encoding="utf-8"), encoding="utf-8"
    )
    with pytest.raises(GrammarError, match=r"Python\.asdl"):
        parse(tmp_path)


def test_asdl_is_imported_under_a_name_that_cannot_collide(tree):
    module = load_asdl(tree)
    assert module.__name__ == "bpc._cpython_asdl"
    assert load_asdl(tree) is module


def test_the_grammar_is_read_once_per_tree(tree):
    from bpc.model import grammar

    assert grammar(tree) is grammar(tree)


def test_a_grammar_can_be_built_by_hand_for_the_renderer_tests():
    """Nothing in `Grammar` needs a checkout, which is what keeps the render tests fast."""
    one = Grammar(name="Toy", definitions=(), line=1)
    assert one.node_count == 0
    assert one.path == "Parser/Python.asdl"
