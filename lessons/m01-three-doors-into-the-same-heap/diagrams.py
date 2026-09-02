#!/usr/bin/env python
"""The diagrams for M01, the three allocator domains and the debug hooks that make them visible.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

`what-the-fences-look-like` is the one doing the work. Everything else in the lesson is a
byte read out of that layout, so it is worth drawing the layout once and properly.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("m01-three-doors-into-the-same-heap")

gallery.add(
    figures.table(
        "three-doors",
        ["the door", "what you call", "what goes through it", "byte"],
        [
            ["raw", "PyMem_RawMalloc", "work done before there is an interpreter", "r"],
            ["mem", "PyMem_Malloc", "buffers that belong to an object", "m"],
            ["obj", "PyObject_Malloc", "the objects themselves", "o"],
        ],
        title="Three ways to ask for memory, and they are not interchangeable",
        caption="Same heap underneath. Different rules about locks, and different bookkeeping.",
        tones=["quiet", "focus", "focus"],
    )
)


gallery.add(
    figures.spans(
        "what-the-fences-look-like",
        "SSSSSSSS IFFFFFFF ..your bytes.. FFFFFFFF",
        [
            (0, 8, "the size you asked for"),
            (9, 10, "which door"),
            (10, 17, "fence, 7 bytes"),
            (18, 32, "the part you get"),
            (33, 41, "fence, 8 bytes"),
        ],
        title="What a block looks like once the debug hooks are on",
        caption="Your pointer is the arrow in the middle. Everything else is behind your back.",
    )
)


gallery.add(
    figures.table(
        "three-bytes-worth-knowing",
        ["byte", "means", "where you find it"],
        [
            ["0xCD", "fresh, nobody has written here yet", "inside a block you just got"],
            ["0xDD", "dead, this was handed back", "inside a block after you free it"],
            ["0xFD", "not yours, do not touch", "the fences at both ends"],
        ],
        title="The three fillers, and they were picked to be obvious",
        caption="None of them is a plausible number, a plausible pointer or a letter.",
        tones=["focus", "durable", "warning"],
    )
)


gallery.add(
    figures.flow(
        "one-object-two-blocks",
        [
            "a list in your program",
            "one block through the obj door",
            "a pointer sitting inside it",
            "one block through the mem door",
        ],
        title="Why sys.getsizeof is bigger than the block the object lives in",
        labels=[
            "56 bytes",
            "at offset 24",
            "as many as it needs",
        ],
        tones=["input", "focus", "intermediate", "durable"],
    )
)


gallery.add(
    figures.compare(
        "where-the-object-door-stops",
        (
            "up to 512 bytes",
            [
                "served from memory we hold",
                "comes out of a pool",
                "needs an arena to be there",
                "no system call at all",
            ],
        ),
        (
            "513 bytes and up",
            [
                "passed to the raw door",
                "comes from the system",
                "no arena involved",
                "the system decides",
            ],
        ),
        title="The obj door does not serve every request itself",
        verdict="512 was picked so that a new dictionary always lands on the left hand side.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.table(
        "the-bottom-layer-comes-out",
        ["PYTHONMALLOC", "what serves a small request", "blocks", "arenas"],
        [
            ["default", "CPython's own allocator", "about 30000", "a few"],
            ["pymalloc", "the same thing, asked for", "about 30000", "a few"],
            ["malloc", "the system, every time", "0", "none at all"],
            ["mimalloc", "a different allocator entirely", "about 31000", "none at all"],
        ],
        title="One environment variable and the whole bottom layer changes",
        caption="Nothing above it notices. That is the point of having the layer.",
        tones=["quiet", "quiet", "focus", "durable"],
    )
)


raise SystemExit(gallery.save())
