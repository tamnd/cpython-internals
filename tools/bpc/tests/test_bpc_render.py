"""Grammar in, markdown out.

Most of these run against a toy grammar built by hand rather than against CPython's. A
renderer tested only on the real thing is tested on 113 node kinds at once, and when it
breaks the failure is a diff of an 800 line file. The toy grammar is small enough that a
failing assertion names the thing that went wrong.

The ones that do use the real grammar are the ones about scale: that every node kind
appears, that the counts in the prose match the tables under them, and that nothing is
quietly dropped.
"""

from __future__ import annotations

import pytest

from bpc.model import Constructor, Definition, Field, Grammar
from bpc.render import BLOCKS, citation, conformance, nodes, observable, overview, table
from refcheck.citation import find_all
from refcheck.tree import PINNED_TAG


def field(name, type="expr", *, marks=""):
    return Field(type=type, name=name, optional="?" in marks, sequence="*" in marks, marks=marks)


@pytest.fixture
def toy():
    """Two types: one sum with two constructors and attributes, one product."""
    return Grammar(
        name="Toy",
        line=1,
        definitions=(
            Definition(
                name="stmt",
                constructors=(
                    Constructor("Pass", (), line=5),
                    Constructor(
                        "Return",
                        (field("value", marks="?"), field("extras", marks="*")),
                        line=6,
                    ),
                ),
                fields=(),
                attributes=(field("lineno", "int"),),
                line=4,
                end_line=7,
            ),
            Definition(
                name="arg",
                constructors=(),
                fields=(field("name", "identifier"), field("annotation", marks="?")),
                attributes=(),
                line=9,
                end_line=10,
            ),
        ),
    )


def test_a_citation_names_the_file_the_line_and_the_symbol(toy):
    assert citation(toy, 4, "stmt") == f"`Parser/Python.asdl:4@{PINNED_TAG}#stmt`"


def test_every_citation_the_renderer_emits_is_one_refcheck_can_read(asdl):
    """The check that matters: refcheck's own parser has to accept all of them."""
    text = "\n".join(BLOCKS[name](asdl) for name in ("overview", "nodes"))
    found = find_all(text)
    constructors = sum(len(one.constructors) for one in asdl.definitions)
    assert len(found) == 2 * len(asdl.definitions) + constructors + 1
    for one in found:
        assert one.tag == PINNED_TAG
        assert one.path == "Parser/Python.asdl"
        assert one.symbol


def test_a_table_gets_the_separator_markdown_insists_on():
    lines = table(["A", "B"], [["1", "2"]])
    assert lines == ["| A | B |", "|---|---|", "| 1 | 2 |"]


def test_a_table_with_no_rows_is_still_a_table():
    assert table(["A"], []) == ["| A |", "|---|"]


def test_the_overview_counts_what_the_grammar_holds(toy):
    text = overview(toy)
    assert "declares 2 types, 1 of them a choice" in text
    assert "1 of them a single fixed shape" in text
    assert "3 concrete node kinds" in text
    assert "with 4 fields" in text
    assert "1 of the types carry source location" in text


def test_the_overview_has_a_row_per_type_and_nothing_else(toy):
    rows = [one for one in overview(toy).splitlines() if one.startswith("| ")]
    assert len(rows) == 3
    assert "`stmt`" in rows[1] and "sum" in rows[1]
    assert "`arg`" in rows[2] and "product" in rows[2]


def test_the_overview_counts_match_the_real_grammar(asdl):
    text = overview(asdl)
    assert f"declares {len(asdl.definitions)} types" in text
    assert f"{asdl.node_count} concrete node kinds" in text
    rows = [one for one in text.splitlines() if one.startswith("| ") and "sum" in one]
    assert len(rows) == sum(1 for one in asdl.definitions if one.sum)


def test_a_sum_gets_one_row_per_field_and_repeats_the_node_name(toy):
    text = nodes(toy)
    assert "### 2.1 `stmt`" in text
    assert "A choice between 2 constructors" in text
    assert text.count("| `Return` |") == 2
    assert "| `Pass` |  | no fields |" in text


def test_a_constructor_is_cited_once_rather_than_once_per_field(toy):
    body = nodes(toy)
    assert body.count(citation(toy, 6, "Return")) == 1


def test_a_product_says_there_is_nothing_to_switch_on(toy):
    text = nodes(toy)
    assert "### 2.2 `arg`" in text
    assert "A single shape with 2 fields" in text
    assert "nothing to switch on" in text


def test_attributes_are_shown_separately_from_fields(toy):
    text = nodes(toy)
    assert "also carries 1 attributes" in text
    assert "| Attribute | Type | Holds |" in text


def test_every_node_kind_in_the_real_grammar_gets_a_row(asdl):
    text = nodes(asdl)
    for one in asdl.definitions:
        assert f"`{one.name}`" in text
        for two in one.constructors:
            assert f"| `{two.name}` |" in text


def test_the_field_kinds_reach_the_table(toy):
    text = nodes(toy)
    assert "| `value` | `expr` | optional |" in text
    assert "| `extras` | `expr` | sequence |" in text


def test_a_sequence_of_optional_is_labelled_as_one(asdl):
    text = nodes(asdl)
    assert "| `keys` | `expr` | sequence of optional |" in text
    assert "| `kw_defaults` | `expr` | sequence of optional |" in text


def test_the_observable_section_prints_fields_the_way_python_prints_them(toy):
    text = observable(toy)
    assert "| `stmt` | abstract | `()` | `('lineno',)` |" in text
    assert "| `Return` | `stmt` | `('value', 'extras')` | `('lineno',)` |" in text
    assert "| `arg` | concrete | `('name', 'annotation')` | `()` |" in text


def test_the_observable_section_states_all_three_defaults(toy):
    text = observable(toy)
    assert "raises `TypeError`" in text
    assert "left out is `None`" in text
    assert "a new empty list" in text
    assert "`Load` singleton" in text


def test_the_observable_section_separates_the_two_kinds_of_attribute(toy):
    text = observable(toy)
    assert "none of them is ever required" in text
    assert "default to `None`" in text
    assert "`AttributeError`" in text
    assert "until `compile` sees the tree" in text


def test_the_conformance_section_names_a_test_for_every_claim(toy):
    text = conformance(toy)
    rows = [one for one in text.splitlines() if one.startswith("| ")]
    assert len(rows) == 7
    assert "`just citations`" in text
    assert "The first five run under `just test`" in text


def test_the_conformance_counts_come_from_the_grammar(toy):
    text = conformance(toy)
    assert "| 2 types |" in text
    assert "| 3 node kinds |" in text
    assert "| 4 fields |" in text
    assert "| 1 types carry attributes |" in text
    assert "| 7 citations |" in text


def test_every_test_the_conformance_section_names_exists():
    """If this fails, section 8 is pointing at a test nobody can run."""
    from pathlib import Path

    source = Path(__file__).with_name("test_bpc_conformance.py").read_text(encoding="utf-8")
    for line in conformance(Grammar("Toy", (), 1)).splitlines():
        for cell in line.split("|"):
            name = cell.strip().strip("`")
            if name.startswith("test_"):
                assert f"def {name}(" in source, f"section 8 names {name} and it does not exist"


def test_the_renderer_is_deterministic(asdl):
    for name, block in BLOCKS.items():
        assert block(asdl) == block(asdl), name


def test_no_block_comes_out_empty_on_the_real_grammar(asdl):
    for name, block in BLOCKS.items():
        assert block(asdl).strip(), name


def test_nothing_the_renderer_writes_has_the_punctuation_the_project_bans(asdl):
    for name, block in BLOCKS.items():
        text = block(asdl)
        assert "\u2014" not in text, name
        assert "\u2013" not in text, name
        assert "\n---\n" not in text, name
