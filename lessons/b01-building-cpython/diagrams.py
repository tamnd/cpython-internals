#!/usr/bin/env python
"""The diagrams for B01, building CPython.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one doing the most work is `three-ways-in`, because the whole argument of this lesson is
that a reader who cannot compile CPython today is not locked out of anything, and a picture
of the three routes makes that easier to believe than a paragraph does.
"""

from nbdiagram import Gallery, figures, stages

gallery = Gallery("b01-building-cpython")

gallery.add(
    stages.map(
        "where-we-are",
        title="The pipeline, with nothing highlighted",
        caption="This lesson is not one of the boxes. It is about the binary that runs all of them.",
    )
)


gallery.add(
    figures.flow(
        "what-a-build-is",
        [
            "configure.ac",
            "configure",
            "Makefile and pyconfig.h",
            "a few hundred .o files",
            "python",
        ],
        title="Five files deep, and only two of them are written by hand",
        labels=[
            "autoconf, run by a CPython developer",
            "you run this, once",
            "make, which does the compiling",
            "the linker",
        ],
        tones=["input", "intermediate", "intermediate", "intermediate", "durable"],
    )
)


gallery.add(
    figures.table(
        "three-ways-in",
        ["route", "what you need", "what you get", "what you give up"],
        [
            ["browser", "a tab", "every Tier 0 experiment", "the C source, and gdb"],
            ["container", "docker, 2 GB", "a debug build and a debugger", "about ten minutes"],
            ["build it", "a compiler, 20 min", "any flags you like", "the twenty minutes"],
        ],
        title="Three ways to have a CPython to poke at",
        caption="Only the third one is building. The first two are not consolation prizes, they are how most of this material is meant to be read.",
        tones=["focus", "focus", "quiet"],
    )
)


gallery.add(
    figures.table(
        "the-five-builds",
        ["build", "configure flag", "what changes", "how you can tell"],
        [
            ["release", "none", "nothing, it is the control", "none of the others are true"],
            ["debug", "--with-pydebug", "bigger objects, self checks", "sys.gettotalrefcount"],
            ["freethreaded", "--disable-gil", "header, refcounts, collector", "Py_GIL_DISABLED"],
            [
                "jit",
                "--enable-experimental-jit",
                "hot loops leave the loop",
                "sys._jit.is_available()",
            ],
            [
                "tailcall",
                "--with-tail-call-interp",
                "the eval loop's shape",
                "_Py_TAIL_CALL_INTERP",
            ],
        ],
        title="The five builds this project publishes, and how each one gives itself away",
        caption="Same source, same commit, five binaries. Several of the numbers in the earlier lessons move between them.",
    )
)


gallery.add(
    figures.table(
        "generated-or-written",
        ["file in the tree", "written by", "from"],
        [
            ["Parser/parser.c", "a generator", "Grammar/python.gram"],
            ["Python/Python-ast.c", "a generator", "Parser/Python.asdl"],
            ["Python/generated_cases.c.h", "a generator", "Python/bytecodes.c"],
            ["Include/opcode_ids.h", "a generator", "Python/bytecodes.c"],
            ["Objects/listobject.c", "a person", "nothing, it is the source"],
        ],
        title="Four of these are output, and editing them is a wasted afternoon",
        caption="The generated ones are committed anyway, so you can build CPython without already having a CPython to run the generators.",
        tones=["quiet", "quiet", "quiet", "quiet", "focus"],
    )
)


gallery.add(
    figures.compare(
        "flags-worth-knowing",
        (
            "makes the build slower",
            [
                "--enable-optimizations",
                "PGO: build, run tests, rebuild",
                "twenty minutes to an hour",
                "for measuring speed",
            ],
        ),
        (
            "makes the build useful",
            [
                "--with-pydebug",
                "assertions and refcount totals",
                "adds a minute, costs 2x at run time",
                "for understanding behaviour",
            ],
        ),
        title="The two flags people reach for, and they are for opposite jobs",
        verdict="Never take a timing on a debug build, and never try to understand a crash on an optimized one.",
        verdict_tone="warning",
    )
)


raise SystemExit(gallery.save())
