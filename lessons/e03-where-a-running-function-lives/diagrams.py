#!/usr/bin/env python
"""The diagrams for E03, frames and the two stacks.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `two-stacks`. Almost everything surprising about recursion in
Python comes from there being two stacks with two different limits.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("e03-where-a-running-function-lives")

gallery.add(
    figures.compare(
        "two-stacks",
        (
            "the data stack",
            [
                "holds one frame per Python call",
                "chunks of 16 KiB, grown as needed",
                "limited by a number you can set",
                "a Python call adds nothing else",
            ],
        ),
        (
            "the C stack",
            [
                "holds one frame per C call",
                "fixed when the thread starts",
                "limited by the operating system",
                "a Python call through C costs a lot",
            ],
        ),
        title="Two stacks, and only one of them is the machine's",
        verdict="Deep recursion in Python is fine. The same depth through sorted is not.",
        verdict_tone="warning",
    )
)


gallery.add(
    figures.stack(
        "what-is-in-a-frame",
        [
            "who called me, and where to go back to",
            "which code object I am running",
            "where in that code I am, to the byte",
            "one slot per local variable",
            "the value stack, sized at compile time",
        ],
        title="Everything a running function has to remember",
        note="The last two are one flat array. A local is an index into it, which is why LOAD_FAST takes a number.",
    )
)


gallery.add(
    figures.flow(
        "where-a-frame-comes-from",
        [
            "a Python function is called",
            "the interpreter takes the next slots off the data stack",
            "it fills them in and starts running",
            "on return the slots are handed straight back",
        ],
        title="Making a frame is moving a pointer",
        labels=[
            "no C function is entered",
            "a bump, or a new 16 KiB chunk",
            "no allocation, no object created",
        ],
        tones=["input", "focus", "focus", "durable"],
    )
)


gallery.add(
    figures.table(
        "one-object-or-two",
        ["what it is", "when it exists", "what it costs"],
        [
            ["the interpreter frame", "for every call, always", "slots on the data stack"],
            ["the frame object", "only when somebody asks", "a real Python object"],
        ],
        title="Two things both called a frame",
        caption="sys._getframe is what asks. So is a traceback, and so is a debugger.",
        tones=["quiet", "focus"],
    )
)


gallery.add(
    figures.bars(
        "what-a-level-of-recursion-costs",
        [
            ["Python calling Python", 0],
            ["through repr", 914],
            ["through sorted", 5667],
        ],
        unit="bytes of C stack",
        title="The same recursion, three routes",
        caption="Measured on one machine, so your numbers will differ. The shape will not.",
        tones=["durable", "warning", "warning"],
        width=520,
    )
)


gallery.add(
    figures.table(
        "two-limits-two-messages",
        ["what ran out", "the message", "what changes it"],
        [
            ["the counter", "maximum recursion depth exceeded", "sys.setrecursionlimit"],
            ["the C stack", "Stack overflow (used 1004 kB)", "the thread's stack size"],
        ],
        title="Two different RecursionErrors",
        caption="Raising the limit moves the first one and does nothing at all to the second.",
        tones=["quiet", "warning"],
    )
)


raise SystemExit(gallery.save())
