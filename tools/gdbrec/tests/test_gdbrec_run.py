"""Turning one batch run of gdb back into one block of output per command.

Nothing here starts a container. What is worth testing without Docker is the part that reads
gdb's output, because that is where a quiet mistake turns into a transcript that looks fine
and has every command's output under the wrong heading.
"""

from __future__ import annotations

import pytest

from gdbrec.run import MARKER, Failed, script_for, split, trimmed
from gdbrec.sessions import PROGRAM, TWO_STACKS, Session, Step

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


def printed(*blocks: list[str], noise: str = "") -> str:
    """What gdb's batch output looks like, with the markers this code puts in it."""
    lines = [noise] if noise else []
    for number, block in enumerate(blocks, start=1):
        lines.append(MARKER.format(number=number))
        lines.extend(block)
    lines.append(MARKER.format(number=len(blocks) + 1))
    return "\n".join(lines) + "\n"


def test_each_command_gets_its_own_output():
    assert split(printed(["one"], ["two", "three"]), 2) == [["one"], ["two", "three"]]


def test_anything_gdb_said_before_the_first_command_is_dropped():
    """Loading symbols and reading libthread_db is not something anybody typed."""
    noise = "Reading symbols from /usr/local/bin/python3..."
    assert split(printed(["one"], ["two"], noise=noise), 2) == [["one"], ["two"]]


def test_a_command_that_printed_nothing_gets_an_empty_block():
    """Rather than being dropped. A command whose point is that it says nothing is a command."""
    assert split(printed([], ["two"]), 2) == [[], ["two"]]


def test_the_blank_lines_the_markers_leave_behind_are_trimmed():
    """The echo puts one either side so the marker stays on a line of its own, and neither is
    part of what the command printed."""
    assert split(printed(["", "one", ""], ["two"]), 2) == [["one"], ["two"]]


def test_a_blank_line_in_the_middle_of_output_is_kept():
    """gdb puts one between the stop message and the source line, and it is part of the shape."""
    assert split(printed(["one", "", "two"]), 1) == [["one", "", "two"]]


def test_a_session_that_stopped_early_is_a_failure_rather_than_a_short_transcript():
    """This is the whole reason the markers are counted. Without the count, a session gdb
    abandoned halfway comes back looking like one where the last commands printed nothing."""
    with pytest.raises(Failed, match="gdb stopped before the end"):
        split(printed(["one"], ["two"]), 3)


def test_trimmed_leaves_a_block_that_is_all_blank_lines_empty():
    assert trimmed(["", "  ", ""]) == []


def test_the_script_writes_the_program_the_session_asked_for():
    assert SESSION.program.rstrip() in script_for(SESSION)
    assert f"cat > {PROGRAM}" in script_for(SESSION)


def test_the_script_runs_every_command_in_order():
    body = script_for(SESSION)
    assert body.index("run /tmp/program.py") < body.index("bt 2")


def test_the_script_turns_off_the_two_things_that_would_hang_a_batch_run():
    """With pagination on, gdb stops every twenty four lines waiting for a keypress."""
    assert "set pagination off" in script_for(SESSION)
    assert "set confirm off" in script_for(SESSION)


def test_the_marker_is_not_something_a_backtrace_would_ever_print():
    """It is the only thing separating one command's output from the next one's."""
    for step in TWO_STACKS.script:
        assert MARKER.format(number=1) not in step.command
