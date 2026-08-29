"""The five builds, and the things about them that would be quiet mistakes."""

from __future__ import annotations

import re

import pytest
from cpybuild import configs
from cpybuild.configs import ARCHITECTURES, BY_KEY, CONFIGURATIONS, LLVM_VERSION, RUNNERS


def test_the_five_builds_the_issue_asked_for_are_all_here():
    assert sorted(BY_KEY) == ["debug", "freethreaded", "jit", "release", "tailcall"]


def test_every_build_says_what_it_is_for():
    """A configuration with no reason attached is one nobody can decide to delete."""
    for one in CONFIGURATIONS:
        assert one.summary
        assert len(one.note) > 100


def test_the_release_build_passes_no_flags():
    """The point of it is to be what you get by typing configure and make."""
    assert BY_KEY["release"].flags == ()


def test_the_debug_build_turns_assertions_on_as_well_as_pydebug():
    """Py_DEBUG without assertions is half the build, and the halves do different things."""
    assert BY_KEY["debug"].flags == ("--with-pydebug", "--with-assertions")


def test_only_the_debug_build_carries_a_debugger_and_the_source():
    """The source tree is most of the image size, so it goes where it earns its place."""
    assert [one.key for one in CONFIGURATIONS if one.debugger] == ["debug"]


def test_the_tail_call_build_asks_for_clang():
    """It leans on musttail, which GCC does not have, so the default compiler would fail."""
    assert BY_KEY["tailcall"].environment["CC"] == "clang"
    assert "clang" in BY_KEY["tailcall"].packages


def test_the_jit_build_installs_llvm_because_copy_and_patch_needs_it_at_build_time():
    installed = configs.packages(BY_KEY["jit"])
    assert f"llvm-{LLVM_VERSION}" in installed
    assert f"clang-{LLVM_VERSION}" in installed


def test_the_jit_build_gets_a_host_python_to_generate_its_templates_with():
    """`make` runs Tools/jit/build.py, so this build needs an interpreter to build an
    interpreter. Found the hard way: the first run of the workflow failed here after sixty
    seconds with `python3: not found`, on both architectures."""
    assert "python3" in configs.packages(BY_KEY["jit"])


def test_no_other_build_needs_a_host_python():
    """Every package in the image is something a reader might mistake for part of CPython."""
    others = [one for one in CONFIGURATIONS if one.key != "jit"]
    assert not any("python3" in configs.packages(one) for one in others)


def test_the_jit_asks_for_the_llvm_cpython_actually_wants():
    """CPython names one exact LLVM major version and refuses anything else, because the JIT
    cuts its templates out of object files LLVM produced. Read it back out of the pinned
    checkout rather than trusting the number here, so a moved pin is a failing test and not a
    twenty minute build failing in CI."""
    tree = pytest.importorskip("refcheck").find_tree()
    said = (tree / "Tools" / "jit" / "_llvm.py").read_text(encoding="utf-8")
    wanted = re.search(r'_LLVM_VERSION\s*=\s*"(\d+)"', said)
    assert wanted, "CPython stopped spelling _LLVM_VERSION the way this test reads it"
    assert wanted.group(1) == LLVM_VERSION


def test_only_the_jit_adds_a_package_repository():
    """Every extra apt source is a thing that can go down and take the build with it."""
    assert [one.key for one in CONFIGURATIONS if one.llvm] == ["jit"]


def test_the_tail_call_build_uses_the_clang_debian_has():
    """It needs Clang 19 for musttail and trixie ships 19, so it stays on the stock package."""
    assert not BY_KEY["tailcall"].llvm


@pytest.mark.parametrize("one", CONFIGURATIONS, ids=lambda one: one.key)
def test_no_build_asks_for_a_package_the_common_list_already_has(one):
    assert not set(one.packages) & set(configs.COMMON_PACKAGES)


@pytest.mark.parametrize("one", CONFIGURATIONS, ids=lambda one: one.key)
def test_the_package_line_is_sorted_and_has_no_repeats(one):
    """It goes straight into an apt command, and a repeat there is a confusing warning."""
    line = configs.packages(one)
    assert list(line) == sorted(set(line))


def test_every_configure_flag_looks_like_one():
    for one in CONFIGURATIONS:
        for flag in one.flags:
            assert flag.startswith("--"), f"{one.key}: {flag}"
            assert " " not in flag


def test_both_architectures_have_a_runner():
    assert set(RUNNERS) == set(ARCHITECTURES)


def test_the_runners_are_native_rather_than_emulated():
    """qemu builds CPython about ten times slower, which makes a job an afternoon."""
    assert RUNNERS["arm64"].endswith("-arm")
    assert not RUNNERS["amd64"].endswith("-arm")


def test_the_matrix_is_every_build_on_every_architecture():
    grid = configs.matrix()
    assert len(grid) == len(CONFIGURATIONS) * len(ARCHITECTURES)
    assert len({(one["config"], one["arch"]) for one in grid}) == len(grid)


def test_the_matrix_carries_the_runner_so_the_workflow_does_not_have_to_know():
    for one in configs.matrix():
        assert one["runner"] == RUNNERS[one["arch"]]


def test_the_matrix_flags_are_one_string_because_that_is_what_a_build_arg_is():
    found = {one["config"]: one["flags"] for one in configs.matrix()}
    assert found["release"] == ""
    assert found["debug"] == "--with-pydebug --with-assertions"
