#!/usr/bin/env python
"""The diagrams for E07, tier two and the traces a hot loop grows.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `where-a-hot-loop-goes`. Everything else is either the shape of
a trace or a measurement of what recording one bought.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("e07-the-loop-that-gets-its-own-program")

gallery.add(
    figures.flow(
        "where-a-hot-loop-goes",
        [
            "the loop runs as ordinary bytecode",
            "four thousand backward jumps later, start recording",
            "one real trip through, written down as micro operations",
            "optimize the straight line and hand it back as an executor",
        ],
        title="What happens to a loop that keeps going round",
        labels=[
            "a counter in the jump instruction",
            "whatever the program actually did",
            "guards where the branches were",
        ],
        tones=["input", "focus", "intermediate", "durable"],
    )
)


gallery.add(
    figures.compare(
        "one-instruction-at-a-time-or-a-whole-loop",
        (
            "tier one, one instruction",
            [
                "rewrites a single instruction",
                "knows nothing about its neighbours",
                "guards run on every execution",
                "warms up after two runs",
            ],
        ),
        (
            "tier two, a whole trace",
            [
                "replaces a run of instructions",
                "reasons across the whole line",
                "guards it can prove are deleted",
                "warms up after four thousand",
            ],
        ),
        title="Two optimizers with two different amounts to look at",
        verdict="The second one only pays off where the first one has run out of room.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.table(
        "what-is-in-a-trace",
        ["micro operation", "what it is doing"],
        [
            ["_START_EXECUTOR", "the entry point, once per trip"],
            ["_CHECK_VALIDITY", "has anything invalidated this trace"],
            ["_GUARD_NOS_INT", "bail out if the guess was wrong"],
            ["_BINARY_OP_ADD_INT", "the actual work"],
            ["_JUMP_TO_TOP", "go round again without leaving"],
            ["_EXIT_TRACE", "a cold tail, for when a guard fails"],
        ],
        title="Six of the thirty one operations in one small trace",
        caption="The first five are the loop. The last kind is the tails nobody runs.",
        tones=["quiet", "quiet", "warning", "focus", "focus", "quiet"],
    )
)


gallery.add(
    figures.bars(
        "guards-per-iteration",
        [
            ["what tier one runs", 6],
            ["what the trace keeps", 1],
        ],
        unit="type guards per turn",
        title="A loop body with three additions in it",
        caption="Once the first pair is checked, the rest are known to be ints too.",
        tones=["warning", "durable"],
        width=520,
    )
)


gallery.add(
    figures.stack(
        "the-shape-of-an-executor",
        [
            "_START_EXECUTOR",
            "the straight line, 21 operations",
            "_JUMP_TO_TOP",
            "8 cold tails",
        ],
        title="Thirty one operations, two halves",
        note="Everything below the jump is only reached when a guard fails.",
    )
)


gallery.add(
    figures.bars(
        "what-the-jit-is-worth",
        [
            ["arithmetic loop, jit off", 18.7],
            ["arithmetic loop, jit on", 12.2],
            ["loop with a call, jit off", 22.1],
            ["loop with a call, jit on", 16.9],
        ],
        unit="ns per iteration",
        title="The same two loops, run twice",
        caption="One machine, one release. On 3.14 the same measurement comes out the other way.",
        tones=["quiet", "durable", "quiet", "durable"],
        width=520,
    )
)


raise SystemExit(gallery.save())
