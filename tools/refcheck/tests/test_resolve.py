"""Resolution against a real checkout of CPython v3.15.0rc1.

These tests are not mocked on purpose. The whole value of refcheck is that it agrees
with the actual tree, and a test suite that agrees with a fixture instead proves nothing
about the thing the tool exists to do.
"""

from __future__ import annotations

from refcheck.citation import Citation
from refcheck.resolve import (
    MAX_CITED_LINES,
    Finding,
    Resolved,
    Status,
    digest_region,
    resolve,
)
from refcheck.tree import PINNED_COMMIT, read_lines, tree_commit


def test_the_checkout_is_the_pinned_commit(tree):
    commit = tree_commit(tree)
    if commit is None:
        return  # an export rather than a checkout, which is legal
    assert commit == PINNED_COMMIT


def test_resolves_the_object_header(tree):
    cite = Citation.parse("Include/object.h:127-149@v3.15.0rc1#ob_refcnt")
    result = resolve(cite, tree)
    assert isinstance(result, Resolved)
    assert result.lines[0].strip() == "struct _object {"
    assert result.lines[-1].strip() == "};"
    assert "PyTypeObject *ob_type" in result.text


def test_resolves_a_single_line_with_a_symbol(tree):
    cite = Citation.parse("Objects/listobject.c:1232@v3.15.0rc1#list_append_impl")
    result = resolve(cite, tree)
    assert isinstance(result, Resolved)
    assert result.first_line.startswith("list_append_impl(")


def test_the_small_int_cache_bound_is_where_we_say_it_is(tree):
    """The claim that 3.15 caches -5 through 1024 has to point at the definition."""
    cite = Citation.parse(
        "Include/internal/pycore_runtime_structs.h:97@v3.15.0rc1#_PY_NSMALLPOSINTS"
    )
    result = resolve(cite, tree)
    assert isinstance(result, Resolved)
    assert result.first_line == "#define _PY_NSMALLPOSINTS           1025"


def test_wrong_tag_is_rejected(tree):
    result = resolve(Citation.parse("Include/object.h:127@v3.14.7"), tree)
    assert isinstance(result, Finding)
    assert result.status is Status.WRONG_TAG


def test_missing_file_is_reported_by_name(tree):
    result = resolve(Citation.parse("Objects/nosuchfile.c:1@v3.15.0rc1"), tree)
    assert isinstance(result, Finding)
    assert result.status is Status.MISSING_FILE
    assert "Objects/nosuchfile.c" in result.detail


def test_a_line_past_the_end_of_the_file_is_reported_with_the_real_length(tree):
    length = len(read_lines(tree, "Include/object.h"))
    result = resolve(Citation.parse(f"Include/object.h:{length + 50}@v3.15.0rc1"), tree)
    assert isinstance(result, Finding)
    assert result.status is Status.OUT_OF_RANGE
    assert str(length) in result.detail


def test_a_wrong_symbol_says_where_the_symbol_really_is(tree):
    """The error a drifting citation produces has to be actionable, not just red."""
    result = resolve(Citation.parse("Include/object.h:127-149@v3.15.0rc1#list_append_impl"), tree)
    assert isinstance(result, Finding)
    assert result.status is Status.SYMBOL_NOT_FOUND
    assert "not in the file" in result.detail


def test_a_symbol_that_moved_within_the_file_reports_its_new_line(tree):
    # ob_type is in the header but not on the first line of the struct.
    result = resolve(Citation.parse("Include/object.h:127@v3.15.0rc1#ob_type"), tree)
    assert isinstance(result, Finding)
    assert result.status is Status.SYMBOL_NOT_FOUND
    assert "it appears at line" in result.detail


def test_overlong_citations_are_refused(tree):
    end = 100 + MAX_CITED_LINES
    result = resolve(Citation.parse(f"Python/ceval.c:100-{end}@v3.15.0rc1"), tree)
    assert isinstance(result, Finding)
    assert result.status is Status.TOO_LONG


def test_a_citation_exactly_at_the_limit_is_allowed(tree):
    end = 100 + MAX_CITED_LINES - 1
    result = resolve(Citation.parse(f"Python/ceval.c:100-{end}@v3.15.0rc1"), tree)
    assert isinstance(result, Resolved)


def test_digest_covers_context_so_a_shift_above_is_caught(tree):
    """A function inserted above the citation moves it, and that must not be silent."""
    a = resolve(Citation.parse("Include/object.h:127-149@v3.15.0rc1"), tree)
    b = resolve(Citation.parse("Include/object.h:128-150@v3.15.0rc1"), tree)
    assert isinstance(a, Resolved) and isinstance(b, Resolved)
    assert a.digest != b.digest


def test_digest_ignores_trailing_whitespace_only():
    assert digest_region(("int x;",)) == digest_region(("int x;   ",))
    assert digest_region(("int x;",)) != digest_region(("  int x;",))


def test_digest_is_order_sensitive():
    assert digest_region(("a", "b")) != digest_region(("b", "a"))


def test_digest_is_stable_across_calls(tree):
    first = resolve(Citation.parse("Include/object.h:127-149@v3.15.0rc1"), tree)
    second = resolve(Citation.parse("Include/object.h:127-149@v3.15.0rc1"), tree)
    assert isinstance(first, Resolved) and isinstance(second, Resolved)
    assert first.digest == second.digest
