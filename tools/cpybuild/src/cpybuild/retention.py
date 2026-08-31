"""Which published images are safe to delete, worked out before anything is deleted.

The registry fills up. Ten images a week, plus the architecture specific halves the manifest
step leaves behind, and after a few months the package page is a wall of digests nobody can
read. Something has to remove the old ones.

Deleting a container image is not reversible and the thing it breaks is somebody else's
afternoon a year from now, so this module is written to be timid. It takes the list the
registry gave us and returns ids, and the workflow does the deleting. Everything it refuses to
delete, it refuses for a stated reason, and there are four of them:

Anything a release points at stays, however old. A reader who checks out `v0.2.0` and runs the
experiments has to get the interpreter that version was written against.

Anything with a tag on it stays. A tag on a version means it is the current image for one of
the five builds, and the whole point of the lockfile is that those keep resolving.

Anything one of those is made of stays. This one is issue #126 and it cost the whole package.
What we call an image is an index: a short list naming an amd64 manifest, an arm64 manifest and
an attestation for each. Those parts are versions in their own right, and they are never tagged
and never in the lockfile, so the first two rules do not see them. The build is fully cached
against a fixed commit, so a part keeps the same digest week after week and its age never moves,
and one Monday it falls past the floor and is deleted. The index survives and lists two halves
that are not there any more, which reads as `manifest unknown` to everybody pulling it. So the
protected set has to be closed over membership before anything is compared against it.

The newest few hundred stay regardless. This is the crude rule and it is the one that catches
what the other three miss: an image published an hour ago that the lockfile pull request has not
been merged for yet is not protected by anything else, and deleting it would be the tidy up
undoing the run it followed.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Version:
    """One version of the package, as the registry describes it."""

    id: int
    digest: str
    created: str
    tags: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, body: dict) -> Version:
        container = (body.get("metadata") or {}).get("container") or {}
        return cls(
            id=int(body["id"]),
            digest=str(body.get("name", "")),
            created=str(body.get("created_at", "")),
            tags=tuple(container.get("tags") or ()),
        )


def read(body: list[dict]) -> list[Version]:
    return [Version.from_dict(one) for one in body]


def anchors(versions: list[Version], protected: Iterable[str]) -> set[str]:
    """Where the keeping starts: every tagged version, and everything a release named.

    Separate from `reachable` because working out the starting points needs no registry and
    following the membership does, and the two being separate is what lets the interesting
    half be tested against a dictionary.
    """
    return {one.digest for one in versions if one.tags} | set(protected)


def reachable(roots: Iterable[str], children: Callable[[str], Iterable[str]]) -> set[str]:
    """Those digests and everything they are made of, all the way down.

    A breadth first walk rather than one pass, because an index can name an index. Today it
    does not, but the shape that produced #126 was somebody reasonably assuming a fixed depth,
    and a walk costs one `while` loop.

    `children` is passed in rather than reached for, so the tidy up can be tested without a
    registry and so the one place that talks to Docker stays in the command line module.
    """
    seen: set[str] = set()
    queue = list(roots)
    while queue:
        one = queue.pop()
        if one in seen:
            continue
        seen.add(one)
        queue.extend(children(one))
    return seen


def doomed(versions: list[Version], protected: set[str], keep: int) -> list[Version]:
    """The versions that can go, newest first, and nothing else.

    `keep` counts versions and not weeks, because the registry does not group a run's ten
    images into anything, and counting the thing it does give us is one fewer place to be
    subtly wrong.
    """
    newest = sorted(versions, key=lambda one: (one.created, one.id), reverse=True)
    return [one for one in newest[keep:] if not one.tags and one.digest not in protected]


def why(versions: list[Version], protected: set[str], keep: int) -> str:
    """One line saying what is going and what is staying, for the run log."""
    going = doomed(versions, protected, keep)
    tagged = sum(1 for one in versions if one.tags)
    pinned = sum(1 for one in versions if one.digest in protected)
    return (
        f"{len(versions)} versions, deleting {len(going)}: "
        f"{keep} newest kept, {tagged} tagged, "
        f"{pinned} named by a release or part of something named"
    )
