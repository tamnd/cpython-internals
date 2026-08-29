"""Keep manim's scratch files out of the working tree.

Building a `Text` makes manim render the glyphs to an SVG and cache it, and by default the
cache is a `media/` directory next to wherever you happened to run pytest from. That is a
build artifact appearing in the repository as a side effect of running the tests, which is
the sort of thing people then gitignore instead of fixing. Point it at a temporary directory
for the session instead, so a test run leaves nothing behind.

Nothing here imports manim at module level, because the rest of the suite runs without it.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session", autouse=True)
def _manim_scratch(tmp_path_factory):
    try:
        from manim import config
    except ImportError:
        yield
        return
    scratch = tmp_path_factory.mktemp("manim")
    was = config.media_dir
    config.media_dir = str(scratch)
    yield
    config.media_dir = was
