from __future__ import annotations

import ast

import pytest

from pyxray import trees

LINE = "answer = 6 * 7\n"

FUNCTION = "def f(a):\n    return a + answer\n"


def test_a_node_class_carries_its_own_asdl_declaration():
    """The docstring is not documentation somebody wrote and has to keep up to date.

    Parser/asdl_c.py reads Parser/Python.asdl and writes the declaration into the generated
    class, so this is the definition of the node type rather than a description of it.
    """
    assert trees.asdl(ast.BinOp) == "BinOp(expr left, operator op, expr right)"


def test_the_declaration_can_be_asked_for_with_a_node_rather_than_a_class():
    node = ast.parse("6 * 7").body[0].value
    assert trees.asdl(node) == trees.asdl(ast.BinOp)


def test_a_sum_type_lists_every_case_it_has():
    # The operators are a closed set, which is why an unknown operator is not a thing that
    # can reach the compiler.
    declaration = trees.asdl(ast.operator)
    assert declaration.startswith("operator = ")
    for case in ["Add", "Sub", "Mult", "FloorDiv"]:
        assert case in declaration


def test_fields_pair_every_name_with_the_type_it_holds():
    assert trees.fields(ast.BinOp) == [("left", "expr"), ("op", "operator"), ("right", "expr")]


def test_a_node_with_no_fields_has_no_fields():
    # Mult is a case, not a container. Readers expect it to hold the "*" somewhere.
    assert trees.fields(ast.Mult) == []


def test_an_outline_names_the_field_each_child_sits_in():
    text = trees.outline(LINE)
    assert "value: BinOp" in text
    assert "left: Constant 6" in text
    assert "right: Constant 7" in text


def test_an_outline_indents_a_child_further_than_its_parent():
    lines = {
        line.strip().split(":")[-1].strip(): len(line) - len(line.lstrip())
        for line in trees.outline(LINE).splitlines()
    }
    assert lines["BinOp"] < lines["Constant 6"]


def test_an_operator_is_shown_inline_rather_than_as_a_node_with_an_empty_body():
    assert "op: Mult" in trees.outline(LINE)


def test_an_outline_accepts_a_tree_as_well_as_a_string():
    assert trees.outline(ast.parse(LINE)) == trees.outline(LINE)


def test_a_function_outline_reaches_its_arguments():
    text = trees.outline(FUNCTION)
    assert "FunctionDef 'f'" in text
    assert "arg 'a'" in text


def test_parentheses_leave_no_trace_in_the_tree():
    assert trees.same_tree("answer = (6 * 7)", "answer = 6 * 7")


def test_spacing_and_comments_leave_no_trace_either():
    assert trees.same_tree("answer=6*7", "answer  =  6  *  7   # a note")


def test_precedence_does_leave_a_trace_because_it_is_the_shape():
    # The parentheses themselves are gone and what they did survives, which is the whole
    # distinction between a syntax tree and a record of what you typed.
    assert not trees.same_tree("x = 1 + 2 * 3", "x = (1 + 2) * 3")


@pytest.mark.parametrize(
    ("written", "meaning"),
    [("x = 0x2a", "x = 42"), ("x = 1_000_000", "x = 1000000"), ("x = 'a' 'b'", "x = 'ab'")],
)
def test_how_a_literal_was_written_is_not_kept(written, meaning):
    assert trees.same_tree(written, meaning)


def test_spans_report_the_source_each_node_covers():
    found = {span.node: span.text for span in trees.spans(LINE)}
    assert found["BinOp"] == "6 * 7"
    assert found["Constant 6"] == "6"


def test_spans_are_ordered_outermost_first():
    # An Assign and the Name inside it both start at column zero, so ordering by start
    # alone puts them in whichever order `walk` happened to produce.
    assert [span.node for span in trees.spans(LINE)][:2] == ["Assign", "Name 'answer'"]


def test_nodes_without_a_position_are_left_out():
    # Mult is not written at a place in the file, so asking where it is has no answer.
    assert not any(span.node == "Mult" for span in trees.spans(LINE))


def test_a_round_trip_gives_back_the_same_tree():
    result = trees.roundtrip("answer = (6 * 7)  # a note")
    assert result.same_tree


def test_a_round_trip_does_not_give_back_the_same_text():
    """The gap between these two is the point of the whole lesson.

    Everything that changes the meaning survives, and nothing about how it was typed does.
    """
    result = trees.roundtrip("answer = (6 * 7)  # a note")
    assert not result.same_text
    assert result.text == "answer = 6 * 7"


def test_source_that_was_already_in_canonical_form_comes_back_unchanged():
    assert trees.roundtrip("answer = 6 * 7").same_text


def test_a_round_trip_reads_as_a_sentence():
    assert "same tree" in str(trees.roundtrip(LINE))


def test_a_survey_counts_the_files_that_matched(tmp_path):
    (tmp_path / "a.py").write_text("x = (1 + 2)  # note\n")
    (tmp_path / "b.py").write_text("def f():\n    return 0x2a\n")
    report = trees.survey(tmp_path)
    assert (report.checked, report.matched) == (2, 2)
    assert report.differed == []


def test_a_survey_skips_a_file_it_cannot_parse_rather_than_failing(tmp_path):
    # The standard library ships files that are only valid on another version. A lesson
    # that fell over on one of them would be making a point about packaging instead.
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "broken.py").write_text("def (\n")
    report = trees.survey(tmp_path)
    assert report.checked == 1
    assert report.skipped == ["broken.py"]


def test_a_survey_is_ordered_and_limited_so_a_notebook_cell_is_repeatable(tmp_path):
    for name in ["c.py", "a.py", "b.py"]:
        (tmp_path / name).write_text("x = 1\n")
    assert trees.survey(tmp_path, limit=2).checked == 2


def test_a_survey_reads_as_a_sentence(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    assert "1 file(s) parsed, 1 round tripped" in str(trees.survey(tmp_path))


def test_the_standard_library_is_where_this_interpreter_says_it_is():
    assert (trees.stdlib() / "ast.py").exists()


def test_the_whole_standard_library_round_trips():
    """The property test from the lesson, run for real rather than described.

    This is slower than every other test here and it is the one worth having. A property
    that holds on the four line example in the notebook and nowhere else is not a property.
    """
    report = trees.survey(trees.stdlib())
    assert report.checked > 100
    assert report.differed == []
