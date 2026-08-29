"""The checks that need no Docker, so every pull request can afford them.

These do not ask whether the numbers are right. Nothing here can: the only thing that can
answer that is the debug build, and running it is the job in `run.py`. What these ask is
whether the recording still belongs to the experiment it says it does, whether it was taken
from the image this project currently pins, and whether the lesson it was written for
actually shows it. Every one of those is a way a recording quietly goes stale while all the
green ticks stay green.
"""

from __future__ import annotations

from pathlib import Path

from cpybuild.images import LOCKFILE, Broken, Lock
from refcheck import PINNED_TAG

from .experiments import EXPERIMENTS, Experiment
from .recording import REPOSITORY, Recording, Unreadable

#: Where the lessons are, relative to the top of the repository.
LESSONS = Path("lessons")

#: The page that lists the recordings, which is the first thing anybody opening this
#: directory reads. Checked rather than generated: it is mostly an explanation of why any of
#: this exists, and a generator that reprinted the whole file would take ownership of that.
INDEX = Path("experiments") / "README.md"


def lesson_directory(lesson: str, root: Path) -> Path | None:
    """The directory for a lesson code like T05, found by its prefix.

    By prefix rather than by a table, because the rest of the name is the lesson's title and
    a table of those is a second place to update every time somebody retitles one.
    """
    found = sorted((root / LESSONS).glob(f"{lesson.lower()}-*"))
    return found[0] if found else None


def shown_in_lesson(experiment: Experiment, root: Path) -> list[str]:
    """Whether the lesson this experiment was written for puts it in front of a reader.

    A recording nobody shows is a file that passes every check in this module and teaches
    nobody anything, and it is the state this whole package decays into if left alone.
    """
    where = lesson_directory(experiment.lesson, root)
    if where is None:
        return [f"{experiment.slug}: there is no {experiment.lesson} lesson to show it in"]
    builder = where / "build.py"
    if not builder.is_file():
        return [f"{experiment.slug}: {where} has no build.py"]
    if experiment.slug not in builder.read_text(encoding="utf-8"):
        return [f"{experiment.slug}: {experiment.lesson} does not show it, so nobody reads it"]
    return []


def listed(experiment: Experiment, root: Path) -> list[str]:
    """Whether the index page mentions this experiment at all.

    A recording that is not in the table is one somebody has to already know about to find,
    and the reason for the table is the reader who does not.
    """
    where = root / INDEX
    if not where.is_file():
        return [f"{experiment.slug}: there is no {INDEX} to list it in"]
    body = where.read_text(encoding="utf-8")
    if experiment.slug not in body:
        return [f"{experiment.slug}: {INDEX} does not list it"]
    if experiment.asks not in body:
        return [f"{experiment.slug}: {INDEX} lists it under a different question"]
    return []


def pinned(recording: Recording, lockfile: Path) -> list[str]:
    """Whether the recording came from the image and the interpreter this project pins now.

    Both halves matter and they fail differently. A stale image means the numbers came from
    an interpreter somebody has since replaced. A stale version means the lesson around it
    talks about one Python and the output below it came from another.
    """
    found = []
    version = PINNED_TAG.removeprefix("v")
    if not recording.interpreter.startswith(version):
        found.append(
            f"{recording.slug}: recorded on Python {recording.interpreter.split()[0]} and the "
            f"project is pinned to {version}"
        )
    try:
        wanted = Lock.load(lockfile).reference_index(recording.build)
    except Broken as error:
        return [*found, f"{recording.slug}: {error}"]
    if recording.image != wanted:
        found.append(
            f"{recording.slug}: recorded against {recording.image} and the lockfile now says "
            f"{wanted}, so run `just build-tier1` and read the diff"
        )
    return found


def problems(root: Path | None = None, lockfile: Path | None = None) -> list[str]:
    """Everything wrong across every experiment, in the order somebody would fix it."""
    root = root or REPOSITORY
    lockfile = lockfile or (root / LOCKFILE)
    found: list[str] = []
    for experiment in EXPERIMENTS:
        found.extend(experiment.problems())
        try:
            recording = Recording.load(experiment.slug, root)
        except Unreadable as error:
            found.append(str(error))
            continue
        found.extend(recording.problems(experiment))
        found.extend(pinned(recording, lockfile))
        found.extend(shown_in_lesson(experiment, root))
        found.extend(listed(experiment, root))
    return found
