from __future__ import annotations

import ast
import dis
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


def test_the_summary_counts_one_of_something_as_one(result):
    """It is the first output of the first lesson, which is not the place to look careless."""
    text = compiler.stages("answer = 6 * 7\n").summary()
    assert "1 line of source" in text
    assert "1 scope," in text
    assert "lines of source" not in text


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


def test_a_normal_run_says_it_had_the_real_constants(result):
    assert result.constants_known


def stripped(monkeypatch):
    """Make this interpreter behave like the WebAssembly one: codegen with no consts key.

    Pyodide 314 returns argcount, kwonlyargcount and posonlyargcount and nothing else.
    That is measured, and the recording is in probes/pyodide/pyodide.json. Faking it here
    rather than only asserting on the helper means the whole of stages() runs the path a
    browser takes, including the real call into optimize_cfg.
    """
    real = compiler._internal()

    class WithoutConsts:
        def compiler_codegen(self, tree, filename, optimize):
            sequence, metadata = real.compiler_codegen(tree, filename, optimize)
            return sequence, {key: value for key, value in metadata.items() if key != "consts"}

        def __getattr__(self, name):
            return getattr(real, name)

    monkeypatch.setattr(compiler, "_internal", WithoutConsts)


def test_the_optimizer_still_runs_when_the_metadata_has_no_constants(monkeypatch):
    stripped(monkeypatch)
    run = compiler.stages(SOURCE)
    assert not run.constants_known
    assert run.optimized
    assert not any(one.pseudo for one in run.optimized)


def test_without_the_constants_the_fold_does_not_happen_and_is_not_claimed(monkeypatch):
    stripped(monkeypatch)
    run = compiler.stages("answer = 6 * 7")
    assert not run.constants_known
    assert "BINARY_OP" in [one.opname for one in run.optimized]
    # The last stage comes from the ordinary compile(), which had the real constants, so
    # the finished code object still shows the fold. That is what stops a build without
    # the metadata from teaching the reader something untrue.
    assert "BINARY_OP" not in [one.opname for one in dis.get_instructions(run.code)]


def test_a_placeholder_stays_a_load_const_rather_than_looking_like_a_known_value(monkeypatch):
    """The optimizer rewrites LOAD_CONST of a None into the shorter common constant form.

    Padding with None would make a browser reader see LOAD_COMMON_CONSTANT where their
    source has a 6, which reads as a real optimization and is not one. The placeholder
    exists so that does not happen.
    """
    stripped(monkeypatch)
    run = compiler.stages("answer = 6 * 7")
    names = [one.opname for one in run.optimized]
    assert names.count("LOAD_CONST") == 3
    assert "LOAD_COMMON_CONSTANT" not in names


def test_the_constants_list_is_never_shorter_than_the_sequence_asks_for():
    """The one that matters. A short list reads past the end of memory under WebAssembly.

    There is no exception to catch there, so this cannot be a try block anywhere. It has to
    be true by construction, which means the list is built here and never handed in.
    """
    internal = compiler._internal()
    sequence, _ = internal.compiler_codegen(ast.parse("answer = 6 * 7"), "<test>", 0)
    needed = compiler._slots_needed(sequence)
    assert needed > 0
    for given in ({}, {"consts": []}, {"consts": [6]}, {"consts": None}, {"consts": "nonsense"}):
        consts, known = compiler._consts_for(sequence, given)
        assert len(consts) == needed, given
        assert not known, given


def test_a_long_enough_real_list_is_passed_through_untouched():
    internal = compiler._internal()
    sequence, metadata = internal.compiler_codegen(ast.parse("answer = 6 * 7"), "<test>", 0)
    consts, known = compiler._consts_for(sequence, metadata)
    assert known
    assert consts == metadata["consts"]


def test_this_interpreter_hands_back_its_constants():
    assert compiler.constants_available()


def test_a_build_without_the_constants_says_so_where_the_reader_is_looking(monkeypatch):
    stripped(monkeypatch)
    assert compiler.available()
    assert not compiler.constants_available()
    report = compiler.what_the_optimizer_did(compiler.stages("answer = 6 * 7"))
    assert "did not hand over the constant values" in report


def test_the_optimizer_report_says_nothing_extra_when_the_values_were_there(result):
    assert "did not hand over" not in compiler.what_the_optimizer_did(result)


def test_constants_are_not_available_without_the_hooks(monkeypatch):
    monkeypatch.setitem(sys.modules, "_testinternalcapi", None)
    assert not compiler.constants_available()


def test_the_placeholder_says_what_it_is():
    assert "not available" in repr(compiler.Unknown())


def test_the_code_object_is_the_one_the_source_really_compiles_to(result):
    assert result.code.co_code == compile(SOURCE, result.filename, "exec").co_code
    assert result.code.co_filename == "<pyxray>"


def test_the_finished_code_actually_runs(result):
    scope: dict = {}
    exec(result.code, scope)
    assert scope["greet"]("world") == "hello world"
    assert scope["greet"]("") == "hello"


def test_assembling_by_hand_refuses_rather_than_aborting_the_process():
    """See issue 35. The C hook asserts on bad metadata, and an assert kills the kernel.

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
