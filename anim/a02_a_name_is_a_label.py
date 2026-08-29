"""What `a = []` and `b = a` and `del a` actually do to one list.

The single most useful thing a beginner can be shown about Python is that a name is not a
container. This is that, in seven steps, with the reference count on screen the whole time
so the connection between "how many names point at it" and "when does it go away" is
visible rather than asserted.

The counts here are the object's own, the ones CPython keeps in `ob_refcnt`. They are not
what `sys.getrefcount` prints, because asking the question passes the object to a function
and that is one more reference while the call is running. T08 does that experiment. This
animation stays with the object.
"""

from __future__ import annotations

from manim import LEFT, FadeIn, FadeOut, Transform, VGroup

from xraymanim.catalogue import A_NAME_IS_A_LABEL
from xraymanim.grammar import UNIT
from xraymanim.mobjects import PyObjectBox, RefArrow
from xraymanim.primitives import box, highlight
from xraymanim.scene import Explainer

NAME_X = -4.6
OBJECT_X = 1.9
OBJECT_Y = -0.3
TOP_Y = 0.7
BOTTOM_Y = -1.3


class A02ANameIsALabel(Explainer):
    storyboard = A_NAME_IS_A_LABEL

    def construct(self) -> None:
        thing = PyObjectBox("list", "[]", 1, tone="durable", width=4.2)
        thing.move_to([OBJECT_X, OBJECT_Y, 0])
        first = self.name("a", TOP_Y)
        tie = RefArrow(first, thing, text="owns it")
        self.show(FadeIn(first), FadeIn(thing), FadeIn(tie))

        # The second beat is the argument of the whole animation, so it gets two movements
        # rather than one: look at the name, now look at the thing joining it to the object.
        # The reader is being asked to see two things where they had assumed there was one.
        seconds = self.beat()
        spot = highlight(first)
        self.play(FadeIn(spot), run_time=0.4)
        self.play(Transform(spot, highlight(tie.body.line)), run_time=0.8)
        self.wait(max(seconds - 2.0, 0.5))
        self.play(FadeOut(spot), run_time=0.4)

        second = self.name("b", BOTTOM_Y)
        also = RefArrow(second, thing, text="owns it too")
        self.show(
            FadeIn(second),
            FadeIn(also),
            Transform(thing.count, thing.refcount(2)),
        )

        counted = highlight(thing.count)
        self.show(FadeIn(counted))

        self.show(
            FadeOut(first, shift=LEFT * UNIT),
            FadeOut(tie),
            Transform(thing.count, thing.refcount(1)),
        )

        self.show(Transform(counted, highlight(thing.count, tone="warning")))

        freed = box("freed", tone="warning", width=4.2, note="the memory goes back")
        freed.move_to(thing.get_center())
        self.show(
            FadeOut(second, shift=LEFT * UNIT),
            FadeOut(also),
            FadeOut(counted),
            FadeOut(thing),
            FadeIn(freed),
        )

    def name(self, text: str, y: float) -> VGroup:
        """One name, drawn as a plain box, on the left where the names live."""
        made = box(text, tone="input", width=1.3, height=0.8, mono=True)
        return made.move_to([NAME_X, y, 0])

    def show(self, *animations: object) -> None:
        """Play one beat's worth of change, then hold while the reader takes it in.

        The hold is not padding. Every one of these beats ends with the picture in a state
        the next caption is about to talk about, and a reader who is still watching things
        move has not looked at it yet.
        """
        seconds = self.beat()
        self.play(*animations, run_time=min(seconds * 0.5, 1.2))
        self.wait(max(seconds - 1.2, 0.5))
