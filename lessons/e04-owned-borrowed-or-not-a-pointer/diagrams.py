#!/usr/bin/env python
"""The diagrams for E04, what a frame slot actually holds.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `what-is-in-a-slot`. Everything else follows from the bottom
two bits of a pointer being free to use for something else.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("e04-owned-borrowed-or-not-a-pointer")

gallery.add(
    figures.stack(
        "what-is-in-a-slot",
        [
            "00: a pointer, and a reference this slot owns",
            "01: a pointer, borrowed or immortal",
            "11: a number shifted up by two, no object",
        ],
        title="One machine word, three things it can be",
        note="Objects are aligned, so the bottom two bits of a pointer are always zero and "
        "free for something else.",
    )
)


gallery.add(
    figures.table(
        "what-the-bottom-bits-say",
        ["bits", "what the word holds", "what closing it does"],
        [
            ["00", "a pointer, and a reference that was counted", "decrement, and maybe free"],
            ["01", "a pointer, borrowed or immortal", "nothing at all"],
            ["10", "not a valid reference", "never happens"],
            ["11", "an integer, shifted up by two", "nothing at all"],
        ],
        title="Reading the tag",
        caption="Closing a reference is one test on two bits. That is the whole idea.",
        tones=["quiet", "focus", "quiet", "focus"],
    )
)


gallery.add(
    figures.table(
        "what-getrefcount-says",
        ["what you ask about", "3.13 said", "3.14 and later say"],
        [
            ["a local, asked directly", "2", "1"],
            ["a local passed down a call", "3", "1"],
            ["a local also stored in a list", "3", "2"],
            ["a module level name", "2", "2"],
        ],
        title="The same four questions, two different answers",
        caption="Nothing about the objects changed. What changed is who bothers to count.",
        tones=["focus", "focus", "focus", "quiet"],
    )
)


gallery.add(
    figures.flow(
        "when-a-borrow-is-promoted",
        [
            "the compiler wants to load a local",
            "does the value escape into the heap",
            "if it does, load it owned",
            "if it does not, load it borrowed",
        ],
        title="How the compiler decides",
        labels=[
            "a list, a frame, a generator, another slot",
            "LOAD_FAST, and a counted reference",
            "LOAD_FAST_BORROW, and no counting",
        ],
        tones=["input", "focus", "warning", "durable"],
    )
)


gallery.add(
    figures.table(
        "borrowed-or-owned",
        ["what the line does", "what gets emitted", "why"],
        [
            ["return x", "LOAD_FAST_BORROW", "returning promotes it"],
            ["len(x)", "LOAD_FAST_BORROW", "the call ends, the borrow ends"],
            ["[x]", "LOAD_FAST_BORROW", "the list takes its own"],
            ["y = x", "LOAD_FAST", "a second slot needs its own"],
        ],
        title="Four lines, and what the compiler proved about each",
        caption="Only the last one puts the value somewhere that outlives the instruction.",
        tones=["quiet", "quiet", "quiet", "focus"],
    )
)


gallery.add(
    figures.compare(
        "why-any-of-this-exists",
        (
            "with the GIL",
            [
                "counting is a plain add",
                "cheap, but not free",
                "borrowing saves the add",
                "immortals skip it entirely",
            ],
        ),
        (
            "free threaded",
            [
                "counting is an atomic add",
                "expensive, and contended",
                "borrowing saves far more",
                "hot objects would be a bottleneck",
            ],
        ),
        title="Why a tag bit was worth the trouble",
        verdict="LOAD_FAST runs on every line of Python anybody writes.",
        verdict_tone="focus",
    )
)


raise SystemExit(gallery.save())
