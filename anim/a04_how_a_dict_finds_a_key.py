"""What happens between `d[9]` and the answer, in a dict that has a collision in it.

Most pictures of a dict draw one table of key and value pairs, and that picture cannot
explain either of the two things people actually ask about dicts: why they keep insertion
order, and what a collision costs. CPython has not stored a dict that way since 3.6. There
is a small array of slot numbers, and there are the entries in the order they went in, and
almost everything interesting follows from the split.

The dict is `{1: "one", 5: "five", 9: "nine"}`, chosen because integers hash to themselves,
so nothing here depends on the hash randomization that would make string keys land in a
different slot on every run. With eight slots the mask is 7, key 1 wants slot 1, key 5 wants
slot 5, and key 9 wants slot 1 as well, which is the collision.

The index array on screen is `[-1, 0, -1, -1, -1, 1, 2, -1]`, and that is not derived from
the probing rule, it was read out of a live 3.15.0rc1 interpreter through `ctypes` at the
address of the dict. The tests next to this file do the same read and would fail if CPython
ever laid it out differently.
"""

from __future__ import annotations

from manim import DOWN, LEFT, RIGHT, FadeIn, FadeOut, Transform, VGroup

from xraymanim.catalogue import HOW_A_DICT_FINDS_A_KEY
from xraymanim.grammar import UNIT
from xraymanim.mobjects import DictTable
from xraymanim.primitives import arrow, box, highlight
from xraymanim.scene import Explainer

SOURCE = 'd = {1: "one", 5: "five", 9: "nine"}'

#: The real index array, read from a live interpreter. -1 is DKIX_EMPTY, and a number is the
#: position of the entry in the entries array, not the key and not the value.
INDICES = (-1, 0, -1, -1, -1, 1, 2, -1)

#: The entries, in the order they were written, which is the order the dict will hand back.
ENTRIES = (("1", "'one'"), ("5", "'five'"), ("9", "'nine'"))

#: How each slot is written on screen. An empty slot says so rather than showing -1, because
#: -1 is a detail of how CPython stores "nothing here" and is not what the slot means.
SLOT_LABELS = tuple("-" if index < 0 else str(index) for index in INDICES)

#: The table is tall, because eight slots stacked up is eight slots stacked up. So the
#: sentence, the question and the answer all live in the column to the left of it rather
#: than above and below, which is the only way this fits in a wide frame.
TABLE_X = 2.4
TABLE_Y = -0.3
SIDE_X = -3.6


class A04HowADictFindsAKey(Explainer):
    storyboard = HOW_A_DICT_FINDS_A_KEY

    def construct(self) -> None:
        source = box(SOURCE, tone="input", width=6.6, height=0.8, mono=True)
        source.move_to([SIDE_X, 2.3, 0])

        self.table = DictTable(ENTRIES, index=SLOT_LABELS, tone="durable")
        self.table.scale(0.84).move_to([TABLE_X, TABLE_Y, 0])

        self.play(FadeIn(source), run_time=0.5)
        self.show(FadeIn(self.table))

        self.spot = highlight(self.table.entries, tone="durable")
        self.show(FadeIn(self.spot))

        self.show(Transform(self.spot, highlight(self.table.index, tone="quiet")))

        # The hash is the number itself for a small int, and the mask is seven, so this is
        # one bitwise and rather than anything the reader has to take on trust.
        hashed = box("d[9]", tone="focus", width=2.4, height=0.8, mono=True, note="hash(9) & 7 = 1")
        hashed.move_to([SIDE_X, 0.7, 0])
        self.show(
            FadeIn(hashed, shift=DOWN * UNIT),
            Transform(self.spot, highlight(self.slot(1), tone="focus")),
        )

        # No words on the arrow. It leaves at an angle, so a label beside it lands on top
        # of the index array, and the caption underneath is already saying which key it is.
        wrong = arrow(self.slot(1), self.entry(0), tone="warning", direction=RIGHT)
        self.show(FadeIn(wrong))

        self.show(
            FadeOut(wrong),
            Transform(self.spot, highlight(self.slot(6), tone="focus")),
        )

        right = arrow(self.slot(6), self.entry(2), tone="focus", direction=RIGHT)
        found = box("'nine'", tone="focus", width=2.4, height=0.8, mono=True, note="the answer")
        found.move_to([SIDE_X, -1.2, 0])
        self.show(FadeIn(right), FadeIn(found, shift=LEFT * UNIT))

        both = VGroup(
            highlight(self.slot(1), tone="warning"),
            highlight(self.slot(6), tone="focus"),
        )
        self.show(FadeOut(self.spot), FadeIn(both))

    def slot(self, index: int) -> VGroup:
        """One cell of the index array, which is the thing a lookup actually reads first."""
        return self.table.index.submobjects[index]

    def entry(self, index: int) -> VGroup:
        """One entry, in insertion order, which is where the key and the value really live."""
        return self.table.entries.submobjects[index]

    def show(self, *animations: object) -> None:
        """Play one beat's worth of change, then hold while the reader takes it in."""
        seconds = self.beat()
        self.play(*animations, run_time=min(seconds * 0.4, 1.0))
        self.wait(max(seconds - 1.0, 0.5))
