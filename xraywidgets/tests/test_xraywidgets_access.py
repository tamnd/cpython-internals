"""What a keyboard and a screen reader get, checked in the markup and the sheet.

Issue 69 asked for two things. The contrast half is measured in `pyxray/tests/test_theme.py`,
because the numbers come out of the palette and belong next to it. This file is the other
half, and it is honest about only doing the part a test can do.

A test can read the markup and say whether the pieces are there: real buttons rather than
styled divs, `aria-pressed` on anything that is on or off, a real textarea, a header row with
`scope`, a name on every group, a focus outline in the sheet, and a front end that puts focus
back where it was after redrawing. All of that is here.

A test cannot say whether tabbing through the widget in a browser lands somewhere sensible,
or whether a screen reader announces a toggle flipping. That needs somebody at a machine with
the software running, and it is issue 82 rather than being quietly counted as done because
the markup looked right.
"""

from __future__ import annotations

import re

import pytest

from pyxray import theme
from xraywidgets import Disassembler, Option, PipelineExplorer, PredictGate
from xraywidgets.style import PREFIX, stylesheet

CODE = "total = sum(values)"

QUESTION = dict(
    question="Which one is it?",
    options=[
        Option("The first one", correct=True, why="Because of the thing."),
        Option("The second one", why="Because of the other thing."),
    ],
)


def widgets():
    """One of each, rendered statically, which is the rendering with no JavaScript in it."""
    return {
        "disassembler": Disassembler(CODE),
        "pipeline": PipelineExplorer(CODE),
        "predict": PredictGate(**QUESTION),
    }


@pytest.fixture(params=sorted(widgets()))
def markup(request):
    return widgets()[request.param].render()


def test_nothing_that_can_be_pressed_is_a_styled_div(markup):
    """A div with a click handler is invisible to the tab key and silent to a screen reader."""
    for suspect in re.findall(r"<div[^>]*>", markup):
        assert "onclick" not in suspect
        # The class ends there, so this does not trip over the `xw-toggles` row that holds
        # the buttons or the `xw-options` row that holds the answers.
        assert f'{PREFIX}-toggle"' not in suspect
        assert f'{PREFIX}-option"' not in suspect


def test_everything_pressable_is_a_button_that_says_whether_it_is_on(markup):
    for button in re.findall(r"<button[^>]*>", markup):
        assert 'type="button"' in button
        assert "aria-pressed=" in button


def test_a_group_of_controls_has_a_name():
    """A group announced as the word group and nothing else is worse than no group at all."""
    for one in widgets().values():
        for group in re.findall(r'<div[^>]*role="group"[^>]*>', one.render()):
            assert "aria-label=" in group


def test_the_source_box_is_a_textarea_when_it_can_be_typed_into():
    """Not a contenteditable div, which a screen reader does not announce as somewhere to type."""
    live = Disassembler(CODE).markup(Disassembler(CODE).state(), live=True)
    assert "<textarea" in str(live)
    assert "contenteditable" not in str(live)


def test_a_table_announces_its_columns_and_has_a_name():
    markup = Disassembler(CODE).render()
    assert "<thead>" in markup
    headings = re.findall(r"<th\b[^>]*>", markup)
    assert headings
    assert all('scope="col"' in one for one in headings)
    assert re.search(r'<table[^>]*aria-label="[^"]+"', markup)


def test_a_button_that_does_nothing_says_so_rather_than_looking_live():
    """The static rendering disables its toggles. A live looking dead button wastes a press."""
    assert "disabled" in Disassembler(CODE).render()


@pytest.mark.parametrize("control", ["toggle", "option", "source", "reveal summary"])
def test_every_control_has_a_focus_outline(control):
    """Present in the sheet is not the same as visible, but absent in the sheet is fatal."""
    sheet = stylesheet()
    assert f".{PREFIX}-{control}:focus-visible" in sheet
    block = sheet.split(f".{PREFIX}-{control}:focus-visible")[1].split("}")[0]
    assert "outline:" in block
    assert "outline-offset:" in block


def test_the_focus_outline_is_not_removed_anywhere():
    """One `outline: none` in a sheet is enough to make the whole thing unusable by keyboard."""
    assert "outline: none" not in stylesheet()
    assert "outline: 0" not in stylesheet()


def test_the_focus_outline_is_the_same_colour_in_both_themes():
    """It is checked against both pages in `test_theme.py`, so it must not move between them."""
    sheet = stylesheet()
    assert sheet.count(f"--{PREFIX}-focus-stroke:") == 1
    assert f"--{PREFIX}-focus-stroke" not in sheet.split("prefers-color-scheme")[1]


def test_the_edge_of_a_control_is_not_the_faint_rule_colour():
    """`LINE` is 1.5:1 against white. A button drawn in it is a button nobody can find."""
    sheet = stylesheet()
    for rule in [f".{PREFIX}-toggle {{", f".{PREFIX}-option {{"]:
        block = sheet.split(rule)[1].split("}")[0]
        assert f"var(--{PREFIX}-edge)" in block
        assert f"var(--{PREFIX}-line)" not in block


def test_words_on_a_coloured_fill_are_written_as_a_colour_and_not_a_variable():
    """The fills do not move between themes. Any variable used there would, and would break.

    This is the failure that would not show up in a screenshot taken on a light machine: a
    reader whose system is set to dark gets pale grey text on a pale blue chip.
    """
    sheet = stylesheet()
    for name, tone in theme.TONES.items():
        block = sheet.split(f".{PREFIX}-{name} {{")[1].split("}")[0]
        assert f"color: {tone.text};" in block
        # Anchored, so `border-color: var(...)` is not read as the text colour. The border
        # is allowed to be a variable, because it does not move between themes either.
        assert not re.search(r"(?<![-\w])color: var\(", block)


def test_the_front_end_puts_focus_back_after_it_redraws():
    """Replacing innerHTML throws focus away, which makes a widget unusable without a mouse."""
    script = Disassembler.esm()
    assert "remember(root)" in script
    assert "restore(root, saved)" in script
    assert "target.focus()" in script


def test_focus_can_be_found_again_for_a_toggle_and_not_only_for_the_source_box():
    """The caret was the obvious case. A button dropping you to the top of the page was not."""
    script = Disassembler.esm()
    handles = re.search(r"const HANDLES = \[([^\]]*)\]", script)
    assert handles
    assert {"role", "flag", "option"} <= set(re.findall(r'"([a-z]+)"', handles.group(1)))


def test_tab_in_the_source_box_indents_rather_than_trapping_the_keyboard():
    """Tab is overridden inside the textarea, so this checks the escape hatch is still there.

    Shift and Tab returns early, which is what stops the box from being a keyboard trap. A
    reader who tabs in has to be able to tab back out, and without that early return the only
    way out would be the mouse.
    """
    script = Disassembler.esm()
    assert 'if (event.key !== "Tab" || event.shiftKey) return;' in script


def test_colour_is_never_the_only_signal_on_a_chip():
    """Enforced in `parts.chip`, checked here on the widgets that actually draw chips."""
    pattern = rf'<span class="{PREFIX}-chip[^"]*"[^>]*>([^<]*)</span>'
    for one in widgets().values():
        for chip in re.findall(pattern, one.render()):
            assert chip.strip()
