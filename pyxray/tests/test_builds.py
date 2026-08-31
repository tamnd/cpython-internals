"""The five configurations, and reading a build's own settings back off it.

Most of these run against whatever interpreter is executing them, which is the point: this
module exists so a reader can ask their own Python what it is, and a test that only passed
on one build would be testing the wrong thing.
"""

from __future__ import annotations

import sys
import sysconfig

import pytest

from cpybuild.configs import BY_KEY as BUILT
from pyxray import builds
from pyxray.build import header


def test_the_five_here_are_the_five_the_workflow_actually_builds():
    assert set(builds.BY_KEY) == set(BUILT)


def test_every_configuration_carries_the_flags_the_builder_passes():
    for key, one in builds.BY_KEY.items():
        assert one.flags == BUILT[key].flags


def test_every_proof_is_the_one_the_publishing_workflow_runs_inside_the_image():
    for key, one in builds.BY_KEY.items():
        assert one.proof == BUILT[key].proof


def test_every_proof_runs_without_raising_on_whatever_is_executing_this():
    found = builds.matches()
    assert set(found) == set(builds.BY_KEY)
    assert all(isinstance(one, bool) for one in found.values())


def test_a_proof_that_cannot_run_is_a_no_rather_than_an_exception():
    assert builds._ask("no_such_name.at_all") is False


def test_identify_agrees_with_the_proofs_it_is_built_from():
    assert builds.identify() == [key for key, yes in builds.matches().items() if yes]


def test_the_debug_proof_is_the_one_thing_a_debug_build_has_that_others_do_not():
    assert ("debug" in builds.identify()) == hasattr(sys, "gettotalrefcount")


def test_the_free_threaded_proof_matches_what_the_test_suite_asks():
    wanted = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))
    assert ("freethreaded" in builds.identify()) == wanted


def test_release_and_debug_cannot_both_be_true_because_release_denies_the_others():
    found = builds.identify()
    assert not ("release" in found and "debug" in found)


def test_settings_covers_everything_in_the_list_and_nothing_else():
    assert [name for name, _, _ in builds.settings()] == [name for name, _ in builds.SETTINGS]


def test_a_setting_the_build_never_defined_reads_as_not_set_rather_than_none():
    assert all(value for _, value, _ in builds.settings())


def test_the_word_size_is_read_off_the_build_rather_than_guessed():
    found = dict((name, value) for name, value, _ in builds.settings())
    assert found["SIZEOF_VOID_P"] in {"4", "8"}


@pytest.mark.skipif(sys.platform == "win32", reason="Windows does not use configure")
def test_the_configure_line_is_split_into_arguments_rather_than_left_as_one_string():
    found = builds.configured()
    assert isinstance(found, list)
    assert all(" " not in one or "=" in one for one in found)


def test_options_keeps_the_flags_and_counts_what_it_dropped():
    chosen, rest = builds.options()
    assert all(one.startswith("--") for one in chosen)
    assert len(chosen) + rest == len(builds.configured())


def test_report_prints_all_five_builds_whether_or_not_you_are_on_one(capsys):
    builds.report()
    printed = capsys.readouterr().out
    for key in builds.BY_KEY:
        assert key in printed


def test_report_says_so_when_the_interpreter_is_none_of_the_five(capsys, monkeypatch):
    monkeypatch.setattr(builds, "identify", lambda: [])
    builds.report()
    assert "None of them, which is normal" in capsys.readouterr().out


def test_the_underscored_macros_are_the_ones_sysconfig_cannot_see():
    macros = header()
    if not macros:
        pytest.skip("this build did not install a pyconfig.h")
    assert all(name.startswith("_") for name in macros)
    assert all(sysconfig.get_config_var(name) is None for name in macros)


def test_a_tail_calling_build_is_found_through_the_header_and_not_through_sysconfig():
    from pyxray.build import current

    macros = header()
    if "_Py_TAIL_CALL_INTERP" not in macros:
        pytest.skip("this build was not built with --with-tail-call-interp")
    assert sysconfig.get_config_var("_Py_TAIL_CALL_INTERP") is None
    assert current().tail_call is (macros["_Py_TAIL_CALL_INTERP"] == "1")
