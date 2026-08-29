"""Every word a widget puts on screen, in one file.

Not because a translation is planned, but because one might be, and the cost of collecting
the strings later is that somebody reads thirty templates looking for text. The cost of
collecting them now is this file. It is also a useful discipline on its own: a label written
here, away from the layout, tends to get read as a sentence rather than as a gap in a table.

The keys are dotted and start with the widget they belong to, so that a widget's whole
vocabulary is one grep. `common.*` is for words shared across widgets, and a word that ends
up in two widgets should move there rather than being written twice with a comma
different in one of them.
"""

from __future__ import annotations

import difflib

STRINGS: dict[str, str] = {
    # Shared.
    "common.python": "Python {version}",
    "common.static_notice": "This is the static picture. Install the live extra and call .live() to click on it.",
    "common.nothing": "Nothing to show yet.",
    "common.error": "That did not compile: {reason}",
    # The disassembler.
    "disassembler.title": "Bytecode",
    "disassembler.source": "Source",
    "disassembler.offset": "Offset",
    "disassembler.instruction": "Instruction",
    "disassembler.argument": "Argument",
    "disassembler.meaning": "What the argument means",
    "disassembler.depth": "Stack",
    "disassembler.adaptive": "Specialized opcodes",
    "disassembler.caches": "Inline caches",
    "disassembler.depths": "Stack depth",
    "disassembler.exceptions": "Exception table",
    "disassembler.cache_row": "{count} cache entr{ies}",
    "disassembler.specialized": "specialized",
    "disassembler.jump": "jumps to {target}",
    "disassembler.no_exceptions": "This code has no exception table, which means nothing in it can catch anything.",
    "disassembler.exception_range": "offsets {start} to {end} jump to {target}, depth {depth}{lasti}",
    "disassembler.lasti": ", and the instruction that raised is pushed",
    "disassembler.count": "{count} instruction{s}",
    # The pipeline explorer.
    "pipeline.title": "From source to a code object",
    "pipeline.tokens": "Tokens",
    "pipeline.tree": "The tree",
    "pipeline.symbols": "The symbol table",
    "pipeline.codegen": "After code generation",
    "pipeline.optimized": "After the optimizer",
    "pipeline.code": "The code object",
    "pipeline.count_tokens": "{count} token{s}",
    "pipeline.count_nodes": "{count} node{s}",
    "pipeline.count_scopes": "{count} scope{s}",
    "pipeline.count_instructions": "{count} instruction{s}",
    "pipeline.count_after": "{count} instruction{s}, {gone} gone",
    "pipeline.count_bytes": "{count} byte{s}",
    "pipeline.more_lines": "and {count} more line{s}",
    "pipeline.no_internals": "not on this build",
    "pipeline.why_no_internals": "Two of these panes run the compiler one stage at a time, which needs the _testinternalcapi module. This interpreter was built without it, so those two are empty and the other four are unaffected.",
    # The prediction gate.
    "predict.title": "Predict first",
    "predict.reveal": "Show the answer, once you have picked one",
    "predict.right": "that is the one",
    "predict.wrong": "not this time",
    "predict.answer": "the answer",
    "predict.yours": "what you picked",
    "predict.check": "Run this if you want to see it for yourself:",
}


#: The plural endings a string can ask for, written as `{s}` or `{ies}` next to a `{count}`.
#: Filled in from the count, so that a string says "1 token" and "2 tokens" without every
#: caller doing the arithmetic. This is the first thing on screen in the first lesson, and
#: "1 tokens" is the kind of thing a reader notices and then stops trusting.
#:
#: The endings stay in the string rather than being computed in the code, so a translator
#: gets a whole sentence to work with and can move or drop them. English is the easy case
#: here and this will not survive a language with three plural forms, but the shape is right:
#: the thing that needs replacing is one dictionary, not thirty call sites.
ENDINGS: dict[str, tuple[str, str]] = {
    "s": ("", "s"),
    "ies": ("y", "ies"),
}


def text(key: str, **values: object) -> str:
    """One string, with its placeholders filled in.

    An unknown key raises, and says what it thinks you meant. A widget asking for a string
    that is not here is a widget that would otherwise render the key, and a table with
    `disassembler.ofset` written across the top of a column is a bug that ships.
    """
    if key not in STRINGS:
        close = difflib.get_close_matches(key, STRINGS, n=3)
        hint = f", did you mean {' or '.join(close)}" if close else ""
        raise KeyError(f"no string called {key!r}{hint}")
    template = STRINGS[key]
    count = values.get("count")
    if isinstance(count, int):
        one = abs(count) == 1
        values = values | {name: forms[0] if one else forms[1] for name, forms in ENDINGS.items()}
    return template.format(**values)
