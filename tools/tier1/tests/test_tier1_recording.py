"""Reading and writing a recording, and what two of them are allowed to disagree about."""

from __future__ import annotations

import pytest

from tier1.experiments import EXPERIMENTS, Experiment
from tier1.recording import Recording, Unreadable, comparable, differences, show

IMAGE = "ghcr.io/tamnd/cpython-internals/cpython:debug@sha256:" + "a" * 64


def one(**changed) -> Recording:
    """A recording with nothing wrong with it, which the tests then break one thing at a time."""
    fields = {
        "slug": "t99-a-question",
        "title": "A question",
        "asks": "Does anything happen?",
        "needs": "it needs a build nobody has",
        "lesson": "T99",
        "build": "debug",
        "image": IMAGE,
        "interpreter": "3.15.0rc1 (main, Jan 1 2026, 00:00:00) [GCC 14.2.0]",
        "recorded": "2026-01-01",
        "program": 'print("~ a measurement: 1")\nprint("a fact")\n',
        "output": ["~ a measurement: 1", "a fact"],
    }
    return Recording(**{**fields, **changed})


def test_a_recording_survives_being_written_and_read_back():
    """The file is markdown for a person and is also parsed, so it has to be both."""
    there = Recording.from_markdown(one().slug, one().as_markdown())
    assert there == one()


def test_the_program_comes_back_exactly_as_it_went_in():
    """The program is the thing the output is an answer to, so a lost blank line matters."""
    program = 'x = 1\n\n\nif x:\n    print("~ two blank lines above: 1")\n'
    there = Recording.from_markdown("t99-a-question", one(program=program).as_markdown())
    assert there.program == program


def test_a_file_with_no_title_is_refused():
    with pytest.raises(Unreadable, match="the first line should be the title"):
        Recording.from_markdown("t99-a-question", "not a title\n")


def test_a_file_missing_a_field_says_which_one():
    text = one().as_markdown().replace("- Image: " + IMAGE + "\n", "")
    with pytest.raises(Unreadable, match="no Image line"):
        Recording.from_markdown("t99-a-question", text)


def test_a_program_with_a_fence_in_it_is_refused_rather_than_written():
    """It would close the block early and the file would parse as something else entirely."""
    with pytest.raises(Unreadable, match="a fence"):
        one(program="print('```')\n").as_markdown()


def test_a_measured_line_is_compared_by_its_label():
    assert comparable("~ a measurement: 1") == comparable("~ a measurement: 4")


def test_a_line_that_is_not_measured_is_compared_by_all_of_it():
    assert comparable("a fact: 1") != comparable("a fact: 4")


def test_a_measured_number_moving_is_not_a_difference():
    """The whole reason the `~` prefix exists. This number moves between runs of one image."""
    assert differences(one(), one(output=["~ a measurement: 44", "a fact"])) == []


def test_a_fact_changing_is_a_difference():
    found = differences(one(), one(output=["~ a measurement: 1", "another fact"]))
    assert found == ["was 'a fact' and is now 'another fact'"]


def test_a_line_going_missing_is_a_difference_rather_than_a_line_that_differs():
    """A program that stopped printing its last line has stopped working, not drifted."""
    found = differences(one(), one(output=["~ a measurement: 1"]))
    assert found == ["printed 2 lines before and 1 now"]


def test_a_different_image_is_a_difference_even_when_the_output_matches():
    found = differences(one(), one(image=IMAGE.replace("a" * 64, "b" * 64)))
    assert len(found) == 1 and found[0].startswith("recorded against")


def test_a_different_interpreter_is_a_difference():
    found = differences(one(), one(interpreter="3.14.7 (main, Jan 1 2026, 00:00:00)"))
    assert found == ["recorded on Python 3.15.0rc1 and ran on 3.14.7"]


def test_a_recording_of_another_program_is_a_problem():
    """The output is an answer, and an answer under the wrong question is worse than none."""
    experiment = Experiment(
        slug="t99-a-question",
        lesson="T99",
        title="A question",
        asks="Does anything happen?",
        needs="it needs a build nobody has",
        build="debug",
        program='print("~ something else: 1")\n',
    )
    found = one().problems(experiment)
    assert len(found) == 1 and "not the one in the catalogue" in found[0]


def test_a_measurement_with_no_label_is_a_problem():
    """Its number is not compared, so with no label there is nothing left to compare at all."""
    found = one(output=["~ 41", "a fact"]).problems(
        Experiment(
            slug="t99-a-question",
            lesson="T99",
            title="A question",
            asks="Does anything happen?",
            needs="it needs a build nobody has",
            build="debug",
            program=one().program,
        )
    )
    assert len(found) == 1 and "has no label" in found[0]


def test_what_a_lesson_shows_holds_the_program_the_numbers_and_the_image(tmp_path):
    one().write(tmp_path)
    said = show("t99-a-question", tmp_path)
    assert "Does anything happen?" in said
    assert "a fact" in said
    assert IMAGE in said


def test_showing_a_recording_nobody_has_taken_says_how_to_take_it(tmp_path):
    with pytest.raises(Unreadable, match="just build-tier1"):
        show("t99-a-question", tmp_path)


@pytest.mark.parametrize("experiment", EXPERIMENTS, ids=lambda one: one.slug)
def test_every_experiment_in_the_catalogue_is_well_formed(experiment):
    assert experiment.problems() == []
