#!/usr/bin/env python
"""The diagrams for Z01, reading C.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

`pointers-are-arrows` is the one that does the work here. Everything else in the lesson is
a table or a piece of prose, but the reason a beginner cannot read `Objects/listobject.c`
is almost always that they have no picture of what a pointer is, and a picture is the only
thing that fixes that.
"""

from nbdiagram import Gallery, figures, stages
from nbdiagram.scene import Scene
from pyxray import theme

gallery = Gallery("z01-reading-c")

gallery.add(
    stages.map(
        "where-we-are",
        highlight=None,
        title="Before any of this",
        caption="Nothing is highlighted because this lesson is not a stage. It is the reading skill you need before the source references in every other lesson are worth clicking.",
    )
)


def _pointers_are_arrows() -> Scene:
    """A name, a struct, a slot array and the objects in it, joined by arrows.

    Panels are drawn before their contents because SVG has no z-index, so each panel's
    height is worked out from the box height rather than measured after the fact. Every
    label is short enough to sit on one line for the same reason: `Scene.box` wraps a long
    label and grows the box to fit, which would push the contents out through the panel.
    """
    scene = Scene("pointers-are-arrows")
    field_width = 190
    field_height = 44
    slot_width = 110

    scene.text("What a pointer actually is", 0, 0, size=theme.TITLE_SIZE)
    top = theme.TITLE_SIZE * theme.LINE_HEIGHT + theme.GRID

    heading = theme.CAPTION_SIZE * theme.LINE_HEIGHT + 10

    # The name on the left. In C this is a PyObject * on somebody's stack or in a frame.
    name_panel_height = heading + field_height + 2 * theme.PADDING
    scene.panel("in your program", 0, top, field_width, name_panel_height, tone="quiet")
    name = scene.box(
        "values",
        theme.PADDING,
        top + heading + theme.PADDING,
        width=field_width - 2 * theme.PADDING,
        height=field_height,
        tone="input",
        mono=True,
        size=theme.CAPTION_SIZE,
    )

    # The struct in the middle. Five fields, in the order the C declares them.
    fields = [
        ("ob_refcnt", "how many hold it", "durable"),
        ("ob_type", "which type it is", "durable"),
        ("ob_size", "len() reads this", "focus"),
        ("ob_item", "-> the slot array", "warning"),
        ("allocated", "slots there are", "focus"),
    ]
    struct_left = field_width + 150
    struct_height = heading + len(fields) * (field_height + 8) + 2 * theme.PADDING
    scene.panel(
        "the list object itself",
        struct_left,
        top,
        field_width + 2 * theme.PADDING,
        struct_height,
        tone="intermediate",
    )
    rows = []
    for index, (label, note, tone) in enumerate(fields):
        y = top + heading + theme.PADDING + index * (field_height + 8)
        rows.append(
            scene.box(
                label,
                struct_left + theme.PADDING,
                y,
                width=field_width,
                height=field_height,
                tone=tone,
                mono=True,
                size=theme.CAPTION_SIZE,
            )
        )
        # Outside the panel rather than inside it, since a note long enough to be worth
        # reading is wider than the field box it belongs to.
        scene.text(
            note,
            struct_left + field_width + 4 * theme.PADDING,
            y + field_height / 2 - theme.CAPTION_SIZE * 0.7,
            size=theme.CAPTION_SIZE,
            colour=theme.MUTED,
        )
    scene.arrow(name, rows[0], label="points at")

    # The slot array on the right, which is a separate allocation from the struct.
    slots = ["slot 0", "slot 1", "unused", "unused"]
    array_left = struct_left + field_width + 300
    array_height = heading + field_height + 2 * theme.PADDING
    array_top = top + struct_height - array_height
    scene.panel(
        "the slot array, allocated wide",
        array_left,
        array_top,
        len(slots) * (slot_width + 8) + 2 * theme.PADDING - 8,
        array_height,
        tone="quiet",
    )
    cells = []
    for index, label in enumerate(slots):
        cells.append(
            scene.box(
                label,
                array_left + theme.PADDING + index * (slot_width + 8),
                array_top + heading + theme.PADDING,
                width=slot_width,
                height=field_height,
                tone="warning" if index < 2 else "quiet",
                mono=True,
                size=theme.CAPTION_SIZE,
            )
        )
    # No label on this one. The note beside ob_item already says where it goes, and a
    # label parked mid arrow lands on top of that note.
    scene.arrow(rows[3], cells[0])

    # The objects the slots point at, which are somewhere else again.
    object_top = array_top + array_height + 70
    for index, label in enumerate(["'a'", "'b'"]):
        target = scene.box(
            label,
            array_left + theme.PADDING + index * (slot_width + 8),
            object_top,
            width=slot_width,
            height=field_height,
            tone="input",
            mono=True,
            size=theme.CAPTION_SIZE,
        )
        scene.arrow(cells[index], target, sides=("bottom", "top"))

    bottom = max(element.box[3] for element in scene.elements)
    for line, words in enumerate(
        [
            "Three separate blocks of memory, joined by two arrows. The name holds an address. The struct holds five",
            "fields, one of which is another address. The slot array holds addresses of the objects themselves.",
            "Every star in the C source is one of these arrows, and every arrow is a number that happens to be an address.",
        ]
    ):
        scene.text(
            words,
            0,
            bottom + theme.GRID + line * theme.CAPTION_SIZE * theme.LINE_HEIGHT,
            size=theme.CAPTION_SIZE,
            colour=theme.MUTED,
        )
    return scene


gallery.add(_pointers_are_arrows())


gallery.add(
    figures.table(
        "the-struct",
        ["field", "type in the C", "what it is for"],
        [
            ["ob_refcnt", "Py_ssize_t", "how many places are holding this list right now"],
            [
                "ob_type",
                "PyTypeObject *",
                "an arrow to the type, which is where every method lives",
            ],
            ["ob_size", "Py_ssize_t", "how many slots are in use, which is what len() returns"],
            [
                "ob_item",
                "PyObject **",
                "an arrow to the slot array, which is a separate allocation",
            ],
            ["allocated", "Py_ssize_t", "how many slots were paid for, which is usually more"],
        ],
        title="Every field of a list, and there are only five",
        caption="The first three come from PyObject_VAR_HEAD, which every variable sized object starts with. Only the last two belong to lists. A struct is a fixed layout, so ob_size is always at the same offset in every object that has one, which is what lets one function read the length of anything.",
        tones=["durable", "durable", "focus", "warning", "focus"],
    )
)


gallery.add(
    figures.table(
        "seven-idioms",
        ["what you see", "how to read it"],
        [
            ["PyObject *v", "an arrow to some Python value, and it could be any type at all"],
            ["static PyObject *f(...)", "this function is private to this one file"],
            ["return NULL;", "something went wrong, and an exception has already been set"],
            [
                "if (x < 0) { ... }",
                "the call before it failed, because 0 or a pointer means it worked",
            ],
            ["Py_NewRef(v)", "hand back v, and count one more holder for it"],
            ["goto error;", "jump to the one cleanup block at the bottom of the function"],
            ["_PyList_Something", "private to CPython, and it can change in any release"],
        ],
        title="Seven things you will see on every page",
        caption="These seven cover most of what makes CPython's C look foreign. None of them are C language features you need to learn. They are house style, and once you can read them the source stops looking like a different language.",
        tones=["quiet"] * 7,
    )
)


gallery.add(
    figures.table(
        "new-or-borrowed",
        ["the call", "what you get", "what you owe"],
        [
            ["Py_NewRef(v)", "a new reference", "one Py_DECREF, eventually"],
            [
                "PyList_GET_ITEM(l, i)",
                "a borrowed reference",
                "nothing, but it dies when the list does",
            ],
            ["PyList_SET_ITEM(l, i, v)", "nothing", "nothing, the list took your reference"],
            ["list.pop() from C", "a new reference", "one Py_DECREF, the list gave up its own"],
            [
                "PyDict_GetItem(d, k)",
                "a borrowed reference",
                "nothing, and this is where bugs live",
            ],
        ],
        title="New, borrowed, or stolen",
        caption="This is the one thing in CPython's C that has no equivalent in Python and no help from the compiler. Getting it wrong by one in either direction is either a crash or a leak, and which of the three a function does is written only in its documentation.",
        tones=["durable", "warning", "warning", "durable", "warning"],
    )
)


gallery.add(
    figures.flow(
        "the-append-path",
        [
            "values.append(x)",
            "list_append_impl, in listobject.c",
            "_PyList_AppendTakeRef, in pycore_list.h",
            "is there a spare slot?",
            "write x into it and add one to ob_size",
        ],
        title="What one append actually does",
        tones=["input", "intermediate", "intermediate", "focus", "durable"],
        labels=[
            "one C call",
            "count one more holder for x",
            "read ob_size and allocated",
            "yes, almost every time",
        ],
    )
)


gallery.add(
    figures.bars(
        "growing",
        [
            ("1st resize", 4),
            ("2nd", 8),
            ("3rd", 16),
            ("4th", 24),
            ("5th", 32),
            ("6th", 40),
            ("7th", 52),
            ("8th", 64),
            ("9th", 76),
            ("10th", 92),
        ],
        unit="slots",
        title="How many slots a list has after each time it grows",
        caption="Roughly one eighth more each time, rounded up to a multiple of four. That is why appending a million items does not do a million reallocations, and the lesson checks this list against a real interpreter rather than quoting it.",
        tones=["intermediate"] * 6 + ["focus"] * 4,
    )
)


gallery.add(
    figures.compare(
        "macros-are-text",
        (
            "what you write",
            [
                "Py_RETURN_NONE;",
                "Py_SIZE(self)",
                "PyList_GET_ITEM(l, i)",
                "Py_CLEAR(item)",
            ],
        ),
        (
            "what the compiler sees",
            [
                "return Py_None;",
                "self->ob_base.ob_size",
                "l->ob_item[i]",
                "a small block that sets it to NULL",
            ],
        ),
        title="A macro is text substitution, and nothing else",
        verdict="This is why grep finds the definition and the debugger does not. A macro has no type, no scope and no address, so it can do things a function cannot, including evaluating its argument twice.",
        verdict_tone="warning",
    )
)


gallery.add(
    figures.table(
        "what-to-reach-for",
        ["when you want to know", "look at"],
        [
            ["what an object's fields are", "the struct in Include/, not the .c file"],
            ["what a method does", "the *_impl function in Objects/, named after the method"],
            ["whether a name is public", "the leading underscore, and whether it is in Include/"],
            ["why a line exists", "git log -S on the line, then the linked issue"],
            ["what a macro expands to", "grep for #define, since nothing else will find it"],
            ["whether you owe a reference", "the docstring, because the code will not tell you"],
        ],
        title="Where to look, once you can read it",
        caption="Reading C is not the hard part of reading CPython. Knowing which of two million lines to open is, and these six cover most of it.",
        tones=["quiet"] * 6,
    )
)


raise SystemExit(gallery.save())
