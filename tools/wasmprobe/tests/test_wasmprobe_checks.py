"""The checks have to be well formed, and they have to actually run somewhere."""

from __future__ import annotations

import ast
import builtins

import pytest
from wasmprobe.checks import BY_KEY, CHECKS, INFO, NICE, TIER0, Check

WEIGHTS = {TIER0, NICE, INFO}


def test_keys_are_unique():
    keys = [check.key for check in CHECKS]
    assert len(keys) == len(set(keys))
    assert set(BY_KEY) == set(keys)


@pytest.mark.parametrize("check", CHECKS, ids=lambda check: check.key)
def test_shape(check: Check):
    assert check.weight in WEIGHTS
    assert check.question and not check.question.endswith(".")
    assert check.costs.endswith(".")
    assert "result" in check.source


@pytest.mark.parametrize("check", CHECKS, ids=lambda check: check.key)
def test_prose_has_no_dashes(check: Check):
    """The questions and the costs end up in a committed report, so the style rules apply."""
    for text in (check.question, check.costs, check.accepted):
        assert "\u2014" not in text
        assert "\u2013" not in text


def test_only_tier_zero_can_be_accepted():
    """Accepting a gap only means something for a check that would otherwise fail a build."""
    for check in CHECKS:
        if check.accepted:
            assert check.weight == TIER0


def test_accepted_checks_do_not_block():
    accepted = [check for check in CHECKS if check.accepted]
    assert accepted, "the point of the field is that at least one gap is known"
    assert not any(check.blocking for check in accepted)


def test_tier_zero_without_an_excuse_blocks():
    plain = [check for check in CHECKS if check.weight == TIER0 and not check.accepted]
    assert plain and all(check.blocking for check in plain)


@pytest.mark.parametrize("check", CHECKS, ids=lambda check: check.key)
def test_a_check_imports_what_it_uses(check: Check):
    """Nothing carries over, because a check that crashes leaves the next one a new runtime."""
    tree = ast.parse(check.source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import | ast.ImportFrom):
            imported.update(alias.asname or alias.name for alias in node.names)
    used = {
        node.value.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
    }
    assigned = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
    }
    assigned |= {node.name for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler)}
    assigned |= {
        node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef | ast.FunctionDef)
    }
    known = imported | assigned | set(dir(builtins))
    assert used <= known, f"{check.key} reaches for {sorted(used - known)} without importing it"


def test_a_check_parses():
    for check in CHECKS:
        ast.parse(check.source)
