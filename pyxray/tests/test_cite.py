from __future__ import annotations

import pytest

from pyxray import cite
from refcheck.citation import CitationError

CITATION = "Objects/listobject.c:1232-1249@v3.15.0rc1#list_append_impl"


def test_the_url_points_at_the_pinned_tag_and_the_right_lines():
    assert cite.url(CITATION) == (
        "https://github.com/python/cpython/blob/v3.15.0rc1/Objects/listobject.c#L1232-L1249"
    )


def test_a_single_line_citation_gets_a_single_line_anchor():
    assert cite.url("Python/ceval.c:1213@v3.15.0rc1#_PyEval_EvalFrameDefault").endswith("#L1213")


def test_markdown_uses_the_citation_as_the_label_by_default():
    text = cite.markdown(CITATION)
    assert text.startswith("[Objects/listobject.c:1232-1249](")
    assert cite.url(CITATION) in text


def test_markdown_takes_a_label_when_the_prose_needs_one():
    assert cite.markdown(CITATION, "list.append").startswith("[list.append](")


def test_a_link_renders_as_html_in_a_notebook():
    html = cite.link(CITATION)._repr_html_()
    assert cite.url(CITATION) in html
    assert "list_append_impl" in html
    assert 'target="_blank"' in html


def test_a_link_renders_as_markdown_too():
    assert cite.link(CITATION)._repr_markdown_() == cite.markdown(CITATION)


def test_a_link_is_readable_in_a_plain_terminal():
    """Not every reader is in a notebook, and repr is what the REPL shows them."""
    text = repr(cite.link(CITATION, "list.append"))
    assert text.startswith("list.append")
    assert cite.url(CITATION) in text


def test_a_malformed_citation_is_rejected_rather_than_linked_to_nowhere():
    with pytest.raises(CitationError):
        cite.url("Objects/listobject.c:1232")


def test_the_notebook_and_the_checker_use_the_same_parser():
    """Two implementations of the format would mean only one of them was ever checked."""
    assert cite.Citation is not None
    assert cite.Citation.parse(CITATION).symbol == "list_append_impl"
