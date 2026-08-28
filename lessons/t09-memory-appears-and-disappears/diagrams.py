#!/usr/bin/env python
"""The diagrams for T09, memory appears and disappears.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The two doing the heavy lifting are `a-cycle`, which is the picture of the one thing
reference counting cannot do, and `the-subtract-trick`, which is how the collector works out
that a group of objects is holding nothing but each other.
"""

from itertools import pairwise

from nbdiagram import Gallery, figures, stages
from nbdiagram.scene import Scene
from pyxray import theme

gallery = Gallery("t09-memory-appears-and-disappears")

gallery.add(
    stages.map(
        "where-we-are",
        title="The pipeline, with nothing highlighted",
        caption="Like T08, this lesson is not one of the boxes. It is about what happens to the values underneath all of them.",
    )
)


gallery.add(
    figures.table(
        "the-count-moves",
        ["what you write", "holders", "what the interpreter does"],
        [
            ["thing = [1, 2, 3]", "1", "builds it, count starts at 1"],
            ["holder = [thing]", "2", "the list holds it too"],
            ["box = {'k': thing}", "3", "so does the dict"],
            ["holder.clear()", "2", "the list lets go"],
            ["del box", "1", "the dict lets go"],
            ["del thing", "0", "freed on the spot"],
        ],
        title="One object, six lines, and the count that decides its fate",
        caption="Nothing is scheduled and nothing is deferred. The last line frees the list before the next line runs.",
        tones=["quiet", "quiet", "quiet", "quiet", "quiet", "focus"],
    )
)


def _a_cycle() -> Scene:
    """Two objects holding each other, before and after the names go away."""
    scene = Scene("a-cycle")
    node_width = 180
    node_height = 84
    inner = 130

    scene.text("The one shape counting cannot free", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    panel_width = 2 * node_width + inner
    panels = [
        ("while the names are there", ["a", "b"], "durable", "2"),
        ("after del a, b", [None, None], "warning", "1"),
    ]
    for panel, (heading, names, tone, count) in enumerate(panels):
        left = panel * (panel_width + 150)
        scene.text(heading, left, top, size=theme.BODY_SIZE)
        name_row = top + theme.BODY_SIZE * theme.LINE_HEIGHT + 14
        node_row = name_row + 90

        nodes = [
            scene.box(
                f"Node\ncount {count}",
                left + index * (node_width + inner),
                node_row,
                width=node_width,
                height=node_height,
                tone=tone,
            )
            for index in range(2)
        ]

        for index, name in enumerate(names):
            middle = left + index * (node_width + inner) + node_width / 2
            if name is None:
                scene.text(
                    "gone", middle - 24, name_row + 12, size=theme.CAPTION_SIZE, colour=theme.MUTED
                )
                continue
            handle = scene.box(
                name, middle - 40, name_row, width=80, height=44, tone="input", mono=True
            )
            scene.arrow(handle, nodes[index], sides=("bottom", "top"))

        edge = left + node_width
        far = edge + inner
        scene.arrow((edge, node_row + 26), (far, node_row + 26))
        scene.arrow((far, node_row + node_height - 26), (edge, node_row + node_height - 26))
        scene.text("other", edge + 36, node_row - 4, size=theme.CAPTION_SIZE, colour=theme.MUTED)
        scene.text(
            "other",
            edge + 36,
            node_row + node_height + 6,
            size=theme.CAPTION_SIZE,
            colour=theme.MUTED,
        )

    bottom = max(element.box[3] for element in scene.elements)
    for line, words in enumerate(
        [
            "Both counts start at 2, one for the name and one for the other Node. Dropping both names",
            "takes each count down to 1 and stops there, because the two objects are still holding each",
            "other. Nothing else in the program can reach them and nothing will ever free them.",
        ]
    ):
        scene.text(
            words,
            0,
            bottom + theme.GRID + line * theme.CAPTION_SIZE * theme.LINE_HEIGHT,
            size=theme.CAPTION_SIZE,
            colour=theme.MUTED,
        )
    return scene


gallery.add(_a_cycle())


gallery.add(
    figures.compare(
        "two-ways-to-free",
        (
            "reference counting",
            [
                "runs on every DECREF",
                "frees the moment the count hits 0",
                "you can predict exactly when",
                "cannot free a cycle",
            ],
        ),
        (
            "the cycle collector",
            [
                "runs when allocations pile up",
                "frees whole groups at once",
                "you cannot predict when",
                "cycles are the only reason it exists",
            ],
        ),
        title="Two mechanisms, doing different jobs",
        verdict="Counting does almost all of the work. The collector exists for the cases counting provably cannot reach.",
        verdict_tone="durable",
    )
)


def _the_subtract_trick() -> Scene:
    """How the collector decides a group of objects is holding nothing but each other."""
    scene = Scene("the-subtract-trick")
    width = 170
    height = 62

    scene.text("How the collector tells garbage from live data", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    steps = [
        (
            "1. copy the counts",
            ["A  2", "B  2", "C  1"],
            ["input", "input", "input"],
            "every candidate gets a scratch copy of its real count",
        ),
        (
            "2. subtract the ones inside",
            ["A  1", "B  0", "C  0"],
            ["intermediate", "intermediate", "intermediate"],
            "walk each candidate and take one off everything it points at",
        ),
        (
            "3. read the answer off the leftovers",
            ["A  keep", "B  free", "C  free"],
            ["durable", "warning", "warning"],
            "A still has a holder the walk never saw, so A lives and the other two go",
        ),
    ]
    y = top
    for heading, rows, tones, note in steps:
        scene.text(heading, 0, y, size=theme.BODY_SIZE)
        row_y = y + theme.BODY_SIZE * theme.LINE_HEIGHT + 8
        for index, cell in enumerate(rows):
            scene.box(
                cell,
                index * (width + 16),
                row_y,
                width=width,
                height=height,
                tone=tones[index],
                mono=True,
                size=theme.CAPTION_SIZE,
                align="center",
            )
        scene.text(
            note,
            3 * (width + 16) + 20,
            row_y + height / 2 - theme.CAPTION_SIZE * theme.LINE_HEIGHT / 2,
            size=theme.CAPTION_SIZE,
            colour=theme.MUTED,
        )
        y = row_y + height + 34

    bottom = max(element.box[3] for element in scene.elements)
    for line, words in enumerate(
        [
            "The scratch copy is why the real reference counts are never disturbed. Anything that ends",
            "at zero is held only by other candidates, and anything reachable from a survivor is kept",
            "as well, because a live object pointing into the group keeps that part of the group alive.",
        ]
    ):
        scene.text(
            words,
            0,
            bottom + theme.GRID + line * theme.CAPTION_SIZE * theme.LINE_HEIGHT,
            size=theme.CAPTION_SIZE,
            colour=theme.MUTED,
        )
    return scene


gallery.add(_the_subtract_trick())


def _generations() -> Scene:
    """Three buckets, and the rule for moving between them."""
    scene = Scene("generations")
    width = 230
    height = 96
    gap = 110

    scene.text("Where the collector looks, and how often", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    buckets = [
        ("generation 0\neverything new", "checked most often", "input"),
        ("generation 1\nsurvived once", "checked less often", "intermediate"),
        ("generation 2\nsurvived twice", "checked rarely", "durable"),
    ]
    boxes = []
    for index, (label, note, tone) in enumerate(buckets):
        x = index * (width + gap)
        box = scene.box(label, x, top, width=width, height=height, tone=tone)
        scene.text(note, x, top + height + 10, size=theme.CAPTION_SIZE, colour=theme.MUTED)
        boxes.append(box)

    for first, second in pairwise(boxes):
        scene.arrow(first, second, label="survived")

    bottom = max(element.box[3] for element in scene.elements)
    for line, words in enumerate(
        [
            "The bet is that most objects die young, which is true of nearly every Python program: the",
            "temporary list inside a loop is gone before the loop turns over. Anything still here after",
            "two collections is probably going to stay, so it gets looked at less. Survive twice and the",
            "collector mostly leaves you alone.",
        ]
    ):
        scene.text(
            words,
            0,
            bottom + theme.GRID + line * theme.CAPTION_SIZE * theme.LINE_HEIGHT,
            size=theme.CAPTION_SIZE,
            colour=theme.MUTED,
        )
    return scene


gallery.add(_generations())


gallery.add(
    figures.nest(
        "the-allocator-layers",
        (
            "the operating system",
            [
                (
                    "arena, 256 KiB or 1 MiB",
                    [
                        (
                            "pool, 4 KiB, one size class",
                            ["block, 64 bytes", "block, 64 bytes", "block, 64 bytes"],
                        )
                    ],
                )
            ],
        ),
        title="Where the bytes for one small object come from",
        caption="Four layers. Your object is a block, blocks of one size share a pool, pools share an arena, and only the arena ever talks to the operating system.",
    )
)


gallery.add(
    figures.table(
        "size-classes",
        ["you ask for", "you get", "size class"],
        [
            ["1 to 16 bytes", "16", "0"],
            ["17 to 32 bytes", "32", "1"],
            ["33 to 48 bytes", "48", "2"],
            ["...", "...", "..."],
            ["481 to 496 bytes", "496", "30"],
            ["497 to 512 bytes", "512", "31"],
            ["more than 512 bytes", "straight to malloc", "none"],
        ],
        title="The thirty two sizes CPython allocates small objects in",
        caption="On a 64 bit build the classes are 16 bytes apart, so 512 divided by 16 gives 32 of them. Rounding up is what lets a freed block be reused by any other object of about the same size.",
        tones=["quiet", "quiet", "quiet", "quiet", "quiet", "quiet", "warning"],
    )
)


def _giving_it_back() -> Scene:
    """What actually happens to the bytes when an object is freed."""
    scene = Scene("giving-it-back")
    width = 250
    height = 78

    scene.text("What freeing an object really does", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    steps = [
        ("the count hits zero", "input"),
        ("tp_dealloc runs", "intermediate"),
        ("the block goes back\nto its pool", "durable"),
        ("the pool stays\nin the arena", "durable"),
    ]
    boxes = []
    for index, (label, tone) in enumerate(steps):
        box = scene.box(label, index * (width + 50), top, width=width, height=height, tone=tone)
        boxes.append(box)
    for first, second in pairwise(boxes):
        scene.arrow(first, second)

    row = top + height + 60
    scene.box(
        "the operating system never hears about any of this",
        0,
        row,
        width=4 * width + 3 * 50,
        height=60,
        tone="warning",
        align="center",
    )

    bottom = max(element.box[3] for element in scene.elements)
    for line, words in enumerate(
        [
            "An arena goes back to the operating system only when every pool in it is empty, which in a",
            "long running program is rare, because one surviving object anywhere in an arena keeps the",
            "whole thing. This is why a process that peaked at two gigabytes usually still looks like a",
            "process that is using two gigabytes, and why the next allocation is fast.",
        ]
    ):
        scene.text(
            words,
            0,
            bottom + theme.GRID + line * theme.CAPTION_SIZE * theme.LINE_HEIGHT,
            size=theme.CAPTION_SIZE,
            colour=theme.MUTED,
        )
    return scene


gallery.add(_giving_it_back())


gallery.add(
    figures.table(
        "what-to-reach-for",
        ["you want to know", "ask this", "watch out for"],
        [
            ["is it still alive", "weakref.ref(x)", "some types cannot be weakly referenced"],
            ["when did it die", "a weakref callback", "the object is already gone by then"],
            ["what is holding it", "gc.get_referrers(x)", "your own frame is in the answer"],
            ["what does it hold", "gc.get_referents(x)", "this is tp_traverse, not __dict__"],
            ["is it in a cycle", "pyxray.heap.cycles(x)", "the walk stops at classes"],
            ["clean up the cycles", "gc.collect()", "returns a count, not a list"],
        ],
        title="The tools, and where each one bites",
        caption="All but one of these are in the standard library. None of them needs a debug build.",
    )
)


raise SystemExit(gallery.save())
