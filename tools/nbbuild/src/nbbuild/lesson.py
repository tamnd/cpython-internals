"""Writing a lesson notebook as a Python file instead of as JSON.

The `.ipynb` format is JSON with the prose stored as lists of strings with the newlines
left on. It is fine for a machine and hostile to a human: the diff for changing one word
is unreadable, ids have to be unique and are easy to duplicate by hand, and there is
nowhere to put a comment explaining why a cell is the way it is.

So the source of truth for every lesson is a `build.py` next to it, and the notebook is
generated. That buys three things. Prose lives in a triple quoted string where it can be
read and reviewed. Citations are produced by the same parser CI validates them with, so a
malformed one fails at build time rather than at review time. And the ids are counted out
rather than typed, which removes the whole class of mistake.

The generated notebook is committed, because a reader clicking a Colab badge must not need
a build step. `nbbuild check` re-runs every builder and fails if the committed file has
drifted, which is what stops the two from disagreeing.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from pyxray.cite import markdown as cite_markdown

#: Colab reads notebooks straight out of GitHub, so the badge has to name the branch as
#: well as the path. Anything else opens an older copy of the lesson without saying so.
COLAB = "https://colab.research.google.com/github/tamnd/cpython-internals/blob/main"
BADGE_IMAGE = "https://colab.research.google.com/assets/colab-badge.svg"

#: Punctuation the project does not use, written as escapes because these characters are
#: almost indistinguishable from a hyphen in a diff, which is exactly why they get in.
BANNED = (("\u2014", "em dash"), ("\u2013", "en dash"))


def repository_root(start: Path | None = None) -> Path:
    """The top of the checkout, found by looking for the workspace pyproject.

    A builder is run from wherever the author happens to be standing, and writing the
    notebook next to the current directory rather than next to the lesson is a mistake that
    is annoying to notice and trivial to prevent.
    """
    here = (start or Path(__file__)).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "pyproject.toml").exists() and (candidate / "lessons").exists():
            return candidate
    raise RuntimeError(f"cannot find the repository root from {here}")


class Malformed(ValueError):
    """Raised for a cell that would produce a notebook nobody wants to read."""


@dataclass
class Lesson:
    """One lesson under construction.

    `slug` is the directory name and `stem` is the file name and the id prefix, so T02
    lives at `lessons/t02-text-becomes-tokens/t02.ipynb` with cells `t02-01` upwards.
    """

    slug: str
    stem: str
    root: Path = field(default_factory=repository_root)
    cells: list[dict] = field(default_factory=list)

    @property
    def path(self) -> Path:
        return self.root / "lessons" / self.slug / f"{self.stem}.ipynb"

    @property
    def relative(self) -> str:
        return f"lessons/{self.slug}/{self.stem}.ipynb"

    @property
    def badge(self) -> str:
        """The Colab badge for this lesson, built from its own path.

        Copying the previous lesson and forgetting to change the link is the easiest
        mistake in the project and `nbcheck` has a rule for catching it. Generating the
        badge from the path the notebook is about to be written to means it cannot happen
        in the first place.
        """
        return f"[![Open In Colab]({BADGE_IMAGE})]({COLAB}/{self.relative})"

    def cite(self, citation: str) -> str:
        """A citation as a markdown link, labelled with the full citation.

        The label is the whole thing rather than a friendly name on purpose. A reader
        skimming for the file and line should not have to hover over anything.
        """
        return cite_markdown(citation, citation)

    def _add(self, kind: str, text: str, extra: dict) -> None:
        body = text.strip("\n")
        if not body.strip():
            raise Malformed(f"cell {len(self.cells) + 1} is empty")
        cell = {
            "cell_type": kind,
            "id": f"{self.stem}-{len(self.cells) + 1:02d}",
            "metadata": {},
            "source": body.splitlines(keepends=True),
            **extra,
        }
        # Keys in alphabetical order, which is what nbformat writes and therefore what any
        # tool that round trips a notebook will write back. Choosing a different order here
        # would mean opening a lesson in Jupyter and saving it reorders the whole file.
        self.cells.append(dict(sorted(cell.items())))

    def md(self, text: str) -> None:
        """A prose cell.

        Two of the project's writing rules are checked here rather than in review, because
        both are invisible in a diff and neither has ever been caught by a human.
        """
        for character, name in BANNED:
            if character in text:
                raise Malformed(f"cell {len(self.cells) + 1} contains an {name}")
        self._add("markdown", text, {})

    def code(self, text: str) -> None:
        """A code cell, with no outputs and no execution count.

        Outputs are never committed. The only proof a cell works is CI executing it, and a
        stored output is a screenshot that goes stale without telling anybody.
        """
        self._add("code", text, {"execution_count": None, "outputs": []})

    def document(self) -> str:
        """The finished notebook as the exact text that belongs on disk."""
        metadata = {
            # Colab writes this key itself on first save. Putting it here means opening a
            # lesson and saving it does not produce a diff that is pure noise.
            "colab": {"provenance": []},
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        }
        book = {
            "cells": self.cells,
            "metadata": dict(sorted(metadata.items())),
            "nbformat": 4,
            "nbformat_minor": 5,
        }
        return json.dumps(book, indent=1) + "\n"

    def save(self, argv: list[str] | None = None) -> int:
        """Write the notebook, or with `--check` report whether it is already correct.

        Both modes are the same function so that the thing CI verifies is the thing an
        author runs, rather than a second implementation that agrees with it most of the
        time.
        """
        arguments = sys.argv[1:] if argv is None else argv
        text = self.document()
        if "--check" in arguments:
            if not self.path.exists():
                print(f"{self.relative} has not been built")
                return 1
            if self.path.read_text() != text:
                print(f"{self.relative} does not match its builder, run `just lessons`")
                return 1
            print(f"{self.relative} is up to date")
            return 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(text)
        print(f"wrote {self.relative}, {len(self.cells)} cells")
        return 0
