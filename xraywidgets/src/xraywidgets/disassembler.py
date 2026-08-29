"""Type Python, see the bytecode, and turn on the parts that are usually hidden.

`dis.dis` prints a good table and stops there. The four things a reader keeps needing next
are not in it: which opcodes the interpreter has rewritten into specialized forms, the
inline cache entries that take up real bytes between the instructions, how deep the value
stack is at each point, and the exception table, which is where a `try` went after 3.11.
Each of those is a toggle here, off by default, because a first disassembly with all four
on is a wall.

Every number here comes from `pyxray`, which is the same module the lessons import when they
print a disassembly into a plain cell. That matters more than it sounds. A reader who checks
a widget against `dis` and finds a disagreement has not found a rendering bug, they have
learned that the material cannot be trusted, and they are right to.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import ClassVar

from pyxray import bytecode, stack

from .base import Widget
from .html import Raw, element, join
from .parts import chip, error, head, source, table, toggles
from .strings import text
from .style import PREFIX

#: The toggles, in the order they appear, with the string that labels each one. The order is
#: the order they become useful: what the interpreter did to the code, then what is between
#: the instructions, then what the stack is doing, then what happens when it all goes wrong.
FLAGS: tuple[tuple[str, str], ...] = (
    ("adaptive", "disassembler.adaptive"),
    ("caches", "disassembler.caches"),
    ("depths", "disassembler.depths"),
    ("exceptions", "disassembler.exceptions"),
)


@dataclass
class Disassembler(Widget):
    """One block of Python and its bytecode, with four things you can turn on.

    The source can be a string, a function, a method or a code object, which is whatever
    `pyxray.bytecode.code_of` accepts, so a lesson can hand it the function it was just
    talking about rather than the text of it.
    """

    slug: ClassVar[str] = "disassembler"

    code: str = "answer = 6 * 7"
    adaptive: bool = False
    caches: bool = False
    depths: bool = False
    exceptions: bool = False
    title: str = ""

    def state(self) -> dict[str, object]:
        """The rows, the toggles and the version, as plain data.

        A source string that does not compile is a state and not an exception. The reader is
        typing, and half typed Python does not compile most of the time, so a widget that
        raised would spend most of its life as a traceback.
        """
        try:
            rows = self.rows()
        except SyntaxError as broken:
            return {
                "code": self.code,
                "title": self.title or text("disassembler.title"),
                "flags": self.flags(),
                "version": text("common.python", version=self.version()),
                "error": text("common.error", reason=str(broken.msg)),
                "rows": [],
                "handlers": [],
            }
        return {
            "code": self.code,
            "title": self.title or text("disassembler.title"),
            "flags": self.flags(),
            "version": text("common.python", version=self.version()),
            "error": "",
            "rows": rows,
            "handlers": self.handlers(),
        }

    def version(self) -> str:
        """The interpreter this disassembly came from, which is not always the reader's.

        Written next to the table because bytecode changes between versions more than almost
        anything else in Python, and a listing without a version on it is a listing somebody
        will quote in three years.
        """
        return ".".join(str(part) for part in sys.version_info[:3])

    def flags(self) -> list[dict[str, object]]:
        """The toggle row as data, so the static and live versions cannot disagree on it."""
        return [
            {"name": name, "label": text(key), "on": bool(getattr(self, name))}
            for name, key in FLAGS
        ]

    def rows(self) -> list[dict[str, object]]:
        """One entry per instruction, plus one per run of inline caches when those are on.

        The stack heights are looked up by offset rather than zipped, because `stack.walk`
        leaves out instructions it cannot reach and zipping two lists of different lengths
        silently shifts every row after the first gap.
        """
        instructions = bytecode.disassemble(self.code, adaptive=self.adaptive)
        heights = {}
        if self.depths:
            heights = {step.offset: (step.before, step.after) for step in stack.walk(self.code)}
        rows: list[dict[str, object]] = []
        for item in instructions:
            before, after = heights.get(item.offset, (None, None))
            rows.append(
                {
                    "kind": "instruction",
                    "offset": item.offset,
                    "opname": item.opname,
                    "arg": "" if item.arg is None else str(item.arg),
                    "argrepr": item.argrepr,
                    "meaning": bytecode.argument_meaning(item.base_opname),
                    "specialized": item.specialized,
                    "base": item.base_opname,
                    "jump_target": item.jump_target,
                    "is_target": item.is_jump_target,
                    "before": before,
                    "after": after,
                }
            )
            if self.caches and item.caches:
                rows.append(
                    {
                        "kind": "cache",
                        "offset": item.offset + 2,
                        "text": text("disassembler.cache_row", count=item.caches),
                        "bytes": 2 * item.caches,
                    }
                )
        return rows

    def handlers(self) -> list[dict[str, object]]:
        """The exception table as sentences, because the raw five numbers mean nothing yet."""
        if not self.exceptions:
            return []
        return [
            {
                "start": one.start,
                "end": one.end,
                "target": one.target,
                "depth": one.depth,
                "lasti": one.lasti,
                "text": text(
                    "disassembler.exception_range",
                    start=one.start,
                    end=one.end,
                    target=one.target,
                    depth=one.depth,
                    lasti=text("disassembler.lasti") if one.lasti else "",
                ),
            }
            for one in bytecode.exception_table(self.code)
        ]

    def markup(self, state: dict[str, object], *, live: bool = False) -> Raw:
        """The source, the toggles, the table, the exception table, and the notice."""
        count = text("disassembler.count", count=len(state["rows"]))
        parts = [
            head(state["title"], state["version"], count),
            source(state["code"], live=live),
            toggles([(one["name"], one["label"], one["on"]) for one in state["flags"]], live=live),
        ]
        if state["error"]:
            parts.append(error(state["error"]))
        elif not state["rows"]:
            parts.append(element("p", text("common.nothing"), class_=f"{PREFIX}-note"))
        else:
            parts.append(table(self.headings(), [self.row(one) for one in state["rows"]]))
        if self.exceptions:
            parts.append(self.exception_block(state["handlers"]))
        if not live:
            parts.append(self.notice())
        return join(parts)

    def headings(self) -> list[str]:
        """The column names, with the stack column present only when it is turned on."""
        names = [
            text("disassembler.offset"),
            text("disassembler.instruction"),
            text("disassembler.argument"),
            text("disassembler.meaning"),
        ]
        if self.depths:
            names.insert(2, text("disassembler.depth"))
        return names

    def row(self, entry: dict[str, object]) -> Raw:
        """One table row, either an instruction or a run of caches between two of them."""
        if entry["kind"] == "cache":
            return element(
                "tr",
                element("td", entry["offset"], class_=f"{PREFIX}-mono"),
                element("td", entry["text"], colspan=str(len(self.headings()) - 1)),
                class_=f"{PREFIX}-cache",
            )
        cells = [
            element("td", entry["offset"], class_=f"{PREFIX}-mono"),
            element("td", self.instruction(entry), class_=f"{PREFIX}-mono"),
            element("td", entry["argrepr"] or entry["arg"], class_=f"{PREFIX}-mono"),
            element("td", self.meaning(entry)),
        ]
        if self.depths:
            cells.insert(2, element("td", self.depth(entry), class_=f"{PREFIX}-mono"))
        return element("tr", join(cells))

    def instruction(self, entry: dict[str, object]) -> Raw:
        """The opcode name, with a chip beside it when the interpreter rewrote it.

        The chip says the word "specialized" and names the opcode it came from. It is not
        just a colour, and it is not just a symbol, because a reader meeting their first
        specialized opcode needs the word before the colour means anything to them.
        """
        if not entry["specialized"]:
            return element("span", entry["opname"])
        return join(
            [
                element("span", entry["opname"]),
                " ",
                chip(
                    text("disassembler.specialized"),
                    "focus",
                    title=f"{entry['opname']} is a specialized form of {entry['base']}",
                ),
            ]
        )

    def depth(self, entry: dict[str, object]) -> str:
        """The stack height either side of the instruction, or a dash where it is unknown.

        A dash rather than a blank. An instruction the walk never reached has no honest
        height, and an empty cell reads as zero.
        """
        if entry["before"] is None:
            return "-"
        return f"{entry['before']} to {entry['after']}"

    def meaning(self, entry: dict[str, object]) -> Raw:
        """What the argument is for, plus where a jump goes if it is one."""
        parts = [entry["meaning"]]
        if entry["jump_target"] is not None:
            parts.append(" ")
            parts.append(
                chip(text("disassembler.jump", target=entry["jump_target"]), "intermediate")
            )
        return join(parts)

    def exception_block(self, handlers: list[dict[str, object]]) -> Raw:
        """The exception table, as sentences, or the sentence that says there is not one."""
        if not handlers:
            return element("p", text("disassembler.no_exceptions"), class_=f"{PREFIX}-note")
        return element(
            "ul",
            join(element("li", one["text"]) for one in handlers),
            class_=f"{PREFIX}-note",
        )

    def _anywidget(self, anywidget: object, traitlets: object) -> object:
        """The live version: the same state, with traits the front end can change.

        Only the toggles and the source are traits the front end writes. `state` is written
        by Python whenever one of those changes, and the front end never computes a row, so
        there is no second implementation of what a disassembly says.
        """
        owner = self

        class LiveDisassembler(anywidget.AnyWidget):
            _esm = owner.esm()
            _css = owner.css()
            code = traitlets.Unicode(owner.code).tag(sync=True)
            adaptive = traitlets.Bool(owner.adaptive).tag(sync=True)
            caches = traitlets.Bool(owner.caches).tag(sync=True)
            depths = traitlets.Bool(owner.depths).tag(sync=True)
            exceptions = traitlets.Bool(owner.exceptions).tag(sync=True)
            view = traitlets.Dict(owner.view()).tag(sync=True)

            @traitlets.observe("code", "adaptive", "caches", "depths", "exceptions")
            def _recompute(self, _change):
                owner.code = self.code
                for name, _ in FLAGS:
                    setattr(owner, name, getattr(self, name))
                self.view = owner.view()

        return LiveDisassembler()
