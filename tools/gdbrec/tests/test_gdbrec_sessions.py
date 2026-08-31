"""The catalogue of sessions, and the things a half written one gets caught on."""

from __future__ import annotations

from dataclasses import replace

import pytest

from gdbrec.sessions import BUILDS, SESSIONS, Session, Step, find

WORKS = Session(
    slug="b99-a-question",
    lesson="B99",
    title="A question",
    asks="Does anything happen?",
    needs="a release build inlines the frame this is about",
    build="debug",
    program="print(1)\n",
    script=(Step("run /tmp/program.py", "Start it."),),
)


def test_every_session_in_the_catalogue_is_complete():
    """The one test here that is about the real sessions rather than about the checks."""
    for one in SESSIONS:
        assert one.problems() == [], one.slug


def test_the_slugs_are_unique():
    """Two sessions with one slug means one transcript, and the second one overwrites it."""
    slugs = [one.slug for one in SESSIONS]
    assert sorted(slugs) == sorted(set(slugs))


def test_a_session_with_nothing_wrong_with_it_has_no_problems():
    assert WORKS.problems() == []


def test_a_slug_that_does_not_start_with_its_lesson_is_caught():
    """The slug is the filename, and a filename that lies about its lesson is unfindable."""
    found = replace(WORKS, slug="t01-a-question").problems()
    assert any("should start with b99" in one for one in found)


def test_a_session_that_does_not_say_why_it_needs_the_debug_build_is_caught():
    """This is the entry fee. Nothing can check the answer, so the check is that it is answered."""
    found = replace(WORKS, needs="  ").problems()
    assert any("needs" in one for one in found)


def test_a_reason_spread_over_two_lines_is_caught():
    """It goes on one line of the transcript header, so a newline would cut it in half."""
    found = replace(WORKS, asks="Does anything\nhappen?").problems()
    assert any("one line" in one for one in found)


def test_a_build_nobody_publishes_is_caught():
    """There is no image to run it in, which is a problem worth hearing before Docker starts."""
    found = replace(WORKS, build="pgo").problems()
    assert any("published builds" in one for one in found)
    assert "pgo" not in BUILDS


def test_a_session_with_no_commands_is_caught():
    found = replace(WORKS, script=()).problems()
    assert any("nothing to record" in one for one in found)


def test_a_command_with_no_explanation_is_caught():
    """Every command gets a line above it in the lesson, and a blank one is a blank page."""
    found = Step("bt", "").problems("b99-a-question")
    assert any("say what" in one for one in found)


def test_two_commands_on_one_step_are_caught():
    """The markers put one block of output under one heading, so two commands lose one block."""
    found = Step("bt\npy-bt", "Both stacks.").problems("b99-a-question")
    assert any("one command" in one for one in found)


def test_find_names_the_sessions_it_knows_about():
    with pytest.raises(KeyError, match="b02-the-two-stacks"):
        find("b02-not-a-session")


def test_find_returns_the_session():
    assert find(SESSIONS[0].slug) is SESSIONS[0]
