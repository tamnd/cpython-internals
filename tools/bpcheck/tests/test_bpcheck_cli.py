"""The command, its exit codes, and what it prints."""

from __future__ import annotations

from pathlib import Path

import pytest
from blueprint_fixtures import clean_text, replace, write

from bpcheck.cli import main


def test_a_clean_directory_passes(tmp_path: Path, capsys):
    root = tmp_path / "blueprints"
    write(root / "BP-DEMO.md", clean_text())
    assert main(["lint", str(root)]) == 0
    assert "1 blueprint(s): 0 problem(s)" in capsys.readouterr().out


def test_a_broken_blueprint_fails(tmp_path: Path, capsys):
    root = tmp_path / "blueprints"
    write(root / "BP-DEMO.md", replace(clean_text(), "**Status:** complete", "**Status:** soon"))
    assert main(["lint", str(root)]) == 1
    captured = capsys.readouterr()
    assert "'soon'" in captured.err
    assert "1 blueprint(s): 1 problem(s)" in captured.out


def test_an_unlisted_blueprint_fails(tmp_path: Path, capsys):
    root = tmp_path / "blueprints"
    write(root / "BP-DEMO.md", clean_text())
    write(root / "BP-OTHER.md", clean_text().replace("BP-DEMO", "BP-OTHER"))
    assert main(["lint", str(root)]) == 1
    assert "BP-OTHER.md is not linked from the index" in capsys.readouterr().err


def test_an_empty_directory_is_not_a_failure(tmp_path: Path, capsys):
    root = tmp_path / "blueprints"
    root.mkdir()
    assert main(["lint", str(root)]) == 0
    assert "no blueprints found" in capsys.readouterr().err


def test_one_file_can_be_checked_on_its_own(tmp_path: Path):
    path = write(tmp_path / "blueprints" / "BP-DEMO.md", clean_text())
    assert main(["lint", str(path)]) == 0


def test_no_subcommand_is_a_usage_error(capsys):
    with pytest.raises(SystemExit) as caught:
        main([])
    assert caught.value.code == 2
