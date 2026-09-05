#!/usr/bin/env python
"""The diagrams for C07, the lock as something the runtime switches rather than something built in.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The order follows the lesson. The two questions people run together, what each of the four
ways of asking actually does, the five steps an import goes through, the counter that decides
whether the lock is on, the eight timings side by side, and the allocator swap underneath them.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("c07-the-lock-that-comes-back")

gallery.add(
    figures.compare(
        "two-questions-that-sound-like-one",
        (
            "was it built without the lock",
            [
                "decided by configure",
                "fixed for the whole binary",
                "Py_GIL_DISABLED in the header",
                "sys.abiflags is t",
            ],
        ),
        (
            "is the lock on right now",
            [
                "decided while running",
                "can change after startup",
                "sys._is_gil_enabled()",
                "one import can flip it",
            ],
        ),
        title="Two different questions about the same lock",
        verdict="A build without the lock can still be running with it on. That is the whole lesson.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.table(
        "four-ways-to-ask-for-the-other-one",
        ["what you ask for", "ordinary build", "build with no lock"],
        [
            ["nothing", "lock on", "lock off"],
            ["-X gil=1", "lock on", "lock on"],
            ["-X gil=0", "refuses to start", "lock off"],
            ["PYTHON_GIL=1", "lock on", "lock on"],
            ["PYTHON_GIL=0", "refuses to start", "lock off"],
        ],
        title="Asking for a lock state on the command line and in the environment",
        caption="An ordinary build will not pretend. Asking it to drop the lock is a fatal error.",
        tones=["quiet", "quiet", "warning", "quiet", "warning"],
    )
)


gallery.add(
    figures.flow(
        "what-an-import-does-to-the-lock",
        [
            "turn the lock on",
            "run the module init",
            "ask the module about threads",
            "no answer given",
            "keep the lock on and warn",
        ],
        title="Importing a compiled module that was written before free threading",
        tones=["intermediate", "input", "focus", "warning", "warning"],
        labels=["before anything runs", "it can do anything", "the Py_mod_gil slot", "silence"],
    )
)


gallery.add(
    figures.table(
        "the-counter-behind-the-switch",
        ["value of gil->enabled", "what it means", "how it got there"],
        [
            ["0", "the lock is off", "the build started this way"],
            ["1 or more", "on, for now", "an import is in progress"],
            ["INT_MAX", "on, for good", "a module did not declare"],
        ],
        title="The lock is not a flag, it is a counter",
        caption="Going from zero to one stops the world, so the switch is not free either.",
        tones=["durable", "focus", "warning"],
    )
)


gallery.add(
    figures.bars(
        "eight-workloads-on-one-thread",
        [
            ["list appends", 0.34],
            ["f-strings", 0.67],
            ["fib(25)", 1.10],
            ["raise and catch", 1.10],
            ["dict stores", 1.18],
            ["attribute reads", 1.33],
            ["calls", 1.35],
            ["sorting", 1.47],
        ],
        unit="times the GIL build",
        title="How long each workload took with no lock, from the two Tier 1 recordings",
        caption="Above one is slower. One thread, nothing shared, so none of this is contention.",
        tones=["durable", "durable", "quiet", "quiet", "quiet", "warning", "warning", "warning"],
        width=620,
    )
)


gallery.add(
    figures.compare(
        "the-allocator-underneath",
        (
            "ordinary build",
            [
                "pymalloc for objects",
                "one shared set of pools",
                "safe because of the lock",
                "small and well tuned",
            ],
        ),
        (
            "build with no lock",
            [
                "mimalloc for objects",
                "a heap per thread",
                "no lock needed to allocate",
                "faster at appending",
            ],
        ),
        title="Removing the lock forced a different allocator",
        verdict="Both bars below one are allocation heavy. That is not a coincidence.",
        verdict_tone="focus",
    )
)


raise SystemExit(gallery.save())
