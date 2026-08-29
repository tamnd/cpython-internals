"""Outcomes and runs, and the round trip through disk that the two sides share."""

from __future__ import annotations

import json

from wasmprobe.result import FATAL, OK, RAISED, SKIPPED, Outcome, Run


def test_worked_is_only_true_for_ok():
    assert Outcome("a", OK).worked
    for status in (RAISED, FATAL, SKIPPED):
        assert not Outcome("a", status, error="why").worked


def test_empty_fields_stay_out_of_the_file():
    body = Outcome("a", OK).as_dict()
    assert body == {"key": "a", "status": OK}


def test_a_value_and_an_error_both_survive():
    body = Outcome("a", RAISED, value=[1], error="ValueError: no").as_dict()
    assert Outcome.from_dict(body) == Outcome("a", RAISED, value=[1], error="ValueError: no")


def test_a_run_round_trips(tmp_path):
    run = Run(
        runtime="pyodide",
        python="3.14.2",
        outcomes={
            "first": Outcome("first", OK, value={"n": 1}),
            "second": Outcome("second", FATAL, error="memory access out of bounds"),
        },
        seconds=1.25,
    )
    path = run.write(tmp_path / "deep" / "run.json")
    assert path.exists()
    assert Run.load(path) == run


def test_the_file_is_readable_json_with_a_trailing_newline(tmp_path):
    run = Run(runtime="native", python="3.15.0", outcomes={"a": Outcome("a", OK)})
    path = run.write(tmp_path / "run.json")
    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert json.loads(text)["outcomes"] == [{"key": "a", "status": OK}]


def test_order_is_kept(tmp_path):
    keys = ["c", "a", "b"]
    run = Run("native", "3.15.0", {key: Outcome(key, OK) for key in keys})
    assert list(Run.load(run.write(tmp_path / "run.json")).outcomes) == keys
