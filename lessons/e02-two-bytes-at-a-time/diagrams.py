#!/usr/bin/env python
"""The diagrams for E02, the instruction stream and dispatch.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `the-same-sixteen-bits`. Everything odd about walking the
instruction stream comes from one word being readable three different ways.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("e02-two-bytes-at-a-time")

gallery.add(
    figures.stack(
        "the-same-sixteen-bits",
        [
            "two bytes: an opcode, then its argument",
            "one whole word: a cache slot for the specializer",
            "a counter: how close this instruction is to being specialized",
        ],
        title="The same sixteen bits, read three different ways",
        note="Which reading applies depends on where in the stream the word is, and nothing in the word says.",
    )
)


gallery.add(
    figures.flow(
        "walking-the-stream",
        [
            "read the two bytes at the pointer",
            "low byte is the opcode, high byte is the argument",
            "jump to the code for that opcode",
            "move the pointer past this word and its cache slots",
        ],
        title="What happens between one instruction and the next",
        labels=[
            "one 16 bit load, nothing else",
            "no decoding, no shifting",
            "three different ways, chosen at build time",
        ],
        tones=["input", "focus", "focus", "durable"],
    )
)


gallery.add(
    figures.table(
        "what-a-listing-hides",
        ["offset", "instruction", "room it takes in the stream"],
        [
            ["0", "RESUME", "one word, then one cache word"],
            ["4", "LOAD_FAST_BORROW_LOAD_FAST_BORROW", "one word, no cache"],
            ["6", "BINARY_OP", "one word, then five cache words"],
            ["18", "STORE_FAST", "one word, no cache"],
            ["20", "LOAD_FAST_BORROW", "one word, no cache"],
            ["22", "RETURN_VALUE", "one word, no cache"],
        ],
        title="Six instructions, twelve words, twenty four bytes",
        caption="Half the words are scratch space. Landing on one of them is a fatal error.",
        tones=["warning", "quiet", "warning", "quiet", "quiet", "quiet"],
    )
)


gallery.add(
    figures.flow(
        "when-one-byte-is-not-enough",
        [
            "EXTENDED_ARG 1 sits in front",
            "it shifts its own argument left by eight",
            "then reads the next opcode itself",
            "STORE_FAST 0 becomes STORE_FAST 256",
        ],
        title="How an argument bigger than 255 gets through a one byte field",
        labels=[
            "the compiler puts it there, up to three of them",
            "1 becomes 256",
            "without going back round the loop",
        ],
        tones=["input", "focus", "focus", "durable"],
    )
)


gallery.add(
    figures.table(
        "numbers-that-cannot-fit",
        ["numbers", "what lives there", "can appear in a code object"],
        [
            ["0 to 232", "real instructions, plain and specialized", "yes"],
            ["233 to 253", "instrumented copies, used while tracing", "yes, swapped in"],
            ["254 and 255", "the tier two entry and the trace recorder", "yes"],
            ["256 to 266", "pseudo instructions the compiler resolves", "no, they do not fit"],
        ],
        title="Why a pseudo instruction can never reach the interpreter",
        caption="One byte holds 0 to 255. Numbering them above that is the guarantee.",
        tones=["quiet", "quiet", "quiet", "focus"],
    )
)


gallery.add(
    figures.table(
        "three-ways-to-jump",
        ["how it was built", "what TARGET becomes", "what the jump becomes"],
        [
            ["plain switch", "case UNARY_NOT:", "goto the top of the switch"],
            ["computed goto", "a label", "goto *opcode_targets[opcode]"],
            ["tail calls", "a whole function", "a tail call through a table"],
        ],
        title="The same generated case, three different interpreters",
        caption="The definition in the DSL says nothing about any of this.",
        tones=["quiet", "focus", "durable"],
    )
)


raise SystemExit(gallery.save())
