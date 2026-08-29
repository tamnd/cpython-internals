"""The command line, driven the way the workflow drives it.

Half of these subcommands exist to be read by a shell, so what they print matters as much as
what they return. A subcommand that helpfully prints a heading breaks the build arg it was
feeding.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from cpybuild.cli import main
from cpybuild.configs import ARCHITECTURES, CONFIGURATIONS
from cpybuild.images import Lock

from refcheck import PINNED_COMMIT

ONE = "sha256:" + "c" * 64

#: Relative to this file rather than to the working directory, so the test says the same thing
#: whether pytest was started at the top of the repository or inside this package.
DOCKERFILE = Path(__file__).parents[3] / "images" / "cpython" / "Dockerfile"


TWO = "sha256:" + "d" * 64


@pytest.fixture
def lockfile(tmp_path):
    path = tmp_path / "cpython.lock.json"
    lock = Lock()
    for config in CONFIGURATIONS:
        for arch in ARCHITECTURES:
            lock.record(config.key, arch, ONE)
        lock.record_index(config.key, TWO)
    lock.write(path)
    return path


@pytest.fixture
def devcontainer(tmp_path, lockfile):
    """A devcontainer pointing at the fixture lockfile, with a comment in it to be preserved."""
    path = tmp_path / "devcontainer.json"
    reference = Lock.load(lockfile).reference_index("debug")
    path.write_text(
        f'// read me\n{{\n  "image": "{reference}"\n}}\n',
        encoding="utf-8",
    )
    return path


def test_list_shows_every_build_and_what_it_is_for(capsys):
    assert main(["list"]) == 0
    printed = capsys.readouterr().out
    for one in CONFIGURATIONS:
        assert one.key in printed
        assert one.summary in printed


def test_matrix_is_one_line_of_json_and_nothing_else(capsys):
    """The workflow reads this with fromJSON, so a heading above it breaks the run."""
    assert main(["matrix"]) == 0
    printed = capsys.readouterr().out
    assert printed.count("\n") == 1
    assert len(json.loads(printed)) == len(CONFIGURATIONS) * len(ARCHITECTURES)


def test_packages_is_one_apt_line(capsys):
    assert main(["packages", "tailcall"]) == 0
    printed = capsys.readouterr().out.strip()
    assert "clang" in printed.split()
    assert "build-essential" in printed.split()


def test_flags_for_the_release_build_is_empty_rather_than_a_word(capsys):
    """It goes into a build arg. The word "none" would be passed to configure."""
    assert main(["flags", "release"]) == 0
    assert capsys.readouterr().out == "\n"


def test_flags_for_the_debug_build_is_the_configure_line(capsys):
    assert main(["flags", "debug"]) == 0
    assert capsys.readouterr().out.strip() == "--with-pydebug --with-assertions"


def test_a_build_nobody_has_heard_of_is_refused(capsys):
    with pytest.raises(SystemExit):
        main(["flags", "pgo"])
    assert "invalid choice" in capsys.readouterr().err


def test_buildargs_covers_every_argument_the_dockerfile_declares(capsys):
    """A build arg the Dockerfile takes and nobody passes silently keeps its default."""
    declared = {
        line.split()[1].split("=")[0]
        for line in DOCKERFILE.read_text(encoding="utf-8").splitlines()
        if line.startswith("ARG ")
    } - {"DEBIAN"}
    main(["buildargs", "debug"])
    passed = {line.split("=", 1)[0] for line in capsys.readouterr().out.splitlines()}
    assert declared <= passed


def test_buildargs_prints_empty_values_rather_than_dropping_the_line(capsys):
    """The Dockerfile tests CC with -n. A missing line leaves whatever the last build set."""
    main(["buildargs", "release"])
    printed = capsys.readouterr().out.splitlines()
    assert "CC=" in printed
    assert "DEBUGGER=" in printed


def test_buildargs_marks_the_debug_build_as_wanting_a_debugger(capsys):
    main(["buildargs", "debug"])
    assert "DEBUGGER=yes" in capsys.readouterr().out.splitlines()


def test_buildargs_carries_the_compiler_for_the_builds_that_need_one(capsys):
    main(["buildargs", "tailcall"])
    assert "CC=clang" in capsys.readouterr().out.splitlines()


def test_buildargs_is_pinned_to_the_same_commit_as_the_citations(capsys):
    main(["buildargs", "release"])
    assert f"CPYTHON_COMMIT={PINNED_COMMIT}" in capsys.readouterr().out.splitlines()


def test_check_passes_on_a_complete_lockfile(lockfile, devcontainer, capsys):
    assert main(["--lockfile", str(lockfile), "--devcontainer", str(devcontainer), "check"]) == 0
    assert "10 images from CPython" in capsys.readouterr().out


def test_check_fails_and_names_what_is_missing(lockfile, capsys):
    lock = Lock.load(lockfile)
    del lock.images["jit"]
    lock.write(lockfile)
    assert main(["--lockfile", str(lockfile), "check"]) == 1
    assert "no jit image for amd64" in capsys.readouterr().err


def test_check_without_a_lockfile_says_what_to_run(tmp_path, capsys):
    assert main(["--lockfile", str(tmp_path / "nothing.json"), "check"]) == 1
    assert "cpython-images" in capsys.readouterr().err


def test_reference_prints_one_pullable_string(lockfile, capsys):
    assert main(["--lockfile", str(lockfile), "reference", "debug", "--arch", "arm64"]) == 0
    printed = capsys.readouterr().out.strip()
    assert printed.endswith(f"@{ONE}")
    assert " " not in printed


def test_reference_defaults_to_amd64_because_that_is_what_ci_runs_on(lockfile, capsys):
    main(["--lockfile", str(lockfile), "reference", "debug"])
    first = capsys.readouterr().out
    main(["--lockfile", str(lockfile), "reference", "debug", "--arch", "amd64"])
    assert capsys.readouterr().out == first


def test_protected_includes_what_is_in_the_lockfile_right_now(lockfile, capsys, monkeypatch):
    """Deleting the image the current site refers to would be the worst possible tidy up."""
    monkeypatch.setattr("cpybuild.cli.protected", lambda: set())
    assert main(["--lockfile", str(lockfile), "protected"]) == 0
    assert sorted(capsys.readouterr().out.split()) == sorted({ONE, TWO})


def test_protected_is_one_digest_per_line_for_a_shell_to_read(lockfile, capsys, monkeypatch):
    other = "sha256:" + "e" * 64
    monkeypatch.setattr("cpybuild.cli.protected", lambda: {other})
    main(["--lockfile", str(lockfile), "protected"])
    printed = capsys.readouterr().out.splitlines()
    assert sorted(printed) == sorted({ONE, TWO, other})
    assert all(line.startswith("sha256:") for line in printed)


def test_prune_prints_ids_on_stdout_and_the_reasoning_on_stderr(tmp_path, capsys):
    """The workflow pipes stdout into a delete loop, so a summary line in it would be an id."""
    versions = tmp_path / "versions.json"
    versions.write_text(
        json.dumps(
            [
                {"id": 1, "name": ONE, "created_at": "2026-08-01T00:00:00Z"},
                {"id": 2, "name": "sha256:" + "f" * 64, "created_at": "2026-08-09T00:00:00Z"},
            ]
        )
    )
    safe = tmp_path / "protected.txt"
    safe.write_text(f"{ONE}\n")
    assert (
        main(["prune", "--versions", str(versions), "--protected", str(safe), "--keep", "0"]) == 0
    )
    said = capsys.readouterr()
    assert said.out.split() == ["2"]
    assert "1 pointed at by a release" in said.err


def test_prune_reads_a_protected_file_with_blank_lines_in_it(tmp_path, capsys):
    """`cpybuild protected` on a repository with no releases yet prints nothing at all."""
    versions = tmp_path / "versions.json"
    versions.write_text(json.dumps([{"id": 1, "name": ONE, "created_at": "2026-08-01T00:00:00Z"}]))
    safe = tmp_path / "protected.txt"
    safe.write_text("\n\n")
    main(["prune", "--versions", str(versions), "--protected", str(safe), "--keep", "0"])
    assert capsys.readouterr().out.split() == ["1"]


def test_record_writes_a_digest_into_a_lockfile_that_does_not_exist_yet(tmp_path, capsys):
    """The first run of the workflow has nothing to update, and should not need special casing."""
    path = tmp_path / "cpython.lock.json"
    assert main(["--lockfile", str(path), "record", "debug", "amd64", ONE]) == 0
    assert Lock.load(path).get("debug", "amd64").digest == ONE


def test_record_leaves_the_other_builds_alone(lockfile):
    other = "sha256:" + "d" * 64
    main(["--lockfile", str(lockfile), "record", "debug", "amd64", other])
    lock = Lock.load(lockfile)
    assert lock.get("debug", "amd64").digest == other
    assert lock.get("release", "amd64").digest == ONE


def test_record_keeps_the_size_so_the_readme_table_can_say_how_big_they_are(lockfile):
    main(["--lockfile", str(lockfile), "record", "debug", "amd64", ONE, "--size", "412000000"])
    assert Lock.load(lockfile).get("debug", "amd64").size == 412000000


def test_proof_prints_a_program_and_nothing_else(capsys):
    """The workflow pipes this straight into `python3 -` inside the image."""
    assert main(["proof", "jit"]) == 0
    said = capsys.readouterr().out
    compile(said, "proof", "exec")
    assert "sys._jit.is_available()" in said


def test_the_proof_program_exits_non_zero_when_the_build_is_wrong(capsys):
    """Running a build's own proof against this interpreter is the only way to find out that
    the program says no by exiting rather than by printing a word nobody reads."""
    main(["proof", "freethreaded"])
    program = capsys.readouterr().out
    namespace: dict = {}
    try:
        exec(program, namespace)
    except SystemExit as leaving:
        assert leaving.code == 1
    else:  # pragma: no cover
        raise AssertionError("a GIL enabled interpreter passed the free threaded proof")


def test_check_notices_a_devcontainer_left_on_an_older_image(lockfile, tmp_path, capsys):
    """The two files move together in the weekly job and apart the moment somebody edits one."""
    stale = tmp_path / "devcontainer.json"
    stale.write_text(f'{{"image": "{ONE}"}}\n', encoding="utf-8")
    assert main(["--lockfile", str(lockfile), "--devcontainer", str(stale), "check"]) == 1


def test_check_says_nothing_about_a_devcontainer_that_is_not_there(lockfile, tmp_path):
    """A checkout with no devcontainer is not broken, it is a checkout with no devcontainer."""
    missing = tmp_path / "nowhere" / "devcontainer.json"
    assert main(["--lockfile", str(lockfile), "--devcontainer", str(missing), "check"]) == 0


def test_reference_names_a_half_and_joined_names_the_whole(lockfile, capsys):
    assert main(["--lockfile", str(lockfile), "reference", "debug", "--arch", "amd64"]) == 0
    assert capsys.readouterr().out.strip().endswith(ONE)
    assert main(["--lockfile", str(lockfile), "reference", "debug", "--joined"]) == 0
    assert capsys.readouterr().out.strip().endswith(TWO)


def test_record_index_writes_the_joined_digest_back(lockfile):
    other = "sha256:" + "e" * 64
    assert main(["--lockfile", str(lockfile), "record-index", "jit", other]) == 0
    assert Lock.load(lockfile).index("jit").digest == other


def test_recording_something_that_is_not_a_digest_is_refused(lockfile):
    assert main(["--lockfile", str(lockfile), "record-index", "jit", "latest"]) == 1


def test_devcontainer_write_moves_the_image_and_keeps_the_comments(lockfile, devcontainer):
    """That file is written by hand and explains itself, so the job edits one line of it."""
    devcontainer.write_text(f'// read me\n{{\n  "image": "{ONE}"\n}}\n', encoding="utf-8")
    args = ["--lockfile", str(lockfile), "--devcontainer", str(devcontainer)]
    assert main([*args, "devcontainer", "--write"]) == 0
    said = devcontainer.read_text(encoding="utf-8")
    assert TWO in said
    assert said.startswith("// read me")


def test_devcontainer_without_write_only_prints(lockfile, devcontainer, capsys):
    before = devcontainer.read_text(encoding="utf-8")
    assert (
        main(["--lockfile", str(lockfile), "--devcontainer", str(devcontainer), "devcontainer"])
        == 0
    )
    assert TWO in capsys.readouterr().out
    assert devcontainer.read_text(encoding="utf-8") == before
