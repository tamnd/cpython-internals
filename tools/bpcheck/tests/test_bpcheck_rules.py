"""Every rule, broken once on purpose."""

from __future__ import annotations

from pathlib import Path

from blueprint_fixtures import BODIES, TITLE, clean_text, replace

from bpcheck.document import parse
from bpcheck.rules import check, check_index

PATH = Path("blueprints/BP-DEMO.md")


def rules(text: str) -> list[str]:
    return [problem.rule for problem in check(parse(PATH, text))]


def messages(text: str) -> str:
    return "\n".join(str(problem) for problem in check(parse(PATH, text)))


def test_the_fixture_passes():
    assert check(parse(PATH, clean_text())) == []


def test_a_missing_title():
    """The header block is still read, so the author gets one problem rather than two."""
    assert rules(clean_text().replace(TITLE + "\n", "", 1)) == ["title"]


def test_a_title_that_disagrees_with_the_file_name():
    text = replace(clean_text(), "# BP-DEMO:", "# BP-OTHER:")
    assert rules(text) == ["title"]
    assert "BP-OTHER" in messages(text)


def test_a_missing_header_field():
    text = replace(clean_text(), "**Status:** complete\n", "")
    assert rules(text) == ["header"]


def test_header_fields_out_of_order():
    text = replace(
        clean_text(),
        "**Status:** complete\n**Compatibility tier:** B",
        "**Compatibility tier:** B\n**Status:** complete",
    )
    assert rules(text) == ["header"]


def test_an_invented_status():
    text = replace(clean_text(), "**Status:** complete", "**Status:** nearly")
    assert rules(text) == ["status"]
    assert "'nearly'" in messages(text)


def test_an_invented_tier():
    text = replace(clean_text(), "**Compatibility tier:** B", "**Compatibility tier:** E")
    assert rules(text) == ["tier"]


def test_a_missing_section():
    text = replace(clean_text(), "## 7. Interactions", "## 7. Interaction")
    assert rules(text) == ["sections"]
    assert "missing 7. Interactions" in messages(text)
    assert "unexpected 7. Interaction" in messages(text)


def test_sections_in_the_wrong_order():
    """Sections 6 and 7 swap places, headings and all, so nothing is missing or extra."""
    blocks = clean_text().split("\n## ")
    blocks[6], blocks[7] = blocks[7], blocks[6]
    text = "\n## ".join(blocks)
    assert rules(text) == ["sections"]
    assert "out of order" in messages(text)


def test_a_section_with_no_body():
    text = replace(text=clean_text(), old=BODIES["Interactions"] + "\n", new="")
    assert rules(text) == ["empty-section"]


def test_invariants_numbered_with_a_gap():
    text = replace(clean_text(), "**INV-DEMO-002.**", "**INV-DEMO-003.**")
    assert "invariant-numbering" in rules(text)


def test_invariants_belonging_to_another_blueprint():
    text = replace(clean_text(), "**INV-DEMO-002.**", "**INV-OTHER-002.**")
    assert rules(text) == ["invariant-slug"]
    assert "whose invariants are INV-DEMO-NNN" in messages(text)


def test_a_section_with_no_invariants_at_all():
    text = replace(
        clean_text(),
        "**INV-DEMO-001.** The demo holds.\n\n**INV-DEMO-002.** It keeps holding.",
        "There are no invariants worth stating.",
    )
    assert rules(text) == ["no-invariants"]


def test_referring_to_an_invariant_that_is_not_stated():
    text = replace(
        clean_text(),
        BODIES["Interactions"],
        "Everything depends on INV-DEMO-009 holding.",
    )
    assert rules(text) == ["unknown-invariant"]


def test_referring_to_another_blueprints_invariant_is_fine():
    text = replace(
        clean_text(),
        BODIES["Interactions"],
        "This rests on INV-OTHER-004 from the blueprint next door.",
    )
    assert rules(text) == []


def test_an_em_dash():
    text = replace(clean_text(), "Porting the demo", "Porting \u2014 the demo")
    assert rules(text) == ["punctuation"]
    assert "em dash" in messages(text)


def test_an_en_dash():
    text = replace(clean_text(), "Porting the demo", "Porting \u2013 the demo")
    assert "en dash" in messages(text)


def test_a_horizontal_rule():
    text = replace(clean_text(), "## 9. Port notes", "---\n\n## 9. Port notes")
    assert rules(text) == ["page-break"]


def test_a_table_separator_is_not_a_horizontal_rule():
    text = replace(
        clean_text(),
        BODIES["Interactions"],
        "| Thing | Other |\n|---|---|\n| a | b |",
    )
    assert rules(text) == []


def test_a_citation_with_no_tag():
    text = replace(
        clean_text(),
        "**Covers:** `Python/demo.c`",
        "**Covers:** `Python/demo.c:10-20`",
    )
    assert rules(text) == ["untagged-citation"]
    assert "Python/demo.c:10-20" in messages(text)


def test_a_citation_with_a_tag_is_fine():
    text = replace(
        clean_text(),
        "**Covers:** `Python/demo.c`",
        "**Covers:** `Python/demo.c:10-20@v3.15.0rc1#demo`",
    )
    assert rules(text) == []


def test_a_file_named_without_a_line_number_is_not_a_citation():
    text = replace(clean_text(), "`Python/demo.c`", "`Python/demo.c` and `Include/demo.h`")
    assert rules(text) == []


def test_sending_the_reader_to_a_lesson():
    text = replace(
        clean_text(),
        BODIES["Interactions"],
        "The reason for this is explained in T05, which covers it well.",
    )
    assert rules(text) == ["deferral"]


def test_section_eight_may_name_a_lesson():
    """The fixture's conformance section says "see the lesson" and has to stay legal."""
    assert "see the lesson" in clean_text()
    assert rules(clean_text()) == []


def test_the_index_has_to_list_every_blueprint():
    document = parse(PATH, clean_text())
    index = Path("blueprints/README.md")
    assert check_index(index, "# Blueprints\n", [document]) != []
    assert check_index(index, "[BP-DEMO](BP-DEMO.md)\n", [document]) == []
