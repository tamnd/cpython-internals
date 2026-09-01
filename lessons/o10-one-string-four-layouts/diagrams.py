#!/usr/bin/env python
"""The diagrams for O10, the four storage layouts behind str.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `the-widest-character-decides`. A string picks its storage
from the single largest code point in it, and everything else about the object follows.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("o10-one-string-four-layouts")

gallery.add(
    figures.table(
        "the-widest-character-decides",
        ["widest character", "bytes per character", "struct used", "example"],
        [
            ["up to U+007F", "1", "PyASCIIObject", "hello"],
            ["up to U+00FF", "1", "PyCompactUnicodeObject", "cafe with an accent"],
            ["up to U+FFFF", "2", "PyCompactUnicodeObject", "most CJK text"],
            ["above U+FFFF", "4", "PyCompactUnicodeObject", "emoji"],
        ],
        title="One character sets the layout for the whole string",
        caption="Add one emoji to an ASCII string and every character in it becomes 4 bytes.",
        tones=["focus", "quiet", "quiet", "warning"],
    )
)


gallery.add(
    figures.stack(
        "inside-a-string-object",
        [
            "the object header, from O01",
            "length, the number of characters, not bytes",
            "hash, or -1 if nobody has asked yet",
            "kind, ascii, compact and interned, packed into four bytes",
            "the characters themselves, right here, plus a trailing zero",
        ],
        title="A short ASCII string, top to bottom",
        note="Forty bytes of header and then the text. One allocation, not two.",
    )
)


gallery.add(
    figures.flow(
        "how-a-string-gets-built",
        [
            "scan the text for the largest code point",
            "pick 1, 2 or 4 bytes per character",
            "one malloc for the struct and the characters together",
            "copy the characters in",
        ],
        title="What happens when a string is created",
        labels=[
            "find_maxchar_surrogates",
            "PyUnicode_New picks the kind",
            "so the text is never a second block",
        ],
        tones=["input", "focus", "focus", "durable"],
    )
)


gallery.add(
    figures.bars(
        "what-a-hundred-characters-cost",
        [
            ("ASCII", 141),
            ("Latin-1", 157),
            ("BMP, 2 bytes", 258),
            ("astral, 4 bytes", 460),
        ],
        unit="bytes for 100 characters",
        title="The same length, four layouts",
        caption="Measured with sys.getsizeof on a 64 bit build.",
        tones=["focus", "quiet", "quiet", "warning"],
        width=460,
    )
)


gallery.add(
    figures.compare(
        "the-utf8-copy",
        (
            "an ASCII string",
            [
                "the characters are already UTF-8",
                "the utf8 pointer aims at them",
                "asking for it costs nothing",
                "and the object never grows",
            ],
        ),
        (
            "anything wider",
            [
                "the stored form is not UTF-8",
                "so a copy has to be made",
                "it is built when C code first asks",
                "and kept on the object from then on",
            ],
        ),
        title="Where the UTF-8 bytes come from",
        verdict="The object can grow without the text changing.",
        verdict_tone="warning",
    )
)


gallery.add(
    figures.table(
        "who-ends-up-in-the-table",
        ["the string", "interned", "immortal"],
        [
            ["a name in your source, like obj.value", "yes", "yes"],
            ["a constant that looks like an identifier", "yes", "no"],
            ["a constant with a space or punctuation", "no", "no"],
            ["a one character Latin-1 string", "yes", "yes"],
            ["anything you built at runtime", "no", "no"],
        ],
        title="Which strings the interpreter keeps only one of",
        caption="Only the first four make `is` reliable, and only by accident of how they were made.",
        tones=["focus", "focus", "quiet", "durable", "quiet"],
    )
)


raise SystemExit(gallery.save())
