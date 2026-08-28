#!/usr/bin/env python
"""The diagrams for T07, the machine runs.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The two carrying the lesson are `the-loop`, which is the whole interpreter in four boxes,
and `two-stacks`, which is the picture that explains why ninety thousand Python calls are
fine and five thousand calls that pass through C are not.
"""

from nbdiagram import Gallery, figures, stages
from nbdiagram.scene import Scene
from pyxray import theme

gallery = Gallery("t07-the-machine-runs")

gallery.add(
    stages.map(
        "where-we-are",
        highlight=stages.ANSWER,
        title="Where this lesson sits",
        caption="The last box. Everything up to here built a code object, and this is the part that runs it.",
    )
)


def _the_loop() -> Scene:
    """The interpreter, in four boxes and one arrow that goes back to the start.

    Drawn as a ring rather than a row because the going back is the point, and a row with a
    long return arrow underneath reads as a pipeline with an afterthought.
    """
    scene = Scene("the-loop")
    width = 320
    height = 100
    gap_x = 220
    gap_y = 130

    scene.text("The whole interpreter", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    steps = [
        ("read two bytes", "opcode and argument", "input", 0, 0),
        ("look up the handler", "one entry per opcode", "intermediate", 1, 0),
        ("run it", "push, pop, compare, call", "focus", 1, 1),
        ("move the pointer on", "past the inline caches", "durable", 0, 1),
    ]
    boxes = []
    for label, note, tone, column, row in steps:
        x = column * (width + gap_x)
        y = top + row * (height + gap_y)
        boxes.append(scene.box(label, x, y, width=width, height=height, tone=tone))
        scene.text(note, x, y + height + 8, size=theme.CAPTION_SIZE, colour=theme.MUTED)

    scene.arrow(boxes[0], boxes[1])
    scene.arrow(boxes[1], boxes[2], sides=("bottom", "top"))
    scene.arrow(boxes[2], boxes[3], sides=("left", "right"))
    scene.arrow(boxes[3], boxes[0], sides=("top", "bottom"), label="and again")

    bottom = max(element.box[3] for element in scene.elements)
    for line, words in enumerate(
        [
            "That is it. There is no scheduler, no plan and no lookahead. The interpreter reads one",
            "instruction, does what it says, and reads the next one. Everything Python can do is one",
            "of the handlers in the top right box, and there are about two hundred of them.",
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


gallery.add(_the_loop())


gallery.add(
    figures.table(
        "three-ways-to-jump",
        ["how the handler is reached", "what it costs", "when CPython uses it"],
        [
            [
                "switch (opcode)",
                "one bounds check, one indirect jump",
                "the fallback, always correct",
            ],
            [
                "goto *targets[opcode]",
                "one indirect jump per instruction",
                "GCC and Clang, the usual build",
            ],
            [
                "tail call the handler",
                "one call the compiler turns into a jump",
                "--with-tail-call-interp",
            ],
        ],
        title="Three ways to get to the code for an opcode",
        caption="Same instruction set, same results, three ways of arriving. Only the third is new in 3.14.",
    )
)


def _a_frame() -> Scene:
    """The layout of an activation record, in the order the fields sit in memory."""
    scene = Scene("a-frame")
    width = 460
    height = 78

    scene.text("What one call needs, in one block of memory", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    parts = [
        (
            "specials",
            "the code object, the globals, the previous frame,\nand where we are in the bytecode",
            "quiet",
        ),
        ("locals", "one slot per name, plus cells and free variables", "input"),
        ("stack", "co_stacksize slots, empty until something pushes", "focus"),
    ]
    y = top
    for label, note, tone in parts:
        box = scene.box(label, 0, y, width=width, height=height, tone=tone)
        scene.text(
            note,
            width + 24,
            y + height / 2 - theme.CAPTION_SIZE * theme.LINE_HEIGHT / 2,
            size=theme.CAPTION_SIZE,
            colour=theme.MUTED,
        )
        y = box.box[3]

    bottom = max(element.box[3] for element in scene.elements)
    for line, words in enumerate(
        [
            "The specials are a fixed size, so the interpreter knows where the locals start without",
            "looking anything up, and the stack starts a known distance after that. Two pointers is",
            "all it has to carry: where this frame begins, and how far up the stack has grown.",
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


gallery.add(_a_frame())


def _two_stacks() -> Scene:
    """Why 90000 Python calls are fine and 5000 calls through C are not."""
    scene = Scene("two-stacks")
    width = 260
    cell = 44
    gap = 140

    scene.text("Two stacks, and only one of them is small", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    columns = [
        (
            "def f(): return f()",
            ["f", "f", "f", "f", "f", "f"],
            ["_PyEval_EvalFrameDefault"],
            "input",
        ),
        (
            "def f(): return sorted([1], key=f)",
            ["f", "f", "f"],
            ["_PyEval_EvalFrameDefault", "list.sort", "_PyEval_EvalFrameDefault", "list.sort"],
            "warning",
        ),
    ]

    for index, (heading, python_frames, c_frames, tone) in enumerate(columns):
        x = index * (2 * width + gap)
        scene.text(heading, x, top, size=theme.CAPTION_SIZE, colour=theme.INK, mono=True)
        head = top + theme.CAPTION_SIZE * theme.LINE_HEIGHT + 12
        scene.text("per thread data stack", x, head, size=theme.CAPTION_SIZE, colour=theme.MUTED)
        scene.text("C stack", x + width + 30, head, size=theme.CAPTION_SIZE, colour=theme.MUTED)
        body = head + theme.CAPTION_SIZE * theme.LINE_HEIGHT + 8
        for row, name in enumerate(python_frames):
            scene.box(
                name,
                x,
                body + row * cell,
                width=width,
                height=cell,
                tone=tone,
                mono=True,
                size=theme.CAPTION_SIZE,
                align="center",
            )
        for row, name in enumerate(c_frames):
            scene.box(
                name,
                x + width + 30,
                body + row * cell,
                width=width + 90,
                height=cell,
                tone="quiet",
                mono=True,
                size=theme.CAPTION_SIZE,
                align="center",
            )

    bottom = max(element.box[3] for element in scene.elements)
    for line, words in enumerate(
        [
            "On the left every call is Python calling Python, so CALL pushes a frame on the data stack and",
            "jumps. The C stack never moves, and ninety thousand of these fit. On the right each call goes out",
            "through sorted and back in, so both stacks grow, and the C stack is a few megabytes the operating",
            "system handed out once. That is the one that runs out first.",
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


gallery.add(_two_stacks())


gallery.add(
    figures.table(
        "what-you-can-watch",
        ["event", "fires when", "what the callback gets"],
        [
            ["PY_START", "a Python function begins", "code, offset"],
            ["PY_RETURN", "it returns normally", "code, offset, value"],
            ["PY_UNWIND", "it leaves because of an exception", "code, offset, exception"],
            ["LINE", "execution reaches a new line", "code, line number"],
            ["INSTRUCTION", "every single instruction", "code, offset"],
            ["JUMP", "a jump is taken", "code, offset, target"],
            ["BRANCH_LEFT", "a two way branch goes one way", "code, offset, target"],
            ["BRANCH_RIGHT", "and the other way", "code, offset, target"],
            ["RAISE", "an exception is raised", "code, offset, exception"],
        ],
        title="What sys.monitoring will tell you",
        caption="Nine of the twenty events. Ask for one and the rest cost nothing, which is the whole design.",
    )
)


gallery.add(
    figures.compare(
        "turning-an-event-off",
        (
            "callback returns None",
            [
                "pass 1  fires",
                "pass 2  fires",
                "pass 3  fires",
                "...",
                "40 calls for a 5 pass loop",
            ],
        ),
        (
            "callback returns DISABLE",
            [
                "pass 1  fires",
                "pass 2  quiet",
                "pass 3  quiet",
                "...",
                "15 calls, one per location",
            ],
        ),
        title="Why sys.monitoring is cheap and settrace is not",
        verdict="DISABLE patches that one location out. Nothing else in the program slows down.",
        verdict_tone="durable",
    )
)


def _where_the_numbers_come_from() -> Scene:
    """The stepper is two sources joined, and the lesson has to be honest about which is which."""
    scene = Scene("where-the-numbers-come-from")
    width = 380
    height = 96

    scene.text("How the stepper knows the stack height", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    left = scene.box(
        "worked out ahead of time",
        0,
        top,
        width=width,
        height=height,
        tone="intermediate",
    )
    scene.text(
        "pyxray.stack walks the code object\nand gets a height for every offset",
        0,
        top + height + 8,
        size=theme.CAPTION_SIZE,
        colour=theme.MUTED,
    )
    right = scene.box(
        "observed while it ran",
        0,
        top + height + 3 * theme.CAPTION_SIZE * theme.LINE_HEIGHT + 30,
        width=width,
        height=height,
        tone="input",
    )
    scene.text(
        "sys.monitoring reports which offset\nran, and in what order",
        0,
        right.box[3] + 8,
        size=theme.CAPTION_SIZE,
        colour=theme.MUTED,
    )

    joined = scene.box(
        "the listing you read",
        width + 160,
        (left.box[1] + right.box[3]) / 2 - height / 2,
        width=width,
        height=height,
        tone="focus",
    )
    scene.arrow(left, joined)
    scene.arrow(right, joined)

    bottom = max(element.box[3] for element in scene.elements)
    for line, words in enumerate(
        [
            "Nothing in the standard library can read the values on the stack, and this does not either.",
            "The order is a real observation of a real run. The heights are the compiler's own answer,",
            "looked up by offset. Both are true, and they are true in different ways.",
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


gallery.add(_where_the_numbers_come_from())


gallery.add(
    figures.pipeline(
        "a-call-in-four-moves",
        [
            ("CALL", "push a frame"),
            ("jump", "to the callee"),
            ("run", "the same loop"),
            ("RETURN_VALUE", "pop the frame"),
        ],
        title="What happens when Python calls Python",
        caption="No C function is entered and nothing recurses. The interpreter pushes a frame on the data stack, jumps to the callee's first instruction, and keeps going round the same loop.",
    )
)


raise SystemExit(gallery.save())
