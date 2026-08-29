"""One line of Python, followed through all eight artifacts.

This is the animated version of the map T01 opens with. The rail across the top is the same
eight boxes the reader sees in every lesson, and everything below it is whatever that stage
actually produces for `answer = 6 * 7`.

Every artifact on screen is real. The tokens are what `tokenize` returns, the tree is what
`ast.parse` builds, and the two instruction listings are what the code generator emits and
what the optimizer leaves behind, taken from `pyxray.compiler.stages` on 3.15.0rc1 rather
than typed out from memory. An animation that gets the bytecode slightly wrong is worse
than no animation, because the reader has no way to check it while they are watching.
"""

from __future__ import annotations

from manim import DOWN, UP, FadeIn, FadeOut, Transform, VGroup

from xraymanim.catalogue import SEVEN_STAGES
from xraymanim.grammar import UNIT
from xraymanim.mobjects import CodeStrip
from xraymanim.primitives import arrow, box, highlight, slots, stream, tree
from xraymanim.scene import Explainer

#: The eight artifacts, in the order they appear, with the same names the diagrams use.
RAIL = (
    "text",
    "tokens",
    "tree",
    "names",
    "instructions",
    "optimized",
    "code object",
    "answer",
)

SOURCE = "answer = 6 * 7"

#: What `tokenize` gives back for that line, minus the encoding marker and the end marker,
#: which are real tokens and are not what this beat is about.
TOKENS = ("NAME answer", "OP =", "NUMBER 6", "OP *", "NUMBER 7", "NEWLINE")

#: `ast.parse("answer = 6 * 7")`, with the constants written the way they print.
TREE = (
    "Module",
    [("Assign", [("Name answer", []), ("BinOp *", [("Constant 6", []), ("Constant 7", [])])])],
)

#: Straight out of the code generator, before anything has been optimized. The placeholder
#: is a real pseudo instruction and it is shown because it is there.
CODEGEN = (
    "RESUME 0",
    "ANNOTATIONS_PLACEHOLDER",
    "LOAD_CONST 0",
    "LOAD_CONST 1",
    "BINARY_OP 5",
    "STORE_NAME 0",
    "LOAD_CONST 2",
    "RETURN_VALUE",
)

#: What is left after the optimizer. Three instructions became one, and the multiply is gone.
OPTIMIZED = (
    "RESUME 0",
    "LOAD_SMALL_INT 42",
    "STORE_NAME 0",
    "LOAD_COMMON_CONSTANT 7",
    "RETURN_VALUE",
)

RAIL_Y = 1.7
ARTIFACT_Y = -1.4
RAIL_WIDTH = 12.4


class A01SevenStages(Explainer):
    storyboard = SEVEN_STAGES

    def construct(self) -> None:
        rail = stream(RAIL, tone="quiet")
        rail.scale_to_fit_width(RAIL_WIDTH).move_to([0, RAIL_Y, 0])
        self.play(FadeIn(rail), run_time=0.5)

        self.spot = highlight(rail.chips[0])
        self.feed = arrow(rail.chips[0], [0, ARTIFACT_Y + 1.2, 0], tone="quiet", direction=DOWN)
        self.rail = rail
        self.showing = VGroup()
        self.add(self.spot, self.feed, self.showing)

        self.stage(0, box(SOURCE, tone="input", width=5.4, mono=True, note="the text you wrote"))
        self.stage(1, stream(TOKENS, tone="input"))
        self.stage(2, tree(TREE, tone="intermediate"))
        self.stage(3, slots(("answer", "module global"), tone="intermediate", width=3.0))
        self.stage(4, CodeStrip(CODEGEN, rows=3, at=4))
        self.stage(5, CodeStrip(OPTIMIZED, at=1))
        self.stage(6, box("code object", tone="durable", width=4.6, note="the part that survives"))
        self.stage(7, box("42", tone="focus", width=2.4, mono=True, note="answer"))

    def stage(self, index: int, artifact: VGroup) -> None:
        """Move the rail highlight to one stage and show what that stage produces."""
        seconds = self.beat(index)
        artifact.move_to([0, ARTIFACT_Y, 0])
        if artifact.width > RAIL_WIDTH:
            artifact.scale_to_fit_width(RAIL_WIDTH)
        if artifact.height > 3.0:
            artifact.scale_to_fit_height(3.0)

        chip = self.rail.chips[index]
        moving = [
            Transform(self.spot, highlight(chip)),
            Transform(self.feed, arrow(chip, artifact, tone="quiet", direction=DOWN)),
        ]
        if self.showing.submobjects:
            going = self.showing.submobjects[0]
            self.showing.remove(going)
            moving.append(FadeOut(going, shift=DOWN * UNIT))
        self.showing.add(artifact)
        moving.append(FadeIn(artifact, shift=UP * UNIT))
        self.play(*moving, run_time=min(seconds, 1.0))
        self.wait(max(seconds - 1.0, 0.4))
