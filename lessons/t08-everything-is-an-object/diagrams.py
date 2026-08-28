#!/usr/bin/env python
"""The diagrams for T08, everything is an object.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The two carrying the lesson are `the-shelf`, which is the small integer cache drawn as the
row of prebuilt objects it literally is, and `borrowed-or-not`, which is why the advice
every tutorial gives about `sys.getrefcount` stopped being true in 3.14.
"""

from nbdiagram import Gallery, figures, stages
from nbdiagram.scene import Scene
from pyxray import theme

gallery = Gallery("t08-everything-is-an-object")

gallery.add(
    stages.map(
        "where-we-are",
        title="The pipeline, with nothing highlighted",
        caption="This lesson is not one of the boxes. It is about the values that travel along every arrow between them.",
    )
)


def _the_header() -> Scene:
    """What is in front of every object, drawn in the order the fields sit in memory."""
    scene = Scene("the-header")
    width = 400
    height = 74

    scene.text("What every object starts with", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    parts = [
        ("ob_refcnt", "how many places are holding this object", "input"),
        ("ob_type", "a pointer to the type, which is another object", "intermediate"),
        (
            "whatever this type needs",
            "an int keeps digits here, a list keeps a pointer\nto its array, a function keeps its code object",
            "focus",
        ),
    ]
    y = top
    for label, note, tone in parts:
        box = scene.box(label, 0, y, width=width, height=height, tone=tone, mono=True)
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
            "Two fields, then the data. That is what makes an int and a list and a function all the",
            "same kind of thing to the interpreter: it can hold one, count it, and ask what it is,",
            "without knowing anything else about it.",
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


gallery.add(_the_header())


gallery.add(
    figures.table(
        "four-questions",
        ["you ask", "you get", "what it does not tell you"],
        [
            ["id(x)", "where the object is", "anything about equal objects elsewhere"],
            ["type(x)", "the object holding the behaviour", "which instance you are looking at"],
            [
                "sys.getrefcount(x)",
                "how many places hold it, plus a few",
                "which places, or for how long",
            ],
            ["sys.getsizeof(x)", "this object's own bytes", "anything it points at"],
        ],
        title="Four questions you can ask about any object",
        caption="The last column is where most confusion about all four of these comes from.",
    )
)


gallery.add(
    figures.compare(
        "is-versus-equals",
        (
            "a == b",
            [
                "calls the type",
                "int.__eq__ compares values",
                "str.__eq__ compares characters",
                "you can change what it means",
            ],
        ),
        (
            "a is b",
            [
                "compares two addresses",
                "no type is consulted",
                "no method is called",
                "you cannot change what it means",
            ],
        ),
        title="Two questions that look alike and are not related",
        verdict="Use is for None, True, False and sentinels. Use == for values. That is the whole rule.",
        verdict_tone="durable",
    )
)


def _the_shelf() -> Scene:
    """The small integer cache, drawn as the shelf of prebuilt objects it actually is."""
    scene = Scene("the-shelf")
    cell = 76
    height = 56

    scene.text(
        "The integers that were made before your program started", 0, 0, size=theme.TITLE_SIZE
    )
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    scene.text(
        "built once, at startup, and handed out forever",
        0,
        top,
        size=theme.CAPTION_SIZE,
        colour=theme.MUTED,
    )
    row = top + theme.CAPTION_SIZE * theme.LINE_HEIGHT + 10

    shelf = ["-5", "-4", "...", "0", "1", "...", "1023", "1024"]
    for index, label in enumerate(shelf):
        tone = "quiet" if label == "..." else "durable"
        scene.box(
            label,
            index * cell,
            row,
            width=cell - 6,
            height=height,
            tone=tone,
            mono=True,
            size=theme.CAPTION_SIZE,
            align="center",
        )

    edge = len(shelf) * cell + 40
    scene.box(
        "1025",
        edge,
        row,
        width=cell - 6,
        height=height,
        tone="warning",
        mono=True,
        size=theme.CAPTION_SIZE,
        align="center",
    )
    scene.text(
        "and everything past here is\nbuilt fresh, every time you ask",
        edge + cell + 16,
        row + 4,
        size=theme.CAPTION_SIZE,
        colour=theme.MUTED,
    )

    bottom = max(element.box[3] for element in scene.elements)
    for line, words in enumerate(
        [
            "The shelf is an array in the interpreter's own memory and its size is a number in a",
            "header file. It was 257 entries for years, and 3.15 raised it to 1025. Nothing in the",
            "language promises either number, which is why every trick built on it eventually breaks.",
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


gallery.add(_the_shelf())


gallery.add(
    figures.compare(
        "two-reasons-to-say-true",
        (
            "a = 257",
            [
                "b = 257",
                "a is b  ->  True",
                "one literal in co_consts",
                "the compiler deduplicated it",
            ],
        ),
        (
            "a = int('257')",
            [
                "b = int('257')",
                "a is b  ->  depends",
                "two objects made at runtime",
                "the shelf decides",
            ],
        ),
        title="The famous example measures the wrong thing",
        verdict="Both say True on 3.15 for completely unrelated reasons. Only the right hand one is about the cache.",
        verdict_tone="warning",
    )
)


gallery.add(
    figures.table(
        "what-gets-interned",
        ["string", "kept in the table", "why"],
        [
            ["''", "yes", "there is exactly one of these"],
            ["'a'", "yes", "single characters are prebuilt"],
            ["'append'", "yes", "looks like an identifier"],
            ["'_private'", "yes", "underscores and digits still count"],
            ["'hello world'", "no", "a space cannot appear in a name"],
            ["'a-b'", "no", "neither can a hyphen"],
        ],
        title="Which string literals end up sharing one object",
        caption="Attribute and variable names get compared constantly, so the ones shaped like names are pooled.",
    )
)


def _borrowed_or_not() -> Scene:
    """Why the old advice about subtracting one from getrefcount stopped working."""
    scene = Scene("borrowed-or-not")
    width = 330
    height = 84
    gap = 90

    scene.text("Why sys.getrefcount stopped being easy to read", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    columns = [
        (
            "a local variable",
            "LOAD_FAST_BORROW",
            "hands over the object without\ncounting it, since the frame is\nalready holding it",
            "adds nothing",
            "durable",
        ),
        (
            "a global variable",
            "LOAD_GLOBAL",
            "takes a real reference, because\nnothing guarantees the global\nsurvives the call",
            "adds one",
            "warning",
        ),
    ]
    for index, (heading, opcode, note, verdict, tone) in enumerate(columns):
        x = index * (width + gap)
        scene.text(heading, x, top, size=theme.BODY_SIZE)
        y = top + theme.BODY_SIZE * theme.LINE_HEIGHT + 10
        scene.box(
            opcode,
            x,
            y,
            width=width,
            height=56,
            tone="input",
            mono=True,
            size=theme.CAPTION_SIZE,
            align="center",
        )
        scene.text(note, x, y + 56 + 10, size=theme.CAPTION_SIZE, colour=theme.MUTED)
        scene.box(
            verdict,
            x,
            y + 56 + 10 + 4 * theme.CAPTION_SIZE * theme.LINE_HEIGHT,
            width=width,
            height=height - 20,
            tone=tone,
            align="center",
        )

    bottom = max(element.box[3] for element in scene.elements)
    for line, words in enumerate(
        [
            "Every tutorial written before 3.14 says the same thing: call sys.getrefcount, subtract one",
            "for the argument you just passed, and that is the answer. The correction is now a property",
            "of the instruction that loaded the object, so the same code gives a different number",
            "depending on whether the name was a local or a global.",
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


gallery.add(_borrowed_or_not())


gallery.add(
    figures.bars(
        "sizes",
        [
            ("None", 16),
            ("42", 28),
            ("'a'", 42),
            ("()", 48),
            ("[]", 56),
            ("{}", 64),
        ],
        unit="bytes",
        title="What an empty object costs",
        caption="Nothing here is holding anything. This is the header plus whatever the type needs to exist at all.",
    )
)


gallery.add(
    figures.bars(
        "sizes-grow",
        [
            ("[]", 56),
            ("[0] * 10", 136),
            ("[0] * 100", 856),
            ("[0] * 1000", 8056),
        ],
        unit="bytes",
        title="What a list costs as it fills up",
        caption="Eight bytes a slot, which is one pointer. The thousand integers are not counted here, because the list does not own them.",
    )
)


raise SystemExit(gallery.save())
