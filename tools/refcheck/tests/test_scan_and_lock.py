"""Scanning authored files, and the lockfile round trip."""

from __future__ import annotations

import json

from refcheck.citation import Citation
from refcheck.lock import Lock
from refcheck.resolve import Resolved
from refcheck.scan import scan, scan_file


def write(tmp_path, name, text):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_scan_markdown_records_the_line_it_was_written_on(tmp_path):
    path = write(
        tmp_path,
        "lesson.md",
        "intro\n\nthe header is `Include/object.h:127-149@v3.15.0rc1`\n",
    )
    found = scan_file(path)
    assert len(found) == 1
    assert found[0].line == 3
    assert found[0].source.endswith("lesson.md:3")


def test_scan_python_comments(tmp_path):
    path = write(
        tmp_path,
        "probe.py",
        "# see Objects/listobject.c:1232@v3.15.0rc1#list_append_impl\nx = 1\n",
    )
    assert [o.citation.symbol for o in scan_file(path)] == ["list_append_impl"]


def test_scan_notebook_reads_source_but_not_output(tmp_path):
    notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "source": ["cited: `Include/object.h:127@v3.15.0rc1`\n"],
            },
            {
                "cell_type": "code",
                "source": ["print(1)\n"],
                "outputs": [{"output_type": "stream", "text": ["Objects/fake.c:1@v3.15.0rc1\n"]}],
            },
        ]
    }
    path = write(tmp_path, "n.ipynb", json.dumps(notebook))
    found = scan_file(path)
    assert [c.citation.path for c in found] == ["Include/object.h"]


def test_scan_notebook_accepts_a_plain_string_source(tmp_path):
    notebook = {"cells": [{"cell_type": "markdown", "source": "`Include/object.h:1@v3.15.0rc1`"}]}
    path = write(tmp_path, "n.ipynb", json.dumps(notebook))
    assert len(scan_file(path)) == 1


def test_scan_notebook_survives_invalid_json(tmp_path):
    path = write(tmp_path, "broken.ipynb", "{not json")
    assert scan_file(path) == []


def test_walk_skips_the_vendored_tree(tmp_path):
    write(tmp_path, "book/a.md", "`Include/object.h:1@v3.15.0rc1`")
    write(tmp_path, "vendor/cpython/README.md", "`Include/object.h:2@v3.15.0rc1`")
    write(tmp_path, "book/__pycache__/x.py", "# Include/object.h:3@v3.15.0rc1")
    found = scan([tmp_path])
    assert [o.citation.start for o in found] == [1]


def test_walk_ignores_files_we_do_not_author(tmp_path):
    write(tmp_path, "a.c", "// Include/object.h:1@v3.15.0rc1")
    write(tmp_path, "b.md", "`Include/object.h:2@v3.15.0rc1`")
    assert [o.citation.start for o in scan([tmp_path])] == [2]


def _resolved(key_line=127):
    cite = Citation.parse(f"Include/object.h:{key_line}@v3.15.0rc1")
    return Resolved(
        citation=cite, lines=("struct _object {",), digest="abc123", first_line="struct _object {"
    )


def test_lock_round_trip(tmp_path):
    lock = Lock()
    lock.put(_resolved())
    path = tmp_path / "citations.lock.json"
    lock.dump(path)

    reloaded = Lock.load(path)
    entry = reloaded.get(Citation.parse("Include/object.h:127@v3.15.0rc1"))
    assert entry is not None
    assert entry.digest == "abc123"
    assert entry.first_line == "struct _object {"


def test_lock_lookup_ignores_the_symbol(tmp_path):
    lock = Lock()
    lock.put(_resolved())
    assert lock.get(Citation.parse("Include/object.h:127@v3.15.0rc1#ob_refcnt")) is not None


def test_an_entry_nothing_cites_any_more_is_dropped():
    # Narrowing a citation leaves the old range behind, and without this the lockfile only
    # ever grows until a reviewer cannot tell a live entry from a dead one.
    lock = Lock()
    lock.put(_resolved(100))
    lock.put(_resolved(200))
    dropped = lock.keep_only(["Include/object.h:100-100@v3.15.0rc1"])
    assert dropped == ["Include/object.h:200-200@v3.15.0rc1"]
    assert list(lock.entries) == ["Include/object.h:100-100@v3.15.0rc1"]


def test_keeping_everything_drops_nothing():
    lock = Lock()
    lock.put(_resolved(100))
    assert lock.keep_only(["Include/object.h:100-100@v3.15.0rc1"]) == []
    assert len(lock.entries) == 1


def test_missing_lockfile_loads_as_empty(tmp_path):
    assert Lock.load(tmp_path / "nope.json").entries == {}


def test_lockfile_keys_are_sorted_so_diffs_are_readable(tmp_path):
    lock = Lock()
    for line in (300, 100, 200):
        lock.put(_resolved(line))
    path = tmp_path / "citations.lock.json"
    lock.dump(path)
    document = json.loads(path.read_text())
    assert list(document["citations"]) == sorted(document["citations"])


def test_lockfile_ends_with_a_newline(tmp_path):
    path = tmp_path / "citations.lock.json"
    Lock().dump(path)
    assert path.read_text().endswith("\n")


def test_lockfile_stores_the_readable_first_line(tmp_path):
    """A reviewer looking at a lockfile diff has to be able to see what moved."""
    path = tmp_path / "citations.lock.json"
    lock = Lock()
    lock.put(_resolved())
    lock.dump(path)
    assert "struct _object {" in path.read_text()
