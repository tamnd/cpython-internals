#!/usr/bin/env python
"""The diagrams for R01, everything the interpreter does before your first statement runs.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The order follows the lesson. The shape of startup, what is already in sys.modules when you
get there, where the configuration comes from, who works out sys.path, what goes in front of
it, and what the whole thing costs on two builds.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("r01-before-your-first-line")

gallery.add(
    figures.flow(
        "before-your-first-line",
        [
            "the shell runs python",
            "read the configuration",
            "build the runtime",
            "core startup",
            "main startup",
            "your first line",
        ],
        title="What happens between the shell and your code",
        tones=["input", "quiet", "quiet", "intermediate", "intermediate", "durable"],
        labels=[
            "argv and the environment",
            "one process wide struct",
            "no imports possible yet",
            "sys.path, then site",
        ],
    )
)


gallery.add(
    figures.table(
        "what-is-already-imported",
        ["how the module got there", "normal start", "started with -S"],
        [
            ["built into the python binary", "15", "12"],
            ["frozen bytecode, also in the binary", "17", "8"],
            ["read from a file on disk", "0", "0"],
            ["everything in sys.modules", "33", "21"],
        ],
        title="What is in sys.modules before your first statement",
        caption="Not one of them was read from disk. They are all inside the binary already.",
        tones=["durable", "focus", "warning", "quiet"],
    )
)


gallery.add(
    figures.table(
        "the-highest-setting-wins",
        ["what you asked for", "what you might expect", "what you actually get"],
        [
            ["-O on its own", "1", "1"],
            ["PYTHONOPTIMIZE=2 on its own", "2", "2"],
            ["PYTHONOPTIMIZE=2 and -O", "1, the flag is nearer", "2"],
            ["PYTHONOPTIMIZE=1 and -OO", "1, the env is stronger", "2"],
            ["PYTHONOPTIMIZE=2 and -E", "2", "0"],
        ],
        title="sys.flags.optimize when the flag and the environment disagree",
        caption="Neither one wins. The higher number wins, unless -E throws the environment out.",
        tones=["quiet", "quiet", "focus", "focus", "warning"],
    )
)


gallery.add(
    figures.flow(
        "who-works-out-sys-path",
        [
            "Modules/getpath.py",
            "compiled at build time",
            "a byte blob in the binary",
            "run during startup",
            "sys.path and friends",
        ],
        title="sys.path is produced by a Python program that is not on sys.path",
        tones=["input", "quiet", "intermediate", "intermediate", "durable"],
        labels=[
            "to bytecode",
            "marshalled in",
            "eleven C helpers stand in for os.path",
        ],
    )
)


gallery.add(
    figures.table(
        "what-goes-in-front",
        ["how you started it", "what lands in sys.path[0]", "when it was added"],
        [
            ["python script.py", "the directory the script is in", "last, after everything"],
            ["python -c code", "the empty string", "last, after everything"],
            ["python -m module", "the current directory", "last, after everything"],
            ["python -P script.py", "nothing is added at all", "never"],
        ],
        title="The front of sys.path is decided after the rest of it",
        caption="This is why a file called random.py next to your script can shadow the real one.",
        tones=["focus", "focus", "focus", "durable"],
    )
)


gallery.add(
    figures.bars(
        "what-startup-costs",
        [
            ["release, normal", 26.5],
            ["release, -S", 20.1],
            ["debug, normal", 56.5],
            ["debug, -S", 35.7],
        ],
        unit="ms to start and do nothing",
        title="Starting an interpreter that runs no code of yours",
        caption="A debug build turns frozen modules off, so it reads from disk what release does not.",
        tones=["durable", "durable", "warning", "quiet"],
        width=500,
    )
)


raise SystemExit(gallery.save())
