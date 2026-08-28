"""Bytecode, shown the way you need to see it rather than the way `dis` prints it.

`dis` is good and this does not replace it. What it adds is the three things a lesson
keeps needing and `dis` does not give you as data: the specialized opcode next to the
one the compiler actually emitted, the inline cache entries that follow an instruction,
and a diff between two disassemblies.
"""

from __future__ import annotations

import dis
import types
from dataclasses import dataclass

from ._opcodes import base_name, cache_entries, is_specialized

CodeLike = types.CodeType | types.FunctionType | types.MethodType | str


@dataclass(frozen=True)
class Instruction:
    """One instruction, with everything a lesson needs to explain it."""

    offset: int
    opname: str
    base_opname: str
    opcode: int
    arg: int | None
    argrepr: str
    line: int | None
    is_jump_target: bool
    jump_target: int | None
    caches: int
    specialized: bool

    @property
    def total_size(self) -> int:
        """Bytes this instruction occupies, including its inline caches.

        A reader counting offsets by hand and getting them wrong is almost always missing
        the caches, because they are invisible in ordinary `dis` output but they are real
        bytes in `co_code` and the offsets step over them.
        """
        return 2 + 2 * self.caches


def code_of(target: CodeLike) -> types.CodeType:
    """Get a code object out of whatever the reader handed us.

    A source string is compiled, so that a lesson can disassemble `"x = 1 + 2"` without
    the reader having to know that `compile` exists yet.
    """
    if isinstance(target, str):
        return compile(target, "<pyxray>", "exec")
    if isinstance(target, types.CodeType):
        return target
    code = getattr(target, "__code__", None)
    if code is None:
        code = getattr(getattr(target, "__func__", None), "__code__", None)
    if code is None:
        raise TypeError(f"cannot get a code object from {type(target).__name__}")
    return code


def disassemble(target: CodeLike, *, adaptive: bool = False) -> list[Instruction]:
    """The instruction stream, as data.

    With ``adaptive=False`` you see what the compiler emitted. With ``adaptive=True`` you
    see what the interpreter has rewritten it into after running it, which is where
    specialization becomes visible. Both are useful and they are different questions, so
    they are the same function with a flag rather than two functions.
    """
    code = code_of(target)
    instructions = []
    for item in dis.get_instructions(code, adaptive=adaptive, show_caches=False):
        name = item.opname
        instructions.append(
            Instruction(
                offset=item.offset,
                opname=name,
                base_opname=base_name(name),
                opcode=item.opcode,
                arg=item.arg,
                argrepr=item.argrepr,
                line=item.line_number,
                is_jump_target=item.is_jump_target,
                jump_target=getattr(item, "jump_target", None),
                caches=cache_entries(name),
                specialized=is_specialized(name),
            )
        )
    return instructions


def table(target: CodeLike, *, adaptive: bool = False, show_caches: bool = False) -> str:
    """A readable disassembly, with a column for the family an opcode came from."""
    rows = disassemble(target, adaptive=adaptive)
    lines = []
    last_line = None
    for item in rows:
        prefix = ""
        if item.line is not None and item.line != last_line:
            prefix = f"{item.line:>4}"
            last_line = item.line
        marker = ">>" if item.is_jump_target else "  "
        family = f"  (from {item.base_opname})" if item.specialized else ""
        cache = f"  +{item.caches} cache" if show_caches and item.caches else ""
        arg = "" if item.arg is None else f"{item.arg:>4}"
        lines.append(
            f"{prefix:>4} {marker} {item.offset:>4}  {item.opname:<32} {arg:>4}"
            f"  {item.argrepr}{family}{cache}".rstrip()
        )
    return "\n".join(lines)


def opnames(target: CodeLike, *, adaptive: bool = False) -> list[str]:
    """Just the instruction names, which is what most comparisons actually want."""
    return [item.opname for item in disassemble(target, adaptive=adaptive)]


def diff(left: CodeLike, right: CodeLike, *, labels: tuple[str, str] = ("left", "right")) -> str:
    """Compare two disassemblies side by side, aligned on position.

    Written for the lesson that compiles the same logic three ways and asks which one the
    compiler likes better. Alignment is by index rather than by a real diff algorithm,
    because a real diff hides exactly the thing the lesson is pointing at, which is that
    one version has fewer instructions than the other.
    """
    a = opnames(left)
    b = opnames(right)
    width = max((len(name) for name in a), default=0)
    width = max(width, len(labels[0]), 10)

    lines = [f"{labels[0]:<{width}}  {labels[1]}", f"{'-' * width}  {'-' * len(labels[1])}"]
    for index in range(max(len(a), len(b))):
        left_name = a[index] if index < len(a) else ""
        right_name = b[index] if index < len(b) else ""
        mark = "  " if left_name == right_name else "| "
        lines.append(f"{left_name:<{width}}  {mark}{right_name}".rstrip())
    lines.append("")
    lines.append(f"{len(a)} instructions vs {len(b)}")
    return "\n".join(lines)


def constants(target: CodeLike) -> list[tuple[int, str, str]]:
    """`co_consts` as index, type name and repr, including nested code objects."""
    code = code_of(target)
    rows = []
    for index, const in enumerate(code.co_consts):
        if isinstance(const, types.CodeType):
            rows.append((index, "code", f"<code {const.co_name}>"))
        else:
            rows.append((index, type(const).__name__, repr(const)))
    return rows


def line_table(target: CodeLike) -> list[tuple[int, int, int | None]]:
    """The decoded line table as (start offset, end offset, line number).

    This is `co_lines()` with a name that says what it is. The encoded form in
    `co_linetable` is one of the more intricate things in the code object and it gets its
    own lesson; this is the decoded view a reader needs long before then.
    """
    return list(code_of(target).co_lines())
