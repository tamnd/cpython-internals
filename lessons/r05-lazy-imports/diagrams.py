#!/usr/bin/env python
"""The diagrams for R05, the import that has not happened yet.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The order follows the lesson. What the two spellings do differently first, then the two bits
of the opcode that carry the decision, then the three places that get a say in it, then what
does and does not wake a placeholder up, then the lock resolution takes, then the bill.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("r05-lazy-imports")

gallery.add(
    figures.compare(
        "two-spellings",
        (
            "import json",
            [
                "find the file",
                "read and unmarshal it",
                "run the module body",
                "bind the name",
            ],
        ),
        (
            "lazy import json",
            [
                "work out the absolute name",
                "bind a placeholder",
            ],
        ),
        title="What the import line does, both ways",
        verdict="The right hand side does the other three steps later, the first time something reads the name.",
    )
)


gallery.add(
    figures.table(
        "the-two-bits",
        ["the low two bits of oparg", "what dis prints", "what the compiler picks it for"],
        [
            ["00", "json", "a plain import at module scope"],
            ["01", "json + lazy", "you wrote the lazy keyword"],
            ["10", "json + eager", "inside a function, a class or a try block"],
        ],
        title="IMPORT_NAME carries the decision in its argument",
        caption="The name index is the rest of the argument, shifted down by two.",
        tones=["quiet", "focus", "warning"],
    )
)


gallery.add(
    figures.pipeline(
        "who-decides",
        [
            ("a bit in the opcode", "Python/codegen.c"),
            ("the mode and the list", "Python/ceval.c"),
            ("the scope and filter", "Python/import.c"),
        ],
        title="Three places get a say before a placeholder is built",
        caption="The eager bit ends it at the first box. Everything after that can still change its mind.",
    )
)


gallery.add(
    figures.table(
        "what-wakes-it",
        ["what you do with the name", "does the placeholder wake up"],
        [
            ["read it as a bare name", "yes, that is the whole design"],
            ["read it as an attribute of a module", "yes"],
            ["look it up in the namespace dict", "no, a dict lookup is just a dict lookup"],
            ["ask whether the name is in the dict", "no"],
            ["print the repr of the placeholder", "no, you get <lazy_import 'json'>"],
        ],
        title="What counts as touching the name",
        caption="Only the opcodes know. Anything that goes around them sees the placeholder.",
        tones=["focus", "focus", "quiet", "quiet", "quiet"],
    )
)


gallery.add(
    figures.compare(
        "which-lock",
        (
            "an ordinary import",
            [
                "one lock per module name",
                "two names go at once",
            ],
        ),
        (
            "waking a placeholder",
            [
                "the interpreter wide import lock",
                "held while the module body runs",
                "two names take turns",
            ],
        ),
        title="Which lock the two paths take",
        verdict="Same work, different lock. On a free threaded build the difference is visible.",
    )
)


gallery.add(
    figures.bars(
        "what-deferring-saves",
        [
            ["twelve plain imports", 227.1],
            ["the same file, deferred", 54.9],
        ],
        unit="ms",
        title="Starting up, importing twelve modules and using one",
        caption="Eleven of the twelve were never needed. Three quarters of the run went with them.",
        tones=["quiet", "focus"],
        width=420,
    )
)


raise SystemExit(gallery.save())
