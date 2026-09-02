#!/usr/bin/env python
"""The diagrams for M03, the second allocator that is already in your Python.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

`where-the-bookkeeping-goes` is the one that explains the rest. Every measurable difference
between the two allocators comes from that single choice about where the per page record
lives, and so does the reason one of them can be split per thread and the other cannot.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("m03-a-heap-for-every-thread")

gallery.add(
    figures.compare(
        "two-reports",
        (
            "the usual allocator",
            [
                "512 byte threshold",
                "32 size classes",
                "1 MiB arenas",
                "16 KiB pools inside them",
            ],
        ),
        (
            "mimalloc",
            [
                "16384 byte threshold",
                "73 size classes",
                "32 MiB segments",
                "64 KiB pages inside them",
            ],
        ),
        title="The same report, printed by two different allocators",
        verdict="Both are compiled into your Python right now. One variable picks which runs.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.table(
        "where-the-bookkeeping-goes",
        ["the question", "the usual allocator", "mimalloc"],
        [
            ["where is the page record", "inside the pool", "in the segment header"],
            ["where does block one start", "48 bytes in", "at the page boundary"],
            ["is a block size aligned", "never", "always"],
            ["who owns the free list", "the interpreter", "one thread"],
            ["what a free costs", "a list push", "a list push, usually"],
        ],
        title="One design choice, and everything else follows from it",
        caption="Keeping the record out of the page is what lets a page belong to one thread.",
        tones=["focus", "focus", "focus", "durable", "quiet"],
    )
)


gallery.add(
    figures.stack(
        "the-fences-sit-on-top",
        [
            "the debug hooks, size and door byte and fences",
            "the allocator you picked, obmalloc or mimalloc",
            "the operating system, mmap or malloc",
        ],
        title="Three layers, and only the middle one changes",
        note="This is why the same reading code from M01 works over either allocator.",
    )
)


gallery.add(
    figures.table(
        "four-heaps-per-thread",
        ["the heap", "what goes in it", "why it is on its own"],
        [
            ["mem", "PyMem_Malloc buffers", "these are not objects"],
            ["object", "objects the collector ignores", "no need to walk them"],
            ["gc", "collected objects", "the collector walks this one"],
            ["gc_pre", "collected, with a pre header", "same walk, different offset"],
        ],
        title="Every thread gets four mimalloc heaps, not one",
        caption="The split is not about speed. It is so the collector knows what it is looking at.",
        tones=["quiet", "quiet", "focus", "focus"],
    )
)


gallery.add(
    figures.compare(
        "how-the-collector-finds-things",
        (
            "with the GIL",
            [
                "objects are in a linked list",
                "two words per object for it",
                "walk the list",
                "one list, one thread at a time",
            ],
        ),
        (
            "free threaded",
            [
                "no list at all",
                "those two words go away",
                "ask the heap to walk itself",
                "each thread walks its own",
            ],
        ),
        title="How the cycle collector finds every object",
        verdict="Being able to walk the heap is why the free threaded build can drop the list.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.nest(
        "one-set-each",
        (
            "one interpreter",
            [
                (
                    "thread one",
                    ["mem", "object", "gc", "gc with pre header"],
                ),
                ("thread two", ["four more of its own"]),
                "a shared pool for the pages of threads that exited",
            ],
        ),
        title="What the free threaded build actually keeps",
        caption="Nothing is shared on the fast path, which is the entire point.",
    )
)


raise SystemExit(gallery.save())
