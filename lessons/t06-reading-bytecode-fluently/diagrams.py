#!/usr/bin/env python
"""The diagrams for T06, reading bytecode fluently.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `one-argument-six-meanings`. Every listing a reader looks
at is full of small numbers that all print the same way and none of which mean the same
thing, and until that is cleared up the rest of the listing is noise.
"""

from nbdiagram import Gallery, figures, stages
from nbdiagram.scene import Scene, text_width
from pyxray import theme

gallery = Gallery("t06-reading-bytecode-fluently")

gallery.add(
    stages.map(
        "where-we-are",
        highlight=stages.CODE_OBJECT,
        title="Where this lesson sits",
        caption="Nothing new gets built here. This is the lesson where you learn to read what the last one made.",
    )
)


def _two_bytes() -> Scene:
    """The unit everything else in the lesson is measured in."""
    scene = Scene("two-bytes")
    height = 64
    width = 200

    scene.text("One instruction is two bytes", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    left = scene.box(
        "5c",
        0,
        top,
        width=width,
        height=height,
        tone="input",
        mono=True,
        size=theme.BODY_SIZE,
        align="center",
    )
    right = scene.box(
        "00",
        width,
        top,
        width=width,
        height=height,
        tone="durable",
        mono=True,
        size=theme.BODY_SIZE,
        align="center",
    )
    for element, note in (
        (left, "opcode 92, LOAD_NAME"),
        (right, "argument 0, one byte"),
    ):
        scene.text(
            note,
            element.box[0] + (element.box[2] - element.box[0]) / 2,
            element.box[3] + 12,
            size=theme.CAPTION_SIZE,
            colour=theme.MUTED,
            align="centre",
        )

    bottom = max(element.box[3] for element in scene.elements)
    for line, words in enumerate(
        [
            "Two bytes out of a real code object. Every instruction is the same size, which is what",
            "keeps the interpreter's inner loop as simple as it is. It also means the argument has to",
            "fit in one byte, and the next few sections are about what happens when it does not.",
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


gallery.add(_two_bytes())

# The figure the lesson is built around. Five instructions, all printed with a 1 after
# them, and five unrelated meanings for that 1.
gallery.add(
    figures.table(
        "one-argument-six-meanings",
        ["you see", "the 1 means", "so it reads as"],
        [
            ["LOAD_CONST      1", "index into co_consts", "load whatever is at co_consts[1]"],
            ["LOAD_NAME       1", "index into co_names", "look up the name co_names[1]"],
            ["LOAD_FAST       1", "which local slot", "load local number 1"],
            ["LOAD_SMALL_INT  1", "the number itself", "push the integer 1"],
            ["CALL            1", "how many arguments", "call with one argument"],
            ["JUMP_FORWARD    1", "how far, in instructions", "skip the next instruction"],
        ],
        title="Six ones, six meanings",
        caption="The argument byte has no meaning of its own. The opcode decides what it is counting.",
    )
)


def _the_stack_rising() -> Scene:
    """What the stack is doing while five instructions run.

    Drawn as five small stacks rather than one stack with arrows, because the reader needs
    to see the shape at each moment and an animated diagram is not available on GitHub.
    """
    scene = Scene("the-stack-rising")
    cell = 46
    width = 150
    gap = 74

    scene.text("total = total + n, one instruction at a time", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    moments = [
        ("start", []),
        ("LOAD_NAME total", ["total"]),
        ("LOAD_NAME n", ["total", "n"]),
        ("BINARY_OP +", ["sum"]),
        ("STORE_NAME total", []),
    ]
    tallest = max(len(contents) for _, contents in moments)
    floor = top + theme.CAPTION_SIZE * theme.LINE_HEIGHT + 8 + tallest * cell

    for index, (label, contents) in enumerate(moments):
        x = index * (width + gap)
        scene.text(label, x, top, size=theme.CAPTION_SIZE, colour=theme.MUTED, mono=True)
        for height, value in enumerate(contents):
            scene.box(
                value,
                x,
                floor - (height + 1) * cell,
                width=width,
                height=cell,
                tone="focus" if height == len(contents) - 1 else "intermediate",
                mono=True,
                size=theme.CAPTION_SIZE,
                align="center",
            )
        scene.line([(x, floor), (x + width, floor)], colour=theme.LINE)

    bottom = max(element.box[3] for element in scene.elements)
    for line, words in enumerate(
        [
            "Two loads put two values on the stack. The add takes both off and puts one back.",
            "The store takes that one off and nothing is left. Every instruction in a listing does",
            "this, and once you can see it happening you can read a listing without running it.",
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


gallery.add(_the_stack_rising())


def _extended_arg() -> Scene:
    """Four real bytes out of a real code object, and how they make a number bigger than 255."""
    scene = Scene("extended-arg")
    height = 60

    scene.text("When one byte is not enough", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    cells = [
        ("43", "EXTENDED_ARG", "quiet"),
        ("01", "carry 1", "quiet"),
        ("5c", "LOAD_NAME", "input"),
        ("2c", "and 44", "input"),
    ]
    width = 150
    for index, (byte, note, tone) in enumerate(cells):
        scene.box(
            byte,
            index * width,
            top,
            width=width,
            height=height,
            tone=tone,
            mono=True,
            size=theme.BODY_SIZE,
            align="center",
        )
        scene.text(
            note,
            index * width + width / 2,
            top + height + 10,
            size=theme.CAPTION_SIZE,
            colour=theme.MUTED,
            align="centre",
        )

    label = "1 * 256 + 44  =  300"
    result = scene.box(
        label,
        4 * width + 90,
        top,
        width=text_width(label, theme.CAPTION_SIZE, mono=True) + 2 * theme.PADDING,
        height=height,
        tone="durable",
        mono=True,
        size=theme.CAPTION_SIZE,
        align="center",
    )
    scene.text(
        "reads co_names[300], which is print",
        result.box[0],
        result.box[3] + 10,
        size=theme.CAPTION_SIZE,
        colour=theme.MUTED,
    )

    bottom = max(element.box[3] for element in scene.elements)
    for line, words in enumerate(
        [
            "A file with 256 different names in it needs an index that does not fit in a byte, so",
            "the compiler writes an extra instruction in front carrying the high bits. The interpreter",
            "shifts what it has left by eight and adds the next argument on. Up to three of these can stack.",
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


gallery.add(_extended_arg())


def _counting_a_jump() -> Scene:
    """Why a jump argument never matches the distance you measure with your finger."""
    scene = Scene("counting-a-jump")
    height = 56
    width = 172

    scene.text("How far is JUMP_BACKWARD 14", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    cells = [
        ("14\nFOR_ITER", "durable"),
        ("18\nSTORE_NAME", "quiet"),
        ("20 to 36\nloop body", "quiet"),
        ("38\nJUMP_BACKWARD", "focus"),
        ("40\ncache", "warning"),
    ]
    boxes = []
    for index, (label, tone) in enumerate(cells):
        boxes.append(
            scene.box(
                label,
                index * width,
                top,
                width=width,
                height=height + 18,
                tone=tone,
                mono=True,
                size=theme.CAPTION_SIZE,
                align="center",
            )
        )

    # The back edge is routed under the row rather than drawn straight across it, because a
    # straight arrow from the jump to its target passes through every box in between and
    # the reader has to work out which end it came from.
    row_bottom = boxes[0].box[3]
    lane = row_bottom + 54
    start_x = boxes[4].centre()[0]
    end_x = boxes[0].centre()[0]
    scene.line([(start_x, row_bottom), (start_x, lane)])
    scene.line([(start_x, lane), (end_x, lane)])
    scene.arrow((end_x, lane), (end_x, row_bottom + 6))
    scene.text(
        "back 14 instructions, from byte 42",
        (start_x + end_x) / 2,
        lane + 10,
        size=theme.CAPTION_SIZE,
        colour=theme.MUTED,
        align="centre",
    )

    bottom = max(element.box[3] for element in scene.elements)
    for line, words in enumerate(
        [
            "The count starts after the jump and after its cache, at byte 42, and it counts",
            "instructions rather than bytes. So 42 minus 14 times 2 gives byte 14, which is the",
            "FOR_ITER at the top of the loop. Count in bytes and you land twenty eight too far along.",
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


gallery.add(_counting_a_jump())


def _how_tall_does_it_get() -> Scene:
    """co_stacksize is the worst case over every path, not the cost of the path taken."""
    scene = Scene("how-tall-does-it-get")
    width = 250
    height = 72

    scene.text("How the compiler works out co_stacksize", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    step = height + 110
    entry = scene.box(
        "test the condition\ndeepest here: 1",
        width * 0.65,
        top,
        width=width,
        height=height,
        tone="input",
        size=theme.CAPTION_SIZE,
        align="center",
    )
    cheap = scene.box(
        "the short branch\ndeepest here: 2",
        0,
        top + step,
        width=width,
        height=height,
        tone="intermediate",
        size=theme.CAPTION_SIZE,
        align="center",
    )
    dear = scene.box(
        "the long branch\ndeepest here: 5",
        width * 1.3,
        top + step,
        width=width,
        height=height,
        tone="focus",
        size=theme.CAPTION_SIZE,
        align="center",
    )
    joined = scene.box(
        "co_stacksize = 5",
        width * 0.65,
        top + 2 * step,
        width=width,
        height=height,
        tone="durable",
        size=theme.CAPTION_SIZE,
        align="center",
    )
    scene.arrow(entry, cheap, sides=("bottom", "top"))
    scene.arrow(entry, dear, sides=("bottom", "top"))
    scene.arrow(cheap, joined, sides=("bottom", "top"))
    scene.arrow(dear, joined, sides=("bottom", "top"))
    # Branch labels are placed by hand. An arrow label on a diagonal arrow lands wherever
    # the arrow started, which here is inside the box the arrow came out of.
    for element, word in ((cheap, "False"), (dear, "True")):
        scene.text(
            word,
            element.centre()[0],
            element.box[1] - theme.CAPTION_SIZE * theme.LINE_HEIGHT - 8,
            size=theme.CAPTION_SIZE,
            colour=theme.MUTED,
            align="centre",
        )

    bottom = max(element.box[3] for element in scene.elements)
    for line, words in enumerate(
        [
            "The frame is allocated once, before anything runs, so it has to be big enough for the",
            "worst path through the function. The compiler walks every path and keeps the largest",
            "number it sees. Nobody measures anything while the program is running.",
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


gallery.add(_how_tall_does_it_get())

gallery.add(
    figures.compare(
        "what-dis-does-not-show",
        (
            "what dis prints",
            [
                "  0  RESUME       0",
                " 14  FOR_ITER    12",
                " 18  STORE_NAME   1",
            ],
        ),
        (
            "what is in co_code",
            [
                "  0  RESUME       0",
                "  2  cache",
                " ...",
                " 14  FOR_ITER    12",
                " 16  cache",
                " 18  STORE_NAME   1",
            ],
        ),
        title="Why the offsets skip numbers",
        verdict="The gaps are real bytes. Count them and the jump arithmetic works out.",
        verdict_tone="durable",
    )
)

gallery.add(
    figures.pipeline(
        "reading-a-listing-cold",
        [
            ("what is loaded", "co_consts, co_names, co_varnames"),
            ("what is done to it", "the operator instructions"),
            ("where it goes", "the store instructions"),
            ("what happens next", "the jumps"),
        ],
        title="Four questions, in this order",
        caption="Nobody reads a disassembly top to bottom. This is the order that actually works.",
    )
)

raise SystemExit(gallery.save())
