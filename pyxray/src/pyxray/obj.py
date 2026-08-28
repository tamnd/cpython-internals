"""Looking at an object the way the interpreter does.

Nothing in here needs a debug build, a C compiler or `ctypes`, which is deliberate. A
reader on a locked down laptop running this in a browser tab has to be able to see a real
reference count on a real object, not a picture of one.
"""

from __future__ import annotations

import dis
import gc
import sys
import types
from dataclasses import dataclass
from functools import cache, lru_cache

#: CPython marks an object immortal by parking its reference count at a value the
#: interpreter never decrements. The number itself is an implementation detail that has
#: already changed once, so nothing here compares against it: `sys._is_immortal` is the
#: supported question and we ask that instead.
_IMMORTAL_HINT = "refcount is parked, this object is never freed"


@dataclass(frozen=True)
class Header:
    """What sits in front of every Python object in memory."""

    address: int
    type_name: str
    refcount: int | None
    immortal: bool
    size: int
    gc_tracked: bool
    gc_trackable: bool

    def describe(self) -> str:
        count = _IMMORTAL_HINT if self.immortal else f"{self.refcount} reference(s)"
        tracked = "tracked by the cycle collector" if self.gc_tracked else "not tracked"
        return f"{self.type_name} at {self.address:#x}, {count}, {self.size} bytes, {tracked}"


def is_immortal(obj: object) -> bool:
    """Is this object one the interpreter will never free?

    True, False, None, small integers, interned strings and every type object are
    immortal, which is why their reference counts look absurd. Immortality landed in 3.12
    so that these objects stop being written to on every access, which matters enormously
    once there is no GIL protecting the write.
    """
    checker = getattr(sys, "_is_immortal", None)
    if checker is not None:
        return bool(checker(obj))
    # Older builds have no direct question to ask, so fall back to the shape of the
    # answer: an object nothing can plausibly hold a billion references to.
    return sys.getrefcount(obj) > 2**30


#: Instructions that hand the interpreter a borrowed reference rather than a new one.
#: `LOAD_FAST_BORROW` arrived in 3.14 and is the reason `sys.getrefcount` stopped being
#: reliably one too high. The name of the opcode is the whole explanation, which is rare
#: and worth pointing at in a lesson.
_BORROWING_LOADS = ("LOAD_FAST_BORROW",)


@cache
def _own_call_cost() -> int:
    """Does passing a local to a function inside this module create a reference?

    Measured, not assumed. A fresh `object()` bound to one local has exactly one
    reference, so whatever `sys.getrefcount` adds on top of that is the cost of the call
    itself. On 3.14 and later the load is borrowing and this is 0. On 3.13 and earlier it
    is 1, and the arithmetic below still comes out right.
    """
    probe = object()
    return sys.getrefcount(probe) - 1


def _caller_load_cost(frame: types.FrameType | None) -> int:
    """Did the caller's own load of the argument create a reference?

    This is the part that cannot be a constant. `refcount(items)` where `items` is a local
    compiles to `LOAD_FAST_BORROW` and costs nothing, while the same call in a notebook
    cell compiles to `LOAD_NAME` and costs one, and a beginner comparing the two would
    have no idea why the numbers disagree. So we look at the instruction that actually
    pushed the argument, which is the one immediately before the call being executed.

    Falls back to 1, the pre 3.14 answer, when the caller cannot be inspected. Being off
    by one is better than raising in the middle of a lesson about reference counting.
    """
    if frame is None:
        return 1
    try:
        instructions = _loads_by_offset(frame.f_code)
    except Exception:
        return 1
    pushed = instructions.get(frame.f_lasti)
    if pushed is None:
        return 1
    return 0 if pushed.startswith(_BORROWING_LOADS) else 1


@lru_cache(maxsize=256)
def _loads_by_offset(code: types.CodeType) -> dict[int, str]:
    """Map each instruction offset to the name of the instruction just before it.

    Cached per code object because a lesson calls this in a loop and disassembling the
    caller every time would make the cheap question expensive.
    """
    previous = None
    table = {}
    for item in dis.get_instructions(code, show_caches=False):
        if previous is not None:
            table[item.offset] = previous
        previous = item.opname
    return table


def refcount(obj: object) -> int | None:
    """How many references there are to this object, not counting the one used to ask.

    `sys.getrefcount` is documented as reporting one more than you would expect, because
    passing the object to it creates a reference. As of 3.14 that is only sometimes true.
    Passing a local variable now compiles to `LOAD_FAST_BORROW`, which hands over a
    borrowed reference and adds nothing, while passing a global still compiles to
    `LOAD_GLOBAL`, which adds one. So the correction is not a constant and this works out
    what it should be for the call being made.

    Getting this right is not cosmetic. A lesson that shows a beginner "1 reference" for a
    variable they just bound is teaching the model. One that shows 0 in a test and 2 in a
    notebook for the same object is teaching them to distrust the number.

    Returns None for immortal objects, because a parked count is not a count and printing
    3221225472 next to a paragraph about reference counting teaches the wrong thing.
    """
    if is_immortal(obj):
        return None
    return sys.getrefcount(obj) - _own_call_cost() - _caller_load_cost(sys._getframe(1))


def raw_refcount(obj: object) -> int:
    """`sys.getrefcount` untouched, for the lesson that explains why it needs touching."""
    return sys.getrefcount(obj)


def header(obj: object) -> Header:
    """The object header, as far as it can be seen from Python."""
    immortal = is_immortal(obj)
    count = (
        None
        if immortal
        else sys.getrefcount(obj) - _own_call_cost() - _caller_load_cost(sys._getframe(1))
    )
    return Header(
        address=id(obj),
        type_name=type(obj).__name__,
        refcount=count,
        immortal=immortal,
        size=sys.getsizeof(obj),
        gc_tracked=gc.is_tracked(obj),
        gc_trackable=_is_gc_type(type(obj)),
    )


def _is_gc_type(cls: type) -> bool:
    """Can instances of this type ever participate in a reference cycle?

    An `int` cannot hold a reference to anything, so it can never be part of a cycle, so
    the collector does not carry the extra header for it. This is the first place a
    reader meets the idea that the collector is opt in per type rather than universal.
    """
    try:
        return bool(cls.__flags__ & (1 << 14))  # Py_TPFLAGS_HAVE_GC
    except AttributeError:
        return False


def small_int_range() -> tuple[int, int]:
    """The inclusive range of integers this interpreter shares rather than allocates.

    Probed, never typed. The bound moved from 256 to 1024 in 3.15 and every tutorial that
    hard coded 256 became wrong without its author being told. A number that comes from
    running the interpreter cannot go stale that way.

    The probe builds each integer from its own string so that the compiler cannot fold
    the two occurrences into one constant, which would make everything look shared.
    """

    def fresh(value: int) -> int:
        return int(str(value))

    low = 0
    while fresh(low - 1) is fresh(low - 1) and low > -4096:
        low -= 1
    high = 0
    while fresh(high + 1) is fresh(high + 1) and high < 65536:
        high += 1
    return low, high


def shares_identity(value: int) -> bool:
    """Does this interpreter hand out the same object twice for this integer?"""

    def fresh() -> int:
        return int(str(value))

    return fresh() is fresh()


def is_interned(text: str) -> bool:
    """Is this exact string object the one the interpreter keeps in its intern table?

    Note the wording. The question is not "does an equal string exist in the table", it
    is "is this the object in the table", which is what makes `is` behave the way it does.

    There is no supported API for asking, so this asks indirectly: intern a fresh equal
    copy and see which object comes back. If `text` is in the table you get `text` back.
    The copy matters. Interning `text` itself would put it in the table and every call
    after the first would answer True no matter what the truth was, which is a probe that
    changes the thing it measures.
    """
    copy = "".join([text, ""])
    if copy is text:
        # The empty string is the only one that lands here, because the interpreter keeps
        # a single static copy of it and hands that back rather than building a new one.
        # Failing to make a second equal object is not the probe breaking, it is the
        # answer: there is one of these in the process and it is the one in the table.
        return True
    return sys.intern(copy) is text


def referrers(obj: object) -> list[str]:
    """A readable list of what is currently holding this object.

    Frames and the caller's own scaffolding are filtered out because they are an artifact
    of asking rather than part of the answer, and a beginner cannot tell those apart.
    """
    found = []
    for holder in gc.get_referrers(obj):
        if isinstance(holder, type(sys._getframe())):
            continue
        found.append(f"{type(holder).__name__} at {id(holder):#x}")
    return sorted(found)
