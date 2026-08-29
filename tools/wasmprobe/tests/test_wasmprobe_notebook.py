"""The notebook is generated and committed, so something has to check it did not drift."""

from __future__ import annotations

import ast
import itertools
import json
from pathlib import Path

import pytest
from wasmprobe import notebook
from wasmprobe.checks import CHECKS

COMMITTED = Path(__file__).resolve().parents[3] / notebook.DESTINATION


def sources(kind: str) -> list[str]:
    return [
        "".join(cell["source"]) for cell in notebook.build()["cells"] if cell["cell_type"] == kind
    ]


def test_it_is_a_notebook_jupyter_will_open():
    body = notebook.build()
    assert body["nbformat"] == 4
    assert body["metadata"]["kernelspec"]["name"] == "python3"
    assert all(cell["id"] for cell in body["cells"])


def test_cell_ids_are_unique_and_in_order():
    ids = [cell["id"] for cell in notebook.build()["cells"]]
    assert ids == sorted(ids)
    assert len(ids) == len(set(ids))


def test_every_code_cell_parses():
    for source in sources("code"):
        ast.parse(source)


def test_every_code_cell_has_a_markdown_cell_in_front_of_it():
    """The same rule the lessons follow. A reader should never meet a cell unannounced."""
    kinds = [cell["cell_type"] for cell in notebook.build()["cells"]]
    assert kinds[0] == "markdown"
    for before, after in itertools.pairwise(kinds):
        if after == "code":
            assert before in {"markdown", "code"}


def test_the_dangerous_check_is_last_and_on_its_own():
    """It kills the runtime in a browser, so everything else has to have printed first."""
    body = notebook.build()
    keys = [cell["id"] for cell in body["cells"]]
    holding = [
        index
        for index, cell in enumerate(body["cells"])
        if "optimize_cfg(sequence, [], 0)" in "".join(cell["source"])
    ]
    assert len(holding) == 1
    assert holding[0] >= len(keys) - 4


def test_the_safe_checks_are_all_in_one_cell():
    body = "\n".join(sources("code"))
    for check in CHECKS:
        if check.key == "optimize_cfg_short_consts":
            continue
        assert f'"{check.key}"' in body


def test_it_installs_nothing():
    """A reader in a locked down browser tab has no package manager, and needs none."""
    body = "\n".join(sources("code"))
    assert "pip install" not in body
    assert "micropip" not in body


def test_the_prose_follows_the_house_style():
    for source in sources("markdown"):
        assert "\u2014" not in source
        assert "\u2013" not in source


def test_the_colab_badge_points_at_the_committed_path():
    first = "".join(notebook.build()["cells"][0]["source"])
    assert "colab.research.google.com/github/tamnd/cpython-internals" in first
    assert str(notebook.DESTINATION) in first


def test_render_is_stable():
    assert notebook.render() == notebook.render()


def test_write_goes_where_it_is_told(tmp_path):
    path = notebook.write(tmp_path / "deep" / "probe.ipynb")
    assert json.loads(path.read_text(encoding="utf-8"))["nbformat"] == 4


def test_the_committed_notebook_matches_the_checks():
    if not COMMITTED.exists():
        pytest.skip("no committed notebook")
    assert COMMITTED.read_text(encoding="utf-8") == notebook.render()
