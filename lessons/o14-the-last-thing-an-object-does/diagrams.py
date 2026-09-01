#!/usr/bin/env python
"""The diagrams for O14, finalization.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `the-order-a-collection-runs-in`. Five steps in a fixed order,
and almost every surprising thing about `__del__` is a consequence of where it sits in that
list rather than of anything about `__del__` itself.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("o14-the-last-thing-an-object-does")

gallery.add(
    figures.compare(
        "two-ways-to-be-told",
        (
            "a weakref callback",
            [
                "runs after the object is gone",
                "handed a reference that says None",
                "cannot bring anything back",
                "lives outside the object",
            ],
        ),
        (
            "a __del__ method",
            [
                "runs before anything is freed",
                "handed the object itself, as self",
                "can store self and cancel the death",
                "is part of the object",
            ],
        ),
        title="Two ways to hear that an object is finished",
        verdict="One is a notification. The other is a last turn at the wheel.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.flow(
        "the-order-a-collection-runs-in",
        [
            "run the weakref callbacks",
            "run the finalizers",
            "check what came back to life",
            "break the remaining weak references",
            "clear the objects and free them",
        ],
        title="Five steps, in this order, every collection",
        labels=[
            "so a callback fires before any __del__",
            "each one at most once, ever",
            "survivors move to the old generation",
            "no callbacks this time",
        ],
        tones=["input", "focus", "focus", "quiet", "warning"],
    )
)


gallery.add(
    figures.table(
        "which-runs-first",
        ["how the object died", "what runs first", "what runs second"],
        [
            ["the count reached zero", "__del__", "the weakref callbacks"],
            ["the collector found a cycle", "the weakref callbacks", "__del__"],
        ],
        title="The same two things, in opposite orders",
        caption="Nothing is wrong. The two death paths are different code.",
        tones=["focus", "warning"],
    )
)


gallery.add(
    figures.flow(
        "a-finalizer-runs-at-most-once",
        [
            "set the finalized bit on the object",
            "then call the finalizer",
            "if it stored self somewhere, the object survives",
            "next time round, the bit is already set",
        ],
        title="Why a resurrected object is never finalized twice",
        labels=[
            "before the call, not after",
            "which is where self becomes reachable again",
            "so the finalizer is skipped",
        ],
        tones=["focus", "input", "warning", "durable"],
    )
)


gallery.add(
    figures.compare(
        "what-changed-in-python-34",
        (
            "before 3.4",
            [
                "a cycle with __del__ was skipped",
                "it went into gc.garbage instead",
                "and leaked until you cleaned it up",
                "so people avoided __del__",
            ],
        ),
        (
            "now",
            [
                "finalizers run, then the cycle breaks",
                "gc.garbage stays empty",
                "each object finalized at most once",
                "so __del__ is safe in a cycle",
            ],
        ),
        title="The rule that most advice about __del__ still assumes",
        verdict="The advice outlived the problem by more than ten years.",
        verdict_tone="warning",
    )
)


gallery.add(
    figures.stack(
        "what-a-finalizer-can-still-see",
        [
            "self, with a normal reference count",
            "every attribute, still set",
            "the other objects in the cycle, still whole",
            "and any weak reference to it, still working",
        ],
        title="What is still true while __del__ is running",
        note="Clearing happens after finalizers, not before, which is what makes any of this usable.",
    )
)


raise SystemExit(gallery.save())
