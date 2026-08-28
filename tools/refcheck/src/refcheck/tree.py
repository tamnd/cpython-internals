"""Locating and reading the pinned CPython tree."""

from __future__ import annotations

import os
import subprocess
from functools import lru_cache
from pathlib import Path

PINNED_TAG = "v3.15.0rc1"
PINNED_COMMIT = "37e98da7c19a9e5892ee756d6dee08225422cd49"

_DEFAULT_RELATIVE = Path("vendor/cpython")


class TreeNotFound(RuntimeError):
    """Raised when no pinned checkout can be located."""


def find_tree(explicit: str | os.PathLike[str] | None = None) -> Path:
    """Return the root of the pinned CPython checkout.

    Resolution order is the explicit argument, then ``CPYTHON_SRC``, then
    ``vendor/cpython`` relative to the repository root. The environment variable exists
    so that a contributor who already has a checkout does not have to keep a second copy,
    and so that CI can point at a cached one.
    """
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(Path(explicit))
    env = os.environ.get("CPYTHON_SRC")
    if env:
        candidates.append(Path(env))
    candidates.append(repo_root() / _DEFAULT_RELATIVE)

    for candidate in candidates:
        if (candidate / "Include" / "Python.h").is_file():
            return candidate.resolve()

    tried = ", ".join(str(c) for c in candidates)
    raise TreeNotFound(
        f"no CPython checkout found (tried {tried}); run `just vendor` "
        f"or set CPYTHON_SRC to a checkout of {PINNED_TAG}"
    )


@lru_cache(maxsize=1)
def repo_root() -> Path:
    """The root of this repository, found by walking up for the marker file."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file() and (parent / ".git").exists():
            return parent
    return Path.cwd()


def tree_commit(tree: Path) -> str | None:
    """The commit the checkout is at, or None if it is not a git checkout."""
    try:
        result = subprocess.run(
            ["git", "-C", str(tree), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except OSError, subprocess.SubprocessError:
        return None
    return result.stdout.strip() or None


@lru_cache(maxsize=512)
def read_lines(tree: Path, path: str) -> tuple[str, ...]:
    """Every line of one file in the tree, without line endings.

    Cached because a lesson typically cites the same handful of files many times and
    reading ``Python/bytecodes.c`` once per citation is a measurable share of the check.
    """
    target = tree / path
    text = target.read_text(encoding="utf-8", errors="surrogateescape")
    return tuple(text.splitlines())
