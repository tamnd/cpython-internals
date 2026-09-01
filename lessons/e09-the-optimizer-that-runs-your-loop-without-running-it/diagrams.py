#!/usr/bin/env python
"""The diagrams for E09, the abstract interpreter that optimizes a trace.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one doing the most work is `what-it-can-know`, because every deletion in this lesson
comes from one of those rows. The rest are the measurements, drawn.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("e09-the-optimizer-that-runs-your-loop-without-running-it")

gallery.add(
    figures.flow(
        "what-the-optimizer-does-to-a-trace",
        [
            "a trace, recorded from one real trip",
            "walk it holding descriptions instead of values",
            "drop the checks that cannot fail",
            "drop the bookkeeping nobody reads",
            "a shorter trace, same behaviour",
        ],
        title="Two passes over a straight line",
        labels=[
            "nothing runs",
            "first pass",
            "second pass",
        ],
        tones=["input", "focus", "focus", "intermediate", "durable"],
    )
)


gallery.add(
    figures.table(
        "what-it-can-know",
        ["what it has been told", "what that rules out", "how it found out"],
        [
            ["nothing", "nothing", "a local it has not seen used"],
            ["it is an object", "it is not empty", "a null check went past"],
            ["its type has not changed", "a patched class", "a version guard went past"],
            ["its exact type", "every other type", "a type guard went past"],
            ["true or false", "the other one", "a truth test went past"],
            ["the object itself", "everything else", "a global that was baked in"],
            ["nothing is possible", "all of it", "two guards that contradict"],
        ],
        title="What the optimizer knows about one value, from least to most",
        caption="It can only ever move down this list, never back up.",
        tones=["quiet", "quiet", "focus", "focus", "focus", "durable", "warning"],
    )
)


gallery.add(
    figures.table(
        "guards-do-not-grow",
        ["additions in the loop", "micro operations", "guards"],
        [
            ["1", "31", "3"],
            ["2", "36", "3"],
            ["4", "46", "3"],
            ["6", "56", "3"],
        ],
        title="The same loop with more additions in it",
        caption="Each addition arrives carrying two guards. Only the first pair survives.",
        tones=["quiet", "quiet", "quiet", "focus"],
    )
)


gallery.add(
    figures.stack(
        "three-reads-one-check",
        [
            "_GUARD_TYPE_VERSION",
            "_LOAD_ATTR_INSTANCE_VALUE",
            "_LOAD_ATTR_INSTANCE_VALUE",
            "_LOAD_ATTR_INSTANCE_VALUE",
        ],
        title="total += p.x + p.x + p.x",
        note="Nothing between the reads can change what p is, so one check covers all three.",
    )
)


gallery.add(
    figures.table(
        "the-same-pop-three-ways",
        ["what comes out", "when it is chosen", "what it costs"],
        [
            ["_POP_TOP_NOP", "borrowed, or known to be immortal", "nothing at all"],
            ["_POP_TOP_INT", "known to be an int", "a decrement, no type question"],
            ["_POP_TOP", "nothing is known about it", "the general one"],
        ],
        title="Throwing away a value the optimizer knows about",
        caption="Same source, same stack effect, three different instructions.",
        tones=["durable", "focus", "quiet"],
    )
)


gallery.add(
    figures.flow(
        "baked-in-and-thrown-away",
        [
            "the loop calls a global function",
            "the function is copied into the trace",
            "you rebind the name",
            "the executor is dropped",
        ],
        title="What a constant costs when it stops being one",
        labels=[
            "no lookup left",
            "a watcher fires",
            "back to bytecode",
        ],
        tones=["input", "durable", "warning", "quiet"],
    )
)


raise SystemExit(gallery.save())
