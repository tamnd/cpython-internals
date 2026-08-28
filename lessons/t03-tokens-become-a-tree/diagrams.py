#!/usr/bin/env python
"""The diagrams for T03, tokens become a tree.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

Two of these are carrying the lesson rather than decorating it. The three sources that
produce one tree is the whole idea of a syntax tree in one picture, and the pair of trees
for `1 + 2 * 3` is the answer to the obvious next question, which is what the tree does
keep if it throws the parentheses away.
"""

from nbdiagram import Gallery, figures, stages
from nbdiagram.scene import Scene, text_width
from pyxray import theme

gallery = Gallery("t03-tokens-become-a-tree")

gallery.add(
    stages.map(
        "where-we-are",
        highlight=stages.TREE,
        title="Where this lesson sits",
        caption="The parser reads the tokens from the box on the left and builds the tree in this one.",
    )
)


def _three_sources_one_tree() -> Scene:
    """Three ways of typing the same line, all arriving at the same tree.

    Everything the lesson says about what the tree throws away is in here. Showing it as a
    convergence rather than as three separate before and after pairs matters, because the
    point is not that each one loses something. It is that they all land in the same place.
    """
    scene = Scene("three-sources-one-tree")
    height = 44
    step = height + 12

    sources = ["answer = (6 * 7)", "answer=6*7", "answer = 6 * 7  # note"]
    width = max(text_width(row, theme.CAPTION_SIZE, mono=True) for row in sources)
    width += 2 * theme.PADDING

    scene.text("Three files, one tree", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    scene.text("what you typed", 0, top, size=theme.CAPTION_SIZE, colour=theme.MUTED)
    rows_top = top + theme.CAPTION_SIZE * theme.LINE_HEIGHT + 10
    boxes = []
    for index, row in enumerate(sources):
        boxes.append(
            scene.box(
                row,
                0,
                rows_top + index * step,
                width=width,
                height=height,
                tone="input",
                mono=True,
                size=theme.CAPTION_SIZE,
            )
        )

    gap = 130
    target = scene.box(
        "BinOp(Constant 6, Mult, Constant 7)",
        width + gap,
        rows_top + step,
        height=height,
        tone="durable",
        mono=True,
        size=theme.CAPTION_SIZE,
    )
    for box in boxes:
        scene.arrow(box, target)

    bottom = max(element.box[3] for element in scene.elements)
    for line, words in enumerate(
        [
            "The brackets, the spacing and the comment are gone by the time the parser is finished.",
            "Nothing later in CPython can tell these three files apart.",
        ]
    ):
        scene.text(
            words,
            0,
            bottom + theme.GRID + line * theme.CAPTION_SIZE * theme.LINE_HEIGHT,
            size=theme.CAPTION_SIZE,
            colour=theme.MUTED,
        )
    return scene


gallery.add(_three_sources_one_tree())

# The natural objection to the picture above is that the parentheses must have mattered for
# something. They did, and what they did is now the shape, which is the one thing a tree is
# good at holding.
gallery.add(
    figures.beside(
        "precedence-is-the-shape",
        [
            (
                "1 + 2 * 3",
                figures.tree(
                    "left",
                    (
                        "BinOp",
                        ["Constant 1", "Add", ("BinOp", ["Constant 2", "Mult", "Constant 3"])],
                    ),
                ),
            ),
            (
                "(1 + 2) * 3",
                figures.tree(
                    "right",
                    (
                        "BinOp",
                        [("BinOp", ["Constant 1", "Add", "Constant 2"]), "Mult", "Constant 3"],
                    ),
                ),
            ),
        ],
        title="The brackets are gone, and what they did is not",
        caption="Same five tokens in the same order. The multiply is inside the add on the left and outside it on the right.",
    )
)

gallery.add(
    figures.flow(
        "where-the-node-classes-come-from",
        [
            "Parser/Python.asdl",
            "Parser/asdl_c.py",
            "Python/Python-ast.c",
            "ast.BinOp.__doc__",
        ],
        title="Why a node class knows its own declaration",
        labels=[
            "read at build time",
            "generates the C and the Python classes",
            "the declaration becomes the docstring",
        ],
        tones=["input", "intermediate", "intermediate", "durable"],
    )
)

# A trace table rather than prose, because the interesting part is that the left column and
# the right column disagree while the tree stays the same the whole way down.
gallery.add(
    figures.table(
        "what-unparse-rewrites",
        ["you wrote", "unparse gives back", "same tree"],
        [
            ["x = 0x2a", "x = 42", "yes"],
            ["x = 1_000_000", "x = 1000000", "yes"],
            ["x = 'a' 'b'", "x = 'ab'", "yes"],
            ["x = (1 + 2)", "x = 1 + 2", "yes"],
            ["x = 1 # note", "x = 1", "yes"],
        ],
        title="What comes back is the meaning, not your text",
        caption="Every row is a different file and the same tree. The tree never held the difference.",
    )
)

raise SystemExit(gallery.save())
