#!/usr/bin/env python
"""The diagrams for B04, reading the tree you just built.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `one-file-many-files`. Everything in the tree that a script
wrote came from somewhere, and seeing one input fan out into eight outputs is what makes a
reader stop hunting for an explanation inside a generated file.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("b04-reading-the-tree")

gallery.add(
    figures.spans(
        "a-reference-is-a-path",
        "Include/opcode_ids.h:1-4",
        [(0, 20, "which file"), (21, 24, "which lines")],
        title="Every source reference in this book is a path and a line range",
        caption="Two pieces, and your own interpreter can hand you both for anything written in Python.",
    )
)


gallery.add(
    figures.table(
        "three-kinds-of-file",
        ["kind", "how to spot it", "what to do with it"],
        [
            ["written by a person", "no banner at the top", "read it, change it, send a patch"],
            [
                "written by a script",
                "says so in the first three lines",
                "read what it was made from",
            ],
            ["copied in from elsewhere", "lives under Modules/expat or similar", "leave it alone"],
        ],
        title="Three kinds of file in the tree, and only one of them is yours",
        caption="The middle row is the one that wastes people's afternoons, and it is the easiest of the three to spot.",
        tones=["focus", "warning", "quiet"],
    )
)


gallery.add(
    figures.bars(
        "typed-and-not-typed",
        [
            ("nobody typed it", 405893),
            ("somebody typed it", 678656),
        ],
        unit="lines of C in a built tree",
        title="How much of the C came out of a script",
        caption="Measured on the tree the debug image was built from. A little over a third of it.",
        tones=["warning", "focus"],
    )
)


gallery.add(
    figures.tree(
        "one-file-many-files",
        (
            "Python/bytecodes.c",
            [
                ("opcode_id_generator.py", ["Include/opcode_ids.h"]),
                ("target_generator.py", ["Python/opcode_targets.h"]),
                ("py_metadata_generator.py", ["Lib/_opcode_metadata.py"]),
                ("tier1_generator.py", ["Python/generated_cases.c.h"]),
            ],
        ),
        title="One input, four scripts, four files, and that is a third of what regen-cases does",
        caption="Change the top box and all four move together. Change one of the bottom boxes and the next build undoes you.",
    )
)


gallery.add(
    figures.table(
        "four-ways-to-ask-why",
        ["what you have", "what to run", "what comes back"],
        [
            ["a line you distrust", "git blame -w -C -- FILE", "the commit that last touched it"],
            ["a function", "git log -L 100,140:FILE", "every commit that changed those lines"],
            ["a word or a name", 'git log -S "PyStackRef"', "the commit that introduced it"],
            ["a commit", "read its first line", "gh-NNNNN, which is the issue number"],
            [
                "an issue number",
                "github.com/python/cpython/issues/N",
                "the argument, and who lost it",
            ],
        ],
        title="Going from a line of C to the argument that put it there",
        caption="The last two rows are the point. Every commit message names an issue, so any line leads to a discussion.",
        tones=["quiet", "focus", "focus", "durable", "durable"],
    )
)


gallery.add(
    figures.table(
        "where-the-prose-is",
        ["place", "written for", "good for"],
        [
            ["Doc/", "people using Python", "what a function promises"],
            ["InternalDocs/", "people changing CPython", "how a subsystem fits together"],
            ["the devguide", "new contributors", "how to build, test and submit"],
            ["Misc/NEWS.d/", "release notes", "what changed in a version, with issue numbers"],
            ["PEPs", "the decision", "why the language works this way at all"],
        ],
        title="Five places CPython keeps prose, and what each one answers",
        caption="If you are stuck on why rather than what, you are almost always in the wrong one of these.",
        tones=["quiet", "focus", "quiet", "intermediate", "durable"],
    )
)


raise SystemExit(gallery.save())
