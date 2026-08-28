"""pyxray, the instrumentation every lesson imports.

The point of this package is that a lesson about the small integer cache should contain
one line about the small integer cache, not thirty lines of introspection scaffolding
that the reader has to skip past to find the idea.

Everything here works on a stock interpreter with no build, no compiler and no `ctypes`,
because the reader on a locked down laptop in a browser tab is the reader this project
exists for. Where a capability is genuinely missing, the code says so in a sentence that
tells the reader what still works, rather than raising something they cannot read.
"""

from __future__ import annotations

from . import bytecode, compiler, obj
from .build import Build, banner, capabilities, current
from .cite import link

__all__ = [
    "Build",
    "banner",
    "bytecode",
    "capabilities",
    "compiler",
    "current",
    "link",
    "obj",
    "show",
]
__version__ = "0.1.0"


def show() -> None:
    """Print the build banner. This is the first cell of every lesson."""
    print(banner())
