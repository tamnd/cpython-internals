#!/usr/bin/env python
"""The diagrams for O12, the free lists.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `where-a-dropped-object-goes`. Freeing an object is not one
decision but three, and the free list is the branch most people never hear about.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("o12-the-objects-that-come-back")

gallery.add(
    figures.flow(
        "where-a-dropped-object-goes",
        [
            "the last reference goes away",
            "is this exactly the base type",
            "is the stash for that type under its cap",
            "push it on the stash instead of freeing it",
        ],
        title="What happens when you drop a float",
        labels=[
            "the count reaches zero",
            "a subclass takes the other branch",
            "a hundred for floats, eighty for lists",
        ],
        tones=["input", "focus", "focus", "durable"],
    )
)


gallery.add(
    figures.stack(
        "the-chain-lives-in-the-dead-objects",
        [
            "the head pointer, in the interpreter",
            "dead object, first word points at the next",
            "dead object, first word points at the next",
            "dead object, first word is null",
        ],
        title="A free list is a chain with no container",
        note="The link overwrites the reference count field, which a dead object has no use for.",
    )
)


gallery.add(
    figures.compare(
        "not-the-same-as-the-allocator",
        (
            "the allocator",
            [
                "hands out blocks by size",
                "any type can have the block",
                "56 bytes is 56 bytes",
                "survives a collection",
            ],
        ),
        (
            "a free list",
            [
                "hands out objects by type",
                "only that exact type",
                "a list slot never becomes a tuple",
                "emptied by the oldest generation",
            ],
        ),
        title="Two layers of reuse, and how to tell them apart",
        verdict="Drop a list and ask for a tuple of the same size. You get different memory.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.bars(
        "how-many-each-type-keeps",
        [
            ("slices", 1),
            ("ranges", 6),
            ("iterators", 10),
            ("lists and dicts", 80),
            ("floats and ints", 100),
            ("contexts", 255),
        ],
        unit="objects kept per type",
        title="The caps, straight from the header",
        caption="Small tuples get one list of 2000 for every size from 1 to 20.",
        tones=["quiet", "quiet", "quiet", "focus", "focus", "warning"],
        width=460,
    )
)


gallery.add(
    figures.table(
        "one-list-per-tuple-size",
        ["tuple size", "has its own free list", "what happens when you drop one"],
        [
            ["1 to 20", "yes, one each", "kept, up to 2000 of that size"],
            ["21", "no", "handed back to the allocator"],
            ["50", "no", "handed back to the allocator"],
            ["0", "no, and it never dies", "there is only one empty tuple"],
        ],
        title="Twenty lists, one per size, and nothing above that",
        caption="You can read the boundary out of the interpreter without opening the header.",
        tones=["focus", "warning", "warning", "quiet"],
    )
)


gallery.add(
    figures.flow(
        "who-empties-them",
        [
            "gc.collect(0) walks the youngest generation",
            "gc.collect(1) walks the middle one",
            "gc.collect(2) walks the oldest",
            "and only that last one empties every free list",
        ],
        title="Three generations, one that clears the stashes",
        labels=[
            "free lists untouched",
            "free lists untouched",
            "this is what a bare gc.collect() does",
        ],
        tones=["quiet", "quiet", "focus", "warning"],
    )
)


raise SystemExit(gallery.save())
