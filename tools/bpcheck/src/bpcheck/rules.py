"""What a blueprint has to look like before anybody is asked to implement from it.

A lesson can be wrong in ways a reader notices. A blueprint cannot, because the reader is
typing code against it and will believe a missing section is a subsystem with nothing to
say. Every rule here is a way a specification quietly stops being one.

The rules are blunt on purpose. Somebody who trips one should be able to fix it from the
message without opening this file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .document import Document

#: The nine sections, in this order, in every blueprint. The order is part of the format:
#: a reader who has read one blueprint knows where the invariants are in all of them, and
#: that only holds if nothing is ever moved or dropped.
SECTIONS: list[str] = [
    "Purpose and scope",
    "Data structures",
    "Algorithms",
    "Invariants",
    "Observable behaviour",
    "Edge cases and error paths",
    "Interactions",
    "Conformance",
    "Port notes",
]

#: The header block, in this order, directly under the title.
FIELDS: list[str] = ["Covers", "Lesson", "Status", "Compatibility tier"]

#: An honest status beats an aspirational one. A stub that says stub is useful.
STATUSES = {"complete", "partial", "stub"}

#: How closely a reimplementation has to match before a Python program can tell.
TIERS = {"A", "B", "C", "D"}

#: The section holding the numbered invariants, and the section allowed to name lessons.
INVARIANTS_SECTION = 4
CONFORMANCE_SECTION = 8

#: Punctuation the project does not use in prose. The characters are written as escapes
#: because the linter flags the literals as ambiguous, which is a fair complaint
#: everywhere except in the one dictionary whose job is to name them.
FORBIDDEN_CHARACTERS = {
    "\u2014": "em dash",
    "\u2013": "en dash",
}

#: A markdown horizontal rule. Table separators like `|---|` are not one of these.
HORIZONTAL_RULE = re.compile(r"^ {0,3}([-*_])(\s*\1){2,}\s*$")

#: `**INV-PIPELINE-004.**` at the start of a line, which is how an invariant is stated.
DEFINITION = re.compile(r"^\*\*INV-([A-Z][A-Z0-9]*)-(\d{3})\.\*\*")

#: The same identifier anywhere, which is how one is referred to.
REFERENCE = re.compile(r"\bINV-([A-Z][A-Z0-9]*)-(\d{3})\b")

#: A citation without its `@tag` is invisible to refcheck, so it is never resolved and
#: never goes stale in a way anybody notices. That is worse than having no citation.
UNTAGGED = re.compile(r"(?<![\w@/])([\w./-]+\.(?:c|h|py|md|gram|asdl)):(\d+(?:-\d+)?)(?![\w@:-])")

#: A blueprint that sends the reader to a lesson for a fact has stopped being a
#: specification. Section 8 is exempt, because naming the lesson that holds a claim up is
#: what that section is for.
DEFERRAL = re.compile(
    r"(?i)\b(?:see|refer to|explained in|described in|covered in)\b[^.\n]{0,60}"
    r"\b(?:lesson|[TZ]\d{2})\b"
)


@dataclass(frozen=True)
class Problem:
    """One thing wrong with one blueprint, said in a way an author can act on."""

    path: Path
    line: int | None
    rule: str
    message: str

    def __str__(self) -> str:
        where = f"{self.path}" if self.line is None else f"{self.path}:{self.line}"
        return f"{where}: {self.message} [{self.rule}]"


def _title(document: Document) -> list[Problem]:
    if document.title_line is None:
        return [Problem(document.path, 1, "title", "no `# ` title on the first line")]
    if document.title is None:
        return [
            Problem(
                document.path,
                document.title_line,
                "title",
                "the title must read `# BP-NAME: what it covers`",
            )
        ]
    if document.title != document.stem:
        return [
            Problem(
                document.path,
                document.title_line,
                "title",
                f"the title says {document.title} and the file is named {document.stem}",
            )
        ]
    return []


def _header(document: Document) -> list[Problem]:
    problems: list[Problem] = []
    names = [field.name for field in document.fields]
    if names != FIELDS:
        problems.append(
            Problem(
                document.path,
                document.title_line,
                "header",
                f"the header block must be {', '.join(FIELDS)} in that order, and it is "
                f"{', '.join(names) if names else 'missing'}",
            )
        )
        return problems

    status = document.field("Status")
    if status is not None and status.value not in STATUSES:
        problems.append(
            Problem(
                document.path,
                status.line,
                "status",
                f"Status is {status.value!r} and must be one of {', '.join(sorted(STATUSES))}",
            )
        )

    tier = document.field("Compatibility tier")
    if tier is not None and tier.value not in TIERS:
        problems.append(
            Problem(
                document.path,
                tier.line,
                "tier",
                f"Compatibility tier is {tier.value!r} and must be one of "
                f"{', '.join(sorted(TIERS))}",
            )
        )
    return problems


def _sections(document: Document) -> list[Problem]:
    problems: list[Problem] = []
    found = [section.heading for section in document.sections]
    wanted = [f"{number}. {title}" for number, title in enumerate(SECTIONS, start=1)]
    if found != wanted:
        missing = [heading for heading in wanted if heading not in found]
        extra = [heading for heading in found if heading not in wanted]
        detail = []
        if missing:
            detail.append(f"missing {', '.join(missing)}")
        if extra:
            detail.append(f"unexpected {', '.join(extra)}")
        if not detail:
            detail.append(f"out of order, found {', '.join(found)}")
        problems.append(
            Problem(
                document.path,
                None,
                "sections",
                f"the nine sections are wrong: {'; '.join(detail)}",
            )
        )
        return problems

    for section in document.sections:
        if not any(line.strip() for line in section.body):
            problems.append(
                Problem(
                    document.path,
                    section.line,
                    "empty-section",
                    f"section {section.heading} has no body, and a stub still has to say so",
                )
            )
    return problems


def _invariants(document: Document) -> list[Problem]:
    slug = document.slug
    if slug is None:
        return [
            Problem(
                document.path,
                None,
                "name",
                f"{document.stem} is not named `BP-NAME`, so its invariants cannot be checked",
            )
        ]

    section = document.section(INVARIANTS_SECTION)
    if section is None:
        return []

    problems: list[Problem] = []
    defined: list[int] = []
    for offset, line in enumerate(section.body):
        match = DEFINITION.match(line)
        if match is None:
            continue
        line_number = section.line + 1 + offset
        if match.group(1) != slug:
            problems.append(
                Problem(
                    document.path,
                    line_number,
                    "invariant-slug",
                    f"INV-{match.group(1)}-{match.group(2)} is stated in {document.stem}, "
                    f"whose invariants are INV-{slug}-NNN",
                )
            )
            continue
        defined.append(int(match.group(2)))

    if not defined:
        problems.append(
            Problem(
                document.path,
                section.line,
                "no-invariants",
                "section 4 states no invariants, and every subsystem has at least one",
            )
        )
        return problems

    expected = list(range(1, len(defined) + 1))
    if defined != expected:
        problems.append(
            Problem(
                document.path,
                section.line,
                "invariant-numbering",
                f"the invariants are numbered {defined} and must run 001 upwards with no "
                "gaps and no repeats",
            )
        )

    known = set(defined)
    for offset, line in enumerate(document.lines):
        for match in REFERENCE.finditer(line):
            if match.group(1) != slug:
                continue
            if int(match.group(2)) not in known:
                problems.append(
                    Problem(
                        document.path,
                        offset + 1,
                        "unknown-invariant",
                        f"{match.group(0)} is referred to and is not stated in section 4",
                    )
                )
    return problems


def _prose(document: Document) -> list[Problem]:
    problems: list[Problem] = []
    for offset, line in enumerate(document.lines):
        line_number = offset + 1
        for character, name in FORBIDDEN_CHARACTERS.items():
            if character in line:
                problems.append(
                    Problem(document.path, line_number, "punctuation", f"contains an {name}")
                )
        if HORIZONTAL_RULE.match(line):
            problems.append(
                Problem(
                    document.path,
                    line_number,
                    "page-break",
                    "horizontal rules are not used anywhere in this project",
                )
            )
    return problems


def _citations(document: Document) -> list[Problem]:
    problems: list[Problem] = []
    for offset, line in enumerate(document.lines):
        for match in UNTAGGED.finditer(line):
            problems.append(
                Problem(
                    document.path,
                    offset + 1,
                    "untagged-citation",
                    f"{match.group(0)} has no @tag, so nothing ever checks it",
                )
            )
    return problems


def _deferral(document: Document) -> list[Problem]:
    problems: list[Problem] = []
    for section in document.sections:
        if section.number == CONFORMANCE_SECTION:
            continue
        for offset, line in enumerate(section.body):
            match = DEFERRAL.search(line)
            if match is not None:
                problems.append(
                    Problem(
                        document.path,
                        section.line + 1 + offset,
                        "deferral",
                        f"{match.group(0)!r} sends the reader to a lesson for a fact, and a "
                        "blueprint has to carry the fact itself",
                    )
                )
    return problems


def check(document: Document) -> list[Problem]:
    """Every problem with one blueprint, in the order somebody would want to fix them."""
    problems = _title(document)
    problems.extend(_header(document))
    problems.extend(_sections(document))
    problems.extend(_invariants(document))
    problems.extend(_prose(document))
    problems.extend(_citations(document))
    problems.extend(_deferral(document))
    return problems


def check_index(index: Path, text: str, documents: list[Document]) -> list[Problem]:
    """Every blueprint has to be listed in the index, or nobody will find it.

    This is the rule that stops the directory and its README from drifting apart, which is
    the failure that makes a reader assume a missing blueprint was never written.
    """
    problems = []
    for document in documents:
        if f"({document.path.name})" not in text:
            problems.append(
                Problem(
                    index,
                    None,
                    "index",
                    f"{document.path.name} is not linked from the index",
                )
            )
    return problems
