#!/usr/bin/env python
"""The diagrams for O01, the object header read one field at a time.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `the-first-sixteen-bytes`. Everybody learns the header as two
fields, a count and a type pointer, and that is close enough until you look at the bytes. The
count is thirty two bits, not sixty four, and the rest of that word is doing other jobs.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("o01-the-header-byte-by-byte")

gallery.add(
    figures.stack(
        "the-first-sixteen-bytes",
        [
            "bytes 0 to 3, ob_refcnt, the count, thirty two bits of it",
            "bytes 4 to 5, ob_overflow, a name with no users yet",
            "bytes 6 to 7, ob_flags, sixteen bits, three of them defined",
            "bytes 8 to 15, ob_type, one pointer to the type object",
            "byte 16 onwards, whatever this particular type needs",
        ],
        title="What every object in a running Python starts with",
        note="Two fields is the usual summary, and the first of the two is really three.",
    )
)


gallery.add(
    figures.spans(
        "three-fields-in-one-word",
        "0005 0000 c0000000",
        [
            (0, 4, "ob_flags is 5"),
            (5, 9, "ob_overflow is 0"),
            (10, 18, "ob_refcnt is 3 << 30"),
        ],
        title="The first word of None, written the way you would read a number",
        caption="Bits 48 and up are flags, the middle sixteen bits are named and unused, and the bottom half is the count.",
    )
)


gallery.add(
    figures.table(
        "how-far-off-you-can-be",
        ["value", "the name in the source", "what it means"],
        [
            ["0", "nothing holds this", "the object is about to be freed"],
            ["2 ** 31", "_Py_IMMORTAL_MINIMUM_REFCNT", "at or above this, treated as immortal"],
            ["3 << 30", "_Py_IMMORTAL_INITIAL_REFCNT", "where an immortal object starts"],
            [
                "2 ** 32",
                "the top of a thirty two bit field",
                "increments stop here rather than wrap",
            ],
        ],
        title="Why an immortal object starts in the middle and not at the top",
        caption="An old extension can be a billion out either way and the object is still immortal.",
        tones=["quiet", "focus", "focus", "quiet"],
    )
)


gallery.add(
    figures.compare(
        "two-ways-to-become-immortal",
        (
            "built into the binary",
            [
                "a static PyObject in the C source",
                "ob_flags is 5, so both bits are on",
                "None, True, small ints, every type",
                "and the identifiers CPython ships",
            ],
        ),
        (
            "promoted while running",
            [
                "_Py_SetImmortal parks the count",
                "ob_flags is 1, immortal bit only",
                "sys.intern does not do this",
                "nor does anything you can call",
            ],
        ),
        title="Immortal by construction, and immortal by promotion",
        verdict="Not decoration. Shutting down frees the promoted ones and leaves the static ones alone.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.table(
        "where-a-length-lives",
        ["type", "the third word", "how len gets it"],
        [
            ["tuple", "ob_size", "a PyVarObject, read straight out"],
            ["list", "ob_size", "the length, and not the capacity"],
            ["bytes", "ob_size", "a PyVarObject too"],
            ["str", "length", "not a PyVarObject, same offset anyway"],
            ["int", "lv_tag", "sign and digit count packed together"],
            ["object, float", "there is none", "sixteen and twenty four bytes, and they stop"],
        ],
        title="The third word, for the types that have one",
        caption="Py_SIZE asserts the type is not an int and not a bool, because those two moved their length elsewhere.",
        tones=["quiet", "focus", "quiet", "focus", "focus", "warning"],
    )
)


gallery.add(
    figures.compare(
        "the-same-header-wider",
        (
            "ordinary build, sixteen bytes",
            [
                "ob_refcnt, thirty two bits",
                "ob_overflow, sixteen bits",
                "ob_flags, sixteen bits",
                "ob_type, one pointer",
            ],
        ),
        (
            "free threaded build, thirty two bytes",
            [
                "ob_tid, which thread owns it",
                "ob_flags, and a one byte mutex",
                "ob_gc_bits",
                "ob_ref_local and ob_ref_shared",
                "ob_type, one pointer",
            ],
        ),
        title="One object, two headers, and the choice is made at build time",
        verdict="Every object costs sixteen more bytes so that two threads can hold the same one without fighting over a cache line.",
        verdict_tone="focus",
    )
)


raise SystemExit(gallery.save())
