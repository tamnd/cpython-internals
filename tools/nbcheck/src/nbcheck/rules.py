"""What a lesson notebook has to look like before anyone is asked to read it.

These are not style preferences. Each one is a way a reader has actually been lost, and
the check exists so that the author finds out instead of the reader.

The rules are deliberately blunt and easy to read. A contributor who trips one should be
able to see why from the message alone, without opening this file.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .notebook import Cell, Notebook

#: The repository the Colab badge has to point at. A badge that opens somebody else's
#: notebook is worse than no badge, because the reader does not notice.
REPOSITORY = "tamnd/cpython-internals"
BADGE_HOST = "colab.research.google.com/github"

#: Punctuation the project does not use in prose. Cheap to check and impossible to see in
#: a diff, which is exactly the combination that makes it worth automating. The characters
#: are written as escapes because the linter flags the literals as ambiguous, which is a
#: fair complaint everywhere except in the one dictionary whose job is to name them.
FORBIDDEN_CHARACTERS = {
    "\u2014": "em dash",
    "\u2013": "en dash",
}


@dataclass(frozen=True)
class Problem:
    """One thing wrong with one notebook, said in a way an author can act on."""

    path: Path
    cell: int | None
    rule: str
    message: str

    def __str__(self) -> str:
        where = f"{self.path}" if self.cell is None else f"{self.path}:cell {self.cell}"
        return f"{where}: {self.message} [{self.rule}]"


def _badge_target(path: Path, root: Path) -> str:
    """The badge URL this notebook, at this path, ought to carry.

    Both sides are resolved before they are compared. The notebook paths come from walking
    a directory and are usually relative, the root comes from a command line flag and is
    usually absolute, and subtracting one from the other without resolving both raises for
    a reason that has nothing to do with the notebook.
    """
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        relative = path
    return f"{BADGE_HOST}/{REPOSITORY}/blob/main/{relative.as_posix()}"


def check_badge(book: Notebook, root: Path) -> list[Problem]:
    """The first cell opens the notebook in Colab, and opens this one rather than another.

    A reader who lands on a notebook in GitHub's viewer has no way to run it. The badge is
    the whole browser tier promise for anyone not using marimo, so it is the first thing
    in the file and it is checked, because a copied badge pointing at the previous lesson
    is the single easiest mistake to make here.
    """
    if not book.cells:
        return [Problem(book.path, None, "badge", "the notebook has no cells")]
    first = book.cells[0]
    if not first.is_markdown:
        message = "the first cell must be markdown with the Colab badge"
        return [Problem(book.path, 1, "badge", message)]
    expected = _badge_target(book.path, root)
    if BADGE_HOST not in first.source:
        return [Problem(book.path, 1, "badge", "the first cell has no Colab badge")]
    if expected not in first.source:
        return [
            Problem(
                book.path,
                1,
                "badge",
                f"the Colab badge does not point at this notebook, expected {expected}",
            )
        ]
    return []


def check_setup_cell(book: Notebook) -> list[Problem]:
    """The reader can run the notebook in Colab without being told to install anything.

    Colab has no pyxray. If the install is not in the notebook then the second cell raises
    ImportError, and a beginner reads that as the lesson being broken rather than as a
    missing dependency.
    """
    for cell in book.code_cells:
        if "pip install" in cell.source:
            if REPOSITORY not in cell.source:
                return [
                    Problem(
                        book.path,
                        cell.number,
                        "setup",
                        f"the install cell does not install from {REPOSITORY}",
                    )
                ]
            return []
    return [Problem(book.path, None, "setup", "no cell installs pyxray, so Colab cannot run this")]


def check_banner_cell(book: Notebook) -> list[Problem]:
    """The reader is told which interpreter produced everything below, before it does.

    Every observation in this material is build dependent. A reader who does not know
    which binary is executing the cell will eventually see a result that contradicts the
    prose and conclude the prose is wrong.
    """
    code = book.code_cells
    if not code:
        return [Problem(book.path, None, "banner", "the notebook has no code cells")]
    for cell in code[:3]:
        if "pyxray.show()" in cell.source:
            return []
    return [
        Problem(
            book.path,
            code[0].number,
            "banner",
            "no pyxray.show() in the first three code cells, so the reader is not told "
            "which interpreter they are on",
        )
    ]


def check_every_code_cell_is_introduced(book: Notebook) -> list[Problem]:
    """No code appears without a sentence saying what it is about to show.

    This is the rule that separates a lesson from a script with comments in it. A beginner
    reading a cell they were not prepared for has to reverse engineer the intent from the
    output, and that is where they stop.
    """
    problems = []
    previous: Cell | None = None
    for cell in book.cells:
        wanted = cell.is_code and not cell.is_empty
        if wanted and (previous is None or not previous.is_markdown):
            problems.append(
                Problem(
                    book.path,
                    cell.number,
                    "introduced",
                    "this code cell is not preceded by a markdown cell explaining it",
                )
            )
        previous = cell
    return problems


def check_no_empty_cells(book: Notebook) -> list[Problem]:
    return [
        Problem(book.path, cell.number, "empty", "this cell is empty")
        for cell in book.cells
        if cell.is_empty
    ]


def check_no_stored_outputs(book: Notebook) -> list[Problem]:
    """Outputs are not committed, so the only proof a cell works is CI running it.

    Committed outputs go stale silently. A reader sees a number from a build that no
    longer exists and has no way to tell. Stripping them also makes review diffs readable,
    which matters when the prose and the code live in the same file.
    """
    problems = []
    for cell in book.code_cells:
        if cell.outputs:
            problems.append(
                Problem(book.path, cell.number, "outputs", "this cell has stored output, strip it")
            )
        elif cell.execution_count is not None:
            problems.append(
                Problem(
                    book.path,
                    cell.number,
                    "outputs",
                    "this cell has an execution count, strip it",
                )
            )
    return problems


def check_prose_punctuation(book: Notebook) -> list[Problem]:
    problems = []
    for cell in book.markdown_cells:
        for character, name in FORBIDDEN_CHARACTERS.items():
            if character in cell.source:
                problems.append(
                    Problem(
                        book.path,
                        cell.number,
                        "punctuation",
                        f"contains {name}, which this project does not use in prose",
                    )
                )
    return problems


def check_cell_ids(book: Notebook) -> list[Problem]:
    """Every cell carries an id, because nbformat 4.5 made them part of the format.

    A notebook without them still opens, so the mistake survives review, and then nbformat
    warns while validating it. This project turns warnings into errors, so what should have
    been a cosmetic omission fails the execution job instead, several minutes later and
    with a message about validation rather than about the missing field.
    """
    problems = []
    seen: dict[str, int] = {}
    for cell in book.cells:
        if not cell.identifier:
            problems.append(Problem(book.path, cell.number, "id", "this cell has no id"))
            continue
        if cell.identifier in seen:
            problems.append(
                Problem(
                    book.path,
                    cell.number,
                    "id",
                    f"id {cell.identifier!r} is already used by cell {seen[cell.identifier]}",
                )
            )
        seen.setdefault(cell.identifier, cell.number)
    return problems


def check_kernel(book: Notebook) -> list[Problem]:
    """The kernel is a plain python3, because that is the only one Colab offers."""
    name = book.metadata.get("kernelspec", {}).get("name")
    if name != "python3":
        return [
            Problem(
                book.path,
                None,
                "kernel",
                f"kernelspec is {name!r}, but Colab only offers python3",
            )
        ]
    return []


def check(book: Notebook, root: Path) -> list[Problem]:
    """Every rule, in the order an author would want to hear about them."""
    problems: list[Problem] = []
    problems.extend(check_badge(book, root))
    problems.extend(check_setup_cell(book))
    problems.extend(check_banner_cell(book))
    problems.extend(check_kernel(book))
    problems.extend(check_cell_ids(book))
    problems.extend(check_every_code_cell_is_introduced(book))
    problems.extend(check_no_empty_cells(book))
    problems.extend(check_no_stored_outputs(book))
    problems.extend(check_prose_punctuation(book))
    return problems
