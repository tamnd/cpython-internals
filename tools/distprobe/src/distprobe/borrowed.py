"""The Pyodide row, taken from the browser probe rather than measured again.

Issue 4 asks for Pyodide in this table and issue 1 already answered it, in far more detail
than one row. Re running it here would mean a second Node driver and a second recording that
can disagree with the first, so this reads `wasmprobe`'s recording and turns the one check
this table cares about into an answer.

If the file is not there, the row says so. This is not worth a hard failure: somebody
running `distprobe` on a machine without Node should still get every other row.
"""

from __future__ import annotations

import json
from pathlib import Path

from .question import WANTED, Answer

#: The check in the browser recording that asks this table's question.
CHECK = "internal_capi_import"

#: Where the browser probe leaves its recording, relative to the top of the repository.
RECORDING = Path("probes/pyodide/pyodide.json")


def from_wasmprobe(path: Path = RECORDING) -> Answer:
    """The Pyodide row, built out of the browser probe's own recording."""
    if not path.is_file():
        return Answer(unreachable=f"no browser recording at {path}, run `just build-probe` first")
    body = json.loads(path.read_text(encoding="utf-8"))
    found = {one["key"]: one for one in body.get("outcomes", [])}
    outcome = found.get(CHECK)
    if outcome is None or outcome.get("status") != "ok":
        return Answer(
            version=str(body.get("python", "")),
            platform="emscripten wasm32",
            internal="the browser probe could not import it either",
        )
    present = outcome.get("value") or {}
    return Answer(
        version=str(body.get("python", "")),
        platform="emscripten wasm32",
        prefix="in the browser",
        internal="ok",
        names=tuple(name for name in WANTED if present.get(name)),
        # The browser probe does not ask about `_testcapi`, because nothing in the lessons
        # needs it there. Saying so beats printing a blank cell that reads as a no.
        testcapi="not asked",
    )
