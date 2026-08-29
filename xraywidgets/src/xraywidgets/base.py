"""What every widget in this package is, and the two ways it can be shown.

A widget here is a plain Python object that knows how to compute its own state and how to
draw that state as HTML. It is not an `ipywidgets` subclass, it does not import anywidget,
and it works with nothing installed beyond `pyxray`. That is what `_repr_html_` gives you,
and it is what a reader gets on GitHub, in an nbconvert render of a lesson, in a PDF export,
and in the seconds before Pyodide has finished starting up.

Calling `.live()` on one asks for the interactive version, which needs anywidget, and which
is the same state drawn by a small piece of JavaScript that can also send changes back. The
important part of that arrangement is which side owns the truth: Python does. The front end
holds no bytecode logic at all, it draws rows that Python computed and it asks Python to
compute new ones when a toggle changes. So the static picture and the live one cannot say
different things, because there is only one implementation of what they say.

This is also why the fallback is real rather than a promise. There is no code path where a
widget is only correct once a browser is involved.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from .html import Raw, element, raw
from .strings import text
from .style import PREFIX, stylesheet

#: Where the front end modules live. One file per widget, named after its slug.
STATIC = Path(__file__).resolve().parent / "static"

#: The half of the front end that is the same for every widget: putting markup on the page,
#: forwarding a keystroke or a click, and putting the caret back afterwards.
SHARED = STATIC / "_common.js"


class Widget:
    """One component, in its two forms.

    A subclass sets `slug`, implements `state` and implements `body`. Everything else here
    is the same for all of them, which is the point of having a base class at all: a second
    widget that draws its own outer frame is a second widget that gets the padding wrong.
    """

    #: The name of the widget, used for its front end file and its root element id. Lower
    #: case with hyphens, matching the animation slugs, for one convention rather than two.
    slug: ClassVar[str]

    def state(self) -> dict[str, object]:
        """Everything the picture is drawn from, as plain data.

        Plain data, and not objects, because this is exactly what crosses to the front end
        when the widget is live. Keeping it to things that survive a round trip through JSON
        means the static path and the live path are drawing the same thing rather than two
        things that agree today.
        """
        raise NotImplementedError

    def markup(self, state: dict[str, object], *, live: bool = False) -> Raw:
        """The picture itself, without the outer frame or the stylesheet.

        One method for both forms, with `live` saying whether the controls work. That is
        deliberate. Two render methods would be two things to keep in step, and the one that
        nobody looks at is the static one, which is the one most readers see.
        """
        raise NotImplementedError

    def body(self, state: dict[str, object]) -> Raw:
        """The still picture, with its controls switched off and the notice underneath."""
        return self.markup(state, live=False)

    def view(self) -> dict[str, object]:
        """What crosses to the front end: the state, and the markup drawn from it.

        The markup travels with the data because the front end does not build any. It puts
        this string on the page and attaches listeners to the buttons and the box you type
        in, and when one of those changes it hands the change back to Python and gets a new
        string. So there is one renderer, written in Python, and the live widget cannot drift
        away from the static one.
        """
        state = self.state()
        return {**state, "html": str(self.markup(state, live=True))}

    def render(self) -> str:
        """The whole widget as a standalone block of HTML.

        The stylesheet goes in with it. That is a duplicated sheet per widget on a page with
        several, which is a few kilobytes and is worth it: a widget that depends on a style
        tag somewhere else on the page is a widget that renders unstyled the first time
        somebody embeds one on its own.
        """
        return str(
            element(
                "div",
                element("style", raw(stylesheet())),
                self.body(self.state()),
                class_=PREFIX,
                data_widget=self.slug,
            )
        )

    def _repr_html_(self) -> str:
        """What Jupyter, marimo and nbconvert call. The static picture, always."""
        return self.render()

    @classmethod
    def esm(cls) -> str:
        """The front end module for this widget, as source, with the shared part on the front.

        Both halves are read off disk rather than embedded in Python strings, so they are
        `.js` files an editor will highlight and a linter could be pointed at.

        The shared half is glued on by concatenation rather than imported. An import would be
        a second network request made from inside a notebook output cell, which works in
        Jupyter and does not reliably work in every other place a lesson gets rendered, and
        the whole file is about a hundred lines.
        """
        path = STATIC / f"{cls.slug}.js"
        if not path.is_file():
            raise FileNotFoundError(f"{cls.slug} has no front end module at {path}")
        return f"{SHARED.read_text(encoding='utf-8')}\n{path.read_text(encoding='utf-8')}"

    @classmethod
    def css(cls) -> str:
        """The stylesheet, for anywidget, which wants it separately rather than inline."""
        return stylesheet()

    def live(self) -> object:
        """The interactive version, which needs anywidget.

        Raises with something a reader can act on rather than an `ImportError` from three
        frames down, because the person who hits this is a reader following a lesson and not
        a developer reading a traceback.
        """
        try:
            import anywidget
            import traitlets
        except ImportError as missing:  # pragma: no cover - depends on the environment
            raise RuntimeError(
                "the live version needs anywidget, which is the `live` extra: "
                "`uv sync --extra live`, or `pip install anywidget`. "
                "The picture you already have is the static one and is not wrong, "
                "it just does not have buttons."
            ) from missing
        return self._anywidget(anywidget, traitlets)

    def _anywidget(self, anywidget: object, traitlets: object) -> object:
        """Build the anywidget instance. Subclasses say which traits they have."""
        raise NotImplementedError

    def notice(self) -> Raw:
        """The line that says this is the still picture and where the moving one is."""
        return element("p", text("common.static_notice"), class_=f"{PREFIX}-note")
