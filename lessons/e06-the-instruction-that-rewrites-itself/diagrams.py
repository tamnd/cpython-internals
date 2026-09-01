#!/usr/bin/env python
"""The diagrams for E06, specialization and the counter that drives it.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `the-life-of-one-instruction`. Everything else is either a
table of what an instruction can turn into, or a measurement of what the change bought.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("e06-the-instruction-that-rewrites-itself")

gallery.add(
    figures.flow(
        "the-life-of-one-instruction",
        [
            "cold, with a counter set to one",
            "second run: look at the operands and rewrite",
            "specialized, with two guards in front",
            "guards keep failing: go back to general",
        ],
        title="What one instruction does over its life",
        labels=[
            "first run just counts down",
            "counter reset to fifty two",
            "fifty three misses, not one",
        ],
        tones=["input", "focus", "durable", "warning"],
    )
)


gallery.add(
    figures.table(
        "what-it-turns-into",
        ["what it saw", "what it became"],
        [
            ["two small ints", "BINARY_OP_ADD_INT"],
            ["two floats", "BINARY_OP_ADD_FLOAT"],
            ["two strings", "BINARY_OP_ADD_UNICODE"],
            ["two lists", "BINARY_OP_EXTEND"],
            ["an int and a float", "BINARY_OP_EXTEND"],
        ],
        title="One line of Python, five different instructions",
        caption="Same source, same compiler, same code object. Only the operands differed.",
        tones=["focus", "focus", "focus", "quiet", "quiet"],
    )
)


gallery.add(
    figures.table(
        "reading-the-counter",
        ["raw word", "value", "backoff", "what it means"],
        [
            ["9", "1", "1", "cold, one more run before trying"],
            ["1", "0", "1", "next run will specialize"],
            ["416", "52", "0", "specialized, fifty two misses of slack"],
            ["0", "0", "0", "out of slack, give up on the next miss"],
        ],
        title="The two bytes after the instruction",
        caption="The low three bits are the backoff exponent. The rest is the countdown.",
        tones=["quiet", "focus", "focus", "warning"],
    )
)


gallery.add(
    figures.table(
        "where-an-attribute-lookup-goes",
        ["what you asked for", "what LOAD_ATTR became"],
        [
            ["an attribute on a normal object", "LOAD_ATTR_INSTANCE_VALUE"],
            ["an attribute on a __slots__ object", "LOAD_ATTR_SLOT"],
            ["a property", "LOAD_ATTR_PROPERTY"],
            ["a name in a module", "LOAD_ATTR_MODULE"],
            ["a method, about to be called", "LOAD_ATTR_METHOD_WITH_VALUES"],
        ],
        title="The same two words, five different instructions",
        caption="One family, many forms. The lookup rules are the same for every one of them.",
        tones=["focus", "focus", "quiet", "quiet", "focus"],
    )
)


gallery.add(
    figures.bars(
        "what-a-miss-costs",
        [
            ["every value an int", 7.5],
            ["every value a float", 7.3],
            ["alternating between the two", 10.5],
        ],
        unit="ns per addition",
        title="The same loop, the same work, three lists",
        caption="Measured on one machine, so your numbers will differ. The gap will not.",
        tones=["durable", "durable", "warning"],
        width=520,
    )
)


gallery.add(
    figures.compare(
        "two-copies-of-the-bytecode",
        (
            "co_code",
            [
                "what the compiler produced",
                "never changes",
                "what dis shows by default",
                "what goes into a pyc file",
            ],
        ),
        (
            "_co_code_adaptive",
            [
                "a private copy per code object",
                "rewritten as the program runs",
                "what dis shows with adaptive=True",
                "thrown away with the process",
            ],
        ),
        title="Every code object carries two versions of its bytecode",
        verdict="Specializing never touches the bytecode you compiled.",
        verdict_tone="focus",
    )
)


raise SystemExit(gallery.save())
