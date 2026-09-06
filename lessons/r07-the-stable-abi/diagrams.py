#!/usr/bin/env python
"""The diagrams for R07, the two gates an extension has to get past.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The order follows the lesson. The file name first, since that is the gate an extension meets
before anything opens it, then the table of which names each build will look at, then the
struct that is the second gate, then who it turns away, and last the stable ABI as a thing
that grew one release at a time.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("r07-the-stable-abi")

gallery.add(
    figures.pipeline(
        "two-gates",
        [
            ("a file turns up", "mod.abi3t.so"),
            ("read the name", "a tag I take?"),
            ("open and run it", "dlopen, then init"),
            ("check the struct", "numbers agree?"),
        ],
        highlight=1,
        title="What an extension has to get past before it is a module",
        caption="The first gate costs one stat call. The second one has already run the extension's code.",
    )
)


gallery.add(
    figures.spans(
        "what-the-name-says",
        "mymodule.cpython-315t-darwin.so",
        [
            (0, 8, "the module"),
            (9, 16, "which Python"),
            (17, 20, "3.15"),
            (20, 21, "no GIL"),
            (22, 28, "the platform"),
            (29, 31, "shared library"),
        ],
        title="Everything the interpreter knows before it opens the file",
        caption="Change any one of the middle four and this build will not even look at it.",
    )
)


gallery.add(
    figures.table(
        "which-names-load",
        ["the file is called", "3.15 with the GIL", "3.15 free threaded", "3.14"],
        [
            ["mod.cpython-315-darwin.so", "considered", "invisible", "invisible"],
            ["mod.cpython-315t-darwin.so", "invisible", "considered", "invisible"],
            ["mod.cpython-314-darwin.so", "invisible", "invisible", "considered"],
            ["mod.abi3.so", "considered", "invisible", "considered"],
            ["mod.abi3t.so", "considered", "considered", "invisible"],
            ["mod.so", "considered", "considered", "considered"],
        ],
        title="Which file names each build is willing to look at",
        caption="abi3t is the only tag both 3.15 builds accept, which is why it is the one to ship.",
        tones=["intermediate", "intermediate", "intermediate", "durable", "durable", "quiet"],
    )
)


gallery.add(
    figures.stack(
        "the-five-fields",
        [
            "abi_version, the version the extension was built for",
            "build_version, the version its headers came from",
            "flags, stable, GIL, free threaded, internal",
            "abiinfo_minor_version, 0 so far",
            "abiinfo_major_version, 1, or 0 to skip the check",
        ],
        title="PyABIInfo, the twelve bytes an extension carries about itself",
        note="Twelve bytes of struct decide whether an ImportError or a module comes back.",
    )
)


gallery.add(
    figures.table(
        "who-gets-refused",
        ["what the extension claims", "3.15 with the GIL", "3.15 free threaded"],
        [
            ["built for this exact version", "loads", "incompatible with free threaded"],
            [
                "built for 3.13 and nothing else",
                "incompatible ABI version",
                "incompatible ABI version",
            ],
            ["stable abi since 3.2", "loads", "incompatible with free threaded"],
            ["stable abi since 3.14", "loads", "incompatible with free threaded"],
            [
                "stable abi from the future",
                "incompatible future version",
                "incompatible future version",
            ],
            ["free threaded only", "only compatible with free threaded", "loads"],
            ["happy either way", "loads", "loads"],
            ["claims internal and stable", "cannot use both", "cannot use both"],
        ],
        title="What PyABIInfo_Check says to each kind of extension",
        caption="One row loads on both builds, and it is the row that promises nothing about the lock.",
        tones=[
            "intermediate",
            "warning",
            "intermediate",
            "intermediate",
            "warning",
            "intermediate",
            "durable",
            "warning",
        ],
    )
)


gallery.add(
    figures.bars(
        "when-it-arrived",
        [
            ["3.3", 26],
            ["3.4", 3],
            ["3.5", 13],
            ["3.6", 4],
            ["3.7", 12],
            ["3.8", 1],
            ["3.9", 10],
            ["3.10", 5],
            ["3.11", 16],
            ["3.12", 6],
            ["3.13", 27],
            ["3.14", 18],
            ["3.15", 32],
        ],
        unit="functions",
        title="When each of the 173 gated functions joined the stable ABI",
        caption="The 528 that were there in 3.2 are not on this chart. These are the ones added since.",
        tones=[
            "quiet",
            "quiet",
            "quiet",
            "quiet",
            "quiet",
            "quiet",
            "quiet",
            "quiet",
            "quiet",
            "quiet",
            "focus",
            "focus",
            "focus",
        ],
        width=560,
    )
)


raise SystemExit(gallery.save())
