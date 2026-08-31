#!/usr/bin/env python
"""The diagrams for F03, the parser nobody wrote.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `one-file-in-a-parser-out`. Everything else follows from the
parser being a generated artifact: the tree shapes, the soft keywords and the two passes are
all decisions written in the grammar file rather than in any C anybody maintains.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("f03-the-parser-nobody-wrote")

gallery.add(
    figures.pipeline(
        "one-file-in-a-parser-out",
        [
            ("python.gram", "1645 lines, written by hand"),
            ("the generator", "Tools/peg_generator"),
            ("parser.c", "39486 lines, written by machine"),
            ("your compiler", "built from both"),
        ],
        highlight=(0, 2),
        title="The only file a person edits is the first one",
        caption="Lib/keyword.py comes out of the same run, which is why your keyword module names the grammar in its docstring.",
    )
)


gallery.add(
    figures.table(
        "shape-follows-rule",
        ["what you write", "the rule that matches it", "the tree you get"],
        [
            ["1 - 2 - 3", "sum: sum '-' term", "(1 - 2) - 3, leans left"],
            ["2 ** 3 ** 4", "power: await_primary '**' factor", "2 ** (3 ** 4), leans right"],
            ["a < b < c", "comparison: bitwise_or pair+", "one flat node, no leaning"],
        ],
        title="Associativity is not a table of precedences, it is the shape of the rule",
        caption="A rule naming itself on the left leans left, one naming itself on the right leans right, and one that repeats does neither.",
        tones=["focus", "focus", "durable"],
    )
)


gallery.add(
    figures.compare(
        "hard-and-soft",
        (
            "a hard keyword, 35 of them",
            [
                "written 'class' in the grammar",
                "the tokenizer knows it",
                "reserved everywhere",
                "class = 1 is a SyntaxError",
            ],
        ),
        (
            "a soft keyword, 5 of them",
            [
                'written "match" in the grammar',
                "only the parser knows it",
                "a keyword in one position",
                "match = 1 is fine",
            ],
        ),
        title="Two kinds of keyword, and the grammar tells them apart by the quotes",
        verdict="A parser deciding one token at a time could not do the right hand column, because whether match is a keyword depends on what follows it.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.flow(
        "two-passes",
        [
            "parse with 209 rules",
            "did it work?",
            "parse again with all 277",
            "an invalid_ rule matches and says what is wrong",
            "no invalid_ rule matches, so it says invalid syntax",
        ],
        title="Good error messages are a second parse, paid for only when you need one",
        labels=[
            "yes, hand back the tree and stop",
            "no, so slow down and look harder",
            "usually",
        ],
        tones=["input", "focus", "warning", "durable", "quiet"],
    )
)


gallery.add(
    figures.bars(
        "a-quarter-is-apologies",
        [
            ("rules that parse Python", 209),
            ("invalid_ rules, for errors", 68),
        ],
        unit="rules",
        title="Nearly a quarter of the grammar exists to explain failures",
        caption="None of the 68 run on a file that parses. They are switched on only for the second pass.",
        tones=["focus", "warning"],
    )
)


gallery.add(
    figures.stack(
        "what-a-rule-carries",
        [
            "the name, and the type it returns",
            "the alternatives, tried in order",
            "the items in it, named so the action can use them",
            "the action in braces, C that builds an AST node",
        ],
        title="Four things in one line of grammar",
        note="The action is what makes this a compiler front end and not a syntax checker. Nothing walks the tree afterwards.",
    )
)


raise SystemExit(gallery.save())
