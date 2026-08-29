"""The three commands, and the exit codes CI reads.

`check` returning 1 rather than repairing what it finds is the whole design, so most of
what is here is about that: it has to notice a missing output, notice a changed one, and
say which file and what to run.
"""

from __future__ import annotations

import pytest

from bpc.cli import main


@pytest.fixture
def sources(tmp_path):
    """A source tree with one small document, laid out the way the repository is."""
    root = tmp_path / "blueprints" / "sources"
    root.mkdir(parents=True)
    (root / "BP-TOY.md").write_text(
        "# BP-TOY: a toy\n\nbefore\n\n<!-- bpc: overview -->\n\nafter\n", encoding="utf-8"
    )
    return root


def run(sources, *args, tree=None):
    argv = ["--sources", str(sources)]
    if tree is not None:
        argv += ["--tree", str(tree)]
    return main([*argv, *args])


def test_list_shows_the_output_path_and_the_blocks(sources, capsys):
    assert run(sources, "list") == 0
    out = capsys.readouterr().out
    assert "BP-TOY.md -> " in out
    assert out.rstrip().endswith(": overview")


def test_list_does_not_need_a_checkout(sources, capsys, monkeypatch):
    """Listing is about the documents, so it works on a machine with no CPython on it."""
    monkeypatch.delenv("CPYTHON_SRC", raising=False)
    assert run(sources, "list") == 0


def test_build_writes_the_output_one_directory_up(sources, tree, capsys):
    assert run(sources, "build", tree=tree) == 0
    written = sources.parent / "BP-TOY.md"
    assert written.exists()
    assert "<!-- bpc:begin overview -->" in written.read_text(encoding="utf-8")
    assert "1 blueprint(s) generated" in capsys.readouterr().out


def test_build_twice_writes_the_same_bytes(sources, tree):
    run(sources, "build", tree=tree)
    first = (sources.parent / "BP-TOY.md").read_bytes()
    run(sources, "build", tree=tree)
    assert (sources.parent / "BP-TOY.md").read_bytes() == first


def test_check_passes_on_what_build_just_wrote(sources, tree, capsys):
    run(sources, "build", tree=tree)
    assert run(sources, "check", tree=tree) == 0
    assert "0 out of date" in capsys.readouterr().out


def test_check_fails_when_the_output_was_never_built(sources, tree, capsys):
    assert run(sources, "check", tree=tree) == 1
    assert "has not been built" in capsys.readouterr().err


def test_check_fails_when_somebody_edited_the_generated_part(sources, tree, capsys):
    run(sources, "build", tree=tree)
    written = sources.parent / "BP-TOY.md"
    written.write_text(
        written.read_text(encoding="utf-8").replace("before", "edited"), encoding="utf-8"
    )
    assert run(sources, "check", tree=tree) == 1
    err = capsys.readouterr().err
    assert "no longer matches" in err
    assert "just build-blueprints" in err


def test_check_does_not_repair_what_it_finds(sources, tree):
    run(sources, "build", tree=tree)
    written = sources.parent / "BP-TOY.md"
    written.write_text("broken\n", encoding="utf-8")
    run(sources, "check", tree=tree)
    assert written.read_text(encoding="utf-8") == "broken\n"


def test_no_source_documents_says_where_it_looked(tmp_path, capsys):
    empty = tmp_path / "sources"
    empty.mkdir()
    assert run(empty, "build") == 0
    assert "no source documents under" in capsys.readouterr().err


def test_a_bad_directive_exits_one_and_explains(sources, tree, capsys):
    (sources / "BP-TOY.md").write_text("<!-- bpc: nope -->\n", encoding="utf-8")
    assert run(sources, "build", tree=tree) == 1
    assert "there is no block called 'nope'" in capsys.readouterr().err


def test_no_checkout_anywhere_exits_two(sources, capsys, monkeypatch):
    """Two rather than one, so CI can tell a missing checkout from a real failure.

    `find_tree` is replaced rather than pointed at an empty directory, because it falls
    back to `CPYTHON_SRC` and then to `vendor/cpython`, and on a machine that has either
    of those a bad `--tree` quietly succeeds.
    """
    from refcheck.tree import TreeNotFound

    def missing(_):
        raise TreeNotFound("no CPython checkout found")

    monkeypatch.setattr("bpc.cli.find_tree", missing)
    assert run(sources, "build") == 2
    assert "no CPython checkout found" in capsys.readouterr().err


def test_a_command_is_required(capsys):
    with pytest.raises(SystemExit):
        main([])
