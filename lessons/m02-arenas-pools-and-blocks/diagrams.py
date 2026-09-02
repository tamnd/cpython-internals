#!/usr/bin/env python
"""The diagrams for M02, the three nested boxes CPython's own allocator is made of.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

`inside-one-pool` is the one carrying the lesson. Two numbers, 16384 and 48, explain every
total the allocator prints about itself, and that picture is where both of them live.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("m02-arenas-pools-and-blocks")

gallery.add(
    figures.nest(
        "three-boxes",
        (
            "one arena, 1048576 bytes from the system",
            [
                (
                    "one pool, 16384 bytes",
                    [
                        "a 48 byte header",
                        "blocks, all of them one size",
                    ],
                ),
                "63 more pools, each with its own size",
            ],
        ),
        title="What the chunk from the last lesson is made of",
        caption="Three boxes, and every number in this picture is readable from Python.",
    )
)


gallery.add(
    figures.spans(
        "inside-one-pool",
        "HHH bbbb bbbb bbbb ... bbbb ~~",
        [
            (0, 3, "48 byte header"),
            (4, 8, "block 1"),
            (9, 13, "block 2"),
            (23, 27, "the last one"),
            (28, 30, "left over"),
        ],
        title="One pool, and one block size for all of it",
        caption="The header is why a block never starts at the top of a pool.",
    )
)


gallery.add(
    figures.table(
        "rounded-up-to-a-class",
        ["you ask for", "you get", "class", "why"],
        [
            ["1 byte", "16 bytes", "0", "there is nothing smaller"],
            ["17 bytes", "32 bytes", "1", "up to the next multiple of 16"],
            ["100 bytes", "112 bytes", "6", "same rule"],
            ["512 bytes", "512 bytes", "31", "the last class there is"],
            ["513 bytes", "513 bytes", "none", "handed to the system instead"],
        ],
        title="Every request is rounded up to one of 32 sizes",
        caption="The gap between what you asked for and what you got is never given back.",
        tones=["quiet", "focus", "focus", "quiet", "warning"],
    )
)


gallery.add(
    figures.bars(
        "how-many-fit-in-a-pool",
        [
            ("16 byte blocks", 1021),
            ("32 byte blocks", 510),
            ("64 byte blocks", 255),
            ("128 byte blocks", 127),
            ("256 byte blocks", 63),
            ("512 byte blocks", 31),
        ],
        unit="per pool",
        title="How many blocks a 16384 byte pool holds",
        caption="Every one of these is 16384 minus 48, divided by the block size, rounded down.",
        tones=["focus", "focus", "quiet", "quiet", "quiet", "durable"],
    )
)


gallery.add(
    figures.compare(
        "why-it-does-not-come-back",
        (
            "every pool in it is free",
            [
                "the arena goes back",
                "the count drops",
                "reclaimed goes up",
                "the process gets smaller",
            ],
        ),
        (
            "one block is still alive",
            [
                "the arena stays",
                "so do its 63 other pools",
                "1 MiB held for 64 bytes",
                "nothing you can do about it",
            ],
        ),
        title="When an arena is handed back to the system",
        verdict="All or nothing. One surviving block anywhere in it keeps the whole arena.",
        verdict_tone="warning",
    )
)


gallery.add(
    figures.table(
        "every-total-adds-up",
        ["the line it prints", "how to get the same number yourself"],
        [
            ["bytes in allocated blocks", "blocks in use times the block size"],
            ["bytes in available blocks", "avail blocks times the block size"],
            ["bytes lost to pool headers", "pools times 48"],
            ["bytes lost to quantization", "pools times what is left at the end"],
            ["arenas allocated current", "all the pools, divided by 64"],
        ],
        title="The summary block is the table above it, added up",
        caption="Two constants and five sums. Nothing else goes into any of these.",
        tones=["focus", "focus", "durable", "durable", "quiet"],
    )
)


raise SystemExit(gallery.save())
