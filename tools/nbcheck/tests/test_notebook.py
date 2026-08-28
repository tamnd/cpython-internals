from __future__ import annotations

import json

import pytest
from notebook_fixtures import code, document, markdown, write

from nbcheck import NotebookError, find, load


def test_a_source_stored_as_a_list_of_lines_comes_back_as_one_string(root):
    path = write(root / "a.ipynb", [markdown("one\ntwo\n")])
    assert load(path).cells[0].source == "one\ntwo\n"


def test_a_source_stored_as_a_single_string_comes_back_the_same_way(root):
    """Colab writes it this way, Jupyter does not, and a file can hold a mixture."""
    raw = document([{"cell_type": "markdown", "metadata": {}, "source": "one\ntwo\n"}])
    path = root / "b.ipynb"
    path.write_text(json.dumps(raw), encoding="utf-8")
    assert load(path).cells[0].source == "one\ntwo\n"


def test_cells_are_numbered_from_one_and_count_every_kind(root):
    path = write(root / "c.ipynb", [markdown("intro"), code("x = 1"), markdown("outro")])
    book = load(path)
    assert [cell.number for cell in book.cells] == [1, 2, 3]
    assert book.cell(2).is_code
    assert [cell.number for cell in book.markdown_cells] == [1, 3]


def test_a_cell_holding_only_whitespace_counts_as_empty(root):
    path = write(root / "d.ipynb", [code("   \n\n")])
    assert load(path).cells[0].is_empty


def test_the_first_line_skips_leading_blank_lines(root):
    path = write(root / "e.ipynb", [code("\n\nimport pyxray\n")])
    assert load(path).cells[0].first_line() == "import pyxray"


def test_the_first_line_of_an_empty_cell_is_empty_rather_than_an_error(root):
    path = write(root / "f.ipynb", [code("")])
    assert load(path).cells[0].first_line() == ""


def test_the_kernel_name_survives_the_trip(root):
    path = write(root / "g.ipynb", [markdown("hi")], kernel="python3")
    assert load(path).metadata["kernelspec"]["name"] == "python3"


def test_a_file_that_is_not_json_says_so(root):
    path = root / "broken.ipynb"
    path.write_text("this is not a notebook", encoding="utf-8")
    with pytest.raises(NotebookError) as caught:
        load(path)
    assert "not valid JSON" in str(caught.value)


def test_json_that_is_not_a_notebook_says_so(root):
    path = root / "list.ipynb"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(NotebookError) as caught:
        load(path)
    assert "not a notebook" in str(caught.value)


def test_a_file_that_is_not_there_says_so(root):
    with pytest.raises(NotebookError) as caught:
        load(root / "missing.ipynb")
    assert "could not be read" in str(caught.value)


def test_find_walks_a_directory_and_sorts_what_it_finds(root):
    write(root / "lessons" / "t02" / "t02.ipynb", [markdown("b")])
    write(root / "lessons" / "t01" / "t01.ipynb", [markdown("a")])
    found = find([root / "lessons"])
    assert [path.name for path in found] == ["t01.ipynb", "t02.ipynb"]


def test_find_skips_checkpoints_and_virtual_environments(root):
    write(root / "lessons" / "t01" / "t01.ipynb", [markdown("a")])
    write(root / "lessons" / ".ipynb_checkpoints" / "t01.ipynb", [markdown("stale")])
    write(root / "lessons" / ".venv" / "share" / "example.ipynb", [markdown("theirs")])
    assert [path.name for path in find([root / "lessons"])] == ["t01.ipynb"]


def test_find_takes_a_single_file_as_well_as_a_directory(root):
    path = write(root / "one.ipynb", [markdown("a")])
    assert find([path]) == [path]


def test_the_whole_text_is_available_for_checks_that_ignore_cell_boundaries(root):
    path = write(root / "h.ipynb", [markdown("alpha"), code("beta")])
    assert "alpha" in load(path).text()
    assert "beta" in load(path).text()
