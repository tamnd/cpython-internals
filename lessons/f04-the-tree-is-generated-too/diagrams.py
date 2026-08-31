#!/usr/bin/env python
"""The diagrams for F04, the tree is generated too.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `one-file-three-outputs`. Everything else follows from the
node types being declared once in a schema: the shape of `_fields`, the difference between a
sum and a product, and the fact that the validator's messages were written by a generator.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("f04-the-tree-is-generated-too")

gallery.add(
    figures.pipeline(
        "one-file-three-outputs",
        [
            ("Python.asdl", "154 lines, written by hand"),
            ("asdl_c.py", "run once, at build time"),
            ("Python-ast.c", "18524 lines, plus two headers"),
            ("the ast module", "the classes you import"),
        ],
        highlight=(0, 2),
        title="One schema, and every node type in both languages comes out of it",
        caption="The C structs the parser fills in and the Python classes you inspect are two views of the same 154 lines.",
    )
)


gallery.add(
    figures.spans(
        "a-line-becomes-a-class",
        "BinOp(expr left, operator op, expr right)",
        [
            (0, 5, "the class name"),
            (6, 15, "field one"),
            (17, 28, "field two"),
            (30, 40, "field three"),
        ],
        title="One alternative in the schema, and what it turns into",
        caption="Read it back in Python as ast.BinOp._fields, which is ('left', 'op', 'right') in that order.",
    )
)


gallery.add(
    figures.compare(
        "sums-and-products",
        (
            "a sum, written with bars",
            [
                "expr = BoolOp(...) | BinOp(...)",
                "an abstract base class",
                "one class per alternative",
                "29 of them under ast.expr",
            ],
        ),
        (
            "a product, written with brackets",
            [
                "arguments = (arg* args, ...)",
                "no base class of its own",
                "exactly one class",
                "there is only ever one shape",
            ],
        ),
        title="Two ways to write a type, and you can tell them apart from Python",
        verdict="Anything you can isinstance against, like ast.expr or ast.stmt, is a sum. The seven leftovers are products.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.table(
        "three-markers",
        ["how the schema writes it", "what it means", "what you get when nothing was written"],
        [
            ["expr value", "exactly one, required", "it is always there"],
            ["expr? value", "one or nothing", "None"],
            ["expr* values", "any number, including none", "an empty list"],
        ],
        title="Three markers, and all the optionality in the tree is one of them",
        caption="A missing return annotation is None. A function with no decorators still has a decorator_list.",
        tones=["durable", "focus", "focus"],
    )
)


gallery.add(
    figures.table(
        "what-abstract-drops",
        ["what you wrote", "what the tree holds", "what went missing"],
        [
            ["x = 1 + (2 * 3)", "x = 1 + 2 * 3", "brackets you did not need"],
            ["x = 1_000", "x = 1000", "how you spelled the number"],
            ["x = 'a' 'b'", "x = 'ab'", "that it was two literals"],
            ["x = 5  # a note", "x = 5", "the comment, entirely"],
        ],
        title="Abstract is not a compliment, it is a description of what was thrown away",
        caption="Everything in the third column changes nothing about what the program does, so the tree does not keep it.",
        tones=["quiet", "quiet", "quiet", "warning"],
    )
)


gallery.add(
    figures.flow(
        "who-checks-what",
        [
            "you build a tree by hand",
            "compile() converts it to C structs",
            "_PyAST_Validate walks it",
            "the compiler gets a tree it can trust",
        ],
        title="Where a hand built tree is checked, and what happens when it is wrong",
        labels=[
            "a missing field stops it here",
            "an empty body or a wrong context stops it here",
            "everything held up",
        ],
        tones=["input", "intermediate", "focus", "durable"],
    )
)


raise SystemExit(gallery.save())
