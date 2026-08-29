"""Which boss fights exist, and where every piece of one lives.

A fight is four files. The grader, at `lessons/<lesson>/grade.py`, which a reader runs with a
plain `python` and no install. The starter, at `lessons/<lesson>/boss/starter.py`, which is
what they copy before they write anything. And two submissions under `tools/boss/submissions`,
one that passes and one that fails, which is what CI runs so that neither the grader nor the
fight can quietly stop working.

The submissions live in this directory rather than next to the lesson on purpose. The good one
is the answer, and an answer sitting in the folder a reader has just been told to copy from is
an answer they will read by accident.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

#: The top of the repository, found from this file so that nothing has to be run from a
#: particular directory.
REPOSITORY = Path(__file__).resolve().parents[4]

#: Where the lessons are, relative to the top of the repository.
LESSONS = Path("lessons")

#: Where the known good and known bad submissions are.
SUBMISSIONS = Path("tools") / "boss" / "submissions"


class Unknown(Exception):
    """Somebody asked for a fight that does not exist."""


@dataclass(frozen=True)
class Fight:
    """One boss fight, named by the lesson it ends."""

    #: The lesson code in lower case, which is also the submissions directory name.
    code: str
    #: The lesson directory, the full one with the title in it.
    lesson: str
    #: What the reader has to do, in one line, as `boss list` prints it.
    asks: str

    def grader(self, root: Path) -> Path:
        return root / LESSONS / self.lesson / "grade.py"

    def starter(self, root: Path) -> Path:
        return root / LESSONS / self.lesson / "boss" / "starter.py"

    def builder(self, root: Path) -> Path:
        return root / LESSONS / self.lesson / "build.py"

    def submissions(self, root: Path) -> Path:
        return root / SUBMISSIONS / self.code

    def good(self, root: Path) -> Path:
        return self.submissions(root) / "good.py"

    def bad(self, root: Path) -> Path:
        return self.submissions(root) / "bad.py"

    def expected(self, root: Path) -> Path:
        return self.submissions(root) / "expected.txt"

    def wanted(self, root: Path) -> list[str]:
        """The lines the bad submission's report has to contain, one per line of the file.

        Lines rather than the whole text, because the report also prints the function that
        was got wrong, and pinning the exact bytes of that would mean editing this file every
        time somebody reworded a snippet.
        """
        found = self.expected(root).read_text(encoding="utf-8").splitlines()
        return [one for one in found if one.strip()]


FIGHTS: tuple[Fight, ...] = (
    Fight(
        code="t05",
        lesson="t05-the-tree-becomes-bytecode",
        asks="work out a function's local slots from its source, without compiling it",
    ),
)


def find(code: str) -> Fight:
    """The fight with this lesson code, or a message naming the ones there are."""
    for one in FIGHTS:
        if one.code == code.lower():
            return one
    known = ", ".join(one.code for one in FIGHTS)
    raise Unknown(f"there is no {code} fight. There is: {known}")
