"""Watching objects die, and finding the ones that will not.

Reference counting is the part of CPython's memory management you can observe directly from
Python, and the cycle collector is the part you normally cannot. This module is the small
amount of scaffolding a lesson needs to see both: a way to notice the exact moment an object
is freed without keeping it alive, a way to find the reference cycles in a graph you built,
and a way to ask which collector generation is holding something.

Nothing here needs a debug build or `ctypes`, which is the same rule the rest of `pyxray`
follows. The cycle finder is a reimplementation rather than a lookup, so it can be wrong,
and the tests check it against object graphs whose answers are known by construction.
"""

from __future__ import annotations

import gc
import sys
import types
import weakref
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

#: The walk refuses to step into these, because every one of them is a door onto the rest of
#: the process. Follow a class and you reach its module, follow a module and you reach every
#: name it imported, and a question about three objects you just made turns into a walk over
#: the whole heap. CPython's own collector has the same problem and solves it the same way,
#: by only ever considering a candidate set rather than everything that exists.
_BOUNDARIES = (
    type,
    types.ModuleType,
    types.FunctionType,
    types.BuiltinFunctionType,
    types.FrameType,
    types.MethodType,
)

#: How many objects the walk will visit before deciding it has escaped. A reader who points
#: this at something with a route out into the interpreter should get a clear error rather
#: than a notebook that appears to have hung.
_LIMIT = 10_000


def label(value: object) -> str:
    """A short readable name for an object, for output that has to fit on one line."""
    return f"{type(value).__name__} at {id(value):#x}"


@dataclass(frozen=True)
class Cycle:
    """One reference cycle, as the names of the objects on it."""

    members: tuple[str, ...]

    def describe(self) -> str:
        """The cycle written out as a loop, ending where it started."""
        return " -> ".join((*self.members, self.members[0]))


def reachable(*roots: object, limit: int = _LIMIT) -> dict[int, object]:
    """Every object reachable from these roots, keyed by identity.

    The walk uses `gc.get_referents`, which is `tp_traverse` exposed to Python, so it sees
    exactly what the collector sees rather than what `__dict__` happens to contain. Objects
    the collector does not track are skipped, since an int cannot hold a reference and so
    cannot be part of a cycle or a path to one.
    """
    seen: dict[int, object] = {}
    pending = list(roots)
    while pending:
        item = pending.pop()
        if id(item) in seen:
            continue
        seen[id(item)] = item
        if len(seen) > limit:
            raise ValueError(
                f"the walk reached more than {limit} objects, which means it found a route "
                "out into the interpreter rather than staying inside the graph you built"
            )
        for referent in gc.get_referents(item):
            if not gc.is_tracked(referent) or isinstance(referent, _BOUNDARIES):
                continue
            pending.append(referent)
    return seen


def cycles(*roots: object, limit: int = _LIMIT) -> list[Cycle]:
    """Every reference cycle in the graph hanging off these objects.

    A cycle is a group of objects that can all reach each other, which is a strongly
    connected component of the reference graph, plus the single objects that refer to
    themselves. Those are the two shapes reference counting cannot free on its own, because
    every object on one is being held by another object on the same one.

    The result is names rather than objects on purpose. Handing back the objects would give
    the caller a fresh reference to each of them, and in a lesson about things staying alive
    longer than they should, a tool that keeps them alive is not much use.
    """
    seen = reachable(*roots, limit=limit)
    edges = {
        key: [id(item) for item in gc.get_referents(value) if id(item) in seen]
        for key, value in seen.items()
    }
    found = []
    for group in _components(edges):
        if len(group) > 1 or group[0] in edges[group[0]]:
            found.append(Cycle(tuple(label(seen[key]) for key in group)))
    return sorted(found, key=lambda cycle: cycle.members)


def _components(edges: dict[int, Sequence[int]]) -> list[list[int]]:
    """Tarjan's strongly connected components, written out rather than recursive.

    Recursion would be the shorter version and would also blow the stack on a graph of a few
    thousand objects, which is well within what a reader might point this at.
    """
    index: dict[int, int] = {}
    low: dict[int, int] = {}
    on_stack: set[int] = set()
    stack: list[int] = []
    result: list[list[int]] = []
    counter = 0

    for root in edges:
        if root in index:
            continue
        work: list[tuple[int, int]] = [(root, 0)]
        while work:
            node, step = work.pop()
            if step == 0:
                index[node] = low[node] = counter
                counter += 1
                stack.append(node)
                on_stack.add(node)
            recursed = False
            for position in range(step, len(edges[node])):
                child = edges[node][position]
                if child not in index:
                    work.append((node, position + 1))
                    work.append((child, 0))
                    recursed = True
                    break
                if child in on_stack:
                    low[node] = min(low[node], index[child])
            if recursed:
                continue
            if low[node] == index[node]:
                group = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    group.append(member)
                    if member == node:
                        break
                result.append(group)
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])
    return result


class Deaths:
    """Notices the exact moment watched objects are freed, without keeping them alive.

    A weak reference is a reference that does not count. It lets you hold onto something and
    still find out when everything that does count has let go of it, which is the only way to
    observe a free from Python: by the time an ordinary name could tell you, the name itself
    is one of the reasons the object is still here.

    Types that cannot be weakly referenced, which includes `int`, `str`, `tuple` and a class
    using `__slots__` without `__weakref__`, are refused with an explanation rather than a
    `TypeError` from the middle of the standard library.
    """

    def __init__(self) -> None:
        self._refs: dict[str, weakref.ref] = {}
        self._order: list[str] = []

    def watch(self, name: str, value: object) -> object:
        """Start watching an object, and hand it straight back so this fits in one line."""
        try:
            self._refs[name] = weakref.ref(value, self._died(name))
        except TypeError:
            raise TypeError(
                f"{type(value).__name__} objects cannot be weakly referenced, so there is no "
                "way to watch one without holding it. Try a class of your own instead."
            ) from None
        return value

    def _died(self, name: str):
        order = self._order

        def note(_ref: weakref.ref) -> None:
            order.append(name)

        return note

    def alive(self, name: str) -> bool:
        """Is the object behind this name still here?"""
        return self._refs[name]() is not None

    @property
    def gone(self) -> list[str]:
        """The names that have been freed, in the order they were freed."""
        return list(self._order)

    def report(self) -> str:
        """One line per watched name, in the order they were added."""
        return "\n".join(
            f"{name:<16} {'alive' if self.alive(name) else 'freed'}" for name in self._refs
        )


def generation_of(value: object) -> int | None:
    """Which collector generation is holding this object, or None if it is not tracked.

    Every tracked object starts in generation 0 and moves up one each time it survives a
    collection of the generation it is in. That is the weak generational hypothesis made
    concrete: most objects die young, so the collector looks at the young ones often and the
    old ones rarely.

    This walks `gc.get_objects` for each generation, which is not cheap and is fine for a
    lesson asking about one object. There is no direct question to ask.
    """
    if not gc.is_tracked(value):
        return None
    for generation in range(len(gc.get_stats())):
        objects = gc.get_objects(generation=generation)
        found = any(item is value for item in objects)
        del objects
        if found:
            return generation
    return None


def allocated() -> int | None:
    """How many blocks the object allocator is currently handing out, if it can be asked.

    `sys.getallocatedblocks` counts blocks rather than bytes and only exists on builds using
    CPython's own small object allocator. A build configured `--without-pymalloc`, and some
    alternative runtimes, will not have it, so this returns None rather than raising.
    """
    counter = getattr(sys, "getallocatedblocks", None)
    return None if counter is None else counter()


def sizes(values: Iterable[object]) -> list[tuple[str, int]]:
    """Each object's own size in bytes, as rows ready for a table or a chart.

    `sys.getsizeof` reports what the object itself takes and nothing it points at, so a list
    of a thousand large integers is eight thousand bytes here and a great deal more in
    reality. That is the whole trap and it is worth putting the two numbers side by side.
    """
    return [(label(value), sys.getsizeof(value)) for value in values]
