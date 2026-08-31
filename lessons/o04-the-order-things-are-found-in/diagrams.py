#!/usr/bin/env python
"""The diagrams for O04, the order the interpreter looks names up in.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `merging-the-lists`. The MRO is not a search, it is a list
computed once by a forty line merge, and every rule people learn about multiple inheritance
falls out of how that merge picks its next candidate.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("o04-the-order-things-are-found-in")

gallery.add(
    figures.table(
        "the-diamond",
        ["class", "declared bases", "defines where"],
        [
            ["A", "object", "yes"],
            ["B", "A", "no"],
            ["C", "A", "yes"],
            ["D", "B, C", "no"],
        ],
        title="Four classes, and one question: whose where does D get",
        caption="Both B and C lead back to A, so there are two paths up and something has to pick.",
        tones=["quiet", "quiet", "focus", "focus"],
    )
)


gallery.add(
    figures.stack(
        "three-rules",
        [
            "a class comes before every one of its bases",
            "the bases stay in the order you declared them",
            "and the same holds for every class in the list, not just D",
        ],
        title="What the order has to satisfy",
        note="There is usually only one list that satisfies all three, and sometimes there is none.",
    )
)


gallery.add(
    figures.flow(
        "merging-the-lists",
        [
            "three lists: B A object, C A object, and B C",
            "B is at the front of one and in nobody's tail, take B",
            "A is next in line but it sits in C's tail, so skip it",
            "C is in no tail either, take C, and now A is free",
            "D, B, C, A, object",
        ],
        title="The merge, one step at a time, for the diamond",
        labels=[
            "the two base MROs plus the bases you declared",
            "this is the whole rule, applied over and over",
            "taking A here would put it before C, which is wrong",
        ],
        tones=["input", "focus", "warning", "focus", "durable"],
    )
)


gallery.add(
    figures.compare(
        "no-order-exists",
        (
            "class XY(X, Y)",
            [
                "says X comes before Y",
                "and that is fine on its own",
            ],
        ),
        (
            "class YX(Y, X)",
            [
                "says Y comes before X",
                "and that is fine on its own",
            ],
        ),
        title="Two classes that each make sense, and one that cannot",
        verdict="class Bad(XY, YX) needs both at once, so pmerge gets stuck and raises TypeError.",
        verdict_tone="warning",
    )
)


gallery.add(
    figures.flow(
        "super-follows-the-instance",
        [
            "super().who() inside Left",
            "look at the instance, not at Left",
            "find Left in that instance's MRO",
            "take whatever is next in the list",
            "which may be a class Left never heard of",
        ],
        title="Why super is not a shortcut for the base class",
        labels=[
            "type(self), which Left cannot know in advance",
            "so the answer changes per instance",
            "one step, no search",
        ],
        tones=["input", "focus", "intermediate", "focus", "durable"],
    )
)


gallery.add(
    figures.flow(
        "where-a-lookup-goes",
        [
            "x.method in your code",
            "find_name_in_mro walks type(x).__mro__",
            "checking each class dict in turn",
            "and stops at the first hit",
        ],
        title="One list, walked front to back, and that is the whole search",
        labels=[
            "the list is already built, nothing is computed here",
            "a plain dict lookup per entry",
        ],
        tones=["input", "focus", "intermediate", "durable"],
    )
)


raise SystemExit(gallery.save())
