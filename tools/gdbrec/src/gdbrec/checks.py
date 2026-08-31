"""The checks that need no Docker, so every pull request can afford them.

None of these ask whether the transcript is right. Nothing offline can: the only thing that
can answer that is gdb inside the debug image, which is `run.py`. What these ask is whether
the transcript still belongs to the session above it, whether it came from the image this
project pins today, and whether the lesson it was written for actually shows it. Each of
those is a way a transcript goes quietly stale while every green tick stays green.
"""

from __future__ import annotations

from pathlib import Path

from cpybuild.images import LOCKFILE, Broken, Lock
from refcheck import PINNED_TAG

from .recording import REPOSITORY, Recording, Unreadable
from .sessions import SESSIONS, Session

#: Where the lessons are, relative to the top of the repository.
LESSONS = Path("lessons")

#: The page that lists the transcripts and explains why recording them is worth the trouble.
#: Checked rather than generated, for the same reason `experiments/README.md` is.
INDEX = Path("debugger") / "README.md"


def lesson_directory(lesson: str, root: Path) -> Path | None:
    """The directory for a lesson code like B02, found by its prefix.

    By prefix rather than by a table, because the rest of the name is the lesson's title and
    a table of those is a second place to update every time somebody retitles one.
    """
    found = sorted((root / LESSONS).glob(f"{lesson.lower()}-*"))
    return found[0] if found else None


def shown_in_lesson(session: Session, root: Path) -> list[str]:
    """Whether the lesson this session was written for puts it in front of a reader.

    A transcript nobody shows passes every other check in this module and teaches nobody
    anything, and it is what this directory decays into if left alone.
    """
    where = lesson_directory(session.lesson, root)
    if where is None:
        return [f"{session.slug}: there is no {session.lesson} lesson to show it in"]
    builder = where / "build.py"
    if not builder.is_file():
        return [f"{session.slug}: {where} has no build.py"]
    if session.slug not in builder.read_text(encoding="utf-8"):
        return [f"{session.slug}: {session.lesson} does not show it, so nobody reads it"]
    return []


def listed(session: Session, root: Path) -> list[str]:
    """Whether the index page mentions this session at all."""
    where = root / INDEX
    if not where.is_file():
        return [f"{session.slug}: there is no {INDEX} to list it in"]
    body = where.read_text(encoding="utf-8")
    if session.slug not in body:
        return [f"{session.slug}: {INDEX} does not list it"]
    if session.asks not in body:
        return [f"{session.slug}: {INDEX} lists it under a different question"]
    return []


def pinned(recording: Recording, lockfile: Path) -> list[str]:
    """Whether the transcript came from the image and the interpreter this project pins now.

    Both halves matter and they fail differently. A stale image means the session ran on an
    interpreter somebody has since replaced. A stale version means the lesson around it talks
    about one Python and the backtrace under it came from another.
    """
    found = []
    version = PINNED_TAG.removeprefix("v")
    if not recording.interpreter.startswith(version):
        found.append(
            f"{recording.slug}: recorded on Python {recording.interpreter.split()[0]} and the "
            f"project is pinned to {version}"
        )
    try:
        wanted = Lock.load(lockfile).reference(recording.build, recording.arch)
    except Broken as error:
        return [*found, f"{recording.slug}: {error}"]
    if recording.image != wanted:
        found.append(
            f"{recording.slug}: recorded against {recording.image} and the lockfile now says "
            f"{wanted}, so run `just build-gdb` on {recording.arch} and read the diff"
        )
    return found


def problems(root: Path | None = None, lockfile: Path | None = None) -> list[str]:
    """Everything wrong across every session, in the order somebody would fix it."""
    root = root or REPOSITORY
    lockfile = lockfile or (root / LOCKFILE)
    found: list[str] = []
    for session in SESSIONS:
        found.extend(session.problems())
        arches = Recording.recorded_arches(session.slug, root)
        if not arches:
            found.append(f"{session.slug}: nothing recorded on any architecture yet")
            continue
        for arch in arches:
            try:
                recording = Recording.load(session.slug, arch, root)
            except Unreadable as error:
                found.append(str(error))
                continue
            found.extend(recording.problems(session))
            found.extend(pinned(recording, lockfile))
        found.extend(shown_in_lesson(session, root))
        found.extend(listed(session, root))
    return found
