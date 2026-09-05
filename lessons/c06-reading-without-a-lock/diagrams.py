#!/usr/bin/env python
"""The diagrams for C06, four threads reading one container with no lock between them.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The order follows the lesson. What a subscript turns into on each of the two builds, the three
steps of an optimistic read, the pair of bars that is the whole point, which objects have a
count to fight over, what happens to storage that somebody might still be reading, and a
summary of where the three containers ended up.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("c06-reading-without-a-lock")

gallery.add(
    figures.compare(
        "two-ways-to-read-one-slot",
        (
            "with the GIL",
            [
                "hold the one big lock",
                "load the pointer",
                "add one to the count",
                "nothing else can be running",
            ],
        ),
        (
            "without the GIL",
            [
                "load the pointer",
                "try to add one to the count",
                "load the pointer again",
                "if it moved, start over",
            ],
        ),
        title="What data[500] turns into on each of the two builds",
        verdict="The right column takes no lock, which is why it can run on four threads at once.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.flow(
        "the-optimistic-read",
        [
            "load the pointer",
            "try to bump the count",
            "load the pointer again",
            "hand the object back",
        ],
        title="An optimistic read, which is _Py_TryIncrefCompare",
        tones=["input", "intermediate", "focus", "durable"],
        labels=["no lock taken", "may fail", "same as before"],
    )
)


gallery.add(
    figures.bars(
        "four-threads-on-one-list",
        [
            ["no GIL, small ints", 3.42],
            ["no GIL, objects", 0.34],
            ["GIL, small ints", 0.87],
            ["GIL, objects", 0.85],
        ],
        unit="times one thread",
        title="Four threads doing the same reads, from the two Tier 1 recordings",
        caption="Same code, same list length, same index. The only change is what the list holds.",
        tones=["durable", "warning", "quiet", "quiet"],
        width=620,
    )
)


gallery.add(
    figures.table(
        "who-has-a-count-and-who-does-not",
        ["the value", "with the GIL", "without the GIL"],
        [
            ["None", "immortal", "immortal"],
            ["the int 5", "immortal", "immortal"],
            ["the literal 1025", "ordinary count", "immortal"],
            ['int("1025")', "ordinary count", "ordinary count"],
            ["a long literal string", "ordinary count", "immortal"],
            ["object()", "ordinary count", "ordinary count"],
        ],
        title="Which objects have a reference count for threads to fight over",
        caption="The free threaded build immortalizes every constant it compiles, so reading one is free.",
        tones=["durable", "durable", "focus", "warning", "focus", "warning"],
    )
)


gallery.add(
    figures.flow(
        "where-the-old-storage-goes",
        [
            "a writer replaces the storage",
            "the old block joins a queue",
            "every thread reaches a check",
            "the block is handed back",
        ],
        title="Why a reader never sees memory that was freed underneath it",
        tones=["input", "intermediate", "focus", "durable"],
        labels=["not freed yet", "with a sequence number", "so nobody is looking"],
    )
)


gallery.add(
    figures.table(
        "what-each-container-does",
        ["container", "reading it", "when a stranger reads it"],
        [
            ["list", "optimistic, no lock", "marked shared, frees get delayed"],
            ["dict", "optimistic, no lock", "marked shared, frees get delayed"],
            ["set", "optimistic, no lock", "marked shared, frees get delayed"],
            ["writing any of them", "takes the object's lock", "readers keep going regardless"],
        ],
        title="Where the three containers ended up in 3.15",
        caption="Reads are lock free on all three. Writes are the part that takes a critical section.",
        tones=["focus", "focus", "focus", "warning"],
    )
)


raise SystemExit(gallery.save())
