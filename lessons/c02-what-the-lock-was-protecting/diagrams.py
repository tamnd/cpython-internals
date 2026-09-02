#!/usr/bin/env python
"""The diagrams for C02, what the one big lock was and was not keeping safe.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

`two-kinds-of-safety` is the spine. Everything else is either evidence for it or the machinery
that replaced the lock: where a counter loses its increments, what a one byte mutex holds, how
two objects get locked without deadlocking, what per object locks do to a benchmark, and the
route by which the lock can come back on while the interpreter is already running.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("c02-what-the-lock-was-protecting")

gallery.add(
    figures.compare(
        "two-kinds-of-safety",
        (
            "the interpreter's own data",
            [
                "a list's array of items",
                "a dict's table",
                "every reference count",
                "safe on both builds",
            ],
        ),
        (
            "the variables in your code",
            [
                "read, add, write back",
                "three separate steps",
                "safe only by accident",
                "never promised anywhere",
            ],
        ),
        title="The two things people mean when they say the GIL made Python thread safe",
        verdict="Only the left column was ever a promise. The right column was luck.",
        verdict_tone="warning",
    )
)


gallery.add(
    figures.table(
        "where-the-count-goes-wrong",
        ["how the counter is written", "between the read and the write", "on a build with a GIL"],
        [
            ["counter = counter + 1", "nothing at all", "every increment kept"],
            ["counter = add_one(counter)", "a call, so a periodic check", "about half get lost"],
            ["a loop that goes round once", "a backward jump", "about two thirds lost"],
        ],
        title="Three ways to add one, and the only difference is what sits in the middle",
        caption="Same threads, same interval, same machine. The lock moves where it is allowed to.",
        tones=["durable", "warning", "warning"],
    )
)


gallery.add(
    figures.table(
        "one-byte-of-lock",
        ["ob_mutex", "what the byte means", "what a thread does about it"],
        [
            ["0b00", "nobody is holding it", "one compare and exchange"],
            ["0b01", "somebody is holding it", "park, and wait to be woken"],
            ["0b10", "free, and threads are parked", "take it, then wake one"],
            ["0b11", "held, and threads are parked", "join the queue"],
        ],
        title="PyMutex, the lock that lives in the object header",
        caption="One byte, two bits used. Every object gets one, and taking a free one is one instruction.",
        tones=["focus", "warning", "intermediate", "quiet"],
    )
)


gallery.add(
    figures.compare(
        "locking-two-at-once",
        (
            "one lock, then the other",
            [
                "thread A takes list a",
                "thread B takes list b",
                "each now wants the other",
                "neither ever moves again",
            ],
        ),
        (
            "Py_BEGIN_CRITICAL_SECTION2",
            [
                "let go of anything held",
                "take both, in one order",
                "no cycle to get stuck in",
                "this is what a + b uses",
            ],
        ),
        title="Why nesting two critical sections is not allowed",
        verdict="A critical section is allowed to suspend itself, which is what stops it deadlocking.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.bars(
        "same-list-or-a-list-each",
        [
            ["one thread, one list", 6],
            ["4 threads, the same list", 45],
            ["4 threads, a list each", 10],
        ],
        unit="ms",
        title="1,600,000 appends, on a build with no GIL",
        caption="From the recording below. On a build with a GIL the last two are the same number.",
        tones=["durable", "warning", "focus"],
        width=500,
    )
)


gallery.add(
    figures.flow(
        "the-lock-coming-back",
        [
            "an extension is imported",
            "it has no Py_mod_gil slot",
            "the import machinery warns",
            "gil->enabled goes to INT_MAX",
            "every thread takes the lock",
        ],
        title="How a free threaded interpreter stops being free threaded, mid run",
        tones=["input", "warning", "intermediate", "durable", "focus"],
        labels=["import time", "so it may not be safe", "RuntimeWarning", "and stays there"],
    )
)


raise SystemExit(gallery.save())
