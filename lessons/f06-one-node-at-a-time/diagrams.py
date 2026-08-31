#!/usr/bin/env python
"""The diagrams for F06, one node at a time.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `one-node-one-shape`. Everything else follows from the code
generator being a walk that looks at one node and emits a fixed shape for it: short circuits
become jumps, evaluation order is whatever order the walk visits in, and nothing is tidied up.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("f06-one-node-at-a-time")

gallery.add(
    figures.table(
        "one-node-one-shape",
        ["the node in the tree", "what the generator does with it", "and that is the whole rule"],
        [
            ["BinOp", "visit left, visit right, emit the operator", "3 lines of C"],
            ["BoolOp", "visit each, jump past the rest if decided", "no operator is emitted"],
            ["Compare", "the same, with a copy kept on the stack", "one node, many jumps"],
            ["Name", "ask the symbol table, emit the load it names", "F05 already decided"],
            ["Assign", "visit the value, then visit the targets", "in that order, always"],
        ],
        title="Every node kind has a function, and the function only looks at that node",
        caption="Nothing here consults what came before or what comes after. That is why the output needs cleaning up later.",
        tones=["focus", "focus", "quiet", "focus", "focus"],
    )
)


gallery.add(
    figures.compare(
        "there-is-no-and",
        (
            "what you wrote",
            [
                "return a and b",
                "one operator",
                "one BoolOp node",
                "a rule you learned as short circuiting",
            ],
        ),
        (
            "what came out",
            [
                "load a, copy it, ask if it is true",
                "jump past the rest if it is not",
                "throw the copy away, load b",
                "no instruction named AND anywhere",
            ],
        ),
        title="Short circuiting is not a feature of the interpreter",
        verdict="There is no and opcode and never was. The behaviour is a jump the code generator wrote for you.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.flow(
        "value-before-target",
        [
            "box[key] = value",
            "visit the value first",
            "then visit the target",
            "LOAD value, LOAD box, LOAD key, STORE_SUBSCR",
        ],
        title="Why the right hand side of an assignment runs before the left",
        labels=[
            "one line of C, before the loop",
            "the loop over the targets",
        ],
        tones=["input", "focus", "focus", "durable"],
    )
)


gallery.add(
    figures.table(
        "only-the-name-changes",
        ["where base + 1 was written", "what F05 said about base", "what the generator emitted"],
        [
            ["at module level", "GLOBAL_IMPLICIT", "LOAD_NAME"],
            ["inside a function", "LOCAL", "LOAD_FAST"],
            ["in a nested function", "FREE", "LOAD_DEREF"],
        ],
        title="The same expression three times, and only one instruction moves",
        caption="The addition is identical in all three. The generator asked the symbol table and emitted what it said.",
        tones=["quiet", "quiet", "focus"],
    )
)


gallery.add(
    figures.compare(
        "not-clever-on-purpose",
        (
            "what the code generator emits",
            [
                "load the constant False",
                "TO_BOOL, then a jump",
                "the whole dead branch",
                "12 instructions",
            ],
        ),
        (
            "what is left after the optimizer",
            [
                "nothing about False at all",
                "no jump, no test",
                "no dead branch",
                "6 instructions",
            ],
        ),
        title="if False, and the generator emits every word of it anyway",
        verdict="Being straightforward is the job. Working out that a branch can never run is a question about a graph, and that is the next lesson.",
        verdict_tone="warning",
    )
)


gallery.add(
    figures.stack(
        "instructions-with-no-line",
        [
            "MAKE_CELL, for a local somebody nested reads",
            "COPY_FREE_VARS, for the other end of that wire",
            "RESUME, where a tracer or a debugger can get in",
            "the return None nobody wrote at the end",
        ],
        title="Four instructions in your function that came from no line of your program",
        note="dis prints a dash instead of a line number for the first two, because there is no line to print.",
    )
)


raise SystemExit(gallery.save())
