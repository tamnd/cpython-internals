#!/usr/bin/env python
"""The diagrams for M06, the two reference counts a free threaded object carries.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

`the-update-that-went-missing` is the one everything else answers. The other five are the three
answers CPython gives to that problem, the shape of the header they need, and the bill.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("m06-two-counts-one-object")

gallery.add(
    figures.table(
        "the-update-that-went-missing",
        ["step", "thread A", "thread B", "the count in memory"],
        [
            ["1", "reads 5", "", "5"],
            ["2", "", "reads 5", "5"],
            ["3", "adds one, gets 6", "", "5"],
            ["4", "", "adds one, gets 6", "5"],
            ["5", "writes 6", "", "6"],
            ["6", "", "writes 6", "6"],
        ],
        title="Two threads take a reference, and the object loses one",
        caption="Two holders, and the count says one. The object gets freed while somebody is using it.",
        tones=["quiet", "quiet", "quiet", "quiet", "warning", "warning"],
    )
)


gallery.add(
    figures.compare(
        "two-headers",
        (
            "with the GIL",
            [
                "ob_refcnt, 8 bytes",
                "ob_type, 8 bytes",
                "16 bytes in total",
                "one number, one writer",
            ],
        ),
        (
            "without it",
            [
                "ob_tid, who owns it",
                "flags, a lock, gc bits",
                "ob_ref_local, 4 bytes",
                "ob_ref_shared, 8 bytes",
                "ob_type, 8 bytes",
                "32 bytes in total",
            ],
        ),
        title="The same object header, built two ways",
        verdict="The count did not get bigger. It got split, and gained a name for its owner.",
    )
)


gallery.add(
    figures.table(
        "three-answers",
        ["the answer", "which objects", "what a reference costs"],
        [
            ["never count it", "None, small ints, types", "nothing at all"],
            ["stop counting it", "functions, classes, modules", "nothing until the collector runs"],
            ["count it locally", "everything else, on its own thread", "a plain add, no atomic"],
            ["count it shared", "everything else, from elsewhere", "one atomic add"],
        ],
        title="Four prices, and most references pay one of the first three",
        caption="Only the last row is expensive, and it is the row the interpreter tries hardest to avoid.",
        tones=["durable", "durable", "focus", "warning"],
    )
)


gallery.add(
    figures.compare(
        "where-the-reference-goes",
        (
            "the thread that made it",
            [
                "ob_tid matches, so",
                "add one to ob_ref_local",
                "a plain 32 bit add",
                "no atomic, no lock",
            ],
        ),
        (
            "any other thread",
            [
                "ob_tid does not match",
                "add four to ob_ref_shared",
                "an atomic add",
                "the count is the sum of both",
            ],
        ),
        title="One object, and which half of it your reference lands in",
        verdict="Most objects are made and dropped on one thread, so most references take the left path.",
    )
)


gallery.add(
    figures.table(
        "inside-the-shared-count",
        ["bits", "what is in them", "why"],
        [
            ["2 and up", "the shared reference count", "shifted left, so the flags fit below"],
            ["bit 1 and 0 as 00", "nothing has happened yet", "the state an object starts in"],
            ["bit 0", "something took a weak reference", "the collector needs to know"],
            ["bit 1", "a decref is queued for the owner", "the owner will do it later"],
            ["both bits", "the two counts have been merged", "ob_tid is now zero"],
        ],
        title="ob_ref_shared is not just a number",
        caption="The bottom two bits are flags, which is why the count is stored shifted up by two.",
        tones=["focus", "quiet", "input", "input", "durable"],
    )
)


gallery.add(
    figures.table(
        "what-the-header-costs",
        ["object", "with the GIL", "without it", "difference"],
        [
            ["object()", "16 bytes", "32 bytes", "16 more"],
            ["a one character string", "42 bytes", "58 bytes", "16 more"],
            ["an empty tuple", "48 bytes", "48 bytes", "the same"],
            ["an empty list", "56 bytes", "56 bytes", "the same"],
            ["an empty dict", "64 bytes", "64 bytes", "the same"],
        ],
        title="What the wider header actually costs you",
        caption="A type the collector can collect pays nothing, because this build dropped the separate collector header.",
        tones=["warning", "warning", "quiet", "quiet", "quiet"],
    )
)


raise SystemExit(gallery.save())
