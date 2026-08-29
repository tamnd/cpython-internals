"""The base scene every animation is built on.

It does the three things that would otherwise be copied into every scene file and would
therefore end up slightly different in each of them: it puts the project's page colour
behind the picture, it runs the caption track from the storyboard, and it checks at the end
that the scene actually played the beats it said it would.

That last check is the reason the storyboards are worth having. A plan that the thing being
planned is free to ignore is a comment. This one fails the render.
"""

from __future__ import annotations

import math

from manim import DOWN, UP, FadeIn, FadeOut, Scene, VGroup, config

from .grammar import CAPTION_SIZE, FADE, INK, MUTED, PAPER, TITLE_SIZE, UNIT
from .primitives import label
from .storyboard import Storyboard


class Explainer(Scene):
    """One animation, with its storyboard attached.

    A subclass sets `storyboard` and writes `construct`, calling `self.beat()` once per beat
    in order. `beat` returns how many seconds that step is allowed, so the scene divides its
    own time rather than every scene inventing its own run times.
    """

    storyboard: Storyboard

    def setup(self) -> None:
        self.camera.background_color = PAPER
        self.played = 0
        self.heading = label(self.storyboard.title, size=TITLE_SIZE, colour=INK)
        self.heading.to_edge(UP, buff=UNIT * 2)
        self.subtitle = label(
            f"lesson {self.storyboard.lesson}", size=CAPTION_SIZE, colour=MUTED
        ).next_to(self.heading, DOWN, buff=UNIT / 2)
        self.caption = VGroup()
        self.add(self.heading, self.subtitle, self.caption)

    def beat(self, index: int | None = None) -> float:
        """Show the next caption, and hand back the seconds that beat is allowed.

        Beats are normally taken in order and the index is left out. Passing one is for the
        rare scene that has to jump, and it still counts as one beat played, so the tally at
        the end catches a scene that skipped one.
        """
        wanted = self.played if index is None else index
        text = self.storyboard.beats[wanted].caption
        self.played += 1

        replacement = label(text, size=CAPTION_SIZE, colour=MUTED)
        replacement.to_edge(DOWN, buff=UNIT * 2)
        if self.caption.submobjects:
            # Cross fading rather than transforming. Manim will happily morph one sentence
            # into another letter by letter, and the result is unreadable for as long as it
            # runs, which is exactly when the reader is trying to read it.
            going = self.caption.submobjects[0]
            self.caption.remove(going)
            self.caption.add(replacement)
            self.play(FadeOut(going), FadeIn(replacement), run_time=FADE)
        else:
            self.caption.add(replacement)
            self.play(FadeIn(replacement), run_time=FADE)
        return max(self.storyboard.beats[wanted].seconds - FADE, FADE)

    def tear_down(self) -> None:
        if self.rendering_a_slice():
            return
        expected = len(self.storyboard.beats)
        if self.played != expected:
            raise AssertionError(
                f"{self.storyboard.slug} played {self.played} beat(s) but its storyboard "
                f"has {expected}; the plan and the picture have come apart"
            )

    @staticmethod
    def rendering_a_slice() -> bool:
        """Whether manim was asked for part of the scene rather than all of it.

        `manim render -n 4,4` stops `construct` early on purpose, to look at one moment of
        the animation, so the beat tally would be wrong every time and would fail every
        probe render. Note what "all of it" looks like: the default upper bound is infinity
        and not -1, which is worth spelling out because reading it as a sentinel is how the
        tally ends up switched off in every render including the real ones.
        """
        return config.from_animation_number > 0 or config.upto_animation_number != math.inf
