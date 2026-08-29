"""The blueprint compiler.

The mechanical half of a specification is a transcription job, and transcription rots. A
list of every AST node and every field, typed by hand, is correct on the day it is written
and wrong the first time upstream adds a field. Nobody notices, because a reader who
trusted the list has no reason to go and check it.

So the mechanical sections are generated from the same files CPython generates its own
front end from, and the generated output is committed next to the hand written prose. A
build that generates and a check that compares are two halves of the same rule: what is in
the repository is what the pinned tree says, or the build fails.
"""

from .model import Constructor, Definition, Field, Grammar
from .template import Source, expand

__all__ = ["Constructor", "Definition", "Field", "Grammar", "Source", "expand"]
