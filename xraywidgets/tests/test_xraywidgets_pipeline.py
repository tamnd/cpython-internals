"""The pipeline explorer, checked against `pyxray` rather than against a frozen listing."""

from __future__ import annotations

import ast

import pytest

from pyxray import compiler, tokens
from xraywidgets.pipeline import LIMIT, PANES, PipelineExplorer

#: The one line program the lessons use, which is small enough that every pane fits on a
#: screen together and still shows a constant being folded away.
L0 = "answer = 6 * 7"


def pane(widget: PipelineExplorer, name: str) -> dict[str, object]:
    return next(one for one in widget.state()["panes"] if one["name"] == name)


def test_there_is_one_pane_per_stage_in_pipeline_order():
    names = [one["name"] for one in PipelineExplorer(L0).state()["panes"]]
    assert names == [name for name, _, _ in PANES]


def test_the_tokens_are_the_ones_pyxray_produced():
    shown = pane(PipelineExplorer(L0), "tokens")
    assert shown["shown"] == len(tokens.stream(L0))


def test_the_token_pane_counts_tokens_and_not_lines_of_something_else():
    assert pane(PipelineExplorer(L0), "tokens")["count"] == f"{len(tokens.stream(L0))} tokens"


def test_the_tree_pane_counts_the_nodes_ast_walk_finds():
    nodes = sum(1 for _ in ast.walk(ast.parse(L0)))
    assert pane(PipelineExplorer(L0), "tree")["count"] == f"{nodes} nodes"


def test_the_symbol_pane_says_one_scope_and_not_one_scopes():
    assert pane(PipelineExplorer(L0), "symbols")["count"] == "1 scope"


def test_the_optimizer_pane_says_how_many_instructions_went_away():
    if not compiler.available():
        pytest.skip("this build has no _testinternalcapi")
    run = compiler.stages(L0)
    shown = pane(PipelineExplorer(L0), "optimized")
    assert shown["count"] == f"{len(run.optimized)} instructions, {run.removed_by_optimizer} gone"


def test_the_multiplication_is_there_after_codegen_and_gone_by_the_code_object():
    if not compiler.available():
        pytest.skip("this build has no _testinternalcapi")
    widget = PipelineExplorer(L0)
    assert any("BINARY_OP" in line for line in pane(widget, "codegen")["lines"])
    assert not any("BINARY_OP" in line for line in pane(widget, "code")["lines"])


def test_the_answer_the_compiler_worked_out_is_in_the_code_object_pane():
    assert any("42" in line for line in pane(PipelineExplorer(L0), "code")["lines"])


def test_an_opcode_that_keeps_its_value_in_arg_still_prints_the_value():
    line = next(
        one for one in pane(PipelineExplorer(L0), "code")["lines"] if "LOAD_SMALL_INT" in one
    )
    assert line.endswith("LOAD_SMALL_INT 42")


def test_an_opcode_with_a_readable_argument_prints_that_instead_of_the_number():
    lines = pane(PipelineExplorer(L0), "code")["lines"]
    assert any(one.endswith("STORE_NAME answer") for one in lines)


def test_a_comment_is_in_the_tokens_and_gone_by_the_tree():
    widget = PipelineExplorer("answer = 42  # a note to nobody")
    assert any("a note to nobody" in line for line in pane(widget, "tokens")["lines"])
    assert not any("a note to nobody" in line for line in pane(widget, "tree")["lines"])


def test_the_summary_is_the_one_pyxray_writes():
    if not compiler.available():
        pytest.skip("this build has no _testinternalcapi")
    assert PipelineExplorer(L0).state()["summary"] == compiler.stages(L0).summary()


def test_broken_code_is_a_message_and_not_a_traceback():
    widget = PipelineExplorer("def (")
    assert "did not compile" in widget.state()["error"]
    assert widget.state()["panes"] == []
    assert "did not compile" in widget.render()


def test_a_long_program_is_cut_off_and_says_how_much_was_cut():
    widget = PipelineExplorer("\n".join(f"name{index} = {index}" for index in range(60)))
    shown = pane(widget, "tokens")
    assert shown["shown"] == LIMIT
    assert shown["hidden"] > 0
    assert f"and {shown['hidden']} more lines" in widget.render()


def test_a_short_program_is_not_cut_off():
    assert pane(PipelineExplorer(L0), "tokens")["hidden"] == 0


def test_the_source_the_reader_typed_is_shown_back_escaped():
    assert "&lt;" in PipelineExplorer("ok = 1 < 2").render()


def test_the_panes_that_need_the_compiler_hooks_are_marked_as_such():
    needs = {name for name, _, needed in PANES if needed}
    assert needs == {"codegen", "optimized"}


def test_the_four_panes_that_do_not_need_the_hooks_always_have_something_in_them():
    widget = PipelineExplorer(L0)
    for name, _, needs_internals in PANES:
        if not needs_internals:
            assert pane(widget, name)["lines"], name


def test_a_build_without_the_hooks_still_draws_the_other_four(monkeypatch):
    def missing(*_args, **_kwargs):
        raise compiler.Unavailable("pretending this build has no _testinternalcapi")

    monkeypatch.setattr(compiler, "stages", missing)
    monkeypatch.setattr(compiler, "available", lambda: False)
    widget = PipelineExplorer(L0)
    assert pane(widget, "tokens")["lines"]
    assert pane(widget, "codegen")["lines"] == []
    assert pane(widget, "codegen")["count"] == "not on this build"
    assert "_testinternalcapi" in widget.render()


def test_a_build_without_the_hooks_does_not_pretend_to_have_a_summary(monkeypatch):
    monkeypatch.setattr(
        compiler, "stages", lambda *a, **k: (_ for _ in ()).throw(compiler.Unavailable("no hooks"))
    )
    assert PipelineExplorer(L0).state()["summary"] == ""


def test_the_live_markup_has_somewhere_to_type_and_the_still_one_does_not():
    assert 'data-role="code"' in PipelineExplorer(L0).view()["html"]
    assert 'data-role="code"' not in PipelineExplorer(L0).render()


def test_the_front_end_module_works_out_no_stages_of_its_own():
    module = PipelineExplorer.esm()
    for word in ("tokenize", "symtable", "BINARY_OP", "co_code"):
        assert word not in module
