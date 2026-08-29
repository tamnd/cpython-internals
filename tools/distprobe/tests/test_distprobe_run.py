"""Building the commands, and the one distinction the report rests on.

Nothing in here starts a container. Pulling five images to prove that a string was
assembled correctly would make the test suite take ten minutes and would fail on a laptop
with no network, which is a bad trade for a test whose subject is a list of arguments. The
container commands are checked as commands. The local ones really run, because they can.
"""

from __future__ import annotations

import base64
import subprocess

from distprobe import run
from distprobe.channels import CONTAINER, LOCAL, RUNNABLE, Channel
from distprobe.question import SOURCE


def channel(kind=CONTAINER, **fields):
    body = dict(key="k", name="A channel", how="type this", kind=kind, where="an:image")
    return Channel(**{**body, **fields})


def test_the_question_reaches_a_container_unmangled():
    """The whole reason for the base64: the source has quotes and newlines in it."""
    command = run.container_command(channel())
    word = next(one for one in command[-1].split() if len(one) > 40)
    assert base64.b64decode(word).decode("utf-8") == SOURCE


def test_a_container_that_needs_a_python_installed_runs_the_setup_first():
    command = run.container_command(channel(setup="apt-get install -y python3"))
    inner = command[-1]
    assert inner.index("apt-get") < inner.index("python3 /question.py")


def test_a_container_that_already_has_a_python_runs_nothing_extra():
    assert " && echo" not in run.container_command(channel(setup="")).pop()


def test_the_architecture_is_pinned_rather_than_left_to_the_daemon():
    command = run.container_command(channel())
    assert command[command.index("--platform") + 1] == run.PLATFORM
    assert run.PLATFORM.startswith("linux/")


def test_a_container_is_cleaned_up_after_itself():
    assert "--rm" in run.container_command(channel())


def test_a_local_channel_with_no_path_asks_this_interpreter():
    command = run.local_command(channel(kind=LOCAL, where=""))
    assert command[1] == "-c"
    assert command[2] == SOURCE


def test_asking_this_interpreter_gets_a_real_answer():
    answer = run.ask(channel(kind=LOCAL, where=""))
    assert answer.has_everything
    assert not answer.unreachable


def test_an_interpreter_that_is_not_installed_is_unreachable_not_a_no():
    answer = run.ask(channel(kind=LOCAL, where="/usr/bin/python-that-is-not-there"))
    assert answer.unreachable
    assert not answer.has_module


def test_docker_missing_says_so_rather_than_looking_like_a_distribution_problem():
    assert run.reachable(channel()) in ("", "docker is not on PATH")


def test_a_command_that_printed_nothing_useful_records_its_last_line(monkeypatch):
    def failed(*args, **kwargs):
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="Unable to find image\n")

    monkeypatch.setattr(run.subprocess, "run", failed)
    assert run.ask(channel()).unreachable == "Unable to find image"


def test_a_command_that_printed_nothing_at_all_still_says_something(monkeypatch):
    def silent(*args, **kwargs):
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="")

    monkeypatch.setattr(run.subprocess, "run", silent)
    assert run.ask(channel()).unreachable == "no output at all"


def test_a_slow_channel_is_given_up_on_rather_than_hanging_the_survey(monkeypatch):
    def slow(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="docker", timeout=5)

    monkeypatch.setattr(run.subprocess, "run", slow)
    assert "gave up" in run.ask(channel(), timeout=5).unreachable


def test_one_broken_channel_does_not_stop_the_others():
    good = channel(key="good", kind=LOCAL, where="")
    bad = channel(key="bad", kind=LOCAL, where="/usr/bin/nope")
    made = run.survey([bad, good])
    assert made.answers["bad"].unreachable
    assert made.answers["good"].has_everything


def test_a_survey_records_what_it_ran_on():
    assert run.survey([]).machine == run.PLATFORM


def test_every_runnable_channel_can_have_a_command_built_for_it():
    """Cheap, and it catches a channel added with the wrong kind or with no image named."""
    for one in RUNNABLE:
        if one.kind == CONTAINER:
            assert one.where, f"{one.key} has no image"
            assert run.container_command(one)[-1].endswith("python3 /question.py")
        else:
            assert run.local_command(one)[-1] == SOURCE
