#!/usr/bin/env python
"""The diagrams for E08, monitoring events and the instructions they swap in.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `what-watching-costs`, because the whole design of
`sys.monitoring` falls out of those three numbers. The rest is either the shape of the
mechanism or a table of what is where.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("e08-watching-without-slowing-it-down")

gallery.add(
    figures.flow(
        "switching-one-event-on",
        [
            "claim one of the six tool ids",
            "register a callback for the event you want",
            "ask for that event on one code object",
            "its instructions are rewritten where they sit",
        ],
        title="Four calls, and the bytecode is different afterwards",
        labels=[
            "nobody else can take it",
            "one function per event",
            "not the whole program",
        ],
        tones=["input", "input", "focus", "durable"],
    )
)


gallery.add(
    figures.table(
        "the-same-function-before-and-after",
        ["offset", "before", "with LINE events on"],
        [
            ["0", "RESUME", "RESUME"],
            ["4", "LOAD_SMALL_INT", "INSTRUMENTED_LINE"],
            ["6", "STORE_FAST", "STORE_FAST"],
            ["8", "LOAD_GLOBAL", "INSTRUMENTED_LINE"],
            ["32", "FOR_ITER", "INSTRUMENTED_LINE"],
        ],
        title="One function, disassembled twice",
        caption="Nothing recompiled. The bytes in the code object were written over.",
        tones=["quiet", "focus", "quiet", "focus", "focus"],
    )
)


gallery.add(
    figures.bars(
        "what-watching-costs",
        [
            ["nobody watching", 14.8],
            ["callback counts the line", 76.0],
            ["callback returns DISABLE", 15.0],
        ],
        unit="ns per turn",
        title="The same loop, watched three ways",
        caption="The third one is still being watched. It just is not being told any more.",
        tones=["quiet", "warning", "durable"],
        width=520,
    )
)


gallery.add(
    figures.table(
        "eight-slots-six-yours",
        ["id", "who has it", "how you get it"],
        [
            ["0", "debuggers, by convention", "DEBUGGER_ID"],
            ["1", "coverage tools, by convention", "COVERAGE_ID"],
            ["2", "profilers, by convention", "PROFILER_ID"],
            ["3, 4", "nobody, take one", "the number itself"],
            ["5", "optimizers, by convention", "OPTIMIZER_ID"],
            ["6, 7", "sys.setprofile and sys.settrace", "not available to you"],
        ],
        title="The eight tool ids and who is expected to use them",
        caption="The names are only a convention. The interpreter checks the number, not the name.",
        tones=["focus", "focus", "focus", "quiet", "quiet", "warning"],
    )
)


gallery.add(
    figures.compare(
        "a-callback-that-stays-or-goes",
        (
            "returns None",
            [
                "called on every execution",
                "2003 calls for a loop of 1000",
                "the loop stays instrumented",
                "what a debugger wants",
            ],
        ),
        (
            "returns DISABLE",
            [
                "called once per location",
                "5 calls for the same loop",
                "that instruction is put back",
                "what a coverage tool wants",
            ],
        ),
        title="The same callback, one line different",
        verdict="Coverage is cheap because it only needs to be told once.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.table(
        "two-tools-one-function",
        ["tool", "asked for", "what it heard"],
        [
            ["debugger, id 0", "LINE", "lines 2, 3, 6 then 2, 5, 6"],
            ["coverage, id 1", "BRANCH_LEFT and BRANCH_RIGHT", "left at 12, then right at 12"],
        ],
        title="Two tools watching the same function at the same time",
        caption="Neither one sees the other's events, and neither had to share a hook.",
        tones=["focus", "focus"],
    )
)


raise SystemExit(gallery.save())
