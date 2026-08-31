"""The offline checks, and the ways a transcript goes stale while every tick stays green."""

from __future__ import annotations

from pathlib import Path

from cpybuild.images import LOCKFILE, Lock
from gdbrec.checks import (
    INDEX,
    LESSONS,
    lesson_directory,
    listed,
    pinned,
    problems,
    shown_in_lesson,
)
from gdbrec.recording import Printed, Recording
from gdbrec.sessions import Session, Step

DIGEST = "sha256:" + "a" * 64

SESSION = Session(
    slug="b99-a-question",
    lesson="B99",
    title="A question",
    asks="Does anything happen?",
    needs="a release build inlines the frame this is about",
    build="debug",
    program="print(1)\n",
    script=(Step("run /tmp/program.py", "Start it."),),
)


def one(**changed) -> Recording:
    """A transcript of that session with nothing wrong with it."""
    fields = {
        "slug": SESSION.slug,
        "title": SESSION.title,
        "asks": SESSION.asks,
        "needs": SESSION.needs,
        "lesson": SESSION.lesson,
        "build": SESSION.build,
        "arch": "arm64",
        "image": f"{Lock().registry}:debug@{DIGEST}",
        "interpreter": "3.15.0rc1 (main, Jan 1 2026, 00:00:00) [GCC 14.2.0]",
        "debugger": "GNU gdb (Debian 16.3-1) 16.3",
        "recorded": "2026-01-01",
        "program": SESSION.program,
        "steps": [Printed("run /tmp/program.py", "Start it.", ["1"])],
    }
    return Recording(**{**fields, **changed})


def repository(tmp_path: Path, *, shows: str = SESSION.slug, index: bool = True) -> Path:
    """A repository with everything this session needs, which the tests then take apart."""
    where = tmp_path / LESSONS / "b99-a-lesson"
    where.mkdir(parents=True)
    (where / "build.py").write_text(f'lesson.md(gdbrec.show("{shows}", "arm64"))\n')
    if index:
        (tmp_path / INDEX).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / INDEX).write_text(f"| {SESSION.slug} | B99 | debug | {SESSION.asks} |\n")
    one().write(tmp_path)
    return tmp_path


def lockfile(tmp_path: Path, digest: str = DIGEST) -> Path:
    """A lockfile naming one debug image on arm64, written the way the real one is."""
    lock = Lock()
    lock.record("debug", "arm64", digest)
    where = tmp_path / LOCKFILE
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_text(lock.as_json())
    return where


def test_a_lesson_is_found_by_its_prefix(tmp_path):
    """By prefix, so retitling a lesson does not need a table somewhere else updating too."""
    where = repository(tmp_path)
    assert lesson_directory("B99", where) == where / LESSONS / "b99-a-lesson"


def test_a_lesson_that_does_not_exist_yet_is_not_a_crash(tmp_path):
    assert lesson_directory("B99", tmp_path) is None


def test_a_session_shown_in_its_lesson_passes(tmp_path):
    assert shown_in_lesson(SESSION, repository(tmp_path)) == []


def test_a_session_with_no_lesson_to_show_it_in_is_caught(tmp_path):
    assert shown_in_lesson(SESSION, tmp_path) == [
        f"{SESSION.slug}: there is no B99 lesson to show it in"
    ]


def test_a_session_the_lesson_never_shows_is_caught(tmp_path):
    """This one is not a formality. A transcript nobody shows passes every other check here."""
    found = shown_in_lesson(SESSION, repository(tmp_path, shows="b99-something-else"))
    assert any("nobody reads it" in said for said in found)


def test_a_lesson_directory_with_no_builder_is_caught(tmp_path):
    where = repository(tmp_path)
    (where / LESSONS / "b99-a-lesson" / "build.py").unlink()
    assert any("no build.py" in said for said in shown_in_lesson(SESSION, where))


def test_a_session_on_the_index_page_passes(tmp_path):
    assert listed(SESSION, repository(tmp_path)) == []


def test_a_session_missing_from_the_index_is_caught(tmp_path):
    found = listed(SESSION, repository(tmp_path, index=False))
    assert any("to list it in" in said for said in found)


def test_an_index_that_asks_a_different_question_is_caught(tmp_path):
    """The index and the transcript are two copies of one sentence, and two copies drift."""
    where = repository(tmp_path)
    (where / INDEX).write_text(f"| {SESSION.slug} | B99 | debug | Something else entirely? |\n")
    assert any("a different question" in said for said in listed(SESSION, where))


def test_a_transcript_from_the_pinned_image_passes(tmp_path):
    assert pinned(one(), lockfile(tmp_path)) == []


def test_a_transcript_from_an_image_nobody_publishes_any_more_is_caught(tmp_path):
    """The session ran on an interpreter somebody has since replaced, and nothing said so."""
    found = pinned(one(), lockfile(tmp_path, digest="sha256:" + "b" * 64))
    assert any("run `just build-gdb`" in said for said in found)


def test_a_transcript_from_another_python_is_caught(tmp_path):
    """The lesson around it talks about one Python and the backtrace came from another."""
    found = pinned(one(interpreter="3.13.1 (main, Jan 1 2026)"), lockfile(tmp_path))
    assert any("pinned to" in said for said in found)


def test_a_lockfile_with_no_such_image_says_so_rather_than_crashing(tmp_path):
    """The whole point of the digest is that it is missable, so missing it has to be readable."""
    found = pinned(one(build="jit"), lockfile(tmp_path))
    assert any("no jit image" in said for said in found)


def test_a_session_recorded_on_no_architecture_at_all_is_caught(tmp_path):
    assert Recording.recorded_arches(SESSION.slug, tmp_path) == []


def test_the_committed_transcripts_have_no_problems():
    """The one test here that is about what is in the repository rather than about the checks."""
    assert problems() == []
