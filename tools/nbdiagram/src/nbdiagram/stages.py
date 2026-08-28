"""The map every lesson opens with.

There is one picture a reader sees more than any other: the row of boxes showing where the
lesson they are about to read sits between the file they wrote and the answer they got. It
has to be the same row of boxes every time. A map that quietly gains a box in lesson forty
is worse than no map, because by then the reader has stopped looking at it and will not
notice it changed.

So the stages live here rather than in any one lesson, and a lesson asks for the picture
with the box it is about lit up::

    from nbdiagram import stages

    gallery.add(stages.map("where-we-are", highlight=stages.TOKENS))

The names are deliberately the artefact rather than the verb: "tokens", not "tokenizing".
Each box is a thing you can print, and most of the lessons are built around printing the
thing in one box and seeing how it became the thing in the next.
"""

from __future__ import annotations

from . import figures
from .scene import Scene

#: Index constants, so a lesson says `highlight=stages.SYMBOLS` instead of `highlight=3`.
#: Off by one errors in a highlight are invisible in review and obvious to a reader.
SOURCE = 0
TOKENS = 1
TREE = 2
SYMBOLS = 3
INSTRUCTIONS = 4
OPTIMIZED = 5
CODE_OBJECT = 6
ANSWER = 7

#: The label and the CPython file that produces it. The second line is the reason this map
#: is worth showing at all: it turns "the compiler does something" into a filename you can
#: open. Paths are checked against the pinned tree by the citation step.
STAGES: list[tuple[str, str]] = [
    ("your file", "the text you wrote"),
    ("tokens", "Parser/lexer/lexer.c"),
    ("syntax tree", "Parser/parser.c"),
    ("symbol table", "Python/symtable.c"),
    ("instructions", "Python/codegen.c"),
    ("optimized", "Python/flowgraph.c"),
    ("code object", "Objects/codeobject.c"),
    ("the answer", "Python/ceval.c"),
]

#: Seven arrows between eight boxes, which is where the "seven stages" in T01 comes from.
COUNT = len(STAGES) - 1


def map(name: str, *, highlight: int | None = None, title: str = "", caption: str = "") -> Scene:
    """The stage map, optionally with one box lit up.

    `highlight` takes one of the index constants above. Passing nothing draws the map with
    no box emphasised, which is what T01 wants, since T01 is about all of them.
    """
    if highlight is not None and not 0 <= highlight < len(STAGES):
        raise IndexError(f"there is no stage {highlight}; the map has {len(STAGES)} boxes")
    return figures.pipeline(name, STAGES, highlight=highlight, title=title, caption=caption)
