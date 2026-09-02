#!/usr/bin/env python
"""The diagrams for C04, what happens when one process holds more than one interpreter.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

`two-ways-to-arrange-four-threads` is the choice the whole lesson is about, and the rest fills
it in. Where the interpreters are kept, which fields belong to which level now that there are
three levels, what two interpreters still share, how a value gets from one to the other, and
the six settings that make a subinterpreter refuse things the main one allows.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("c04-more-than-one-interpreter")

gallery.add(
    figures.compare(
        "two-ways-to-arrange-four-threads",
        (
            "four threads, one interpreter",
            [
                "one GIL between them",
                "one sys.modules",
                "every object in reach",
                "four cores, one at a time",
            ],
        ),
        (
            "four threads, four interpreters",
            [
                "a GIL each",
                "a sys.modules each",
                "almost nothing in reach",
                "four cores, all at once",
            ],
        ),
        title="The same four threads, arranged two ways",
        verdict="Both columns are one process. The right one is what this lesson is about.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.flow(
        "the-interpreter-list",
        [
            "_PyRuntime.interpreters.head",
            "interpreter 2, the newest",
            "interpreter 1",
            "interpreter 0, the main one",
        ],
        title="One list per process, and it is built the same way the thread list is",
        tones=["input", "focus", "quiet", "durable"],
        labels=["->next", "->next", "->next"],
    )
)


gallery.add(
    figures.table(
        "who-owns-what",
        ["the field", "what it hangs off", "how many in a process"],
        [
            ["interpreters.head", "the runtime", "exactly one"],
            ["ceval.gil", "an interpreter", "one for each"],
            ["gil->interval", "an interpreter", "one for each"],
            ["threads.head", "an interpreter", "one for each"],
            ["tstate->state", "a thread", "one for each thread"],
        ],
        title="Three levels, once there is more than one interpreter",
        caption="C03 covered the bottom row. The middle three are what having a second one changes.",
        tones=["durable", "focus", "focus", "quiet", "quiet"],
    )
)


gallery.add(
    figures.compare(
        "shared-or-a-copy",
        (
            "one object, both interpreters",
            [
                "None, True and False",
                "ints from -5 up to 1024",
                "one character strings",
                "the built in types",
            ],
        ),
        (
            "one each, at different addresses",
            [
                "any longer string",
                "any bigger int",
                "every list and dict",
                "every module, including sys",
            ],
        ),
        title="What two interpreters in one process still have in common",
        verdict="The left column is exactly the set M05 called immortal, and that is not a coincidence.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.flow(
        "across-the-gap",
        [
            "a list in interpreter 0",
            "turned into bytes on the way in",
            "held in the queue, owned by neither",
            "built again in interpreter 1",
            "a different object, the same value",
        ],
        title="What a queue does to the thing you put in it",
        tones=["input", "intermediate", "quiet", "intermediate", "focus"],
        labels=["q.put", "no interpreter owns it", "q.get", "so edits do not travel"],
    )
)


gallery.add(
    figures.table(
        "the-isolated-config",
        ["setting", "value", "what it stops"],
        [
            ["gil", "OWN_GIL", "nothing, this is the point"],
            ["allow_threads", "1", "nothing, ordinary threads work"],
            ["allow_daemon_threads", "0", "threading.Thread(daemon=True)"],
            ["allow_fork", "0", "os.fork"],
            ["allow_exec", "0", "os.execv"],
            ["check_multi_interp_extensions", "1", "import readline"],
            ["use_main_obmalloc", "0", "sharing the main heap"],
        ],
        title="The seven settings concurrent.interpreters asks for",
        caption="Every refusal you get from a subinterpreter is one of these lines saying no.",
        tones=["focus", "quiet", "warning", "warning", "warning", "warning", "durable"],
    )
)


raise SystemExit(gallery.save())
