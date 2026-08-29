"""Turning a cell's outputs into text that can be compared across two interpreters.

The whole tool rests on this file being conservative. Every substitution here throws away
a real difference, and the differences this tool exists to find are exactly the ones a
careless normaliser would sweep up: a changed opcode name, a changed size, a changed
number of instructions. So the rule is that a pattern gets normalised only when it varies
between two runs of the same interpreter, which makes it noise rather than a version
difference.

There are three of those. Addresses, which are a different number every time the process
starts. Absolute paths, because the two recordings are made in different directories.
And the total in `sys._debugmallocstats`, which moves with whatever else the process has
allocated.
"""

from __future__ import annotations

import re

#: `0x7f9c1a2b3c40` in a repr, and the same thing in a ctypes or a traceback line. Six or
#: more digits, so a small hex literal a lesson wrote on purpose is left alone.
ADDRESS = re.compile(r"0x[0-9a-fA-F]{6,}")

#: Anything that looks like a POSIX or Windows absolute path. The two recordings are made
#: from different virtual environments, so every path to an installed module differs, and
#: none of those differences is about the language version.
PATH = re.compile(r"(/[\w.+-]+){2,}/?|[A-Za-z]:\\[^\s\"']+")

#: A temporary file name, which nbclient and the kernel both produce.
TEMPORARY = re.compile(r"(tmp|ipykernel)[_-]?\w{4,}")

#: How long something took. A lesson that prints a duration is printing a fact about the
#: machine, and the machine is not what is being compared.
DURATION = re.compile(r"\b\d+(\.\d+)?\s?(ns|us|µs|ms|s)\b")

REPLACEMENTS = (
    (ADDRESS, "0xADDRESS"),
    (PATH, "PATH"),
    (TEMPORARY, "TEMPORARY"),
    (DURATION, "DURATION"),
)


def text(value: str) -> str:
    """One blob of output, with the noise taken out and the trailing space trimmed."""
    for pattern, replacement in REPLACEMENTS:
        value = pattern.sub(replacement, value)
    lines = [line.rstrip() for line in value.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def outputs(cell: dict) -> str:
    """Everything one code cell printed, in order, as one string.

    Images are reduced to a note rather than compared. A diagram embedded in a lesson is
    the same PNG on both interpreters because it came out of the repository, and a plot
    drawn at run time differs in the last byte of its compression for reasons that have
    nothing to do with Python.
    """
    parts = []
    for one in cell.get("outputs", []):
        kind = one.get("output_type")
        if kind == "stream":
            parts.append(_joined(one.get("text", "")))
        elif kind in ("execute_result", "display_data"):
            data = one.get("data", {})
            if "text/plain" in data:
                parts.append(_joined(data["text/plain"]))
            else:
                parts.append(f"<{', '.join(sorted(data))}>")
        elif kind == "error":
            # The message, not the traceback. A traceback is full of file paths and frame
            # counts that differ for reasons the reader does not care about, and a lesson
            # that raises on purpose cares about which exception and what it said.
            parts.append(f"{one.get('ename', '')}: {one.get('evalue', '')}")
    # One newline between outputs, no matter how many the outputs came with. A `print` puts
    # a newline on the end of the stream and a returned value does not, so joining them
    # raw gives a blank line in one cell and not in another for no reason a reader cares
    # about.
    return text("\n".join(part.rstrip("\n") for part in parts))


def _joined(value: object) -> str:
    """Notebook text is a string or a list of strings with the newlines left on."""
    if isinstance(value, list):
        return "".join(str(one) for one in value)
    return str(value)
