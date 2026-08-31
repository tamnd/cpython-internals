#!/usr/bin/env python
"""The diagrams for F01, the tokenizer in C.

Each scene is written out twice, as an editable `.excalidraw` and as the `.svg` the lesson
embeds. Run this file to regenerate them, or `just build-diagrams` for every lesson.

The one carrying the lesson is `one-line-in-the-buffer`. Everything else in F01 is easier
once a reader believes that the tokenizer has one line of your file and nothing else, because
that single fact explains the four front ends, the two stacks and half the error messages.
"""

from nbdiagram import Gallery, figures

gallery = Gallery("f01-the-tokenizer-in-c")

gallery.add(
    figures.table(
        "one-table-five-files",
        ["what comes out", "what it is", "who reads it"],
        [
            ["Include/internal/pycore_token.h", "a #define per token", "the lexer, in C"],
            ["Parser/token.c", "an array of token names", "error messages and -d"],
            ["Lib/token.py", "the same numbers, in Python", "tokenize, ast, dis"],
            ["Doc/library/token-list.inc", "a documentation table", "the docs build"],
            ["the PEG generator", "not generated, edited by hand", "whoever adds a token"],
        ],
        title="Grammar/Tokens is 78 lines, and four files are written from it",
        caption="The last row is the catch. One place still has to be edited by hand, and the file says so at the top.",
        tones=["focus", "quiet", "focus", "quiet", "warning"],
    )
)


gallery.add(
    figures.table(
        "four-front-ends",
        ["constructor", "where the text comes from", "who calls it"],
        [
            ["_PyTokenizer_FromString", "a bytes object, cookie honoured", "compile(b'...')"],
            ["_PyTokenizer_FromUTF8", "a str, cookie ignored", "compile('...')"],
            ["_PyTokenizer_FromFile", "a FILE *, read as it goes", "python script.py"],
            ["_PyTokenizer_FromReadline", "a Python callable", "the tokenize module"],
        ],
        title="Four ways in, and after that the same lexer",
        caption="They differ in one field. Each sets tok->underflow to its own way of getting the next line.",
        tones=["focus", "focus", "intermediate", "durable"],
    )
)


gallery.add(
    figures.spans(
        "one-line-in-the-buffer",
        "b = 2",
        [(0, 2, "cur"), (2, 5, "not read yet")],
        title="The whole of what the tokenizer is holding, at one moment",
        caption="Four pointers into one line. The lines before it are gone and the lines after it are not read.",
    )
)


gallery.add(
    figures.stack(
        "the-state-that-matters",
        [
            "indstack, the column of every open block",
            "indent, how far into that stack we are",
            "altindstack, the same columns counted with tabs worth 1",
            "pendin, how many INDENT or DEDENT tokens still owe you",
            "atbol, whether we are at the start of a line",
            "level, how many brackets are open",
            "parenstack, which brackets they were",
            "cont_line, whether the last line ended in a backslash",
        ],
        title="Eight fields of struct tok_state decide the token stream",
        note="There are about fifty fields in the struct. The other forty are buffers, encodings and f-string bookkeeping.",
    )
)


gallery.add(
    figures.flow(
        "pendin-drains",
        [
            "column 8, two blocks open",
            "next line is at column 0",
            "pendin = -2",
            "one DEDENT",
            "one DEDENT",
            "the NAME on the new line",
        ],
        title="Why two DEDENTs come out of one line ending",
        labels=[
            "the lexer compares",
            "pop twice",
            "drain one",
            "drain one",
        ],
        tones=["input", "input", "warning", "focus", "focus", "durable"],
    )
)


gallery.add(
    figures.compare(
        "two-kinds-of-error",
        (
            "written in the lexer",
            [
                "unterminated string literal",
                "invalid decimal literal",
                "too many nested parentheses",
                "source code cannot contain null bytes",
            ],
        ),
        (
            "a number the parser translates",
            [
                "E_TABSPACE, becomes a TabError",
                "E_TOODEEP, becomes an IndentationError",
                "E_DEDENT, becomes an IndentationError",
                "E_LINECONT, becomes a SyntaxError",
            ],
        ),
        title="Two ways the tokenizer tells you it is unhappy",
        verdict="The left column knows what went wrong and says so. The right column sets a number and lets the parser find the words.",
    )
)


raise SystemExit(gallery.save())
