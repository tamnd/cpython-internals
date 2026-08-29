"""The checks that do not have to run anything, so they can be instant and always on.

These do not ask whether a submission passes. Only the grader can answer that, and running it
is `run.py`. What these ask is whether the fight is still assembled: the four files present,
the grader still runnable by somebody with nothing installed, the starter still a file you can
fill in rather than one that already parses as an answer, and the lesson still pointing at any
of it. Every one of those is a way a fight rots while all the ticks stay green.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from .fights import FIGHTS, REPOSITORY, Fight

#: What the reader has to write, and what the grader looks for.
ENTRY = "predict"


def imports(source: str) -> list[str]:
    """The top level name of every module a file imports."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found += [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append(node.module.split(".")[0])
    return found


def stdlib_only(where: Path, root: Path) -> list[str]:
    """Whether a file could run on a Python nobody has installed anything into.

    The whole promise of a boss fight is `python grade.py answer.py` on the machine the reader
    already has. One `import numpy` in the grader turns that into an afternoon of setup, and
    it would be an easy one to add without noticing, because everything in this repository is
    developed inside an environment where the import works.
    """
    outside = [one for one in imports(where.read_text(encoding="utf-8")) if one not in STDLIB]
    if not outside:
        return []
    named = ", ".join(sorted(set(outside)))
    return [f"{where.relative_to(root)} imports {named}, which a reader may not have"]


#: Everything a reader is guaranteed to have. `sys.stdlib_module_names` includes the private
#: ones, which is right here: a grader importing `_ast` is still a grader that runs anywhere.
STDLIB = sys.stdlib_module_names


def defines(where: Path, name: str) -> bool:
    """Whether a file defines a function with this name at the top level."""
    tree = ast.parse(where.read_text(encoding="utf-8"))
    return any(
        isinstance(one, ast.FunctionDef | ast.AsyncFunctionDef) and one.name == name
        for one in tree.body
    )


def present(fight: Fight, root: Path) -> list[str]:
    """Whether the four files a fight is made of are all there."""
    wanted = {
        "grader": fight.grader(root),
        "starter": fight.starter(root),
        "good submission": fight.good(root),
        "bad submission": fight.bad(root),
        "expected report": fight.expected(root),
    }
    return [
        f"{fight.code}: the {what} is missing, expected at {where.relative_to(root)}"
        for what, where in wanted.items()
        if not where.is_file()
    ]


def shaped(fight: Fight, root: Path) -> list[str]:
    """Whether the three Python files still hold up their end of the contract."""
    found: list[str] = []
    for what, where in (
        ("starter", fight.starter(root)),
        ("good submission", fight.good(root)),
        ("bad submission", fight.bad(root)),
    ):
        if not defines(where, ENTRY):
            found.append(f"{fight.code}: the {what} does not define {ENTRY}()")
    if fight.good(root).read_text() == fight.bad(root).read_text():
        found.append(f"{fight.code}: the good and bad submissions are the same file")
    if not fight.wanted(root):
        found.append(
            f"{fight.code}: expected.txt is empty, so the bad submission would pass this "
            f"check by being turned down for any reason at all"
        )
    return found


def told(fight: Fight, root: Path) -> list[str]:
    """Whether the lesson sends anybody to the fight.

    A fight nobody is pointed at is a directory that passes every check in this module and is
    read by nobody, which is the state this decays into if left alone.
    """
    builder = fight.builder(root)
    if not builder.is_file():
        return [f"{fight.code}: there is no {builder.relative_to(root)} to send anybody there"]
    body = builder.read_text(encoding="utf-8")
    if "grade.py" not in body:
        return [f"{fight.code}: {builder.relative_to(root)} never mentions grade.py"]
    return []


def problems(root: Path | None = None) -> list[str]:
    """Everything wrong across every fight, in the order somebody would fix it."""
    root = root or REPOSITORY
    found: list[str] = []
    for fight in FIGHTS:
        missing = present(fight, root)
        found += missing
        if missing:
            # The rest of the checks read these files. Reporting that a file is missing and
            # then crashing on it reads like the tool is broken rather than the fight.
            continue
        found += shaped(fight, root)
        found += stdlib_only(fight.grader(root), root)
        found += stdlib_only(fight.starter(root), root)
        found += told(fight, root)
    return found
