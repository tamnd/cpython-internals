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
    "disassembler.cache_row": "{count} cache entries",
    "disassembler.specialized": "specialized",
    "disassembler.jump": "jumps to {target}",
    "disassembler.no_exceptions": "This code has no exception table, which means nothing in it can catch anything.",
    "disassembler.exception_range": "offsets {start} to {end} jump to {target}, depth {depth}{lasti}",
    "disassembler.lasti": ", and the instruction that raised is pushed",
    "disassembler.count": "{count} instructions",
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
    return STRINGS[key].format(**values)
