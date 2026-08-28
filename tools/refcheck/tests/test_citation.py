"""Parsing and linking, which is pure string handling and needs no tree."""

from __future__ import annotations

import pytest

from refcheck.citation import Citation, CitationError, find_all


def test_single_line():
    cite = Citation.parse("Objects/listobject.c:1232@v3.15.0rc1")
    assert cite.path == "Objects/listobject.c"
    assert cite.start == cite.end == 1232
    assert cite.tag == "v3.15.0rc1"
    assert cite.symbol is None
    assert cite.line_count == 1


def test_range_with_symbol():
    cite = Citation.parse("Include/object.h:127-149@v3.15.0rc1#ob_refcnt")
    assert (cite.start, cite.end) == (127, 149)
    assert cite.symbol == "ob_refcnt"
    assert cite.line_count == 23


@pytest.mark.parametrize(
    "tag",
    ["v3.15.0", "v3.15.0rc1", "v3.14.7", "v3.15.0a4", "v3.15.0b3"],
)
def test_accepts_every_tag_shape_cpython_uses(tag):
    assert Citation.parse(f"Python/ceval.c:10@{tag}").tag == tag


@pytest.mark.parametrize(
    "text",
    [
        "Objects/listobject.c@v3.15.0rc1",  # no line
        "Objects/listobject.c:0@v3.15.0rc1",  # lines are one based
        "Objects/listobject.c:20-10@v3.15.0rc1",  # backwards range
        "/Objects/listobject.c:1@v3.15.0rc1",  # absolute path
        "../listobject.c:1@v3.15.0rc1",  # escapes the tree
        "Objects/listobject.c:1@3.15.0rc1",  # tag missing its v
        "Objects/listobject.c:1@v3.15.0rc1#9lives",  # symbol is not an identifier
    ],
)
def test_rejects_malformed(text):
    with pytest.raises(CitationError):
        Citation.parse(text)


def test_github_url_single_line():
    cite = Citation.parse("Objects/listobject.c:1232@v3.15.0rc1")
    assert cite.github_url() == (
        "https://github.com/python/cpython/blob/v3.15.0rc1/Objects/listobject.c#L1232"
    )


def test_github_url_range_highlights_the_whole_region():
    cite = Citation.parse("Include/object.h:127-149@v3.15.0rc1")
    assert cite.github_url().endswith("/Include/object.h#L127-L149")


def test_symbol_does_not_leak_into_the_url():
    cite = Citation.parse("Objects/listobject.c:1232@v3.15.0rc1#list_append_impl")
    assert "#L1232" in cite.github_url()
    assert "list_append_impl" not in cite.github_url()


def test_key_ignores_the_symbol():
    with_symbol = Citation.parse("Objects/listobject.c:1232@v3.15.0rc1#list_append_impl")
    without = Citation.parse("Objects/listobject.c:1232@v3.15.0rc1")
    assert with_symbol.key == without.key


def test_short_form_is_what_prose_shows():
    assert Citation.parse("Python/ceval.c:10@v3.15.0rc1").short() == "Python/ceval.c:10"
    assert Citation.parse("Python/ceval.c:10-12@v3.15.0rc1").short() == "Python/ceval.c:10-12"


def test_markdown_link_uses_the_short_form_as_the_label():
    cite = Citation.parse("Python/ceval.c:10@v3.15.0rc1")
    assert cite.markdown_link() == f"[Python/ceval.c:10]({cite.github_url()})"
    assert cite.markdown_link("the eval loop").startswith("[the eval loop](")


def test_find_all_in_prose():
    text = (
        "The header is `Include/object.h:127-149@v3.15.0rc1#ob_refcnt` and the append "
        "path is `Objects/listobject.c:1232@v3.15.0rc1`."
    )
    found = find_all(text)
    assert [c.path for c in found] == ["Include/object.h", "Objects/listobject.c"]


def test_find_all_ignores_things_that_only_look_like_citations():
    text = "See file.c:12 for details, and version v3.15.0rc1 of the docs, and a@b.com."
    assert find_all(text) == []


def test_find_all_survives_a_malformed_citation_on_the_same_line():
    text = "bad Objects/x.c:0@v3.15.0rc1 good Objects/y.c:5@v3.15.0rc1"
    found = find_all(text)
    assert len(found) == 1
    assert found[0].path == "Objects/y.c"


def test_citations_sort_by_path_then_line():
    unordered = [
        Citation.parse("Python/ceval.c:50@v3.15.0rc1"),
        Citation.parse("Objects/object.c:10@v3.15.0rc1"),
        Citation.parse("Python/ceval.c:10@v3.15.0rc1"),
    ]
    assert [c.short() for c in sorted(unordered)] == [
        "Objects/object.c:10",
        "Python/ceval.c:10",
        "Python/ceval.c:50",
    ]
