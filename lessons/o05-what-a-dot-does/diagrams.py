#!/usr/bin/env python
"""The diagrams for O05, what actually happens when you write a dot.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `five-steps-in-order`. Everything people learn as separate
rules about attributes is one function reading four places in a fixed order, and knowing the
order is enough to predict every case.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("o05-what-a-dot-does")

gallery.add(
    figures.flow(
        "five-steps-in-order",
        [
            "x.name, and tp_getattro gets called",
            "walk type(x).__mro__ for name",
            "found a data descriptor, call its __get__",
            "otherwise look in the instance dict",
            "otherwise use what the MRO found",
            "otherwise raise AttributeError",
        ],
        title="What PyObject_GenericGetAttr does, in the order it does it",
        labels=[
            "one lookup, cached, described in O04",
            "one that has __set__ as well as __get__",
            "which is why a property cannot be shadowed",
            "a plain value, or a __get__ with no __set__",
        ],
        tones=["input", "focus", "warning", "focus", "focus", "quiet"],
    )
)


gallery.add(
    figures.table(
        "who-wins",
        ["what is on the type", "what is in the instance dict", "what x.name gives you"],
        [
            ["a data descriptor", "a value", "the descriptor"],
            ["a non data descriptor", "a value", "the instance dict"],
            ["a plain value", "a value", "the instance dict"],
            ["a non data descriptor", "nothing", "the descriptor"],
            ["nothing", "nothing", "AttributeError, then __getattr__"],
        ],
        title="The only row that surprises people is the first one",
        caption="A data descriptor is one with __set__ or __delete__, which is what property and slots make.",
        tones=["warning", "quiet", "quiet", "quiet", "focus"],
    )
)


gallery.add(
    figures.compare(
        "two-hooks-not-one",
        (
            "__getattribute__",
            [
                "runs for every single attribute",
                "including __dict__ and __class__",
                "the default one is the C function",
                "override it and you own everything",
            ],
        ),
        (
            "__getattr__",
            [
                "runs only after the normal path failed",
                "and only on AttributeError",
                "there is no default one at all",
                "override it and you own the gaps",
            ],
        ),
        title="Two names one letter apart that do completely different jobs",
        verdict="The slot is the same either way. A class with __getattr__ gets the hook dispatcher instead.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.flow(
        "a-class-is-different",
        [
            "Klass.name, and type_getattro gets called",
            "walk type(Klass).__mro__, the metaclass chain",
            "found a data descriptor there, call it",
            "otherwise walk Klass.__mro__ itself",
            "and call __get__ with None as the instance",
        ],
        title="Looking a name up on a class takes a different function",
        labels=[
            "the metaclass comes first, not the class",
            "this is how a metaclass property works",
            "the same MRO walk, one level down",
        ],
        tones=["input", "focus", "warning", "focus", "durable"],
    )
)


gallery.add(
    figures.stack(
        "the-version-tag",
        [
            "every type has a tp_version_tag, a plain number",
            "the cache stores type version, name, and the answer",
            "a hit needs both the version and the name to match",
            "changing anything on the class zeroes the tag",
            "and zeroes it on every subclass too",
        ],
        title="How the answer gets remembered, and how it gets forgotten",
        note="There is no invalidation pass. The old entries stay and simply never match again.",
    )
)


gallery.add(
    figures.flow(
        "specialised-then-not",
        [
            "LOAD_ATTR, the general form",
            "after a few runs, LOAD_ATTR_INSTANCE_VALUE",
            "someone assigns a property to the class",
            "the guard fails and it goes back to general",
            "and settles on LOAD_ATTR_PROPERTY",
        ],
        title="The bytecode rewrites itself around what it keeps seeing",
        labels=[
            "the guard is the type version tag",
            "which zeroes every version tag under it",
            "no invalidation pass, just a check that stops matching",
        ],
        tones=["input", "focus", "warning", "intermediate", "durable"],
    )
)


raise SystemExit(gallery.save())
