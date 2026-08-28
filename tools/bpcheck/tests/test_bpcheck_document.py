"""Reading a blueprint into pieces, including the wrong ones."""

from __future__ import annotations

from pathlib import Path

import pytest
from blueprint_fixtures import clean_text, replace, write

from bpcheck.document import DocumentError, find, load, parse


def parsed(text: str = ""):
    return parse(Path("blueprints/BP-DEMO.md"), text or clean_text())


def test_title_and_subtitle_are_separated():
    document = parsed()
    assert document.title == "BP-DEMO"
    assert document.subtitle == "a subsystem that exists only in the tests"
    assert document.title_line == 1


def test_slug_comes_from_the_file_name_not_the_title():
    document = parse(Path("blueprints/BP-OTHER.md"), clean_text())
    assert document.stem == "BP-OTHER"
    assert document.slug == "OTHER"


def test_a_file_not_named_like_a_blueprint_has_no_slug():
    assert parse(Path("blueprints/NOTATION.md"), clean_text()).slug is None


def test_the_header_block_keeps_its_order():
    document = parsed()
    assert [field.name for field in document.fields] == [
        "Covers",
        "Lesson",
        "Status",
        "Compatibility tier",
    ]
    assert document.field("Status").value == "complete"
    assert document.field("Status").line == 5
    assert document.field("nothing") is None


def test_a_bold_line_inside_a_section_is_not_a_header_field():
    """The header block stops at the first line that is not a field, and stays stopped."""
    document = parsed()
    assert document.field("INV-DEMO-001") is None
    assert len(document.fields) == 4


def test_nine_sections_with_their_bodies():
    document = parsed()
    assert len(document.sections) == 9
    assert document.section(1).title == "Purpose and scope"
    assert document.section(4).title == "Invariants"
    assert "INV-DEMO-001" in "\n".join(document.section(4).body)
    assert document.section(99) is None


def test_the_last_section_runs_to_the_end_of_the_file():
    document = parsed(clean_text() + "\nA trailing paragraph.\n")
    assert "A trailing paragraph." in "\n".join(document.section(9).body)


def test_a_document_with_nothing_in_it_still_parses():
    document = parse(Path("blueprints/BP-EMPTY.md"), "")
    assert document.title is None
    assert document.title_line is None
    assert document.fields == []
    assert document.sections == []


def test_a_wrong_title_parses_with_no_title():
    document = parsed(replace(clean_text(), "# BP-DEMO:", "# Demo:"))
    assert document.title is None
    assert document.title_line == 1


def test_load_reports_a_missing_file_rather_than_raising_oserror(tmp_path: Path):
    with pytest.raises(DocumentError):
        load(tmp_path / "nope.md")


def test_find_skips_the_prose_files(tmp_path: Path):
    root = tmp_path / "blueprints"
    write(root / "BP-DEMO.md", clean_text())
    write(root / "BP-OTHER.md", clean_text())
    (root / "NOTATION.md").write_text("# Notation\n", encoding="utf-8")
    assert find([root]) == [root / "BP-DEMO.md", root / "BP-OTHER.md"]


def test_find_takes_a_file_as_well_as_a_directory(tmp_path: Path):
    path = write(tmp_path / "blueprints" / "BP-DEMO.md", clean_text())
    assert find([path]) == [path]
