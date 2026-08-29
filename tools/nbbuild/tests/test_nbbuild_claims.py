"""The claim ledger, and the rule that a claim needs a runnable cell behind it.

Most of these are about the rule refusing something, because a check that only ever passes is
indistinguishable from no check at all, and this one is guarding a promise the README makes on
the project's behalf.
"""

from __future__ import annotations

import pytest

from nbbuild import Lesson
from nbbuild.claims import UNOBSERVABLE_CAP, TooMany, Unproved, headings, render, resolve


def lesson(tmp_path) -> Lesson:
    """A lesson with a root that exists, so nothing here touches the real one."""
    (tmp_path / "lessons").mkdir(exist_ok=True)
    (tmp_path / "pyproject.toml").write_text("")
    return Lesson("t99-a-lesson", "t99", root=tmp_path)


def test_a_claim_returns_its_own_text_so_the_prose_reads_the_same(tmp_path):
    """The whole design rests on this. If marking a claim changed the sentence, nobody would
    mark one on the paragraph that most needed it."""
    one = lesson(tmp_path)
    said = one.claim("dictionaries keep their insertion order")
    assert said == "dictionaries keep their insertion order"


def test_the_next_code_cell_is_the_evidence(tmp_path):
    one = lesson(tmp_path)
    one.md(f"# T99\n\n{one.claim('small integers are shared')}")
    one.code("print(1 is 1)")
    assert resolve(one.claims, one.cells)[0].evidence == "t99-02"


def test_a_claim_with_no_code_cell_after_it_at_all_is_refused(tmp_path):
    one = lesson(tmp_path)
    one.md(f"# T99\n\n{one.claim('small integers are shared')}")
    one.md("and that is the end of the lesson")
    with pytest.raises(Unproved, match="small integers are shared"):
        resolve(one.claims, one.cells)


def test_evidence_on_the_far_side_of_a_heading_does_not_count(tmp_path):
    """A claim proved three sections later is a claim nobody reading the paragraph checked."""
    one = lesson(tmp_path)
    one.md(f"# T99\n\n{one.claim('small integers are shared')}")
    one.md("## Something else entirely")
    one.code("print(1 is 1)")
    with pytest.raises(Unproved):
        resolve(one.claims, one.cells)


def test_a_heading_after_the_claim_in_its_own_cell_counts_too(tmp_path):
    """Cells here routinely end with the heading that opens the next section, so without this
    a claim could sit one paragraph above a heading and borrow the next section's cell."""
    one = lesson(tmp_path)
    one.md(f"# T99\n\n{one.claim('small integers are shared')}\n\n## Something else")
    one.code("print(1 is 1)")
    with pytest.raises(Unproved):
        resolve(one.claims, one.cells)


def test_a_heading_before_the_claim_in_its_own_cell_is_fine(tmp_path):
    """The usual shape: a cell opens a section and the claim is in the paragraph under it."""
    one = lesson(tmp_path)
    one.md(f"## A section\n\n{one.claim('small integers are shared')}")
    one.code("print(1 is 1)")
    assert resolve(one.claims, one.cells)[0].evidence == "t99-02"


def test_an_unobservable_claim_needs_no_cell(tmp_path):
    one = lesson(tmp_path)
    one.md(f"# T99\n\n{one.claim('the header has two fields', unobservable='it is C')}")
    found = resolve(one.claims, one.cells)
    assert found[0].evidence == ""
    assert found[0].unobservable == "it is C"


def test_more_unobservable_claims_than_the_cap_is_refused(tmp_path):
    """Without the cap the escape hatch is the whole game and this goes back to being a book."""
    one = lesson(tmp_path)
    for number in range(UNOBSERVABLE_CAP + 1):
        one.md(f"# T99 {number}\n\n{one.claim(f'claim {number}', unobservable='it is C')}")
    with pytest.raises(TooMany, match=str(UNOBSERVABLE_CAP)):
        resolve(one.claims, one.cells)


def test_exactly_the_cap_is_allowed(tmp_path):
    one = lesson(tmp_path)
    for number in range(UNOBSERVABLE_CAP):
        one.md(f"# T99 {number}\n\n{one.claim(f'claim {number}', unobservable='it is C')}")
    assert len(resolve(one.claims, one.cells)) == UNOBSERVABLE_CAP


def test_every_unproved_claim_is_named_and_not_only_the_first(tmp_path):
    """An author who marked six and proved four wants both names, not one and a rebuild."""
    one = lesson(tmp_path)
    one.md(f"# T99\n\n{one.claim('the first thing')}\n\n{one.claim('the second thing')}")
    with pytest.raises(Unproved) as raised:
        resolve(one.claims, one.cells)
    assert "the first thing" in str(raised.value)
    assert "the second thing" in str(raised.value)


def test_saving_a_lesson_resolves_its_claims_rather_than_waiting_to_be_asked(tmp_path):
    """Otherwise a claim could lose its evidence and nothing would say so until the ledger was
    next rebuilt, which is exactly the drift this is here to stop."""
    one = lesson(tmp_path)
    one.md(f"# T99\n\n{one.claim('small integers are shared')}")
    with pytest.raises(Unproved):
        one.save([])


def test_a_hash_inside_a_fenced_block_is_not_a_heading():
    """Lessons quote C and shell sessions constantly, and those are full of comment lines."""
    body = "text\n\n```\n# not a heading\n```\n\nmore text\n"
    assert headings(body) == []


def test_a_real_heading_after_a_fenced_block_is_still_found():
    body = "```\n# not a heading\n```\n\n## a real one\n"
    assert len(headings(body)) == 1


def test_a_hash_with_no_space_after_it_is_not_a_heading():
    """`#!/usr/bin/env python` at the top of a quoted file is the case that matters."""
    assert headings("#!/usr/bin/env python\n") == []


def test_the_ledger_says_which_lessons_have_not_been_marked_up_yet():
    """The lessons were written before the ledger existed and are being done one at a time. A
    reader looking at a lesson with no rows deserves to know which of those two it is."""
    said = render([{"notebook": "lessons/t99-x/t99.ipynb", "title": "T99. A lesson", "claims": []}])
    assert "Not marked up yet." in said
    assert "| Claim |" not in said


def test_the_ledger_links_relative_to_itself_and_not_to_the_repository_root():
    """It lives in `lessons/`, so a link starting `lessons/` would be a broken one."""
    entry = {
        "notebook": "lessons/t99-x/t99.ipynb",
        "title": "T99. A lesson",
        "claims": [{"text": "a thing", "evidence": "t99-02", "unobservable": ""}],
    }
    assert "(t99-x/t99.ipynb)" in render([entry])


def test_the_ledger_counts_the_unobservable_ones_where_a_reader_can_see_the_total():
    entry = {
        "notebook": "lessons/t99-x/t99.ipynb",
        "title": "T99. A lesson",
        "claims": [
            {"text": "a thing", "evidence": "t99-02", "unobservable": ""},
            {"text": "another", "evidence": "", "unobservable": "it is C"},
        ],
    }
    assert "2 claims across 1 lessons, 1 of them not observable" in render([entry])
