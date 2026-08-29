"""The table, the summary line, and the one thing that fails a build."""

from __future__ import annotations

import pytest
from wasmprobe.checks import INFO, TIER0, Check
from wasmprobe.report import (
    BOTH_FINE,
    NEITHER,
    ONLY_BROWSER,
    ONLY_NATIVE,
    differences,
    markdown,
    regressions,
    summary,
    table,
    verdict,
)
from wasmprobe.result import FATAL, OK, RAISED, Outcome, Run


def check(key, weight=TIER0, accepted=""):
    return Check(
        key=key,
        question=f"Does {key} work",
        weight=weight,
        costs="Something.",
        source="result = 1",
        accepted=accepted,
    )


def runs(here, there):
    native = Run("native", "3.15.0", {key: value for key, value in here.items()})
    browser = Run("pyodide", "3.14.2", {key: value for key, value in there.items()}, seconds=1.4)
    return native, browser


@pytest.mark.parametrize(
    ("here", "there", "expected"),
    [
        (OK, OK, BOTH_FINE),
        (OK, FATAL, ONLY_NATIVE),
        (OK, RAISED, ONLY_NATIVE),
        (RAISED, OK, ONLY_BROWSER),
        (RAISED, RAISED, NEITHER),
    ],
)
def test_verdict(here, there, expected):
    assert verdict(Outcome("a", here), Outcome("a", there)) == expected


def test_a_blocking_check_that_broke_in_the_browser_is_a_regression():
    one = check("compiler")
    native, browser = runs(
        {"compiler": Outcome("compiler", OK)},
        {"compiler": Outcome("compiler", FATAL, error="boom")},
    )
    assert regressions(native, browser, [one]) == [one]


def test_an_accepted_gap_is_not_a_regression():
    one = check("optimizer", accepted="We build the list ourselves instead.")
    native, browser = runs(
        {"optimizer": Outcome("optimizer", OK)},
        {"optimizer": Outcome("optimizer", RAISED, error="KeyError")},
    )
    assert regressions(native, browser, [one]) == []


def test_a_nice_to_have_is_not_a_regression():
    one = check("threads", weight=INFO)
    native, browser = runs(
        {"threads": Outcome("threads", OK)}, {"threads": Outcome("threads", RAISED, error="no")}
    )
    assert regressions(native, browser, [one]) == []


def test_broken_in_both_places_is_our_problem_not_a_regression():
    one = check("gone")
    native, browser = runs(
        {"gone": Outcome("gone", RAISED, error="no")}, {"gone": Outcome("gone", RAISED, error="no")}
    )
    assert regressions(native, browser, [one]) == []


def test_a_check_missing_from_one_side_is_skipped():
    one = check("half")
    native, browser = runs({"half": Outcome("half", OK)}, {})
    assert regressions(native, browser, [one]) == []


def test_differences_only_looks_at_checks_that_worked_in_both():
    same = check("same")
    apart = check("apart")
    broken = check("broken")
    native, browser = runs(
        {
            "same": Outcome("same", OK, value=1),
            "apart": Outcome("apart", OK, value=8),
            "broken": Outcome("broken", OK, value=2),
        },
        {
            "same": Outcome("same", OK, value=1),
            "apart": Outcome("apart", OK, value=4),
            "broken": Outcome("broken", FATAL, error="boom"),
        },
    )
    assert differences(native, browser, [same, apart, broken]) == [(apart, 8, 4)]


def test_summary_counts_and_names_the_blocking_ones():
    good = check("good")
    bad = check("bad")
    native, browser = runs(
        {"good": Outcome("good", OK), "bad": Outcome("bad", OK)},
        {"good": Outcome("good", OK), "bad": Outcome("bad", FATAL, error="boom")},
    )
    line = summary(native, browser, [good, bad])
    assert line == f"2 checks: 1 {BOTH_FINE}, 1 {ONLY_NATIVE}, 1 of them blocking."


def test_the_table_has_a_row_for_every_check_and_names_both_pythons():
    one, two = check("one"), check("two")
    native, browser = runs(
        {"one": Outcome("one", OK), "two": Outcome("two", OK)},
        {"one": Outcome("one", OK), "two": Outcome("two", RAISED, error="KeyError: nope")},
    )
    body = table(native, browser, [one, two])
    lines = body.splitlines()
    assert len(lines) == 4
    assert "3.15.0 native" in lines[0]
    assert "3.14.2 WebAssembly" in lines[0]
    assert "raises, KeyError: nope" in lines[3]


def test_the_report_mentions_the_boot_time_and_the_known_gaps():
    one = check("optimizer", accepted="We build the list ourselves instead.")
    native, browser = runs(
        {"optimizer": Outcome("optimizer", OK)},
        {"optimizer": Outcome("optimizer", RAISED, error="KeyError")},
    )
    body = markdown(native, browser, [one])
    assert "booted in 1.4 seconds" in body
    assert "Known gaps" in body
    assert "We build the list ourselves instead." in body
    assert body.endswith("\n")


def test_no_known_gaps_means_no_section():
    one = check("fine")
    native, browser = runs({"fine": Outcome("fine", OK)}, {"fine": Outcome("fine", OK)})
    assert "Known gaps" not in markdown(native, browser, [one])
