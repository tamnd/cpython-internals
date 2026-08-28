"""The value stack, which is the thing you have to be holding in your head to read bytecode.

Every instruction takes some values off the stack and puts some back. Once you know those
two numbers for an instruction you can read a listing without running it, and `dis` will
not tell you either of them.

The other half of this module is `high_water`, which works out `co_stacksize` from a
finished code object. That is a reimplementation of `calculate_stackdepth` in
`Python/flowgraph.c`, written in Python, and there is a test that runs it over every code
object in the standard library and compares. Agreement on thirty three thousand code
objects is a much better argument that the rule has been described correctly than any
amount of prose about it.
"""

from __future__ import annotations

import dis
import itertools
import types
from dataclasses import dataclass

from .bytecode import CodeLike, code_of

# Instructions after which control does not simply carry on to the next instruction. Two
# of them jump and the rest leave the frame. Anything else, including a conditional jump,
# can fall through and the walk keeps going.
LEAVES_THE_LINE = frozenset(
    {
        "JUMP_FORWARD",
        "JUMP_BACKWARD",
        "JUMP_BACKWARD_NO_INTERRUPT",
        "RETURN_VALUE",
        "RAISE_VARARGS",
        "RERAISE",
    }
)


@dataclass(frozen=True)
class Step:
    """One instruction, with the stack height either side of it."""

    offset: int
    opname: str
    arg: int | None
    argrepr: str
    before: int
    after: int
    jump_to: int | None = None

    @property
    def effect(self) -> int:
        """How much taller the stack got. Negative means the instruction consumed values."""
        return self.after - self.before


def _handlers(code: types.CodeType) -> list[tuple[int, int]]:
    """Where an exception can land, and how deep the stack is when it does.

    The exception table records, for each protected range, the handler offset and the
    stack depth to unwind to. The handler then gets the exception itself pushed on top,
    and one more slot if the entry asks for the instruction offset to be pushed too.
    Miss either of those and every function with a `try` in it comes out one or two short.

    `dis._parse_exception_table` is private. The alternative is decoding `co_exceptiontable`
    by hand, which is a varint format that deserves its own lesson rather than a helper
    function nobody reads.
    """
    parse = getattr(dis, "_parse_exception_table", None)
    if parse is None:
        return []
    return [(entry.target, entry.depth + (1 if entry.lasti else 0) + 1) for entry in parse(code)]


def _reachable(code: types.CodeType) -> tuple[dict[int, int], int]:
    """Walk every path through the code, recording the stack height entering each instruction.

    This follows the same shape as `calculate_stackdepth`: start at the top with an empty
    stack, follow both sides of every branch, and keep the largest height seen. Cycles are
    fine because a loop that changed the stack height each time round would grow without
    limit, so the compiler already guarantees it does not.
    """
    instructions = {item.offset: item for item in dis.get_instructions(code)}
    offsets = sorted(instructions)
    following = dict(itertools.pairwise(offsets))

    entering: dict[int, int] = {}
    pending = [(0, 0), *_handlers(code)]
    highest = 0

    while pending:
        offset, depth = pending.pop()
        while offset is not None:
            # A path that reaches here no lower than a path we already followed cannot
            # find anything new further on, so stop rather than walk it again.
            if entering.get(offset, -1) >= depth:
                break
            entering[offset] = depth
            item = instructions[offset]
            try:
                net = dis.stack_effect(item.opcode, item.arg)
            except ValueError:
                # A specialized opcode has no declared effect. Nothing the compiler emits
                # is specialized, so this only happens on adaptive bytecode.
                break
            highest = max(highest, depth)
            if item.jump_target is not None:
                taken = depth + dis.stack_effect(item.opcode, item.arg, jump=True)
                pending.append((item.jump_target, taken))
            depth += net
            if item.opname in LEAVES_THE_LINE:
                break
            offset = following.get(offset)

    return entering, highest


def high_water(target: CodeLike) -> int:
    """The tallest the stack ever gets, which is what `co_stacksize` records.

    The frame is allocated once with room for this many values, so it is worked out at
    compile time by walking the code rather than measured while the code runs.

    The floor of one is not part of the walk. A function whose body is a bare `raise`
    never pushes anything, and CPython still gives it a stack of one because a frame with
    no room at all is a shape the rest of the interpreter does not expect. That is in
    `init_code` rather than in the depth calculation, and copying the walk without it
    leaves you disagreeing with CPython on exactly those functions.
    """
    return max(1, _reachable(code_of(target))[1])


def walk(target: CodeLike) -> list[Step]:
    """Every instruction with the stack height before and after it.

    Heights come from the path the walk reached first, which for straight line code is
    the only path. An instruction the walk never reaches at all is left out, since there
    is no honest height to print for it.
    """
    code = code_of(target)
    entering, _ = _reachable(code)
    steps = []
    for item in dis.get_instructions(code):
        if item.offset not in entering:
            continue
        before = entering[item.offset]
        try:
            after = before + dis.stack_effect(item.opcode, item.arg)
        except ValueError:
            after = before
        steps.append(
            Step(
                offset=item.offset,
                opname=item.opname,
                arg=item.arg,
                argrepr=item.argrepr,
                before=before,
                after=after,
                jump_to=item.jump_target,
            )
        )
    return steps


def table(target: CodeLike) -> str:
    """The disassembly with a stack column, which is how you read one without running it.

    Each row shows the height going in, the height coming out, and a bar for the height
    coming out. The tallest bar is the number in `co_stacksize`.

    Where a row's incoming height does not match the previous row's outgoing height, the
    only way to arrive there is by a jump from somewhere else. That is worth noticing
    rather than smoothing over, because the listing is in address order and the program is
    not.
    """
    steps = walk(target)
    tallest = max((step.after for step in steps), default=0)
    width = max((len(step.opname) for step in steps), default=0)
    lines = []
    for step in steps:
        arg = "" if step.arg is None else f"{step.arg:>4}"
        note = f" ({step.argrepr})" if step.argrepr else ""
        bar = "#" * step.after + "." * (tallest - step.after)
        lines.append(
            f"{step.offset:>4}  {step.opname:<{width}} {arg:>4}{note:<22}"
            f"  {step.before} -> {step.after}  {bar}".rstrip()
        )
    return "\n".join(lines)
