#!/usr/bin/env python
"""The diagrams for M05, the objects whose reference count never moves.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

`held-a-hundred-thousand-times` is the one to start from. Everything else here is either a list
of which objects get that treatment or a consequence of the fact that the list has to stay small.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("m05-the-ones-that-never-die")

gallery.add(
    figures.compare(
        "held-a-hundred-thousand-times",
        (
            "None",
            [
                "count before: enormous",
                "count after: the same",
                "no memory was written",
                "no cache line was claimed",
            ],
        ),
        (
            "a list you made",
            [
                "count before: 3",
                "count after: 100003",
                "100000 writes happened",
                "the same 8 bytes, each time",
            ],
        ),
        title="Putting the same object into a hundred thousand containers",
        verdict="One of these two is safe to share between threads without a lock.",
        verdict_tone="warning",
    )
)


gallery.add(
    figures.table(
        "who-is-on-the-list",
        ["object", "never freed", "why"],
        [
            ["None, True, False", "yes", "one of each, used everywhere"],
            ["the small integers", "yes", "made once at startup"],
            ["one character strings", "yes", "made once at startup"],
            ["int, object, ValueError", "yes", "built into the binary"],
            ["the name print", "yes", "a name, so it was interned"],
            ["the print function", "no", "an ordinary heap object"],
            ["the sys module", "no", "an ordinary heap object"],
            ["anything you built", "no", "nobody else shares it"],
        ],
        title="Which objects opt out of reference counting",
        caption="The rule is roughly: shared by everything, and cheap enough to keep forever.",
        tones=["focus", "focus", "focus", "durable", "durable", "quiet", "quiet", "warning"],
    )
)


gallery.add(
    figures.table(
        "the-fixed-set",
        ["what", "how many", "made when"],
        [
            ["small integers", "about a thousand", "before your code runs"],
            ["one character strings", "256", "before your code runs"],
            ["types and exceptions", "a few hundred", "compiled into the binary"],
            ["names in your code", "one per name", "when your module is compiled"],
        ],
        title="The whole set, and it is not big",
        caption="Tens of kilobytes that are never given back, in exchange for never counting them.",
        tones=["focus", "focus", "durable", "input"],
    )
)


gallery.add(
    figures.compare(
        "where-the-cache-stops",
        (
            "Python 3.14",
            [
                "-5 up to 256",
                "262 integers made once",
                "300 is a new object",
                "and it is mortal",
            ],
        ),
        (
            "Python 3.15",
            [
                "-5 up to 1024",
                "1030 integers made once",
                "300 is the shared one",
                "and it never dies",
            ],
        ),
        title="One constant moved, and you can find it from Python",
        verdict="Same code, different answer. A binary search over the count finds the edge.",
    )
)


gallery.add(
    figures.table(
        "two-flags-not-one",
        ["the string", "interned", "immortal"],
        [
            ["a name you used", "yes", "yes"],
            ["a plain string constant", "yes", "no"],
            ["a string you built at runtime", "no", "no"],
            ["after sys.intern on that string", "yes", "no"],
        ],
        title="Interned and immortal are two separate bits",
        caption="Interning is about sharing one copy. Immortality is about never freeing it.",
        tones=["focus", "warning", "quiet", "warning"],
    )
)


gallery.add(
    figures.compare(
        "what-it-buys-and-costs",
        (
            "what you get",
            [
                "no write on incref",
                "no lock, no atomic",
                "safe to share across threads",
                "free threading becomes possible",
            ],
        ),
        (
            "what you pay",
            [
                "the object is never freed",
                "one compare on every decref",
                "the set has to stay small",
                "you cannot add to it yourself",
            ],
        ),
        title="The trade the interpreter makes",
        verdict="Which is why there is no way to immortalize your own object from Python.",
        verdict_tone="warning",
    )
)


raise SystemExit(gallery.save())
