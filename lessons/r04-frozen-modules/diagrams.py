#!/usr/bin/env python
"""The diagrams for R04, the modules that live inside the binary.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The order follows the lesson. How a source file becomes part of the binary first, then the
three groups it can land in, then the moment the import system loads itself, then the two
ways a module can arrive, then what is still visible afterwards, then the bill.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("r04-frozen-modules")

gallery.add(
    figures.flow(
        "from-source-to-binary",
        [
            "Lib/os.py",
            "a code object",
            "os.h, a C array",
            "the python3 binary",
        ],
        title="How a standard library file ends up inside the interpreter",
        tones=["input", "intermediate", "intermediate", "durable"],
        labels=[
            "compile, during the build",
            "marshal",
            "the C compiler",
        ],
    )
)


gallery.add(
    figures.table(
        "three-groups",
        ["the array in frozen.c", "what is in it", "names", "can it be switched off"],
        [
            ["bootstrap_modules", "the import system itself", "3", "no"],
            ["stdlib_modules", "what a bare startup needs", "19", "yes"],
            ["test_modules", "hello world, for the test suite", "11", "yes"],
        ],
        title="Thirty three frozen names, in three groups that are treated differently",
        caption="Only the first group is searched no matter what the flag says.",
        tones=["focus", "intermediate", "quiet"],
    )
)


gallery.add(
    figures.stack(
        "where-the-loop-is-cut",
        [
            "Py_InitializeFromConfig      C, no Python running yet",
            "init_importlib               still C",
            "PyImport_ImportFrozenModule  reads _frozen_importlib out of an array",
            "_install(sys, _imp)          the first Python call of the process",
            "_setup(sys, _imp)            global sys, _imp, then assign them",
            "sys.meta_path                three finders, import works from here",
        ],
        title="Loading the import system without an import system",
        note="_bootstrap.py never writes import sys. The module is handed to it as an argument.",
    )
)


gallery.add(
    figures.compare(
        "two-ways-in",
        (
            "frozen",
            [
                "look the name up in a C array",
                "unmarshal the bytes already in memory",
                "run the module body",
            ],
        ),
        (
            "the same module from disk",
            [
                "ask each finder on sys.meta_path",
                "list the directory, look for a match",
                "open the pyc, check magic and mtime",
                "unmarshal what was read",
                "run the module body",
            ],
        ),
        title="What it takes to load os, both ways",
        verdict="On a stock build a startup reads 13 of these files with the flag off, none with it on.",
    )
)


gallery.add(
    figures.table(
        "frozen-but-not-hidden",
        ["what you ask for", "what you get back"],
        [
            ["os.__spec__.origin", "frozen"],
            ["os.__spec__.cached", "None, because no pyc was involved"],
            ["os.__file__", "the real path to os.py"],
            ["os.makedirs.__code__.co_filename", "<frozen os>"],
            ["inspect.getsource(os.makedirs)", "the source, found through __file__"],
        ],
        title="A frozen module knows where it came from, even though it never went there",
        caption="The path on the spec is what lets tracebacks and pdb show you real lines.",
        tones=["focus", "quiet", "durable", "focus", "durable"],
    )
)


gallery.add(
    figures.bars(
        "what-freezing-saves",
        [
            ["release, frozen on", 30.5],
            ["release, frozen off", 35.6],
            ["debug, frozen on", 41.1],
            ["debug, frozen off", 45.6],
        ],
        unit="ms",
        title="Starting up and doing nothing, measured both ways on two builds",
        caption="Around a tenth of a startup, and every millisecond of it is file reading.",
        tones=["focus", "quiet", "focus", "quiet"],
        width=420,
    )
)


raise SystemExit(gallery.save())
