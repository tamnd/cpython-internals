"""The prediction gate, and the rule it exists to enforce: every option gets an explanation."""

from __future__ import annotations

import pytest

from xraywidgets import Option, PredictGate

FOLDING = dict(
    question="The compiler sees 6 * 7. What ends up in the code object?",
    options=[
        Option(
            "A BINARY_OP that multiplies at run time",
            why="That is what happens for a * b, where the compiler cannot know the values. Here it does know them.",
        ),
        Option(
            "The constant 42",
            correct=True,
            why="Both sides are literals, so the compiler does the multiplication once while compiling and stores the result.",
        ),
        Option(
            "Both, in case something rebinds one of them",
            why="Nothing can rebind a literal. There is no name here at all, so there is nothing that could change.",
        ),
    ],
)


@pytest.fixture
def gate():
    return PredictGate(**FOLDING)


def test_an_option_needs_a_reason():
    with pytest.raises(ValueError, match="not worth offering"):
        Option("Something plausible", why="  ")


def test_an_option_needs_something_to_click_on():
    with pytest.raises(ValueError, match="something to click on"):
        Option("", why="a reason")


def test_the_right_answer_needs_a_reason_too():
    with pytest.raises(ValueError, match="not worth offering"):
        Option("The right one", why="", correct=True)


def test_a_gate_needs_exactly_one_right_answer():
    with pytest.raises(ValueError, match="0 correct options"):
        PredictGate(
            question="Which?",
            options=[Option("a", why="no"), Option("b", why="no")],
        )


def test_a_gate_with_two_right_answers_is_refused():
    with pytest.raises(ValueError, match="2 correct options"):
        PredictGate(
            question="Which?",
            options=[Option("a", why="yes", correct=True), Option("b", why="yes", correct=True)],
        )


def test_a_gate_with_one_option_is_not_a_question():
    with pytest.raises(ValueError, match="not a question"):
        PredictGate(question="Which?", options=[Option("a", why="yes", correct=True)])


def test_a_gate_needs_a_question():
    with pytest.raises(ValueError, match="needs a question"):
        PredictGate(question="   ", options=list(FOLDING["options"]))


def test_the_answer_is_the_option_marked_correct(gate):
    assert gate.answer == 1


def test_the_still_picture_asks_before_it_tells(gate):
    markup = gate.render()
    assert markup.index("<details") < markup.index("compiler does the multiplication")


def test_the_still_picture_gates_with_details_and_not_javascript(gate):
    assert "<details" in gate.render()
    assert "<script" not in gate.render()


def test_the_still_picture_does_not_offer_buttons_that_do_nothing(gate):
    assert "data-option" not in gate.render()


def test_the_live_picture_offers_a_button_per_option(gate):
    html = gate.view()["html"]
    for index in range(len(gate.options)):
        assert f'data-option="{index}"' in html


def test_nothing_is_revealed_before_the_reader_picks(gate):
    assert "compiler does the multiplication" not in gate.view()["html"]


def test_picking_reveals_every_explanation_and_not_only_the_one_picked(gate):
    gate.chosen = 0
    html = gate.view()["html"]
    for one in gate.options:
        assert one.why[:40] in html


def test_a_wrong_pick_is_told_so_in_words_and_not_only_in_a_colour(gate):
    gate.chosen = 0
    assert "not this time" in gate.view()["html"]


def test_a_right_pick_is_told_so(gate):
    gate.chosen = gate.answer
    assert "that is the one" in gate.view()["html"]


def test_the_option_the_reader_picked_is_marked_as_theirs(gate):
    gate.chosen = 2
    html = gate.view()["html"]
    assert "what you picked" in html
    assert 'data-option="2" aria-pressed="true"' in html


def test_the_right_answer_is_marked_whether_or_not_it_was_picked(gate):
    gate.chosen = 0
    assert "the answer" in gate.view()["html"]


def test_the_check_line_is_shown_once_the_answer_is_out():
    gate = PredictGate(**FOLDING, check="dis.dis(compile('6 * 7', '<here>', 'eval'))")
    gate.chosen = 0
    assert "dis.dis" in gate.view()["html"]
    assert "Run this if you want to see it for yourself" in gate.view()["html"]


def test_a_gate_without_a_check_line_does_not_leave_an_empty_box(gate):
    gate.chosen = 0
    assert 'class="xw-source"' not in gate.view()["html"]


def test_the_key_is_stable_across_two_gates_asking_the_same_question():
    assert PredictGate(**FOLDING).key == PredictGate(**FOLDING).key


def test_two_different_questions_get_different_keys(gate):
    other = PredictGate(question="Something else entirely?", options=list(FOLDING["options"]))
    assert gate.key != other.key


def test_the_key_is_named_after_the_package_so_it_does_not_collide(gate):
    assert gate.key.startswith("xw-predict-")


def test_the_question_is_escaped():
    gate = PredictGate(question="Is 1 < 2?", options=list(FOLDING["options"]))
    assert "&lt;" in gate.render()


def test_the_front_end_stores_the_answer_and_sends_nothing_anywhere():
    module = PredictGate.esm()
    assert "localStorage" in module
    for word in ("fetch(", "XMLHttpRequest", "navigator.sendBeacon"):
        assert word not in module


def test_the_front_end_survives_a_browser_that_refuses_to_store_anything():
    assert PredictGate.esm().count("catch") >= 2
