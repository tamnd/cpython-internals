"""The Node side, and the committed recordings it produced.

The slow test here really does boot a WebAssembly Python, so it only runs when Node and the
Pyodide package are both installed. Everything else works off the recordings in the
repository, which is the point of committing them.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from wasmprobe import browser, report
from wasmprobe.checks import BY_KEY, CHECKS
from wasmprobe.result import FATAL, OK, SKIPPED, Outcome, Run

RESULTS = Path(__file__).resolve().parents[3] / "probes" / "pyodide"


def test_the_driver_is_next_to_the_package():
    assert browser.DRIVER.name == "driver.mjs"
    assert browser.DRIVER.exists()


def test_a_missing_check_comes_back_as_skipped():
    body = {"runtime": "pyodide", "python": "3.14.2", "seconds": 1.0, "outcomes": []}
    run = browser._assemble(body, [BY_KEY["version"]], 0)
    assert run.outcomes["version"].status == SKIPPED


def test_the_order_of_the_checks_is_the_order_of_the_report():
    keys = ["version", "gc"]
    body = {
        "runtime": "pyodide",
        "python": "3.14.2",
        "seconds": 1.0,
        "outcomes": [{"key": "gc", "status": OK}, {"key": "version", "status": OK}],
    }
    run = browser._assemble(body, [BY_KEY[key] for key in keys], 0)
    assert list(run.outcomes) == keys


def test_a_driver_that_died_gets_a_better_sentence():
    body = {
        "runtime": "pyodide",
        "python": "3.14.2",
        "seconds": 1.0,
        "outcomes": [{"key": "gc", "status": FATAL, "error": "the runtime did not come back"}],
    }
    run = browser._assemble(body, [BY_KEY["gc"]], 1)
    assert run.outcomes["gc"].error == "took the whole process down"


def test_ready_says_what_is_missing(monkeypatch):
    monkeypatch.setattr(browser.shutil, "which", lambda name: None)
    assert browser.ready() == "node is not on PATH"


def test_running_without_node_raises_rather_than_pretending(monkeypatch):
    monkeypatch.setattr(browser, "ready", lambda: "node is not on PATH")
    with pytest.raises(browser.Missing):
        browser.run()


def recorded():
    """The two files in probes/pyodide, which are the committed answer to the gate."""
    for name in ("native.json", "pyodide.json"):
        if not (RESULTS / name).exists():
            pytest.skip(f"no recording at {RESULTS / name}")
    return Run.load(RESULTS / "native.json"), Run.load(RESULTS / "pyodide.json")


def test_both_recordings_cover_every_check():
    native, browser_run = recorded()
    keys = {check.key for check in CHECKS}
    assert set(native.outcomes) == keys
    assert set(browser_run.outcomes) == keys


def test_nothing_blocking_is_broken_in_the_recorded_browser_run():
    native, browser_run = recorded()
    assert report.regressions(native, browser_run) == []


def test_the_report_on_disk_matches_the_recordings():
    native, browser_run = recorded()
    path = RESULTS / "report.md"
    if not path.exists():
        pytest.skip("no report yet")
    assert path.read_text(encoding="utf-8") == report.markdown(native, browser_run)


def test_the_recorded_browser_run_really_was_webassembly():
    _, browser_run = recorded()
    assert browser_run.outcomes["version"].value["platform"].startswith("emscripten")


def test_the_native_recording_answered_everything():
    """It is the control. Anything broken there is our bug rather than a WebAssembly one."""
    native, _ = recorded()
    broken = {key: one.error for key, one in native.outcomes.items() if not one.worked}
    assert not broken


@pytest.mark.slow
def test_a_real_webassembly_run():
    problem = browser.ready()
    if problem:
        pytest.skip(problem)
    run = browser.run([BY_KEY["version"], BY_KEY["front_end_modules"]])
    assert run.runtime == "pyodide"
    assert run.seconds > 0
    assert run.outcomes["version"].value["platform"].startswith("emscripten")
    assert run.outcomes["front_end_modules"].value["dis"] is True


@pytest.mark.slow
def test_a_check_that_kills_the_runtime_does_not_take_the_rest_with_it():
    """The whole reason the driver reboots between checks."""
    problem = browser.ready()
    if problem:
        pytest.skip(problem)
    run = browser.run([BY_KEY["optimize_cfg_short_consts"], BY_KEY["front_end_modules"]])
    assert run.outcomes["optimize_cfg_short_consts"].status == FATAL
    assert run.outcomes["front_end_modules"].status == OK


def test_the_recordings_are_indented_json_a_person_can_read():
    path = RESULTS / "pyodide.json"
    if not path.exists():
        pytest.skip("no recording")
    text = path.read_text(encoding="utf-8")
    assert "\n  " in text
    assert json.loads(text)["runtime"] == "pyodide"


def test_outcome_equality_is_by_value():
    assert Outcome("a", OK, value=[1]) == Outcome("a", OK, value=[1])
