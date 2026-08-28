#!/usr/bin/env python
"""The diagrams for T01, one line and seven stages.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The map at the top comes from `nbdiagram.stages` rather than from this file, because every
lesson in the project opens with the same row of boxes and lights up a different one. A
reader who has read that picture once knows where they are in every later lesson without
reading a word.
"""

from nbdiagram import Gallery, figures, stages
from nbdiagram.scene import Scene, text_width
from pyxray import theme

gallery = Gallery("t01-one-line-seven-stages")

# No box highlighted. This lesson is the only one that is about all of them at once.
gallery.add(
    stages.map(
        "seven-stages",
        title="Where one line of Python goes",
        caption="Eight things, and seven steps turning each one into the next. That is where the seven in the title comes from.",
    )
)

gallery.add(
    figures.spans(
        "tokens-of-one-line",
        "answer = 6 * 7",
        [(0, 6, "NAME"), (7, 8, "OP"), (9, 10, "NUMBER"), (11, 12, "OP"), (13, 14, "NUMBER")],
        title="Stage 1: the line cut into tokens",
        caption="The tokenizer also adds ENCODING before these and ENDMARKER after them, and you typed neither.",
    )
)

gallery.add(
    figures.tree(
        "the-tree",
        (
            "Assign",
            [
                ("Name", ["id 'answer'", "ctx Store"]),
                ("BinOp", ["Constant 6", "Mult", "Constant 7"]),
            ],
        ),
        title="Stage 2: the same line as a tree",
        caption="Nothing has been worked out yet. 6 * 7 is still a multiplication sitting in a tree.",
    )
)

# Two rows on each side, in the same order, so the eye can pair them off. The point is that
# the left side puts two roles on one name and the right side splits them across two.
gallery.add(
    figures.compare(
        "one-name-two-answers",
        ("at module level", ["answer  local", "answer  global"]),
        ("inside a function", ["a       local", "answer  global"]),
        title="Stage 3: what the symbol table decided",
        verdict="At module level one name is both at once. Inside a function the two roles land on two different names.",
    )
)


def _the_fold() -> Scene:
    """The three instructions the optimizer replaced with one.

    A before and after, side by side, with the multiply tinted on the left and nothing
    matching it on the right. The lesson can say "the multiplication is gone" in a sentence,
    and the sentence is easier to believe when the picture is next to it.
    """
    scene = Scene("the-multiplication-disappears")
    height = 44
    step = height + 10

    before = ["LOAD_CONST 0", "LOAD_CONST 1", "BINARY_OP 5"]
    after = ["LOAD_SMALL_INT 42"]
    width = max(text_width(row, theme.CAPTION_SIZE, mono=True) for row in [*before, *after])
    width += 2 * theme.PADDING

    scene.text("Stage 5: the optimizer does your arithmetic", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    gap = 140
    rows_top = top + theme.CAPTION_SIZE * theme.LINE_HEIGHT + 10
    # The right column is one row against three, so it is nudged down until its middle lines
    # up with the middle of the left column. Then the arrow between them is level, and a
    # level arrow reads as "this became that" rather than "this went somewhere".
    offset = (len(before) - 1) * step / 2

    for index, (heading, rows, shift) in enumerate(
        [
            ("what the compiler emitted", before, 0.0),
            ("what the optimizer left", after, offset),
        ]
    ):
        x = index * (width + gap)
        scene.text(
            heading, x + width / 2, top, size=theme.CAPTION_SIZE, colour=theme.MUTED, align="centre"
        )
        y = rows_top + shift
        for row in rows:
            tone = "warning" if row.startswith("BINARY_OP") else "intermediate"
            scene.box(
                row, x, y, width=width, height=height, tone=tone, mono=True, size=theme.CAPTION_SIZE
            )
            y += step

    middle = rows_top + offset + height / 2
    scene.arrow((width + 16, middle), (width + gap - 16, middle))

    bottom = rows_top + len(before) * step
    for line, words in enumerate(
        [
            "0 and 1 are slots in the constant table, holding 6 and 7.",
            "The multiply ran once, while you were compiling. Your program will never do it.",
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


gallery.add(_the_fold())


def _where_the_42_lives() -> Scene:
    """Two places a number can end up, and the one number that is in neither useful place.

    This is the detail readers reliably get backwards. They expect 42 in the constant table
    and they expect the 6 to have been thrown away, and both guesses are wrong.
    """
    scene = Scene("where-the-42-lives")
    height = 44
    width = 190

    scene.text("Stage 6: where each number ended up", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    note_x = width * 1.6 + theme.GAP

    def note(words: str, y: float) -> None:
        scene.text(
            words,
            note_x,
            y + (height - theme.CAPTION_SIZE * theme.LINE_HEIGHT) / 2,
            size=theme.CAPTION_SIZE,
            colour=theme.MUTED,
        )

    scene.text("co_consts", 0, top, size=theme.CAPTION_SIZE, colour=theme.MUTED)
    row = top + theme.CAPTION_SIZE * theme.LINE_HEIGHT + 8
    scene.box(
        "6",
        0,
        row,
        width=width / 2,
        height=height,
        tone="warning",
        mono=True,
        size=theme.CAPTION_SIZE,
        align="center",
    )
    note("kept for as long as the code object lives, and loaded by nothing", row)

    row += height + theme.GAP
    scene.text("the instruction", 0, row, size=theme.CAPTION_SIZE, colour=theme.MUTED)
    row += theme.CAPTION_SIZE * theme.LINE_HEIGHT + 8
    scene.box(
        "LOAD_SMALL_INT 42",
        0,
        row,
        width=width * 1.6,
        height=height,
        tone="durable",
        mono=True,
        size=theme.CAPTION_SIZE,
        align="center",
    )
    note("the 42 is the argument itself, not an entry in any table", row)

    scene.text(
        "Most people expect the opposite of both rows: the 42 in the table, and the 6 thrown away.",
        0,
        row + height + theme.GRID,
        size=theme.CAPTION_SIZE,
        colour=theme.MUTED,
    )
    return scene


gallery.add(_where_the_42_lives())

gallery.add(
    figures.flow(
        "two-constant-folders",
        ["the tree", "folded on the tree", "the control flow graph", "folded on the graph"],
        title="CPython folds constants twice",
        labels=[
            "ast_preprocess.c, which this notebook skips",
            "codegen, then flowgraph",
            "flowgraph.c, the one you can watch",
        ],
        tones=["input", "quiet", "intermediate", "durable"],
    )
)

raise SystemExit(gallery.save())
