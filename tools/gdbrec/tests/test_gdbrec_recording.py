"""Reading and writing a transcript, and what two runs of one session may disagree about."""

from __future__ import annotations

from dataclasses import replace

import pytest

from gdbrec.recording import (
    Printed,
    Recording,
    Unreadable,
    comparable,
    differences,
    show,
    steps_of,
)
from gdbrec.sessions import Session, Step

IMAGE = "ghcr.io/tamnd/cpython-internals/cpython:debug@sha256:" + "a" * 64

SESSION = Session(
    slug="b99-a-question",
    lesson="B99",
    title="A question",
    asks="Does anything happen?",
    needs="a release build inlines the frame this is about",
    build="debug",
    program="print(1)\n",
    script=(
        Step("run /tmp/program.py", "Start it."),
        Step("bt 2", "The top two frames."),
    ),
)


def one(**changed) -> Recording:
    """A transcript with nothing wrong with it, which the tests break one thing at a time."""
    fields = {
        "slug": SESSION.slug,
        "title": SESSION.title,
        "asks": SESSION.asks,
        "needs": SESSION.needs,
        "lesson": SESSION.lesson,
        "build": SESSION.build,
        "arch": "arm64",
        "image": IMAGE,
        "interpreter": "3.15.0rc1 (main, Jan 1 2026, 00:00:00) [GCC 14.2.0]",
        "debugger": "GNU gdb (Debian 16.3-1) 16.3",
        "recorded": "2026-01-01",
        "program": SESSION.program,
        "steps": [
            Printed("run /tmp/program.py", "Start it.", ["1", "[Inferior 1 exited normally]"]),
            Printed("bt 2", "The top two frames.", ["#0  one () at a.c:1", "#1  0x1234 in two ()"]),
        ],
    }
    return Recording(**{**fields, **changed})


def test_a_transcript_survives_being_written_and_read_back():
    """The file is markdown for a person and is also parsed back, so it has to be both."""
    assert Recording.from_markdown(one().slug, one().as_markdown()) == one()


def test_the_program_comes_back_exactly_as_it_went_in():
    """A lost blank line would move every line number the backtrace under it talks about."""
    program = "import ctypes\n\n\ndef go():\n    return ctypes.string_at(0)\n"
    there = Recording.from_markdown(SESSION.slug, one(program=program).as_markdown())
    assert there.program == program


def test_a_command_that_printed_nothing_still_gets_a_heading():
    """Some gdb commands say nothing on purpose, and dropping them renumbers the rest."""
    quiet = [Printed("set listsize 20", "Show more source.", [""]), *one().steps]
    there = Recording.from_markdown(SESSION.slug, one(steps=quiet).as_markdown())
    assert [step.command for step in there.steps] == [step.command for step in quiet]


def test_a_file_with_no_title_is_refused():
    with pytest.raises(Unreadable, match="the first line should be the title"):
        Recording.from_markdown(SESSION.slug, "not a title\n")


def test_a_file_missing_a_field_says_which_one():
    text = one().as_markdown().replace(f"- Image: {IMAGE}\n", "")
    with pytest.raises(Unreadable, match="no Image line"):
        Recording.from_markdown(SESSION.slug, text)


def test_output_with_a_fence_in_it_is_refused_rather_than_written():
    """It would close the block early and the rest of the file would parse as something else."""
    fenced = [Printed("bt", "The stack.", ["```"])]
    with pytest.raises(Unreadable, match="a fence"):
        one(steps=fenced).as_markdown()


def test_headings_and_blocks_that_do_not_add_up_are_refused():
    text = one().as_markdown().replace("### 2. `bt 2`", "### 2. `bt 2`\n\n### 3. `py-bt`")
    with pytest.raises(Unreadable, match="cannot both be right"):
        Recording.from_markdown(SESSION.slug, text)


def test_an_address_may_move_between_runs():
    """Every run loads the program somewhere new, and no lesson is about where."""
    assert comparable("#1  0x0000aaaaaad2ed04 in run ()") == comparable("#1  0xffff7f2c in run ()")


def test_a_process_id_may_move_between_runs():
    assert comparable("process 4231 exited") == comparable("process 9 exited")


def test_an_offset_into_the_runtime_struct_may_move():
    """It shifts whenever anything earlier in _PyRuntime changes size, which is not the point."""
    was = "config=0xaaaa <_PyRuntime+144048>"
    now = "config=0xbbbb <_PyRuntime+144112>"
    assert comparable(was) == comparable(now)


def test_a_function_name_may_not_move():
    """This is the whole reason for recording: the shape of the stack is the lesson."""
    assert comparable("#1  0x1 in _PyEval_EvalFrameDefault ()") != comparable("#1  0x1 in run ()")


def test_two_runs_that_only_disagree_about_addresses_are_the_same_run():
    fresh = one(
        steps=[
            one().steps[0],
            Printed(
                "bt 2",
                "The top two frames.",
                [
                    "#0  one () at a.c:1",
                    "#1  0xffffabcd in two ()",
                ],
            ),
        ]
    )
    assert differences(one(), fresh) == []


def test_a_command_that_stopped_printing_a_line_is_a_difference():
    """Half a backtrace is the failure this whole check exists for, so it may not read as noise."""
    short = [one().steps[0], Printed("bt 2", "The top two frames.", ["#0  one () at a.c:1"])]
    found = differences(one(), one(steps=short))
    assert any("printed 2 line(s) and now prints 1" in said for said in found)


def test_a_run_on_another_architecture_is_not_compared_at_all():
    """The frames genuinely differ, so comparing them would only teach people to ignore this."""
    found = differences(one(), one(arch="amd64"))
    assert found == ["recorded on arm64, ran on amd64, which are not comparable"]


def test_a_run_against_another_image_is_a_difference():
    found = differences(one(), one(image=IMAGE.replace("a" * 64, "b" * 64)))
    assert any("ran against" in said for said in found)


def test_a_run_on_another_python_is_a_difference():
    fresh = one(interpreter="3.16.0 (main, Jan 1 2027, 00:00:00) [GCC 14.2.0]")
    found = differences(one(), fresh)
    assert any("ran on Python 3.16.0" in said for said in found)


def test_a_run_under_another_gdb_is_a_difference():
    """gdb decides how much of the stack survives the unwinder, so its version is part of this."""
    found = differences(one(), one(debugger="GNU gdb (Debian 17.1-1) 17.1"))
    assert any("ran with" in said for said in found)


def test_a_transcript_matching_its_session_has_no_problems():
    assert one().problems(SESSION) == []


def test_a_transcript_of_a_program_nobody_runs_any_more_is_caught():
    found = one(program="print(2)\n").problems(SESSION)
    assert any("not the one in the catalogue" in said for said in found)


def test_a_transcript_of_commands_nobody_runs_any_more_is_caught():
    """Somebody changed the script and left the old output sitting underneath it."""
    stale = [one().steps[0], Printed("py-bt", "The top two frames.", ["nothing"])]
    found = one(steps=stale).problems(SESSION)
    assert any("somebody changed the script" in said for said in found)


def test_an_explanation_edited_in_the_file_rather_than_the_code_is_caught():
    """The file is generated, so an edit here is an edit the next build silently throws away."""
    edited = [one().steps[0], Printed("bt 2", "The top three frames.", one().steps[1].output)]
    found = one(steps=edited).problems(SESSION)
    assert any("edited by hand" in said for said in found)


def test_a_transcript_written_and_loaded_back_from_disk(tmp_path):
    one().write(tmp_path)
    assert Recording.load(SESSION.slug, "arm64", tmp_path) == one()
    assert Recording.recorded_arches(SESSION.slug, tmp_path) == ["arm64"]


def test_loading_something_never_recorded_says_how_to_record_it(tmp_path):
    with pytest.raises(Unreadable, match="run `just build-gdb`"):
        Recording.load(SESSION.slug, "amd64", tmp_path)


def test_show_gives_back_the_steps_that_were_asked_for(tmp_path):
    one().write(tmp_path)
    later = show(SESSION.slug, "arm64", tmp_path, first=2)
    assert later.startswith("**2. `bt 2`**")
    assert "run /tmp/program.py" not in later


def test_show_keeps_the_real_numbering_across_a_gap(tmp_path):
    """A lesson puts its own paragraphs between two steps, and the reader has to be able to
    tell it is still one session rather than the start of another one."""
    one().write(tmp_path)
    assert show(SESSION.slug, "arm64", tmp_path, first=2).startswith("**2.")


def test_asking_for_a_step_that_is_not_there_says_how_many_there_are(tmp_path):
    one().write(tmp_path)
    with pytest.raises(Unreadable, match="there are 2"):
        show(SESSION.slug, "arm64", tmp_path, first=1, last=9)


def test_steps_of_gives_a_lesson_the_whole_session_to_lay_out_itself(tmp_path):
    one().write(tmp_path)
    assert [step.command for step in steps_of(SESSION.slug, "arm64", tmp_path)] == [
        "run /tmp/program.py",
        "bt 2",
    ]


def test_a_transcript_of_the_wrong_build_is_caught():
    found = one(build="release").problems(SESSION)
    assert any("wants debug" in said for said in found)


def test_a_transcript_filed_under_the_wrong_lesson_is_caught():
    found = one(lesson="B03").problems(replace(SESSION, lesson="B02"))
    assert any("belongs to B02" in said for said in found)
