"""Turning the grammar into the parts of a blueprint that nobody should be typing.

Every function here takes the grammar and returns markdown. There is no state, no file
access and no formatting that depends on anything but the grammar, which is what makes the
output deterministic: run it twice on the same pin and the bytes are identical, so a diff
against the previous run means the pin moved and nothing else.

The tables are wide rather than clever. A specification is read by somebody who is looking
for one field of one node, so every row repeats the node name instead of relying on a
reader keeping their finger on the last one, and every row can be found with grep.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from refcheck.citation import find_all
from refcheck.tree import PINNED_TAG

from .model import Constructor, Definition, Grammar

#: The four location attributes CPython puts on the node types that can be pointed at in
#: an error message. Named here only so the generated prose can say how many there are.
LOCATION_ATTRIBUTES = ("lineno", "col_offset", "end_lineno", "end_col_offset")


def citation(grammar: Grammar, line: int, symbol: str) -> str:
    """One citation into the pinned grammar file, as a code span.

    A single line rather than a range on purpose. The name being cited is on that line, so
    the citation is self checking: if upstream moves the definition, the symbol is no
    longer where the citation says it is and `just citations` fails instead of quietly
    pointing at whatever moved into that slot.
    """
    return f"`{grammar.path}:{line}@{PINNED_TAG}#{symbol}`"


def table(headings: Iterable[str], rows: Iterable[Iterable[str]]) -> list[str]:
    """A markdown table, with the header separator markdown insists on."""
    names = list(headings)
    lines = ["| " + " | ".join(names) + " |", "|" + "|".join(["---"] * len(names)) + "|"]
    lines.extend("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows)
    return lines


def overview(grammar: Grammar) -> str:
    """Section 1: what the grammar contains, counted."""
    sums = sum(1 for one in grammar.definitions if one.sum)
    fields = sum(len(one.fields) for one in grammar.definitions)
    fields += sum(len(two.fields) for one in grammar.definitions for two in one.constructors)
    carrying = [one.name for one in grammar.definitions if one.attributes]

    lines = [
        f"The grammar declares {len(grammar.definitions)} types, {sums} of them a choice "
        f"between constructors and {len(grammar.definitions) - sums} of them a single fixed "
        f"shape. Between them they describe {grammar.node_count} concrete node kinds with "
        f"{fields} fields, and {len(carrying)} of the types carry source location attributes "
        "on every node.",
        "",
        f"The module header is at {citation(grammar, grammar.line, grammar.name)}.",
        "",
    ]
    rows = []
    for index, one in enumerate(grammar.definitions, start=1):
        rows.append(
            [
                str(index),
                f"`{one.name}`",
                one.kind,
                str(len(one.constructors)) if one.sum else "",
                str(_field_count(one)),
                str(len(one.attributes)),
                citation(grammar, one.line, one.name),
            ]
        )
    lines.extend(
        table(
            ["#", "Type", "Kind", "Constructors", "Fields", "Attributes", "Declared at"],
            rows,
        )
    )
    return "\n".join(lines)


def nodes(grammar: Grammar) -> str:
    """Section 2: every type, every constructor, every field, in declaration order."""
    lines: list[str] = []
    for index, one in enumerate(grammar.definitions, start=1):
        if lines:
            lines.append("")
        lines.extend(_definition(grammar, one, f"2.{index}"))
    return "\n".join(lines)


def observable(grammar: Grammar) -> str:
    """Section 5: what a Python program can see of all this through the `ast` module."""
    lines = [
        f"The whole grammar is visible from Python. Each of the {grammar.node_count} node "
        f"kinds below is a class in the `ast` module with the same name, each of the "
        f"{len(grammar.definitions)} types is a class those inherit from, and the field "
        "order in the grammar is the order those classes take positional arguments in. A "
        "reimplementation that renames a field or reorders two of them is detectable by "
        "any program that builds a tree by hand or reads one back.",
        "",
        "The three field kinds are three different things to leave out. A required field "
        "has to be passed, and building the node without it raises `TypeError` naming the "
        "field. An optional field left out is `None`. A sequence field left out is a new "
        "empty list, so `body` is `[]` rather than missing. There is one field type that "
        "breaks the pattern: a field of type `expr_context` left out is the `Load` "
        "singleton, because nearly every expression in a tree is being read rather than "
        "written to.",
        "",
        f"The {len(LOCATION_ATTRIBUTES)} location attributes are separate from the fields. "
        "They are listed in `_attributes` rather than `_fields`, and none of them is ever "
        "required by the constructor, so a node can always be built without them. The two "
        "declared optional default to `None` like any other optional. The two declared "
        "required have no value at all, and reading one raises `AttributeError` rather than "
        "returning `None`. Nothing complains until `compile` sees the tree, which is where "
        "a missing line number becomes `TypeError` and where a port has to put the same "
        "check.",
        "",
    ]
    rows = []
    for one in grammar.definitions:
        rows.append(
            [
                f"`{one.name}`",
                "abstract" if one.sum else "concrete",
                _tuple(field.name for field in one.fields),
                _tuple(field.name for field in one.attributes),
            ]
        )
        for two in one.constructors:
            rows.append(
                [
                    f"`{two.name}`",
                    f"`{one.name}`",
                    _tuple(field.name for field in two.fields),
                    _tuple(field.name for field in one.attributes),
                ]
            )
    lines.extend(table(["Class", "Base", "`_fields`", "`_attributes`"], rows))
    return "\n".join(lines)


def conformance(grammar: Grammar) -> str:
    """Section 8: what holds the two sections above up, and how much of them it covers."""
    fields = sum(len(one.fields) for one in grammar.definitions)
    fields += sum(len(two.fields) for one in grammar.definitions for two in one.constructors)
    carrying = sum(1 for one in grammar.definitions if one.attributes)
    citations = len(find_all(overview(grammar))) + len(find_all(nodes(grammar)))

    lines = [
        "Sections 1, 2 and 5 are generated from the grammar file, so the way they go wrong "
        "is not a typo. They go wrong when the running interpreter and the pinned grammar "
        "have stopped agreeing, which is what the checks below are for. Each one reads the "
        "grammar from the pinned tree and compares it against the `ast` module of the "
        "interpreter running the test.",
        "",
    ]
    rows = [
        [
            "Every type in section 1 is a class in `ast`",
            "`test_every_type_in_the_grammar_is_a_class_in_ast`",
            f"{len(grammar.definitions)} types",
        ],
        [
            "Every constructor in section 2 is a class in `ast`",
            "`test_every_constructor_in_the_grammar_is_a_class_in_ast`",
            f"{grammar.node_count} node kinds",
        ],
        [
            "`_fields` is the grammar's field names, in the grammar's order",
            "`test_the_field_order_is_the_order_the_grammar_declares`",
            f"{fields} fields",
        ],
        [
            "`_attributes` is the grammar's attributes, in the grammar's order",
            "`test_the_attributes_are_the_ones_the_grammar_declares`",
            f"{carrying} types carry attributes",
        ],
        [
            "Leaving a field out does what section 5 says it does",
            "`test_the_defaults_are_the_ones_section_5_describes`",
            "the three field kinds",
        ],
        [
            "Every citation generated into sections 1 and 2 resolves against the pinned tree",
            "`just citations`",
            f"{citations} citations",
        ],
    ]
    lines.extend(table(["Claim", "Held up by", "Covers"], rows))
    lines.extend(
        [
            "",
            "The first five run under `just test` and live in `tools/bpc/tests/"
            "test_bpc_conformance.py`. They are skipped on an interpreter whose version does "
            f"not match the pinned tree, because a difference between {PINNED_TAG} and some "
            "other version is a fact about the two versions rather than a failure of this "
            "document.",
        ]
    )
    return "\n".join(lines)


def _definition(grammar: Grammar, one: Definition, number: str) -> list[str]:
    """One type: its heading, what it is, and a row per field."""
    lines = [f"### {number} `{one.name}`", ""]
    where = citation(grammar, one.line, one.name)
    if one.sum:
        lines.append(f"A choice between {len(one.constructors)} constructors, declared at {where}.")
    else:
        lines.append(
            f"A single shape with {len(one.fields)} fields, declared at {where}. There is "
            "nothing to switch on: every value of this type has exactly these fields."
        )
    lines.append("")

    if one.attributes:
        lines.append(
            f"Every `{one.name}` node also carries {len(one.attributes)} attributes, which "
            "are not fields and are not part of the constructor's positional arguments."
        )
        lines.append("")
        lines.extend(
            table(
                ["Attribute", "Type", "Holds"],
                [[f"`{field.name}`", f"`{field.type}`", field.kind] for field in one.attributes],
            )
        )
        lines.append("")

    if one.sum:
        lines.extend(
            table(
                ["Node", "Order", "Field", "Type", "Holds", "Declared at"],
                _sum_rows(grammar, one),
            )
        )
    else:
        lines.extend(table(["Order", "Field", "Type", "Holds"], _product_rows(one)))
    return lines


def _sum_rows(grammar: Grammar, one: Definition) -> Iterator[list[str]]:
    for two in one.constructors:
        where = citation(grammar, two.line, two.name)
        if not two.fields:
            yield [f"`{two.name}`", "", "no fields", "", "", where]
            continue
        for order, field in enumerate(two.fields, start=1):
            yield [
                f"`{two.name}`",
                str(order),
                f"`{field.name}`",
                f"`{field.type}`",
                field.kind,
                where if order == 1 else "",
            ]


def _product_rows(one: Definition) -> Iterator[list[str]]:
    for order, field in enumerate(one.fields, start=1):
        yield [str(order), f"`{field.name}`", f"`{field.type}`", field.kind]


def _field_count(one: Definition) -> int:
    if not one.sum:
        return len(one.fields)
    return sum(len(two.fields) for two in one.constructors)


def _tuple(names: Iterable[str]) -> str:
    """A Python tuple of strings, written the way `_fields` prints."""
    inside = ", ".join(f"'{name}'" for name in names)
    if not inside:
        return "`()`"
    return f"`({inside},)`" if inside.count(",") == 0 else f"`({inside})`"


def signature(two: Constructor) -> str:
    """A constructor as the grammar writes it, for anywhere a table is too much."""
    return two.signature


#: The blocks a source document can ask for, by the name it writes in its directive.
BLOCKS = {
    "overview": overview,
    "nodes": nodes,
    "observable": observable,
    "conformance": conformance,
}
