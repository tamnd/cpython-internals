from __future__ import annotations

import ast
import sys
import token
import tokenize
import types

import pytest

from pyxray import compiler

pytestmark = pytest.mark.skipif(
    not compiler.available(),
    reason="this interpreter does not export _testinternalcapi",
)

SOURCE = """\
def greet(name):
    if name:
        return "hello " + name
    return "hello"
"""


@pytest.fixture(scope="module")
def result():
    return compiler.stages(SOURCE)


def test_the_tokenizer_invents_indent_and_dedent(result):
    """Neither token is in the source text. Seeing that is when whitespace stops being magic."""
    kinds = {item.type for item in result.tokens}
    assert token.INDENT in kinds
    assert token.DEDENT in kinds
    assert "INDENT" not in SOURCE


def test_the_token_stream_round_trips_to_the_source(result):
    assert tokenize.untokenize(result.tokens).decode("utf-8") == SOURCE


def test_the_first_token_is_the_encoding_declaration(result):
    """The tokenizer's first job is deciding how to read the bytes at all."""
    assert result.tokens[0].type == token.ENCODING
    assert result.tokens[0].string == "utf-8"


def test_the_tree_is_a_module_holding_a_function(result):
    assert isinstance(result.tree, ast.Module)
    assert isinstance(result.tree.body[0], ast.FunctionDef)
    assert result.tree.body[0].name == "greet"


def test_the_stages_run_in_order_and_all_produce_something(result):
    assert result.tokens
    assert result.codegen
    assert result.optimized
    assert isinstance(result.code, types.CodeType)


def test_code_generation_emits_pseudo_instructions(result):
    """Instructions that exist only inside the compiler and never reach a code object."""
    assert any(item.pseudo for item in result.codegen)


def test_the_optimizer_removes_every_pseudo_instruction(result):
    assert not any(item.pseudo for item in result.optimized)


def test_the_optimizer_makes_the_sequence_shorter(result):
    assert result.removed_by_optimizer > 0
    assert len(result.optimized) < len(result.codegen)


def test_no_pseudo_instruction_survives_into_the_finished_code(result):
    from pyxray.bytecode import disassemble

    assert all(item.opcode <= 255 for item in disassemble(result.code))


def test_every_instruction_carries_a_real_source_position(result):
    for item in result.codegen:
        if item.line <= 0:
            continue  # compiler generated, with no source to point at
        assert 1 <= item.line <= len(SOURCE.splitlines())
        assert item.end_line >= item.line
        assert item.end_column >= item.column


def test_an_instruction_prints_as_a_name_an_argument_and_a_marker(result):
    rendered = [str(item) for item in result.codegen]
    assert any(text.endswith("(pseudo)") for text in rendered)
    assert all(text == text.strip() for text in rendered)


def test_the_summary_counts_the_things_it_says_it_counts(result):
    text = result.summary()
    assert f"{len(result.tokens)} tokens" in text
    assert f"{len(result.codegen)} instructions after code generation" in text
    assert f"{len(result.optimized)} after the optimizer" in text
    assert f"{len(result.code.co_code)} bytes of bytecode" in text
    assert "\n" not in text


def test_the_optimizer_report_shows_both_columns_and_the_two_counts(result):
    text = compiler.what_the_optimizer_did(result)
    assert "after code generation" in text
    assert "after the optimizer" in text
    assert text.splitlines()[-1] == (
        f"{len(result.codegen)} instructions in, {len(result.optimized)} out"
    )


def test_the_optimizer_folds_a_constant():
    """Small enough to read the whole before and after by eye, which is the point."""
    folded = compiler.stages("x = 1 + 2\n")
    assert "BINARY_OP" in [item.opname for item in folded.codegen]
    assert "BINARY_OP" not in [item.opname for item in folded.optimized]


def test_running_at_optimize_two_drops_the_docstring():
    """The docstring lives in the nested function's constants, not the module's."""

    def inner_consts(stages):
        nested = [c for c in stages.code.co_consts if isinstance(c, types.CodeType)]
        return nested[0].co_consts

    source = 'def f():\n    "a docstring"\n    return 1\n'
    assert "a docstring" in inner_consts(compiler.stages(source, optimize=0))
    assert "a docstring" not in inner_consts(compiler.stages(source, optimize=2))


def test_the_metadata_from_code_generation_is_handed_back(result):
    assert "consts" in result.metadata
    assert isinstance(result.metadata["consts"], list)


def test_the_code_object_is_the_one_the_source_really_compiles_to(result):
    assert result.code.co_code == compile(SOURCE, result.filename, "exec").co_code
    assert result.code.co_filename == "<pyxray>"


def test_the_finished_code_actually_runs(result):
    scope: dict = {}
    exec(result.code, scope)
    assert scope["greet"]("world") == "hello world"
    assert scope["greet"]("") == "hello"


def test_assembling_by_hand_refuses_rather_than_aborting_the_process():
    """See issue 34. The C hook asserts on bad metadata, and an assert kills the kernel.

    A notebook reader losing everything they had done is the worst failure this material
    can produce, so the hook stays behind a refusal until its inputs can be validated.
    """
    with pytest.raises(NotImplementedError) as caught:
        compiler.assemble()
    message = str(caught.value)
    assert "assemble_code_object" in message
    assert "aborts the process" in message or "aborts" in message


def test_a_syntax_error_arrives_as_a_syntax_error():
    with pytest.raises(SyntaxError):
        compiler.stages("def f(\n")


def test_compile_three_ways_keeps_the_source_as_the_key():
    spellings = (
        "result = [x * 2 for x in items]",
        "result = list(map(lambda x: x * 2, items))",
    )
    compiled = compiler.compile_three_ways(*spellings)
    assert set(compiled) == set(spellings)
    assert all(isinstance(code, types.CodeType) for code in compiled.values())


def test_python_version_matches_the_interpreter():
    assert compiler.python_version() == sys.version.split()[0]


def test_tokens_can_be_taken_without_running_the_whole_pipeline():
    assert [item.string for item in compiler.tokens("x = 1\n") if item.type == token.NAME] == ["x"]


def test_unavailable_says_what_still_works(monkeypatch):
    """The reader who hits this has the least context, so the message has to carry it."""
    monkeypatch.setitem(sys.modules, "_testinternalcapi", None)
    assert not compiler.available()
    with pytest.raises(compiler.Unavailable) as caught:
        compiler.stages("x = 1\n")
    assert "Every other cell in this lesson still works" in str(caught.value)
