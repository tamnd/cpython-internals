#!/usr/bin/env python
"""The diagrams for O09, how an int is stored and what that costs.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `thirty-bit-digits`. An int is a sign, a count and an array of
digits in base 2**30, and every surprising thing about Python integers follows from that.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("o09-arrays-of-thirty-bit-digits")

gallery.add(
    figures.table(
        "thirty-bit-digits",
        ["the number", "digits it needs", "bytes it costs"],
        [
            ["0", "none stored, room for one", "28"],
            ["1", "1", "28"],
            ["2**30 - 1", "1", "28"],
            ["2**30", "2", "32"],
            ["2**60", "3", "36"],
            ["2**90", "4", "40"],
        ],
        title="An int grows one digit at a time, and a digit is 30 bits",
        caption="Four bytes per digit, and the first one comes free with the object.",
        tones=["quiet", "focus", "focus", "warning", "quiet", "quiet"],
    )
)


gallery.add(
    figures.stack(
        "an-int-top-to-bottom",
        [
            "the object header, from O01",
            "lv_tag: the digit count, a flag and the sign",
            "digit 0, the least significant 30 bits",
            "digit 1",
            "and so on, as many as the number needs",
        ],
        title="Every int, from the smallest to the largest",
        note="The digits are stored least significant first, which is the opposite of how you "
        "write a number down.",
    )
)


gallery.add(
    figures.spans(
        "whats-in-the-tag",
        "000000001100",
        [
            (0, 9, "digit count"),
            (9, 10, "shared int"),
            (10, 12, "sign"),
        ],
        title="The tag for the number 5, as bits",
        caption="A tag below 16 means one digit and not negative.",
    )
)


gallery.add(
    figures.compare(
        "the-ones-made-for-you",
        (
            "-5 through 1024",
            [
                "made once, at startup",
                "handed out by every operation",
                "immortal, so never refcounted",
                "x is y is true for two of them",
            ],
        ),
        (
            "everything else",
            [
                "allocated when you make it",
                "a fresh object each time",
                "refcounted like anything else",
                "x is y is false, x == y is true",
            ],
        ),
        title="Two kinds of int, and the only difference is how big",
        verdict="The range was 256 up to 3.14 and is 1024 from 3.15, so never write code that "
        "depends on it.",
        verdict_tone="warning",
    )
)


gallery.add(
    figures.bars(
        "two-ways-to-multiply",
        [
            ("70 digits, either way", 4900),
            ("140, schoolbook", 19600),
            ("140, karatsuba", 13690),
            ("280, schoolbook", 78400),
            ("280, karatsuba", 40131),
        ],
        unit="digit multiplies",
        title="Where splitting the number in half starts paying",
        caption="Below 70 digits CPython does not bother.",
        width=460,
        tones=["quiet", "warning", "focus", "warning", "focus"],
    )
)


gallery.add(
    figures.table(
        "why-str-has-a-limit",
        ["what you ask for", "what it costs"],
        [
            ["int in binary, len or bit_length", "linear, no limit"],
            ["hex, oct, bin", "linear, no limit"],
            ["str or int of a decimal string", "quadratic, capped at 4300 digits"],
        ],
        title="Only one of these is slow, and only one of them has a limit",
        caption="Base 10 is not a power of two, so converting means dividing, over and over.",
        tones=["quiet", "quiet", "warning"],
    )
)


raise SystemExit(gallery.save())
