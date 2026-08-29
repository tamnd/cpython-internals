"""Which published images are safe to delete, worked out before anything is deleted.

The registry fills up. Ten images a week, plus the architecture specific halves the manifest
step leaves behind, and after a few months the package page is a wall of digests nobody can
read. Something has to remove the old ones.

Deleting a container image is not reversible and the thing it breaks is somebody else's
afternoon a year from now, so this module is written to be timid. It takes the list the
registry gave us and returns ids, and the workflow does the deleting. Everything it refuses to
delete, it refuses for a stated reason, and there are three of them:

Anything a release points at stays, however old. A reader who checks out `v0.2.0` and runs the
experiments has to get the interpreter that version was written against.

Anything with a tag on it stays. A tag on a version means it is the current image for one of
the five builds, and the whole point of the lockfile is that those keep resolving.

The newest few hundred stay regardless. This is the crude rule and it is the one that catches
what the other two miss: an image published an hour ago that the lockfile pull request has not
been merged for yet is not protected by anything else, and deleting it would be the tidy up
undoing the run it followed.
"""

from __future__ import annotations

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
        f"{keep} newest kept, {tagged} tagged, {pinned} pointed at by a release"
    )
