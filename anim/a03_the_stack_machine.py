"""One call to a two line function, one instruction at a time, with the stack on screen.

The hard part of the eval loop for a beginner is not the loop, it is the stack. Reading a
disassembly listing tells you nothing about it, because the listing shows what each
instruction is called and not what it does to the pile of values underneath. So this shows
the pile, and lets the listing sit above it with a pointer walking along.

The function is `def area(w): return w * 2 + 1`, called with 6, which gives 13. It was
chosen for its stack profile rather than for what it computes: the depth goes 0, 1, 2, 1, 2,
1, and those two climbs and two drops are the whole idea.

The instructions and the depths came from `pyxray.stack.walk` on 3.15.0rc1. `LOAD_FAST_BORROW`
really is what the compiler emits for `w` here rather than `LOAD_FAST`, and it is left as it
is, because a reader who disassembles this function themselves should see what we showed them.
"""

from __future__ import annotations

from manim import DOWN, RIGHT, FadeIn, FadeOut, Transform

from xraymanim.catalogue import THE_STACK_MACHINE
from xraymanim.grammar import UNIT
from xraymanim.mobjects import CodeStrip, Frame
from xraymanim.primitives import box
from xraymanim.scene import Explainer

SOURCE = "def area(w): return w * 2 + 1"

#: The instructions as `dis` prints them, in order, from a real 3.15.0rc1 run.
INSTRUCTIONS = (
    "RESUME 0",
    "LOAD_FAST_BORROW w",
    "LOAD_SMALL_INT 2",
    "BINARY_OP *",
    "LOAD_SMALL_INT 1",
    "BINARY_OP +",
    "RETURN_VALUE",
)

#: What the value stack holds after each of those instructions, first item at the bottom of
#: the pile. The depths are from `pyxray.stack.walk`, so they are the compiler's own numbers
#: rather than a guess, and the values are what a call with w = 6 actually pushes.
STACKS = (
    (),
    ("6",),
    ("6", "2"),
    ("12",),
    ("12", "1"),
    ("13",),
    ("13",),
)

SOURCE_Y = 2.35
CODE_Y = 0.95
FRAME_X = -0.4
RETURN_X = 4.4
FLOOR_Y = -2.7


class A03TheStackMachine(Explainer):
    storyboard = THE_STACK_MACHINE

    def construct(self) -> None:
        source = box(SOURCE, tone="input", width=7.4, height=0.7, mono=True)
        source.move_to([0, SOURCE_Y, 0])

        self.strip = CodeStrip(INSTRUCTIONS, at=0, rows=2)
        self.strip.scale_to_fit_width(11.0).move_to([0, CODE_Y, 0])
        self.play(FadeIn(source), FadeIn(self.strip), run_time=0.6)

        # The frame arrives on the first beat rather than with the code, because the first
        # caption is about the call happening. Before the call there is no frame, and a
        # picture that shows one anyway has answered a question nobody asked yet.
        self.frame = self.frame_at(0)
        seconds = self.beat()
        self.play(FadeIn(self.frame), run_time=0.8)
        self.wait(max(seconds - 0.8, 0.4))

        # One beat per instruction, except the last. RETURN_VALUE gets its own ending,
        # because what it does is take the frame away, and that is not a change to the
        # picture the loop knows how to make.
        for index in range(len(INSTRUCTIONS) - 1):
            self.step(index)

        returned = box(
            "13", tone="focus", width=2.4, height=0.8, mono=True, note="back to the caller"
        )
        returned.move_to([RETURN_X, FLOOR_Y + 1.2, 0])
        seconds = self.beat()
        self.play(
            Transform(self.strip.pointer, self.strip.at(len(INSTRUCTIONS) - 1)),
            FadeOut(self.frame, shift=DOWN * UNIT),
            FadeIn(returned, shift=RIGHT * UNIT),
            run_time=1.0,
        )
        self.wait(max(seconds - 1.0, 0.6))

    def step(self, index: int) -> None:
        """Run one instruction: move the pointer, and redraw the frame with the new stack."""
        seconds = self.beat()
        wanted = self.frame_at(index)
        self.play(
            Transform(self.strip.pointer, self.strip.at(index)),
            FadeOut(self.frame),
            run_time=min(seconds * 0.3, 0.6),
        )
        self.frame = wanted
        self.play(FadeIn(self.frame), run_time=0.4)
        self.wait(max(seconds - 1.0, 0.4))

    def frame_at(self, index: int) -> Frame:
        """The frame as it stands after instruction `index`, sitting on a floor that stays put.

        A new one each time rather than one that is edited, because the frame gets taller as
        the stack does, and cross fading two of them keeps the floor still while the top of
        the box moves. That is the right way round: a value stack grows upward.
        """
        made = Frame("area", {"w": "6"}, STACKS[index], width=6.2)
        made.scale(0.8).move_to([FRAME_X, FLOOR_Y, 0], aligned_edge=DOWN)
        return made
