"""The command line, driven the way `just` drives it.

Nothing here pulls an image. `survey` is stubbed at the two functions that touch the
outside world, because what is being tested is that the subcommand writes the file and
prints the line, not that Docker works.
"""

from __future__ import annotations

import pytest

from distprobe import borrowed, report, run
from distprobe.channels import CONTAINER, ELSEWHERE, Channel
from distprobe.cli import ANSWERS, REPORT, main
from distprobe.question import WANTED, Answer, Survey

FEDORA = Channel(
    key="fedora",
    name="Fedora",
    how="dnf install python3",
    kind=CONTAINER,
    where="fedora:43",
    setup="dnf install -y python3",
    note="Ships the module in a separate package.",
)
WINDOWS = Channel(
    key="windows",
    name="python.org Windows",
    how="the installer from python.org",
    kind=ELSEWHERE,
    note="Needs a Windows machine, which this one is not.",
)
GOOD = Answer(internal="ok", version="3.14.7", platform="linux-aarch64", names=WANTED)
GONE = Answer(internal="ModuleNotFoundError: no module", version="3.14.7")


@pytest.fixture
def two(monkeypatch):
    """Cut the channel list down to two, so the fixtures below are the whole world."""
    wanted = [FEDORA, WINDOWS]
    monkeypatch.setattr(report, "CHANNELS", wanted)
    return wanted


def recording(room, answer=GOOD):
    made = Survey(machine="linux/arm64", answers={"fedora": answer})
    (room / ANSWERS).write_text(made.as_json(), encoding="utf-8")
    return made


def test_list_prints_every_channel_and_whether_it_runs_here(capsys):
    assert main(["list"]) == 0
    printed = capsys.readouterr().out
    assert "fedora" in printed
    assert "elsewhere" in printed
    assert printed.count("\n") >= 10


def test_the_question_can_be_printed_for_somebody_to_paste_elsewhere(capsys):
    """The two channels this machine cannot reach get answered by a person, not by us."""
    assert main(["question"]) == 0
    printed = capsys.readouterr().out
    assert "_testinternalcapi" in printed
    assert "DISTPROBE" in printed


def test_survey_writes_the_recording_and_says_what_it_found(tmp_path, capsys, monkeypatch, two):
    monkeypatch.setattr(run, "survey", lambda: Survey(machine="linux/arm64", answers={}))
    monkeypatch.setattr(borrowed, "from_wasmprobe", lambda: GOOD)
    assert main(["survey", "--into", str(tmp_path)]) == 0
    assert (tmp_path / ANSWERS).exists()
    assert "2 channels" in capsys.readouterr().out


def test_survey_takes_the_browser_row_from_the_other_probe(tmp_path, monkeypatch, two):
    """Copied rather than measured twice, so the two probes cannot disagree."""
    monkeypatch.setattr(run, "survey", lambda: Survey(machine="linux/arm64", answers={}))
    monkeypatch.setattr(borrowed, "from_wasmprobe", lambda: GOOD)
    main(["survey", "--into", str(tmp_path)])
    written = Survey.from_json((tmp_path / ANSWERS).read_text(encoding="utf-8"))
    assert written.answers["pyodide"] == GOOD


def test_survey_makes_the_directory_it_was_pointed_at(tmp_path, monkeypatch, two):
    monkeypatch.setattr(run, "survey", lambda: Survey(machine="linux/arm64", answers={}))
    monkeypatch.setattr(borrowed, "from_wasmprobe", lambda: GOOD)
    room = tmp_path / "deep" / "down"
    assert main(["survey", "--into", str(room)]) == 0
    assert (room / ANSWERS).exists()


def test_survey_can_redo_one_channel_without_touching_the_others(tmp_path, monkeypatch, two):
    """One Fedora row timed out, and redoing all twelve to fix it costs half an hour."""
    (tmp_path / ANSWERS).write_text(
        Survey(machine="linux/arm64", answers={"fedora": GONE, "uv": GOOD}).as_json(),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        run, "survey", lambda wanted: Survey(machine="linux/arm64", answers={"fedora": GOOD})
    )
    assert main(["survey", "--into", str(tmp_path), "--only", "fedora"]) == 0
    written = Survey.from_json((tmp_path / ANSWERS).read_text(encoding="utf-8"))
    assert written.answers["fedora"] == GOOD
    assert written.answers["uv"] == GOOD


def test_redoing_one_channel_asks_only_that_channel(tmp_path, monkeypatch, two):
    asked = []

    def watch(wanted):
        asked.extend(one.key for one in wanted)
        return Survey(machine="linux/arm64", answers={})

    monkeypatch.setattr(run, "survey", watch)
    main(["survey", "--into", str(tmp_path), "--only", "fedora"])
    assert asked == ["fedora"]


def test_redoing_one_channel_does_not_go_back_to_the_browser_recording(tmp_path, monkeypatch, two):
    """`--only` is for a container row. Reaching for wasmprobe here would be surprising."""

    def refuse():
        raise AssertionError("the browser recording should not have been read")

    monkeypatch.setattr(borrowed, "from_wasmprobe", refuse)
    monkeypatch.setattr(
        run, "survey", lambda wanted: Survey(machine="linux/arm64", answers={"fedora": GOOD})
    )
    assert main(["survey", "--into", str(tmp_path), "--only", "fedora"]) == 0


def test_a_channel_that_cannot_be_asked_from_here_is_refused_rather_than_hung_on(tmp_path, capsys):
    """Pyodide is answered elsewhere, so asking for it is a typo and should say so at once."""
    with pytest.raises(SystemExit):
        main(["survey", "--into", str(tmp_path), "--only", "pyodide"])
    assert "invalid choice" in capsys.readouterr().err


def test_report_without_a_destination_prints(tmp_path, capsys, two):
    recording(tmp_path)
    assert main(["report", str(tmp_path)]) == 0
    assert "# Does `_testinternalcapi` ship" in capsys.readouterr().out


def test_report_into_a_file(tmp_path, two):
    recording(tmp_path)
    destination = tmp_path / "deep" / "report.md"
    assert main(["report", str(tmp_path), "--into", str(destination)]) == 0
    assert "Fedora" in destination.read_text(encoding="utf-8")


def test_check_passes_when_the_report_matches_the_recording(tmp_path, capsys, two):
    made = recording(tmp_path)
    (tmp_path / REPORT).write_text(report.markdown(made), encoding="utf-8")
    assert main(["check", str(tmp_path)]) == 0
    assert "2 channels" in capsys.readouterr().out


def test_check_fails_when_the_report_has_fallen_behind(tmp_path, capsys, two):
    recording(tmp_path)
    assert main(["check", str(tmp_path)]) == 1
    assert "out of date: report.md" in capsys.readouterr().err


def test_check_does_not_fail_because_a_distribution_said_no(tmp_path, capsys, two):
    """A red build every time somebody runs it would not change how Fedora packages Python."""
    made = recording(tmp_path, answer=GONE)
    (tmp_path / REPORT).write_text(report.markdown(made), encoding="utf-8")
    assert main(["check", str(tmp_path)]) == 0
    assert "Fedora: ModuleNotFoundError" in capsys.readouterr().out


def test_a_missing_recording_says_which_file_and_what_to_run(tmp_path):
    with pytest.raises(SystemExit) as stopped:
        main(["check", str(tmp_path)])
    assert ANSWERS in str(stopped.value)
    assert "distprobe survey" in str(stopped.value)
