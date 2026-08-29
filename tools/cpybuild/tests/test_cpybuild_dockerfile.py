"""Things about the Dockerfile that only a failed twenty minute build would otherwise tell us.

Nothing in here builds an image. These are the properties that are cheap to read off the text
and expensive to learn from CI, which is most of what goes wrong with a Dockerfile.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

DOCKERFILE = Path(__file__).parents[3] / "images" / "cpython" / "Dockerfile"

TEXT = DOCKERFILE.read_text(encoding="utf-8")

#: Every RUN block, with the line continuations joined, so a test can ask what one command did
#: without caring how it was wrapped.
COMMANDS = [
    " ".join(part.strip() for part in one.split("\\\n"))
    for one in re.findall(r"^RUN .*?(?=\n[A-Z#]|\n\n|\Z)", TEXT, re.MULTILINE | re.DOTALL)
]

INSTALLS = [one for one in COMMANDS if "apt-get" in one]


def test_both_stages_install_packages():
    """The guard on the tests below: if this is ever one, they stopped covering a stage."""
    assert len(INSTALLS) == 2


@pytest.mark.parametrize("command", INSTALLS, ids=["build", "final"])
def test_apt_is_told_to_retry_a_failed_download(command):
    """apt gives up on the first failed fetch, and a package mirror dropping one connection is
    an ordinary Tuesday. The first run of this on main lost both JIT builds twenty seconds in
    to `Could not resolve 'apt.llvm.org'`, on a host whose index had been fetched a moment
    earlier. Twenty minutes of matrix is too much to lose to one unlucky lookup."""
    assert 'Acquire::Retries "5"' in command


@pytest.mark.parametrize("command", INSTALLS, ids=["build", "final"])
def test_the_retry_setting_is_written_before_anything_is_fetched(command):
    """Written after the first `apt-get update` it would still be there, and would still have
    let that update fail."""
    assert command.index("Acquire::Retries") < command.index("apt-get")


@pytest.mark.parametrize("command", INSTALLS, ids=["build", "final"])
def test_the_package_lists_are_deleted_in_the_same_layer_that_made_them(command):
    """Layers only add. A separate `rm` leaves the forty megabytes in the image anyway."""
    assert command.rstrip().endswith("rm -rf /var/lib/apt/lists/*")


def test_the_llvm_key_download_retries_too():
    """It is one curl to one host, and that host is the one that has actually gone missing."""
    key = next(one for one in COMMANDS if "llvm-snapshot.gpg.key" in one)
    assert "--retry" in key


def test_the_llvm_repository_is_only_added_when_a_build_asks_for_one():
    """Every other build takes Debian's clang, and an apt source nobody needs is a thing that
    can go down and take four passing builds with it."""
    key = next(one for one in COMMANDS if "llvm-snapshot.gpg.key" in one)
    assert 'if [ -n "${LLVM}" ]' in key
