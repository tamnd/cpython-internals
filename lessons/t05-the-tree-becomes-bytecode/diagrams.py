#!/usr/bin/env python
"""The diagrams for T05, the tree becomes bytecode.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `where-the-multiplication-went`. T01 promised the reader that
`6 * 7` is never multiplied while their program runs, and this is the picture of the three
instructions that would have done it turning into one instruction that already has the
answer.
"""

from nbdiagram import Gallery, figures, stages
from nbdiagram.scene import Scene, text_width
from pyxray import theme

gallery = Gallery("t05-the-tree-becomes-bytecode")

gallery.add(
    stages.map(
        "where-we-are",
        highlight=[stages.INSTRUCTIONS, stages.OPTIMIZED, stages.CODE_OBJECT],
        title="Where this lesson sits",
        caption="Three boxes, and one call. compile() does all of it without telling you where one stage ends.",
    )
)

gallery.add(
    figures.pipeline(
        "three-stages-in-one-call",
        [
            ("syntax tree", "Python/ast.c"),
            ("instructions", "Python/codegen.c"),
            ("blocks, tidied", "Python/flowgraph.c"),
            ("code object", "Python/assemble.c"),
        ],
        title="What compile() does, one file at a time",
        caption="Each arrow is a real function you can call on its own, which is what makes this lesson possible.",
    )
)

# The before and after that answers T01. Written out as literal instruction listings rather
# than described, because the reader is meant to count the rows.
gallery.add(
    figures.compare(
        "before-and-after",
        (
            "after codegen",
            [
                "RESUME 0",
                "ANNOTATIONS_PLACEHOLDER",
                "LOAD_CONST 0",
                "LOAD_CONST 1",
                "BINARY_OP 5",
                "STORE_NAME 0",
                "LOAD_CONST 2",
                "RETURN_VALUE",
            ],
        ),
        (
            "after the optimizer",
            [
                "RESUME 0",
                "LOAD_SMALL_INT 42",
                "STORE_NAME 0",
                "LOAD_COMMON_CONSTANT 7",
                "RETURN_VALUE",
            ],
        ),
        title="answer = 6 * 7, before and after the optimizer",
        verdict="Eight instructions in, five out, and the multiplication is not one of them.",
        verdict_tone="durable",
    )
)


def _where_the_multiplication_went() -> Scene:
    """Three instructions becoming one, which is the whole promise T01 made."""
    scene = Scene("where-the-multiplication-went")
    width = 240
    height = 46
    gap = 12

    scene.text("Where the multiplication went", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    opcodes = ["LOAD_CONST 0    (6)", "LOAD_CONST 1    (7)", "BINARY_OP 5     (*)"]
    inner = width + 2 * theme.PADDING
    header = theme.CAPTION_SIZE * theme.LINE_HEIGHT + 18
    before = scene.panel(
        "three instructions",
        0,
        top,
        inner,
        header + len(opcodes) * (height + gap) - gap + theme.PADDING,
        tone="quiet",
        mono=True,
    )
    for index, opcode in enumerate(opcodes):
        scene.box(
            opcode,
            theme.PADDING,
            top + header + index * (height + gap),
            width=width,
            height=height,
            tone="input",
            mono=True,
            size=theme.CAPTION_SIZE,
        )

    after = scene.box(
        "LOAD_SMALL_INT 42",
        inner + 220,
        (before.box[1] + before.box[3]) / 2 - (height + gap) / 2,
        width=width,
        height=height + gap,
        tone="durable",
        mono=True,
        size=theme.CAPTION_SIZE,
        align="center",
    )
    scene.arrow(before, after, label="fold_const_binop")

    bottom = max(element.box[3] for element in scene.elements)
    for line, words in enumerate(
        [
            "The optimizer runs the multiply itself, puts the answer where the operands were,",
            "and turns the two loads into nothing. 42 is small enough to ride inside the instruction,",
            "so it does not even reach the constants table.",
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


gallery.add(_where_the_multiplication_went())


def _the_unreachable_block() -> Scene:
    """Why the optimizer works on a graph and not on a list.

    Drawn with one block deliberately left with no arrow pointing into it, because that is
    literally the test the compiler applies. It counts arrows in, and a block with none goes.
    """
    scene = Scene("the-unreachable-block")
    width = 260
    height = 76

    scene.text("How dead code is found", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    entry = scene.box(
        "LOAD_CONST False\nTO_BOOL\nPOP_JUMP_IF_FALSE",
        0,
        top,
        width=width,
        height=height,
        tone="input",
        mono=True,
        size=theme.CAPTION_SIZE,
    )
    orphan = scene.box(
        'print("never")',
        width + 150,
        top,
        width=width,
        height=height,
        tone="warning",
        mono=True,
        size=theme.CAPTION_SIZE,
        align="center",
    )
    after = scene.box(
        'print("after")',
        0,
        top + height + 90,
        width=width,
        height=height,
        tone="durable",
        mono=True,
        size=theme.CAPTION_SIZE,
        align="center",
    )
    scene.arrow(entry, after, label="always taken", sides=("bottom", "top"))

    scene.text(
        "no arrow points here",
        orphan.box[0],
        orphan.box[3] + 14,
        size=theme.CAPTION_SIZE,
        colour=theme.TONES["warning"].stroke,
    )

    bottom = max(element.box[3] for element in scene.elements)
    for line, words in enumerate(
        [
            "The condition folds to False, so the jump is taken every time and the arrow into the",
            "middle block disappears. Then a walk from the entry never arrives there, its count of",
            "arrows in stays at zero, and the whole block is deleted. The string is not in the file.",
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


gallery.add(_the_unreachable_block())

gallery.add(
    figures.table(
        "four-limits",
        ["limit", "value", "what it stops", "the line either side of it"],
        [
            ["MAX_INT_SIZE", "128 bits", "huge integers", "2 ** 64 folds, 2 ** 65 does not"],
            [
                "MAX_COLLECTION_SIZE",
                "256 items",
                "repeated tuples",
                "(1,2) * 128 folds, * 129 does not",
            ],
            ["MAX_STR_SIZE", "4096 chars", "repeated strings", "'-' * 4096 folds, * 4097 does not"],
            ["MAX_TOTAL_ITEMS", "1024 items", "nested collections", "counted through the nesting"],
        ],
        title="The four numbers that decide how much work happens now",
        caption="Folding trades a bigger file for less work later, and past these sizes the trade stops paying.",
    )
)

gallery.add(
    figures.nest(
        "what-the-assembler-makes",
        (
            "code object",
            [
                "co_code            the bytes",
                "co_consts          values too big to ride along",
                "co_names           globals and attributes, by name",
                "co_varnames        the frame slots",
                "co_linetable       byte range to source position",
                "co_exceptiontable  byte range to handler",
                "co_stacksize       how deep the stack ever gets",
            ],
        ),
        title="What the assembler hands back",
        caption="The last two are built here and nowhere else. Neither one is in the bytes.",
    )
)


def _one_instruction() -> Scene:
    """Two bytes, and the caches that make the third instruction start where it does."""
    scene = Scene("one-instruction")
    height = 54

    scene.text("Why offsets jump by more than two", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    cells = [
        ("RESUME", "input"),
        ("0", "input"),
        ("cache", "quiet"),
        ("cache", "quiet"),
        ("LOAD_NAME", "durable"),
        ("0", "durable"),
    ]
    width = max(text_width(label, theme.CAPTION_SIZE, mono=True) for label, _ in cells) + 28
    for index, (label, tone) in enumerate(cells):
        scene.box(
            label,
            index * width,
            top,
            width=width,
            height=height,
            tone=tone,
            mono=True,
            size=theme.CAPTION_SIZE,
            align="center",
        )
        scene.text(
            str(index),
            index * width + width / 2,
            top + height + 10,
            size=theme.CAPTION_SIZE,
            colour=theme.MUTED,
            mono=True,
            align="centre",
        )

    bottom = max(element.box[3] for element in scene.elements)
    for line, words in enumerate(
        [
            "Every instruction is one byte of opcode and one byte of argument. Some of them are",
            "followed by blank space the interpreter writes into while the program runs, and that",
            "space is real bytes in co_code. It is why the next instruction starts at 4 and not 2.",
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


gallery.add(_one_instruction())

raise SystemExit(gallery.save())
