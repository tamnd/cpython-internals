#!/usr/bin/env python
"""The diagrams for E11, the interpreter written as one small function per opcode.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `the-same-file-three-endings`, because everything else here
is a consequence of that table. `what-must-tail-means` is the bit people get wrong when
they hear the word call, so it is drawn rather than explained.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("e11-one-function-per-opcode")

gallery.add(
    figures.flow(
        "one-case-becomes-one-function",
        [
            "bytecodes.c, one case per opcode",
            "generated_cases.c.h, still one case per opcode",
            "TARGET(LOAD_FAST) expands to a function header",
            "_TAIL_CALL_LOAD_FAST, a function of its own",
            "slot 83 in a table of 256 function pointers",
        ],
        title="Where the function for one opcode comes from",
        labels=[
            "a build step",
            "the same text either way",
            "only in this build",
            "filled in by the generator",
        ],
        tones=["input", "intermediate", "focus", "focus", "durable"],
    )
)


gallery.add(
    figures.table(
        "the-same-file-three-endings",
        ["how the build was configured", "what one opcode is", "how it reaches the next one"],
        [
            ["plain C", "a case in a switch", "goto the top of the switch"],
            ["computed gotos", "a label in one function", "goto *table[opcode]"],
            ["tail calls", "a function of its own", "return table[opcode](args)"],
        ],
        title="One source file, three ways of stitching it together",
        caption="Same generated_cases.c.h in all three. The macros around it differ.",
        tones=["quiet", "quiet", "focus"],
    )
)


gallery.add(
    figures.compare(
        "what-must-tail-means",
        (
            "an ordinary call",
            [
                "pushes a return address",
                "the caller waits for the result",
                "the C stack gets one frame deeper",
                "a million in a row overflows it",
            ],
        ),
        (
            "a call marked musttail",
            [
                "pushes nothing",
                "the caller is finished already",
                "the frame is reused, not stacked",
                "a million in a row is a loop",
            ],
        ),
        title="Why one opcode can call the next one forever",
        verdict="If the compiler cannot do it as a jump, the build fails rather than running slowly.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.table(
        "two-hundred-and-fifty-six-slots",
        ["what is in the slot", "on 3.15", "on 3.14"],
        [
            ["a real opcode", "234", "227"],
            ["_TAIL_CALL_UNKNOWN_OPCODE", "22", "29"],
            ["slots in the table", "256", "256"],
        ],
        title="The dispatch table is always full",
        caption="A byte has 256 values, so every one of them has to lead somewhere.",
        tones=["focus", "quiet", "durable"],
    )
)


gallery.add(
    figures.table(
        "the-bill-is-per-instruction",
        ["the same job, written three ways", "instructions", "nanoseconds", "each"],
        [
            ["a while loop", "20012", "19930", "1.00"],
            ["a for loop", "10008", "9901", "0.99"],
            ["a comprehension", "6011", "6474", "1.08"],
        ],
        title="Building a list of a thousand items",
        caption="Three times the instructions, three times the time. The rate barely moves.",
        tones=["quiet", "quiet", "focus"],
    )
)


gallery.add(
    figures.compare(
        "why-it-is-not-slower",
        (
            "one enormous function",
            [
                "one set of registers, shared",
                "the compiler plans for the worst",
                "spare values get pushed to memory",
            ],
        ),
        (
            "one small function each",
            [
                "its own set of registers",
                "the compiler sees one case only",
                "six values stay in registers",
            ],
        ),
        title="The reason this is faster has nothing to do with calls",
        verdict="The call is close to free. What you save is everything that was not in a register.",
        verdict_tone="focus",
    )
)


raise SystemExit(gallery.save())
