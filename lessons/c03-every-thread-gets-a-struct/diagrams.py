#!/usr/bin/env python
"""The diagrams for C03, what a thread is once the interpreter has hold of it.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

`what-a-thread-is-here` sets up the split the whole lesson runs on: the operating system gives
you one thing and the interpreter bolts a second thing onto it. The rest is that second thing.
What is in it, how the interpreter finds them all, the three numbers that identify one, the four
values its state field can hold, and what happens to a thread that is still running when the
interpreter has decided to stop.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("c03-every-thread-gets-a-struct")

gallery.add(
    figures.compare(
        "what-a-thread-is-here",
        (
            "what the operating system gives",
            [
                "a stack and a register set",
                "an id it will hand out again",
                "no idea what Python is",
                "the same for any language",
            ],
        ),
        (
            "what the interpreter adds",
            [
                "a PyThreadState struct",
                "an id that never repeats",
                "its own frames and exception",
                "a slot in one linked list",
            ],
        ),
        title="A Python thread is two things stapled together",
        verdict="Almost everything in this lesson lives in the right column.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.stack(
        "what-rides-on-the-state",
        [
            "prev and next, the list it sits in",
            "interp, the interpreter it belongs to",
            "current_frame, what it is running",
            "current_exception, what it is handling",
            "py_recursion_remaining, how much further it may go",
            "dict, a scratch dict only it can reach",
            "threading_local_key, where its threading.local values hang",
            "critical_section, the locks it will pick back up",
            "state, attached or detached or suspended",
        ],
        title="Nine of the forty odd fields in one PyThreadState",
        note="Bottom up is roughly the order the header lists them. Every one is per thread.",
    )
)


gallery.add(
    figures.flow(
        "the-list-newest-first",
        [
            "interp->threads.head",
            "state id 4, the newest thread",
            "state id 3",
            "state id 2",
            "state id 1, the main thread",
        ],
        title="Every thread state in one singly walked list, newest at the front",
        tones=["input", "focus", "quiet", "quiet", "durable"],
        labels=["->next", "->next", "->next", "->next"],
    )
)


gallery.add(
    figures.table(
        "three-numbers-one-thread",
        ["the number", "who fills it in", "when", "handed out twice?"],
        [
            ["tstate->id", "the interpreter", "when the struct is made", "never"],
            ["thread_id", "the thread itself", "when it first binds", "yes, often"],
            ["native_thread_id", "the operating system", "when it first binds", "yes, eventually"],
        ],
        title="Three ways to say which thread, and only the first one is yours to trust",
        caption="get_ident() returns the second. Start and join threads in waves and it repeats.",
        tones=["focus", "warning", "warning"],
    )
)


gallery.add(
    figures.table(
        "attached-detached-suspended",
        ["state", "value", "who may change it", "what the thread is doing"],
        [
            ["attached", "1", "the thread itself", "running Python"],
            ["detached", "0", "the thread itself", "inside C, or waiting"],
            ["suspended", "2", "whoever stopped the world", "parked, will resume"],
            ["shutting down", "3", "the interpreter, at exit", "about to be hung"],
        ],
        title="One int on the thread state, four values it can hold",
        caption="A thread moves between the first two by itself. The other two are done to it.",
        tones=["focus", "durable", "intermediate", "warning"],
    )
)


gallery.add(
    figures.flow(
        "the-daemon-at-shutdown",
        [
            "the main thread returns",
            "shutdown stores 3 into every other state",
            "the daemon reaches its next periodic check",
            "it tries to attach and reads the 3",
            "the thread is hung where it stands",
        ],
        title="What happens to a daemon thread that is still working when Python exits",
        tones=["input", "warning", "intermediate", "intermediate", "focus"],
        labels=["so finalize starts", "one atomic store each", "and tries to attach", "for good"],
    )
)


raise SystemExit(gallery.save())
