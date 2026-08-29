"""The question, and reading an answer back out of whatever a container printed around it."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from distprobe.question import MARKER, SOURCE, WANTED, Answer, Survey, Unreadable, parse


def line(**fields) -> str:
    body = {"version": "3.14.7", "platform": "linux-aarch64", "internal": "ok", "names": []}
    return MARKER + json.dumps({**body, **fields})


def test_the_question_runs_on_this_interpreter_and_prints_one_answer():
    """Not a mock. The source that gets shipped is run, because that is the thing that breaks."""
    finished = subprocess.run(
        [sys.executable, "-c", SOURCE], capture_output=True, text=True, check=True
    )
    marked = [one for one in finished.stdout.splitlines() if one.startswith(MARKER)]
    assert len(marked) == 1


def test_this_interpreter_has_the_module_and_all_three_functions():
    """The pinned build. If this fails, the pin moved and the lessons need looking at."""
    finished = subprocess.run(
        [sys.executable, "-c", SOURCE], capture_output=True, text=True, check=True
    )
    answer = parse(finished.stdout)
    assert answer.has_everything
    assert answer.missing == ()


def test_the_question_imports_nothing_that_a_stripped_python_might_not_have():
    """It runs where the answer is no, so it cannot depend on the thing it is asking about."""
    for name in ("_testinternalcapi", "_testcapi"):
        assert f"import {name}\n" in SOURCE
        assert SOURCE.count(f"import {name}") == 1
    for name in ("import json", "import sys", "import sysconfig"):
        assert name in SOURCE


def test_apt_noise_before_the_answer_is_ignored():
    output = "Get:1 http://deb.debian.org trixie InRelease\nSetting up python3\n" + line()
    assert parse(output).has_module


def test_the_last_answer_wins_when_a_command_answered_twice():
    output = line(version="3.9.6") + "\n" + line(version="3.14.7")
    assert parse(output).version == "3.14.7"


def test_output_with_no_answer_in_it_is_an_error_and_not_a_no():
    with pytest.raises(Unreadable):
        parse("E: Unable to locate package python3\n")


def test_a_module_with_none_of_the_functions_is_not_a_module_that_works():
    answer = parse(line(names=[]))
    assert answer.has_module
    assert not answer.has_everything
    assert answer.missing == WANTED


def test_a_module_with_two_of_three_names_the_one_that_is_missing():
    answer = parse(line(names=["compiler_codegen", "optimize_cfg"]))
    assert answer.missing == ("assemble_code_object",)


def test_an_import_error_is_carried_through_with_its_message():
    answer = parse(line(internal="ModuleNotFoundError: No module named '_testinternalcapi'"))
    assert not answer.has_module
    assert "_testinternalcapi" in answer.internal


def test_a_channel_that_could_not_be_reached_is_not_a_channel_that_said_no():
    """The distinction the whole report rests on, so it is checked at the bottom too."""
    answer = Answer(unreachable="docker is not on PATH")
    assert not answer.has_module
    assert answer.unreachable


def test_an_answer_survives_a_round_trip_through_json():
    answer = parse(line(names=list(WANTED), testcapi="ok"))
    assert Answer.from_dict(answer.as_dict()) == answer


def test_a_survey_survives_a_round_trip_through_json():
    made = Survey(machine="linux/arm64", answers={"uv": parse(line(names=list(WANTED)))})
    assert Survey.from_json(made.as_json()) == made


def test_a_survey_written_out_ends_in_a_newline():
    """It gets committed, and a file without one shows up as a diff in every editor."""
    assert Survey(machine="linux/arm64").as_json().endswith("\n")
