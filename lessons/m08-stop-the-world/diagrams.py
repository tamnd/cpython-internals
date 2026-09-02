#!/usr/bin/env python
"""The diagrams for M08, the collector on the free threaded build.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

`two-shapes-of-heap` is the spine. The rest cover the counter every thread shares, what happens
to the other threads while a pass runs, and the mark alive pass that pays for all of it.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("m08-stop-the-world")

gallery.add(
    figures.compare(
        "two-shapes-of-heap",
        (
            "the ordinary build",
            [
                "three linked lists",
                "an object is in one",
                "a pass walks one list",
                "surviving moves you up",
            ],
        ),
        (
            "the free threaded build",
            [
                "no lists at all",
                "objects sit in the heap",
                "a pass walks all of it",
                "there is nowhere to move",
            ],
        ),
        title="Where the collector looks for your object",
        verdict="Generations are an optimisation that needs a list. This build does not have one.",
    )
)


gallery.add(
    figures.table(
        "same-question-two-answers",
        ["what you ask", "ordinary build", "free threaded build"],
        [
            ["gc.get_objects(generation=0)", "the young list", "the whole heap"],
            ["gc.get_objects(generation=2)", "the old list", "the whole heap"],
            ["where a new object is", "generation 0", "everywhere at once"],
            ["gc.collect(0) on an old cycle", "cannot see it", "frees it"],
            ["what a pass costs", "depends which one", "always everything"],
        ],
        title="The same three cells from M07, run on the other build",
        caption="The generation argument is still accepted. It just no longer selects anything.",
        tones=["input", "input", "quiet", "focus", "warning"],
    )
)


gallery.add(
    figures.flow(
        "the-count-nobody-owns",
        [
            "a thread makes an object",
            "its own counter goes up",
            "it reaches 512",
            "one atomic add",
            "the shared count moves",
        ],
        title="Why the counter is approximate",
        tones=["input", "quiet", "warning", "intermediate", "focus"],
        labels=["local", "still local", "flush", "visible to everyone"],
    )
)


gallery.add(
    figures.table(
        "what-stopping-costs",
        ["a thread that is", "how it gets stopped", "what it costs"],
        [
            ["running Python", "a bit on its eval breaker", "up to one instruction"],
            ["blocked in C on IO", "marked parked where it is", "nothing"],
            ["holding a lock", "parks between instructions", "up to one instruction"],
            ["the one collecting", "not stopped, it is the one asking", "the whole pass"],
        ],
        title="Stopping the world, one thread at a time",
        caption="The collector waits in one millisecond steps until the last thread has parked.",
        tones=["input", "durable", "input", "focus"],
    )
)


gallery.add(
    figures.flow(
        "mark-alive-first",
        [
            "start from sys.modules",
            "follow every reference",
            "set the alive bit",
            "walk the heap",
            "skip anything marked",
        ],
        title="How a build with no generations stays affordable",
        tones=["input", "quiet", "durable", "intermediate", "focus"],
        labels=["a known root", "tp_traverse", "then the real pass", "most objects"],
    )
)


gallery.add(
    figures.table(
        "the-bits-that-replaced-the-lists",
        ["bit", "name", "what the collector uses it for"],
        [
            ["0", "tracked", "this object is the collector's business"],
            ["1", "finalized", "tp_finalize has already run"],
            ["2", "unreachable", "working state during a pass"],
            ["3", "frozen", "gc.freeze was called, skip it"],
            ["4", "shared", "more than one thread has seen it"],
            ["5", "alive", "reached from a root, skip it"],
            ["6", "deferred", "its count is not being kept"],
        ],
        title="ob_gc_bits, one byte in every object header",
        caption="M06 found this byte at offset 11. This is what the collector keeps in it.",
        tones=["focus", "quiet", "intermediate", "durable", "quiet", "intermediate", "input"],
    )
)


raise SystemExit(gallery.save())
