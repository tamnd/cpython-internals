#!/usr/bin/env python
"""The diagrams for O06, the descriptor protocol.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `four-of-a-kind`. People learn `property`, `classmethod`,
`staticmethod` and bound methods as four separate features, and they are one protocol with
four different answers to the same question.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("o06-what-property-actually-is")

gallery.add(
    figures.table(
        "four-of-a-kind",
        ["what you wrote", "what __get__ hands back", "lines of C"],
        [
            ["a plain def", "a bound method holding self", "7"],
            ["@staticmethod", "the function, untouched", "6"],
            ["@classmethod", "a bound method holding the class", "8"],
            ["@property", "the result of calling your getter", "34"],
        ],
        title="Four features you learned separately, one protocol underneath",
        caption="All four sit in the class dict and all four answer the same call, __get__.",
        tones=["quiet", "quiet", "quiet", "focus"],
    )
)


gallery.add(
    figures.stack(
        "the-three-methods",
        [
            "__get__(self, obj, owner) runs when something reads the attribute",
            "__set__(self, obj, value) runs when something assigns to it",
            "__delete__(self, obj) runs on del",
            "__set_name__(self, owner, name) runs once, when the class is built",
        ],
        title="The whole protocol, and there is nothing else to it",
        note="Define __get__ only and you have a non data descriptor. Add __set__ and the "
        "precedence flips.",
    )
)


gallery.add(
    figures.compare(
        "data-or-not",
        (
            "non data descriptor",
            [
                "has __get__ and nothing else",
                "the instance dict beats it",
                "so you can shadow a method",
                "plain functions live here",
            ],
        ),
        (
            "data descriptor",
            [
                "has __set__ or __delete__ too",
                "it beats the instance dict",
                "so you cannot shadow a property",
                "property and __slots__ live here",
            ],
        ),
        title="One bit of difference, and it decides who wins",
        verdict="PyDescr_IsData is one line. It asks whether tp_descr_set is filled in.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.flow(
        "a-function-becomes-a-method",
        [
            "def greet(self) in the class body",
            "it lands in the class dict as a plain function",
            "g.greet reads it, finds __get__, calls it",
            "func_descr_get sees a real obj, not None",
            "PyMethod_New packs the function and g together",
        ],
        title="Where the self in your methods comes from",
        labels=[
            "nothing special has happened yet",
            "functions are non data descriptors",
            "on a class it returns the function unchanged",
        ],
        tones=["input", "quiet", "focus", "focus", "durable"],
    )
)


gallery.add(
    figures.table(
        "the-c-side",
        ["where you find it", "the type you get", "data descriptor"],
        [
            ["a __slots__ entry", "member_descriptor", "yes"],
            ["int.numerator", "getset_descriptor", "yes"],
            ["str.join", "method_descriptor", "no"],
            ["int.__add__", "wrapper_descriptor", "no"],
            ["dict.fromkeys", "classmethod_descriptor", "no"],
        ],
        title="C code cannot write a class body, so it builds these instead",
        caption="Same protocol, same __get__ call. Only the constructor is different.",
        tones=["focus", "focus", "quiet", "quiet", "quiet"],
    )
)


gallery.add(
    figures.flow(
        "set-name-timing",
        [
            "the class body runs and fills a dict",
            "type() builds the class from that dict",
            "type_new_set_names copies the dict and walks it",
            "every value with __set_name__ gets called",
            "and it never runs again",
        ],
        title="How a descriptor learns the name it was assigned to",
        labels=[
            "your descriptor exists but has no name yet",
            "the copy is why you can add attributes inside __set_name__",
            "assign the same descriptor later and it stays nameless",
        ],
        tones=["input", "quiet", "focus", "focus", "durable"],
    )
)


raise SystemExit(gallery.save())
