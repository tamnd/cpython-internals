#!/usr/bin/env python
"""The diagrams for F11, the line table and the exception table.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `nothing-in-the-hot-path`. Both tables exist for the same
reason: something that is needed only when a program goes wrong should cost nothing while it
is going right. So both live beside the bytecode rather than in it, and both are read only by
code that has already stopped running your instructions.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("f11-two-tables-on-the-side")

gallery.add(
    figures.compare(
        "nothing-in-the-hot-path",
        (
            "in co_code, runs every time",
            [
                "the loop that adds the numbers up",
                "and that is the whole list",
                "no instruction marks the try",
                "no instruction unmarks it",
            ],
        ),
        (
            "beside co_code, read on the way out",
            [
                "co_exceptiontable, range to handler",
                "co_linetable, line and columns",
                "looked at when something raises",
                "and when a debugger asks",
            ],
        ),
        title="Why a try you never trip costs nothing",
        verdict="The instructions inside a try are the ones you get without it.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.stack(
        "the-first-byte-says-what-follows",
        [
            "bit 7 set, so this byte starts an entry",
            "bits 3 to 6, which of the six forms this is",
            "bits 0 to 2, how many code units it covers, less one",
            "then zero or more bytes with bit 7 clear",
        ],
        title="One byte at the front of every location entry, and it is doing three jobs",
        note="The top bit is what lets you land in the middle of the table and walk backwards to a boundary.",
    )
)


gallery.add(
    figures.table(
        "six-ways-to-say-where",
        ["code", "form", "what it stores", "bytes"],
        [
            ["0 to 9", "short", "the column, in the code and one more byte", "2"],
            ["10 to 12", "one line", "a line delta of 0, 1 or 2, and two columns", "3"],
            ["13", "no columns", "a signed line delta, nothing else", "2"],
            ["14", "long", "signed line delta, end line, both columns", "up to 25"],
            ["15", "none", "nothing at all, this instruction is from nowhere", "1"],
        ],
        title="The compiler picks the smallest form that fits",
        caption="Most instructions are on one line in the first eighty columns, which is what the two byte short form is for.",
        tones=["focus", "quiet", "quiet", "quiet", "focus"],
    )
)


gallery.add(
    figures.spans(
        "one-entry-decoded",
        "85 12 19 00",
        [
            (0, 2, "start 5, top bit set"),
            (3, 5, "size 18"),
            (6, 8, "target 25"),
            (9, 11, "depth 0, lasti off"),
        ],
        title="One entry, four bytes, and every number in code units",
        caption="That covers bytes 10 to 46, puts the handler at byte 50, and pops the stack back to nothing.",
    )
)


gallery.add(
    figures.flow(
        "how-a-raise-finds-its-handler",
        [
            "something raises at some offset",
            "look that offset up in co_exceptiontable",
            "pop the stack back to the depth in the entry",
            "jump to the target and carry on",
        ],
        title="What happens between the raise and the except",
        labels=[
            "binary search, even though entries vary in size",
            "which is why the depth is in the table",
        ],
        tones=["input", "focus", "intermediate", "durable"],
    )
)


gallery.add(
    figures.compare(
        "two-varints-in-one-file",
        (
            "the exception table",
            [
                "most significant chunk first",
                "bit 6 means another byte follows",
                "read with parse_varint",
                "so a prefix is already the big part",
            ],
        ),
        (
            "the line table",
            [
                "least significant chunk first",
                "bit 6 means another byte follows",
                "written with write_varint",
                "so it is written as it is computed",
            ],
        ),
        title="Six bits to a byte in both, and the chunks go opposite ways",
        verdict="Not an accident. The exception table is binary searched on its first number, and comparing the leading chunk first is what makes that cheap.",
        verdict_tone="focus",
    )
)


raise SystemExit(gallery.save())
