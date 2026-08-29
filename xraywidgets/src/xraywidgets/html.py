"""Building HTML by hand, in about eighty lines, because the alternative is worse.

A template engine would be a dependency, and a dependency here is a dependency in the WASM
build, where every wheel is a download the reader waits through. The widgets emit small,
regular structures, so the amount of templating actually needed is one function that joins
tags and one that escapes text.

Escaping is not optional and it is not a detail. A `Disassembler` renders whatever source
the reader typed, and the reader is going to type `<`, because they are learning a language
that uses it. Everything that goes into a document goes through `escape` on the way, and
the only way to put raw markup in is `raw`, which is deliberately awkward to write.
"""

from __future__ import annotations

import html
from collections.abc import Iterable

#: Tags that have no closing half. There are more in HTML, but a widget that needs `<embed>`
#: has gone somewhere this module should not follow it to.
VOID = frozenset({"br", "hr", "img", "input", "meta", "link"})


class Raw(str):
    """Markup that is already safe, which `element` will not escape again.

    A separate type rather than a flag, so that passing a string somewhere it will be
    escaped is the default and passing one somewhere it will not needs the word `raw` in
    the source. That is the right way round: the mistake to make hard is the unsafe one.
    """

    __slots__ = ()


def raw(markup: str) -> Raw:
    """Mark a string as markup rather than text. Read the call site twice."""
    return Raw(markup)


def escape(text: object) -> Raw:
    """Anything at all, as text that cannot become markup.

    Quotes are escaped too, because the same function is used for attribute values, and a
    version that only handles `<` and `&` works right up until somebody puts a title on a
    button.
    """
    if isinstance(text, Raw):
        return text
    return Raw(html.escape(str(text), quote=True))


def attribute_name(name: str) -> str:
    """A Python keyword argument as an HTML attribute name.

    `class_` becomes `class` and `aria_label` becomes `aria-label`, which covers everything
    the widgets need. The trailing underscore is the escape hatch for the handful of
    attribute names that are Python keywords.
    """
    return name.rstrip("_").replace("_", "-")


def element(tag: str, *children: object, **attributes: object) -> Raw:
    """One element, with its attributes and its children.

    An attribute whose value is `None` or `False` is left out entirely rather than written
    as the string "None", which is how `disabled=False` ends up disabling a button. An
    attribute whose value is `True` is written bare, which is what HTML means by a boolean
    attribute.
    """
    parts = []
    for name, value in attributes.items():
        if value is None or value is False:
            continue
        if value is True:
            parts.append(f" {attribute_name(name)}")
        else:
            parts.append(f' {attribute_name(name)}="{escape(value)}"')
    opened = f"<{tag}{''.join(parts)}>"
    if tag in VOID:
        if children:
            raise ValueError(f"<{tag}> cannot have children, and was given {len(children)}")
        return Raw(opened)
    return Raw(f"{opened}{join(children)}</{tag}>")


def join(children: Iterable[object]) -> Raw:
    """Several children in a row, each escaped unless it is already markup."""
    return Raw("".join(str(escape(child)) for child in children))
