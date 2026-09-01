#!/usr/bin/env python
"""The diagrams for O08, split tables and inline values.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `one-copy-of-the-keys`. Ten thousand instances of a class have
ten thousand copies of the same attribute names in the obvious design, and one copy in the
design CPython actually uses.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("o08-where-attributes-really-live")

gallery.add(
    figures.compare(
        "one-copy-of-the-keys",
        (
            "a dict per instance",
            [
                "every instance owns a keys array",
                "with the same names as its siblings",
                "plus a hash table sized for them",
                "about 350 bytes for two attributes",
            ],
        ),
        (
            "one shared keys array",
            [
                "the type owns the keys, once",
                "each instance keeps a bare array",
                "stored inside the instance",
                "about 125 bytes for two attributes",
            ],
        ),
        title="The same two attributes, stored two ways",
        verdict="Nothing in the language changed. The names moved to the type.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.stack(
        "what-an-instance-holds",
        [
            "the object header, from O01",
            "any fields the type declared",
            "capacity, size, embedded, valid, four bytes total",
            "one pointer per possible attribute, most of them NULL",
            "one byte per attribute actually set, in the order they were set",
        ],
        title="An ordinary instance, top to bottom",
        note="There is no dict here. The names live on the type and the order lives in "
        "those last few bytes.",
    )
)


gallery.add(
    figures.flow(
        "how-the-keys-get-filled",
        [
            "the compiler records every self.name it sees",
            "and stores the list as __static_attributes__",
            "the class gets a keys array with room for 30",
            "prefilled from that list",
            "anything set later is added on first use",
        ],
        title="Where the shared names come from",
        labels=[
            "a tuple you can read from Python",
            "SHARED_KEYS_MAX_SIZE, a hard limit",
            "so the first instance is already laid out",
        ],
        tones=["input", "focus", "focus", "durable", "quiet"],
    )
)


gallery.add(
    figures.bars(
        "the-cost-of-each-shape",
        [
            ("two shared names", 125),
            ("__dict__ touched", 188),
            ("40 possible names", 351),
        ],
        unit="bytes per instance",
        title="Bytes per instance, same two attributes",
        caption="Measured with tracemalloc over ten thousand instances.",
        tones=["focus", "quiet", "warning"],
    )
)


gallery.add(
    figures.flow(
        "what-breaks-the-sharing",
        [
            "more than 30 distinct attribute names on the class",
            "assigning to __dict__ directly",
            "any object whose type was not built from a class statement",
            "and the values array is abandoned",
        ],
        title="Three ways an instance ends up with a dict of its own",
        labels=[
            "the keys array has no room left",
            "the dict you hand over is the one it keeps",
            "C types opt in with a flag",
        ],
        tones=["warning", "warning", "warning", "quiet"],
    )
)


gallery.add(
    figures.table(
        "reading-it-back",
        ["what you do", "what happens"],
        [
            ["obj.name", "one array read, no dict involved"],
            ["vars(obj)", "a dict object is built and kept from then on"],
            ["obj.__dict__['x'] = 1", "the same, and it writes through to the values"],
            ["del obj.name", "the slot goes NULL, siblings unaffected"],
        ],
        title="Which of these makes a dict appear",
        caption="Only the first one leaves the instance in its small form.",
        tones=["focus", "warning", "warning", "quiet"],
    )
)


raise SystemExit(gallery.save())
