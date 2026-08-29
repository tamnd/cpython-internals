"""Ask before you show. A question, some options, and an explanation for every one of them.

The reason this exists is that reading a disassembly teaches almost nothing on its own. A
reader looks at the listing, it makes sense, they move on, and their model of what the
compiler does is exactly as wrong as it was before, because nothing ever forced them to
commit to a prediction that could turn out wrong. Being wrong on purpose, in private, and
then finding out why is the part that sticks.

So a gate goes in front of the interesting output. Predict first, then look. And every wrong
option carries a written explanation, not just a cross, because a wrong option is only worth
offering if somebody could plausibly pick it, and if somebody could plausibly pick it then
the reason it is wrong is a thing worth teaching. A gate that only explains its right answer
is a multiple choice quiz, and multiple choice quizzes teach people to recognise answers
rather than to hold a model.

`Option` refuses to be built without that explanation, in the same way `parts.chip` refuses
to be built without a label. It is the cheapest way to keep a rule that would otherwise be a
review comment written over and over.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import ClassVar

from .base import Widget
from .html import Raw, element, join
from .parts import chip, head
from .strings import text
from .style import PREFIX


@dataclass(frozen=True)
class Option:
    """One answer a reader can pick, and why it is right or wrong.

    `why` is required on every option, including the correct one. On a wrong option it is
    the whole point of the exercise. On the right one it is the difference between a reader
    who guessed correctly and a reader who knows why they were correct, and those two look
    identical from the outside.
    """

    label: str
    why: str
    correct: bool = False

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("an option needs something to click on")
        if not self.why.strip():
            raise ValueError(
                f"the option {self.label!r} needs a reason, because an option nobody can be "
                "told why they got wrong is an option not worth offering"
            )


@dataclass
class PredictGate(Widget):
    """A question in front of an output, with the answer behind a gate.

    Nothing here checks anybody's work or keeps a score. The choice is recorded in the
    reader's own browser and goes nowhere else, which is deliberate: a reader who thinks a
    wrong answer is being logged somewhere stops guessing and starts reading ahead, and
    guessing is the entire mechanism.
    """

    slug: ClassVar[str] = "predict"

    question: str
    options: list[Option]
    #: A line the reader can run to see for themselves, shown once the answer is revealed.
    #: Optional, and worth writing whenever there is one, because an explanation a reader can
    #: check is a different kind of thing from an explanation they have to accept.
    check: str = ""
    #: Which option the reader picked, if any. Written by the front end.
    chosen: int | None = None
    title: str = ""

    def __post_init__(self) -> None:
        if not self.question.strip():
            raise ValueError("a prediction gate needs a question")
        correct = [one for one in self.options if one.correct]
        if len(self.options) < 2:
            raise ValueError("a prediction gate with fewer than two options is not a question")
        if len(correct) != 1:
            raise ValueError(
                f"{self.question!r} has {len(correct)} correct options, and needs exactly one"
            )

    @property
    def key(self) -> str:
        """A stable name for this question, for the reader's browser to file the answer under.

        A hash of the question text rather than a number, because the alternative is that
        every gate in a lesson needs a hand written id, ids get copied along with the block
        they came from, and a reader's answer to one question turns up pre-filled on another.
        """
        digest = hashlib.sha256(self.question.encode("utf-8")).hexdigest()
        return f"{PREFIX}-predict-{digest[:12]}"

    @property
    def answer(self) -> int:
        """Which option is the right one."""
        return next(index for index, one in enumerate(self.options) if one.correct)

    def state(self) -> dict[str, object]:
        """The question, the options, and whether the answer is showing yet."""
        return {
            "key": self.key,
            "title": self.title or text("predict.title"),
            "question": self.question,
            "check": self.check,
            "chosen": self.chosen,
            "revealed": self.chosen is not None,
            "correct": self.chosen == self.answer if self.chosen is not None else None,
            "options": [
                {
                    "index": index,
                    "label": one.label,
                    "why": one.why,
                    "correct": one.correct,
                    "picked": index == self.chosen,
                }
                for index, one in enumerate(self.options)
            ],
        }

    def markup(self, state: dict[str, object], *, live: bool = False) -> Raw:
        """The question and the options, with the answer gated.

        The two forms gate differently and both of them really do gate. When the widget is
        live the explanations appear once a reader has picked. When it is not, they go inside
        a `<details>`, which folds and unfolds with no JavaScript at all and is reachable
        from the keyboard, so a reader looking at a rendered notebook on GitHub still gets
        asked the question before they get told the answer.
        """
        parts: list[object] = [
            head(state["title"]),
            element("p", state["question"], class_=f"{PREFIX}-question"),
        ]
        if live:
            parts.append(self.buttons(state))
            if state["revealed"]:
                parts.append(self.verdict(state))
                parts.append(self.explanations(state))
                parts.append(self.check_line())
        else:
            parts.append(self.listing(state))
            parts.append(
                element(
                    "details",
                    element("summary", text("predict.reveal")),
                    self.explanations(state),
                    self.check_line(),
                    class_=f"{PREFIX}-reveal",
                )
            )
            parts.append(self.notice())
        return join(parts)

    def buttons(self, state: dict[str, object]) -> Raw:
        """The options as things to press, with the one already picked marked as pressed."""
        return element(
            "div",
            join(
                element(
                    "button",
                    one["label"],
                    type="button",
                    class_=f"{PREFIX}-option",
                    data_option=str(one["index"]),
                    aria_pressed="true" if one["picked"] else "false",
                )
                for one in state["options"]
            ),
            class_=f"{PREFIX}-options",
            role="group",
            aria_label=text("predict.options_label"),
        )

    def listing(self, state: dict[str, object]) -> Raw:
        """The options as a list, for the rendering where nothing can be pressed.

        A list and not disabled buttons. A disabled button says the thing it does is
        unavailable, and here the thing is not unavailable, it is just being done in the
        reader's head instead of in the page.
        """
        return element(
            "ol",
            join(element("li", one["label"]) for one in state["options"]),
            class_=f"{PREFIX}-options-list",
        )

    def verdict(self, state: dict[str, object]) -> Raw:
        """One line saying how it went, in words rather than in a colour."""
        right = state["correct"]
        return element(
            "p",
            chip(
                text("predict.right") if right else text("predict.wrong"),
                "durable" if right else "warning",
            ),
            class_=f"{PREFIX}-verdict",
        )

    def explanations(self, state: dict[str, object]) -> Raw:
        """Every option and why, not only the one that was picked and not only the right one.

        All of them, always. A reader who guessed right learns the most from the explanation
        of the option they nearly picked instead, and a reader who guessed wrong needs to see
        that their answer was a reasonable thing to think rather than a silly mistake.
        """
        rows = []
        for one in state["options"]:
            marks = [chip(text("predict.answer"), "durable")] if one["correct"] else []
            if one["picked"]:
                marks.append(chip(text("predict.yours"), "focus"))
            rows.append(
                element(
                    "li",
                    element("span", one["label"], class_=f"{PREFIX}-option-label"),
                    " ",
                    join(marks),
                    element("p", one["why"]),
                    class_=f"{PREFIX}-explanation",
                )
            )
        return element("ul", join(rows), class_=f"{PREFIX}-explanations")

    def check_line(self) -> Raw:
        """The line a reader can run to see it for themselves, if the gate has one."""
        if not self.check:
            return Raw("")
        return join(
            [
                element("p", text("predict.check"), class_=f"{PREFIX}-note"),
                element("div", self.check, class_=f"{PREFIX}-source"),
            ]
        )

    def _anywidget(self, anywidget: object, traitlets: object) -> object:
        """The live version. The front end writes which option was picked, and nothing else."""
        owner = self

        class LivePredictGate(anywidget.AnyWidget):
            _esm = owner.esm()
            _css = owner.css()
            chosen = traitlets.Int(-1).tag(sync=True)
            view = traitlets.Dict(owner.view()).tag(sync=True)

            @traitlets.observe("chosen")
            def _recompute(self, _change):
                owner.chosen = None if self.chosen < 0 else self.chosen
                self.view = owner.view()

        return LivePredictGate()
