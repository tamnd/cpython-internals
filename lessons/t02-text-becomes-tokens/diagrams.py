#!/usr/bin/env python
"""The diagrams for T02, text becomes tokens.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The pictures here are doing real work. A zero width token, a tab landing on a stop, and a
tokenizer changing mode partway through a string are all things you can describe in a
sentence and nobody will picture correctly.
"""

from nbdiagram import Gallery, figures
from nbdiagram.scene import Scene, text_width
from pyxray import theme

gallery = Gallery("t02-text-becomes-tokens")

# The map, with the tokenizer lit up. T01 draws the same seven stages. Reusing the picture
# with the focus moved is worth much more than drawing a new one, because the reader
# recognises where they are instead of having to read it again.
gallery.add(
    figures.pipeline(
        "where-we-are",
        [
            ("your file", "the text you wrote"),
            ("tokens", "Parser/lexer/lexer.c"),
            ("syntax tree", "Parser/parser.c"),
            ("symbol table", "Python/symtable.c"),
            ("bytecode", "Python/compile.c"),
            ("the answer", "Python/ceval.c"),
        ],
        highlight=1,
        title="Where this lesson sits",
        caption="This lesson is about the second box. Once it is finished, nothing further along reads your file.",
    )
)

gallery.add(
    figures.spans(
        "one-line-many-tokens",
        "    return x + 1",
        [(0, 4, "INDENT"), (4, 10, "NAME"), (11, 12, "NAME"), (13, 14, "OP"), (15, 16, "NUMBER")],
        title="What the tokenizer sees in one line",
        caption="INDENT is the four spaces themselves. It has width, and it carries the text it matched.",
    )
)

gallery.add(
    figures.flow(
        "who-knows-about-keywords",
        ["the tokenizer", "the parser"],
        title="Where a keyword is decided",
        labels=["hands over NAME 'if'"],
        tones=["input", "durable"],
    )
)

gallery.add(
    figures.table(
        "name-or-keyword",
        ["you wrote", "tokenizer says", "parser checks", "parser says"],
        [
            ["if", "NAME", "is it in the table?", "IF"],
            ["answer", "NAME", "is it in the table?", "NAME"],
        ],
        title="Same token type, different answer",
        caption="The tokenizer does not decide. That is why match and case still work as variable names.",
    )
)


def _asymmetry() -> Scene:
    """INDENT against DEDENT, drawn against one shared ruler.

    One of these covers four columns and the other covers none. You can say that in a
    sentence and readers will nod and carry on picturing two mirror images. Drawing both on
    the same ruler, at the widths they really have, does not leave that option open.
    """
    scene = Scene("indent-is-not-symmetric")
    unit = 30
    columns = 8
    left = 200
    height = 56
    caption_x = left + columns * unit + 28

    scene.text("INDENT and DEDENT are not opposites", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    scene.text("column", left - 76, top, size=theme.CAPTION_SIZE, colour=theme.MUTED)
    for column in range(columns + 1):
        scene.text(
            str(column),
            left + column * unit,
            top,
            size=theme.CAPTION_SIZE,
            colour=theme.MUTED,
            align="centre",
        )
    ruler = top + theme.CAPTION_SIZE * theme.LINE_HEIGHT + 6
    rows = ruler + 2 * height + theme.GRID
    for column in range(columns + 1):
        x = left + column * unit
        scene.line([(x, ruler), (x, rows)], colour=theme.LINE, dashed=True)

    def annotate(row: float, words: str) -> None:
        scene.text(
            words,
            caption_x,
            row + (height - theme.CAPTION_SIZE * theme.LINE_HEIGHT) / 2,
            size=theme.CAPTION_SIZE,
            colour=theme.MUTED,
        )

    row = ruler + 8
    scene.text(
        "opening a block",
        0,
        row + (height - theme.BODY_SIZE * theme.LINE_HEIGHT) / 2,
        size=theme.BODY_SIZE,
    )
    scene.box("", left, row, width=4 * unit, height=height, tone="input")
    annotate(row, "INDENT: 4 columns wide, text is the four spaces")

    row += height + theme.GRID
    scene.text(
        "closing a block",
        0,
        row + (height - theme.BODY_SIZE * theme.LINE_HEIGHT) / 2,
        size=theme.BODY_SIZE,
    )
    scene.line(
        [(left + 4 * unit, row), (left + 4 * unit, row + height)],
        colour=theme.tone("warning").stroke,
    )
    annotate(row, "DEDENT: 0 columns wide, text is the empty string")

    scene.text(
        "A DEDENT takes up no room, so three blocks can close on one line and you get three DEDENTs at the same column.",
        0,
        rows + theme.GRID,
        size=theme.CAPTION_SIZE,
        colour=theme.MUTED,
    )
    return scene


gallery.add(_asymmetry())

gallery.add(
    figures.table(
        "how-the-stack-moves",
        ["the line", "column", "stack after", "emitted"],
        [
            ["if a:", "0", "[0]", ""],
            ["    if b:", "4", "[0 4]", "INDENT"],
            ["        c = 1", "8", "[0 4 8]", "INDENT"],
            ["d = 2", "0", "[0]", "DEDENT DEDENT"],
        ],
        title="The whole indentation algorithm, one line at a time",
        caption="Bigger than the top: push and emit one INDENT. Smaller: pop until it matches, one DEDENT per pop.",
    )
)


def _tab_stops() -> Scene:
    """Where a tab lands.

    A tab is not worth a number of columns, it is worth however many columns are left
    before the next stop. Three examples on one ruler make that obvious, and nothing else
    does: the same tab character is one column wide in one row and eight in another.
    """
    scene = Scene("where-a-tab-lands")
    unit = 34
    columns = 16
    height = 34

    examples = [
        (0, 8, 'a tab on its own      "\\tx"'),
        (7, 8, 'seven spaces, a tab   "       \\tx"'),
        (8, 16, 'eight spaces, a tab   "        \\tx"'),
    ]
    left = max(text_width(words, theme.CAPTION_SIZE, mono=True) for _, _, words in examples)
    left += theme.GRID

    scene.text("A tab jumps to the next multiple of 8", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID + 26

    for column in range(columns + 1):
        scene.text(
            str(column),
            left + column * unit,
            top,
            size=theme.CAPTION_SIZE,
            colour=theme.MUTED,
            align="centre",
        )
    ruler = top + theme.CAPTION_SIZE * theme.LINE_HEIGHT + 6

    bottom = ruler + len(examples) * (height + 12)

    for column in range(columns + 1):
        x = left + column * unit
        stop = column % 8 == 0
        scene.line(
            [(x, ruler), (x, bottom)],
            colour=theme.tone("focus").stroke if stop else theme.LINE,
            dashed=not stop,
        )
    for column in (0, 8, 16):
        scene.text(
            "tab stop",
            left + column * unit,
            ruler - theme.CAPTION_SIZE * theme.LINE_HEIGHT - 26,
            size=theme.CAPTION_SIZE,
            colour=theme.tone("focus").stroke,
            align="centre",
        )

    row = ruler + 8
    for start, stop, words in examples:
        scene.text(
            words,
            0,
            row + (height - theme.CAPTION_SIZE * theme.LINE_HEIGHT) / 2,
            size=theme.CAPTION_SIZE,
            mono=True,
        )
        if start:
            scene.box("", left, row, width=start * unit, height=height, tone="quiet")
        # Only the number goes inside the bar. One of these bars is a single column wide,
        # and a sentence in it would spill over three neighbours.
        scene.box(
            str(stop - start),
            left + start * unit,
            row,
            width=(stop - start) * unit,
            height=height,
            tone="focus",
            size=theme.CAPTION_SIZE,
            align="center",
        )
        scene.text(
            f"the tab is worth {stop - start} columns here",
            left + columns * unit + 24,
            row + (height - theme.CAPTION_SIZE * theme.LINE_HEIGHT) / 2,
            size=theme.CAPTION_SIZE,
            colour=theme.MUTED,
        )
        row += height + 12

    scene.text(
        "The same character in all three rows. What it is worth depends on what came before it.",
        0,
        bottom + theme.GRID,
        size=theme.CAPTION_SIZE,
        colour=theme.MUTED,
    )
    return scene


gallery.add(_tab_stops())

gallery.add(
    figures.compare(
        "two-counts-of-one-line",
        ("a tab is worth 8", ["tab      -> col 8", "8 spaces -> col 8", "same"]),
        ("a tab is worth 1", ["tab      -> col 1", "8 spaces -> col 8", "different"]),
        title="Every line is measured twice",
        verdict="When the two counts disagree about which line is deeper, CPython raises TabError.",
    )
)

gallery.add(
    figures.table(
        "a-dedent-with-no-home",
        ["the line", "column", "stack after", "what happens"],
        [
            ["if x:", "0", "[0]", ""],
            ["  y = 1", "2", "[0 2]", "INDENT"],
            [" z = 2", "1", "[0]", "popped 2, but 1 is not 0"],
        ],
        tones=["quiet", "quiet", "warning"],
        title="A dedent to a column nobody indented to",
        caption="Nothing left to pop and still no match, so the tokenizer stops here with an error.",
    )
)


def _two_streams() -> Scene:
    """What tokenize hands you, against what the compiler is given.

    Most people assume the compiler sees more than they do. It sees less, and drawing the
    two rows one above the other with the dropped tokens left as empty outlines makes the
    difference impossible to misread.
    """
    scene = Scene("two-token-streams")
    kinds = ["ENCODING", "NAME", "OP", "NUMBER", "COMMENT", "NL", "NEWLINE", "ENDMARKER"]
    dropped = {"COMMENT", "NL"}
    height = 40

    scene.text("The compiler sees fewer tokens than you do", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    widths = [text_width(kind, theme.CAPTION_SIZE) + 2 * theme.PADDING for kind in kinds]
    lefts = [sum(widths[:index]) + 8 * index for index in range(len(kinds))]
    left = max(
        text_width(label, theme.CAPTION_SIZE)
        for label in ["what tokenize gives you", "what the compiler gets"]
    )
    left += theme.GRID

    for row_index, (label, keep) in enumerate(
        [("what tokenize gives you", False), ("what the compiler gets", True)]
    ):
        y = top + row_index * (height + theme.GAP)
        scene.text(
            label,
            0,
            y + (height - theme.CAPTION_SIZE * theme.LINE_HEIGHT) / 2,
            size=theme.CAPTION_SIZE,
            colour=theme.MUTED,
        )
        for kind, x, width in zip(kinds, lefts, widths, strict=True):
            if keep and kind in dropped:
                scene.line(
                    [
                        (left + x, y),
                        (left + x + width, y),
                        (left + x + width, y + height),
                        (left + x, y + height),
                        (left + x, y),
                    ],
                    colour=theme.LINE,
                    dashed=True,
                )
                continue
            scene.box(
                kind,
                left + x,
                y,
                width=width,
                height=height,
                tone="warning" if kind in dropped else "intermediate",
                size=theme.CAPTION_SIZE,
                align="center",
            )

    scene.text(
        "COMMENT and NL exist so that formatters can see them. The compiler asks for them to be left out.",
        0,
        top + 2 * height + theme.GAP + theme.GRID,
        size=theme.CAPTION_SIZE,
        colour=theme.MUTED,
    )
    return scene


gallery.add(_two_streams())


def _mode_switch() -> Scene:
    """The two modes an f-string bounces between.

    This is the one picture that explains why PEP 701 got so much for free. The expression
    inside the braces is tokenized by the ordinary code, in the ordinary mode, so it did
    not need a single special case.
    """
    scene = Scene("the-mode-switch")
    width = 260
    height = 84
    gap = 260

    scene.text("An f-string is the tokenizer changing its mind", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID + 30

    normal = scene.box("normal mode", 0, top, width=width, height=height, tone="input")
    fstring = scene.box("f-string mode", width + gap, top, width=width, height=height, tone="focus")

    scene.arrow((width, top + 24), (width + gap, top + 24))
    scene.text(
        'sees  f"  or  }',
        width + gap / 2,
        top - 6,
        size=theme.CAPTION_SIZE,
        colour=theme.MUTED,
        mono=True,
        align="centre",
    )
    scene.arrow((width + gap, top + height - 24), (width, top + height - 24))
    scene.text(
        'sees  {  or  "',
        width + gap / 2,
        top + height + 8,
        size=theme.CAPTION_SIZE,
        colour=theme.MUTED,
        mono=True,
        align="centre",
    )

    # Clear of the lower arrow's own label, which sits just under the boxes. Two rows of
    # caption on one line read as a single sentence and say something nobody meant.
    under = top + height + theme.CAPTION_SIZE * theme.LINE_HEIGHT + theme.GRID
    for box, words in (
        (normal, "the code between the braces"),
        (fstring, "the quotes and the literal text"),
    ):
        scene.text(
            words,
            box.centre()[0],
            under,
            size=theme.CAPTION_SIZE,
            colour=theme.MUTED,
            align="centre",
        )
    scene.text(
        "The code inside the braces goes through the ordinary tokenizer, which is why nested quotes and backslashes work.",
        0,
        under + theme.CAPTION_SIZE * theme.LINE_HEIGHT + theme.GRID,
        size=theme.CAPTION_SIZE,
        colour=theme.MUTED,
    )
    return scene


gallery.add(_mode_switch())

raise SystemExit(gallery.save())
