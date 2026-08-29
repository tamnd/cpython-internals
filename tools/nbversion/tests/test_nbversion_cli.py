"""The two subcommands, and the exit codes CI branches on.

The distinction that matters is 1 against 2. A run that found a problem and a run that
never looked at anything both fail, and only one of them means a lesson is wrong.
"""

from __future__ import annotations

import pytest
from version_fixtures import code, notebook, recorded

from nbversion.cli import main


def lessons(tmp_path, cells, name="t01.ipynb"):
    """A lessons directory with one notebook in it, where the CLI looks by default."""
    return notebook(tmp_path / "lessons" / "t01" / name, cells)


def test_no_subcommand_is_a_usage_error():
    with pytest.raises(SystemExit) as caught:
        main([])
    assert caught.value.code == 2


def test_comparing_a_directory_that_is_not_there_exits_two(tmp_path, capsys):
    assert main(["compare", str(tmp_path / "nowhere"), str(tmp_path)]) == 2
    assert "not a directory" in capsys.readouterr().err


def test_two_empty_directories_exit_two_rather_than_passing(tmp_path, capsys):
    """Nothing to compare is not the same as nothing differing, and CI has to tell them apart."""
    first, second = tmp_path / "a", tmp_path / "b"
    first.mkdir()
    second.mkdir()
    assert main(["compare", str(first), str(second)]) == 2
    assert "no recordings" in capsys.readouterr().err


def test_two_matching_recordings_pass(tmp_path, capsys):
    lessons(tmp_path, [code("print(1)\n", identifier="t01-01")])
    recorded(tmp_path / "a", "3.15", {"t01-01": "1"})
    recorded(tmp_path / "b", "3.14", {"t01-01": "1"})
    code_ = main(
        ["compare", str(tmp_path / "a"), str(tmp_path / "b"), "--paths", str(tmp_path / "lessons")]
    )
    assert code_ == 0
    assert "no differences" in capsys.readouterr().out


def test_an_undeclared_difference_exits_one(tmp_path, capsys):
    lessons(tmp_path, [code("print(1)\n", identifier="t01-01")])
    recorded(tmp_path / "a", "3.15", {"t01-01": "1"})
    recorded(tmp_path / "b", "3.14", {"t01-01": "2"})
    code_ = main(
        ["compare", str(tmp_path / "a"), str(tmp_path / "b"), "--paths", str(tmp_path / "lessons")]
    )
    assert code_ == 1
    out = capsys.readouterr()
    assert "undeclared" in out.err
    assert "`differs=` note" in out.err


def test_a_declared_difference_passes_and_says_so(tmp_path, capsys):
    lessons(tmp_path, [code("print(1)\n", identifier="t01-01", differs="3.14 prints 2.")])
    recorded(tmp_path / "a", "3.15", {"t01-01": "1"})
    recorded(tmp_path / "b", "3.14", {"t01-01": "2"})
    code_ = main(
        ["compare", str(tmp_path / "a"), str(tmp_path / "b"), "--paths", str(tmp_path / "lessons")]
    )
    assert code_ == 0
    out = capsys.readouterr()
    assert "declared" in out.out
    assert "3.14 prints 2." in out.out


def test_a_note_on_a_cell_that_stopped_differing_exits_one(tmp_path, capsys):
    lessons(tmp_path, [code("print(1)\n", identifier="t01-01", differs="3.14 prints 2.")])
    recorded(tmp_path / "a", "3.15", {"t01-01": "1"})
    recorded(tmp_path / "b", "3.14", {"t01-01": "1"})
    code_ = main(
        ["compare", str(tmp_path / "a"), str(tmp_path / "b"), "--paths", str(tmp_path / "lessons")]
    )
    assert code_ == 1
    assert "stale" in capsys.readouterr().err


def test_recording_nothing_exits_two(tmp_path, capsys):
    (tmp_path / "empty").mkdir()
    assert main(["record", str(tmp_path / "empty"), "--into", str(tmp_path / "out")]) == 2
    assert "no notebooks found" in capsys.readouterr().err


def test_recording_writes_one_file_per_notebook_under_the_version(tmp_path, capsys):
    pytest.importorskip("nbclient")
    pytest.importorskip("ipykernel")
    from nbversion.record import version

    lessons(tmp_path, [code("print(6 * 7)\n", identifier="t01-01")])
    into = tmp_path / "out"
    assert main(["record", str(tmp_path / "lessons"), "--into", str(into)]) == 0
    written = into / version() / "t01.json"
    assert written.exists()
    assert '"42"' in written.read_text(encoding="utf-8")


def test_a_recording_compares_against_itself_with_no_differences(tmp_path):
    """The round trip, end to end, on one interpreter: record twice, compare, pass."""
    pytest.importorskip("nbclient")
    pytest.importorskip("ipykernel")
    from nbversion.record import version

    lessons(tmp_path, [code("print(6 * 7)\n", identifier="t01-01")])
    for name in ("first", "second"):
        assert main(["record", str(tmp_path / "lessons"), "--into", str(tmp_path / name)]) == 0
    here = version()
    assert (
        main(
            [
                "compare",
                str(tmp_path / "first" / here),
                str(tmp_path / "second" / here),
                "--paths",
                str(tmp_path / "lessons"),
            ]
        )
        == 0
    )
