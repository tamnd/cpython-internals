#!/usr/bin/env python
"""The diagrams for R03, what one import statement actually does.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The order follows the lesson. The compiled form of the statement first, then the six steps
the machinery runs, then the three finders that answer questions, then the moment a
half built module becomes visible to everyone, then the three caches, then the bill.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("r03-what-import-does")

gallery.add(
    figures.table(
        "what-the-statement-compiles-to",
        ["what you wrote", "the name IMPORT_NAME asks for", "the name you end up with"],
        [
            ["import os", "os", "os"],
            ["import os.path", "os.path", "os"],
            ["import os.path as p", "os.path", "p"],
            ["from os import sep", "os", "sep"],
            ["from . import sibling", "the empty string, at level 1", "sibling"],
        ],
        title="Five statements, and the name each one leaves behind",
        caption="Row two is the one that surprises people. Importing os.path binds os.",
        tones=["quiet", "focus", "quiet", "quiet", "intermediate"],
    )
)


gallery.add(
    figures.stack(
        "the-import-protocol",
        [
            "__import__(name)              the builtin the bytecode calls",
            "_gcd_import(name)             parents first, left to right",
            "_find_and_load(name)          looks in sys.modules with no lock",
            "_find_and_load_unlocked()     now holding the lock for this name",
            "_find_spec(name, path)        asks every finder on sys.meta_path",
            "_load_unlocked(spec)          sys.modules first, then the body",
        ],
        title="What runs between import x and x being usable",
        note="Almost every import in a running program stops at the third box and returns.",
    )
)


gallery.add(
    figures.table(
        "three-finders",
        ["the finder on sys.meta_path", "answers for", "the origin it reports"],
        [
            ["BuiltinImporter", "modules compiled into the binary", "built-in"],
            ["FrozenImporter", "modules baked in as bytecode", "frozen"],
            ["PathFinder", "anything reachable from sys.path", "a file on disk"],
        ],
        title="The three finders every Python starts with, in the order they are asked",
        caption="A name can have more than one answer. import os stops at the second row.",
        tones=["durable", "focus", "intermediate"],
    )
)


gallery.add(
    figures.flow(
        "when-the-module-becomes-visible",
        [
            "first.py starts",
            "sys.modules is set",
            "second.py runs",
            "first.py finishes",
        ],
        title="A module is visible to everybody long before it is finished",
        tones=["input", "warning", "focus", "durable"],
        labels=[
            "the empty module",
            "first.py imports it",
            "reads back half a module",
        ],
    )
)


gallery.add(
    figures.table(
        "three-caches",
        ["the cache", "keyed by", "what it saves you", "cleared by"],
        [
            ["sys.modules", "the module name", "the whole import", "deleting the key"],
            [
                "sys.path_importer_cache",
                "a sys.path entry",
                "picking a finder",
                "invalidate_caches",
            ],
            [
                "FileFinder._path_cache",
                "a directory",
                "one listdir per lookup",
                "the directory mtime",
            ],
        ],
        title="Three caches, and importing hits all three on the way down",
        caption="They are ordinary Python objects on sys, and you are allowed to look.",
        tones=["focus", "intermediate", "durable"],
    )
)


gallery.add(
    figures.bars(
        "cores-kept-busy",
        [
            ["four modules, with the lock", 1.02],
            ["four modules, no lock", 3.63],
            ["one module, with the lock", 1.00],
            ["one module, no lock", 1.01],
        ],
        unit="cores kept busy",
        title="Four threads importing at once, on two builds",
        caption="The per module lock only bites when two threads want the same module.",
        tones=["quiet", "focus", "quiet", "quiet"],
        width=420,
    )
)


raise SystemExit(gallery.save())
