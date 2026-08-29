"""The bits of markup more than one widget needs, so they only look one way.

There is one rule enforced here rather than remembered, and it is `chip`. Every coloured
thing in a widget is a chip, and a chip cannot be made without words in it. Colour never
carries information on its own in this project: not for a reader with any of the common
kinds of colour blindness, not in a printed handout, and not in a screenshot somebody pasted
into a chat with the saturation eaten by compression. Making the label a required argument
is the cheapest way to keep that true, because the alternative is a review comment that has
to be written every time.
"""

from __future__ import annotations

from collections.abc import Sequence

from pyxray import theme

from .html import Raw, element, join
from .style import PREFIX


def chip(label: str, tone: str = "quiet", *, title: str = "") -> Raw:
    """A small coloured badge, which always has words in it.

    The tone is checked against the theme rather than pasted into a class name, so a typo is
    an error here instead of an unstyled grey pill in a notebook.
    """
    if not label.strip():
        raise ValueError("a chip has to have a label, because colour is never the only signal")
    theme.tone(tone)
    return element("span", label, class_=f"{PREFIX}-chip {PREFIX}-{tone}", title=title or None)


def head(title: str, *notes: object) -> Raw:
    """The title line, with whatever short remarks belong beside it."""
    return element(
        "div",
        element("span", title, class_=f"{PREFIX}-title"),
        join(element("span", note, class_=f"{PREFIX}-note") for note in notes),
        class_=f"{PREFIX}-head",
    )


def source(code: str, *, live: bool = False) -> Raw:
    """The reader's own code, in the input tone, typed into or just shown back to them.

    A `<textarea>` when the widget is live and a plain block when it is not. Not a `<div>`
    with `contenteditable`, which looks the same and behaves differently in every browser,
    and which a screen reader does not announce as somewhere to type.
    """
    if live:
        return element(
            "textarea",
            code,
            class_=f"{PREFIX}-source",
            data_role="code",
            spellcheck="false",
            rows=str(max(code.count("\n") + 1, 2)),
        )
    return element("div", code, class_=f"{PREFIX}-source")


def error(message: str) -> Raw:
    """Something did not work, said in the warning tone with the reason in it."""
    return element("div", message, class_=f"{PREFIX}-error")


def toggles(options: Sequence[tuple[str, str, bool]], *, live: bool = False) -> Raw:
    """The row of on and off buttons above a widget.

    Real `<button>` elements with `aria-pressed`, not styled `<div>`s. That is what makes
    them reachable by tab and operable by space bar without a line of JavaScript, and it is
    what a screen reader needs in order to say whether one is on. The static rendering
    disables them, because a button that looks live and does nothing is worse than one that
    says it is not.
    """
    return element(
        "div",
        join(
            element(
                "button",
                label,
                type="button",
                class_=f"{PREFIX}-toggle",
                data_flag=name,
                aria_pressed="true" if on else "false",
                disabled=not live,
            )
            for name, label, on in options
        ),
        class_=f"{PREFIX}-toggles",
        role="group",
    )


def table(headings: Sequence[str], rows: Sequence[Raw]) -> Raw:
    """A table with a real header row, so the columns are announced with the cells."""
    return element(
        "table",
        element("thead", element("tr", join(element("th", one, scope="col") for one in headings))),
        element("tbody", join(rows)),
    )
