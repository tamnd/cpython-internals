"""Running the checks here, which is also the control the browser run is compared against."""

from __future__ import annotations

import pytest
from wasmprobe.checks import CHECKS, INFO, Check
from wasmprobe.native import one, run
from wasmprobe.result import OK, RAISED

BOOM = Check(
    key="boom",
    question="What does a check that throws look like",
    weight=INFO,
    costs="Nothing. It is here for the tests.",
    source="raise ValueError('no')",
)

QUIET = Check(
    key="quiet",
    question="What does a check that answers nothing look like",
    weight=INFO,
    costs="Nothing. It is here for the tests.",
    source="pass",
)


def test_a_check_that_works():
    outcome = one(CHECKS[0])
    assert outcome.status == OK
    assert outcome.worked
    assert outcome.value["python"]


def test_a_check_that_throws_is_recorded_rather_than_raised():
    outcome = one(BOOM)
    assert outcome.status == RAISED
    assert not outcome.worked
    assert outcome.error == "ValueError: no"


def test_a_check_that_never_sets_result():
    outcome = one(QUIET)
    assert outcome.status == OK
    assert outcome.value is None


def test_every_check_works_on_this_interpreter():
    """The native side is the control, so a failure here is our bug rather than a finding."""
    finished = run()
    broken = {key: value.error for key, value in finished.outcomes.items() if not value.worked}
    assert not broken


@pytest.mark.parametrize("check", CHECKS, ids=lambda check: check.key)
def test_answers_survive_json(check: Check):
    """Whatever a check returns has to fit through the pipe from the Node driver."""
    import json

    json.dumps(one(check).value)


def test_run_reports_this_interpreter():
    finished = run([CHECKS[0]])
    assert finished.runtime == "native"
    assert finished.python.count(".") == 2
    assert list(finished.outcomes) == [CHECKS[0].key]
