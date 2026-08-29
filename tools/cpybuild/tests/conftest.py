from __future__ import annotations

import pytest

from refcheck.tree import TreeNotFound, find_tree


@pytest.fixture(scope="session")
def tree():
    """The pinned CPython checkout, or a skip if this machine does not have one.

    The same bargain the other tools make: somebody changing a build configuration should not
    need 200 MB of CPython on disk to run the tests that cover it. Only one test in here wants
    the tree, and the job that vendors a checkout runs it.
    """
    try:
        return find_tree()
    except TreeNotFound as error:
        pytest.skip(str(error))
