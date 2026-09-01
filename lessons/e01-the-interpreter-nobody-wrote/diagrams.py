#!/usr/bin/env python
"""The diagrams for E01, the instruction DSL and the generators.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `one-file-many-outputs`. Seven files, one source, and the
smallest of them is already sitting on the reader's machine.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("e01-the-interpreter-nobody-wrote")

gallery.add(
    figures.flow(
        "where-the-interpreter-comes-from",
        [
            "someone writes an instruction in Python/bytecodes.c",
            "Tools/cases_generator reads it as a small language",
            "seven files are written out",
            "the C compiler builds the eval loop from those",
        ],
        title="Nobody types the eval loop",
        labels=[
            "six thousand lines that are not quite C",
            "a parser, then one script per output",
            "checked in, so you can read them",
        ],
        tones=["input", "focus", "durable", "quiet"],
    )
)


gallery.add(
    figures.table(
        "one-file-many-outputs",
        ["file", "what it holds", "lines"],
        [
            ["Python/generated_cases.c.h", "the tier one eval loop", "13292"],
            ["Python/executor_cases.c.h", "the tier two interpreter", "24443"],
            ["Python/optimizer_cases.c.h", "the abstract interpreter", "5837"],
            ["pycore_opcode_metadata.h", "the tables the C code reads", "2171"],
            ["pycore_uop_ids.h", "the numbers for the small operations", "1452"],
            ["Python/opcode_targets.h", "the jump table for dispatch", "1295"],
            ["Lib/_opcode_metadata.py", "the tables Python reads", "387"],
        ],
        title="What 6725 lines of instruction definitions turn into",
        caption="Just under fifty thousand lines out. The last row is already on your machine.",
        tones=["focus", "quiet", "quiet", "quiet", "quiet", "quiet", "focus"],
    )
)


gallery.add(
    figures.spans(
        "what-one-definition-carries",
        "inst(UNARY_NOT, (value -- res))",
        [
            (0, 4, "what kind of thing this is"),
            (5, 14, "the name it will be known by"),
            (16, 30, "what it takes and what it leaves"),
        ],
        title="One line of the language, and everything the generators need",
        caption="The body underneath is plain C. This first line is not.",
    )
)


gallery.add(
    figures.table(
        "the-arrow-is-the-stack-effect",
        ["written in the definition", "takes", "leaves", "effect"],
        [
            ["(value --)", "1", "0", "-1"],
            ["(-- res)", "0", "1", "+1"],
            ["(value -- res)", "1", "1", "0"],
            ["(obj -- obj, len)", "1", "2", "+1"],
            ["(receiver, index_or_null, value -- val)", "3", "1", "-2"],
        ],
        title="Count the names on each side and you have the number",
        caption="No table anywhere holds these. They are read straight off the arrow.",
        tones=["quiet", "quiet", "focus", "quiet", "quiet"],
    )
)


gallery.add(
    figures.flow(
        "where-the-cache-slots-come-from",
        [
            "the macro line adds up counter/1 and unused/2",
            "the generator totals them and writes 3",
            "the compiler leaves three CACHE words after TO_BOOL",
            "and dis skips exactly three when it walks the code",
        ],
        title="Why every TO_BOOL is followed by three empty instructions",
        labels=[
            "written once, in the definition",
            "into the C table and the Python one",
            "six bytes of scratch space",
        ],
        tones=["input", "focus", "durable", "quiet"],
    )
)


gallery.add(
    figures.compare(
        "generated-against-written-by-hand",
        (
            "generated",
            [
                "opmap and every specialized name",
                "the stack effect of each opcode",
                "which family a specialization is in",
                "cannot drift from the interpreter",
            ],
        ),
        (
            "still typed by a person",
            [
                "the cache layout in Lib/opcode.py",
                "the list of common constants",
                "with a comment saying keep in sync",
                "can drift, and you find out late",
            ],
        ),
        title="What is left over after the generators have run",
        verdict="Two hand written tables, and both are mirrors of something generated.",
        verdict_tone="warning",
    )
)


raise SystemExit(gallery.save())
