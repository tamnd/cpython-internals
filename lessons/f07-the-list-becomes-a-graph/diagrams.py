#!/usr/bin/env python
"""The diagrams for F07, the list becomes a graph.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `graph-then-list-again`. Everything else follows from the
compiler spending the fourth pass in a shape it does not keep: blocks and edges, questions that
only make sense about a graph, and an order on disk that is nobody's idea of source order.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("f07-the-list-becomes-a-graph")

gallery.add(
    figures.pipeline(
        "graph-then-list-again",
        [
            ("a flat list", "what F06 emitted"),
            ("a graph of blocks", "edges, not offsets"),
            ("a flat list again", "reordered and shorter"),
            ("a code object", "F09 assembles it"),
        ],
        highlight=(1,),
        title="The fourth pass works in a shape the finished code object does not keep",
        caption="Nothing in a code object is a graph. The exception table and the odd line order are all that is left of one.",
    )
)


gallery.add(
    figures.table(
        "where-a-block-ends",
        ["an instruction starts a block when", "why", "example"],
        [
            ["it is the first one", "somewhere has to be the entry", "RESUME"],
            ["something jumps to it", "control can arrive from elsewhere", "a loop head"],
            ["the one before it jumped", "control never falls through", "after JUMP_BACKWARD"],
            ["the one before it returned", "same reason", "after RETURN_VALUE"],
        ],
        title="Three rules, and a flat list of instructions falls into blocks",
        caption="A basic block is a run of instructions you always enter at the top and always leave at the bottom.",
        tones=["quiet", "focus", "focus", "focus"],
    )
)


gallery.add(
    figures.compare(
        "two-different-orders",
        (
            "the order on disk",
            [
                "block 1, the try body",
                "block 2, the handler",
                "block 3, the reraise",
                "one after another in memory",
            ],
        ),
        (
            "the order control flow takes",
            [
                "block 1, then usually done",
                "block 2, only on an exception",
                "block 3, only if the type is wrong",
                "edges, and most are never walked",
            ],
        ),
        title="Once there is a graph, where a block sits stops meaning anything",
        verdict="b_next is the next block in memory. The edges are separate fields. Mixing the two up is the classic mistake.",
        verdict_tone="warning",
    )
)


gallery.add(
    figures.compare(
        "depth-is-a-path-question",
        (
            "walking the list straight through",
            [
                "add up the stack effects",
                "keep the highest total",
                "right for code with no branches",
                "wrong the moment there is a handler",
            ],
        ),
        (
            "walking every path in the graph",
            [
                "record the depth at each block's top",
                "follow every edge out of it",
                "a handler starts above empty",
                "keep the deepest path found",
            ],
        ),
        title="How deep does the stack get, and why you cannot answer it from a list",
        verdict="co_stacksize is how many slots a frame reserves, so getting it wrong is not a slow program, it is a broken one.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.flow(
        "cold-goes-last",
        [
            "mark every exception handler cold",
            "spread cold to blocks only handlers reach",
            "move all of them past the end",
            "add a real jump where one used to fall through",
        ],
        title="Why the handler for line 6 sits after the return on line 7",
        labels=[
            "and everything else warm",
            "the reordering itself",
        ],
        tones=["input", "intermediate", "focus", "durable"],
    )
)


gallery.add(
    figures.stack(
        "what-a-block-carries",
        [
            "b_next, the next block in memory, not in control flow",
            "b_instr, the instructions themselves",
            "b_predecessors, how many blocks can arrive here",
            "b_startdepth, how deep the stack is on entry",
            "b_cold, whether anything but an exception reaches it",
        ],
        title="One basic block, and the five fields the passes actually read",
        note="Four of these are answers computed by earlier passes. Only the instructions came from the code generator.",
    )
)


raise SystemExit(gallery.save())
