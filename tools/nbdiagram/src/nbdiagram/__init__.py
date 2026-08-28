"""The diagrams the lessons are made of.

Every structural picture in this project is an Excalidraw scene generated from Python,
committed twice: once as `.excalidraw`, which anybody can open at excalidraw.com and edit,
and once as `.svg`, which is what GitHub and Colab can actually display.

The colours, type and spacing come from `pyxray.theme`, which the matplotlib charts and the
manim animations import as well, so all three end up looking like one project rather than
three.
"""

from __future__ import annotations

from . import figures
from .gallery import Gallery
from .link import RAW, Diagrams
from .render import to_svg
from .scene import Element, Scene, text_width

__all__ = ["RAW", "Diagrams", "Element", "Gallery", "Scene", "figures", "text_width", "to_svg"]
__version__ = "0.1.0"
