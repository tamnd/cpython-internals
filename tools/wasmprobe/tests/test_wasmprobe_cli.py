"""The command line, driven the way CI drives it."""

from __future__ import annotations

import pytest
from wasmprobe import notebook, report
from wasmprobe.cli import BROWSER, NATIVE, NOTEBOOK, REPORT, main
from wasmprobe.result import FATAL, OK, Outcome, Run


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


def generated(room, checks):
    """Write the two generated files, so the staleness gate has nothing to complain about."""
    native, browser = Run.load(room / NATIVE), Run.load(room / BROWSER)
    (room / REPORT).write_text(report.markdown(native, browser, checks), encoding="utf-8")
    (room / NOTEBOOK).write_text(notebook.render(), encoding="utf-8")


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


def test_a_missing_recording_says_which_one(tmp_path):
    with pytest.raises(SystemExit) as stopped:
        main(["check", str(tmp_path)])
    assert "native.json" in str(stopped.value)


def test_browser_without_node_is_a_failure_not_a_crash(capsys, monkeypatch):
    from wasmprobe import browser

    monkeypatch.setattr(browser, "ready", lambda: "node is not on PATH")
    assert main(["browser", "--into", "unused"]) == 1
    assert "node is not on PATH" in capsys.readouterr().err
