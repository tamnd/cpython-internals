"""What counts as noise and what counts as a version difference.

Half of these tests exist to pin down what is *not* normalised. A normaliser that is too
keen passes everything, and a comparison that passes everything is worse than no
comparison at all because somebody will trust it.
"""

from __future__ import annotations

from nbversion.normalise import outputs, text


def stream(body):
    return {"output_type": "stream", "name": "stdout", "text": body}


def result(plain):
    return {"output_type": "execute_result", "data": {"text/plain": plain}}


def test_an_address_becomes_a_placeholder():
    assert text("<object at 0x7f9c1a2b3c40>") == "<object at 0xADDRESS>"


def test_a_short_hex_number_is_left_alone():
    """`0x64` in a lesson about opcode arguments is content, not an address."""
    assert text("oparg 0x64") == "oparg 0x64"


def test_two_different_addresses_become_the_same_placeholder():
    assert text("0x7f9c1a2b3c40 0xaabbccddee11") == "0xADDRESS 0xADDRESS"


def test_an_absolute_path_becomes_a_placeholder():
    assert text("<module 'dis' from '/opt/py/lib/dis.py'>") == "<module 'dis' from 'PATH'>"


def test_a_windows_path_becomes_a_placeholder():
    assert text(r"C:\Users\a\lib.py") == "PATH"


def test_a_citation_is_not_a_path_because_it_has_no_leading_slash():
    assert text("Python/ceval.c:1213") == "Python/ceval.c:1213"


def test_a_temporary_name_becomes_a_placeholder():
    assert text("/tmp/tmpab12cd/x") == "PATH"


def test_a_duration_becomes_a_placeholder():
    assert text("took 12.5 ms") == "took DURATION"


def test_a_bare_number_is_not_a_duration():
    assert text("28 bytes") == "28 bytes"


def test_a_number_of_seconds_written_without_a_space_is_still_a_duration():
    assert text("4.0s") == "DURATION"


def test_an_opcode_name_survives_because_that_is_the_whole_point():
    body = "  2  LOAD_FAST  0 (x)"
    assert text(body) == body


def test_a_size_survives_because_that_is_also_the_point():
    assert text("sys.getsizeof(1) == 28") == "sys.getsizeof(1) == 28"


def test_trailing_blank_lines_are_dropped():
    assert text("a\nb\n\n\n") == "a\nb"


def test_trailing_spaces_on_a_line_are_dropped():
    assert text("a   \nb\t") == "a\nb"


def test_a_cell_with_no_output_is_the_empty_string():
    assert outputs({"outputs": []}) == ""


def test_stream_text_arrives_as_a_list_of_lines_with_the_newlines_on():
    assert outputs({"outputs": [stream(["one\n", "two\n"])]}) == "one\ntwo"


def test_stream_text_also_arrives_as_one_string():
    assert outputs({"outputs": [stream("one\ntwo\n")]}) == "one\ntwo"


def test_a_blank_line_survives_the_kernel_splitting_the_output():
    """The kernel breaks a cell's stdout into chunks and where it breaks is a race.

    Two stream outputs with the break landing on a blank line the cell printed on purpose
    have to read the same as one stream output holding the lot, or a cell differs between
    two interpreters on nothing, and differently every run.
    """
    whole = {"outputs": [stream("one\n\ntwo\n")]}
    split = {"outputs": [stream("one\n"), stream("\ntwo\n")]}
    assert outputs(split) == outputs(whole) == "one\n\ntwo"


def test_a_stream_broken_in_three_reads_as_one():
    pieces = {"outputs": [stream("a\n"), stream("b\n"), stream("c\n")]}
    assert outputs(pieces) == "a\nb\nc"


def test_a_result_between_two_streams_still_separates_them():
    cell = {"outputs": [stream("before\n\n"), result("value"), stream("after\n")]}
    assert outputs(cell) == "before\nvalue\nafter"


def test_several_outputs_are_joined_in_order():
    cell = {"outputs": [stream("printed\n"), result("returned")]}
    assert outputs(cell) == "printed\nreturned"


def test_an_image_is_reduced_to_its_mime_types():
    cell = {"outputs": [{"output_type": "display_data", "data": {"image/png": "aGk="}}]}
    assert outputs(cell) == "<image/png>"


def test_a_rich_output_with_a_text_fallback_uses_the_text():
    data = {"image/png": "aGk=", "text/plain": "<Figure>"}
    cell = {"outputs": [{"output_type": "display_data", "data": data}]}
    assert outputs(cell) == "<Figure>"


def test_an_error_keeps_the_exception_and_the_message():
    error = {"output_type": "error", "ename": "TypeError", "evalue": "no", "traceback": ["x"]}
    assert outputs({"outputs": [error]}) == "TypeError: no"


def test_an_error_drops_the_traceback():
    error = {
        "output_type": "error",
        "ename": "ValueError",
        "evalue": "bad",
        "traceback": ["  File /opt/py/x.py, line 3", "ValueError: bad"],
    }
    assert "File" not in outputs({"outputs": [error]})
