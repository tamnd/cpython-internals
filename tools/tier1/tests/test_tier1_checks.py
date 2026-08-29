"""The checks that run without Docker, and the state of the recordings actually committed."""

from __future__ import annotations

import json

import pytest

from cpybuild.images import Lock
from refcheck import PINNED_TAG
from tier1.checks import LESSONS, lesson_directory, pinned, problems, shown_in_lesson
from tier1.experiments import EXPERIMENTS
from tier1.recording import REPOSITORY, Recording

IMAGE = "ghcr.io/tamnd/cpython-internals/cpython:debug@sha256:" + "a" * 64


def lockfile(tmp_path, image: str = IMAGE):
    """A lockfile naming one joined debug image, which is all these checks read out of it."""
    lock = Lock()
    lock.record_index("debug", image.rpartition("@")[2])
    where = tmp_path / "cpython.lock.json"
    where.write_text(json.dumps(json.loads(lock.as_json())), encoding="utf-8")
    return where


def recording(**changed) -> Recording:
    fields = {
        "slug": "t99-a-question",
        "title": "A question",
        "asks": "Does anything happen?",
        "needs": "it needs a build nobody has",
        "lesson": "T99",
        "build": "debug",
        "image": IMAGE,
        "interpreter": PINNED_TAG.removeprefix("v") + " (main, Jan 1 2026, 00:00:00)",
        "recorded": "2026-01-01",
        "program": 'print("~ a measurement: 1")\n',
        "output": ["~ a measurement: 1"],
    }
    return Recording(**{**fields, **changed})


def test_nothing_is_wrong_with_the_recordings_this_repository_committed():
    """The one that matters. Everything else here describes a way this can go wrong."""
    assert problems(REPOSITORY) == []


@pytest.mark.parametrize("experiment", EXPERIMENTS, ids=lambda one: one.slug)
def test_every_experiment_has_a_recording_that_was_really_taken(experiment):
    """A recording is a run that happened, so it names an image and prints something."""
    one = Recording.load(experiment.slug, REPOSITORY)
    assert one.image.startswith("ghcr.io/") and "@sha256:" in one.image
    assert one.output


def test_a_lesson_directory_is_found_by_its_code():
    found = lesson_directory("T05", REPOSITORY)
    assert found is not None and found.name.startswith("t05-")


def test_a_lesson_that_does_not_exist_is_reported_rather_than_guessed(tmp_path):
    (tmp_path / LESSONS).mkdir(parents=True)
    found = shown_in_lesson(EXPERIMENTS[0], tmp_path)
    assert len(found) == 1 and "there is no" in found[0]


def test_a_recording_no_lesson_shows_is_a_problem(tmp_path):
    """It would pass every other check here and teach nobody anything."""
    where = tmp_path / LESSONS / "t05-the-tree-becomes-bytecode"
    where.mkdir(parents=True)
    (where / "build.py").write_text("lesson.md('nothing about it')\n", encoding="utf-8")
    found = shown_in_lesson(EXPERIMENTS[0], tmp_path)
    assert len(found) == 1 and "does not show it" in found[0]


def test_a_recording_taken_from_an_image_the_lockfile_no_longer_names_is_a_problem(tmp_path):
    found = pinned(recording(), lockfile(tmp_path, IMAGE.replace("a" * 64, "b" * 64)))
    assert len(found) == 1 and "build-tier1" in found[0]


def test_a_recording_taken_on_another_python_is_a_problem(tmp_path):
    found = pinned(recording(interpreter="3.14.7 (main, Jan 1 2026, 00:00:00)"), lockfile(tmp_path))
    assert len(found) == 1 and "3.14.7" in found[0]


def test_a_recording_on_the_pinned_python_and_the_locked_image_is_fine(tmp_path):
    assert pinned(recording(), lockfile(tmp_path)) == []
