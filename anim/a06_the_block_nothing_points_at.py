"""How the compiler works out that some of your code can never run, and deletes it.

T05 spends a section on this and the section has a still picture in it, which is the wrong
medium for it. The whole idea is that something goes away: an arrow disappears, and then a
block of instructions that nothing points at any more disappears with it. A still picture
can show the before or the after and has to describe the step in a caption.

The example is smaller than the one in the lesson. The lesson uses `print` calls, and those
compile to five instructions each, which is three blocks of text too wide to read at this
size. This one assigns a number instead, so the dead block is two instructions and the whole
thing is eleven, and the eleven fit on screen at a size somebody can read on a phone.

    if False: x = 1
    y = 2

That is the same bytecode as the indented three line version, which is worth saying because
it looks like a trick to save a line. It is not: `compile()` gives byte for byte identical
code either way, and there is a test in this package that says so.

The instruction listings are real, from `pyxray.compiler.stages` on 3.15.0rc1. What is not
literal is the arguments: the code generator emits `LOAD_CONST 0`, and this shows
`LOAD_CONST False`, which is the value `dis` prints in brackets beside the index. An index
into a table the viewer cannot see tells them nothing, and the whole beat turns on `False`
being a constant.
"""

from __future__ import annotations

from manim import DOWN, RIGHT, UP, FadeIn, FadeOut, VGroup

from xraymanim.catalogue import THE_BLOCK_NOTHING_POINTS_AT
from xraymanim.grammar import UNIT
from xraymanim.primitives import arrow, box, highlight, slots
from xraymanim.scene import Explainer

#: The two statements, one per box, as they are written.
SOURCE = ("if False: x = 1", "y = 2")

#: What the code generator emits, before the optimizer has looked at it. Eleven, in order.
GENERATED = (
    "RESUME 0",
    "ANNOTATIONS_PLACEHOLDER",
    "LOAD_CONST False",
    "TO_BOOL",
    "POP_JUMP_IF_FALSE",
    "LOAD_CONST 1",
    "STORE_NAME x",
    "LOAD_CONST 2",
    "STORE_NAME y",
    "LOAD_CONST None",
    "RETURN_VALUE",
)

#: The same eleven, cut where a jump lands or leaves. The first block ends at the jump, the
#: second is the body of the `if`, and the third is everything after it. Written out rather
#: than sliced out of the tuple above, so a test can read them without running this file and
#: check that the three of them really are the eleven and nothing else.
ENTRY = (
    "RESUME 0",
    "ANNOTATIONS_PLACEHOLDER",
    "LOAD_CONST False",
    "TO_BOOL",
    "POP_JUMP_IF_FALSE",
)
BODY = ("LOAD_CONST 1", "STORE_NAME x")
AFTER = ("LOAD_CONST 2", "STORE_NAME y", "LOAD_CONST None", "RETURN_VALUE")

#: The entry block after `TO_BOOL` folds, and then after the jump stops being conditional.
FOLDED = ("RESUME 0", "ANNOTATIONS_PLACEHOLDER", "LOAD_CONST False", "POP_JUMP_IF_FALSE")
JUMPING = ("RESUME 0", "ANNOTATIONS_PLACEHOLDER", "LOAD_CONST False", "JUMP")

#: And what actually comes out, which is six. `LOAD_SMALL_INT` rather than `LOAD_CONST`
#: because the optimizer knows small integers are already made, and `NOP` is the placeholder
#: with nothing to put in it.
#:
#: Note what is not claimed here. The name `x` is still in the code object's names table,
#: because names are collected while the code is generated and nobody goes back to tidy the
#: table afterwards. What is gone is every instruction that could store into it, which is
#: what the last caption says and is not quite the same sentence.
FINAL = (
    "RESUME 0",
    "NOP",
    "LOAD_SMALL_INT 2",
    "STORE_NAME y",
    "LOAD_COMMON_CONSTANT None",
    "RETURN_VALUE",
)

#: One row per instruction. Eleven of them in a single column has to fit between the title
#: and the caption, which is what sets this.
ROW = 0.36
BLOCK_WIDTH = 3.8

#: Where the three blocks sit once the list has been cut up. Left to right, in the order
#: control reaches them, so the jump that skips the middle one arcs forward over it and
#: reads as skipping something rather than as going backward.
LEFT_X = -5.0
MIDDLE_X = 0.0
RIGHT_X = 5.0
BLOCK_Y = -0.55

#: How far above the blocks the jump arc goes. It has to clear the middle block, because a
#: jump drawn through the thing it skips is a picture of the opposite of what it does, and
#: it has to stay under the source at the top, because an arrow touching the code looks like
#: it is pointing at it. It bows upward, over the block it skips, rather than sagging
#: through the gap under it, which is a picture of going around something rather than past.

#: Where the arrow counts go. Under the blocks rather than over them, because over them is
#: where the jump arc is, and a number sitting on an arrow is two things to read at once.
ARC_LIFT = 0.35
TALLY_Y = -2.15
ARC_BEND = -0.6

SOURCE_Y = 1.75


class A06TheBlockNothingPointsAt(Explainer):
    storyboard = THE_BLOCK_NOTHING_POINTS_AT

    def construct(self) -> None:
        source = VGroup(
            *(box(line, tone="input", width=4.0, height=0.55, mono=True) for line in SOURCE)
        )
        source[0].move_to([-2.2, SOURCE_Y, 0])
        source[1].move_to([2.2, SOURCE_Y, 0])

        flat = self.rows(GENERATED)
        flat.move_to([0, BLOCK_Y, 0])

        seconds = self.beat()
        self.play(FadeIn(source), run_time=0.5)
        self.play(FadeIn(flat), run_time=0.7)
        self.wait(max(seconds - 1.2, 0.4))

        # The cut. Fading the flat list out and the three blocks in, rather than sliding the
        # rows apart, because the rows do not move to where they are going: they change
        # width and get a border each. A transform between those two is a smear.
        self.entry = self.block(ENTRY, LEFT_X)
        self.body = self.block(BODY, MIDDLE_X)
        self.after = self.block(AFTER, RIGHT_X)
        blocks = VGroup(self.entry, self.body, self.after)

        seconds = self.beat()
        self.play(FadeOut(flat), run_time=0.4)
        self.play(FadeIn(blocks), run_time=0.7)
        self.wait(max(seconds - 1.1, 0.4))

        # Two ways out of the entry block, which is the whole reason there are three blocks
        # and not one. The straight arrow is the case where the test fails and control falls
        # into the next block. The arc is the jump.
        self.fall = arrow(self.entry, self.body, owned=False, tone="quiet", direction=RIGHT)
        self.onward = arrow(self.body, self.after, owned=False, tone="quiet", direction=RIGHT)
        # Given as two points rather than as two blocks, because an arrow between blocks
        # leaves from the middle of one edge and arrives at the middle of another, and the
        # middle block is in the way of that line. This one leaves from above.
        self.jump = arrow(
            [LEFT_X + 1.2, self.entry.get_top()[1] + ARC_LIFT, 0],
            [RIGHT_X - 1.2, self.after.get_top()[1] + ARC_LIFT, 0],
            owned=False,
            tone="focus",
            bend=ARC_BEND,
        )

        seconds = self.beat()
        self.play(FadeIn(self.fall), FadeIn(self.onward), FadeIn(self.jump), run_time=0.9)
        self.wait(max(seconds - 0.9, 0.4))

        self.fold(FOLDED)
        self.fold(JUMPING)

        # The arrow goes, and nothing else moves. That stillness is the point: the middle
        # block is exactly as it was, and it is now unreachable anyway.
        seconds = self.beat()
        self.play(FadeOut(self.fall), run_time=0.7)
        self.wait(max(seconds - 0.7, 0.4))

        self.count()

        seconds = self.beat()
        self.play(FadeOut(self.body), FadeOut(self.onward), run_time=0.9)
        self.wait(max(seconds - 0.9, 0.4))

        final = self.rows(FINAL)
        final.move_to([0, BLOCK_Y, 0])
        mark = highlight(final, tone="durable")
        seconds = self.beat()
        self.play(FadeOut(self.entry), FadeOut(self.after), FadeOut(self.jump), run_time=0.5)
        self.play(FadeIn(final), FadeIn(mark), run_time=0.7)
        self.wait(max(seconds - 1.2, 0.5))

    def rows(self, instructions: tuple[str, ...]) -> VGroup:
        """One instruction per cell, touching, because a basic block runs straight through."""
        return slots(instructions, tone="quiet", width=BLOCK_WIDTH, height=ROW, columns=1)

    def block(self, instructions: tuple[str, ...], x: float) -> VGroup:
        """A basic block: the instructions, with a border saying where it starts and ends."""
        inside = self.rows(instructions)
        drawn = VGroup(inside, highlight(inside, tone="intermediate"))
        drawn.move_to([x, BLOCK_Y, 0])
        return drawn

    def fold(self, instructions: tuple[str, ...]) -> None:
        """Redraw the entry block with one fewer instruction, or one different one.

        Redrawn rather than edited, because the border has to shrink with the instructions
        and manim will not resize a rectangle and reflow what is inside it in one move. It
        stays centred where it was, so the two arrows leaving it stay attached to it.
        """
        seconds = self.beat()
        wanted = self.block(instructions, LEFT_X)
        going = self.entry
        self.entry = wanted
        self.play(FadeOut(going), run_time=0.35)
        self.play(FadeIn(self.entry), run_time=0.45)
        self.wait(max(seconds - 0.8, 0.4))

    def count(self) -> None:
        """The pass itself: walk from the entry block, count the arrows arriving at each one.

        Drawn as the tally the pass keeps, above each block, because the number is the whole
        decision. The entry block is reachable by definition, the last block has two arrows
        arriving at this point, and the middle one has none.
        """
        seconds = self.beat()
        tally = VGroup(
            *(
                box(text, tone=tone, width=1.5, height=0.5, mono=True).move_to([x, TALLY_Y, 0])
                for text, tone, x in (
                    ("entry", "durable", LEFT_X),
                    ("in: 0", "focus", MIDDLE_X),
                    ("in: 2", "durable", RIGHT_X),
                )
            )
        )
        self.play(FadeIn(tally, shift=UP * UNIT), run_time=0.8)
        self.wait(max(seconds - 0.8, 0.4))
        self.play(FadeOut(tally, shift=DOWN * UNIT), run_time=0.4)
