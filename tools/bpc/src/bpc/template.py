"""Expanding a source document into the blueprint that gets committed.

A blueprint is part specification and part transcription. The specification part is written
by somebody who understands the subsystem and cannot be generated. The transcription part
is a table of every node and every field, which can be generated and therefore should be,
because a hand typed one is right the day it is written and wrong the first time upstream
adds a field.

So the source document holds the prose with a one line directive wherever a generated block
belongs, and this module swaps each directive for the block. The markers left behind in the
output are HTML comments, which are invisible on GitHub and obvious in an editor, and they
are what makes "no hand written content in a generated section" a thing anybody can see
rather than a thing everybody has to remember.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .model import Grammar
from .render import BLOCKS

#: `<!-- bpc: nodes -->` on a line of its own, which is what a source document writes.
DIRECTIVE = re.compile(r"^<!-- bpc: ([a-z][a-z-]*) -->$")

#: What the expanded document has instead, so the boundary survives into the output.
BEGIN = "<!-- bpc:begin {name} -->"
END = "<!-- bpc:end {name} -->"

#: Where the source documents live, and where their output goes.
SOURCES = Path("blueprints") / "sources"
OUTPUT = Path("blueprints")


class TemplateError(RuntimeError):
    """The source document asked for something that cannot be generated."""


@dataclass(frozen=True)
class Source:
    """One source document, and the file it produces."""

    path: Path

    @property
    def name(self) -> str:
        """`BP-AST`, which is the name of both the source and the output."""
        return self.path.stem

    @property
    def output(self) -> Path:
        """Where the expanded document belongs, which is one directory up."""
        return self.path.parent.parent / self.path.name

    def text(self) -> str:
        return self.path.read_text(encoding="utf-8")

    def blocks(self) -> list[str]:
        """The generated blocks this document asks for, in the order it asks for them."""
        found = []
        for line in self.text().splitlines():
            match = DIRECTIVE.match(line)
            if match is not None:
                found.append(match.group(1))
        return found


def expand(source: Source, grammar: Grammar) -> str:
    """The finished document: the prose, with every directive replaced by its block.

    Every generated block is checked as it goes in. An empty one means the grammar changed
    shape in a way the renderer did not follow, and shipping a section with a heading and
    nothing under it is how a specification comes to have a hole in it that reads like a
    subsystem with nothing to say.
    """
    seen: set[str] = set()
    out: list[str] = []
    for number, line in enumerate(source.text().splitlines(), start=1):
        match = DIRECTIVE.match(line)
        if match is None:
            out.append(line)
            continue
        name = match.group(1)
        if name not in BLOCKS:
            known = ", ".join(sorted(BLOCKS))
            raise TemplateError(
                f"{source.path}:{number}: there is no block called {name!r}, only {known}"
            )
        if name in seen:
            raise TemplateError(
                f"{source.path}:{number}: the {name!r} block is asked for twice, and a "
                "specification that states the same table in two places has two of them to "
                "keep in step"
            )
        seen.add(name)
        body = BLOCKS[name](grammar)
        if not body.strip():
            raise TemplateError(
                f"{source.path}:{number}: the {name!r} block came out empty, which means the "
                "grammar no longer has what the renderer went looking for"
            )
        out.append(BEGIN.format(name=name))
        out.append(body)
        out.append(END.format(name=name))
    if not seen:
        raise TemplateError(
            f"{source.path}: no `<!-- bpc: name -->` directives, so there is nothing here "
            "that bpc can generate and the file does not need to be a source document"
        )
    return "\n".join(out).rstrip("\n") + "\n"


def find(root: Path = SOURCES) -> list[Source]:
    """Every source document under `blueprints/sources`, sorted."""
    if not root.is_dir():
        return []
    return [Source(path) for path in sorted(root.glob("BP-*.md"))]
