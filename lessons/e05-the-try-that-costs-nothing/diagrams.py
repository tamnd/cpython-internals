#!/usr/bin/env python
"""The diagrams for E05, zero cost exceptions and the table behind them.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `two-ways-to-mark-a-try`. Everything else is either the shape
of the table that replaced the instructions, or a measurement of what the trade bought.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("e05-the-try-that-costs-nothing")

gallery.add(
    figures.compare(
        "two-ways-to-mark-a-try",
        (
            "before 3.11",
            [
                "an instruction on the way in",
                "an instruction on the way out",
                "a stack of active handlers",
                "paid on every pass, raise or not",
            ],
        ),
        (
            "since 3.11",
            [
                "no instruction at all",
                "no instruction at all",
                "a table beside the bytecode",
                "read only once something raises",
            ],
        ),
        title="The same try block, marked two different ways",
        verdict="Raising got a bit slower. Not raising got free.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.table(
        "what-one-entry-says",
        ["field", "what it means"],
        [
            ["start", "first instruction this handler covers"],
            ["end", "first instruction after it"],
            ["target", "where to jump when something raises"],
            ["depth", "how tall the value stack should be there"],
            ["lasti", "whether to push where the raise happened"],
        ],
        title="One row of the exception table",
        caption="Five numbers per guarded range, and no instruction anywhere in the bytecode.",
        tones=["quiet", "quiet", "focus", "focus", "quiet"],
    )
)


gallery.add(
    figures.table(
        "four-bytes-one-entry",
        ["byte", "bits", "what it holds"],
        [
            ["131", "1 0 000011", "start of an entry, code unit 3"],
            ["8", "0 0 001000", "eight code units long"],
            ["12", "0 0 001100", "handler at code unit 12"],
            ["0", "0 0 000000", "stack depth 0, do not push lasti"],
        ],
        title="A whole handler in four bytes",
        caption="The top bit marks where an entry starts. The next one says another byte follows.",
        tones=["focus", "quiet", "quiet", "quiet"],
    )
)


gallery.add(
    figures.flow(
        "what-happens-when-something-raises",
        [
            "an instruction raises",
            "look up this offset in the table",
            "found one: trim the stack and jump",
            "found none: add the frame to the traceback and try the caller",
        ],
        title="What the interpreter does with an exception",
        labels=[
            "a binary search over a few dozen bytes",
            "the depth came from the table",
            "and if the top is reached, the program stops",
        ],
        tones=["input", "focus", "durable", "warning"],
    )
)


gallery.add(
    figures.bars(
        "what-not-raising-costs",
        [
            ["nothing guarded", 13.3],
            ["wrapped in a try", 13.3],
            ["checking a returned value", 16.1],
        ],
        unit="ns per iteration",
        title="A loop that never fails, three ways",
        caption="Measured on one machine, so your numbers will differ. The order will not.",
        tones=["durable", "durable", "warning"],
        width=520,
    )
)


gallery.add(
    figures.bars(
        "what-raising-costs",
        [
            ["1 frame", 197],
            ["5 frames", 394],
            ["20 frames", 1100],
            ["50 frames", 2715],
        ],
        unit="ns to raise and catch",
        title="What the exception pays on the way up",
        caption="About fifty nanoseconds per frame, and most of that is building the traceback.",
        tones=["quiet", "quiet", "warning", "warning"],
        width=520,
    )
)


raise SystemExit(gallery.save())
