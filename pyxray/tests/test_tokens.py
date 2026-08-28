from __future__ import annotations

import pytest

from pyxray import tokens

SIMPLE = "if x:\n    y = 1\n"

NESTED = "if a:\n    if b:\n        c = 1\nd = 2\n"


def kinds_of(source):
    return tokens.kinds(source)


def test_every_stream_starts_with_encoding_and_ends_with_endmarker():
    """Two tokens that are not in the file, wrapped around every one that is.

    ENCODING is the tokenizer reporting what it decided the bytes meant, which is a real
    decision because PEP 263 lets a file say. ENDMARKER is how the grammar spells the end
    of input, since a grammar cannot match on running out of characters.
    """
    stream = kinds_of(SIMPLE)
    assert stream[0] == "ENCODING"
    assert stream[-1] == "ENDMARKER"


def test_the_encoding_token_carries_the_encoding_and_occupies_no_source():
    first = tokens.stream(SIMPLE)[0]
    assert first.text == "utf-8"
    assert first.start == first.end == (0, 0)
    assert first.synthesized


def test_indent_is_a_real_run_of_characters_and_dedent_is_not():
    """The asymmetry that makes people look for DEDENT in the file and not find it.

    An indent has text, because there really are four spaces at the start of that line. A
    dedent has none: it is emitted at the first column of the next line, zero characters
    wide, and it exists only because the parser needs to be told the block ended.
    """
    stream = {item.kind: item for item in tokens.stream(SIMPLE)}
    assert stream["INDENT"].text == "    "
    assert stream["DEDENT"].text == ""
    assert stream["DEDENT"].start == stream["DEDENT"].end


def test_one_line_can_close_three_blocks_and_produces_one_dedent_for_each():
    """Dedents are counted, indents are not, which is the whole shape of the algorithm."""
    stream = kinds_of(NESTED)
    assert stream.count("INDENT") == 2
    assert stream.count("DEDENT") == 2
    positions = [item.start for item in tokens.stream(NESTED) if item.kind == "DEDENT"]
    assert positions == [(4, 0), (4, 0)]


def test_the_tokenizer_does_not_know_what_a_keyword_is():
    """`if` is a NAME, and this surprises everybody the first time.

    The token stream has no keyword token in it. The parser turns a NAME into a keyword
    afterwards by looking the text up in a table, at
    Parser/pegen.c:162-179@v3.15.0rc1#_get_keyword_or_name_type. That is why soft keywords
    like `match` are possible at all: the tokenizer never committed to anything.
    """
    stream = tokens.stream("if x:\n    pass\n")
    assert [item.kind for item in stream if item.text == "if"] == ["NAME"]
    assert [item.kind for item in tokens.stream("match = 1\n") if item.text == "match"] == ["NAME"]


def test_every_operator_is_an_op_and_the_exact_type_says_which_one():
    plus_equal = next(item for item in tokens.stream("a += 1\n") if item.text == "+=")
    assert plus_equal.kind == "OP"
    assert plus_equal.exact == "PLUSEQUAL"


def test_a_newline_inside_brackets_is_not_a_newline():
    """Implicit line joining, visible as a token kind rather than described as a rule.

    NEWLINE ends a logical line. NL is a physical line ending that did not end anything.
    The tokenizer decides between them at
    Parser/lexer/lexer.c:804-827@v3.15.0rc1#tok_extra_tokens, purely on whether a bracket
    is open, and the parser never sees the NL at all.
    """
    stream = kinds_of("x = (1,\n     2)\n")
    assert stream.count("NL") == 1
    assert stream.count("NEWLINE") == 1
    assert "INDENT" not in stream


def test_a_backslash_continuation_leaves_no_token_behind_at_all():
    """Not even a marker. The two physical lines become one and the evidence is the positions."""
    stream = tokens.stream("x = 1 + \\\n    2\n")
    assert [item.text for item in stream if item.kind == "NUMBER"] == ["1", "2"]
    assert [item.start[0] for item in stream if item.kind == "NUMBER"] == [1, 2]
    assert "NL" not in [item.kind for item in stream]


def test_a_comment_only_line_does_not_affect_indentation():
    stream = kinds_of("x = 1\n        # indented comment\ny = 2\n")
    assert "INDENT" not in stream
    assert stream.count("COMMENT") == 1


def test_an_fstring_is_several_tokens_and_the_expression_inside_is_ordinary_code():
    """Since 3.12 an f-string is not one blob, and this is where you can see it.

    The expression between the braces is tokenized as normal Python, by the same
    tokenizer, in a different mode. `tok_get` picks the mode at
    Parser/lexer/lexer.c:1615-1624@v3.15.0rc1#tok_get.
    """
    stream = kinds_of('f"a{b+1}c"\n')
    assert stream.count("FSTRING_START") == 1
    assert stream.count("FSTRING_END") == 1
    assert "NAME" in stream
    assert "NUMBER" in stream


def test_a_tstring_gets_its_own_token_kinds_rather_than_reusing_the_fstring_ones():
    """PEP 750 landed in 3.14, and the tokenizer distinguishes the two from the prefix."""
    stream = kinds_of('t"a{b}c"\n')
    assert stream.count("TSTRING_START") == 1
    assert stream.count("TSTRING_END") == 1
    assert "FSTRING_START" not in stream


def test_the_table_puts_one_token_on_each_line_with_its_position():
    text = tokens.table(SIMPLE)
    assert len(text.splitlines()) == len(tokens.stream(SIMPLE))
    assert "INDENT" in text
    assert "1:0" in text


def test_mixed_tabs_and_spaces_is_reported_as_a_taberror_and_not_a_crash():
    """The experiment the lesson runs, and the reason the second column count exists."""
    problem = tokens.failure("if x:\n\ty = 1\n        z = 2\n")
    assert problem is not None
    assert problem.error == "TabError"
    assert "tabs and spaces" in problem.message
    assert problem.line == 3


def test_an_unclosed_bracket_is_a_tokenerror_and_carries_a_position_differently():
    problem = tokens.failure("x = (1,\n")
    assert problem is not None
    assert problem.error == "TokenError"
    assert "EOF" in problem.message
    assert problem.line == 1


def test_a_dedent_to_a_column_nobody_used_is_an_indentationerror():
    problem = tokens.failure("if x:\n  y = 1\n z = 2\n")
    assert problem is not None
    assert problem.error == "IndentationError"
    assert "outer indentation level" in problem.message


def test_source_that_tokenizes_cleanly_reports_no_failure():
    assert tokens.failure(SIMPLE) is None


def test_a_failure_prints_the_kind_the_place_and_the_message():
    assert str(tokens.failure("if x:\n\ty = 1\n        z = 2\n")).startswith("TabError at line 3")


def test_a_tab_advances_to_the_next_tab_stop_rather_than_a_fixed_width():
    """One tab is eight columns from column zero and one column from column seven."""
    assert tokens.measure("\tx") == (8, 1)
    assert tokens.measure("       \tx") == (8, 8)
    assert tokens.measure("        \tx") == (16, 9)


def test_spaces_agree_with_themselves_under_any_tab_size_and_tabs_do_not():
    """What the second count is actually for, in one assertion.

    Leading spaces produce the same number twice, so no file made only of spaces can ever
    trip the check. A tab produces two different numbers, which is what lets the tokenizer
    notice that a line agrees with another one only by accident of the tab width.
    """
    assert tokens.measure("    x")[0] == tokens.measure("    x")[1]
    col, altcol = tokens.measure("\tx")
    assert col != altcol


def test_a_formfeed_resets_the_column_count_to_zero():
    """A concession to Emacs that is still in the tokenizer and still observable."""
    assert tokens.measure("    \014    x") == (4, 4)


CORPUS = [
    "x = 1\n",
    SIMPLE,
    NESTED,
    "if a:\n    b = 1\nelse:\n    c = 2\n",
    "def f():\n    if x:\n        return 1\n    return 2\n",
    "class C:\n    def m(self):\n        pass\n\n    def n(self):\n        pass\n",
    "x = 1\n\n\ny = 2\n",
    "x = 1\n        # a comment indented for no reason\ny = 2\n",
    "if a:\n\tb = 1\n\tc = 2\nd = 3\n",
    "if a:\n  b = 1\n  if c:\n          d = 2\ne = 3\n",
    "while x:\n    while y:\n        while z:\n            pass\n",
]


@pytest.mark.parametrize("source", CORPUS, ids=range(len(CORPUS)))
def test_the_transcription_and_cpython_agree_on_every_source_in_the_corpus(source):
    """The test that makes the transcription worth reading rather than worth doubting.

    `indent_trace` is thirty lines of C rewritten in Python. The only thing that makes it
    trustworthy is running it and the original against the same input and requiring the
    same sequence of INDENT and DEDENT tokens, which is what happens here. If the C ever
    changes, this fails, and the lesson gets corrected rather than the reader misled.
    """
    mine = [name for step in tokens.indent_trace(source) for name in step.emitted]
    theirs = [kind for kind in tokens.kinds(source) if kind in {"INDENT", "DEDENT"}]
    assert mine == theirs


def test_the_trace_shows_the_stack_growing_and_shrinking():
    steps = tokens.indent_trace(NESTED)
    assert [step.stack for step in steps] == [(0,), (0, 4), (0, 4, 8), (0,)]
    assert [step.emitted for step in steps] == [(), ("INDENT",), ("INDENT",), ("DEDENT", "DEDENT")]


def test_the_trace_skips_blank_and_comment_only_lines_entirely():
    steps = tokens.indent_trace("x = 1\n\n    # comment\ny = 2\n")
    assert [step.line for step in steps] == [1, 4]


def test_the_transcription_raises_the_same_errors_cpython_does():
    with pytest.raises(TabError):
        tokens.indent_trace("if x:\n\ty = 1\n        z = 2\n")
    with pytest.raises(IndentationError):
        tokens.indent_trace("if x:\n  y = 1\n z = 2\n")


def test_the_transcription_refuses_source_it_does_not_model_rather_than_guessing():
    """Brackets and backslashes turn the indentation code off, and this does not model that."""
    with pytest.raises(tokens.OutOfScope):
        tokens.indent_trace("x = (1,\n     2)\n")
    with pytest.raises(tokens.OutOfScope):
        tokens.indent_trace("x = 1 + \\\n    2\n")


def test_the_report_has_a_header_and_one_row_per_measured_line():
    text = tokens.indent_report(NESTED)
    lines = text.splitlines()
    assert lines[0].strip().startswith("ln")
    assert len(lines) == 2 + len(tokens.indent_trace(NESTED))
