#!/usr/bin/env python
"""The diagrams for R06, the three doors into the C API.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The order follows the lesson. The three directories first, then the one macro that opens or
closes the second door, then what a limited build gives up, then how the naming convention
lines up against the directories, and last the sweep that shows none of it survives the build.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("r06-the-c-api-tiers")

gallery.add(
    figures.nest(
        "three-doors",
        (
            "Include/internal, 148 files, needs Py_BUILD_CORE",
            [
                (
                    "Include/cpython, 63 files, needs Py_LIMITED_API to be undefined",
                    [("Include, 79 files, anybody may use these", [])],
                )
            ],
        ),
        title="The C API is three directories, one inside the next",
        caption="An extension gets the inner ring. CPython itself gets all three.",
    )
)


gallery.add(
    figures.table(
        "who-can-see-what",
        ["tier", "directory", "what opens it", "how the names look", "how long it lasts"],
        [
            ["public", "Include/", "always open", "PyList_Append", "PEP 387"],
            [
                "cpython only",
                "Include/cpython/",
                "Py_LIMITED_API undefined",
                "PyUnstable_Code_New",
                "one release",
            ],
            [
                "internal",
                "Include/internal/",
                "Py_BUILD_CORE defined",
                "_PyDict_SizeOf",
                "no promise",
            ],
        ],
        title="The three tiers, and what each one asks of you",
        caption="The middle row is the one most extensions actually live in without noticing.",
        tones=["durable", "intermediate", "warning"],
    )
)


gallery.add(
    figures.flow(
        "the-gate",
        [
            "you include Python.h",
            "is Py_LIMITED_API defined",
            "no, so pull in cpython/object.h",
            "yes, so skip it",
        ],
        title="How the second door opens and closes",
        tones=["input", "focus", "durable", "warning"],
        labels=("", "one macro", "the whole struct", "an opaque pointer"),
    )
)


gallery.add(
    figures.compare(
        "what-limited-costs",
        (
            "an ordinary build",
            [
                "PyObject has fields",
                "Py_DECREF is a decrement",
                "Py_TYPE reads ob_type",
                "recompile for every minor release",
            ],
        ),
        (
            "a limited build",
            [
                "PyObject is an opaque type",
                "Py_DECREF calls _Py_DecRef",
                "Py_TYPE calls Py_TYPE",
                "one build runs on many releases",
            ],
        ),
        title="What defining Py_LIMITED_API actually changes",
        verdict="It takes away the layout, not the functions. Every field read becomes a call.",
    )
)


gallery.add(
    figures.table(
        "names-against-tiers",
        ["tier", "plain Py names", "PyUnstable names", "underscore names"],
        [
            ["Include/", "752", "1", "17"],
            ["Include/cpython/", "322", "33", "90"],
            ["Include/internal/", "8", "0", "522"],
        ],
        title="The naming convention against the directory it sits in",
        caption="Close, but not the same thing. The 17 in the top right are what public macros expand to.",
        tones=["durable", "intermediate", "warning"],
    )
)


gallery.add(
    figures.bars(
        "what-leaves-the-binary",
        [
            ["internal, spelled PyAPI_FUNC", 93.0],
            ["internal, spelled plain extern", 0.4],
        ],
        unit="percent",
        title="How much of the private C API the linker hands out",
        caption="Both spellings sit in the same headers, often two lines apart.",
        tones=["warning", "durable"],
        width=460,
    )
)


raise SystemExit(gallery.save())
