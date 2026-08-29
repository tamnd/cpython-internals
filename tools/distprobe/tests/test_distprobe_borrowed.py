"""Reading the Pyodide row out of the browser probe's recording."""

from __future__ import annotations

import json

from distprobe import borrowed
from distprobe.question import WANTED


def recording(tmp_path, outcome, python="3.14.2"):
    path = tmp_path / "pyodide.json"
    body = {"python": python, "outcomes": [outcome] if outcome else []}
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def working(**names):
    value = dict.fromkeys(WANTED, True)
    value.update(names)
    return {"key": borrowed.CHECK, "status": "ok", "value": value}


def test_the_committed_recording_is_where_this_expects_it():
    """A path typed once and never checked is a path that quietly stops being right."""
    assert borrowed.RECORDING.name == "pyodide.json"


def test_the_browser_row_comes_out_of_the_browser_recording(tmp_path):
    answer = borrowed.from_wasmprobe(recording(tmp_path, working()))
    assert answer.has_everything
    assert answer.version == "3.14.2"
    assert answer.platform == "emscripten wasm32"


def test_a_function_the_browser_does_not_have_is_reported_missing(tmp_path):
    answer = borrowed.from_wasmprobe(recording(tmp_path, working(optimize_cfg=False)))
    assert answer.has_module
    assert answer.missing == ("optimize_cfg",)


def test_the_browser_saying_no_is_carried_through_as_a_no(tmp_path):
    outcome = {"key": borrowed.CHECK, "status": "failed", "value": None}
    answer = borrowed.from_wasmprobe(recording(tmp_path, outcome))
    assert not answer.has_module
    assert not answer.unreachable


def test_a_check_the_browser_probe_never_ran_is_still_a_no(tmp_path):
    answer = borrowed.from_wasmprobe(recording(tmp_path, None))
    assert not answer.has_module


def test_no_recording_at_all_is_unreachable_and_says_what_to_run(tmp_path):
    """Somebody without Node should still get the other eleven rows."""
    answer = borrowed.from_wasmprobe(tmp_path / "nothing.json")
    assert answer.unreachable
    assert "just build-probe" in answer.unreachable


def test_the_browser_probe_is_not_asked_about_testcapi_and_says_so(tmp_path):
    """A blank cell would read as a no. Nothing in the lessons needs it there."""
    assert borrowed.from_wasmprobe(recording(tmp_path, working())).testcapi == "not asked"
