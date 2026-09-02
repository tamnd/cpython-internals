#!/usr/bin/env python
"""The diagrams for C05, the one word that lets anything interrupt a running thread.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

`where-a-thread-stops-to-look` is the shape of the whole lesson, and the rest fills it in. The
two backward jumps, the eight bits in the order the runtime deals with them, the long way a
signal travels before your handler sees it, who is allowed to ask for what, and the pair of
numbers that show what happens when a thread never stops to look at all.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("c05-the-bit-that-interrupts")

gallery.add(
    figures.compare(
        "where-a-thread-stops-to-look",
        (
            "it looks here",
            [
                "after a backward jump",
                "when a function resumes",
                "when a call returns",
                "roughly every few opcodes",
            ],
        ),
        (
            "it does not look here",
            [
                "inside one call to sort",
                "inside a regex match",
                "inside a yield from loop",
                "for as long as that takes",
            ],
        ),
        title="Where a running thread can be interrupted, and where it cannot",
        verdict="Ctrl-C, the collector and every other interruption wait for the left column.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.compare(
        "two-backward-jumps",
        (
            "JUMP_BACKWARD",
            [
                "an ordinary while or for",
                "runs _CHECK_PERIODIC",
                "Ctrl-C lands here",
                "53 of them in asyncio",
            ],
        ),
        (
            "JUMP_BACKWARD_NO_INTERRUPT",
            [
                "a yield from or await",
                "skips the check on purpose",
                "the inner one handles it",
                "86 of them in asyncio",
            ],
        ),
        title="Two loop opcodes that jump to the same place",
        verdict="The counts are from one module, asyncio.base_events, and the first cell prints them.",
        verdict_tone="quiet",
    )
)


gallery.add(
    figures.table(
        "one-word-eight-bits",
        ["bit", "who sets it", "what the thread does"],
        [
            ["EVAL_PLEASE_STOP", "the runtime, at shutdown", "suspends itself"],
            ["SIGNALS_PENDING", "the C signal handler", "runs your Python handler"],
            ["CALLS_TO_DO", "Py_AddPendingCall", "runs the queued C callbacks"],
            ["EVAL_EXPLICIT_MERGE", "the free threaded build", "merges its reference counts"],
            ["GC_SCHEDULED", "the allocator, past 2000", "runs a collection"],
            ["JIT_INVALIDATE_COLD", "the JIT", "throws away cold traces"],
            ["GIL_DROP_REQUEST", "another thread waiting", "drops the lock and takes it back"],
            ["ASYNC_EXCEPTION", "PyThreadState_SetAsyncExc", "raises the exception it was handed"],
        ],
        title="The eight bits, in the order _Py_HandlePending deals with them",
        caption="One word on the thread state. The eval loop reads it, and only unpacks it when it is not zero.",
        tones=[
            "quiet",
            "focus",
            "focus",
            "quiet",
            "focus",
            "quiet",
            "durable",
            "focus",
        ],
    )
)


gallery.add(
    figures.flow(
        "the-long-way-round-a-signal",
        [
            "you press Ctrl-C",
            "the C handler writes down which signal",
            "it sets one bit on the main thread",
            "the main thread reaches a check",
            "your Python handler runs",
        ],
        title="What happens between Ctrl-C and KeyboardInterrupt",
        tones=["input", "intermediate", "intermediate", "focus", "durable"],
        labels=["the kernel calls it", "nothing else", "could be a while", "at last"],
    )
)


gallery.add(
    figures.table(
        "who-asks-and-who-runs",
        ["what you call", "whose bit it sets", "which thread does the work"],
        [
            ["signal.raise_signal", "the main thread", "the main thread, always"],
            ["Py_AddPendingCall", "the main thread", "the main thread, always"],
            ["PyThreadState_SetAsyncExc", "the thread you named", "that thread"],
            ["_Py_ScheduleGC", "the thread allocating", "that thread"],
            ["sys.remote_exec", "a thread in another process", "the main thread over there"],
        ],
        title="Five ways to set a bit, and where the work lands",
        caption="Asking is cheap and never blocks. Whoever owns the bit does the work later.",
        tones=["focus", "focus", "quiet", "quiet", "durable"],
    )
)


gallery.add(
    figures.bars(
        "one-call-or-sixty-thousand-steps",
        [
            ["json.loads, 60,000 dicts", 1],
            ["a list display, 60,000 dicts", 89],
        ],
        unit="collections",
        title="How many times the collector ran while the same objects were built",
        caption="Same objects, same count, same allocator. Only one of the two ever stops to look.",
        tones=["durable", "warning"],
        width=560,
    )
)


raise SystemExit(gallery.save())
