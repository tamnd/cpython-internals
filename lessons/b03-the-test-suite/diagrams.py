#!/usr/bin/env python
"""The diagrams for B03, running one test out of a very large number of them.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `narrowing-it-down`. Everything else here is background for
the single move a reader has to learn, which is going from the command that runs everything
to the command that runs the one test they care about.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("b03-the-test-suite")

gallery.add(
    figures.bars(
        "how-big-it-is",
        [
            ("Lib/test", 709292),
            ("all the rest of Lib", 351408),
        ],
        unit="lines of Python",
        title="The test suite against the library it tests",
        caption="Two lines of test for every line of library. Nobody reads all of it and nobody runs all of it either.",
        tones=["focus", "quiet"],
    )
)


gallery.add(
    figures.compare(
        "what-regrtest-adds",
        (
            "unittest",
            [
                "finds test methods on a class",
                "runs them and counts results",
                "prints a dot per test",
                "in the standard library, on every Python",
            ],
        ),
        (
            "regrtest, on top of it",
            [
                "finds test files in a directory",
                "runs each file in its own process",
                "checks the environment came back clean",
                "hunts reference leaks, on a debug build",
            ],
        ),
        title="The suite is unittest with a lot of bookkeeping around it",
        verdict="Everything on the right is about running four hundred files without one of them ruining the next.",
    )
)


gallery.add(
    figures.flow(
        "from-a-command-to-a-test",
        [
            "python -m test",
            "the argument list",
            "a list of file names",
            "an imported module",
            "a suite of test methods",
            "an exit code",
        ],
        title="What happens between the command and the answer",
        labels=[
            "parsed in cmdline.py",
            "found by listdir",
            "imported by name",
            "filtered by -m",
        ],
        tones=["input", "intermediate", "intermediate", "intermediate", "intermediate", "durable"],
    )
)


gallery.add(
    figures.table(
        "narrowing-it-down",
        ["command", "what it runs", "roughly how long"],
        [
            ["python -m test", "every file in Lib/test", "half an hour"],
            ["python -m test -j0", "the same, one process per core", "a few minutes"],
            ["python -m test test_dis", "one file", "seconds"],
            ["python -m test test_dis -m test_dis_object", "one method", "under a second"],
            ["python -m unittest test.test_dis", "one file, no regrtest", "seconds"],
            ["python -m test --list-cases test_dis", "nothing, it just lists them", "instant"],
        ],
        title="Six ways to run the suite, from all of it to none of it",
        caption="The third and fourth rows are the ones you will type. The rest are here so the shape of the command makes sense.",
        tones=["quiet", "quiet", "focus", "focus", "intermediate", "intermediate"],
    )
)


gallery.add(
    figures.table(
        "what-the-exit-code-means",
        ["code", "what it means", "where it comes from"],
        [
            ["0", "everything passed", "the default"],
            ["2", "a test failed", "EXITCODE_BAD_TEST"],
            ["3", "a test changed the environment", "EXITCODE_ENV_CHANGED"],
            ["4", "nothing ran, which is usually a typo", "EXITCODE_NO_TESTS_RAN"],
            ["5", "it failed, then passed on the rerun", "EXITCODE_RERUN_FAIL"],
            ["130", "you pressed control C", "EXITCODE_INTERRUPTED"],
        ],
        title="What the number after a run is telling you",
        caption="Codes 3 and 4 are the two that surprise people. Both mean the run was not clean even though nothing failed.",
        tones=["durable", "warning", "warning", "focus", "focus", "quiet"],
    )
)


gallery.add(
    figures.table(
        "six-repetitions",
        ["run", "1", "2", "3", "4", "5", "6"],
        [
            ["counted?", "no", "no", "no", "yes", "yes", "yes"],
            ["the clean file", "X", "X", ".", ".", ".", "."],
            ["the leaky file", "X", "X", "1", "1", "1", "1"],
        ],
        title="What -R 3:3 prints, one character per run",
        caption="The first three are warmups and get thrown away, because caches filling up look just like a leak.",
        tones=["quiet", "durable", "warning"],
    )
)


raise SystemExit(gallery.save())
