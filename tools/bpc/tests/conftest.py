from __future__ import annotations

import pytest

from bpc.model import grammar
from refcheck.tree import PINNED_TAG, TreeNotFound, find_tree


@pytest.fixture(scope="session")
def tree():
    """The pinned CPython checkout, or a skip if this machine does not have one.

    Same bargain as refcheck's: somebody changing the renderer should not need 200 MB of
    CPython on disk to run the tests that cover it, and CI always has the tree, so
    everything here runs somewhere.
    """
    try:
        return find_tree()
    except TreeNotFound as error:
        pytest.skip(str(error))


@pytest.fixture(scope="session")
def asdl(tree):
    """The parsed grammar, read once for the whole session."""
    return grammar(tree)


@pytest.fixture(scope="session")
def pinned_interpreter():
    """A skip unless the interpreter running the tests is the pinned version.

    The conformance tests compare the pinned grammar against the `ast` module of whatever
    is running them. On a different version a difference is a fact about the two versions
    rather than a failure of the document, so there is nothing to report and nothing to fix.
    """
    import sys

    running = ".".join(str(part) for part in sys.version_info[:2])
    wanted = PINNED_TAG.removeprefix("v").split("rc")[0].rsplit(".", 1)[0]
    if running != wanted:
        pytest.skip(f"running {running}, the pin is {wanted}")
