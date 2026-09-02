#!/usr/bin/env python
"""The diagrams for M09, finding the thing that will not go away.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

`four-questions-in-order` is the spine, since most of this lesson is a procedure rather than a
mechanism. The rest cover what each tool can actually see, the two chains that catch real code,
and the routes into gc.garbage.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("m09-what-will-not-go-away")

gallery.add(
    figures.flow(
        "four-questions-in-order",
        [
            "is it growing at all",
            "does a pass free it",
            "who is holding it",
            "where did it come from",
        ],
        title="The order to ask, because each answer decides the next question",
        tones=["input", "quiet", "focus", "durable"],
        labels=["sys.getallocatedblocks", "gc.collect", "gc.get_referrers"],
    )
)


gallery.add(
    figures.table(
        "what-a-refcount-means",
        ["what you ask about", "what you get", "what it is worth"],
        [
            ["a fresh object", "2, not 1", "subtract the argument you passed"],
            ["an immortal object", "3221225472", "nothing, it never changes"],
            ["an object in a cycle", "a real number", "nothing, they hold each other"],
            ["an object you cannot find", "a real number", "the count, not the holders"],
        ],
        title="sys.getrefcount, and why it rarely ends an investigation",
        caption="It tells you how many references exist. It never tells you where any of them are.",
        tones=["input", "quiet", "warning", "warning"],
    )
)


gallery.add(
    figures.compare(
        "the-graph-you-can-walk",
        (
            "what the tools show",
            [
                "tracked objects only",
                "edges from tp_traverse",
                "one hop at a time",
                "a walk of the whole heap",
            ],
        ),
        (
            "what actually holds memory",
            [
                "untracked tuples too",
                "bytes inside a str",
                "C state with no traverse",
                "whatever your extension did",
            ],
        ),
        title="gc.get_referrers and gc.get_referents work on the collector's graph",
        verdict="If the collector cannot see an edge, neither can you. Absence is not proof.",
    )
)


gallery.add(
    figures.flow(
        "the-exception-chain",
        [
            "one saved exception",
            "its __traceback__",
            "tb_frame",
            "f_locals",
            "every local in it",
        ],
        title="Why one variable can hold a whole function's worth of objects",
        tones=["input", "quiet", "intermediate", "durable", "focus"],
        labels=["holds", "holds", "holds", "holds"],
    )
)


gallery.add(
    figures.table(
        "how-things-reach-gc-garbage",
        ["route in", "what ends up there", "does it happen to you"],
        [
            ["a class with __del__", "nothing since PEP 442", "no"],
            ["tp_del in a C extension", "the whole cycle", "rarely"],
            ["a broken tp_traverse", "nothing, it is invisible", "no"],
            ["gc.set_debug(DEBUG_SAVEALL)", "everything a pass freed", "only when you ask"],
        ],
        title="gc.garbage is empty, and that is not the good news it sounds like",
        caption="The list is checked for tp_del, which no pure Python class has. Use SAVEALL.",
        tones=["quiet", "warning", "quiet", "focus"],
    )
)


gallery.add(
    figures.table(
        "which-tool-answers-what",
        ["tool", "the question it answers", "what it costs"],
        [
            ["sys.getallocatedblocks", "is anything growing", "nothing"],
            ["gc.collect return value", "was it a cycle", "one full pass"],
            ["gc.get_referrers", "who points at this", "a walk of the heap"],
            ["gc.get_referents", "what does this point at", "one tp_traverse"],
            ["DEBUG_SAVEALL", "what did that pass free", "the objects stay alive"],
            ["tracemalloc", "which line allocated it", "every allocation traced"],
        ],
        title="Six tools, six different questions",
        caption="Reaching for the wrong one is how an afternoon disappears.",
        tones=["input", "quiet", "focus", "quiet", "intermediate", "durable"],
    )
)


raise SystemExit(gallery.save())
