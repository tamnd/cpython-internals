from __future__ import annotations

import sys
import sysconfig
import types

import pytest

from pyxray import build


@pytest.fixture(scope="module")
def info():
    return build.current()


def test_reports_the_version_it_is_actually_running_on(info):
    assert info.version == sys.version.split()[0]
    assert info.version_info == tuple(sys.version_info)


def test_detects_the_debug_build_the_same_way_the_interpreter_does(info):
    assert info.debug == hasattr(sys, "gettotalrefcount")


def test_detects_free_threading_from_the_build_configuration(info):
    assert info.free_threaded == bool(sysconfig.get_config_var("Py_GIL_DISABLED"))


def test_free_threaded_and_gil_enabled_agree(info):
    """A GIL build always has the GIL on. A free threaded build usually does not."""
    if not info.free_threaded:
        assert info.gil_enabled


def test_jit_cannot_be_active_unless_it_is_available(info):
    if not info.jit_available:
        assert not info.jit_enabled
        assert not info.jit_active


def test_is_pinned_is_true_exactly_on_the_pinned_release(info):
    expected = sys.version_info[:3] == (3, 15, 0) and sys.version_info[3] == "candidate"
    assert info.is_pinned == expected


def test_a_non_pinned_build_says_so_in_the_banner(info):
    """The reader must never be left guessing which interpreter produced an output."""
    text = build.banner(info)
    assert info.version in text
    if not info.is_pinned_minor:
        assert "3.15" in text


def test_a_debug_build_warns_against_taking_timings(info):
    if info.debug:
        assert any("performance" in note for note in info.warnings())


def test_capabilities_are_all_booleans(info):
    assert info.capabilities
    assert all(isinstance(value, bool) for value in info.capabilities.values())


def test_a_probe_that_blows_up_reports_an_absence():
    """A missing capability must never take the notebook down with it."""
    assert build._probe(lambda: 1 / 0) is False
    assert build._probe(lambda: True) is True
    assert build._probe(lambda: None) is False


def test_the_compiler_hooks_are_present_on_a_stock_interpreter(info):
    """The claim in the README that _testinternalcapi ships on stock builds.

    Twelve ways of getting a Python were asked this, and the table is in
    probes/distributions. Most of them say yes. If this starts failing somewhere new, that
    is not a broken test, it is a row of that table changing and it needs writing down.
    """
    assert info.capabilities["testinternalcapi"], (
        "no _testinternalcapi on this build, which changes the browser tier story"
    )


def test_the_capability_means_the_functions_and_not_just_the_module(monkeypatch):
    """The macOS system Python, 3.9, has the module and none of the three functions.

    A banner that called that available would be telling the reader least able to work it out
    the opposite of the truth.
    """
    monkeypatch.setitem(sys.modules, "_testinternalcapi", types.SimpleNamespace())
    assert build.capabilities()["testinternalcapi"] is False


def test_the_banner_and_the_compiler_agree_about_which_functions_matter():
    """Two lists, written out separately so build.py can import nothing. Kept in step here."""
    from pyxray import compiler

    assert build.COMPILER_HOOKS == compiler.HOOKS


def test_missing_lists_only_absent_capabilities(info):
    missing = info.missing()
    assert missing == sorted(missing)
    assert all(not info.capabilities[name] for name in missing)


def test_summary_is_one_line(info):
    assert "\n" not in info.summary()


def test_banner_leads_with_the_summary(info):
    assert build.banner(info).splitlines()[0] == info.summary()
