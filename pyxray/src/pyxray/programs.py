"""The three programs this project uses for everything.

Every lesson from here on picks one of `L0`, `L1` and `L2` rather than inventing a fresh
example. That sounds like a small housekeeping decision and it is not. A reader who meets a
new program and a new subsystem in the same lesson is doing two jobs, and the one they drop
is the subsystem. By the time the exception table turns up in part four, the intent is that
they already know what `L2` does well enough to spend all of their attention on the table.

The three are deliberately spread out rather than being three sizes of the same thing.

`L0` is one line with no function in it, so its bytecode, its tree and its symbol table all
fit on a screen at once. It is the program for showing a stage of the pipeline for the first
time, because nothing in it competes with the stage for attention.

`L1` is an iterative Fibonacci. It is the smallest program with a loop that runs long enough
for the interpreter to notice, which makes it the one to use whenever the subject is the
interpreter itself: the value stack rising and falling, an instruction specializing after a
few laps, a trace getting hot enough for the JIT to look at it.

`L2` is a small linked structure with a class, a generator, a closure, a dict, a
`try`/`except`/`finally` and, if you ask for it, a reference cycle. Every one of those is
there because a later lesson needs to point at it, and nothing is in it twice. It is the
program for the object model, for frames, for exceptions and for the garbage collector.

Nothing here executes on import. A program is source text until somebody asks for it, which
matters because `L2` can be made to build a cycle and a module that quietly left one lying
around would show up in somebody else's lesson about garbage.
"""

from __future__ import annotations

import types
from dataclasses import dataclass, field

__all__ = ["ALL", "L0", "L1", "L2", "Program", "get", "summary"]


L0_SOURCE = """\
answer = 6 * 7
"""


L1_SOURCE = '''\
def fib(n):
    """The nth Fibonacci number, counted forwards rather than worked out recursively."""
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
'''


L2_SOURCE = '''\
class Node:
    """A name and a pointer to another node, which is the least you need to make a ring."""

    def __init__(self, name):
        self.name = name
        self.next = None

    def __repr__(self):
        return f"Node({self.name!r})"


def chain(names, *, ring=False):
    """Link one node to the next, front to back. With `ring`, the last points at the first."""
    nodes = [Node(name) for name in names]
    for node, following in zip(nodes, nodes[1:]):
        node.next = following
    if ring:
        nodes[-1].next = nodes[0]
    return nodes[0]


def forward(start):
    """Hand back one node at a time, going forward, until there is no next one."""
    node = start
    while node is not None:
        yield node
        node = node.next


def labeller(prefix):
    """Number the nodes as they go past. The count lives in a cell, not in a global."""
    count = 0

    def label(node):
        nonlocal count
        count += 1
        return f"{prefix}{count}:{node.name}"

    return label


def index(start, limit):
    """Walk at most `limit` nodes into a dict, and shut the walk down either way."""
    found = {}
    label = labeller("n")
    walker = forward(start)
    try:
        for _ in range(limit):
            node = next(walker)
            found[label(node)] = node
    except StopIteration:
        pass
    finally:
        walker.close()
    return found


def main():
    """Three nodes in a line, walked with room to spare, so the walk runs out first."""
    return tuple(index(chain(("a", "b", "c")), 10))
'''


@dataclass(frozen=True)
class Program:
    """One of the three, as source text plus the few facts a lesson wants alongside it."""

    #: `L0`, `L1` or `L2`. Short on purpose, because it is going to appear in a lot of prose.
    name: str

    #: What to call it in a sentence, so a lesson does not have to say "L1" out loud.
    title: str

    #: The program itself, ending in a newline, ready to hand to `compile`.
    source: str

    #: The name to ask the finished program for. If it turns out to be a function, `run`
    #: calls it with `args`, and if it is an ordinary value `run` hands that back instead.
    #: `L0` has no function in it at all, which is the whole reason this is a name and not
    #: an entry point.
    entry: str

    #: What `run` produces. Pinned by a test, so that editing one of these three programs
    #: is a thing somebody has to do on purpose rather than something that happens.
    answer: object

    #: Why the program is shaped the way it is, one line per feature it is carrying. The
    #: order is the order the features appear in the source.
    exercises: tuple[str, ...]

    args: tuple[object, ...] = field(default_factory=tuple)

    @property
    def filename(self) -> str:
        """What the code objects say they came from, so a traceback names the program."""
        return f"<{self.name}>"

    @property
    def lines(self) -> int:
        """How many lines it is. The point of these three is that they stay small."""
        return len(self.source.rstrip("\n").split("\n"))

    @property
    def size(self) -> str:
        """The line count as a phrase, since one of the three really is one line long."""
        return "1 line" if self.lines == 1 else f"{self.lines} lines"

    def code(self) -> types.CodeType:
        """The module level code object, which is what the compiler lessons disassemble."""
        return compile(self.source, self.filename, "exec")

    def load(self) -> types.SimpleNamespace:
        """Run the source and hand back what it defined, as attributes rather than a dict.

        Each call gets a fresh namespace. Nothing is cached, because two lessons sharing
        one set of objects would mean one of them measuring reference counts the other put
        there.
        """
        namespace: dict[str, object] = {}
        exec(self.code(), namespace)
        namespace.pop("__builtins__", None)
        return types.SimpleNamespace(**namespace)

    def target(self) -> object:
        """Whatever `entry` names, out of a fresh namespace."""
        return getattr(self.load(), self.entry)

    def run(self) -> object:
        """Run it and give back the answer, which should be `answer` every time."""
        target = self.target()
        return target(*self.args) if callable(target) else target

    def describe(self) -> str:
        """A short paragraph and the source, which is what a notebook cell prints."""
        head = f"{self.name}, {self.title}. {self.size}, and it gives back {self.answer!r}."
        carries = "\n".join(f"  - {item}" for item in self.exercises)
        return f"{head}\n\nIt is carrying:\n{carries}\n\n{self.source}"


L0 = Program(
    name="L0",
    title="one line",
    source=L0_SOURCE,
    entry="answer",
    answer=42,
    exercises=(
        "two constants and an operator, which the compiler works out before you run it",
        "a name bound at module level, which is neither a local nor quite a global",
        "no function, no frame beyond the module's own, and nothing to step into",
    ),
)


L1 = Program(
    name="L1",
    title="the loop",
    source=L1_SOURCE,
    entry="fib",
    args=(30,),
    answer=832040,
    exercises=(
        "a function with a parameter, so there is a frame with something in it",
        "two locals rebound together, which is a tuple the compiler takes apart again",
        "a call to a builtin, `range`, which is a different kind of call to a Python one",
        "a loop with a backward jump, which one call is enough to get specialized",
        "integer addition, the arithmetic that has a fast path and a slow one",
    ),
)


L2 = Program(
    name="L2",
    title="the linked structure",
    source=L2_SOURCE,
    entry="main",
    answer=("n1:a", "n2:b", "n3:c"),
    exercises=(
        "a class, and instances that keep their attributes in a dict of their own",
        "a list comprehension, which is inlined into its enclosing function these days",
        "an optional ring, so the same code can build a reference cycle when asked",
        "a generator, which is a frame that outlives the call that made it",
        "a closure over a counter, so there is a cell to look at",
        "a dict being filled a key at a time",
        "a `try`, an `except` and a `finally`, which become a table of ranges, not instructions",
    ),
)


#: The three, in the order a reader meets them.
ALL: tuple[Program, ...] = (L0, L1, L2)


def get(name: str) -> Program:
    """Look one up by name, case insensitively, because `l1` and `L1` are the same program."""
    wanted = name.strip().upper()
    for program in ALL:
        if program.name == wanted:
            return program
    options = ", ".join(candidate.name for candidate in ALL)
    raise KeyError(f"no program called {name!r}. There are three: {options}")


def summary() -> str:
    """One line each, which is enough for a lesson to remind a reader which is which."""
    rows = [
        f"{program.name}  {program.title:<20} {program.size:>8}  gives back {program.answer!r}"
        for program in ALL
    ]
    return "\n".join(rows)
