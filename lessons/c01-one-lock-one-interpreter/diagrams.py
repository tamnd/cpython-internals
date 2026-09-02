#!/usr/bin/env python
"""The diagrams for C01, the lock that lets one thread run Python at a time.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

`the-handoff` is the spine, because almost every surprising thing about threads in CPython
falls out of who asks for the lock and when. The rest cover the struct, the one place in the
eval loop where the lock can actually be dropped, the split between CPU work and waiting, the
switch interval trade, and the same benchmark on the build with no lock at all.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("c01-one-lock-one-interpreter")

gallery.add(
    figures.flow(
        "the-handoff",
        [
            "a waiting thread asks",
            "it waits out the interval",
            "it sets the drop bit",
            "the running thread checks",
            "the running thread lets go",
            "the waiting thread runs",
        ],
        title="How the lock actually changes hands, and why it takes so long",
        tones=["input", "quiet", "warning", "intermediate", "durable", "focus"],
        labels=["take_gil", "5 ms by default", "eval_breaker", "at a backward jump", "drop_gil"],
    )
)


gallery.add(
    figures.table(
        "what-the-lock-is-made-of",
        ["field", "what it holds", "why it is there"],
        [
            ["locked", "one boolean", "is anybody holding it"],
            ["mutex, cond", "a lock and a signal", "wait without spinning"],
            ["interval", "microseconds", "how long a waiter is patient"],
            ["last_holder", "a thread state", "did somebody else get a turn"],
            ["switch_number", "a counter", "tell a real handoff from a timeout"],
            ["switch_cond", "another signal", "stop one thread hogging turns"],
        ],
        title="struct _gil_runtime_state, all of it",
        caption="Six fields. The famous lock is one boolean and the machinery to hand it over.",
        tones=["focus", "quiet", "input", "quiet", "intermediate", "durable"],
    )
)


gallery.add(
    figures.flow(
        "where-the-check-happens",
        [
            "JUMP_BACKWARD",
            "_CHECK_PERIODIC",
            "check_periodics",
            "_Py_HandlePending",
            "detach, then attach",
        ],
        title="The only route from running code to letting go of the lock",
        tones=["input", "quiet", "intermediate", "warning", "focus"],
        labels=["runs this op", "calls", "sees the bit", "drops the lock"],
    )
)


gallery.add(
    figures.compare(
        "adding-versus-waiting",
        (
            "two threads adding numbers",
            [
                "both need the lock",
                "one runs, one waits",
                "handed over and back",
                "no faster than in a row",
            ],
        ),
        (
            "two threads sleeping",
            [
                "sleep drops the lock",
                "both wait at once",
                "no handoff needed",
                "twice as fast as in a row",
            ],
        ),
        title="The same two threads, and the only thing that changed is what they do",
        verdict="Threads help when they are waiting for something, not when they are computing.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.table(
        "the-switch-interval-trade",
        ["sys.setswitchinterval", "work the two threads get done", "how evenly they share"],
        [
            ["1 microsecond", "about half the default", "very evenly"],
            ["5 ms, the default", "the baseline", "close to evenly"],
            ["50 ms", "more than the default", "starting to skew"],
            ["half a second", "one thread's worth", "one thread never runs"],
        ],
        title="It is not a fairness dial, it is a trade against the cost of a handoff",
        caption="Smaller means more handoffs, and every handoff stops one thread and starts another.",
        tones=["warning", "focus", "quiet", "warning"],
    )
)


gallery.add(
    figures.compare(
        "two-builds-one-benchmark",
        (
            "the build you have",
            [
                "one GIL per interpreter",
                "one thread runs Python",
                "2 threads, 1.0x speedup",
                "sys._is_gil_enabled True",
            ],
        ),
        (
            "the free threaded build",
            [
                "no lock to take",
                "all threads run Python",
                "2 threads, 2.0x speedup",
                "sys._is_gil_enabled False",
            ],
        ),
        title="The same benchmark, run on both builds, from the same program",
        verdict="Same source, same version, same machine. The only difference is a build flag.",
        verdict_tone="focus",
    )
)


raise SystemExit(gallery.save())
