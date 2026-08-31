#!/usr/bin/env python
"""The diagrams for O03, the table that connects dunder names to C slots.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `the-table-runs-both-ways`. There is a single table of ninety
four rows in typeobject.c, and every rule people learn as a separate quirk of dunder methods
comes out of one of its rows being read in one direction or the other.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("o03-dunders-and-slots")

gallery.add(
    figures.compare(
        "the-table-runs-both-ways",
        (
            "you wrote the class in Python",
            [
                "your __repr__ goes in the class dict",
                "fixup_slot_dispatchers reads it",
                "tp_repr gets a generic dispatcher",
                "which looks your function back up",
            ],
        ),
        (
            "the type was written in C",
            [
                "tp_repr already has a function",
                "add_operators reads it",
                "__repr__ appears in the class dict",
                "as a wrapper around the C one",
            ],
        ),
        title="One table, read forwards when you write a class and backwards when C does",
        verdict="Neither direction is a special case. Both walk the same ninety four rows.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.stack(
        "one-row-of-the-table",
        [
            "the name, as a string and as an interned object",
            "the offset of the slot inside PyHeapTypeObject",
            "the dispatcher to install when Python defines it",
            "the wrapper to expose when C defines it",
            "the docstring that wrapper will carry",
        ],
        title="What one row of slotdefs holds",
        note="The offset is why the table is sorted by slot rather than alphabetically by name.",
    )
)


gallery.add(
    figures.flow(
        "looked-up-on-the-type",
        [
            "repr(x) in your code",
            "the C function reads Py_TYPE(x)->tp_repr",
            "which is slot_tp_repr for a Python class",
            "that looks __repr__ up on the type",
            "and calls it with x",
        ],
        title="Why a dunder set on an instance is never called",
        labels=[
            "the instance dict is not consulted at all",
            "one dispatcher for every Python class",
            "on the type, and only on the type",
        ],
        tones=["input", "focus", "intermediate", "focus", "durable"],
    )
)


gallery.add(
    figures.table(
        "one-name-many-slots",
        ["what you write", "what it fills", "and what that buys you"],
        [
            ["__eq__ and five others", "tp_richcompare", "one slot, an op argument picks"],
            ["__len__", "mp_length and sq_length", "len and truthiness both work"],
            ["__getitem__", "mp_subscript and sq_item", "and the class becomes iterable"],
            ["__add__ and __radd__", "nb_add", "one slot decides who goes first"],
        ],
        title="The mapping is not one to one in either direction",
        caption="Every surprise about dunder methods is one of these four rows.",
        tones=["quiet", "focus", "focus", "warning"],
    )
)


gallery.add(
    figures.flow(
        "who-goes-first",
        [
            "self + other, and nb_add dispatches both",
            "is other's type a subclass of self's type",
            "and does other define __radd__ itself",
            "if both, __radd__ first, otherwise __add__",
        ],
        title="How one slot decides between __add__ and __radd__",
        labels=[
            "so the reflected call is worth considering",
            "inheriting it from a shared base does not count",
        ],
        tones=["input", "intermediate", "intermediate", "durable"],
    )
)


gallery.add(
    figures.flow(
        "how-eq-loses-hash",
        [
            "you define __eq__ and not __hash__",
            "overrides_hash sees __eq__ in the class dict",
            "so tp_hash is not copied down from the base",
            "type_ready_set_hash finds it still empty",
            "and writes __hash__ = None into the class dict",
        ],
        title="Three steps between defining __eq__ and unhashable type",
        labels=[
            "which is the only question it asks",
            "and neither is tp_richcompare",
            "so the None you see is real, not a rule",
        ],
        tones=["input", "focus", "intermediate", "intermediate", "warning"],
    )
)


raise SystemExit(gallery.save())
