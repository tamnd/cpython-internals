#!/usr/bin/env python
"""The diagrams for F10, inside a code object.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `one-array-four-views`. Everything else follows from a code
object being a plain record with no values in it, whose most confusing part is that four of its
attributes are not stored at all but computed from one array and one string of tag bytes.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("f10-inside-a-code-object")

gallery.add(
    figures.table(
        "one-array-four-views",
        ["slot", "name", "tagged local", "tagged cell"],
        [
            ["0", "a", "yes", "yes"],
            ["1", "b", "yes", "no"],
            ["5", "inner", "yes", "no"],
            ["6", "n", "no", "yes"],
        ],
        title="Seven slots in one array, and co_varnames plus co_cellvars adds up to eight",
        caption="A parameter that a nested function reads is tagged twice, so it turns up in two tuples and is counted twice.",
        tones=["focus", "quiet", "quiet", "focus"],
    )
)


gallery.add(
    figures.tree(
        "boxes-inside-boxes",
        (
            "the module",
            [
                ("the class body", ["a method"]),
                ("a function", ["the listcomp is inlined, so no box"]),
            ],
        ),
        title="Compiling one file gives you one code object, with the rest inside it",
        caption="A nested definition ends up in the outer object's constants, next to the numbers and strings.",
    )
)


gallery.add(
    figures.flow(
        "a-parameter-becomes-a-cell",
        [
            "a arrives in slot 0, an ordinary parameter",
            "MAKE_CELL 0 runs before anything else",
            "slot 0 now holds a cell with a inside it",
            "the nested function gets the cell, not the value",
        ],
        title="Why the first two instructions of a function can run before line one",
        labels=[
            "tagged both local and cell",
            "which is what makes the closure work",
        ],
        tones=["input", "focus", "intermediate", "durable"],
    )
)


gallery.add(
    figures.compare(
        "what-equality-looks-at",
        (
            "compared",
            [
                "the name and the argument counts",
                "the flags and the first line number",
                "the bytecode, in its unspecialized form",
                "the constants, names and side tables",
            ],
        ),
        (
            "not compared",
            [
                "the file it was compiled from",
                "anything the specializer wrote later",
                "the stack size",
                "how many times it has run",
            ],
        ),
        title="The same source compiled twice, from two different files",
        verdict="They are equal, and they hash the same. The filename is carried for tracebacks, not identity.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.stack(
        "no-values-in-here",
        [
            "co_code, the instructions",
            "co_consts, the literals and the nested code objects",
            "co_names, everything looked up by name at run time",
            "co_localsplusnames, the slots a frame will need",
            "co_flags, co_stacksize, co_firstlineno",
        ],
        title="Everything a code object holds, and none of it is a value your program computed",
        note="One code object serves every call. The values live in a frame, which is what F13 builds.",
    )
)


gallery.add(
    figures.table(
        "some-of-the-flags",
        ["bit", "name", "what it tells the interpreter"],
        [
            ["0x0001", "CO_OPTIMIZED", "locals are array slots, not a dictionary"],
            ["0x0004", "CO_VARARGS", "there is a *args parameter"],
            ["0x0020", "CO_GENERATOR", "calling this returns a generator"],
            ["0x8000000", "CO_METHOD", "this was defined inside a class body"],
        ],
        title="co_flags is one integer, and every bit in it was decided at compile time",
        caption="A module body and a class body have no flags set at all. Only functions get the interesting ones.",
        tones=["focus", "quiet", "quiet", "focus"],
    )
)


raise SystemExit(gallery.save())
