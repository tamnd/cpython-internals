"""Where a name lives, decided before your program runs.

The tree from T03 knows that a line says `answer`. It does not know which `answer` that is,
and it cannot know, because the answer depends on the whole block the line sits in rather
than on the line itself. Working that out is a separate pass, and it happens in
Python/symtable.c:1139@v3.15.0rc1#analyze_block long before anything executes.

The result of that pass is a decision per name per block, and the decision is visible twice.
`symtable` shows you the compiler's own answer, and the bytecode shows you what the compiler
did with it, because a different scope produces a literally different opcode. This module
puts those two views in one table, since seeing them agree is the point.

Five answers are possible, and Python/compile.c:1009@v3.15.0rc1#_PyCompile_ResolveNameop is
where each one turns into an opcode family:

    local    a slot in the frame, read with LOAD_FAST
    cell     a box this block owns so an inner function can share it, read with LOAD_DEREF
    free     a box an enclosing function owns, also read with LOAD_DEREF
    global   the module dictionary, read with LOAD_GLOBAL
    name     looked up while the code runs, read with LOAD_NAME

The last one only happens at module level and in a class body, which is why the same line of
code compiles differently depending on whether you put it inside a function.
"""

from __future__ import annotations

import dis
import symtable
import types
from dataclasses import dataclass, field

#: What each scope means, in the order a reader meets them. Kept here rather than in the
#: lesson so the notebook and the tests are describing the same five things.
SCOPES: dict[str, str] = {
    "local": "a numbered slot in this call's frame",
    "cell": "a box this block owns, because an inner function reads it",
    "free": "a box an enclosing function owns",
    "global": "the module dictionary, then builtins",
    "name": "looked up while the code runs, in this block then globals then builtins",
}


@dataclass(frozen=True)
class Binding:
    """One name in one block, with the decision made about it and the opcodes that show it.

    `why` is the reason the decision came out this way, phrased the way you would say it out
    loud. It is worth carrying, because "global" is the answer for a name you declared global
    and for a name you simply never assigned, and those are not the same situation at all.
    """

    name: str
    scope: str
    why: str
    reads: tuple[str, ...] = ()
    writes: tuple[str, ...] = ()

    def __str__(self) -> str:
        seen = ", ".join(sorted(set(self.reads + self.writes))) or "never used here"
        return f"{self.name:<12} {self.scope:<8} {self.why:<48} {seen}"


@dataclass(frozen=True)
class Block:
    """One symbol table block: a module, a function, a class body or an annotation.

    A block is the unit the decision is made in. Not a line, not a file, and not a class
    plus its methods. Every `def`, every `lambda`, every `class` and the module itself get
    one, and a name can be local in one and global in the block right next to it.
    """

    name: str
    kind: str
    line: int
    depth: int
    bindings: list[Binding] = field(default_factory=list)

    def __getitem__(self, name: str) -> Binding:
        for binding in self.bindings:
            if binding.name == name:
                return binding
        raise KeyError(f"{name!r} is not a name in the {self.name!r} block")

    def __str__(self) -> str:
        head = f"{'  ' * self.depth}{self.kind} {self.name!r} (line {self.line})"
        rows = [f"{'  ' * self.depth}    {binding}" for binding in self.bindings]
        return "\n".join([head, *rows])


def _kind(entry: symtable.SymbolTable) -> str:
    """The block type as a plain string.

    `get_type` returns a str on 3.14 and a string enum on 3.15, and printing the enum in a
    lesson would put `SymbolTableType.FUNCTION` on the page, which teaches nobody anything.
    """
    return str(entry.get_type())


def _codes(code: types.CodeType, found: dict[tuple[str, int], types.CodeType]) -> None:
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            found[(const.co_name, const.co_firstlineno)] = const
            _codes(const, found)


#: Opcodes that read a name. `LOAD_ATTR` is deliberately not here: its argument is an
#: attribute on some object, which has nothing to do with the scope of anything.
_READS = frozenset(
    {
        "LOAD_FAST",
        "LOAD_FAST_CHECK",
        "LOAD_FAST_BORROW",
        "LOAD_FAST_AND_CLEAR",
        "LOAD_DEREF",
        "LOAD_FROM_DICT_OR_DEREF",
        "LOAD_GLOBAL",
        "LOAD_NAME",
        "LOAD_FROM_DICT_OR_GLOBALS",
        "MAKE_CELL",
    }
)

_WRITES = frozenset(
    {
        "STORE_FAST",
        "STORE_DEREF",
        "STORE_GLOBAL",
        "STORE_NAME",
        "DELETE_FAST",
        "DELETE_DEREF",
        "DELETE_GLOBAL",
        "DELETE_NAME",
    }
)


def _opcodes(code: types.CodeType | None) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Which opcodes read and which write each name, taken straight from the disassembly."""
    reads: dict[str, list[str]] = {}
    writes: dict[str, list[str]] = {}
    if code is None:
        return reads, writes
    for instruction in dis.get_instructions(code):
        # LOAD_GLOBAL prints its argument as `print + NULL` when the call sequence wants a
        # spare slot on the stack, which is a detail about calling and not about the name.
        name = instruction.argrepr.removesuffix(" + NULL").strip()
        if not name.isidentifier():
            continue
        if instruction.opname in _READS:
            reads.setdefault(name, []).append(instruction.opname)
        elif instruction.opname in _WRITES:
            writes.setdefault(name, []).append(instruction.opname)
    return reads, writes


def _scope(
    symbol: symtable.Symbol,
    entry: symtable.SymbolTable,
    code: types.CodeType | None,
) -> tuple[str, str]:
    """The decision for one name, and the reason it came out that way.

    The order here follows Python/symtable.c:669@v3.15.0rc1#analyze_name, which checks the
    two declarations first and only then looks at whether the name is assigned. That order
    is the reason a `global` statement wins over an assignment sitting right underneath it.
    """
    name = symbol.get_name()
    if symbol.is_declared_global():
        if not _function_like(entry):
            # A `global x` inside any function marks x explicitly global in the module block
            # too, which is why the module's own assignment becomes STORE_GLOBAL rather than
            # STORE_NAME. One line inside a function changed the opcode outside it.
            return "global", "a global statement somewhere in the file names it"
        return "global", "you wrote a global statement"
    if symbol.is_nonlocal():
        return "free", "you wrote a nonlocal statement"
    # 3.15 added `Symbol.is_cell`, and asking the code object works on 3.14 as well, so the
    # code object is what this uses. It is also the more convincing answer, because it comes
    # from the thing that will actually run.
    if code is not None and name in code.co_cellvars:
        return "cell", "assigned here, and an inner block reads it"
    if code is not None and name in code.co_freevars:
        return "free", "assigned in a function around this one"
    if symbol.is_local():
        why = (
            "it is a parameter"
            if symbol.is_parameter()
            else "it is assigned somewhere in this block"
        )
        return ("local", why) if _function_like(entry) else ("name", why)
    return "global", "it is never assigned in this block"


def _function_like(entry: symtable.SymbolTable) -> bool:
    """Does this block get frame slots, or a dictionary?

    Functions, lambdas and comprehensions get numbered slots. Modules and class bodies get a
    dictionary they fill in as they run, which is why you can call `exec` in one and have the
    result be visible and cannot do that in the other. The compiler asks the same question at
    Python/compile.c:1026@v3.15.0rc1#_PyCompile_ResolveNameop.
    """
    return _kind(entry) not in {"module", "class"}


def table(
    source: str,
    *,
    filename: str = "lesson.py",
    annotations: bool = False,
) -> list[Block]:
    """Every block in a piece of source, with every name in it and what was decided.

    Blocks come back in reading order, module first, each one after its parent.

    Annotation blocks are left out by default. Since PEP 649 every `def` gets one whether or
    not you annotated anything, so a four function file grows four extra blocks that are all
    empty and none of which the reader asked about. Pass `annotations=True` to see them.
    """
    top = symtable.symtable(source, filename, "exec")
    module = compile(source, filename, "exec")
    codes: dict[tuple[str, int], types.CodeType] = {}
    _codes(module, codes)

    blocks: list[Block] = []

    def visit(entry: symtable.SymbolTable, depth: int) -> None:
        kind = _kind(entry)
        if kind == "annotation" and not annotations:
            return
        code = module if depth == 0 else codes.get((entry.get_name(), entry.get_lineno()))
        reads, writes = _opcodes(code)
        bindings = []
        for symbol in entry.get_symbols():
            scope, why = _scope(symbol, entry, code)
            bindings.append(
                Binding(
                    name=symbol.get_name(),
                    scope=scope,
                    why=why,
                    reads=tuple(reads.get(symbol.get_name(), ())),
                    writes=tuple(writes.get(symbol.get_name(), ())),
                )
            )
        blocks.append(
            Block(
                # symtable calls the module block "top" and reports it as line 0. `dis` calls
                # the same thing "<module>" starting at line 1. Two names for one block is a
                # thing to spare the reader, so this uses the one they will see in a
                # disassembly.
                name="<module>" if depth == 0 else entry.get_name(),
                kind=kind,
                line=module.co_firstlineno if depth == 0 else entry.get_lineno(),
                depth=depth,
                bindings=sorted(bindings, key=lambda binding: binding.name),
            )
        )
        for child in entry.get_children():
            visit(child, depth + 1)

    visit(top, 0)
    return blocks


def show(source: str, **kwargs: object) -> str:
    """The whole table as text, one block after another, ready to print in a notebook."""
    return "\n\n".join(str(block) for block in table(source, **kwargs))  # type: ignore[arg-type]


def find(source: str, block: str, name: str, **kwargs: object) -> Binding:
    """The decision for one name in one named block.

    Handy in a test or in the middle of a sentence, where the surrounding table is noise and
    the one row is the claim being made.
    """
    for candidate in table(source, **kwargs):  # type: ignore[arg-type]
        if candidate.name == block:
            return candidate[name]
    raise KeyError(f"there is no block called {block!r} in this source")


def opcodes(source: str, block: str) -> list[tuple[str, str]]:
    """Every instruction in one block, as opcode and argument.

    `dis.dis` prints offsets, jump targets and cache entries, which are exactly right when
    you are reading bytecode and in the way when the only question is which load you got.
    """
    module = compile(source, "lesson.py", "exec")
    codes: dict[tuple[str, int], types.CodeType] = {}
    _codes(module, codes)
    found = module if block == "<module>" else None
    if found is None:
        for (name, _), code in codes.items():
            if name == block:
                found = code
                break
    if found is None:
        raise KeyError(f"nothing called {block!r} was compiled from this source")
    return [(each.opname, each.argrepr) for each in dis.get_instructions(found)]
