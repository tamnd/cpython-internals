#!/usr/bin/env python
"""The diagrams for O13, weak references.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `what-happens-when-it-dies`. Every weak reference is broken
first and only then are the callbacks run, which is why a callback can never reach the object
it was told about.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("o13-pointing-without-holding")

gallery.add(
    figures.compare(
        "a-reference-that-does-not-count",
        (
            "an ordinary name",
            [
                "bumps the reference count",
                "keeps the object alive",
                "always gives you the object",
                "you cannot tell when it dies",
            ],
        ),
        (
            "a weak reference",
            [
                "leaves the count alone",
                "is not a reason to stay",
                "gives you the object or None",
                "can call you when it dies",
            ],
        ),
        title="Two ways to point at the same object",
        verdict="The header calls it a stealth reference, which is exactly what it is.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.stack(
        "where-the-pointer-lives",
        [
            "the weak reference list head, at offset -32",
            "the instance dictionary, at offset -24",
            "two words of GC pre header",
            "the object itself, which is where id() points",
        ],
        title="What sits in front of an instance of your class",
        note="Four words before the object starts. Adding __weakref__ to __slots__ buys two of them.",
    )
)


gallery.add(
    figures.flow(
        "the-list-of-weak-references",
        [
            "the object holds one pointer",
            "the callback free reference sits at the head",
            "every reference with a callback goes in front of the rest",
            "and each one points back as well as forward",
        ],
        title="One object, a chain of references to it",
        labels=[
            "null until someone asks for a reference",
            "there is only ever one of these",
            "so the newest callback runs first",
        ],
        tones=["input", "durable", "focus", "quiet"],
    )
)


gallery.add(
    figures.flow(
        "what-happens-when-it-dies",
        [
            "the reference count reaches zero",
            "walk the chain and break every reference",
            "then walk it again and run the callbacks",
            "then free the memory",
        ],
        title="The order that makes callbacks safe",
        labels=[
            "the object is doomed but still in memory",
            "each one now returns None",
            "so a callback can never resurrect it",
        ],
        tones=["input", "focus", "focus", "warning"],
    )
)


gallery.add(
    figures.table(
        "who-can-be-weakly-referenced",
        ["object", "weakref offset", "can you point at it"],
        [
            ["a class you wrote", "-32", "yes, and you paid nothing for it"],
            ["set, function, type", "192, 96, 368", "yes, a real field in the struct"],
            ["list, dict, tuple, int, str", "0", "no"],
            ["__slots__ without __weakref__", "0", "no, until you add it"],
        ],
        title="Read it straight off the type with __weakrefoffset__",
        caption="Zero means no room for the pointer, so there is nowhere to keep the list.",
        tones=["focus", "quiet", "warning", "warning"],
    )
)


gallery.add(
    figures.flow(
        "the-memory-is-back-but-the-object-is-not",
        [
            "take a bound method and note its address",
            "drop it, and the free list keeps the memory",
            "take the method again and get the same address",
            "but the old weak reference still says None",
        ],
        title="The one thing O12 could not show you",
        labels=[
            "bound methods have a free list and weak references",
            "nothing is handed back to the allocator",
            "byte for byte the same place",
        ],
        tones=["input", "quiet", "warning", "focus"],
    )
)


raise SystemExit(gallery.save())
