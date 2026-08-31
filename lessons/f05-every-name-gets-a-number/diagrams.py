#!/usr/bin/env python
"""The diagrams for F05, every name gets a number.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `five-scopes`. Everything else follows from every name in a
block being sorted into one of those five before a single instruction is chosen: the errors
that only this pass can raise, the whole block rule, and the wire between a cell and a free
variable.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("f05-every-name-gets-a-number")

gallery.add(
    figures.table(
        "five-scopes",
        ["the scope", "how a name ends up here", "what the compiler then emits"],
        [
            ["LOCAL", "assigned somewhere in this block", "LOAD_FAST"],
            ["GLOBAL_EXPLICIT", "named in a global statement", "LOAD_GLOBAL"],
            ["GLOBAL_IMPLICIT", "used here, assigned nowhere", "LOAD_GLOBAL"],
            ["CELL", "local here, and used by a block inside", "LOAD_FAST, in a cell"],
            ["FREE", "used here, local in a block outside", "LOAD_DEREF"],
        ],
        title="Five answers, and every name in your program gets exactly one",
        caption="The names on the left are the five constants the symbol table header defines. There is no sixth.",
        tones=["focus", "quiet", "quiet", "focus", "focus"],
    )
)


gallery.add(
    figures.pipeline(
        "a-pass-in-between",
        [
            ("tokens", "F01 and F02"),
            ("the tree", "F03 and F04"),
            ("the symbol table", "names only, no code yet"),
            ("bytecode", "F06 onwards"),
        ],
        highlight=(2,),
        title="A whole pass that produces no code at all",
        caption="It walks the tree twice, decides what every name means, and hands the answer to the code generator.",
    )
)


gallery.add(
    figures.compare(
        "parses-but-refuses",
        (
            "what the parser thinks",
            [
                "nonlocal x at module level",
                "the grammar has a rule for it",
                "ast.parse is perfectly happy",
                "a tree comes back",
            ],
        ),
        (
            "what the symbol table thinks",
            [
                "there is no block outside this one",
                "so there is nothing to bind to",
                "SyntaxError, at compile time",
                "no bytecode is ever produced",
            ],
        ),
        title="Some syntax errors are not syntax errors",
        verdict="If a mistake needs to know about scopes to spot, the parser cannot spot it, and this is the pass that does.",
        verdict_tone="warning",
    )
)


gallery.add(
    figures.flow(
        "the-whole-block-at-once",
        [
            "def f():",
            "print(x), a use with nothing assigned yet",
            "x = 1, four words later",
            "x is LOCAL for the whole function",
            "the print reads a local that has no value",
        ],
        title="Why the classic UnboundLocalError happens, in the order it happens",
        labels=[
            "the pass reads the whole body first",
            "one assignment is enough",
            "so the compiler emits LOAD_FAST_CHECK",
        ],
        tones=["input", "quiet", "focus", "focus", "warning"],
    )
)


gallery.add(
    figures.compare(
        "cell-and-free",
        (
            "in the outer function",
            [
                "total is assigned here",
                "and read by a block inside",
                "so it is CELL, not LOCAL",
                "co_cellvars holds total",
            ],
        ),
        (
            "in the inner function",
            [
                "total is read here",
                "and is local somewhere outside",
                "so it is FREE",
                "co_freevars holds total",
            ],
        ),
        title="One name, two blocks, two different answers",
        verdict="Both answers were decided by the symbol table before any bytecode existed. The code object just repeats them.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.flow(
        "the-cell-you-did-not-ask-for",
        [
            "you write super() with no arguments",
            "the symbol table notices",
            "it adds __class__ to the method's free variables",
            "the class body gets a cell to fill in",
            "super() finds the class it was defined in",
        ],
        title="The one name the symbol table adds that you never wrote",
        labels=[
            "while walking the class body",
            "as if you had written nonlocal __class__",
            "handed over as __classcell__",
        ],
        tones=["input", "focus", "focus", "intermediate", "durable"],
    )
)


raise SystemExit(gallery.save())
