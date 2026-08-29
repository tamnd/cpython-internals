"""The probe as a notebook, so anybody can run it in their own browser.

The recordings in this directory were made by the Node driver, which is convenient and also
one step removed from what a reader will actually use. This notebook closes that gap: open
it in Colab, in JupyterLite, or in a local Jupyter, and it runs the same checks in whatever
Python is underneath and prints the same matrix.

It carries the checks inside itself rather than importing them, because a reader in a
browser tab has not installed this project and should not have to.
"""

from __future__ import annotations

import json
from pathlib import Path

from .checks import CHECKS, Check

#: Where the notebook lives, next to the recordings it can be compared against.
DESTINATION = Path("probes/pyodide/probe.ipynb")

#: The repository, for the badge at the top.
REPOSITORY = "tamnd/cpython-internals"

INTRO = """# Which parts of CPython work in a browser

This project promises that the first experiments in every lesson run in a browser tab with nothing installed. That rests on Pyodide, which is CPython compiled to WebAssembly, and on the introspection surfaces the lessons poke at surviving that build. Some of them do not, and the point of this notebook is to find out which, on the exact runtime you are sitting in front of rather than on one we tested a while ago.

Run every cell. It takes a few seconds and installs nothing. At the end you get a table of what worked here, and you can compare it against the recordings committed next to this file.

One warning worth reading first. One of the checks below asks what happens when the bytecode optimizer is handed a constants list that is too short. On a normal build that raises a tidy exception. In a WebAssembly build it reads past the end of memory and takes the whole runtime with it, which in a notebook means the kernel dies and you have to restart it. That check is last for exactly this reason, and everything above it will have already printed.
"""

CHECKS_INTRO = """## The checks

Each one is a small piece of Python that leaves its answer in a variable called `result`. They are written out in full rather than imported, so you can read what is being asked, and edit one to ask something else.
"""

RUN_INTRO = """## Running them

Each check gets a fresh namespace and anything it throws is caught and recorded, so one failure does not stop the rest. A check that takes the runtime down cannot be caught, which is why the dangerous one is separated out below.
"""

TABLE = '''
def matrix(answers):
    """Print what happened, one row per check."""
    width = max(len(key) for key in answers)
    print(f"{'check'.ljust(width)}  status  answer")
    print("-" * (width + 40))
    for key, (status, answer) in answers.items():
        print(f"{key.ljust(width)}  {status.ljust(6)}  {answer}")


matrix(answers)
'''

RUNNER = """
answers = {}
for key, source in CHECKS.items():
    namespace = {}
    try:
        exec(source, namespace)
    except BaseException as error:
        answers[key] = ("raised", f"{type(error).__name__}: {error}")
    else:
        answers[key] = ("ok", namespace.get("result"))

print(f"{sum(1 for status, _ in answers.values() if status == 'ok')} of {len(answers)} worked")
"""

DANGER = """## The one that can kill the kernel

Everything above has already printed, so run this last. The cell catches the exception itself, so on a normal build you get a tidy `ValueError` naming the constant it could not find. In a browser there is nothing to catch: the read goes past the end of memory, the runtime does not come back, and you restart the kernel.

That difference is the reason the pipeline widget in the lessons builds its own constants list rather than trusting the one it is handed.
"""

TABLE_INTRO = """### The table

The same shape as the matrix in `report.md` next to this notebook, so the two are easy to read against each other. The answer column is whatever the check left in `result`.
"""

AFTERWARDS = """If the cell above came back rather than killing the kernel, here is what it caught. If the kernel died, that is the answer, and it is the one worth telling us about.
"""

CLOSING = """## What to do with this

Compare what you got against `report.md` in this directory, which is the same matrix recorded on a native CPython and on Pyodide under Node.

A check that failed here and passed there is usually your environment: an old Pyodide, a sandbox that blocks threads, a Python built without the test modules. A check that failed in both is our problem, and worth an issue.
"""


def _cell(kind: str, source: str, key: str) -> dict:
    body = {
        "cell_type": kind,
        "id": key,
        "metadata": {},
        "source": source.strip("\n").splitlines(keepends=True),
    }
    if kind == "code":
        body["execution_count"] = None
        body["outputs"] = []
    # Keys in alphabetical order, the same reason the lesson builder does it: that is what
    # nbformat writes, so opening this in Jupyter and saving does not reorder the file.
    return dict(sorted(body.items()))


def _badge() -> str:
    path = f"https://colab.research.google.com/github/{REPOSITORY}/blob/main/{DESTINATION}"
    return f"[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)]({path})"


def _literal(checks: list[Check]) -> str:
    """The checks as a dictionary somebody can read and edit, one entry per check."""
    lines = ["CHECKS = {"]
    for check in checks:
        lines.append(f"    # {check.question}")
        lines.append(f'    "{check.key}": """{check.source}""",')
    lines.append("}")
    lines.append("")
    lines.append('print(f"{len(CHECKS)} checks")')
    return "\n".join(lines)


def build(checks: list[Check] | None = None) -> dict:
    """The notebook, as the dictionary that gets written out as JSON."""
    wanted = checks if checks is not None else CHECKS
    # The dangerous one runs on its own at the end, after everything else has printed.
    safe = [check for check in wanted if check.key != "optimize_cfg_short_consts"]
    risky = [check for check in wanted if check.key == "optimize_cfg_short_consts"]

    written = [
        ("markdown", INTRO + "\n" + _badge()),
        ("markdown", CHECKS_INTRO),
        ("code", _literal(safe)),
        ("markdown", RUN_INTRO),
        ("code", RUNNER),
        ("markdown", TABLE_INTRO),
        ("code", TABLE),
    ]
    if risky:
        written.append(("markdown", DANGER))
        written.append(("code", risky[0].source))
        written.append(("markdown", AFTERWARDS))
        written.append(("code", "print(result)"))
    written.append(("markdown", CLOSING))
    cells = [
        _cell(kind, source, f"probe-{number:02d}")
        for number, (kind, source) in enumerate(written, start=1)
    ]

    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def render(checks: list[Check] | None = None) -> str:
    return json.dumps(build(checks), indent=1, ensure_ascii=False) + "\n"


def write(path: Path | None = None, checks: list[Check] | None = None) -> Path:
    destination = path or DESTINATION
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render(checks), encoding="utf-8")
    return destination
