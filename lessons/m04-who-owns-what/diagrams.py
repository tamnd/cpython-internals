#!/usr/bin/env python
"""The diagrams for M04, the ownership protocol behind the reference count.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

`owned-or-borrowed` is the one to look at first. Every other picture here is a consequence of
that single distinction, including the two objects at the end whose counts never reach zero.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("m04-who-owns-what")

gallery.add(
    figures.table(
        "the-extra-one",
        ["how you ask", "what it says", "why"],
        [
            ["sys.getrefcount(thing)", "2", "the argument is a reference too"],
            ["reading the memory", "1", "nothing was passed anywhere"],
            ["what you meant to ask", "1", "the name is the only holder"],
        ],
        title="Two ways to read the same number, one apart",
        caption="Looking at an object in Python almost always means holding it for a moment.",
        tones=["warning", "focus", "focus"],
    )
)


gallery.add(
    figures.table(
        "what-takes-a-reference",
        ["what you did", "the count", "when it goes back down"],
        [
            ["bound a second name", "up one", "the name is rebound or deleted"],
            ["appended to a list", "up one", "the item is removed or the list dies"],
            ["stored as a dict value", "up one", "the key is replaced or removed"],
            ["put in a tuple", "up one", "the tuple dies, since it cannot change"],
            ["set as an attribute", "up one", "the attribute is replaced or the owner dies"],
            ["captured by a closure", "up one", "the function object dies"],
            ["used as a default value", "up one", "the function object dies"],
            ["passed to a function", "up one", "the call returns"],
        ],
        title="Everything that holds an object holds exactly one reference",
        caption="No holder is special and none of them counts for more than one.",
        tones=["quiet", "focus", "focus", "durable", "quiet", "quiet", "quiet", "warning"],
    )
)


gallery.add(
    figures.compare(
        "owned-or-borrowed",
        (
            "an owned reference",
            [
                "the count went up for you",
                "you must put it back down",
                "safe to keep",
                "LOAD_FAST, PyList_GetItemRef",
            ],
        ),
        (
            "a borrowed reference",
            [
                "the count did not move",
                "you owe nothing",
                "valid only while the owner is",
                "LOAD_FAST_BORROW, PyList_GetItem",
            ],
        ),
        title="Two kinds of pointer at the same object",
        verdict="Getting this wrong in either direction is a leak or a crash.",
        verdict_tone="warning",
    )
)


gallery.add(
    figures.flow(
        "zero-means-now",
        [
            "the last holder lets go",
            "the count reaches zero",
            "tp_dealloc runs",
            "everything it held drops by one",
            "some of those reach zero too",
        ],
        title="What happens the instant a count runs out",
        tones=["quiet", "focus", "focus", "input", "warning"],
        labels=("minus one", "immediately", "your __del__ here", "and again"),
    )
)


gallery.add(
    figures.table(
        "what-the-del-sees",
        ["what you did", "what __del__ finds when it runs"],
        [
            ["box[0] = something else", "the list, already holding the new value"],
            ["table['k'] = something else", "the dict, already holding the new value"],
            ["box.clear()", "an empty list"],
            ["table.clear()", "an empty dict"],
        ],
        title="Your code runs in the middle of somebody else's update",
        caption="Containers finish rearranging themselves before they drop anything.",
        tones=["focus", "focus", "durable", "durable"],
    )
)


gallery.add(
    figures.compare(
        "stuck-at-one",
        (
            "a chain",
            [
                "a holds b, b holds c",
                "drop a and all three go",
                "counts reach zero in order",
                "nothing left behind",
            ],
        ),
        (
            "a loop",
            [
                "a holds b, b holds a",
                "drop both names",
                "both counts stop at one",
                "unreachable and still alive",
            ],
        ),
        title="Where counting on its own runs out",
        verdict="Two objects nobody can reach, holding each other up. This is what M07 is for.",
        verdict_tone="warning",
    )
)


raise SystemExit(gallery.save())
