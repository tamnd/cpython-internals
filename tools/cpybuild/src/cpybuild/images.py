"""The lockfile: which image is which, named by digest rather than by tag.

A tag is a name somebody can move. `:debug` today and `:debug` next month can be different
images, and if one of them stops having `sys.gettotalrefcount` the lesson that depended on it
fails on a machine nobody changed. A digest is the image. Referring to builds by digest is
the whole reason this file exists, and `cpybuild check` is what stops somebody quietly
writing a tag into a workflow instead.

The lockfile also records which CPython commit went in, so a reader who wants to know what
they are stepping through has an answer that does not involve trusting a label.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from refcheck import PINNED_COMMIT, PINNED_TAG

from .configs import ARCHITECTURES, CONFIGURATIONS

#: Where the images are published. GitHub's registry, because the repository is already there
#: and a second account to keep credentials for is a second thing to go wrong.
REGISTRY = "ghcr.io/tamnd/cpython-internals/cpython"

#: The committed lockfile, relative to the top of the repository.
LOCKFILE = Path("images/cpython.lock.json")

#: A digest is sha256 and sixty four hex characters. Checked rather than assumed, because the
#: failure mode of a typo here is an image reference that pulls nothing with no explanation.
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")

#: The devcontainer, which is the only thing outside CI that pulls one of these images.
DEVCONTAINER = Path(".devcontainer/devcontainer.json")

#: The image line in the devcontainer. That file is rewritten rather than regenerated: it has
#: comments in it that are there for a person to read, and a generator that reprinted the whole
#: file would either lose them or take ownership of them.
IMAGE_LINE = re.compile(r'("image"\s*:\s*")([^"]*)(")')


class Broken(ValueError):
    """The lockfile says something that cannot be true."""


@dataclass(frozen=True)
class Built:
    """One image: one configuration on one architecture."""

    digest: str
    built: str
    size: int = 0

    def as_dict(self) -> dict:
        return {"digest": self.digest, "built": self.built, "size": self.size}

    @classmethod
    def from_dict(cls, body: dict) -> Built:
        return cls(
            digest=str(body.get("digest", "")),
            built=str(body.get("built", "")),
            size=int(body.get("size", 0)),
        )


@dataclass(frozen=True)
class Lock:
    """Every image, and the CPython it was built from."""

    tag: str = PINNED_TAG
    commit: str = PINNED_COMMIT
    registry: str = REGISTRY
    images: dict[str, dict[str, Built]] = field(default_factory=dict)

    #: The joined image for each configuration, the one a person pulls without saying which
    #: architecture they are on. It is a separate digest rather than either half's, because
    #: joining two architectures copies their manifests into a new index and that index is its
    #: own object in the registry. Recorded here so the devcontainer can name it and so the
    #: tidy up knows not to delete it.
    indexes: dict[str, Built] = field(default_factory=dict)

    def get(self, config: str, arch: str) -> Built | None:
        return self.images.get(config, {}).get(arch)

    def index(self, config: str) -> Built | None:
        return self.indexes.get(config)

    def reference(self, config: str, arch: str) -> str:
        """What to write in a workflow or a devcontainer, which is never a bare tag."""
        found = self.get(config, arch)
        if found is None:
            raise Broken(f"no {config} image for {arch} in the lockfile")
        return f"{self.registry}:{config}@{found.digest}"

    def reference_index(self, config: str) -> str:
        """What a devcontainer names: one reference that works on either architecture."""
        found = self.index(config)
        if found is None:
            raise Broken(f"no joined {config} image in the lockfile")
        return f"{self.registry}:{config}@{found.digest}"

    def record(self, config: str, arch: str, digest: str, size: int = 0) -> None:
        self.images.setdefault(config, {})[arch] = Built(
            digest=digest, built=date.today().isoformat(), size=size
        )

    def record_index(self, config: str, digest: str, size: int = 0) -> None:
        self.indexes[config] = Built(digest=digest, built=date.today().isoformat(), size=size)

    def as_json(self) -> str:
        body = {
            "tag": self.tag,
            "commit": self.commit,
            "registry": self.registry,
            "images": {
                name: {arch: one.as_dict() for arch, one in sorted(builds.items())}
                for name, builds in sorted(self.images.items())
            },
            "indexes": {name: one.as_dict() for name, one in sorted(self.indexes.items())},
        }
        return json.dumps(body, indent=2) + "\n"

    @classmethod
    def from_json(cls, text: str) -> Lock:
        body = json.loads(text)
        return cls(
            tag=str(body.get("tag", PINNED_TAG)),
            commit=str(body.get("commit", PINNED_COMMIT)),
            registry=str(body.get("registry", REGISTRY)),
            images={
                name: {arch: Built.from_dict(one) for arch, one in builds.items()}
                for name, builds in body.get("images", {}).items()
            },
            indexes={name: Built.from_dict(one) for name, one in body.get("indexes", {}).items()},
        )

    @classmethod
    def load(cls, path: Path = LOCKFILE) -> Lock:
        if not path.is_file():
            raise Broken(f"no lockfile at {path}, run the cpython-images workflow first")
        return cls.from_json(path.read_text(encoding="utf-8"))

    def write(self, path: Path = LOCKFILE) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.as_json(), encoding="utf-8")


def digests(lock: Lock) -> set[str]:
    """Every digest one lockfile refers to, the joined images included.

    The joined ones matter as much as the halves here, because this set is what the tidy up
    is not allowed to delete and the joined image is the one a reader pulls.
    """
    found = {one.digest for builds in lock.images.values() for one in builds.values()}
    return found | {one.digest for one in lock.indexes.values()}


def _from_git(revision: str, path: str = str(LOCKFILE)) -> str | None:
    """The contents of a file as of some revision, or None if it was not there yet."""
    done = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return done.stdout if done.returncode == 0 else None


def _release_tags() -> list[str]:
    done = subprocess.run(
        ["git", "tag", "--list", "v*"], capture_output=True, text=True, check=False
    )
    return [one for one in done.stdout.split() if one]


def protected(
    tags: Iterable[str] | None = None,
    read: Callable[[str], str | None] = _from_git,
) -> set[str]:
    """Every digest that must survive a tidy up, because something published points at it.

    The retention rule is the last few weekly builds plus every image a released version of
    the site refers to, and the second half of that cannot be expressed as a count. A reader
    who checks out `v0.2.0` and runs the experiments has to get the interpreter that version
    was written against, so the digests in the lockfile as of every release tag are read back
    out of git and kept, however old they are.

    Both the tag list and the file reads are injectable so the tests can describe a repository
    without making one.
    """
    names = list(_release_tags() if tags is None else tags)
    found: set[str] = set()
    for name in names:
        body = read(name)
        if body is None:
            # A tag from before the images existed. Not a problem, just nothing to keep.
            continue
        try:
            found |= digests(Lock.from_json(body))
        except (ValueError, TypeError) as error:
            # Refusing rather than skipping. Skipping would mean the tidy up quietly stops
            # protecting that release's images and deletes them, and the reader who finds out
            # is one running `v0.2.0` a year later against a digest that no longer resolves.
            # Failing here means nothing is deleted, which is the direction to fail in.
            raise Broken(f"the lockfile at {name} cannot be read: {error}") from error
    return found


def problems(lock: Lock) -> list[str]:
    """Everything wrong with a lockfile, in the order somebody would want to fix it.

    A list rather than an exception, because reporting the first of eight missing images and
    stopping means eight runs of a job that takes twenty minutes.
    """
    found = []
    if lock.tag != PINNED_TAG:
        found.append(f"built from {lock.tag}, and the project is pinned to {PINNED_TAG}")
    if lock.commit != PINNED_COMMIT:
        found.append(f"built from commit {lock.commit[:12]}, and the pin is {PINNED_COMMIT[:12]}")
    for one in CONFIGURATIONS:
        for arch in ARCHITECTURES:
            built = lock.get(one.key, arch)
            if built is None:
                found.append(f"no {one.key} image for {arch}")
            elif not DIGEST.match(built.digest):
                found.append(f"{one.key} on {arch} has a digest that is not one: {built.digest}")
    for one in CONFIGURATIONS:
        joined = lock.index(one.key)
        if joined is None:
            found.append(f"no joined {one.key} image, so nothing can pull it without an arch")
        elif not DIGEST.match(joined.digest):
            found.append(f"the joined {one.key} image has a digest that is not one")
    known = {one.key for one in CONFIGURATIONS}
    for name in sorted((set(lock.images) | set(lock.indexes)) - known):
        found.append(f"{name} is in the lockfile and not in the configuration list")
    return found


def image_in(text: str) -> str:
    """Which image a devcontainer file names."""
    found = IMAGE_LINE.search(text)
    if found is None:
        raise Broken("the devcontainer names no image")
    return found.group(2)


def retarget(text: str, reference: str) -> str:
    """The same devcontainer file, pointed at another image.

    A replacement rather than a rewrite, so the comments in that file survive the weekly
    rebuild moving a digest under them.
    """
    if IMAGE_LINE.search(text) is None:
        raise Broken("the devcontainer names no image")
    return IMAGE_LINE.sub(lambda found: found.group(1) + reference + found.group(3), text, count=1)


def devcontainer_problems(lock: Lock, text: str, config: str = "debug") -> list[str]:
    """Whether the devcontainer still points at the image the lockfile describes.

    The two files are updated by the same job and drift the moment somebody edits one of them
    by hand, and the way that drift shows up otherwise is a reader spending an evening in an
    interpreter that is a month older than everything the lessons say about it.
    """
    try:
        named = image_in(text)
        wanted = lock.reference_index(config)
    except Broken as error:
        return [str(error)]
    if named != wanted:
        return [f"the devcontainer pulls {named} and the lockfile says {wanted}"]
    return []
