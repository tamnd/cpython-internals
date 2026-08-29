"""One box of Python, and every form it takes on the way to a code object.

The pipeline is the first thing a lesson has to get across and the hardest thing to get
across in prose, because the point of it is that six things happen and each one throws away
something the one before it had. Text describes them one at a time. A reader who has just
finished the paragraph about the parser has forgotten what the token stream looked like.

So all six panes are on screen together and all six change when you type. Add a comment and
watch it appear in the tokens and be gone by the tree. Write `6 * 7` and watch the
multiplication survive code generation and vanish before the code object. That is one edit
and two panes, and it is a lot more convincing than a sentence saying that constants are
folded.

Two of the six panes need `_testinternalcapi`, which not every build ships. When it is
missing those two say so and the other four still work, because a widget that shows nothing
because one interpreter hook is absent teaches nobody anything about the four stages that
would have run fine.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import ClassVar

from pyxray import bytecode, compiler, tokens, trees

from .base import Widget
from .html import Raw, element, join
from .parts import chip, error, head, source
from .strings import text
from .style import PREFIX

#: The panes, in the order the compiler produces them, with the string that names each one
#: and whether it needs the internal compiler hooks. The order is the whole point of the
#: widget, so it lives in one tuple rather than being implied by the order of six methods.
PANES: tuple[tuple[str, str, bool], ...] = (
    ("tokens", "pipeline.tokens", False),
    ("tree", "pipeline.tree", False),
    ("symbols", "pipeline.symbols", False),
    ("codegen", "pipeline.codegen", True),
    ("optimized", "pipeline.optimized", True),
    ("code", "pipeline.code", False),
)

#: How many lines of a pane to show before cutting it off. Six panes of a hundred lines each
#: is a page nobody scrolls through, and the widget is for small examples: the lessons that
#: use it hand it one or two lines. The cut is announced rather than silent.
LIMIT = 40


@dataclass
class PipelineExplorer(Widget):
    """Six views of the same source, updating together.

    The source is a string and only a string here, unlike the disassembler, because the
    tokenizer and the parser both work on text. Handing this a function would mean going
    back to the file it came from, and a function typed into a notebook does not have one.
    """

    slug: ClassVar[str] = "pipeline"

    code: str = "answer = 6 * 7"
    title: str = ""

    def state(self) -> dict[str, object]:
        """The six panes, the summary line, and whatever went wrong."""
        common = {
            "code": self.code,
            "title": self.title or text("pipeline.title"),
            "version": text("common.python", version=compiler.python_version()),
            "internals": compiler.available(),
        }
        try:
            run = self.run()
            panes = self.panes(run)
        except SyntaxError as broken:
            return {
                **common,
                "error": text("common.error", reason=str(broken.msg)),
                "panes": [],
                "summary": "",
            }
        return {
            **common,
            "error": "",
            "panes": panes,
            "summary": run.summary() if run else "",
        }

    def panes(self, run: compiler.Stages | None) -> list[dict[str, object]]:
        """One entry per stage, in pipeline order, whether or not it could be computed."""
        return [
            {
                "name": name,
                "label": text(key),
                "available": run is not None or not needs_internals,
                **self.content(name, run),
            }
            for name, key, needs_internals in PANES
        ]

    def run(self) -> compiler.Stages | None:
        """The compiler stages, or `None` on a build without the internal hooks.

        `None` rather than an exception, because two of the six panes want it and four do
        not, and a widget that fell over here would take the four that work with it.
        """
        try:
            return compiler.stages(self.code)
        except compiler.Unavailable:
            return None

    def content(self, name: str, run: compiler.Stages | None) -> dict[str, object]:
        """The lines and the count for one pane, by name."""
        if name == "tokens":
            stream = tokens.stream(self.code)
            return self.lines(
                [str(one) for one in stream],
                text("pipeline.count_tokens", count=len(stream)),
            )
        if name == "tree":
            tree = ast.parse(self.code)
            return self.lines(
                trees.outline(tree).splitlines(),
                text("pipeline.count_nodes", count=sum(1 for _ in ast.walk(tree))),
            )
        if name == "symbols":
            scope = compiler.symbols(self.code)
            return self.lines(
                scope.tree().splitlines(),
                text("pipeline.count_scopes", count=sum(1 for _ in scope.walk())),
            )
        if name == "code":
            listing = bytecode.disassemble(self.code)
            return self.lines(
                [f"{one.offset:>4}  {one.opname} {self.argument(one)}".rstrip() for one in listing],
                text("pipeline.count_bytes", count=len(self.bytes())),
            )
        if run is None:
            return {"lines": [], "shown": 0, "hidden": 0, "count": text("pipeline.no_internals")}
        if name == "codegen":
            return self.lines(
                [str(one) for one in run.codegen],
                text("pipeline.count_instructions", count=len(run.codegen)),
            )
        return self.lines(
            [str(one) for one in run.optimized],
            text("pipeline.count_after", count=len(run.optimized), gone=run.removed_by_optimizer),
        )

    def argument(self, item: bytecode.Instruction) -> str:
        """What to print after an opcode name, in one column rather than two.

        `argrepr` is the readable form and is what you want whenever there is one, but plenty
        of opcodes leave it empty and put the whole story in `arg`. `LOAD_SMALL_INT` is the
        one that matters here: after the optimizer folds 6 * 7 the finished code says
        `LOAD_SMALL_INT 42`, and 42 lives in `arg` with `argrepr` empty. Printing only
        `argrepr` would drop the number this widget exists to show.
        """
        if item.argrepr:
            return item.argrepr
        return "" if item.arg is None else str(item.arg)

    def bytes(self) -> bytes:
        """The finished bytecode, so the last pane can say how many bytes it came to."""
        return bytecode.code_of(self.code).co_code

    def lines(self, produced: list[str], count: str) -> dict[str, object]:
        """One pane's text, cut to `LIMIT` lines, with the cut counted rather than hidden."""
        return {
            "lines": produced[:LIMIT],
            "shown": min(len(produced), LIMIT),
            "hidden": max(len(produced) - LIMIT, 0),
            "count": count,
        }

    def markup(self, state: dict[str, object], *, live: bool = False) -> Raw:
        """The source box, the six panes side by side, and the summary underneath."""
        parts = [
            head(state["title"], state["version"]),
            source(state["code"], live=live),
        ]
        if state["error"]:
            parts.append(error(state["error"]))
        else:
            parts.append(
                element(
                    "div",
                    join(self.pane(one) for one in state["panes"]),
                    class_=f"{PREFIX}-panes",
                )
            )
            if state["summary"]:
                parts.append(element("p", state["summary"], class_=f"{PREFIX}-note"))
        if not state["internals"]:
            parts.append(element("p", text("pipeline.why_no_internals"), class_=f"{PREFIX}-note"))
        if not live:
            parts.append(self.notice())
        return join(parts)

    def pane(self, entry: dict[str, object]) -> Raw:
        """One stage: its name, how much of it there is, and the text itself."""
        title = element("span", entry["label"], class_=f"{PREFIX}-pane-title")
        tone = "quiet" if entry["available"] else "warning"
        body: list[object] = [
            element("div", title, chip(entry["count"], tone), class_=f"{PREFIX}-pane-head")
        ]
        if entry["lines"]:
            body.append(element("pre", "\n".join(entry["lines"])))
        if entry["hidden"]:
            body.append(
                element(
                    "p",
                    text("pipeline.more_lines", count=entry["hidden"]),
                    class_=f"{PREFIX}-note",
                )
            )
        return element("div", join(body), class_=f"{PREFIX}-pane", data_stage=entry["name"])

    def _anywidget(self, anywidget: object, traitlets: object) -> object:
        """The live version. One trait, because there is one thing to change."""
        owner = self

        class LivePipeline(anywidget.AnyWidget):
            _esm = owner.esm()
            _css = owner.css()
            code = traitlets.Unicode(owner.code).tag(sync=True)
            view = traitlets.Dict(owner.view()).tag(sync=True)

            @traitlets.observe("code")
            def _recompute(self, _change):
                owner.code = self.code
                self.view = owner.view()

        return LivePipeline()
