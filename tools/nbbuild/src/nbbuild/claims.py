"""The claim ledger, and the rule that a claim has to be runnable.

The promise at the top of the README is that nothing in this project is asserted without an
experiment. That is easy to write and easy to drift away from, because the sentence that
quietly becomes untrue is never the one somebody was paying attention to. It is a number that
was right on the version it was written against, or a "CPython does X" that was true of the
build the author happened to have.

So a lesson marks its behavioural claims as it makes them:

    lesson.md(f'''
    {lesson.claim("integers from -5 to 256 are shared rather than made fresh")}, which is
    why two names holding 100 are the same object and two names holding 1000 are not.
    ''')

`claim` returns the sentence unchanged, so it reads exactly as it would have without the call
and the reader sees no difference. What it adds is a record, and a rule the build enforces:

**A claim's evidence is the next code cell, and that cell has to come before the next
section heading.** Proving it three sections later is not proving it, because nobody reading
the paragraph will find the cell. Having no cell at all is the case this is really for.

Some true things about CPython cannot be observed from Python. The layout of `PyObject`, what
the allocator does with a freed block, the fact that the eval loop is one enormous switch. A
claim like that is marked with the reason it cannot be shown, and those are capped at three
per lesson, because without a cap the escape hatch is the whole game and this turns back into
a book with citations.

The ledger itself is generated into `lessons/CLAIMS.md` and committed, the same way the
notebooks and the glossary are, so it can be read without running anything.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: How many claims a lesson is allowed to mark as unobservable from Python. Three is small
#: enough to be a real constraint and large enough that a lesson about the object header is
#: not impossible to write. It is a number in a file rather than a rule in somebody's head
#: because the whole point is that raising it has to be a visible decision.
UNOBSERVABLE_CAP = 3


class TooMany(ValueError):
    """Raised when a lesson marks more claims unobservable than the cap allows."""


class Unproved(ValueError):
    """Raised when a claim has no runnable cell behind it before the next heading."""


@dataclass(frozen=True)
class Claim:
    """One behavioural claim, and where in the lesson it was made.

    `at` is the index the claim's own prose cell will land at, taken while the f-string is
    being evaluated and therefore before the cell exists. That is the whole trick: it means
    the claim knows where it is without the author having to say.
    """

    text: str
    at: int
    unobservable: str = ""

    #: The id of the code cell that proves it, filled in once the lesson is complete. Empty
    #: for an unobservable claim, which is the point of marking one.
    evidence: str = ""


def headings(body: str) -> list[int]:
    """Where the section headings start in a markdown cell.

    Fenced blocks are skipped, because a lesson quoting a C file or a shell session is full
    of lines beginning with a hash and none of them opens a section.
    """
    found = []
    at = 0
    fenced = False
    for line in body.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced and re.match(r"#{1,6} ", line):
            found.append(at)
        at += len(line)
    return found


def _source(cell: dict) -> str:
    return "".join(cell["source"])


def evidence_for(claim: Claim, cells: list[dict]) -> str:
    """The id of the cell that proves this claim, or an empty string if nothing does.

    Walks forward from the claim's own cell and stops at the next section heading. Stopping
    is what makes this mean anything: without it, every claim in the lesson would resolve to
    some code cell somewhere below it and the check would pass on a lesson that proves
    nothing.

    A heading in the middle of the claim's own cell counts too, which is not a detail. Cells
    here routinely end with the heading that opens the next section, so a claim made in the
    paragraph above one of those is a claim whose next code cell belongs to a different
    section. The claim text is found by searching the finished cell for it, which works
    because `claim` returns the text and the text therefore appears verbatim.
    """
    own = cells[claim.at] if claim.at < len(cells) else None
    if own is not None:
        body = _source(own)
        where = body.find(claim.text)
        if where >= 0 and any(at > where for at in headings(body)):
            return ""

    for cell in cells[claim.at + 1 :]:
        if cell["cell_type"] == "code":
            return cell["id"]
        if headings(_source(cell)):
            return ""
    return ""


def resolve(claims: list[Claim], cells: list[dict]) -> list[Claim]:
    """Attach each claim to its evidence, and complain about the ones with none.

    Every problem at once rather than the first one. An author who has marked six claims and
    proved four wants both missing cells named, not one and then a rebuild.
    """
    marked = sum(1 for one in claims if one.unobservable)
    if marked > UNOBSERVABLE_CAP:
        raise TooMany(
            f"{marked} claims marked unobservable and the cap is {UNOBSERVABLE_CAP}. "
            "Either one of them can be shown after all, or the lesson is trying to cover "
            "something the reader cannot get at from here."
        )

    done = []
    missing = []
    for one in claims:
        if one.unobservable:
            done.append(one)
            continue
        found = evidence_for(one, cells)
        if not found:
            missing.append(one.text)
        done.append(Claim(one.text, one.at, one.unobservable, found))

    if missing:
        listed = "\n".join(f"  {text}" for text in missing)
        raise Unproved(
            f"{len(missing)} claim(s) with no code cell before the next heading:\n{listed}\n"
            "Put a runnable cell under the paragraph, or mark the claim unobservable with "
            "the reason it cannot be shown."
        )
    return done


def title(cells: list[dict]) -> str:
    """The lesson's own heading, so the ledger does not need a second copy of the titles."""
    for cell in cells:
        if cell["cell_type"] != "markdown":
            continue
        body = _source(cell)
        for at in headings(body):
            return body[at:].splitlines()[0].lstrip("# ").strip()
    return ""


def as_json(claims: list[Claim], cells: list[dict], relative: str) -> dict:
    """One lesson's entry, as the builder hands it to the collector.

    Builders run in their own processes, which is deliberate and means the ledger cannot be
    assembled by importing them. So each one prints this and `nbbuild claims` reads it back.
    """
    return {
        "notebook": relative,
        "title": title(cells),
        "claims": [
            {"text": one.text, "evidence": one.evidence, "unobservable": one.unobservable}
            for one in claims
        ],
    }


HEADER = """# The claim ledger

Every behavioural claim the lessons make about CPython, and the cell that proves it.

This file is generated. A lesson marks a claim where it makes it, the build works out which
cell answers it, and `just claims` fails when one has no answer. The rule is that the
evidence is the next code cell and it has to come before the next section heading, because a
claim proved three sections later is a claim nobody checked.

A handful of true things cannot be observed from Python at all: the layout of an object
header, what the allocator does with a freed block, the shape of the eval loop. Those are
marked with the reason, and a lesson is allowed at most {cap} of them. The cap is the point.
Without it the exception becomes the rule and this goes back to being a book.
"""


def render(entries: list[dict]) -> str:
    """The whole ledger as the exact text that belongs on disk."""
    out = [HEADER.format(cap=UNOBSERVABLE_CAP)]
    total = sum(len(one["claims"]) for one in entries)
    marked = sum(1 for one in entries for c in one["claims"] if c["unobservable"])
    out.append(
        f"\n{total} claims across {len(entries)} lessons, {marked} of them not observable "
        f"from Python.\n"
    )
    for entry in entries:
        out.append(f"\n## {entry['title']}\n")
        # A lesson with nothing marked yet says so rather than showing an empty table. The
        # lessons were written before the ledger existed and are being marked up one at a
        # time, and a reader deserves to know which of those they are looking at.
        if not entry["claims"]:
            out.append("\nNot marked up yet.\n")
            continue
        out.append("\n| Claim | Proved by |\n| --- | --- |\n")
        for one in entry["claims"]:
            if one["unobservable"]:
                answer = f"not observable from Python: {one['unobservable']}"
            else:
                # The ledger sits in `lessons/`, so the link is relative to that rather than
                # to the repository root the notebook path is written against.
                here = entry["notebook"].removeprefix("lessons/")
                answer = f"[`{one['evidence']}`]({here})"
            out.append(f"| {one['text']} | {answer} |\n")
    return "".join(out)
