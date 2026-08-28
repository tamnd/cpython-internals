"""Watching the interpreter run, one instruction at a time, from ordinary Python.

`sys.monitoring` arrived in 3.12 and it can report every instruction the interpreter
executes. That is enough to build a stepper without a debugger, without C, and without
patching anything, which is the whole reason this module exists.

One thing it cannot do is show you the values on the stack. Nothing in the standard
library can. What it can do is tell you which instruction ran and in what order, and
`pyxray.stack` already knows how tall the stack is at every offset, so putting the two
together gives you the height at every step of a real run. The heights are worked out
ahead of time and the order is observed, and this module keeps that distinction visible
rather than pretending it measured something it did not.
"""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass

from . import stack
from .bytecode import CodeLike, code_of, disassemble

# The four ids `sys.monitoring` reserves have owners, and stepping on a running profiler
# or coverage tool would be rude. 3 and 4 belong to nobody, so that is where we live.
FREE_TOOL_IDS = (3, 4)


@dataclass(frozen=True)
class Moment:
    """One thing that happened, in the order it happened."""

    step: int
    kind: str
    offset: int
    opname: str
    argrepr: str
    line: int | None
    depth_before: int
    depth_after: int

    @property
    def effect(self) -> int:
        return self.depth_after - self.depth_before


@dataclass
class Recording:
    """What came back from a run: the answer, and everything that happened on the way."""

    result: object
    moments: list[Moment]
    code: types.CodeType

    @property
    def deepest(self) -> int:
        """The tallest the stack got during this particular run."""
        return max((moment.depth_after for moment in self.moments), default=0)

    def table(self, *, bars: bool = True) -> str:
        """The run as a listing, one line per instruction, in execution order."""
        width = max((len(moment.opname) for moment in self.moments), default=0)
        tallest = max(self.deepest, 1)
        lines = []
        for moment in self.moments:
            bar = "#" * moment.depth_after + "." * (tallest - moment.depth_after)
            trail = f"  {bar}" if bars else ""
            lines.append(
                f"{moment.step:>4}  {moment.offset:>4}  {moment.opname:<{width}}"
                f"  {moment.argrepr:<18}"
                f"  {moment.depth_before} -> {moment.depth_after}{trail}".rstrip()
            )
        return "\n".join(lines)


def _borrow_a_tool_id(name: str) -> int:
    """Find a monitoring slot nobody is using, or say clearly that they are all taken."""
    for tool_id in FREE_TOOL_IDS:
        if sys.monitoring.get_tool(tool_id) is None:
            sys.monitoring.use_tool_id(tool_id, name)
            return tool_id
    raise RuntimeError(
        "every sys.monitoring tool id is in use, "
        "which usually means a debugger or coverage tool is running"
    )


def run(function: CodeLike, /, *args: object, **kwargs: object) -> Recording:
    """Call `function` and record every instruction it executes.

    Only the function's own instructions are recorded. Anything it calls runs at full
    speed and shows up as nothing at all, which keeps the listing short enough to read.
    """
    code = code_of(function)
    static = {step.offset: step for step in stack.walk(code)}
    described = {item.offset: item for item in disassemble(code)}
    moments: list[Moment] = []

    def remember(kind: str, offset: int) -> None:
        item = described.get(offset)
        known = static.get(offset)
        moments.append(
            Moment(
                step=len(moments),
                kind=kind,
                offset=offset,
                opname=item.opname if item else "?",
                argrepr=item.argrepr if item else "",
                line=item.line if item else None,
                depth_before=known.before if known else 0,
                depth_after=known.after if known else 0,
            )
        )

    events = sys.monitoring.events
    tool_id = _borrow_a_tool_id("pyxray stepper")
    try:
        sys.monitoring.register_callback(
            tool_id, events.PY_START, lambda _code, offset: remember("start", offset)
        )
        sys.monitoring.register_callback(
            tool_id, events.INSTRUCTION, lambda _code, offset: remember("instruction", offset)
        )
        sys.monitoring.set_local_events(tool_id, code, events.PY_START | events.INSTRUCTION)
        result = function(*args, **kwargs)
    finally:
        sys.monitoring.set_local_events(tool_id, code, 0)
        sys.monitoring.free_tool_id(tool_id)

    return Recording(result=result, moments=moments, code=code)


def table(function: CodeLike, /, *args: object, **kwargs: object) -> str:
    """Run it and hand back the listing, for when you do not want the recording itself."""
    return run(function, *args, **kwargs).table()


def chain(frame: types.FrameType | None = None) -> list[tuple[str, int]]:
    """The frames currently on the stack, innermost first, as name and line number.

    This is what `traceback` prints, without the formatting. Asking for it is what makes
    CPython build real frame objects, because the interpreter does not have any until
    somebody wants one.
    """
    current = frame if frame is not None else sys._getframe(1)
    found = []
    while current is not None:
        found.append((current.f_code.co_name, current.f_lineno))
        current = current.f_back
    return found
