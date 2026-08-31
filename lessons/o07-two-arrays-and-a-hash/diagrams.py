#!/usr/bin/env python
"""The diagrams for O07, how a dict is laid out and how it grows.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `two-arrays-not-one`. A dict is a small array of slot numbers
in front of a plain append only array of entries, and almost everything surprising about
dicts comes from that split.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("o07-two-arrays-and-a-hash")

gallery.add(
    figures.table(
        "two-arrays-not-one",
        ["dk_indices", "holds", "dk_entries", "holds"],
        [
            ["slot 0", "-1, never used", "entry 0", "hash, 'name', 'ada'"],
            ["slot 1", "entry 2", "entry 1", "hash, 'city', 'oslo'"],
            ["slot 2", "-1, never used", "entry 2", "hash, 'age', 41"],
            ["slot 3", "entry 0", "", ""],
            ["slot 4", "-1, never used", "", ""],
            ["slot 5", "entry 1", "", ""],
        ],
        title="A dict is two arrays, and only the small one has holes in it",
        caption="Reading the entries top to bottom gives you insertion order, for free.",
        tones=["quiet", "focus", "quiet", "focus", "quiet", "focus"],
    )
)


gallery.add(
    figures.flow(
        "where-a-key-lands",
        [
            "hash(key), a whole machine word",
            "keep the low bits: i = hash & mask",
            "read dk_indices[i]",
            "-1 means the key is not here, stop",
            "otherwise compare, and on a miss probe again",
        ],
        title="Finding a slot, which is usually the first thing tried",
        labels=[
            "for a size 8 table, mask is 7",
            "one byte read for a small dict",
            "this is the answer for every failed lookup",
        ],
        tones=["input", "focus", "focus", "durable", "warning"],
    )
)


gallery.add(
    figures.stack(
        "the-probe-recurrence",
        [
            "perturb starts as the whole hash",
            "perturb >>= 5",
            "i = mask & (i * 5 + perturb + 1)",
            "and repeat until a slot is empty or matches",
        ],
        title="Three lines that decide where to look next",
        note="For a size 8 table starting at 0 the order is 0, 1, 6, 7, 4, 5, 2, 3, which is "
        "every slot exactly once.",
    )
)


gallery.add(
    figures.bars(
        "when-it-grows",
        [
            ("6th key", 16),
            ("11th key", 32),
            ("22nd key", 64),
            ("43rd key", 128),
            ("86th key", 256),
        ],
        title="The table size after each resize, and the key that triggered it",
        caption="A table is never more than two thirds full, and each resize doubles it.",
    )
)


gallery.add(
    figures.compare(
        "delete-leaves-a-mark",
        (
            "the slot in dk_indices",
            [
                "becomes -2, a dummy",
                "not -1, which would end a probe",
                "a later insert can reuse it",
            ],
        ),
        (
            "the row in dk_entries",
            [
                "is cleared but stays put",
                "so nothing after it moves",
                "and its space is not given back",
            ],
        ),
        title="Why deleting from a dict does not free anything",
        verdict="Delete and insert in a loop and the entry array fills up, so the dict resizes "
        "while its length never changes.",
        verdict_tone="warning",
    )
)


gallery.add(
    figures.table(
        "two-kinds-of-entry",
        ["dk_kind", "what a row holds", "bytes per row", "when you get it"],
        [
            ["DICT_KEYS_UNICODE", "key, value", "16", "every key is an exact str"],
            ["DICT_KEYS_GENERAL", "hash, key, value", "24", "anything else is a key"],
        ],
        title="A dict with only string keys does not store the hashes",
        caption="A str caches its own hash, so the copy in the entry would be redundant.",
        tones=["focus", "quiet"],
    )
)


raise SystemExit(gallery.save())
