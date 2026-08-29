"""The visual grammar for the animations, so that a hundred of them look like one project.

Importing this package does not import manim. That is deliberate. The grammar, the
storyboards and the checks are plain data and plain functions, they are what CI looks at on
every job, and none of it needs a renderer, cairo or ffmpeg. The drawing lives one import
further in::

    from xraymanim.primitives import box, arrow
    from xraymanim.mobjects import PyObjectBox
    from xraymanim.scene import Explainer

which is what a scene file in `anim/` pulls in, and what the animations job installs the
extra dependencies for.
"""

from __future__ import annotations

from .catalogue import ANIMATIONS, find
from .grammar import CAP_SECONDS, MOBJECTS, PRIMITIVES, SHAPES, Pen, cycle, pen
from .storyboard import Beat, Storyboard

__all__ = [
    "ANIMATIONS",
    "CAP_SECONDS",
    "MOBJECTS",
    "PRIMITIVES",
    "SHAPES",
    "Beat",
    "Pen",
    "Storyboard",
    "cycle",
    "find",
    "pen",
]
