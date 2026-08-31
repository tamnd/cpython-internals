#!/usr/bin/env python
"""The diagrams for F02, f-strings in the lexer.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `one-string-many-tokens`. Every other picture here is a
consequence of an f-string being a stretch of source that the tokenizer walks in and out of
rather than a single token it hands over whole.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("f02-f-strings-in-the-lexer")

gallery.add(
    figures.spans(
        "one-string-many-tokens",
        'f"a{x+1}b"',
        [
            (0, 2, "FSTRING_START"),
            (2, 3, "FSTRING_MIDDLE"),
            (3, 8, "ordinary tokens, one per character here"),
            (8, 9, "FSTRING_MIDDLE"),
            (9, 10, "FSTRING_END"),
        ],
        title="Nine tokens where a plain string would be one",
        caption="The part in braces is not special. It goes through the same lexer as the rest of your file.",
    )
)


gallery.add(
    figures.stack(
        "the-mode-stack",
        [
            "f-string mode, the inner one, quote is a double quote",
            "f-string mode, the outer one, quote is a double quote",
            "regular mode, which is where every file starts",
        ],
        title="Where the tokenizer thinks it is, halfway through a nested f-string",
        note="Each entry remembers its own quote character, its own brace depth and whether it is inside a format spec.",
    )
)


gallery.add(
    figures.table(
        "two-ceilings",
        ["what you are nesting", "the constant", "deepest that compiles", "what it says"],
        [
            [
                "f-strings inside f-strings",
                "MAXFSTRINGLEVEL 150",
                "149",
                "too many nested f-strings",
            ],
            [
                "fields inside a format spec",
                "MAX_EXPR_NESTING 3",
                "3",
                "expressions nested too deeply",
            ],
        ],
        title="Two separate ceilings, and neither one is the number in the header",
        caption="Both checks run before the push, which is why one limit lands a step below its constant and the other lands on it.",
        tones=["focus", "warning"],
    )
)


gallery.add(
    figures.spans(
        "the-spec-is-a-string",
        'f"{v:{w}.{p}f}"',
        [
            (2, 5, "the value"),
            (5, 8, "a field"),
            (8, 9, "MIDDLE"),
            (9, 12, "a field"),
            (12, 13, "MIDDLE"),
        ],
        title="A format spec is an f-string in its own right",
        caption="The dot and the trailing f come out as FSTRING_MIDDLE, exactly like text in the body would.",
    )
)


gallery.add(
    figures.compare(
        "raw-until-the-parser",
        (
            'the token, for f"a\\nb"',
            [
                "FSTRING_MIDDLE",
                "covers four characters",
                "a, backslash, n, b",
                "raw or not is undecided",
            ],
        ),
        (
            "the AST node the parser builds",
            [
                "Constant",
                "holds three characters",
                "a, a real newline, b",
                "rf skips the decoding",
            ],
        ),
        title="The tokenizer does not decode escapes, and never has",
        verdict="A backslash means nothing to the lexer inside an f-string body. The parser decodes it later, which is why the same token can become three characters or four.",
        verdict_tone="focus",
    )
)


gallery.add(
    figures.flow(
        "the-text-is-kept",
        [
            'you write f"{x + 1 = }"',
            "the lexer copies the characters as it scans them",
            "last_expr_buffer, a private copy of your source",
            "set_ftstring_expr hangs it on the token",
            "the AST carries the text next to the expression",
            "the printed result is x + 1 = 2",
        ],
        title="How the printed form of your expression survives all the way to run time",
        labels=[
            "one character at a time",
            "until a colon, a bang or a closing brace",
            "as token metadata",
            "compiled into a constant",
        ],
        tones=["input", "intermediate", "focus", "focus", "intermediate", "durable"],
    )
)


raise SystemExit(gallery.save())
