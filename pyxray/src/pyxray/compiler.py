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
import dis
import io
import opcode
import symtable
import sys
import tokenize
import types
from collections.abc import Iterator
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


def _count(number: int, word: str) -> str:
    return f"{number} {word}" if number == 1 else f"{number} {word}s"


@dataclass(frozen=True)
class Stages:
    """Every intermediate form between source text and a code object."""

    source: str
    filename: str
    tokens: list[tokenize.TokenInfo]
    tree: ast.AST
    scope: Scope
    codegen: list[RawInstruction]
    optimized: list[RawInstruction]
    code: types.CodeType
    metadata: dict = field(default_factory=dict)

    @property
    def removed_by_optimizer(self) -> int:
        return len(self.codegen) - len(self.optimized)

    @property
    def pseudo(self) -> list[RawInstruction]:
        """The instructions the code generator emitted that can never be executed.

        Worth having as its own list rather than as a filter the reader writes, because
        the point being made is that this list is not empty and the finished code object's
        equivalent is.
        """
        return [instruction for instruction in self.codegen if instruction.pseudo]

    def summary(self) -> str:
        """The whole trip in one line of counts, read out loud rather than tabulated.

        A one line source produces "1 line", not "1 lines". It is a small thing and it is
        the first output of the first lesson, which is not the place to look careless.
        """
        return ", ".join(
            [
                f"{_count(len(self.source.splitlines()), 'line')} of source",
                _count(len(self.tokens), "token"),
                f"{_count(sum(1 for _ in ast.walk(self.tree)), 'node')} in the tree",
                _count(sum(1 for _ in self.scope.walk()), "scope"),
                f"{_count(len(self.codegen), 'instruction')} after code generation",
                f"{len(self.optimized)} after the optimizer",
                f"{_count(len(self.code.co_code), 'byte')} of bytecode",
            ]
        )


def tokens(source: str) -> list[tokenize.TokenInfo]:
    """The token stream, including the synthesized indentation tokens.

    INDENT and DEDENT are not in the source text. The tokenizer invents them from column
    positions, and seeing that happen is the moment significant whitespace stops being
    magic.
    """
    reader = io.BytesIO(source.encode("utf-8")).readline
    return list(tokenize.tokenize(reader))


#: The questions the symbol table can answer about one name, in the order they are worth
#: asking. The order is the order they print in, so it is part of what a reader sees.
_QUESTIONS = (
    ("parameter", "is_parameter"),
    ("local", "is_local"),
    ("global", "is_global"),
    ("free", "is_free"),
    ("cell", "is_cell"),
    ("declared global", "is_declared_global"),
    ("nonlocal", "is_nonlocal"),
    ("assigned", "is_assigned"),
    ("referenced", "is_referenced"),
    ("imported", "is_imported"),
    ("annotated", "is_annotated"),
    ("namespace", "is_namespace"),
)


@dataclass(frozen=True)
class Symbol:
    """One name, and everything the symbol table decided about it.

    The flags are kept separate rather than collapsed into a single scope word on purpose.
    A name at module level answers yes to both local and global, which looks like a bug and
    is not: a module level binding really is stored in the module's own namespace and
    really is what every function in the file sees as a global. Collapsing that into one
    word would hide the one fact about scope that beginners get wrong most often.
    """

    name: str
    flags: tuple[str, ...]

    def __contains__(self, question: str) -> bool:
        return question in self.flags

    def __str__(self) -> str:
        return f"{self.name}: {', '.join(self.flags) if self.flags else 'no flags set'}"


@dataclass(frozen=True)
class Scope:
    """One symbol table: a module, a function, a class, or a lambda.

    CPython builds one of these per block before it generates a single instruction, and
    the reason is that it cannot know how to compile `x` until it knows whether `x` is a
    local, a global, or a closure variable. That decision is made here and nowhere else.
    """

    name: str
    kind: str
    line: int
    nested: bool
    symbols: list[Symbol]
    children: list[Scope]

    def lookup(self, name: str) -> Symbol | None:
        """The symbol for this name in this scope, or None if this scope never sees it.

        `symtable.SymbolTable.lookup` raises KeyError for a name it does not hold, which
        makes the common question, does this scope know about this name, awkward to ask.
        """
        for symbol in self.symbols:
            if symbol.name == name:
                return symbol
        return None

    def walk(self) -> Iterator[Scope]:
        """This scope and every scope nested inside it, outermost first."""
        yield self
        for child in self.children:
            yield from child.walk()

    def tree(self, indent: int = 0) -> str:
        """The whole nest of scopes as text, one name per line."""
        pad = "  " * indent
        lines = [f"{pad}{self.kind} {self.name!r} (line {self.line})"]
        lines.extend(f"{pad}  {symbol}" for symbol in self.symbols)
        lines.extend(child.tree(indent + 1) for child in self.children)
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.tree()


def questions() -> tuple[str, ...]:
    """The questions this interpreter's symbol table can actually answer.

    Not every release exposes the same set. `Symbol.is_cell` arrived in 3.15, so on 3.14
    there is no public way to tell a cell apart from a plain local: `is_local` answers yes
    for both. Asking here rather than assuming keeps the older interpreter honest instead
    of crashing on it.
    """
    return tuple(label for label, question in _QUESTIONS if hasattr(symtable.Symbol, question))


def _scope_of(table: symtable.SymbolTable) -> Scope:
    asked = [pair for pair in _QUESTIONS if hasattr(symtable.Symbol, pair[1])]
    rows = []
    for symbol in table.get_symbols():
        flags = tuple(label for label, question in asked if getattr(symbol, question)())
        rows.append(Symbol(name=symbol.get_name(), flags=flags))
    return Scope(
        name=table.get_name(),
        kind=str(table.get_type()),
        line=table.get_lineno(),
        nested=table.is_nested(),
        symbols=rows,
        children=[_scope_of(child) for child in table.get_children()],
    )


def symbols(source: str, filename: str = "<pyxray>") -> Scope:
    """Build the symbol table for this source, the way the compiler does before codegen.

    This is a real stage and not a summary of one. `symtable.symtable` calls the same
    `_PySymtable_Build` that `compile()` calls, so what comes back here is the table the
    code generator would have used, not a reconstruction of it.
    """
    return _scope_of(symtable.symtable(source, filename, "exec"))


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
        scope=symbols(source, filename),
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
    piece of work rather than a line, and it is tracked as issue 35.
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


def pseudo_instructions() -> tuple[str, ...]:
    """Every instruction that exists only inside the compiler, from the opcode table.

    Read rather than written down, for the usual reason. This list gained and lost members
    in most of the last five releases, and a copy of it in a lesson would be a paragraph
    that goes quietly wrong.
    """
    return tuple(sorted(name for name, number in opcode.opmap.items() if is_pseudo(number)))


def folds(expression: str) -> bool:
    """Did the compiler work this expression out, or did it leave the work for later?

    The test is whether any arithmetic survived into the code object. If the compiler
    computed the answer there is nothing left to compute, so no BINARY_OP or UNARY_OP is
    emitted and the result sits in the constants instead.
    """
    code = compile(expression, "<pyxray>", "eval")
    arithmetic = {"BINARY_OP", "UNARY_NEGATIVE", "UNARY_INVERT", "UNARY_NOT"}
    return not any(step.opname in arithmetic for step in dis.get_instructions(code))


def compile_three_ways(*sources: str) -> dict[str, types.CodeType]:
    """Compile several spellings of the same idea, for comparing what they cost."""
    return {source: compile(source, "<pyxray>", "exec") for source in sources}


def python_version() -> str:
    return sys.version.split()[0]
