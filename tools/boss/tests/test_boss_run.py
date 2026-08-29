"""Running a grader, and deciding what its answer means.

The mechanics are tested against a fake grader, so they stay fast and so a real fight failing
does not also fail the tests for the thing that runs it. The last two tests run the real t05
grader against the real submissions, which is the part that would actually go wrong.
"""

from __future__ import annotations

import pytest

from boss import Ran, find, graded, verdicts
from boss.fights import REPOSITORY, Fight
from boss.run import PATIENCE

#: A grader that agrees with any submission whose text contains the word `right`. Enough of a
#: grader to test the thing that runs graders, and not one line more.
FAKE = """\
import argparse
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("submission", type=Path)
parser.add_argument("--seed", type=int, default=0)
parser.add_argument("--count", type=int, default=40)
args = parser.parse_args()

if "right" in args.submission.read_text():
    print(f"agreed on seed {args.seed}, {args.count} of them")
    sys.exit(0)
print("disagrees with CPython on 'the-first-one'", file=sys.stderr)
print(f"count was {args.count}", file=sys.stderr)
sys.exit(1)
"""

PRETEND = Fight(code="t99", lesson="t99-a-fight", asks="do the thing")


@pytest.fixture
def room(tmp_path):
    """A fake repository with the fake fight in it."""
    lesson = tmp_path / "lessons" / PRETEND.lesson
    lesson.mkdir(parents=True)
    (lesson / "grade.py").write_text(FAKE, encoding="utf-8")
    submissions = tmp_path / "tools" / "boss" / "submissions" / PRETEND.code
    submissions.mkdir(parents=True)
    (submissions / "good.py").write_text("# right\n", encoding="utf-8")
    (submissions / "bad.py").write_text("# wrong\n", encoding="utf-8")
    (submissions / "expected.txt").write_text("disagrees with CPython\n", encoding="utf-8")
    return tmp_path


def test_a_passing_run_is_reported_as_passing(room):
    ran = graded(PRETEND, PRETEND.good(room), room)
    assert ran.passed
    assert "agreed on seed 0" in ran.output


def test_the_seed_reaches_the_grader(room):
    assert "agreed on seed 7" in graded(PRETEND, PRETEND.good(room), room, seed=7).output


def test_the_count_is_left_alone_unless_somebody_asks(room):
    assert "40 of them" in graded(PRETEND, PRETEND.good(room), room).output
    assert "3 of them" in graded(PRETEND, PRETEND.good(room), room, count=3).output


def test_a_report_on_standard_error_is_still_a_report(room):
    ran = graded(PRETEND, PRETEND.bad(room), room)
    assert not ran.passed
    assert "disagrees with CPython" in ran.output


def test_says_reports_only_the_lines_that_are_missing():
    ran = Ran(code=1, output="first line\nthird line\n")
    assert ran.says(["first line", "second line", "third line"]) == ["second line"]


def test_verify_is_happy_when_both_submissions_behave(room):
    assert verdicts(PRETEND, room, seeds=3) == []


def test_verify_complains_when_the_good_submission_stops_passing(room):
    PRETEND.good(room).write_text("# wrong now\n", encoding="utf-8")
    found = verdicts(PRETEND, room)
    assert "the good submission failed on seed 0" in found[0]


def test_verify_complains_when_the_bad_submission_stops_failing(room):
    PRETEND.bad(room).write_text("# right after all\n", encoding="utf-8")
    assert verdicts(PRETEND, room) == ["t99: the bad submission passed on seed 0"]


def test_verify_complains_when_the_grader_stops_saying_why(room):
    PRETEND.expected(room).write_text("a sentence nobody prints\n", encoding="utf-8")
    found = verdicts(PRETEND, room)
    assert len(found) == 1
    assert "without the grader saying 'a sentence nobody prints'" in found[0]


def test_every_seed_is_graded(room):
    PRETEND.expected(room).write_text("count was 40\n", encoding="utf-8")
    PRETEND.bad(room).write_text("# wrong\n", encoding="utf-8")
    assert verdicts(PRETEND, room, seeds=4) == []


def test_a_grader_that_hangs_is_given_a_minute_and_not_forever():
    assert PATIENCE <= 60


def test_the_real_good_submission_passes_the_real_grader():
    fight = find("t05")
    ran = graded(fight, fight.good(REPOSITORY))
    assert ran.passed, ran.output


def test_the_real_bad_submission_is_turned_down_with_the_promised_message():
    fight = find("t05")
    ran = graded(fight, fight.bad(REPOSITORY))
    assert not ran.passed
    assert ran.says(fight.wanted(REPOSITORY)) == []
