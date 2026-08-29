"""Swapping directives for blocks, and the four ways a source document can be wrong.

The errors matter more than the happy path here. A template engine that quietly does
nothing when it does not recognise a directive produces a document with a heading and no
body, which reads like a subsystem with nothing to say rather than like a mistake.
"""

from __future__ import annotations

import pytest

from bpc.model import Grammar
from bpc.template import BEGIN, END, Source, TemplateError, expand, find


@pytest.fixture
def empty():
    """A grammar with nothing in it, so the blocks come out short and readable."""
    return Grammar(name="Toy", definitions=(), line=1)


def source(tmp_path, text, name="BP-TOY.md"):
    root = tmp_path / "blueprints" / "sources"
    root.mkdir(parents=True)
    path = root / name
    path.write_text(text, encoding="utf-8")
    return Source(path)


def test_a_source_knows_its_name_and_where_its_output_goes(tmp_path):
    one = source(tmp_path, "<!-- bpc: overview -->\n")
    assert one.name == "BP-TOY"
    assert one.output == tmp_path / "blueprints" / "BP-TOY.md"


def test_the_blocks_are_listed_in_the_order_the_document_asks_for_them(tmp_path):
    one = source(tmp_path, "a\n<!-- bpc: nodes -->\nb\n<!-- bpc: overview -->\n")
    assert one.blocks() == ["nodes", "overview"]


def test_a_directive_has_to_be_alone_on_its_line(tmp_path):
    one = source(tmp_path, "text <!-- bpc: nodes --> more\n<!-- bpc: overview -->\n")
    assert one.blocks() == ["overview"]


def test_the_prose_around_a_directive_is_kept_exactly(tmp_path, empty):
    one = source(tmp_path, "# Title\n\nbefore\n\n<!-- bpc: overview -->\n\nafter\n")
    out = expand(one, empty).splitlines()
    assert out[:4] == ["# Title", "", "before", ""]
    assert out[-2:] == ["", "after"]


def test_the_output_marks_where_the_generated_part_starts_and_stops(tmp_path, empty):
    out = expand(source(tmp_path, "<!-- bpc: overview -->\n"), empty)
    assert out.startswith(BEGIN.format(name="overview") + "\n")
    assert out.rstrip().endswith(END.format(name="overview"))


def test_the_directive_itself_does_not_survive_into_the_output(tmp_path, empty):
    out = expand(source(tmp_path, "<!-- bpc: overview -->\n"), empty)
    assert "<!-- bpc: overview -->" not in out


def test_the_output_ends_with_exactly_one_newline(tmp_path, empty):
    out = expand(source(tmp_path, "<!-- bpc: overview -->\n\n\n\n"), empty)
    assert out.endswith("\n")
    assert not out.endswith("\n\n")


def test_an_unknown_block_names_the_line_and_lists_the_real_ones(tmp_path, empty):
    one = source(tmp_path, "a\n<!-- bpc: invariants -->\n")
    with pytest.raises(TemplateError) as caught:
        expand(one, empty)
    assert ":2:" in str(caught.value)
    assert "'invariants'" in str(caught.value)
    assert "conformance, nodes, observable, overview" in str(caught.value)


def test_the_same_block_twice_is_an_error_rather_than_two_copies(tmp_path, empty):
    one = source(tmp_path, "<!-- bpc: overview -->\n<!-- bpc: overview -->\n")
    with pytest.raises(TemplateError, match="asked for twice"):
        expand(one, empty)


def test_a_document_with_no_directives_is_not_a_source_document(tmp_path, empty):
    with pytest.raises(TemplateError, match="does not need to be a source document"):
        expand(source(tmp_path, "# Title\n\nAll hand written.\n"), empty)


def test_a_block_that_comes_out_empty_stops_the_build(tmp_path, empty):
    """The renderer following a grammar it no longer understands, caught here."""
    from bpc import template

    original = dict(template.BLOCKS)
    template.BLOCKS["nodes"] = lambda grammar: "   \n"
    try:
        with pytest.raises(TemplateError, match="came out empty"):
            expand(source(tmp_path, "<!-- bpc: nodes -->\n"), empty)
    finally:
        template.BLOCKS.clear()
        template.BLOCKS.update(original)


def test_finding_sources_ignores_anything_not_named_like_a_blueprint(tmp_path):
    root = tmp_path / "sources"
    root.mkdir()
    for name in ("BP-AST.md", "BP-PARSER.md", "README.md", "notes.md"):
        (root / name).write_text("<!-- bpc: overview -->\n", encoding="utf-8")
    assert [one.name for one in find(root)] == ["BP-AST", "BP-PARSER"]


def test_finding_sources_in_a_directory_that_is_not_there_finds_nothing(tmp_path):
    assert find(tmp_path / "nowhere") == []


def test_the_real_source_document_expands_to_what_is_committed(asdl):
    """The check that `just blueprints` runs, stated once here so it is covered by tests."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    one = Source(root / "blueprints" / "sources" / "BP-AST.md")
    assert one.output.read_text(encoding="utf-8") == expand(one, asdl)
