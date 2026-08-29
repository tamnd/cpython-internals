"""Getting each channel to answer, without letting one bad channel take the survey down.

There is one rule in here worth stating before the code. A channel that cannot be reached
records why, and the report keeps that separate from a Python that answered no. Docker not
being installed is our problem. Fedora not shipping a module is Fedora's answer. A table
that ran the two together would be worse than no table, because the interesting row is
indistinguishable from the broken one.

The question goes into a container base64 encoded. Not for secrecy, obviously. A container
is reached through `sh -c`, the source has quotes and newlines in it, and every layer of
quoting between here and there is a chance to break the source in a way that shows up as a
syntax error attributed to the distribution.
"""

from __future__ import annotations

import base64
import platform
import shutil
import subprocess
import sys

from .channels import CONTAINER, LOCAL, RUNNABLE, Channel
from .question import SOURCE, Answer, Survey, Unreadable, parse

#: Long enough for a package manager on a cold cache. `dnf` on a fresh image regularly takes
#: several minutes before it has said anything at all, and a timeout that fires there gets
#: recorded as unreachable, which reads as our problem rather than the distribution's and is
#: still not the truth. Half an hour rather than fifteen minutes because fifteen was not
#: enough: installing `python3` and `python3-test` together took over that on a cold cache
#: while other containers were competing for the network.
TIMEOUT = 1800

#: The architecture containers are asked for. Taken from the machine rather than left to the
#: daemon, so the recording says what it measured. Nothing found so far packages this
#: differently on two architectures, and a recording that did not say could not tell us.
PLATFORM = "linux/arm64" if platform.machine() in ("arm64", "aarch64") else "linux/amd64"


def encoded() -> str:
    """The question, as one base64 word that survives any amount of shell quoting."""
    return base64.b64encode(SOURCE.encode("utf-8")).decode("ascii")


def container_command(channel: Channel) -> list[str]:
    """The full docker invocation for one channel.

    Built as a list rather than a string so the only shell involved is the one inside the
    container, which is the one whose quoting is being worked around.
    """
    body = channel.setup + " && " if channel.setup else ""
    inner = f"{body}echo {encoded()} | base64 -d > /question.py && python3 /question.py"
    return ["docker", "run", "--rm", "--platform", PLATFORM, channel.where, "sh", "-c", inner]


def local_command(channel: Channel) -> list[str]:
    """Ask an interpreter already on this machine, or this one when no path is named."""
    return [channel.where or sys.executable, "-c", SOURCE]


def reachable(channel: Channel) -> str:
    """Why this channel cannot be asked right now, or an empty string when it can be."""
    if channel.kind == CONTAINER:
        if shutil.which("docker") is None:
            return "docker is not on PATH"
        return ""
    if channel.kind == LOCAL and channel.where and shutil.which(channel.where) is None:
        return f"no interpreter at {channel.where}"
    return ""


def ask(channel: Channel, timeout: int = TIMEOUT) -> Answer:
    """One channel's answer, or an answer that says why there is not one."""
    problem = reachable(channel)
    if problem:
        return Answer(unreachable=problem)
    command = container_command(channel) if channel.kind == CONTAINER else local_command(channel)
    try:
        finished = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired:
        return Answer(unreachable=f"gave up after {timeout} seconds")
    try:
        return parse(finished.stdout)
    except Unreadable:
        tail = (finished.stderr or finished.stdout).strip().splitlines()
        return Answer(unreachable=tail[-1][:160] if tail else "no output at all")


def survey(channels: list[Channel] | None = None, timeout: int = TIMEOUT) -> Survey:
    """Every runnable channel, in order, each one independent of the others."""
    wanted = channels if channels is not None else RUNNABLE
    return Survey(
        machine=PLATFORM,
        answers={one.key: ask(one, timeout=timeout) for one in wanted},
    )
