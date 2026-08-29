"""The five CPython builds this project teaches from.

Most of what the lessons observe is a property of the binary rather than of the language, so
the material needs more than one interpreter to point at. This package holds the list of
builds, the lockfile that names the published images by digest instead of by tag, and the
check that says when the two have fallen out of step.

It builds nothing itself. Compiling CPython five ways on two architectures is a workflow's
job. What is here is the part that has to be readable, testable and runnable on a laptop.
"""

from .configs import (
    ARCHITECTURES,
    BY_KEY,
    COMMON_PACKAGES,
    CONFIGURATIONS,
    RUNNERS,
    Configuration,
    matrix,
    packages,
)
from .images import DIGEST, LOCKFILE, REGISTRY, Broken, Built, Lock, problems

__all__ = [
    "ARCHITECTURES",
    "BY_KEY",
    "COMMON_PACKAGES",
    "CONFIGURATIONS",
    "DIGEST",
    "LOCKFILE",
    "REGISTRY",
    "RUNNERS",
    "Broken",
    "Built",
    "Configuration",
    "Lock",
    "matrix",
    "packages",
    "problems",
]
