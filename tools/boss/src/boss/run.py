"""Running a grader against a submission, the same way a reader runs it.

In a subprocess, with a plain interpreter, from the top of the repository. Importing the
grader instead would be faster and would test something else: the reader's first contact with
this is `python grade.py answer.py`, so that is the thing worth knowing still works.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .fights import REPOSITORY, Fight

#: How long a single grading run gets. A grader is a few thousand compiles and finishes in
#: about a second, so a minute means something has hung rather than something is slow.
PATIENCE = 60


@dataclass(frozen=True)
class Ran:
    """What one grading run said and what it exited with."""

    #: The exit code. Zero means the submission passed.
    code: int
    #: Standard output and standard error, joined, because the grader writes the report to
    #: whichever one matches the verdict and a caller checking the report should not care.
    output: str

    @property
    def passed(self) -> bool:
        return self.code == 0

    def says(self, wanted: list[str]) -> list[str]:
        """Which of these lines the report is missing."""
        return [one for one in wanted if one not in self.output]


def graded(
    fight: Fight,
    submission: Path,
    root: Path | None = None,
    seed: int = 0,
    count: int | None = None,
    python: str | None = None,
) -> Ran:
    """Grade one submission and hand back the exit code and the report."""
    root = root or REPOSITORY
    command = [python or sys.executable, str(fight.grader(root)), str(submission)]
    command += ["--seed", str(seed)]
    if count is not None:
        command += ["--count", str(count)]
    done = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=PATIENCE,
        check=False,
    )
    return Ran(code=done.returncode, output=done.stdout + done.stderr)


def verdicts(
    fight: Fight,
    root: Path | None = None,
    seeds: int = 1,
    python: str | None = None,
) -> list[str]:
    """Everything wrong with one fight, found by running it.

    Two questions, and they fail for different reasons. A good submission that stops passing
    means the fight has drifted away from the interpreter underneath it, usually because a new
    Python lays something out in a different order. A bad submission that stops failing, or
    that fails with a different complaint, means the grader has gone soft: it is still saying
    no, but not for the reason the lesson promised it would.
    """
    root = root or REPOSITORY
    found: list[str] = []
    wanted = fight.wanted(root)
    for seed in range(seeds):
        good = graded(fight, fight.good(root), root, seed=seed, python=python)
        if not good.passed:
            found.append(f"{fight.code}: the good submission failed on seed {seed}")
            found.append(f"  {good.output.strip()}")
        bad = graded(fight, fight.bad(root), root, seed=seed, python=python)
        if bad.passed:
            found.append(f"{fight.code}: the bad submission passed on seed {seed}")
            continue
        for missing in bad.says(wanted):
            found.append(
                f"{fight.code}: on seed {seed} the bad submission was turned down without "
                f"the grader saying {missing!r}"
            )
    return found
