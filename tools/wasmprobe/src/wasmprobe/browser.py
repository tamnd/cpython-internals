"""Running the same checks on Pyodide, which is CPython built for WebAssembly.

Python cannot host that runtime itself, so this hands the work to a small Node script and
reads back what it wrote. The checks travel as JSON so the Node side never has to know
anything about this package beyond "here is a list of things with a source field".

The one thing this module knows that the driver does not is what a missing outcome means.
A check the driver never reached, because an earlier one took the process down rather than
just the runtime, comes back as skipped rather than as a silent absence.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .checks import CHECKS, Check
from .result import FATAL, SKIPPED, Outcome, Run

#: The driver, next to the package rather than inside it, because it is not Python.
DRIVER = Path(__file__).resolve().parents[2] / "driver.mjs"


class Missing(RuntimeError):
    """Node or the Pyodide package is not installed."""


def ready() -> str:
    """The problem stopping a browser run, or an empty string when there is none."""
    if shutil.which("node") is None:
        return "node is not on PATH"
    if not (DRIVER.parent / "node_modules" / "pyodide").is_dir():
        return f"pyodide is not installed, run npm install in {DRIVER.parent}"
    return ""


def run(checks: list[Check] | None = None, timeout: int = 900) -> Run:
    """Every check, in order, inside a WebAssembly runtime."""
    problem = ready()
    if problem:
        raise Missing(problem)
    wanted = checks if checks is not None else CHECKS
    with tempfile.TemporaryDirectory() as room:
        inbox = Path(room) / "checks.json"
        outbox = Path(room) / "out.json"
        inbox.write_text(
            json.dumps([{"key": one.key, "source": one.source} for one in wanted]),
            encoding="utf-8",
        )
        finished = subprocess.run(
            ["node", str(DRIVER), str(inbox), str(outbox)],
            cwd=DRIVER.parent,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if not outbox.exists():
            tail = (finished.stderr or finished.stdout).strip().splitlines()
            raise Missing("the driver wrote nothing: " + (tail[-1] if tail else "no output"))
        body = json.loads(outbox.read_text(encoding="utf-8"))
    return _assemble(body, wanted, finished.returncode)


def _assemble(body: dict, wanted: list[Check], code: int) -> Run:
    """Turn the driver's JSON into a Run, filling in the checks it never reached."""
    outcomes = {one["key"]: Outcome.from_dict(one) for one in body["outcomes"]}
    for check in wanted:
        if check.key not in outcomes:
            outcomes[check.key] = Outcome(check.key, SKIPPED, error="the run stopped first")
    if code != 0:
        # The driver exiting badly means the last check it started took the process with
        # it, not only the runtime. The placeholder it wrote before starting is already
        # fatal, so this only fills in a better sentence.
        last = body["outcomes"][-1]["key"] if body["outcomes"] else ""
        if last and outcomes[last].status == FATAL:
            outcomes[last] = Outcome(last, FATAL, error="took the whole process down")
    return Run(
        runtime=str(body.get("runtime", "pyodide")),
        python=str(body.get("python", "unknown")),
        outcomes={check.key: outcomes[check.key] for check in wanted},
        seconds=float(body.get("seconds", 0.0)),
        payload_bytes=int(body.get("payload_bytes", 0)),
    )
