"""Running CPython's compiler one stage at a time.

This is the best teaching hook in the codebase and almost nobody uses it.
`_testinternalcapi` exports `compiler_codegen`, `optimize_cfg` and
`assemble_code_object` on a stock interpreter, which means a beginner can watch the
compiler emit an instruction sequence, watch the optimizer rewrite it, and watch the
assembler turn it into a code object, from a notebook, with no build and no C.

The module exists because the raw hooks are unpleasant. They hand back opaque
`InstructionSequence` objects and six element tuples of integers, and the metadata
dictionary they need has fourteen keys and no documentation. All of that is here so a
lesson can stay about the compiler.
"""

from __future__ import annotations

import ast
import io
import sys
import tokenize
import types
from dataclasses import dataclass, field

from ._opcodes import is_pseudo, opcode_name


class Unavailable(RuntimeError):
    """Raised when this interpreter does not expose the compiler stages.

    The message says what to do about it rather than just stating the fact, because the
    reader who hits this is by definition the reader with the least context.
    """


def _internal():
    try:
        import _testinternalcapi
    except ImportError as error:
        raise Unavailable(
            "this interpreter has no _testinternalcapi, so the compiler stages cannot be "
            "run separately here. Every other cell in this lesson still works. The stage "
            "outputs below came from a recorded run against the pinned build."
        ) from error
    return _testinternalcapi


def available() -> bool:
    """Can the stage by stage compiler be run on this interpreter?"""
    try:
        _internal()
    except Unavailable:
        return False
    return True


@dataclass(frozen=True)
class RawInstruction:
    """One instruction as the compiler holds it, before there is a code object.

    The compiler works in terms of a graph of instructions carrying full source positions
    and pseudo instructions that never reach the finished code. This is that form, not
    the `dis` form.
    """

    opcode: int
    opname: str
    arg: int | None
    line: int
    end_line: int
    column: int
    end_column: int

    @property
    def pseudo(self) -> bool:
        return is_pseudo(self.opcode)

    def __str__(self) -> str:
        arg = "" if self.arg is None else f" {self.arg}"
        mark = " (pseudo)" if self.pseudo else ""
        return f"{self.opname}{arg}{mark}"


def _instructions(sequence) -> list[RawInstruction]:
    rows = []
    for item in sequence.get_instructions():
        number, arg, line, end_line, column, end_column = item
        rows.append(
            RawInstruction(
                opcode=number,
                opname=opcode_name(number),
                arg=arg,
                line=line,
                end_line=end_line,
                column=column,
                end_column=end_column,
            )
        )
    return rows


@dataclass(frozen=True)
class Stages:
    """Every intermediate form between source text and a code object."""

    source: str
    filename: str
    tokens: list[tokenize.TokenInfo]
    tree: ast.AST
    codegen: list[RawInstruction]
    optimized: list[RawInstruction]
    code: types.CodeType
    metadata: dict = field(default_factory=dict)

    @property
    def removed_by_optimizer(self) -> int:
        return len(self.codegen) - len(self.optimized)

    def summary(self) -> str:
        return (
            f"{len(self.source.splitlines())} lines of source, "
            f"{len(self.tokens)} tokens, "
            f"{sum(1 for _ in ast.walk(self.tree))} AST nodes, "
            f"{len(self.codegen)} instructions after code generation, "
            f"{len(self.optimized)} after the optimizer, "
            f"{len(self.code.co_code)} bytes of bytecode"
        )


def tokens(source: str) -> list[tokenize.TokenInfo]:
    """The token stream, including the synthesized indentation tokens.

    INDENT and DEDENT are not in the source text. The tokenizer invents them from column
    positions, and seeing that happen is the moment significant whitespace stops being
    magic.
    """
    reader = io.BytesIO(source.encode("utf-8")).readline
    return list(tokenize.tokenize(reader))


def stages(source: str, filename: str = "<pyxray>", *, optimize: int = 0) -> Stages:
    """Run the front end one stage at a time and keep every intermediate form.

    Raises Unavailable when the interpreter does not export the compiler hooks, which is
    the case a lesson has to handle rather than crash on.
    """
    internal = _internal()

    tree = ast.parse(source, filename)
    sequence, metadata = internal.compiler_codegen(tree, filename, optimize)
    generated = _instructions(sequence)

    optimized_sequence = internal.optimize_cfg(sequence, metadata["consts"], 0)
    optimized = _instructions(optimized_sequence)

    # The third hook, assemble_code_object, is deliberately not called here. See
    # assemble() below for why. The finished code object comes from the ordinary
    # compile(), which runs the same three stages inside the interpreter, so this is the
    # real output of the pipeline the first two stages belong to and not a reconstruction.
    code = compile(source, filename, "exec", optimize=optimize)

    return Stages(
        source=source,
        filename=filename,
        tokens=tokens(source),
        tree=tree,
        codegen=generated,
        optimized=optimized,
        code=code,
        metadata=dict(metadata),
    )


def assemble(*_args, **_kwargs):
    """Not in this version, and the reason is worth reading.

    `_testinternalcapi.assemble_code_object` is the third compiler hook and it is the one
    that would let a lesson build a code object by hand. It is not wired up yet because
    it asserts on its metadata rather than raising, and a failed assertion aborts the
    process. In a notebook that kills the kernel and loses whatever the reader had done,
    which is the worst possible failure for the audience this is written for.

    Two specific traps found while trying. `compiler_codegen` returns `consts` as a list
    and `assemble_code_object` requires a dict of constant to index, so passing one
    straight to the other aborts. And `compiler_codegen` does not return `names`,
    `varnames`, `cellvars` or `freevars` at all, so for any code that touches a name
    there is no way to build correct metadata from the previous stage's output alone.

    Doing this safely means validating every key and its type before the call, which is a
    piece of work rather than a line, and it is tracked separately.
    """
    raise NotImplementedError(assemble.__doc__)


def what_the_optimizer_did(result: Stages) -> str:
    """A readable account of the difference the optimizer made.

    Alignment is by index and not by a real diff, on purpose. A real diff hides the thing
    the lesson is pointing at, which is that one column is shorter than the other.
    """
    before = [str(i) for i in result.codegen]
    after = [str(i) for i in result.optimized]
    width = max((len(text) for text in before), default=0)
    width = max(width, 24)

    lines = [f"{'after code generation':<{width}}  after the optimizer", "-" * (width * 2)]
    for index in range(max(len(before), len(after))):
        left = before[index] if index < len(before) else ""
        right = after[index] if index < len(after) else ""
        lines.append(f"{left:<{width}}  {right}".rstrip())
    lines.append("")
    lines.append(f"{len(before)} instructions in, {len(after)} out")
    return "\n".join(lines)


def compile_three_ways(*sources: str) -> dict[str, types.CodeType]:
    """Compile several spellings of the same idea, for comparing what they cost."""
    return {source: compile(source, "<pyxray>", "exec") for source in sources}


def python_version() -> str:
    return sys.version.split()[0]
