#!/usr/bin/env python
"""The diagrams for C08, handing work to a second interpreter and paying for the handover.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The order follows the lesson. What happens to one argument on its way across, the three routes
it can take, the two workloads split three ways on each of the two builds, what a single
crossing costs, and a summary of which arrangement to reach for.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("c08-sending-work-to-another-interpreter")

gallery.add(
    figures.flow(
        "what-happens-to-an-argument",
        [
            "your object",
            "reduced to plain bytes",
            "carried across",
            "built again",
            "a different object",
        ],
        title="An argument on its way to another interpreter",
        tones=["input", "intermediate", "quiet", "intermediate", "durable"],
        labels=["nothing is shared", "no pointers cross", "at a new address"],
    )
)


gallery.add(
    figures.table(
        "the-three-routes-across",
        ["what you are sending", "route it takes", "what arrives"],
        [
            ["int, str, bytes, float", "a direct one, per type", "a copy, sometimes the same one"],
            ["tuple of those", "the direct one, per item", "a new tuple of copies"],
            ["a function using no globals", "the code itself", "the same function, rebuilt"],
            ["list, dict, set, instances", "pickle", "a copy, if it pickles at all"],
            ["a function using a global", "nothing works", "NotShareableError"],
        ],
        title="How a value gets from one interpreter to another",
        caption="Whichever route it takes, the object on the far side is a different object.",
        tones=["durable", "durable", "focus", "quiet", "warning"],
    )
)


gallery.add(
    figures.bars(
        "two-workloads-with-the-lock",
        [
            ["arithmetic, threads", 1.03],
            ["arithmetic, interpreters", 2.44],
            ["big list, threads", 0.75],
            ["big list, interpreters", 0.02],
        ],
        unit="times one at a time",
        title="Two workloads split four ways on a build that has the lock",
        caption="Above one is a win. The last bar is the crossing cost eating the whole job.",
        tones=["quiet", "durable", "quiet", "warning"],
        width=500,
    )
)


gallery.add(
    figures.bars(
        "two-workloads-with-no-lock",
        [
            ["arithmetic, threads", 2.83],
            ["arithmetic, interpreters", 1.41],
            ["big list, threads", 1.23],
            ["big list, interpreters", 0.04],
        ],
        unit="times one at a time",
        title="The same two workloads on a build with no lock",
        caption="Threads now win the job interpreters used to win, and the crossing still costs.",
        tones=["durable", "quiet", "durable", "warning"],
        width=500,
    )
)


gallery.add(
    figures.bars(
        "what-one-crossing-costs",
        [
            ["a small int", 1902],
            ["a 1000 byte string", 1552],
            ["a 100 item list", 121],
        ],
        unit="thousand round trips a second",
        title="Putting one value on a queue and taking it off again",
        caption="The first two go the direct route. The third has to be pickled and rebuilt.",
        tones=["durable", "durable", "warning"],
        width=500,
    )
)


gallery.add(
    figures.table(
        "which-one-to-reach-for",
        ["shape of the work", "build with the lock", "build with no lock"],
        [
            ["much work, small arguments", "interpreters", "either, threads are simpler"],
            ["little work, big arguments", "neither, keep it serial", "threads"],
            ["waiting on the network", "threads", "threads"],
            ["needs an old C extension", "interpreters may refuse it", "it turns the lock back on"],
        ],
        title="Where each arrangement earns its keep",
        caption="The build matters, and so does how much data each job has to carry with it.",
        tones=["focus", "warning", "quiet", "warning"],
    )
)


raise SystemExit(gallery.save())
