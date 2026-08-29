"""The one question, written once, as source that gets shipped to whatever is answering.

Every channel in `channels.py` answers the same question, and most of them are a Python
inside a container that knows nothing about this package. So the question travels as a
string of source rather than as a function, the same trick `wasmprobe` uses, and for the
same reason: two copies of a question drift, and the drift is silent because both copies
keep working.

The source prints one line of JSON and nothing else. It imports only `json`, `sys` and
`sysconfig`, so it runs on any CPython back to about 3.2, which matters because one of the
answers is a Python 3.9 that shipped with an operating system in 2021.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

#: The three functions `pyxray.compiler` reaches for. Importing the module is not enough:
#: a build can ship the module and not these, which is what an old Python looks like, since
#: `compiler_codegen` and the other two only arrived in 3.12.
WANTED = ("compiler_codegen", "optimize_cfg", "assemble_code_object")

SOURCE = """
import json
import sys
import sysconfig

answer = {
    "version": sys.version.split()[0],
    "platform": sysconfig.get_platform(),
    "prefix": sys.prefix,
}
try:
    import _testinternalcapi
    answer["internal"] = "ok"
    answer["names"] = [
        name
        for name in ("compiler_codegen", "optimize_cfg", "assemble_code_object")
        if hasattr(_testinternalcapi, name)
    ]
except BaseException as problem:
    answer["internal"] = type(problem).__name__ + ": " + str(problem)[:120]
    answer["names"] = []
try:
    import _testcapi
    answer["testcapi"] = "ok"
except BaseException as problem:
    answer["testcapi"] = type(problem).__name__

print("DISTPROBE " + json.dumps(answer))
"""

#: What the answer line starts with. The channels that run in a container print apt and dnf
#: noise on the way past, and a marker is cheaper than trying to silence six package
#: managers, each of which has its own idea of which stream is for progress.
MARKER = "DISTPROBE "


class Unreadable(ValueError):
    """Nothing in the output looked like an answer."""


@dataclass(frozen=True)
class Answer:
    """What one Python said, in the shape the report and the tests work with."""

    #: Empty when the module imported. Otherwise the exception, as text.
    internal: str = ""
    version: str = ""
    platform: str = ""
    prefix: str = ""
    names: tuple[str, ...] = ()
    testcapi: str = ""

    #: Set when the channel could not be reached at all, which is a different thing from a
    #: Python saying no. A missing container image is our problem and a missing module is
    #: the distribution's, and a report that ran them together would be worthless.
    unreachable: str = ""

    @property
    def has_module(self) -> bool:
        return self.internal == "ok"

    @property
    def has_everything(self) -> bool:
        """The module is there and so are all three functions, which is what a lesson needs."""
        return self.has_module and set(WANTED) <= set(self.names)

    @property
    def missing(self) -> tuple[str, ...]:
        return tuple(name for name in WANTED if name not in self.names)

    def as_dict(self) -> dict:
        body = {
            "version": self.version,
            "platform": self.platform,
            "prefix": self.prefix,
            "internal": self.internal,
            "names": list(self.names),
            "testcapi": self.testcapi,
        }
        if self.unreachable:
            body["unreachable"] = self.unreachable
        return body

    @classmethod
    def from_dict(cls, body: dict) -> Answer:
        return cls(
            internal=str(body.get("internal", "")),
            version=str(body.get("version", "")),
            platform=str(body.get("platform", "")),
            prefix=str(body.get("prefix", "")),
            names=tuple(body.get("names", ())),
            testcapi=str(body.get("testcapi", "")),
            unreachable=str(body.get("unreachable", "")),
        )


def parse(output: str) -> Answer:
    """Pull the answer out of whatever else the channel printed on the way.

    Reads the last marked line rather than the first. A container that installs a package
    before answering can print something that happens to start with the marker only if
    somebody has gone out of their way, and taking the last line means a retry inside the
    same command still gives the answer rather than the first attempt.
    """
    lines = [one for one in output.splitlines() if one.startswith(MARKER)]
    if not lines:
        raise Unreadable("no answer line in the output")
    return Answer.from_dict(json.loads(lines[-1][len(MARKER) :]))


@dataclass(frozen=True)
class Survey:
    """Every channel's answer, and enough about the run to know what it is worth.

    `machine` is in here because a container answer on an arm64 laptop is an arm64 answer.
    That has not mattered yet, since no distribution has been found packaging the module
    differently on two architectures, but a recording that does not say what it ran on
    cannot be checked later.
    """

    machine: str = ""
    answers: dict[str, Answer] = field(default_factory=dict)

    def as_json(self) -> str:
        body = {
            "machine": self.machine,
            "answers": {key: value.as_dict() for key, value in self.answers.items()},
        }
        return json.dumps(body, indent=2) + "\n"

    @classmethod
    def from_json(cls, text: str) -> Survey:
        body = json.loads(text)
        return cls(
            machine=str(body.get("machine", "")),
            answers={
                key: Answer.from_dict(value) for key, value in body.get("answers", {}).items()
            },
        )
