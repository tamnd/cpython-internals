#!/usr/bin/env python
"""The diagrams for R02, the three levels the runtime keeps its state at.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The order follows the lesson. The three boxes first, then what two interpreters share, then
the pointer chain that gets you from a thread back up to the runtime, then a table of which
level each fact this book has taught you lives at, then signals, then the bill.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("r02-where-the-state-lives")

gallery.add(
    figures.nest(
        "three-levels",
        (
            "the runtime, one per process",
            [
                "None, True, small ints, one character strings, the type objects",
                "the table of signal handlers",
                (
                    "an interpreter, id 0, the main one",
                    [
                        "sys.modules, builtins, the import lock, the warnings filters",
                        ("a thread, the main one", ["the exception being handled, the stack"]),
                        ("another thread", ["its own exception, its own stack"]),
                    ],
                ),
                (
                    "an interpreter, id 1",
                    [
                        "its own sys.modules, its own builtins, its own filters",
                        ("its own thread", ["its own exception, its own stack"]),
                    ],
                ),
            ],
        ),
        title="Where a running Python keeps things",
        caption="Every fact in this book lives at exactly one of these three levels.",
    )
)


gallery.add(
    figures.table(
        "what-two-interpreters-share",
        ["ask both interpreters for id(...)", "same address", "who made it"],
        [
            ["None", "yes", "the runtime, at startup"],
            ["the bool True", "yes", "the runtime, at startup"],
            ["the int 5", "yes", "the runtime, at startup"],
            ["the int 100000", "no", "each interpreter, on demand"],
            ["the string a", "yes", "the runtime, at startup"],
            ["the string startup", "no", "each interpreter, when compiled"],
            ["the type object int", "yes", "the runtime, it is static"],
            ["the sys module", "no", "each interpreter, at its own startup"],
            ["the dict sys.modules", "no", "each interpreter, at its own startup"],
        ],
        title="Two interpreters in one process, asked the same question",
        caption="The yes rows are the objects listed in _Py_static_objects. Nothing else is shared.",
        tones=[
            "durable",
            "durable",
            "durable",
            "warning",
            "durable",
            "warning",
            "durable",
            "focus",
            "focus",
        ],
    )
)


gallery.add(
    figures.flow(
        "the-pointer-chain",
        [
            "the thread you are on",
            "PyThreadState",
            "PyInterpreterState",
            "_PyRuntimeState",
        ],
        title="How C code gets from here to any of the three levels",
        tones=["input", "focus", "intermediate", "durable"],
        labels=[
            "PyThreadState_GET()",
            "tstate->interp",
            "interp->runtime",
        ],
    )
)


gallery.add(
    figures.table(
        "where-each-fact-lives",
        ["something this book has shown you", "which level owns it", "how you can tell"],
        [
            ["the small int cache", "the runtime", "same id in both interpreters"],
            ["the interned string table", "the runtime", "same id for a one character string"],
            ["sys.modules", "the interpreter", "a new one starts with 55 modules"],
            ["the recursion limit", "the interpreter", "set it here, unchanged there"],
            ["the warnings filters", "the interpreter", "add one here, unchanged there"],
            ["the import lock", "the interpreter", "one _gil field per interpreter"],
            ["the signal handler table", "the runtime", "one handlers[] array per process"],
            ["the exception being handled", "the thread", "two threads, two answers"],
        ],
        title="Pick any fact from the last seventy two lessons and it lands in one row",
        caption="The level is not a detail. It decides who can see the change you just made.",
        tones=[
            "durable",
            "durable",
            "focus",
            "focus",
            "focus",
            "focus",
            "durable",
            "intermediate",
        ],
    )
)


gallery.add(
    figures.compare(
        "who-may-handle-a-signal",
        (
            "signal.signal() succeeds",
            [
                "the main thread",
                "of the main interpreter",
                "and nowhere else at all",
            ],
        ),
        (
            "signal.signal() raises ValueError",
            [
                "any other thread",
                "the main thread of a subinterpreter",
                "any thread of a subinterpreter",
            ],
        ),
        title="One process wide table, one place allowed to write to it",
        verdict="The C test is _Py_IsMainThread() && _Py_IsMainInterpreter(interp), one per level.",
        verdict_tone="durable",
    )
)


gallery.add(
    figures.bars(
        "what-an-interpreter-costs",
        [
            ["os thread, with the lock", 329],
            ["interpreter, with the lock", 16758],
            ["os thread, no lock", 621],
            ["interpreter, no lock", 34808],
        ],
        unit="microseconds to make one",
        title="An interpreter is not a heavier thread, it is a different order of thing",
        caption="Roughly fifty times the price, and a few megabytes of memory on top of that.",
        tones=["quiet", "focus", "quiet", "warning"],
        width=420,
    )
)


raise SystemExit(gallery.save())
