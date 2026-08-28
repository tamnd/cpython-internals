"""Bytecode, shown the way you need to see it rather than the way `dis` prints it.

`dis` is good and this does not replace it. What it adds is the three things a lesson
keeps needing and `dis` does not give you as data: the specialized opcode next to the
one the compiler actually emitted, the inline cache entries that follow an instruction,
and a diff between two disassemblies.
"""

from __future__ import annotations

import dis
import opcode
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


# What the argument byte means for a handful of instructions where the generic answer
# ("a plain number") is true and useless. Everything else is classified from the tables in
# the `opcode` module, so this stays short on purpose. A test checks every name here still
# exists, because an opcode that gets renamed should break the build and not the reader.
ARGUMENT_NOTES = {
    "LOAD_SMALL_INT": "the integer itself, not an index",
    "LOAD_COMMON_CONSTANT": "which of the handful of values the interpreter keeps around",
    "BINARY_OP": "which operator, numbered by the order they appear in the C table",
    "CALL": "how many arguments are on the stack",
    "LOAD_FAST_LOAD_FAST": "two local slots packed into one byte, four bits each",
    "LOAD_FAST_BORROW_LOAD_FAST_BORROW": "two local slots packed into one byte, four bits each",
    "STORE_FAST_STORE_FAST": "two local slots packed into one byte, four bits each",
    "STORE_FAST_LOAD_FAST": "two local slots packed into one byte, four bits each",
    "COPY": "how far down the stack to copy from, counting from the top",
    "SWAP": "how far down the stack to swap with, counting from the top",
    "UNPACK_SEQUENCE": "how many values to spread out",
    "BUILD_TUPLE": "how many values to take off the stack",
    "BUILD_LIST": "how many values to take off the stack",
    "RESUME": "which kind of resume point this is: function start, after a yield, after an await",
}


def argument_meaning(opname: str) -> str:
    """What the argument byte of an instruction is counting or indexing.

    This is the question that stops a reader cold. `LOAD_CONST 1` and `LOAD_NAME 1` and
    `CALL 1` all print the same way and the 1 means three unrelated things. Nearly every
    answer is in the tables the `opcode` module already publishes, which is where these
    come from.
    """
    if opname in ARGUMENT_NOTES:
        return ARGUMENT_NOTES[opname]
    number = opcode.opmap.get(opname)
    if number is None:
        raise KeyError(f"no such instruction: {opname}")
    if number in opcode.hasconst:
        return "an index into co_consts"
    if number in opcode.hasname:
        return "an index into co_names"
    if number in opcode.haslocal:
        return "which local variable, by slot"
    if number in opcode.hasfree:
        return "which closed over variable, by slot"
    if number in opcode.hasjrel:
        return "how far to jump, in instructions rather than bytes"
    if number in opcode.hascompare:
        return "which comparison, encoded"
    if number in opcode.hasexc:
        return "where the exception handler starts"
    if number in opcode.hasarg:
        return "a plain number this instruction knows what to do with"
    return "nothing; the byte is written but never read"


@dataclass(frozen=True)
class Jump:
    """One jump, with the arithmetic that gets you from the argument to the target."""

    offset: int
    opname: str
    arg: int
    resumes_at: int
    target: int

    @property
    def backwards(self) -> bool:
        return self.target < self.offset

    def arithmetic(self) -> str:
        """The sum, written out, so a reader can check it against the listing."""
        sign = "-" if self.backwards else "+"
        return f"{self.resumes_at} {sign} {self.arg} * 2 = {self.target}"


def jumps(target: CodeLike) -> list[Jump]:
    """Every jump in the code, with where it lands and why.

    Jump arguments trip people up twice. They count instructions rather than bytes, so the
    argument is half the distance you measure with your finger. And they count from the
    instruction after this one including its caches, not from the jump itself, so an
    instruction with caches lands further along than the arithmetic suggests.
    """
    found = []
    for item in disassemble(target):
        if item.jump_target is None or item.arg is None:
            continue
        found.append(
            Jump(
                offset=item.offset,
                opname=item.opname,
                arg=item.arg,
                resumes_at=item.offset + item.total_size,
                target=item.jump_target,
            )
        )
    return found


def jump_table(target: CodeLike) -> str:
    """The jumps as a readable table, one line of arithmetic each."""
    found = jumps(target)
    width = max((len(jump.opname) for jump in found), default=0)
    lines = []
    for jump in found:
        way = "back" if jump.backwards else "on"
        lines.append(
            f"{jump.offset:>4}  {jump.opname:<{width}} {jump.arg:>4}"
            f"   {jump.arithmetic():<22}  jumps {way}"
        )
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
