"""The command line, driven the way CI drives it."""

from __future__ import annotations

import pytest

from wasmprobe import lessons, notebook, report
from wasmprobe.cli import BROWSER, LESSONS, LESSONS_REPORT, NATIVE, NOTEBOOK, REPORT, main
from wasmprobe.lessons import Cell, Lesson, Ran
from wasmprobe.result import FATAL, OK, RAISED, Outcome, Run


def pair(room, browser_status=OK):
    native = Run("native", "3.15.0", {"gc": Outcome("gc", OK)})
    browser = Run(
        "pyodide",
        "3.14.2",
        {"gc": Outcome("gc", browser_status, error="boom" if browser_status != OK else "")},
        seconds=1.4,
    )
    native.write(room / NATIVE)
    browser.write(room / BROWSER)
    return native, browser


def taught(room, status=OK):
    """Write a lesson run, which `check` treats as required rather than optional."""
    error = "ValueError: boom" if status != OK else ""
    ran = Ran(
        python="3.14.2", lessons=[Lesson("t99-a-lesson", [Cell("t99-1", status, error=error)])]
    )
    ran.write(room / LESSONS)
    (room / LESSONS_REPORT).write_text(lessons.markdown(ran), encoding="utf-8")
    return ran


def generated(room, checks, status=OK):
    """Write the generated files, so the staleness gate has nothing to complain about."""
    native, browser = Run.load(room / NATIVE), Run.load(room / BROWSER)
    (room / REPORT).write_text(report.markdown(native, browser, checks), encoding="utf-8")
    (room / NOTEBOOK).write_text(notebook.render(), encoding="utf-8")
    taught(room, status)


def only_gc(monkeypatch):
    """Trim the check list the report walks, so the fixtures above are the whole world."""
    from wasmprobe.checks import BY_KEY

    wanted = [BY_KEY["gc"]]
    monkeypatch.setattr(report, "CHECKS", wanted)
    return wanted


def test_list_prints_every_check(capsys):
    assert main(["list"]) == 0
    printed = capsys.readouterr().out
    assert "internal_capi_import" in printed
    assert printed.count("\n") >= 10


def test_native_writes_a_run(tmp_path, capsys):
    assert main(["native", "--into", str(tmp_path)]) == 0
    assert (tmp_path / NATIVE).exists()
    assert "checks worked on CPython" in capsys.readouterr().out


def test_report_without_a_destination_prints(tmp_path, capsys, monkeypatch):
    only_gc(monkeypatch)
    pair(tmp_path)
    assert main(["report", str(tmp_path)]) == 0
    assert "# What works under Pyodide" in capsys.readouterr().out


def test_report_into_a_file(tmp_path, monkeypatch):
    only_gc(monkeypatch)
    pair(tmp_path)
    destination = tmp_path / "deep" / "report.md"
    assert main(["report", str(tmp_path), "--into", str(destination)]) == 0
    assert "3.14.2 WebAssembly" in destination.read_text(encoding="utf-8")


def test_check_passes_when_nothing_regressed(tmp_path, monkeypatch, capsys):
    wanted = only_gc(monkeypatch)
    pair(tmp_path)
    generated(tmp_path, wanted)
    assert main(["check", str(tmp_path)]) == 0
    assert "works in both" in capsys.readouterr().out


def test_check_fails_when_the_report_has_fallen_behind(tmp_path, monkeypatch, capsys):
    only_gc(monkeypatch)
    pair(tmp_path)
    assert main(["check", str(tmp_path)]) == 1
    assert "out of date: report.md, probe.ipynb" in capsys.readouterr().err


def test_notebook_writes_where_it_is_told(tmp_path, capsys):
    destination = tmp_path / "probe.ipynb"
    assert main(["notebook", "--into", str(destination)]) == 0
    assert destination.exists()
    assert "run in their own browser" in capsys.readouterr().out


def test_check_fails_and_says_what_it_costs(tmp_path, monkeypatch, capsys):
    wanted = only_gc(monkeypatch)
    pair(tmp_path, browser_status=FATAL)
    generated(tmp_path, wanted)
    assert main(["check", str(tmp_path)]) == 1
    complaint = capsys.readouterr().err
    assert "gc: fatal" in complaint
    assert "move those experiments to Tier 1" in complaint


def test_check_fails_when_a_lesson_cell_broke_and_nobody_said_why(tmp_path, monkeypatch, capsys):
    wanted = only_gc(monkeypatch)
    pair(tmp_path)
    generated(tmp_path, wanted, status=RAISED)
    assert main(["check", str(tmp_path)]) == 1
    assert "t99-a-lesson t99-1: ValueError: boom" in capsys.readouterr().err


def test_check_fails_when_nobody_has_run_the_lessons(tmp_path, monkeypatch, capsys):
    """A gate that passes when its recording is missing passes forever once somebody deletes it."""
    wanted = only_gc(monkeypatch)
    pair(tmp_path)
    native, browser = Run.load(tmp_path / NATIVE), Run.load(tmp_path / BROWSER)
    (tmp_path / REPORT).write_text(report.markdown(native, browser, wanted), encoding="utf-8")
    (tmp_path / NOTEBOOK).write_text(notebook.render(), encoding="utf-8")
    assert main(["check", str(tmp_path)]) == 1
    assert "no lesson run at" in capsys.readouterr().err


def test_a_missing_recording_says_which_one(tmp_path):
    with pytest.raises(SystemExit) as stopped:
        main(["check", str(tmp_path)])
    assert "native.json" in str(stopped.value)


def test_browser_without_node_is_a_failure_not_a_crash(capsys, monkeypatch):
    from wasmprobe import browser

    monkeypatch.setattr(browser, "ready", lambda: "node is not on PATH")
    assert main(["browser", "--into", "unused"]) == 1
    assert "node is not on PATH" in capsys.readouterr().err
