"""Where a reader's Python comes from, and how to get one of each to answer the question.

The list is issue 4's list, which is the channels a beginner is actually likely to be
holding. It is not every way to get a Python. Building from source is missing on purpose,
because somebody who built their own can turn the test modules on and this question is about
the ones that arrive already made.

A channel is a container image and a line of shell, or a path to an interpreter already on
this machine. The container ones are the interesting half: they pin the distribution rather
than whatever happens to be installed on the laptop running this, so the answer is about
Debian and not about one person's Debian.

Two channels cannot be answered from here at all, and they are on the list anyway with a
note saying what would answer them. Leaving them off would make the table look complete.
"""

from __future__ import annotations

from dataclasses import dataclass

#: An interpreter already on this machine. The answer is about this laptop as much as about
#: the channel, which is why there are only three of these and none of them is load bearing.
LOCAL = "local"

#: A container image, which is the only way to say Debian and mean Debian.
CONTAINER = "container"

#: Cannot be answered from here. Needs a machine, an operating system or a privilege this
#: process does not have.
ELSEWHERE = "elsewhere"


@dataclass(frozen=True)
class Channel:
    """One way of ending up with a Python, and how to ask it the question."""

    key: str

    #: What a reader would call it, which is what goes in the table.
    name: str

    #: What a reader types to get this Python. In the table, so somebody looking up their
    #: own situation can find the row by recognising the command rather than the name.
    how: str

    kind: str

    #: For LOCAL, the interpreter. For CONTAINER, the image.
    where: str = ""

    #: For CONTAINER, the shell that has to run before there is a `python3` to ask. Empty
    #: when the image already has one, which is the difference between an image built around
    #: Python and an operating system image that happens to be able to install it.
    setup: str = ""

    #: Why this channel is on the list, or what would answer it when it cannot be answered
    #: from here. Printed under the table rather than in it.
    note: str = ""


CHANNELS: list[Channel] = [
    Channel(
        key="uv",
        name="uv python install",
        how="uv python install",
        kind=LOCAL,
        where="",
        note=(
            "The build this project develops against and the one the contributing guide "
            "tells people to use. These are the python-build-standalone binaries, which is "
            "also what `uvx` and `uv run --python` fetch, so it is a lot of readers. No "
            "version in the command because this row is answered by whichever interpreter "
            "is running the survey, which is the pinned one, and writing a version there "
            "would claim something the run did not check."
        ),
    ),
    Channel(
        key="homebrew",
        name="Homebrew",
        how="brew install python@3.14",
        kind=LOCAL,
        where="/opt/homebrew/bin/python3.14",
        note="The usual answer on a Mac that somebody set up for development.",
    ),
    Channel(
        key="macos_system",
        name="macOS system python3",
        how="already there, at /usr/bin/python3",
        kind=LOCAL,
        where="/usr/bin/python3",
        note=(
            "Not a channel anybody should use, and the one a beginner reaches first, "
            "because typing python3 on a Mac finds it. Worth measuring for exactly that "
            "reason."
        ),
    ),
    Channel(
        key="debian",
        name="Debian python3",
        how="apt install python3",
        kind=CONTAINER,
        where="debian:trixie",
        setup="apt-get -qq update && apt-get -qq install -y python3",
        note="Debian stable, so this is what a lot of servers and a lot of WSL installs have.",
    ),
    Channel(
        key="ubuntu",
        name="Ubuntu python3",
        how="apt install python3",
        kind=CONTAINER,
        where="ubuntu:24.04",
        setup="apt-get -qq update && apt-get -qq install -y python3",
        note="The long term support release, which is what Colab and most tutorials assume.",
    ),
    Channel(
        key="fedora",
        name="Fedora python3",
        how="dnf install python3",
        kind=CONTAINER,
        where="fedora:43",
        setup="dnf -q -y install python3",
        note=(
            "Fedora ships a much newer Python than Debian, which makes the answer here a surprise."
        ),
    ),
    Channel(
        key="fedora_test",
        name="Fedora, plus python3-test",
        how="dnf install python3 python3-test",
        kind=CONTAINER,
        where="fedora:43",
        setup="dnf -q -y install python3 python3-test",
        note=(
            "The same image with one more package. On the list because it is the fallback "
            "for the row above, and a fallback nobody has run is a guess."
        ),
    ),
    Channel(
        key="docker",
        name="Official Docker image",
        how="docker run -it python:3.14-slim",
        kind=CONTAINER,
        where="python:3.14-slim",
        setup="",
        note=(
            "The slim variant, because the full one is a superset and would be an easier question."
        ),
    ),
    Channel(
        key="conda",
        name="conda-forge",
        how="conda install python",
        kind=CONTAINER,
        where="condaforge/miniforge3:latest",
        setup="",
        note=(
            "How a lot of scientific Python arrives, and a completely separate build from the rest."
        ),
    ),
    Channel(
        key="pyodide",
        name="Pyodide",
        how="load it in a browser tab",
        kind=ELSEWHERE,
        note=(
            "Answered by `wasmprobe` in probes/pyodide, and copied into this table by "
            "`distprobe survey` so the two do not have to be read side by side. Issue 1 has "
            "the detail."
        ),
    ),
    Channel(
        key="pythonorg_macos",
        name="python.org installer, macOS",
        how="download the .pkg from python.org and double click it",
        kind=ELSEWHERE,
        note=(
            "Installing it needs an administrator password, so this process cannot do it. "
            "The payload can be read without installing: fetch the .pkg, run "
            "`pkgutil --expand-full` on it, and look for a `_testinternalcapi` shared "
            "object under `Python_Framework.pkg`. Somebody who has already installed it "
            "can just run the question."
        ),
    ),
    Channel(
        key="pythonorg_windows",
        name="python.org installer, Windows",
        how="download the .exe from python.org and run it",
        kind=ELSEWHERE,
        note=(
            "Needs a Windows machine. The installer offers a test suite component, and "
            "whether `_testinternalcapi.pyd` lands in a default install is the thing to "
            "find out. Run the question printed by `distprobe question` in the installed "
            "Python and paste the line into this table."
        ),
    ),
]

BY_KEY = {one.key: one for one in CHANNELS}

#: The channels a run on this machine can actually answer.
RUNNABLE = [one for one in CHANNELS if one.kind in (LOCAL, CONTAINER)]
