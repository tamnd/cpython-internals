"""Opcode facts, read from the tables CPython generates for itself.

None of this is a table we maintain. `_opcode_metadata` is generated from
`Python/bytecodes.c` by `Tools/cases_generator` when CPython is built, so asking it is
asking the same source the interpreter was compiled from. A hand written copy would be
wrong within one release, which is the whole thesis of this project applied to itself.
"""

from __future__ import annotations

import dis
import opcode
from functools import lru_cache


@lru_cache(maxsize=1)
def _specializations() -> dict[str, str]:
    """Specialized opcode name to the base opcode it specializes."""
    try:
        from _opcode_metadata import _specializations as families
    except ImportError:
        return {}
    return {special: base for base, specials in families.items() for special in specials}


@lru_cache(maxsize=1)
def _families() -> dict[str, tuple[str, ...]]:
    """Base opcode name to every specialized form of it."""
    try:
        from _opcode_metadata import _specializations as families
    except ImportError:
        return {}
    return {base: tuple(specials) for base, specials in families.items()}


def is_specialized(name: str) -> bool:
    """Is this a form the interpreter rewrote in, rather than one the compiler emitted?"""
    return name in _specializations()


def base_name(name: str) -> str:
    """The opcode the compiler emitted, given any form of it."""
    return _specializations().get(name, name)


def family(name: str) -> tuple[str, ...]:
    """Every specialized form of an opcode, in the order the metadata lists them."""
    return _families().get(base_name(name), ())


def cache_entries(name: str) -> int:
    """How many inline cache entries follow this instruction.

    These are real bytes in `co_code`. A reader stepping through offsets by hand and
    getting them wrong is almost always forgetting these, because ordinary `dis` output
    does not show them but the offsets step over them.
    """
    return dis._inline_cache_entries.get(name, 0) if hasattr(dis, "_inline_cache_entries") else 0


@lru_cache(maxsize=1)
def name_by_number() -> dict[int, str]:
    """Every opcode number to its name, specialized and pseudo instructions included.

    Neither of the two tables CPython exposes is enough on its own, and picking the wrong
    one gives you a map with holes in it rather than an error.

    `opcode.opname` is a list of 256 entries and it does include the specialized forms the
    interpreter rewrites in, but it stops at 255. `opcode.opmap` goes past 255 and so
    covers the pseudo instructions the compiler uses internally, but it leaves the
    specialized forms out entirely, which on this release is 91 missing names. Merging
    them is safe because no number appears in both with a different name.
    """
    table = {number: name for number, name in enumerate(opcode.opname) if not name.startswith("<")}
    table.update({number: name for name, number in opcode.opmap.items()})
    return table


def opcode_name(number: int) -> str:
    """Name an opcode number, including the pseudo instructions."""
    return name_by_number().get(number, f"<{number}>")


def is_pseudo(number: int) -> bool:
    """Is this an instruction that exists only inside the compiler?

    Pseudo instructions carry information between compiler stages and never appear in a
    finished code object. Seeing them disappear between codegen and assembly is one of
    the clearer moments in the front end lessons.
    """
    return number > 255


def has_argument(number: int) -> bool:
    try:
        import _opcode

        return bool(_opcode.has_arg(number))
    except ImportError, ValueError:
        return number >= opcode.HAVE_ARGUMENT
