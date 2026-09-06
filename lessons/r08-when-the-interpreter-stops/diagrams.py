#!/usr/bin/env python
"""The diagrams for R08, what the interpreter does after your last line.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The order follows the lesson. The shape of shutdown first, then the two things you can
register and the order they come back in, then what is still reachable once the sweep has
started, then the table of nine endings, then the one case that goes wrong and what it costs.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("r08-when-the-interpreter-stops")

gallery.add(
    figures.pipeline(
        "the-order-of-the-end",
        [
            ("your last line", "the program is done"),
            ("threads", "non daemon ones join"),
            ("atexit", "newest callback first"),
            ("the sweep", "modules, then objects"),
        ],
        highlight=2,
        title="What happens after your last line, in the order it happens",
        caption="Only the first two steps run with a normal interpreter underneath them.",
    )
)


gallery.add(
    figures.stack(
        "atexit-is-a-stack",
        [
            "atexit.register(first)",
            "atexit.register(second)",
            "atexit.register(third)",
        ],
        title="Why the last callback you register is the first one to run",
        note="Each register call puts the new callback at the front of one list, so the list comes back in reverse.",
    )
)


gallery.add(
    figures.table(
        "what-a-late-finalizer-can-reach",
        ["what you try", "what you get"],
        [
            ["reading your module's globals", "still there, they are what is being freed"],
            ["len(sys.modules)", "0, the dict has already been emptied"],
            ["import anything, even something imported", "ImportError, sys.meta_path is None"],
            ["sys.is_finalizing()", "True, which is how you can tell"],
            ["print(...)", "works, but comes out after everything else"],
        ],
        title="What a __del__ that runs during shutdown can still do",
        caption="A finalizer that imports something works every time you test it and fails on the way out.",
        tones=["durable", "warning", "warning", "intermediate", "intermediate"],
    )
)


gallery.add(
    figures.table(
        "what-each-ending-runs",
        ["how the process ends", "atexit", "finalizer", "status"],
        [
            ["it just runs off the end", "yes", "yes", "0"],
            ["sys.exit(3)", "yes", "yes", "3"],
            ["an exception nobody caught", "yes", "yes", "1"],
            ["os._exit(0)", "no", "no", "0"],
            ["an atexit callback raises", "yes", "yes", "0"],
            ["a finalizer raises", "yes", "yes", "0"],
            ["a daemon thread inside time.sleep", "yes", "yes", "0"],
            ["a daemon thread running your code", "yes", "no", "0"],
            ["a subinterpreter nobody closed", "yes", "yes", "0"],
        ],
        title="Nine ways to end, and what each one still runs",
        caption="Two rows skip work you asked for, and only one of them is a call you made on purpose.",
        tones=[
            "durable",
            "durable",
            "durable",
            "warning",
            "intermediate",
            "intermediate",
            "durable",
            "warning",
            "intermediate",
        ],
    )
)


gallery.add(
    figures.compare(
        "the-thread-that-holds-your-globals",
        (
            "target=time.sleep",
            [
                "the thread is running library code",
                "nothing of yours is on its stack",
                "your module gets cleared as usual",
                "your finalizers run",
            ],
        ),
        (
            "target=your_function",
            [
                "the thread is running your code",
                "the frame holds your module's globals",
                "the module dict cannot be cleared",
                "your finalizers never run",
            ],
        ),
        title="One daemon thread, two ways to start it, two different endings",
        verdict="Passing your own function instead of a library one is the whole difference.",
    )
)


gallery.add(
    figures.bars(
        "what-was-left-behind",
        [
            ["nothing held", 0],
            ["5000 objects held", 0],
            ["the same, plus a daemon thread", 12680],
        ],
        unit="references",
        title="What a debug build says was left over when it stopped",
        caption="Holding objects costs nothing. Holding them behind a daemon thread costs all of them.",
        tones=["quiet", "quiet", "warning"],
        width=460,
    )
)


raise SystemExit(gallery.save())
