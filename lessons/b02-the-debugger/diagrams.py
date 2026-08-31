#!/usr/bin/env python
"""The diagrams for B02, watching the interpreter stop.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `two-stacks`. Seventeen C frames next to four Python frames is
the single fact B02 exists to hand over, and it is a fact about shape, so a picture of the
shape does more than the sentence does.
"""

from nbdiagram import Gallery, figures, stages

gallery = Gallery("b02-the-debugger")

gallery.add(
    stages.map(
        "where-we-are",
        highlight=stages.ANSWER,
        title="The pipeline, stopped in the last box",
        caption="Both recorded sessions stop while the eval loop is running. This lesson is about what you can see from there.",
    )
)


gallery.add(
    figures.beside(
        "two-stacks",
        [
            (
                "what C sees",
                figures.stack(
                    "c-side",
                    [
                        "PyNumber_Multiply",
                        "_PyEval_EvalFrameDefault",
                        "_PyEval_EvalFrame",
                        "_PyEval_Vector",
                        "PyEval_EvalCode",
                        "run_eval_code_obj",
                        "eleven more, down to main",
                    ],
                    note="17 frames",
                ),
            ),
            (
                "what Python sees",
                figures.stack(
                    "python-side",
                    [
                        "double",
                        "middle",
                        "top",
                        "<module>",
                    ],
                    note="4 frames",
                ),
            ),
        ],
        title="One stopped program, two answers to what is it doing",
        caption="Same instant, same process. One _PyEval_EvalFrameDefault covers all four Python calls, which is T07's point where you can count it.",
    )
)


gallery.add(
    figures.table(
        "four-ways-to-look",
        ["tool", "sees Python frames", "sees C frames", "needs", "works in a browser"],
        [
            ["traceback", "yes", "no", "an exception", "yes"],
            ["pdb", "yes", "no", "nothing", "yes"],
            ["faulthandler", "yes", "no", "nothing", "yes"],
            ["gdb", "no", "yes", "a second process", "no"],
            ["gdb with py-bt", "yes", "yes", "a debug build", "no"],
        ],
        title="Four things that can tell you where a program is, and what each one costs",
        caption="The first three are already on your machine and are enough most days. Only the last row works on a process that has stopped running Python.",
        tones=["focus", "focus", "focus", "quiet", "quiet"],
    )
)


gallery.add(
    figures.flow(
        "where-py-bt-comes-from",
        [
            "the C stack",
            "an _PyEval_EvalFrameDefault frame",
            "its frame argument",
            "_PyInterpreterFrame",
            "filename, line, function",
        ],
        title="py-bt is not magic, it is five pointer hops written down once",
        labels=[
            "scan for the eval loop",
            "read the local",
            "follow f_executable",
            "read co_filename and the line table",
        ],
        tones=["input", "intermediate", "intermediate", "intermediate", "durable"],
    )
)


gallery.add(
    figures.compare(
        "two-ways-to-stop",
        (
            "an exception",
            [
                "the interpreter is still fine",
                "it prints the traceback itself",
                "you get a file and a line number",
                "handled in Python/errors.c",
            ],
        ),
        (
            "a segfault",
            [
                "the process is gone",
                "nothing prints, there is nothing left to print it",
                "the shell says 139 and stops",
                "handled by the kernel",
            ],
        ),
        title="Two ways a program stops, and only one of them explains itself",
        verdict="py-bt gets you the file and the line for the right hand column too, out of what is left.",
        verdict_tone="warning",
    )
)


gallery.add(
    figures.table(
        "the-commands-worth-knowing",
        ["command", "what it does", "the Python one"],
        [
            ["break FUNC", "stop when FUNC is called", "breakpoint()"],
            ["run", "start the program", "python file.py"],
            ["continue", "carry on to the next stop", "c in pdb"],
            ["bt", "the C stack, top first", "traceback.print_stack()"],
            ["py-bt", "the Python stack, top first", "the same, from outside"],
            ["print EXPR", "evaluate a C expression here", "p expr in pdb"],
            ["py-list", "the Python source around here", "l in pdb"],
        ],
        title="Seven gdb commands, which is enough for everything in this lesson",
        caption="Six of the seven have a pdb equivalent you already have. The one that does not is py-bt, and it is the reason the debug image exists.",
    )
)


raise SystemExit(gallery.save())
