#!/usr/bin/env python
"""The diagrams for E10, copy and patch and the machine code it hands you.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The two doing the real work are `where-the-machine-code-comes-from`, which is the whole
build time story on one page, and `what-goes-in-a-hole`, which is the only part that
happens while your program is running. The rest are measurements, drawn.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("e10-the-compiler-that-finished-before-you-started")

gallery.add(
    figures.flow(
        "where-the-machine-code-comes-from",
        [
            "bytecodes.c, written by hand",
            "executor_cases.c.h, generated from it",
            "one small C file per micro operation",
            "clang -Os, one object file each",
            "jit_stencils.h, shipped inside the build",
            "your trace, pasted together while it runs",
        ],
        title="Six steps, and only the last one happens on your machine",
        labels=[
            "a build step",
            "one CASE at a time",
            "at build time",
            "still at build time",
            "months earlier",
        ],
        tones=["input", "input", "focus", "focus", "durable", "warning"],
    )
)


gallery.add(
    figures.flow(
        "size-first-then-bytes",
        [
            "walk the trace, add up one fixed size per micro operation",
            "ask the operating system for that many bytes, rounded to a page",
            "walk the trace again, copy each chunk into place",
            "fill in the addresses that were left blank",
            "make it executable and stop being able to write to it",
        ],
        title="What _PyJIT_Compile does, start to finish",
        labels=[
            "nothing written yet",
            "one allocation",
            "the copy",
            "the patch",
        ],
        tones=["input", "intermediate", "focus", "focus", "durable"],
    )
)


gallery.add(
    figures.table(
        "the-code-grows-in-a-straight-line",
        ["additions in the loop", "micro operations", "bytes of machine code", "difference"],
        [
            ["1", "31", "1277", ""],
            ["2", "36", "1597", "320"],
            ["3", "41", "1917", "320"],
            ["4", "46", "2237", "320"],
            ["6", "56", "2877", "640"],
            ["10", "76", "4157", "1280"],
        ],
        title="The same loop, with more additions in it each time",
        caption="Five more micro operations costs 320 more bytes, every single time.",
        tones=["quiet", "quiet", "quiet", "quiet", "focus", "focus"],
    )
)


gallery.add(
    figures.table(
        "what-goes-in-a-hole",
        ["the blank", "what gets written into it", "why it could not be known earlier"],
        [
            ["_JIT_OPERAND0", "the address of an object", "the object did not exist yet"],
            ["_JIT_OPARG", "the argument of this instruction", "the trace did not exist yet"],
            ["_JIT_TARGET", "where to resume in the bytecode", "depends on this trace"],
            ["_JIT_CONTINUE", "the address of the next chunk", "depends on where it landed"],
            ["_JIT_JUMP_TARGET", "the address of a chunk further on", "same reason"],
            ["_JIT_ERROR_TARGET", "the address of the error chunk", "same reason"],
        ],
        title="The blanks left in a stencil, and who fills them",
        caption="Every one of them is an address, and addresses are the one thing a build cannot know.",
        tones=["focus", "quiet", "quiet", "durable", "durable", "durable"],
    )
)


gallery.add(
    figures.compare(
        "two-loops-one-number-different",
        (
            "total += ONE",
            [
                "35 micro operations",
                "1637 bytes of machine code",
                "the address of ONE at byte 1448",
            ],
        ),
        (
            "total += TWO",
            [
                "35 micro operations",
                "1637 bytes of machine code",
                "the address of TWO at byte 1448",
            ],
        ),
        title="Two loops that differ in one name",
        verdict="22 bytes out of 1637 are different. The other 1615 were compiled months ago.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.stack(
        "then-it-stops-being-writable",
        [
            "mprotect, read and execute",
            "flush the instruction cache",
            "patch the blanks",
            "copy the chunks in",
            "mmap, read and write",
        ],
        title="The life of one page of JIT memory, oldest at the bottom",
        note="It is never writable and executable at the same time, which is the whole point.",
    )
)


raise SystemExit(gallery.save())
