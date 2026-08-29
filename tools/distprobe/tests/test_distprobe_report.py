"""The table, and the three answers it has to keep apart.

Yes, no, and did not ask are three different things, and a table that folds the third into
the second is the reason somebody would trust it and be wrong. Most of this file is about
that.
"""

from __future__ import annotations

import pytest

from distprobe import report
from distprobe.channels import CONTAINER, ELSEWHERE, Channel
from distprobe.question import WANTED, Answer, Survey


def channel(key, **fields):
    body = dict(key=key, name=key.title(), how=f"install {key}", kind=CONTAINER, where="an:image")
    return Channel(**{**body, **fields})


def answer(**fields):
    body = dict(version="3.14.7", platform="linux-aarch64", internal="ok", names=WANTED)
    return Answer(**{**body, **fields})


def survey(**answers):
    return Survey(machine="linux/arm64", answers=answers)


GOOD = answer()
OLD = answer(version="3.9.6", names=())
GONE = answer(internal="ModuleNotFoundError: No module named '_testinternalcapi'", names=())
AWAY = Answer(unreachable="docker is not on PATH")


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (GOOD, report.FULL),
        (OLD, report.PARTIAL),
        (GONE, report.NONE),
        (AWAY, report.UNKNOWN),
        (None, report.UNKNOWN),
    ],
)
def test_the_four_verdicts(given, expected):
    assert report.verdict(given) == expected


def test_a_channel_nobody_asked_is_not_a_channel_that_said_no():
    """The distinction the table exists to keep, stated as bluntly as it can be."""
    assert report.verdict(AWAY) != report.verdict(GONE)


def test_a_module_with_no_functions_names_the_ones_it_is_missing():
    said = report.cell(OLD)
    for name in WANTED:
        assert name in said


def test_a_missing_module_says_which_exception_and_not_the_whole_message():
    assert report.cell(GONE) == "ModuleNotFoundError"


def test_an_unreachable_channel_says_why_in_its_own_cell():
    assert "docker is not on PATH" in report.cell(AWAY)


def test_the_table_has_a_row_for_every_channel_even_the_unmeasured_ones():
    one, two = channel("debian"), channel("windows", kind=ELSEWHERE)
    body = report.table(survey(debian=GOOD), [one, two])
    lines = body.splitlines()
    assert len(lines) == 4
    assert "Debian" in lines[2]
    assert "Windows" in lines[3]


def test_the_table_says_how_the_python_was_obtained():
    """Somebody looking their own situation up finds the row by the command they typed."""
    assert "`install debian`" in report.table(survey(debian=GOOD), [channel("debian")])


def test_the_summary_counts_every_kind():
    channels = [channel(one) for one in ("a", "b", "c", "d")]
    made = survey(a=GOOD, b=OLD, c=GONE, d=AWAY)
    line = report.summary(made, channels)
    assert line.startswith("4 channels:")
    for name in (report.FULL, report.PARTIAL, report.NONE, report.UNKNOWN):
        assert f"1 {name}" in line


def test_the_summary_leaves_out_a_kind_nothing_landed_in():
    made = survey(a=GOOD)
    assert report.UNKNOWN not in report.summary(made, [channel("a")])


def test_the_problems_are_the_channels_a_reader_would_trip_over():
    channels = [channel(one) for one in ("fine", "old", "gone", "away")]
    made = survey(fine=GOOD, old=OLD, gone=GONE, away=AWAY)
    assert [one.key for one in report.problems(made, channels)] == ["gone", "old"]


def test_a_channel_that_was_not_measured_is_not_counted_as_a_problem():
    """Otherwise the number of problems goes down when somebody uninstalls Docker."""
    assert report.problems(survey(away=AWAY), [channel("away")]) == []


def test_the_report_names_the_problem_channels_and_says_what_to_do():
    channels = [channel("fedora", note="Install python3-test.")]
    body = report.markdown(survey(fedora=GONE), channels)
    assert "Where a reader hits this" in body
    assert "Install python3-test." in body


def test_the_report_says_what_it_could_not_measure_and_how_to_finish_it():
    channels = [channel("windows", kind=ELSEWHERE, note="Needs a Windows machine.")]
    body = report.markdown(survey(), channels)
    assert "Not measured, and what would measure it" in body
    assert "Needs a Windows machine." in body


def test_a_channel_that_docker_could_not_reach_says_that_too():
    channels = [channel("debian", note="Debian stable.")]
    body = report.markdown(survey(debian=AWAY), channels)
    assert "This run could not: docker is not on PATH." in body


def test_a_report_with_nothing_wrong_has_no_problem_section():
    body = report.markdown(survey(fine=GOOD), [channel("fine", note="Fine.")])
    assert "Where a reader hits this" not in body
    assert "Not measured" not in body


def test_every_channel_gets_its_note_printed_exactly_once():
    channels = [channel(one, note=f"Note about {one}.") for one in ("fine", "gone", "away")]
    body = report.markdown(survey(fine=GOOD, gone=GONE, away=AWAY), channels)
    for one in channels:
        assert body.count(one.note) == 1


def test_the_report_says_what_architecture_the_containers_ran_as():
    assert "linux/arm64" in report.markdown(survey(fine=GOOD), [channel("fine")])


def test_the_report_ends_in_exactly_one_newline():
    body = report.markdown(survey(fine=GOOD), [channel("fine")])
    assert body.endswith("\n")
    assert not body.endswith("\n\n")
