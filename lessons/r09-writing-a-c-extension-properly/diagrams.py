#!/usr/bin/env python
"""The diagrams for R09, the four things a C extension owes the runtime.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The order follows the lesson. The one missing line on an error path first, then the three
boxes and what the collector can see of each, then the step that needs tp_traverse and the
short list of what tp_traverse may call, then where the two teardown hooks run, and last
what the leak hunter reports about four tests that all pass an ordinary run.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("r09-writing-a-c-extension-properly")

gallery.add(
    figures.compare(
        "the-branch-nobody-tests",
        (
            "the version with one line missing",
            [
                "pair = PyTuple_Pack(2, arg, arg)",
                "the tuple now holds two refs on arg",
                "hashing it fails, so return NULL",
                "the tuple is never freed",
            ],
        ),
        (
            "the version with the line",
            [
                "pair = PyTuple_Pack(2, arg, arg)",
                "the tuple now holds two refs on arg",
                "hashing it fails, so Py_DECREF first",
                "the tuple is freed, and lets go of arg",
            ],
        ),
        title="Two error paths that differ by one line",
        verdict="A thousand failed calls, two thousand references, and no error anybody can see.",
    )
)


gallery.add(
    figures.table(
        "three-boxes-one-cycle",
        ["the type", "collector sees it", "tp_traverse reports", "freed after a collection"],
        [
            ["Loose, no GC flag", "no", "nothing, there is none", "no"],
            ["Half, traverse forgets", "yes", "its type only", "no"],
            ["Tracked, traverse complete", "yes", "its type and its item", "yes"],
        ],
        title="One container written three ways, each put in a cycle and collected",
        caption="The flag gets you into the collector. A complete tp_traverse gets you back out.",
        tones=["warning", "warning", "durable"],
    )
)


gallery.add(
    figures.flow(
        "how-the-collector-uses-traverse",
        [
            "take the reference count of every candidate",
            "call tp_traverse on each of them",
            "subtract one for every visit landing inside the set",
            "whatever is still above zero is held from outside",
        ],
        title="Why an incomplete tp_traverse leaks instead of crashing",
        tones=["quiet", "focus", "focus", "durable"],
    )
)


gallery.add(
    figures.table(
        "what-traverse-may-call",
        ["what you may call in tp_traverse", "what it is for"],
        [
            ["the visit function you were handed", "reporting one reference"],
            ["Py_VISIT", "the same thing, with the null check written for you"],
            ["Py_TYPE and Py_SIZE", "reading the header, valid for this call only"],
            ["PyObject_VisitManagedDict", "reporting an instance dict the runtime owns"],
            ["PyType_HasFeature and the Check macros", "asking what kind of object this is"],
            ["the _DuringGC functions, new in 3.15", "reaching module state without side effects"],
        ],
        title="The whole list of what a tp_traverse handler is allowed to do",
        caption="Anything that can allocate, raise or run Python is not on it.",
        tones=["focus", "focus", "quiet", "quiet", "quiet", "durable"],
    )
)


gallery.add(
    figures.compare(
        "where-the-two-hooks-run",
        (
            "the count reached zero on its own",
            [
                "tp_dealloc is called",
                "it calls tp_finalize first",
                "then it frees the memory",
            ],
        ),
        (
            "the collector found a cycle",
            [
                "tp_finalize runs on everything first",
                "then tp_clear breaks the links",
                "counts fall, and tp_dealloc follows",
            ],
        ),
        title="The two ways your object dies, and the one hook that runs either way",
        verdict="tp_finalize runs at most once per object, and the runtime keeps that flag for you.",
        verdict_tone="durable",
    )
)


gallery.add(
    figures.table(
        "what-the-hunter-counts",
        ["the test", "an ordinary run", "six runs with the hunter"],
        [
            ["holds nothing", "passed", "nothing left behind"],
            ["fills a cache once", "passed", "[1, 0, 0] references, called fine"],
            ["appends to a global list", "passed", "[1, 1, 1] references, a failure"],
            ["duplicates a file handle", "passed", "[1, 1, 1] file descriptors, a failure"],
        ],
        title="Four small tests, and the two verdicts each one gets",
        caption="Every one of them passes the run you do before you open a pull request.",
        tones=["durable", "intermediate", "warning", "warning"],
    )
)


raise SystemExit(gallery.save())
