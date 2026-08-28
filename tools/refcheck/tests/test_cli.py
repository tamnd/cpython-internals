"""End to end behaviour of the command line, including the exit codes CI depends on."""

from __future__ import annotations

import json

import pytest
from refcheck.cli import main


@pytest.fixture
def lesson(tmp_path):
    path = tmp_path / "book" / "lesson.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "The object header is `Include/object.h:127-149@v3.15.0rc1#ob_refcnt`.\n",
        encoding="utf-8",
    )
    return path


def run(args, tree):
    return main(["--tree", str(tree), *args])


def test_url_needs_no_tree_at_all(capsys):
    assert main(["url", "Objects/listobject.c:1232@v3.15.0rc1"]) == 0
    out = capsys.readouterr().out.strip()
    assert out.endswith("/blob/v3.15.0rc1/Objects/listobject.c#L1232")


def test_url_rejects_a_malformed_citation(capsys):
    assert main(["url", "not-a-citation"]) == 2
    assert "not a citation" in capsys.readouterr().err


def test_show_prints_numbered_lines_and_the_permalink(tree, capsys):
    assert run(["show", "Include/object.h:127-129@v3.15.0rc1"], tree) == 0
    out = capsys.readouterr().out
    assert "127  struct _object {" in out
    assert "#L127-L129" in out


def test_show_fails_on_an_unresolvable_citation(tree, capsys):
    assert run(["show", "Objects/nope.c:1@v3.15.0rc1"], tree) == 1
    assert "missing-file" in capsys.readouterr().err


def test_verify_fails_before_the_lockfile_exists(tree, tmp_path, lesson, capsys):
    lock = tmp_path / "citations.lock.json"
    code = run(["verify", str(lesson), "--lock", str(lock)], tree)
    assert code == 1
    assert "not-in-lock" in capsys.readouterr().err


def test_update_writes_the_lock_and_then_verify_passes(tree, tmp_path, lesson):
    lock = tmp_path / "citations.lock.json"
    assert run(["verify", str(lesson), "--lock", str(lock), "--update"], tree) == 0
    assert lock.is_file()
    assert run(["verify", str(lesson), "--lock", str(lock)], tree) == 0


def test_verify_catches_a_citation_that_drifted(tree, tmp_path, lesson):
    """The failure this tool exists for: the lines moved and the prose did not."""
    lock = tmp_path / "citations.lock.json"
    run(["verify", str(lesson), "--lock", str(lock), "--update"], tree)

    document = json.loads(lock.read_text())
    key = next(iter(document["citations"]))
    document["citations"][key]["digest"] = "0" * 16
    document["citations"][key]["first_line"] = "struct _something_else {"
    lock.write_text(json.dumps(document))

    assert run(["verify", str(lesson), "--lock", str(lock)], tree) == 1


def test_the_drift_message_names_both_the_old_and_the_new_line(tree, tmp_path, lesson, capsys):
    lock = tmp_path / "citations.lock.json"
    run(["verify", str(lesson), "--lock", str(lock), "--update"], tree)
    document = json.loads(lock.read_text())
    key = next(iter(document["citations"]))
    document["citations"][key]["digest"] = "0" * 16
    document["citations"][key]["first_line"] = "struct _something_else {"
    lock.write_text(json.dumps(document))

    run(["verify", str(lesson), "--lock", str(lock)], tree)
    err = capsys.readouterr().err
    assert "struct _something_else {" in err
    assert "struct _object {" in err


def test_verify_reports_the_source_file_and_line_of_the_bad_citation(tree, tmp_path, capsys):
    bad = tmp_path / "bad.md"
    bad.write_text("one\ntwo\n`Objects/nope.c:1@v3.15.0rc1`\n", encoding="utf-8")
    run(["verify", str(bad), "--lock", str(tmp_path / "l.json")], tree)
    assert "bad.md:3" in capsys.readouterr().err


def test_scan_lists_every_citation(tree, tmp_path, lesson, capsys):
    assert run(["scan", str(lesson)], tree) == 0
    out = capsys.readouterr().out
    assert "Include/object.h:127-149@v3.15.0rc1#ob_refcnt" in out


def test_a_file_with_no_citations_verifies_clean(tree, tmp_path):
    empty = tmp_path / "empty.md"
    empty.write_text("no citations here\n", encoding="utf-8")
    assert run(["verify", str(empty), "--lock", str(tmp_path / "l.json")], tree) == 0


def test_update_does_not_paper_over_a_citation_that_cannot_resolve(tree, tmp_path, capsys):
    """--update re-baselines a stale digest. It must not make a broken path go green."""
    bad = tmp_path / "bad.md"
    bad.write_text("`Objects/nosuchfile.c:1@v3.15.0rc1`\n", encoding="utf-8")
    code = run(["verify", str(bad), "--lock", str(tmp_path / "l.json"), "--update"], tree)
    assert code == 1
    assert "missing-file" in capsys.readouterr().err


def test_update_does_clear_a_stale_digest(tree, tmp_path, lesson):
    lock = tmp_path / "citations.lock.json"
    run(["verify", str(lesson), "--lock", str(lock), "--update"], tree)
    document = json.loads(lock.read_text())
    key = next(iter(document["citations"]))
    document["citations"][key]["digest"] = "0" * 16
    lock.write_text(json.dumps(document))

    assert run(["verify", str(lesson), "--lock", str(lock), "--update"], tree) == 0
    assert run(["verify", str(lesson), "--lock", str(lock)], tree) == 0
