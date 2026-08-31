#!/usr/bin/env python
"""The diagrams for F12, marshal and the .pyc file.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `the-round-trip`. Everything from F01 onwards has been one
direction, source text turning into a code object, and this is the stage where the code object
turns into bytes on disk and then back into the same code object without going through any of
it again. That is the whole reason importing a module the second time is fast.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("f12-what-ends-up-on-disk")

gallery.add(
    figures.pipeline(
        "the-round-trip",
        [
            ("greet.py", "text, as you typed it"),
            ("a code object", "eleven stages of work"),
            ("greet.pyc", "a header and one blob"),
            ("a code object", "read straight back"),
        ],
        highlight=(1, 3),
        title="The second import skips the eleven stages in the middle",
        caption="The two ends are equal code objects, and getting from the third box to the fourth is a read and a walk.",
    )
)


gallery.add(
    figures.stack(
        "what-a-pyc-holds",
        [
            "bytes 0 to 3, the magic number for this exact bytecode",
            "bytes 4 to 7, flags, and bit 0 decides what the next eight mean",
            "bytes 8 to 15, when the source was last written and how long it is",
            "bytes 16 onwards, one marshalled code object and nothing else",
        ],
        title="A .pyc file is a sixteen byte header and then one object",
        note="Set bit 0 of the flags and the last eight bytes hold a hash of the source instead of a timestamp.",
    )
)


gallery.add(
    figures.stack(
        "one-byte-two-jobs",
        [
            "the byte 0xda is 1101 1010",
            "the top bit is set, so put this object in the table and number it",
            "the other seven bits are 0x5a, which is the letter Z",
            "Z means a short ascii string that the interpreter had already interned",
        ],
        title="Every object starts with one byte, and that byte is doing two things",
        note="Clear the top bit and you have an ascii letter naming the type, which is why a .pyc is readable in a hex dump.",
    )
)


gallery.add(
    figures.table(
        "some-of-the-type-codes",
        ["byte", "letter", "what comes after it"],
        [
            ["0x4e", "N", "nothing, the object is None"],
            ["0x69", "i", "four bytes, a signed integer"],
            ["0x7a", "z", "one length byte, then that many ascii characters"],
            ["0x29", ")", "one length byte, then that many objects"],
            ["0x63", "c", "sixteen fields, and the first five are plain numbers"],
            ["0x72", "r", "four bytes, an index into everything seen so far"],
        ],
        title="Six of the thirty type codes, and they cover most of a .pyc",
        caption="The letters are the format. Reading marshal.c is mostly reading a switch over these.",
        tones=["quiet", "quiet", "quiet", "quiet", "focus", "focus"],
    )
)


gallery.add(
    figures.spans(
        "said-once-then-pointed-at",
        "a9 02 da 04 61 62 63 64 72 01 00 00 00",
        [
            (0, 2, "a tuple, number it"),
            (3, 5, "two items"),
            (6, 8, "a string, number it"),
            (9, 11, "four bytes"),
            (12, 23, "abcd"),
            (24, 26, "seen this one"),
            (27, 38, "it was number 1"),
        ],
        title="The tuple ('abcd', 'abcd') in thirteen bytes",
        caption="The second abcd costs five bytes, and so would a hundred character string, and so would a nested code object.",
    )
)


gallery.add(
    figures.stack(
        "sixteen-fields-in-order",
        [
            "five plain numbers: argcount, posonly, kwonly, stacksize, flags",
            "the bytecode, then the constants, then the names",
            "localsplusnames and localspluskinds, the array F10 pulled apart",
            "filename, name, qualname, and the first line number",
            "the line table and the exception table, the two F11 decoded",
        ],
        title="What a code object looks like once it is flattened",
        note="Constants hold code objects, so this list is walked again for every function in the file.",
    )
)


raise SystemExit(gallery.save())
