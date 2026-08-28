#!/usr/bin/env python
"""The diagrams for T04, names get scopes.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `the-same-line-twice`. Two functions containing the identical
line, and a different opcode underneath each of them. Everything else here is either setting
that up or explaining it.
"""

from nbdiagram import Gallery, figures, stages
from nbdiagram.scene import Scene, text_width
from pyxray import theme

gallery = Gallery("t04-names-get-scopes")

gallery.add(
    stages.map(
        "where-we-are",
        highlight=stages.SYMBOLS,
        title="Where this lesson sits",
        caption="One pass over the tree that writes nothing into the tree. It answers a question instead.",
    )
)


def _one_function(name: str, lines: list[str], opcode: str, tone: str) -> Scene:
    """One function, and the instruction the compiler produced for the name it reads.

    Both source boxes are sized for the longer function so the two instruction boxes end
    up level with each other. Panels whose punchlines sit at different heights read as two
    separate pictures rather than as one comparison.
    """
    scene = Scene(name)
    width = 320
    source = scene.box(
        "\n".join(lines),
        0,
        0,
        width=width,
        height=44 * 3,
        tone="input",
        mono=True,
        size=theme.CAPTION_SIZE,
    )
    result = scene.box(
        opcode,
        0,
        source.box[3] + 70,
        width=width,
        height=52,
        tone=tone,
        mono=True,
        size=theme.CAPTION_SIZE,
        align="center",
    )
    scene.arrow(source, result, label="becomes", sides=("bottom", "top"))
    return scene


# The picture the whole lesson is written around. The reader's first reaction is that the
# print comes before the assignment so the assignment cannot possibly matter, and the answer
# is that the compiler was not reading line by line.
gallery.add(
    figures.beside(
        "the-same-line-twice",
        [
            (
                "def show():",
                _one_function(
                    "show",
                    ["def show():", "    print(answer)"],
                    "LOAD_GLOBAL answer",
                    "durable",
                ),
            ),
            (
                "def broken():",
                _one_function(
                    "broken",
                    ["def broken():", "    print(answer)", "    answer = 1"],
                    "LOAD_FAST_CHECK answer",
                    "warning",
                ),
            ),
        ],
        title="The same line, and two different instructions",
        caption="One extra line at the bottom of the function changed the instruction two lines above it.",
        gap=110,
    )
)

# Containment rather than a tree, because the claim is that a block is the unit the decision
# is made in, and a tree would say these things are merely related.
gallery.add(
    figures.nest(
        "one-decision-per-block",
        (
            "module",
            [
                "answer   is a name here",
                ("def show():", ["answer   global"]),
                ("def broken():", ["answer   local"]),
                (
                    "def outer():",
                    [
                        "total    cell",
                        ("def inner():", ["total    free"]),
                    ],
                ),
            ],
        ),
        title="A decision per name, per block",
        caption="Four blocks, and answer means something different in three of them. Nothing here is about a line.",
    )
)

gallery.add(
    figures.table(
        "five-answers",
        ["answer", "where the value lives", "read with", "how a name gets it"],
        [
            ["local", "a slot in the frame", "LOAD_FAST", "assigned in this block"],
            [
                "cell",
                "a box this block owns",
                "LOAD_DEREF",
                "assigned here, read by an inner block",
            ],
            ["free", "a box further out", "LOAD_DEREF", "assigned in a block around this one"],
            [
                "global",
                "the module dictionary",
                "LOAD_GLOBAL",
                "never assigned, or declared global",
            ],
            ["name", "looked up as it runs", "LOAD_NAME", "assigned in a module or a class body"],
        ],
        title="Five possible answers, and the instruction each one produces",
        caption="The scope is not written anywhere in the code object. The opcode is the record of it.",
    )
)


def _the_cascade() -> Scene:
    """The order analyze_name asks its questions in, which is why global wins over assignment.

    Drawn as a ladder rather than as a flowchart with branches. Every question has the same
    two outcomes, answer and stop or carry on down, so the branches would all be the same
    shape and the diamonds would be decoration.
    """
    scene = Scene("the-cascade")
    steps = [
        ("did you write global here?", "global"),
        ("did you write nonlocal here?", "free"),
        ("is it assigned anywhere in this block?", "local, or cell"),
        ("is it assigned in a block around this one?", "free"),
        ("none of the above", "global"),
    ]
    question_width = max(text_width(question, theme.CAPTION_SIZE) for question, _ in steps) + 40
    answer_width = 190
    height = 50
    step = height + 40

    scene.text("The order the questions are asked in", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    for index, (question, answer) in enumerate(steps):
        y = top + index * step
        left = scene.box(
            question,
            0,
            y,
            width=question_width,
            height=height,
            tone="quiet" if index < len(steps) - 1 else "intermediate",
            size=theme.CAPTION_SIZE,
        )
        right = scene.box(
            answer,
            question_width + 90,
            y,
            width=answer_width,
            height=height,
            tone="durable",
            mono=True,
            size=theme.CAPTION_SIZE,
            align="center",
        )
        scene.arrow(left, right, label="yes" if index < len(steps) - 1 else "")
        if index < len(steps) - 1:
            scene.arrow(
                (44, y + height),
                (44, y + step),
                label="no",
            )

    bottom = max(element.box[3] for element in scene.elements)
    scene.text(
        "The first yes wins, which is why a global statement beats an assignment sitting under it.",
        0,
        bottom + theme.GRID,
        size=theme.CAPTION_SIZE,
        colour=theme.MUTED,
    )
    return scene


gallery.add(_the_cascade())


def _one_box_two_frames() -> Scene:
    """Why a closure needs a cell: two frames, one value, and the outer frame has gone."""
    scene = Scene("one-box-two-frames")
    width = 260
    height = 56

    scene.text("What a closure actually shares", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    outer = scene.panel("outer's frame", 0, top, width, 150, tone="input", mono=True)
    scene.box(
        "total   cell 0",
        theme.PADDING,
        top + 56,
        width=width - 2 * theme.PADDING,
        height=height,
        tone="quiet",
        mono=True,
        size=theme.CAPTION_SIZE,
    )

    inner = scene.panel(
        "inner's frame", 0, outer.box[3] + 90, width, 150, tone="intermediate", mono=True
    )
    scene.box(
        "total   free 0",
        theme.PADDING,
        inner.box[1] + 56,
        width=width - 2 * theme.PADDING,
        height=height,
        tone="quiet",
        mono=True,
        size=theme.CAPTION_SIZE,
    )

    cell = scene.box(
        "cell\n\nvalue: 0",
        width + 150,
        top + 120,
        width=170,
        height=140,
        tone="durable",
        mono=True,
        size=theme.CAPTION_SIZE,
        align="center",
    )
    scene.arrow(outer, cell)
    scene.arrow(inner, cell)

    bottom = max(element.box[3] for element in scene.elements)
    for line, words in enumerate(
        [
            "Both frames hold the same cell, so writing through one is visible through the other.",
            "outer returns and its frame goes away. The cell does not, because inner still holds it.",
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


gallery.add(_one_box_two_frames())

raise SystemExit(gallery.save())
