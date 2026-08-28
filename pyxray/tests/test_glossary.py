"""Tests for the glossary.

Most of these check the things that go wrong quietly. A cross reference to a term somebody
renamed still looks like a link and goes nowhere. An anchor computed with the wrong slug
rule looks right in the source and lands at the top of the page. And a generated file that
is committed drifts from the thing that generates it the first time somebody is in a hurry.

The one that matters most is the last: `GLOSSARY.md` is generated, so the committed copy has
to be compared against the module in CI rather than trusted.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from pyxray import glossary

ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The characters a term name is allowed to use. Anything else and GitHub's slug rule and
#: ours stop agreeing, which gives you links that look right and go nowhere.
ALLOWED = re.compile(r"^[A-Za-z0-9_ ]+$")


@pytest.mark.parametrize("term", glossary.TERMS, ids=lambda term: term.name)
def test_every_term_has_both_a_short_line_and_a_paragraph(term):
    assert term.short.endswith(".")
    assert len(term.long.split()) > 25


@pytest.mark.parametrize("term", glossary.TERMS, ids=lambda term: term.name)
def test_term_names_stay_inside_the_characters_anchors_survive(term):
    assert ALLOWED.match(term.name)


@pytest.mark.parametrize("term", glossary.TERMS, ids=lambda term: term.name)
def test_every_cross_reference_points_at_a_term_that_exists(term):
    for other in term.see:
        assert glossary.get(other).name == other


@pytest.mark.parametrize("term", glossary.TERMS, ids=lambda term: term.name)
def test_nothing_points_at_itself(term):
    assert term.name not in term.see


def test_no_term_is_defined_twice():
    names = [term.name.lower() for term in glossary.TERMS]
    assert len(names) == len(set(names))


def test_the_anchor_rule_keeps_underscores_and_loses_spaces():
    # GitHub lowercases, drops punctuation and turns spaces into hyphens, but it leaves
    # underscores alone. Getting that backwards is the way to produce a glossary full of
    # links that all land at the top of the page.
    assert glossary.anchor("EXTENDED_ARG") == "extended_arg"
    assert glossary.anchor("PEG parser") == "peg-parser"
    assert glossary.anchor("Argument Clinic") == "argument-clinic"


def test_looking_up_a_term_does_not_care_about_case():
    assert glossary.get("Pointer") is glossary.get("pointer")


def test_asking_for_a_term_that_is_not_there_raises():
    with pytest.raises(KeyError, match="no glossary entry"):
        glossary.get("monad")


def test_a_link_is_absolute_because_colab_cannot_resolve_a_relative_one():
    url = glossary.link("code object")
    assert (
        url
        == "[code object](https://github.com/tamnd/cpython-internals/blob/main/GLOSSARY.md#code-object)"
    )


def test_a_link_can_carry_the_words_the_sentence_needed():
    assert glossary.link("oparg", "the argument byte").startswith("[the argument byte](")


def test_the_index_is_alphabetical_and_complete():
    assert glossary.names() == sorted(glossary.names())
    assert len(glossary.names()) == len(glossary.TERMS)


def test_the_committed_glossary_matches_the_module():
    # It is generated and also committed, because a reader wants to click a link and read
    # it rather than run a build first. Anything generated and committed drifts unless
    # something checks, so this is the something.
    committed = (ROOT / glossary.PATH).read_text(encoding="utf-8")
    assert committed == glossary.markdown()


def test_the_glossary_has_no_dashes_the_style_guide_bans():
    # Written as escapes rather than as the characters themselves, because ruff flags a
    # literal one of these as ambiguous, and a test for a rule should not break the rule.
    assert "\u2014" not in glossary.markdown()
    assert "\u2013" not in glossary.markdown()


def test_every_group_has_terms_in_it():
    for group in glossary.GROUPS:
        assert group.terms


def test_the_terms_a_lesson_already_leans_on_are_all_here():
    # These are the words the twelve written lessons use without stopping to define, which
    # is the whole reason the glossary exists. If one goes missing the reader is stranded.
    wanted = [
        "abstract syntax tree",
        "bytecode",
        "cell",
        "code object",
        "constant folding",
        "exception table",
        "frame",
        "inline cache",
        "reference count",
        "specialization",
        "symbol table",
        "token",
        "value stack",
    ]
    for name in wanted:
        assert glossary.get(name)
