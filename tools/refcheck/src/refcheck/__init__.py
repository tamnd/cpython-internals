"""Citation integrity for cpython-internals.

Every claim this project makes about CPython points at a specific region of a specific
tagged tree. refcheck is what stops those pointers from going stale without anyone
noticing, which is the failure mode that has made every other CPython explainer wrong.
"""

from .citation import Citation, CitationError, find_all
from .lock import Lock
from .resolve import Finding, Resolved, Status, resolve
from .scan import Occurrence, scan
from .tree import PINNED_COMMIT, PINNED_TAG, TreeNotFound, find_tree

__all__ = [
    "PINNED_COMMIT",
    "PINNED_TAG",
    "Citation",
    "CitationError",
    "Finding",
    "Lock",
    "Occurrence",
    "Resolved",
    "Status",
    "TreeNotFound",
    "find_all",
    "find_tree",
    "resolve",
    "scan",
]
__version__ = "0.1.0"
