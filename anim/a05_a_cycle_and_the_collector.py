"""Two objects that keep each other alive, and the pass that notices.

Reference counting is easy to explain and it is right nearly all of the time, so the honest
next question is when it is wrong. This is the case: two objects that hold each other. Take
the names away and both counts drop, but neither drops to zero, because each object is still
being pointed at by the other one. Nothing is left that can reach them, and nothing will free
them either.

The numbers here are from a real 3.15.0rc1 run. With both names bound each object's count is
2, one from the name and one from the other object's attribute. After `del a, b` each count
is 1, read straight out of the header with `ctypes` so that nothing in the measurement is
itself holding a reference. `gc.collect()` then reports 2, which is these two and nothing
else.

The second half is the collector's trick, and it is smaller than people expect. It copies
each count into a scratch field, then walks every reference from one tracked object to
another and takes one off the copy at the far end. A copy that reaches zero means every
reference to that object came from inside the group, so nothing outside can reach it.
"""

from __future__ import annotations

import numpy as np
from manim import LEFT, FadeIn, FadeOut, Transform, VGroup

from xraymanim.catalogue import A_CYCLE_AND_THE_COLLECTOR
from xraymanim.mobjects import ArenaMap, PyObjectBox, RefArrow
from xraymanim.primitives import box, counter, graph, highlight
from xraymanim.scene import Explainer

SOURCE = "a = Node(); b = Node(); a.other = b; b.other = a"

#: One row of a pool. The two stars are the pair this animation is about, and the rest is
#: there so that freeing them reads as two blocks going back to a pool rather than as the
#: whole of memory being handed back, which is not what happens.
POOL_BEFORE = "##*###*#....#..."
POOL_AFTER = "##.###.#....#..."
POOL_LABEL = "the pool these two live in"

OBJECT_Y = 0.9
#: Wide enough that `ob_type: Node` and the count are not fighting over the same space,
#: then scaled down so that the two of them plus the arrows between them still fit.
OBJECT_WIDTH = 4.4
OBJECT_SCALE = 0.88
OBJECT_X = 3.75
NAME_X = 6.9
GC_Y = -0.7
POOL_Y = -2.2

#: How far the two arrows between the objects curve, in radians. Straight they would be one
#: line drawn twice, because the pair points both ways along the same gap.
BEND = 0.9


class A05ACycleAndTheCollector(Explainer):
    storyboard = A_CYCLE_AND_THE_COLLECTOR

    def construct(self) -> None:
        source = box(SOURCE, tone="input", width=9.4, height=0.75, mono=True)
        source.move_to([0, 2.2, 0])

        self.pool = ArenaMap(POOL_BEFORE, columns=16, label_text=POOL_LABEL)
        self.pool.move_to([0, POOL_Y, 0])
        self.play(FadeIn(source), FadeIn(self.pool), run_time=0.6)

        # The picture people already have, first. Two things, two arrows, no counts. Beat 2
        # replaces it with what CPython actually holds, and putting them one after the other
        # is the point: the familiar picture is not wrong, it is just missing the field that
        # decides when either of them is freed.
        sketch = graph(
            {"a": (-2.4, OBJECT_Y), "b": (2.4, OBJECT_Y)},
            [("a", "b"), ("b", "a")],
            tone="quiet",
            bend=BEND,
        )
        self.hold(FadeIn(sketch))

        self.left = PyObjectBox("Node", refcount=2, width=OBJECT_WIDTH)
        self.left.scale(OBJECT_SCALE).move_to([-OBJECT_X, OBJECT_Y, 0])
        self.right = PyObjectBox("Node", refcount=2, width=OBJECT_WIDTH)
        self.right.scale(OBJECT_SCALE).move_to([OBJECT_X, OBJECT_Y, 0])
        self.cycle = VGroup(
            RefArrow(self.left.shell, self.right.shell, text="a.other", bend=BEND),
            RefArrow(self.right.shell, self.left.shell, text="b.other", bend=BEND, direction=LEFT),
        )
        self.names = VGroup(
            RefArrow(np.array([-NAME_X, OBJECT_Y, 0.0]), self.left.shell, text="a"),
            RefArrow(np.array([NAME_X, OBJECT_Y, 0.0]), self.right.shell, text="b", direction=LEFT),
        )
        self.hold(
            FadeOut(sketch),
            FadeIn(self.left),
            FadeIn(self.right),
            FadeIn(self.cycle),
            FadeIn(self.names),
        )

        self.hold(FadeOut(self.names))

        on_the_count = highlight(self.left.count, tone="warning")
        self.hold(
            Transform(self.left.count, self.left.refcount(1)),
            Transform(self.right.count, self.right.refcount(1)),
            FadeIn(on_the_count),
        )

        # The scratch counts go under each object rather than inside it, because gc_refs is
        # not a field of the object. It lives in the header the collector keeps in front of
        # every tracked object, and drawing it inside would be teaching a struct that does
        # not exist.
        # No highlight on these. They arrive in the warning tone and they are the only thing
        # that moves for the next two beats, which is enough. A box around a pair of counters
        # standing on their own is a border round mostly empty space.
        self.copies = VGroup(self.gc_refs(-OBJECT_X, 1), self.gc_refs(OBJECT_X, 1))
        self.hold(FadeOut(on_the_count), FadeIn(self.copies))

        zeroed = VGroup(self.gc_refs(-OBJECT_X, 0), self.gc_refs(OBJECT_X, 0))
        self.hold(Transform(self.copies, zeroed))

        freed = ArenaMap(POOL_AFTER, columns=16, label_text=POOL_LABEL)
        freed.move_to([0, POOL_Y, 0])
        self.hold(
            FadeOut(self.left, self.right, self.cycle, self.copies),
            Transform(self.pool, freed),
        )

    def gc_refs(self, x: float, value: int) -> VGroup:
        """The collector's scratch copy of one object's count, sitting under that object."""
        made = counter(value, name="gc_refs", tone="warning")
        made.scale(0.85).move_to([x, GC_Y, 0])
        return made

    def hold(self, *animations: object) -> None:
        """Play one beat's worth of change, then stop moving while the reader reads it."""
        seconds = self.beat()
        self.play(*animations, run_time=min(seconds * 0.4, 1.0))
        self.wait(max(seconds - 1.0, 0.5))
