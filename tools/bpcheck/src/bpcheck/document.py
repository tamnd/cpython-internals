"""Reading a blueprint into the few pieces the rules care about.

A blueprint is markdown, so almost anything parses. This module deliberately keeps only
the structure the rules are about: the title, the header block, and the top level
sections with the lines under each of them. Everything else stays as text.

Nothing here decides whether a document is right. That is `rules.py`. A blueprint that is
missing every section still loads, and the rules then say so one problem at a time, which
is far more useful than a parse error that names the first thing it tripped on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

#: A blueprint file is named after the thing it specifies. `BP-PIPELINE.md` holds
#: `BP-PIPELINE`, its invariants are `INV-PIPELINE-001` and up, and the checks lean on
#: all three agreeing.
NAME_PATTERN = re.compile(r"^BP-([A-Z][A-Z0-9]*)$")

TITLE_PATTERN = re.compile(r"^# (BP-[A-Z][A-Z0-9]*): (.+)$")
FIELD_PATTERN = re.compile(r"^\*\*([^*]+):\*\* (.+)$")
SECTION_PATTERN = re.compile(r"^## (\d+)\. (.+)$")


class DocumentError(Exception):
    """The file could not be read at all, as opposed to being wrong."""


@dataclass(frozen=True)
class Field:
    """One line of the header block, with the line it came from."""

    name: str
    value: str
    line: int


@dataclass(frozen=True)
class Section:
    """One top level section, and everything under it up to the next one."""

    number: int
    title: str
    line: int
    body: list[str]

    @property
    def heading(self) -> str:
        return f"{self.number}. {self.title}"


@dataclass(frozen=True)
class Document:
    """One blueprint, split into the pieces the rules ask about."""

    path: Path
    lines: list[str]
    title: str | None
    subtitle: str | None
    title_line: int | None
    fields: list[Field]
    sections: list[Section]

    @property
    def stem(self) -> str:
        """`BP-PIPELINE` for `blueprints/BP-PIPELINE.md`, whatever is inside the file."""
        return self.path.stem

    @property
    def slug(self) -> str | None:
        """`PIPELINE` for `BP-PIPELINE.md`, or None when the file is not named like one."""
        match = NAME_PATTERN.match(self.stem)
        return match.group(1) if match else None

    def field(self, name: str) -> Field | None:
        for field in self.fields:
            if field.name == name:
                return field
        return None

    def section(self, number: int) -> Section | None:
        for section in self.sections:
            if section.number == number:
                return section
        return None


def _parse_header(lines: list[str], start: int) -> tuple[list[Field], int]:
    """The run of `**Name:** value` lines under the title, and where it ends.

    The block ends at the first line that is not a field, which is usually the blank line
    before section 1. Stopping on the first miss rather than scanning the whole file is
    what keeps a bold line in the middle of section 3 from being read as a header field.
    """
    fields: list[Field] = []
    index = start
    while index < len(lines):
        line = lines[index].rstrip()
        if not line:
            if fields:
                break
            index += 1
            continue
        match = FIELD_PATTERN.match(line)
        if match is None:
            break
        fields.append(Field(match.group(1), match.group(2), index + 1))
        index += 1
    return fields, index


def parse(path: Path, text: str) -> Document:
    """Split one blueprint into its pieces. Never raises for a wrong document."""
    lines = text.splitlines()

    title = None
    subtitle = None
    title_line = None
    header_start = 0
    for index, line in enumerate(lines):
        if line.startswith("# "):
            match = TITLE_PATTERN.match(line.rstrip())
            if match is not None:
                title = match.group(1)
                subtitle = match.group(2)
            title_line = index + 1
            header_start = index + 1
            break

    fields, _ = _parse_header(lines, header_start)

    sections: list[Section] = []
    pending: list[tuple[int, str, int]] = []
    starts: list[int] = []
    for index, line in enumerate(lines):
        match = SECTION_PATTERN.match(line.rstrip())
        if match is not None:
            pending.append((int(match.group(1)), match.group(2), index + 1))
            starts.append(index)
    for position, (number, section_title, line_number) in enumerate(pending):
        begin = starts[position] + 1
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        sections.append(Section(number, section_title, line_number, lines[begin:end]))

    return Document(
        path=path,
        lines=lines,
        title=title,
        subtitle=subtitle,
        title_line=title_line,
        fields=fields,
        sections=sections,
    )


def load(path: Path) -> Document:
    """Read and parse one blueprint."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise DocumentError(f"{path}: could not be read: {error}") from error
    return parse(path, text)


def find(roots: list[Path]) -> list[Path]:
    """Every `BP-*.md` under the given roots, sorted, with `README` and `NOTATION` left out.

    The two prose files in `blueprints/` are not blueprints and do not have the nine
    sections. Matching on the `BP-` prefix rather than excluding them by name means a
    third prose file added later needs no change here.
    """
    found: list[Path] = []
    for root in roots:
        path = Path(root)
        if path.is_file():
            found.append(path)
            continue
        found.extend(sorted(path.glob("BP-*.md")))
    return sorted(set(found))
