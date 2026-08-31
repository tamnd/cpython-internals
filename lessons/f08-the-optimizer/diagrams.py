#!/usr/bin/env python
"""The diagrams for F08, the optimizer.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `folded-or-not`. Everything else follows from the optimizer being
a set of small, cautious rewrites with hard numbers in them rather than anything clever: four
size limits, a copy budget of four instructions, and an operand that has to fit in four bits.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("f08-the-optimizer")

gallery.add(
    figures.table(
        "folded-or-not",
        ["what you wrote", "what ends up in the file", "why"],
        [
            ["2 ** 64", "the answer, all 20 digits", "its estimate lands on 128"],
            ["2 ** 65", "a 2, a 65 and a power", "one over, so it gives up"],
            ["'ab' * 2048", "the finished 4096 character string", "exactly the limit"],
            ["'ab' * 2049", "the pieces, and the work left to do", "one character over"],
        ],
        title="The compiler will do your arithmetic, up to a point that is written down",
        caption="Folding a huge number would bloat the file and slow the import, so four numbers say when to stop.",
        tones=["focus", "warning", "focus", "warning"],
    )
)


gallery.add(
    figures.table(
        "four-numbers",
        ["the limit", "its value", "what it stops"],
        [
            ["MAX_INT_SIZE", "128 bits", "2 ** 65 and 1 << 128"],
            ["MAX_COLLECTION_SIZE", "256 items", "(1,) * 257"],
            ["MAX_STR_SIZE", "4096 characters", "'ab' * 2049"],
            ["MAX_TOTAL_ITEMS", "1024 items", "a tuple of tuples, repeated"],
        ],
        title="Four constants, near the top of the folding code, and that is the whole policy",
        caption="No heuristics and nothing adaptive. Someone picked four numbers and wrote them down where you can read them.",
        tones=["focus", "quiet", "focus", "quiet"],
    )
)


gallery.add(
    figures.compare(
        "slot-zero-is-special",
        (
            "a module with no docstring",
            [
                "x = 1000 * 1000",
                "1000 goes into the constants first",
                "the fold makes it useless",
                "and it is still there: (1000, 1000000)",
            ],
        ),
        (
            "the same module with a docstring",
            [
                "the docstring claims slot zero",
                "1000 lands in slot one",
                "the fold makes it useless",
                "and it goes: ('A module.', 1000000)",
            ],
        ),
        title="Why a leftover constant sometimes survives and sometimes does not",
        verdict="The pass that removes unused constants always keeps slot zero, because slot zero might be the docstring. One comment in the source, and you can see it from Python.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.compare(
        "copy-instead-of-jump",
        (
            "what the code generator emitted",
            [
                "break jumps to the end",
                "the end loads 1 and returns",
                "two instructions, reached by a jump",
                "one block, two ways in",
            ],
        ),
        (
            "what the optimizer left",
            [
                "no jump at all",
                "load 1 and return, written out twice",
                "four instructions instead of three",
                "two blocks, one way in each",
            ],
        ),
        title="A jump worth deleting, even though the code gets longer",
        verdict="The budget is four instructions, and the target has to leave the function. Copying a small ending is cheaper than jumping to it.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.flow(
        "two-into-one",
        [
            "LOAD_FAST a, LOAD_FAST b, next to each other",
            "are they on the same line of source",
            "are both slot numbers under 16",
            "LOAD_FAST_LOAD_FAST, one instruction",
        ],
        title="Two instructions become one, if two small conditions hold",
        labels=[
            "put a line break between them and you lose it",
            "the two slots share one operand byte",
        ],
        tones=["input", "quiet", "quiet", "durable"],
    )
)


gallery.add(
    figures.compare(
        "proving-it-is-set",
        (
            "the compiler can prove it",
            [
                "every path here assigns x first",
                "so the slot cannot be empty",
                "LOAD_FAST, no check",
                "nothing to test at runtime",
            ],
        ),
        (
            "the compiler cannot",
            [
                "one path here skips the assignment",
                "so the slot might be empty",
                "LOAD_FAST_CHECK",
                "and a possible UnboundLocalError",
            ],
        ),
        title="The same name, read twice in one function, compiled two different ways",
        verdict="This is a walk over the graph tracking which locals are definitely set. Where the answer is yes, the check is free to remove.",
        verdict_tone="focus",
    )
)


raise SystemExit(gallery.save())
