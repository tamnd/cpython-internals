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


#: The three functions this module drives the compiler through. Checked together, because a
#: module that is there without them is a different problem with a different answer, and the
#: reader should be told which one they have rather than finding out from an AttributeError
#: four cells later.
HOOKS = ("compiler_codegen", "optimize_cfg", "assemble_code_object")

#: The one distribution measured so far that leaves the module out, and the package that puts
#: it back. Named in the error rather than left to the reader to find, because the reader who
#: hits this is the one least able to guess that a private CPython test module is packaged
#: separately. probes/distributions has the rest of the table.
FEDORA = "on Fedora and RHEL, dnf install python3-test puts it back"

#: The release the three functions arrived in. The macOS system interpreter is 3.9, ships the
#: module, and has none of them, which is the other way this fails and the more confusing one.
FIRST_VERSION = (3, 12)

#: The tail of both messages. The reader is mid lesson and the first thing they want to know
#: is whether they have to stop.
STILL_WORKS = (
    "Every other cell in this lesson still works. The stage outputs below came from a "
    "recorded run against the pinned build."
)


def _internal():
    try:
        import _testinternalcapi
    except ImportError as error:
        raise Unavailable(
            "this interpreter has no _testinternalcapi, so the compiler stages cannot be "
            f"run separately here. Most Pythons ship it and a few do not: {FEDORA}. " + STILL_WORKS
        ) from error
    missing = [name for name in HOOKS if not hasattr(_testinternalcapi, name)]
    if missing:
        wanted = ".".join(str(one) for one in FIRST_VERSION)
        raise Unavailable(
            f"this interpreter has _testinternalcapi but not {', '.join(missing)}, so the "
            f"compiler stages cannot be run separately here. Those arrived in {wanted} and "
            f"this is {sys.version_info[0]}.{sys.version_info[1]}, so the answer is a newer "
            "Python rather than another package. " + STILL_WORKS
        )
    return _testinternalcapi


def available() -> bool:
    """Can the stage by stage compiler be run on this interpreter?"""
    try:
        _internal()
    except Unavailable:
        return False
    return True


def constants_available() -> bool:
    """Does this build's code generator hand back the constants it collected?

    Two builds can both export the compiler hooks and still differ here. The optimizer
    needs the values to work out that `6 * 7` is `42`, and Pyodide's build returns metadata
    with no constants in it at all, so on a browser that answer is False and no fold in this
    material happens. Measured rather than assumed, because it is the sort of thing that
    changes in a release and a lesson that asserted it would go quietly wrong.
    """
    try:
        internal = _internal()
    except Unavailable:
        return False
    sequence, metadata = internal.compiler_codegen(ast.parse("answer = 6 * 7"), "<pyxray>", 0)
    return _consts_for(sequence, metadata)[1]


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


def _slots_needed(sequence) -> int:
    """How long a constants list has to be before this sequence can be optimized.

    One past the largest index any instruction reads, or zero when none of them reads one.
    `dis.hasconst` holds only `LOAD_CONST` today and has held more in the past, so this
    asks the interpreter rather than naming the opcode.
    """
    indexes = [
        item[1]
        for item in sequence.get_instructions()
        if item[0] in dis.hasconst and isinstance(item[1], int)
    ]
    return max(indexes) + 1 if indexes else 0


class Unknown:
    """A stand in for a constant the interpreter did not hand over.

    Used only when `compiler_codegen` returns no constants at all, which happens on the
    WebAssembly build. The optimizer needs a list of the right length or it reads past the
    end of it, so it gets one of these per slot. They exist to be unusable: the optimizer
    cannot fold them, cannot compare them to anything it recognises, and cannot rewrite a
    `LOAD_CONST` of one into the shorter `LOAD_COMMON_CONSTANT` form. So the pane shows
    `LOAD_CONST 0` and the reader sees a stage that ran without the values rather than a
    fold that looks real and is not.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "<constant not available on this build>"


def _consts_for(sequence, metadata: dict) -> tuple[list, bool]:
    """The constants list to hand the optimizer, and whether it holds the real values.

    `compiler_codegen` collects the constants it saw and returns them under a `consts`
    key, and that list is the one to use, because the optimizer reads the values out of it
    to turn `6 * 7` into `42`. Pyodide's build does not return that key at all. Asking for
    it there raises `KeyError` and the middle stage never runs, which is the bug this
    function exists to fix. The measurement is in `probes/pyodide/`.

    When the key is missing the list is built from the sequence instead, one `Unknown` per
    slot, and the second half of the return value is False. Callers have to check it before
    saying anything about what the optimizer did, because without the values the optimizer
    does not simply skip its constant work, it does that work on the wrong information.
    `6 * 7` keeps its `BINARY_OP` and `while 0:` keeps its loop. The stage really ran and
    what it produced is not what the source compiles to, and both halves of that need
    saying.

    The length is the part to be careful about. Hand `optimize_cfg` a list shorter than the
    largest index in the sequence and a native interpreter raises a tidy `ValueError`,
    while the WebAssembly build reads past the end of its memory and does not come back.
    There is no exception to catch and in a notebook it takes the reader's kernel with it.
    So this pads to the right length every time rather than trusting what it was handed,
    and nothing outside this module gets to supply the list.
    """
    needed = _slots_needed(sequence)
    given = metadata.get("consts")
    consts = list(given) if isinstance(given, list) else []
    known = isinstance(given, list) and len(consts) >= needed
    consts.extend(Unknown() for _ in range(needed - len(consts)))
    return consts, known


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
    #: Did the optimizer get the real constant values? False on a build whose codegen
    #: metadata has no consts key, Pyodide being the one we have measured. The optimizer
    #: still runs there, on placeholders, so `optimized` is a real answer to a different
    #: question and not what this source compiles to. Check this before saying anything
    #: about what the optimizer did.
    constants_known: bool = True

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

    consts, constants_known = _consts_for(sequence, metadata)
    optimized_sequence = internal.optimize_cfg(sequence, consts, 0)
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
        constants_known=constants_known,
    )


def innermost_codegen(source: str, filename: str = "<pyxray>") -> list[RawInstruction]:
    """What the code generator emitted for the innermost code unit in this source.

    `stages` keeps the top level sequence, which is the right answer when the source is one
    module and the wrong one when the point being made is about a function body. The compiler
    holds each nested unit as its own sequence hanging off the one around it, so walking in is
    a matter of following the first nested sequence until there are none left.

    This is the generator's output rather than the finished code object's, which matters: the
    optimizer rewrites some of these instructions into specialized forms, so a disassembly is
    not a fair picture of what this pass produced.
    """
    internal = _internal()
    sequence, _metadata = internal.compiler_codegen(ast.parse(source, filename), filename, 0)
    while nested := sequence.get_nested():
        sequence = nested[0]
    return _instructions(sequence)


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
    if not result.constants_known:
        # Only ever true in a browser. Saying it here rather than in the lesson text means
        # the reader is told next to the output they are looking at, which is where the
        # wrong conclusion would otherwise be drawn.
        lines.append(
            "This build did not hand over the constant values, so the optimizer ran "
            "without them. Nothing above was folded, and parts of the right column are "
            "not what this source really compiles to."
        )
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
