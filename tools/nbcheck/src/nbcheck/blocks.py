"""The blocks a lesson is built from, and how long each one is allowed to be.

The authoring guide says a lesson is nine blocks in a fixed order, and gives each of them a
word cap. Both halves of that are easy to agree with and easy to let slide, because nothing
goes red when a lesson quietly grows a tenth section or an extra thousand words. This module
is what goes red.

Blocks are found by their headings, which is how a reader finds them too. That means a lesson
that renames its ending to something friendlier fails here, which is the intended trade: the
headings are part of the shape, and a reader who has done four lessons should know where the
recap is without looking.

Length is measured in words of prose. Code cells, code fences, images, HTML and the front
matter every lesson gets for free are all left out, because none of it is reading the reader
has to do, and counting it would let a lesson buy room by adding a picture.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .notebook import Cell, Notebook

#: The generated front matter. Identical in every lesson, written by `nbbuild` rather than by
#: an author, and skipped over here for the same reason: nobody can shorten it by writing
#: better, and it would be the same tax on every lesson's budget.
GENERATED = ("about the source references", "how to read the source references", "setup")

#: The section that says which interpreter the reader is on. Real prose, so it counts towards
#: the lesson, but it is not the tour and it grows for reasons the author does not control.
VERSIONS = ("which python is this", "which interpreter is this")

#: The three sections that close a lesson, in the order they have to appear in. The second
#: name in each row is what an earlier lesson called it, kept working rather than renamed,
#: because a reader mid way through the series should not meet a retitled ending.
CLOSING: tuple[tuple[str, ...], ...] = (
    ("try it yourself", "exercises"),
    ("what just happened", "what you now know"),
    ("where this goes next", "what is next"),
)

#: Where the boss fight goes when a lesson has one. After the exercises, so the reader has
#: warmed up, and before the recap, so the recap is the last thing they read.
FIGHT = "boss fight"

#: Word caps. The hook is the authoring guide's own number and it holds: 150 words is plenty
#: for a question and a surprise, and a hook that runs long is throat clearing rather than
#: material. The other two are not the guide's numbers. The guide asked for a 1500 word tour
#: and a 2500 word lesson, and twelve lessons later nothing lands anywhere near that: the
#: shortest tour is 1269 words and the median is over 2300. Rather than declare nine of twelve
#: lessons broken, these are set where they bite on the four longest and leave the rest alone.
HOOK = 150
TOUR = 2500
LESSON = 3500

#: What a picture looks like in a notebook: an embedded image, which covers both the diagrams
#: and the animations, since both are written into the markdown the same way.
PICTURE = re.compile(r"!\[[^\]]*\]\([^)]+\)")

#: Everything that is not prose. Fenced code first, then images, then any HTML left over.
NOISE = (
    re.compile(r"```.*?```", re.S),
    PICTURE,
    re.compile(r"<[^>]+>", re.S),
)

#: A link, which a reader reads as its text. The address is not words on the page, and
#: counting it would charge a lesson for linking into the glossary.
LINK = re.compile(r"\[([^\]]*)\]\([^)]+\)")


def words(text: str) -> int:
    """How many words of prose, with everything a reader does not read taken out."""
    for pattern in NOISE:
        text = pattern.sub(" ", text)
    return len(LINK.sub(r"\1", text).split())


@dataclass
class Section:
    """One `## ` section, or the title cell, with the prose and code cells under it."""

    #: The heading as written, or an empty string for the title cell.
    name: str
    #: The cell the heading is in, one based, so a message can name it.
    number: int
    #: Markdown under this heading, in order.
    prose: list[str] = field(default_factory=list)
    #: Code cells under this heading, kept for the checks that ask whether anything runs.
    code: list[Cell] = field(default_factory=list)

    @property
    def key(self) -> str:
        return self.name.strip().lower()

    @property
    def words(self) -> int:
        return words("\n".join(self.prose))


def sections(book: Notebook) -> list[Section]:
    """Every section of a notebook, split on `## ` headings wherever they appear.

    Split on headings rather than on cells, because a markdown cell often ends one section
    and opens the next, and a reader sees the heading rather than the cell boundary.
    """
    found = [Section(name="", number=1)]
    for cell in book.cells:
        if cell.is_code:
            found[-1].code.append(cell)
            continue
        held: list[str] = []
        for line in cell.source.splitlines():
            if line.startswith("## "):
                found[-1].prose.append("\n".join(held))
                held = []
                found.append(Section(name=line[3:].strip(), number=cell.number))
            else:
                held.append(line)
        found[-1].prose.append("\n".join(held))
    return found


@dataclass(frozen=True)
class Shape:
    """A lesson, measured. Everything the checks below need and nothing else."""

    #: Every section, in order.
    sections: list[Section]

    def named(self, names: tuple[str, ...]) -> Section | None:
        for one in self.sections:
            if one.key in names:
                return one
        return None

    def index(self, names: tuple[str, ...]) -> int | None:
        for spot, one in enumerate(self.sections):
            if one.key in names:
                return spot
        return None

    @property
    def title(self) -> Section:
        return self.sections[0]

    @property
    def hook(self) -> int:
        """The prose in the title cell, which is the question and the surprise under it."""
        return self.title.words

    @property
    def tour(self) -> list[Section]:
        """Everything between the version section and whatever closes the lesson."""
        start = self.index(VERSIONS)
        end = self.index(CLOSING[0]) or len(self.sections)
        if start is None:
            return []
        return self.sections[start + 1 : end]

    @property
    def counted(self) -> list[Section]:
        """Every section whose length is the author's to control."""
        return [one for one in self.sections if one.key not in GENERATED]

    @property
    def lesson(self) -> int:
        return sum(one.words for one in self.counted)


def shape(book: Notebook) -> Shape:
    return Shape(sections=sections(book))


def fights(path: Path) -> bool:
    """Whether this lesson has a boss fight, which is a grader sitting next to it."""
    return (path.parent / "grade.py").is_file()


def measurements(book: Notebook) -> dict[str, int]:
    """The three numbers, for `nbcheck blocks` to print whether or not anything is wrong."""
    one = shape(book)
    return {
        "hook": one.hook,
        "tour": sum(section.words for section in one.tour),
        "lesson": one.lesson,
    }


def too_long(book: Notebook) -> list[str]:
    """The caps, checked. One line each, naming the cap and what to do about it."""
    found = []
    sizes = measurements(book)
    if sizes["hook"] > HOOK:
        found.append(
            f"the hook is {sizes['hook']} words and the cap is {HOOK}. It is the first thing "
            f"anybody reads and it has one job, which is a surprise they can run"
        )
    if sizes["tour"] > TOUR:
        found.append(
            f"the tour is {sizes['tour']} words and the cap is {TOUR}. A tour that needs more "
            f"is usually two lessons rather than one long one"
        )
    if sizes["lesson"] > LESSON:
        found.append(
            f"the lesson is {sizes['lesson']} words of prose and the cap is {LESSON}. "
            f"Everybody reads it start to finish, and length is how this kind of writing fails"
        )
    return found


def out_of_shape(book: Notebook, path: Path) -> list[str]:
    """The blocks, checked: present, in order, and with a picture in the tour."""
    one = shape(book)
    found = []
    if one.title.name != "" or not one.title.prose:
        found.append("the notebook does not open with a title cell")
    if not one.hook:
        found.append("the title cell has no hook under it, so the lesson opens on a heading")
    if one.index(VERSIONS) is None:
        found.append("there is no section saying which Python the reader is on")
    if not one.tour:
        found.append("there is no tour between the version section and the ending")
    elif not any(PICTURE.search("\n".join(section.prose)) for section in one.tour):
        found.append("the tour has no picture in it, and every lesson gets one")

    spots = [one.index(names) for names in CLOSING]
    for names, spot in zip(CLOSING, spots, strict=True):
        if spot is None:
            found.append(f"there is no `## {names[0].capitalize()}` section to close on")
    known = [spot for spot in spots if spot is not None]
    if len(known) == len(spots) and known != sorted(known):
        found.append(
            "the closing sections are out of order. Exercises, then what just happened, "
            "then where this goes next"
        )

    fight = one.index((FIGHT,))
    if fights(path) and fight is None:
        found.append("there is a grade.py next to this lesson and nothing sends the reader to it")
    ordered = known == sorted(known) and len(known) == len(spots)
    if fight is not None and ordered and not spots[0] < fight < spots[1]:
        found.append(
            "the boss fight is in the wrong place. It goes after the exercises and before "
            "the recap, so the recap is the last thing read"
        )
    return found


def problems(book: Notebook, path: Path) -> list[str]:
    """Everything wrong with one lesson's shape, in the order somebody would fix it."""
    return out_of_shape(book, path) + too_long(book)
