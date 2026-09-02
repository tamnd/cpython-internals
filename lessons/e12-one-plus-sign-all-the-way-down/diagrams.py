#!/usr/bin/env python
"""The diagrams for E12, one plus sign followed through every layer of the interpreter.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

`what-the-macro-line-says` is the one to look at twice. Every other scene here is a
consequence of that single line of the instruction DSL, and so is most of the lesson.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("e12-one-plus-sign-all-the-way-down")

gallery.add(
    figures.flow(
        "one-plus-sign-six-layers",
        [
            "a plus sign in your source",
            "one BINARY_OP with five cache slots",
            "BINARY_OP_ADD_INT written over it",
            "three micro operations in a trace",
            "one micro operation, every time after",
            "a few hundred bytes of machine code",
        ],
        title="What one character turns into",
        labels=[
            "the compiler",
            "a few hundred trips",
            "the trace recorder",
            "the optimizer",
            "copy and patch",
        ],
        tones=["input", "intermediate", "focus", "focus", "durable", "warning"],
    )
)


gallery.add(
    figures.table(
        "what-the-macro-line-says",
        ["piece of the macro line", "what it is for", "how you can see it"],
        [
            ["_GUARD_TOS_INT", "check the right operand", "give it a float and watch"],
            ["_GUARD_NOS_INT", "check the left operand", "same, on the other side"],
            ["unused/5", "five slots of inline cache", "a gap in the offsets"],
            ["_BINARY_OP_ADD_INT", "the addition itself", "in the trace"],
            ["_POP_TOP_INT", "drop the left operand", "in the trace"],
            ["_POP_TOP_INT", "drop the right operand", "in the trace"],
        ],
        title="macro(BINARY_OP_ADD_INT), taken apart",
        caption="One line of the instruction DSL, and every part of it shows up somewhere.",
        tones=["focus", "focus", "durable", "quiet", "quiet", "quiet"],
    )
)


gallery.add(
    figures.table(
        "the-decision-tree",
        ["what you add", "what it becomes", "why"],
        [
            ["1 + 2", "BINARY_OP_ADD_INT", "both small ints"],
            ["1.5 + 2.5", "BINARY_OP_ADD_FLOAT", "both floats"],
            ["'a' + 'b'", "BINARY_OP_ADD_UNICODE", "both strings"],
            ["s = s + 'b'", "BINARY_OP_INPLACE_ADD_UNICODE", "the result goes back to s"],
            ["1 + 2.5", "BINARY_OP_EXTEND", "the two types differ"],
            ["9 / 4", "BINARY_OP", "division has no fast path"],
        ],
        title="The same plus sign, six answers",
        caption="Decided once, a few hundred trips in, by looking at what actually turned up.",
        tones=["focus", "focus", "focus", "durable", "quiet", "quiet"],
    )
)


gallery.add(
    figures.compare(
        "first-time-and-every-time-after",
        (
            "the first addition",
            [
                "_GUARD_TOS_OVERFLOWED",
                "_GUARD_NOS_INT",
                "_BINARY_OP_ADD_INT",
            ],
        ),
        (
            "the next two",
            [
                "_BINARY_OP_ADD_INT_INPLACE",
            ],
        ),
        title="total = total + i + i + i, as micro operations",
        verdict="The guards are gone, and so is the copy, because the result has nobody else holding it.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.table(
        "the-same-plus-in-six-places",
        ["where you are looking", "what it is called there", "how big it is"],
        [
            ["your source", "a plus sign", "1 character"],
            ["Python/bytecodes.c", "macro(BINARY_OP)", "1 line"],
            ["the code object", "BINARY_OP and its cache", "12 bytes"],
            ["after it warms up", "BINARY_OP_ADD_INT", "the same 12 bytes"],
            ["in a trace", "three micro operations", "the first one only"],
            ["machine code", "part of one stencil run", "a few hundred bytes"],
        ],
        title="Six names for one addition",
        caption="Nothing was added along the way. Each layer is the one above it, spelled out.",
        tones=["input", "input", "focus", "focus", "durable", "warning"],
    )
)


gallery.add(
    figures.stack(
        "all-the-way-down",
        [
            "machine code, pasted together while you wait",
            "micro operations, most of them deleted",
            "a trace, recorded from one real trip",
            "a specialized instruction, written over the first",
            "one instruction and five cache slots",
            "a plus sign",
        ],
        title="The whole stack, newest at the top",
        note="Every layer below the first was built by the layer above it noticing something.",
    )
)


raise SystemExit(gallery.save())
