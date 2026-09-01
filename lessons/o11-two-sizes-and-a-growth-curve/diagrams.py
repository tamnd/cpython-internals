#!/usr/bin/env python
"""The diagrams for O11, lists and tuples.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `two-objects-not-one`. A list is a small fixed object plus a
separately allocated array, and almost everything odd about lists follows from that split.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("o11-two-sizes-and-a-growth-curve")

gallery.add(
    figures.compare(
        "two-objects-not-one",
        (
            "a list",
            [
                "a fixed 56 byte object",
                "holding a pointer to an array",
                "two sizes: used and allocated",
                "the array is resized as you append",
            ],
        ),
        (
            "a tuple",
            [
                "one object, one allocation",
                "the items follow the header",
                "one size, because it never changes",
                "and room for a cached hash",
            ],
        ),
        title="Where the items actually are",
        verdict="Everything else in this lesson follows from that one difference.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.stack(
        "what-a-list-holds",
        [
            "the object header, from O01",
            "ob_size, how many items you can see",
            "ob_item, a pointer to somewhere else",
            "allocated, how many slots that somewhere else has",
        ],
        title="A list object, top to bottom",
        note="Fifty six bytes, whatever the list contains. The items are not in here.",
    )
)


gallery.add(
    figures.bars(
        "the-growth-curve",
        [
            ("1 item", 4),
            ("5 items", 8),
            ("9 items", 16),
            ("17 items", 24),
            ("41 items", 52),
            ("77 items", 92),
        ],
        unit="slots allocated",
        title="What append actually asks for",
        caption="newsize + newsize/8 + 6, rounded down to a multiple of 4.",
        tones=["quiet", "quiet", "focus", "focus", "focus", "warning"],
        width=460,
    )
)


gallery.add(
    figures.flow(
        "what-append-does",
        [
            "is there a spare slot already",
            "if yes, write it and bump ob_size",
            "if no, work out a bigger size",
            "realloc the array and copy nothing",
        ],
        title="One append, start to finish",
        labels=[
            "allocated > ob_size",
            "no allocation at all, which is the common case",
            "about 12 percent more, plus six",
        ],
        tones=["input", "durable", "focus", "warning"],
    )
)


gallery.add(
    figures.table(
        "how-you-built-it-matters",
        ["how the list was made", "slots for five items"],
        [
            ["[a, b, c, d, e]", "5"],
            ["[1, 2, 3, 4, 5]", "6"],
            ["list(range(5))", "6"],
            ["five appends to []", "8"],
            ["[n for n in range(5)]", "8"],
        ],
        title="Five lists of five items, three different sizes",
        caption="A known length is allocated to fit. Appending guesses ahead.",
        tones=["focus", "quiet", "quiet", "warning", "warning"],
    )
)


gallery.add(
    figures.flow(
        "why-a-tuple-can-cache-its-hash",
        [
            "a tuple cannot change after it is made",
            "so its hash cannot change either",
            "so it is worth storing in the object",
            "which is why tuples can be dict keys and lists cannot",
        ],
        title="One property, three consequences",
        labels=[
            "no append, no assignment, no sort",
            "computed once, on the first ask",
            "the field starts at -1",
        ],
        tones=["input", "focus", "durable", "durable"],
    )
)


raise SystemExit(gallery.save())
