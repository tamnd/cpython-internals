#!/usr/bin/env python
"""The diagrams for M07, the generational collector and what makes it run.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

`nobody-calls-it` is the spine. The rest fill in the three lists the collector keeps, how an
object moves between them, the brake on full collections, and the work the collector removes
from its own future.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("m07-the-collector-nobody-calls")

gallery.add(
    figures.flow(
        "nobody-calls-it",
        [
            "you make a list",
            "a counter goes up",
            "it passes 2000",
            "a bit gets set",
            "the collector runs",
        ],
        title="Nothing in your code asks for this",
        tones=["input", "quiet", "warning", "intermediate", "focus"],
        labels=["tracked", "check", "schedule", "next instruction"],
    )
)


gallery.add(
    figures.table(
        "what-the-counter-counts",
        ["when", "what happens to the counter", "where"],
        [
            ["a tracked object is made", "generation 0 count goes up by one", "_PyObject_GC_Link"],
            [
                "a tracked object is freed",
                "generation 0 count goes down by one",
                "_PyObject_GC_Del",
            ],
            ["the count passes 2000", "a bit is set on the eval breaker", "_Py_ScheduleGC"],
            ["the next instruction starts", "the collector actually runs", "ceval_gil.c"],
        ],
        title="The counter is live objects, not total allocations",
        caption="Make a million objects and free them as you go and the counter barely moves.",
        tones=["input", "input", "warning", "focus"],
    )
)


gallery.add(
    figures.table(
        "three-lists",
        ["generation", "threshold", "what its count means", "how often it runs"],
        [
            ["0, the young", "2000", "tracked objects alive right now", "constantly"],
            ["1, the middle", "10", "collections of generation 0", "once per 2000 or so"],
            ["2, the old", "10", "collections of generation 1", "rarely, and on purpose"],
        ],
        title="Three lists, and each one counts something different",
        caption="Only generation 0 counts objects. The other two count collections underneath them.",
        tones=["focus", "intermediate", "durable"],
    )
)


gallery.add(
    figures.table(
        "where-your-object-goes",
        ["after this", "gc.get_objects says"],
        [
            ["you made it", "generation 0"],
            ["one pass over generation 0", "generation 1"],
            ["another pass over generation 0", "generation 1"],
            ["a pass over generation 1", "generation 2"],
            ["a full pass", "generation 2, and it stays there"],
        ],
        title="Surviving a collection is a promotion",
        caption="Nothing moves an object back down. Generation 2 is where long lived data ends up.",
        tones=["input", "quiet", "quiet", "intermediate", "durable"],
    )
)


gallery.add(
    figures.compare(
        "the-brake-on-full-passes",
        (
            "what the threshold says",
            [
                "hundreds of middle passes",
                "one full pass every two",
                "so hundreds of full passes",
                "each walking every object",
            ],
        ),
        (
            "what actually ran",
            [
                "the same hundreds",
                "a handful of full passes",
                "fewer than one in twenty",
                "the rest were skipped",
            ],
        ),
        title="The rule that stops full collections happening",
        verdict="A full pass is skipped unless a quarter of the old objects are new since the last one.",
    )
)


gallery.add(
    figures.table(
        "one-layer-per-pass",
        ["collections so far", "tuples still tracked", "why"],
        [
            ["0", "4 of 5", "the innermost one was never tracked"],
            ["1", "3 of 5", "its parent can now see that"],
            ["2", "2 of 5", "and so on, one layer at a time"],
            ["3", "1 of 5", "each pass reveals the next"],
            ["4", "0 of 5", "nothing left to walk"],
        ],
        title="The collector shrinking its own future work",
        caption="A tuple that cannot reach anything trackable stops being walked, one layer per pass.",
        tones=["input", "quiet", "quiet", "intermediate", "durable"],
    )
)


raise SystemExit(gallery.save())
