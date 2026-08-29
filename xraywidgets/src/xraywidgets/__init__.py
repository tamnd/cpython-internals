"""Small interactive widgets for the lessons, which also work with nothing installed.

Every widget here draws itself as plain HTML with no dependency beyond `pyxray`, so it shows
up on GitHub, in an nbconvert render, in a PDF, and while Pyodide is still starting. Call
`.live()` on one to get the version with working buttons, which needs anywidget.

    from xraywidgets import Disassembler

    Disassembler("total = sum(values)", depths=True)   # a still picture
    Disassembler("total = sum(values)").live()          # the same thing, clickable

See `base.Widget` for why the truth lives in Python and the browser only draws.
"""

from .base import Widget
from .disassembler import Disassembler

__all__ = ["Disassembler", "Widget"]
