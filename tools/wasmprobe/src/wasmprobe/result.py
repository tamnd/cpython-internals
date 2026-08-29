"""What one run of the checks produced, and how to keep it on disk.

A run is a plain dictionary of check key to outcome, plus a note saying which runtime made
it. Two runs are compared by the report, so both sides use this shape: the native one this
process produces and the WebAssembly one the Node driver hands back as JSON.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

#: The check ran and returned something.
OK = "ok"

#: The check raised. The runtime is still standing and the next check can go ahead.
RAISED = "raised"

#: The check took the whole runtime down with it. Nothing after it ran in that runtime, so
#: the driver starts a new one and carries on from the next check.
FATAL = "fatal"

#: Never got as far as running, because the run stopped early.
SKIPPED = "skipped"


@dataclass(frozen=True)
class Outcome:
    """One check's answer on one runtime."""

    key: str
    status: str
    value: object = None
    error: str = ""

    @property
    def worked(self) -> bool:
        return self.status == OK

    def as_dict(self) -> dict:
        body = {"key": self.key, "status": self.status}
        if self.value is not None:
            body["value"] = self.value
        if self.error:
            body["error"] = self.error
        return body

    @classmethod
    def from_dict(cls, body: dict) -> Outcome:
        return cls(
            key=str(body["key"]),
            status=str(body["status"]),
            value=body.get("value"),
            error=str(body.get("error", "")),
        )


@dataclass(frozen=True)
class Run:
    """Every outcome from one runtime, and enough about it to name it in a report."""

    runtime: str
    python: str
    outcomes: dict[str, Outcome] = field(default_factory=dict)

    #: How long the runtime took to become ready to run the first check. Zero for the
    #: interpreter this process already is.
    seconds: float = 0.0

    #: What a browser has to download before any of this can start. Zero for a runtime that
    #: was already on the machine. This is the number that decides whether somebody on a
    #: phone waits or closes the tab, more than the boot time does.
    payload_bytes: int = 0

    def as_json(self) -> str:
        body = {
            "runtime": self.runtime,
            "python": self.python,
            "seconds": round(self.seconds, 3),
            "payload_bytes": self.payload_bytes,
            "outcomes": [one.as_dict() for one in self.outcomes.values()],
        }
        return json.dumps(body, indent=2, sort_keys=False) + "\n"

    @classmethod
    def load(cls, path: Path) -> Run:
        body = json.loads(path.read_text(encoding="utf-8"))
        outcomes = {one["key"]: Outcome.from_dict(one) for one in body["outcomes"]}
        return cls(
            runtime=str(body["runtime"]),
            python=str(body["python"]),
            outcomes=outcomes,
            seconds=float(body.get("seconds", 0.0)),
            payload_bytes=int(body.get("payload_bytes", 0)),
        )

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.as_json(), encoding="utf-8")
        return path
