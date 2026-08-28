from __future__ import annotations

import pytest
from refcheck.tree import TreeNotFound, find_tree


@pytest.fixture(scope="session")
def tree():
    """The pinned CPython checkout, or a skip if this machine does not have one.

    Skipping rather than failing is deliberate. Someone changing the citation parser
    should not need 200 MB of CPython on disk to run the tests that cover it. CI always
    has the tree, so the tests that need it always run somewhere.
    """
    try:
        return find_tree()
    except TreeNotFound as error:
        pytest.skip(str(error))
