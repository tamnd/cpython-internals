#!/usr/bin/env python
"""The diagrams for F09, two bytes at a time.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `sizes-and-offsets`. Everything else follows from the last
compiler stage having exactly one hard problem: how far a jump goes depends on how big every
instruction between here and there is, and how big a jump instruction is depends on how far it
goes.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("f09-two-bytes-at-a-time")

gallery.add(
    figures.pipeline(
        "sizes-and-offsets",
        [
            ("a list of labels", "jump to the top"),
            ("sizes, then gaps", "how far is that"),
            ("gaps, then sizes", "it moved"),
            ("bytes", "co_code"),
        ],
        highlight=(2,),
        title="The last compiler stage, and the one thing it cannot get right in one pass",
        caption="Widening a jump makes the code longer, which moves the target, which can widen the jump again.",
    )
)


gallery.add(
    figures.spans(
        "every-byte-of-it",
        "8000 0000 5500 5d01 2a00 ... 2100",
        [
            (0, 4, "RESUME"),
            (5, 9, "one cache"),
            (10, 14, "LOAD_FAST_BORROW"),
            (15, 19, "LOAD_SMALL_INT"),
            (20, 24, "BINARY_OP"),
            (25, 28, "five caches"),
            (29, 33, "RETURN_VALUE"),
        ],
        title="All of def g(x): return x + 1, byte for byte",
        caption="Eleven pairs of bytes, with the five zero pairs folded up. Nothing else is in there.",
    )
)


gallery.add(
    figures.table(
        "why-the-offsets-jump",
        ["offset", "what dis prints there", "what is really there"],
        [
            ["0", "RESUME 0", "the instruction, two bytes"],
            ["2", "nothing", "a cache slot, never executed"],
            ["4", "LOAD_FAST_BORROW 0", "the instruction, two bytes"],
            ["8", "BINARY_OP 0", "the instruction, and five cache slots after it"],
        ],
        title="Why a disassembly does not count 0, 2, 4, 6",
        caption="The gaps belong to the instruction above them. They are storage, not code, and the interpreter walks straight past.",
        tones=["focus", "quiet", "focus", "focus"],
    )
)


gallery.add(
    figures.compare(
        "counting-from-where",
        (
            "counting from the jump itself",
            [
                "FOR_ITER sits at offset 14",
                "its argument is 19",
                "14 plus 19 twos is 52",
                "and there is nothing at 52",
            ],
        ),
        (
            "counting from after the fetch",
            [
                "two bytes for the instruction",
                "two more for its cache slot",
                "18 plus 19 twos is 56",
                "which is exactly where END_FOR is",
            ],
        ),
        title="A jump argument is a distance, and the question is a distance from what",
        verdict="Jump offsets are computed relative to the instruction pointer after fetching the jump instruction. Six words of comment in the source, and every off by one in a hand written disassembler.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.flow(
        "one-byte-only-reaches-255",
        [
            "the distance comes out over 255",
            "an EXTENDED_ARG goes in front, carrying the high bits",
            "which makes the function one code unit longer",
            "so work out every size and offset again",
        ],
        title="The chicken and egg in the middle of the assembler",
        labels=[
            "one byte, so 255 is the ceiling",
            "and the target just moved further away",
        ],
        tones=["input", "focus", "warning", "durable"],
    )
)


gallery.add(
    figures.flow(
        "three-things-first",
        [
            "labels turn into positions in the list",
            "JUMP becomes JUMP_FORWARD or JUMP_BACKWARD",
            "positions turn into distances in bytes",
            "and only now, write the bytes",
        ],
        title="Four steps, in this order, and the code object falls out of the last one",
        labels=[
            "a label is a name, not a place",
            "now the direction is known",
        ],
        tones=["input", "intermediate", "focus", "durable"],
    )
)


raise SystemExit(gallery.save())
