#!/usr/bin/env python
"""R02. Where the state lives.

The second runtime lesson, and the one that puts a frame around everything before it. A running
Python is three nested things: a runtime that there is one of per process, interpreters inside
that, and threads inside those. Every fact this book has taught you belongs to exactly one of the
three levels, and the level decides who can see a change when you make one.

The method is the same in every section. Make a second interpreter, ask both of them the same
question, and watch where the answers stop matching. The small int cache matches. `sys.modules`
does not. Signals turn out to be one table for the whole process with one thread allowed to touch
it, which is a rule you can read straight off two lines of C.

The two Tier 1 recordings put a price on it: an interpreter costs about fifty times what an
operating system thread costs to make, plus a couple of megabytes to keep.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording

lesson = Lesson("r02-where-the-state-lives", "r02")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("r02-where-the-state-lives").figure

WITH_LOCK = "r02-what-a-second-interpreter-costs"
WITHOUT_LOCK = "r02-what-a-second-interpreter-costs-without-the-lock"


lesson.md(f"""
# R02. Where the state lives

{badge}

Every lesson so far has said "the interpreter" as though there were one of them and as though it owned everything. Neither is quite true. A running Python is three nested things: a runtime, one per process, with interpreters inside it, and threads inside those.

Every fact this book has taught you belongs to exactly one of those three levels, and which level it is decides who can see it when you change it. This lesson finds the boundaries by experiment rather than by assertion. Make a second interpreter, ask both of them the same question, and watch for where the answers stop matching.

{figure("three-levels", "nested boxes showing the runtime holding shared objects and signal handlers, two interpreters inside it, and threads inside those")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Include/internal/pycore_runtime.h:14-22@v3.15.0rc1`.

Read it as three parts: the file, the lines, and the release those line numbers belong to. Sometimes there is a fourth part after a `#`, which is the name of the thing those lines are inside.

Every reference is a link, and every one is checked against the pinned source on each change, so a stale reference fails the build instead of sending you somewhere wrong. You never have to read any of it. The references are there so you can go deeper when you want to, and so you can check that this lesson is not making things up.

## Setup

Colab does not come with the small package these lessons use, so the next cell installs it. If you are running this from a checkout of the repository it is already installed and the cell does nothing.
""")


lesson.code("""
import sys

if sys.version_info < (3, 14):
    print("This lesson needs CPython 3.14 or newer.")
    print(f"This runtime is {sys.version.split()[0]}, and the cells below will not run on it.")
else:
    try:
        import pyxray
    except ImportError:
        %pip install -q "pyxray @ git+https://github.com/tamnd/cpython-internals@main#subdirectory=pyxray"
        import pyxray
""")


lesson.md("""
## Which Python is this

Nearly every cell here makes a second interpreter and asks it something. That needs `concurrent.interpreters`, which arrived in 3.14, and it needs a runtime that can actually build one. A browser tab cannot, so each cell checks first and says so rather than failing, and the notebook still reads through on a runtime that cannot run it.

## Which interpreter is this
""")


lesson.code(
    """
import pyxray

pyxray.show()
""",
    differs=BANNER,
    quiet=True,
)


lesson.md(f"""
## What two interpreters share

Start with the simplest question there is. Two interpreters, in the same process, in the same address space. Ask each of them for the address of the same thing and see whether the two addresses match.

A matching address means there is one object and both interpreters are looking at the same bytes. A different address means each of them built its own copy. That single test sorts the whole of Python into two piles, and the sorting is not arbitrary.

{lesson.claim("Two interpreters in one process return the same id for None, for True, for small ints, for one character strings and for the built in type objects, and different ids for the sys module, for sys.modules and for anything either of them built for itself")}
""")


lesson.code("""
import importlib


def load_interpreters():
    \"\"\"Some runtimes cannot make a second interpreter at all. A browser tab is one of them.\"\"\"
    try:
        return importlib.import_module("concurrent.interpreters")
    except ImportError:
        return None


ci = load_interpreters()
NOTHING = "  this runtime cannot make a second interpreter, so there is nothing to look at"

ASK = \"\"\"
import sys

answers = []
for what, thing in [
    ("None", None),
    ("the bool True", True),
    ("the int 5", 5),
    ("the int 100000", 100000),
    ("the one character string a", "a"),
    ("the longer string startup", "startup"),
    ("the type object int", int),
    ("the sys module", sys),
    ("the dict sys.modules", sys.modules),
]:
    answers.append((what, id(thing)))
post.put(tuple(answers))
\"\"\"

if ci is None:
    print(NOTHING)
else:
    post = ci.create_queue()
    worker = ci.create()
    worker.prepare_main(post=post)
    worker.exec(ASK)
    theirs = dict(post.get())
    worker.close()

    here = {}
    exec(ASK.replace("post.put(tuple(answers))", "pass"), here)
    mine = dict(here["answers"])

    for what in mine:
        verdict = "one object, shared" if mine[what] == theirs[what] else "one each"
        print(f"  {what:28} {verdict}")
""")


lesson.md(f"""
{figure("what-two-interpreters-share", "a table of nine objects, whether two interpreters give the same address for each, and who made it")}

The shared ones are not shared by luck. They are fields of a struct. `_Py_static_objects` is part of the runtime, and it holds `None`, `True`, `False`, the small ints, the empty bytes object, the 256 one byte bytes objects, a table of fixed identifier strings and a couple of other odds and ends {cite("Include/internal/pycore_runtime_structs.h:102-126@v3.15.0rc1#_Py_static_objects")}. The one character strings are in there too, as an `ascii` array and a `latin1` array {cite("Include/internal/pycore_global_strings.h:898-924@v3.15.0rc1#latin1")}.

Being a field rather than an allocation is the whole point. Nothing allocated them, so nothing can free them, which makes every one of them an {term("immortal object")} without needing any special handling. And because the runtime is one per process, every interpreter in the process ends up pointing at the same field. That is what a {term("static object")} is.

The type objects come out the same way for the same reason, since a {term("static type")} is a `PyTypeObject` that the compiler laid down in the binary rather than something built at startup.

## Where the sharing stops

The small ints are shared and `100000` is not, so there is a line somewhere. You do not have to look it up. Ask both interpreters for the address of every int in a range and see exactly where they stop agreeing.

{lesson.claim("The ints that two interpreters agree on are a contiguous run starting at minus five, and where that run ends is a compile time constant rather than anything the two interpreters negotiate")}
""")


lesson.code(
    """
LOW, HIGH = -20, 1200

EVERY = \"\"\"
post.put(tuple(id(n) for n in range(low, high)))
\"\"\"

if ci is None:
    print(NOTHING)
else:
    post = ci.create_queue()
    worker = ci.create()
    worker.prepare_main(post=post, low=LOW, high=HIGH)
    worker.exec(EVERY)
    theirs_ids = post.get()
    worker.close()

    mine_ids = tuple(id(n) for n in range(LOW, HIGH))
    both = [n for n, a, b in zip(range(LOW, HIGH), mine_ids, theirs_ids, strict=True) if a == b]
    print(f"  the ints the two of them agree on: {min(both)} up to {max(both)}")
    print(f"  that is {len(both)} objects, built before either interpreter existed")
""",
    differs=(
        "3.14 caches the small ints from minus five up to 256, and 3.15 widened the top of that "
        "range to 1024, so the same cell reports a different edge on the two releases"
    ),
)


lesson.md(f"""
Those two numbers are literally two `#define` lines: `_PY_NSMALLNEGINTS` is 5 and `_PY_NSMALLPOSINTS` is 1025 {cite("Include/internal/pycore_runtime_structs.h:96-99@v3.15.0rc1#_PY_NSMALLPOSINTS")}. The array in the runtime struct is exactly that many entries long, which is why the run is contiguous and why it starts where it does.

If you ran this on 3.14 you got 256 instead of 1024. The array grew between the two releases. It costs a few kilobytes of the binary and it means a great deal more integer arithmetic never allocates anything at all.

Strings work the same way but with a much smaller table. A one character string is in the runtime, so it is shared. `"startup"` is not, even though both interpreters interned it, because interning happens per interpreter into a dict that belongs to that interpreter.

## Three structs, and a pointer chain

Now the shape underneath. There are three structs and they nest.

The runtime is `_PyRuntime`, and it is a plain global variable rather than a pointer to one, so it exists before anything has run {cite("Include/internal/pycore_runtime.h:14-22@v3.15.0rc1#_PyRuntime")}. That is the {term("runtime state")}. Its first field is a table of struct offsets, which is there so that a debugger attached from outside the process can find its way around a Python it did not build {cite("Include/internal/pycore_runtime_structs.h:134-152@v3.15.0rc1#pyruntimestate")}.

Inside it is a small struct holding the interpreters: a linked list, a pointer to the head, a pointer to the main one, and the next id to hand out {cite("Include/internal/pycore_runtime_structs.h:184-201@v3.15.0rc1#pyinterpreters")}. Each entry is a `PyInterpreterState`, which is the {term("interpreter state")} {cite("Include/internal/pycore_interp_structs.h:842-856@v3.15.0rc1#_is")}. Its first field is the evaluation state, and that is deliberate: `eval_breaker` is read on almost every trip round the evaluation loop, so it sits where the offset arithmetic is cheapest.

Inside each interpreter is a list of `PyThreadState`, the {term("thread state")}, one per thread that has ever attached {cite("Include/cpython/pystate.h:66-101@v3.15.0rc1#_ts")}.

Going down is a list walk. Going up is one pointer each way: a thread state has an `interp`, and an interpreter has a `runtime`, and the comment in the header spells the chain out {cite("Include/internal/pycore_interp_structs.h:883-887@v3.15.0rc1#runtime")}.

{figure("the-pointer-chain", "a flow from the thread you are on to PyThreadState to PyInterpreterState to the runtime state, with the field name on each hop")}

From Python you can see the middle level directly. Interpreters have ids, the main one is always zero, and the ids only ever count upwards.

{lesson.claim("The main interpreter is always id 0, new interpreters get the next number that has never been used, and closing one does not put its number back in the pool")}
""")


lesson.code(
    """
if ci is None:
    print(NOTHING)
else:
    print(f"  {'interpreters right now':26} {len(ci.list_all())}")
    made = [ci.create() for _ in range(3)]
    for one in ci.list_all():
        whose = "the main interpreter" if one.id == 0 else "made by this cell"
        label = f"id {one.id}"
        print(f"  {label:26} {whose}")
    for one in made:
        one.close()
    print(f"  {'after closing those three':26} {len(ci.list_all())}")
""",
    varies=(
        "the ids count upwards from the interpreters the earlier cells made and closed, so running "
        "this notebook twice in one kernel gives higher numbers the second time"
    ),
)


lesson.md(f"""
## Everything else belongs to one interpreter

The shared pile turned out to be small: some numbers, some short strings, the type objects. Almost everything else you think of as belonging to Python belongs to one interpreter rather than to the process.

The header is a good read here. An interpreter owns its own `sysdict`, its own `builtins`, its own import state and its own lock {cite("Include/internal/pycore_interp_structs.h:910-921@v3.15.0rc1#sysdict")}. A little further down it owns the warnings state, the `atexit` callbacks, its own stop the world state and its own quiescent state tracking {cite("Include/internal/pycore_interp_structs.h:956-962@v3.15.0rc1#warnings")}.

That the import lock is per interpreter rather than per process is what makes a {term("subinterpreter")} worth having at all. Two of them can import at the same time.

The next cell changes three of these on this side and then asks the other interpreter what it thinks. Nothing crosses.

{lesson.claim("Setting the recursion limit, adding a warnings filter and importing a module all change one interpreter and are invisible to another interpreter in the same process")}
""")


lesson.code(
    """
import warnings

LEVELS = \"\"\"
import sys
import warnings

post.put((sys.getrecursionlimit(), len(warnings.filters), len(sys.modules), sys.flags.optimize))
\"\"\"

if ci is None:
    print(NOTHING)
else:
    post = ci.create_queue()
    worker = ci.create()
    worker.prepare_main(post=post)

    was = sys.getrecursionlimit()
    with warnings.catch_warnings():
        warnings.filterwarnings("error", message="only in this interpreter")
        sys.setrecursionlimit(1234)
        worker.exec(LEVELS)
        limit, filters, modules, optimize = post.get()
        rows = [
            ("the recursion limit", sys.getrecursionlimit(), limit),
            ("how many warnings filters", len(warnings.filters), filters),
            ("how many modules imported", len(sys.modules), modules),
            ("sys.flags.optimize", sys.flags.optimize, optimize),
        ]
    sys.setrecursionlimit(was)
    worker.close()

    for what, ours, thing in rows:
        print(f"  {what:26} here {ours:<6} there {thing}")
""",
    varies=(
        "the module count on this side is whatever your notebook has imported, which is hundreds, "
        "and the filter count depends on what your environment set up before you got here"
    ),
)


lesson.md(f"""
The last row is the one that does cross, and it is worth understanding why. `sys.flags` comes from the configuration the process was started with, and a new interpreter inherits that configuration rather than being asked again. It is not shared state, it is the same answer arrived at twice.

The module count is the striking one. A brand new interpreter starts with dozens of modules of its own, none of which the parent lent it. That is most of what an interpreter costs, and the last section puts a number on it.

{figure("where-each-fact-lives", "a table matching eight facts from earlier lessons to the level that owns them and the test that shows it")}

## Some state really is one per process

Signals are the exception that proves the rule, and they are the cleanest example in the whole lesson.

The operating system delivers a signal to a process, not to an interpreter, because the operating system has never heard of interpreters. So the table of handlers has to be one per process, and it is: a fixed array of `Py_NSIG` entries hanging off the runtime {cite("Include/internal/pycore_signal.h:39-70@v3.15.0rc1#_signals_runtime_state")}.

One table means one writer. The test for who is allowed to write is two conditions, one for each of the two upper levels {cite("Include/internal/pycore_pystate.h:80-88@v3.15.0rc1#_Py_ThreadCanHandleSignals")}, and `signal.signal` calls it before it does anything else {cite("Modules/signalmodule.c:497-503@v3.15.0rc1#_Py_ThreadCanHandleSignals")}. If you have ever seen the error message, you have read the C without knowing it: it says main thread of the main interpreter, and those are exactly the two conditions.

{lesson.claim("signal.signal only works on the main thread of the main interpreter, and it raises ValueError both on another thread of the main interpreter and on the main thread of a second interpreter")}
""")


lesson.code("""
import signal
import threading

WHICH = getattr(signal, "SIGUSR1", signal.SIGINT)

TRY = \"\"\"
import signal

try:
    signal.signal(getattr(signal, "SIGUSR1", signal.SIGINT), signal.SIG_IGN)
except ValueError as problem:
    post.put(str(problem))
else:
    post.put("it worked")
\"\"\"


def install_a_handler():
    \"\"\"Try to take over a signal, then put back whatever was there before.\"\"\"
    try:
        before = signal.signal(WHICH, signal.SIG_IGN)
    except ValueError as problem:
        return str(problem)
    signal.signal(WHICH, before)
    return "it worked"


if ci is None:
    print(NOTHING)
else:
    said = []
    print(f"  main thread, main interpreter: {install_a_handler()}")

    helper = threading.Thread(target=lambda: said.append(install_a_handler()))
    try:
        helper.start()
        helper.join()
    except RuntimeError:
        said.append("this runtime cannot start a thread")
    print(f"  another thread, same one:      {said[0]}")

    post = ci.create_queue()
    worker = ci.create()
    worker.prepare_main(post=post)
    worker.exec(TRY)
    print(f"  main thread, second one:       {post.get()}")
    worker.close()
""")


lesson.md(f"""
{figure("who-may-handle-a-signal", "two columns, one listing the single place signal dot signal succeeds and one listing the three places it raises")}

This is also why a second interpreter cannot be interrupted with control C in any direct way. The handler runs on the main thread of the main interpreter, and getting the news across to anybody else is a separate mechanism.

## And some belongs to one thread

The bottom level is the smallest and the easiest to forget. The exception currently being handled is per thread, and so is the stack of frames, and so is the recursion budget.

`sys.exception()` reads it. Two threads can each be inside an `except` block at the same moment, holding different exceptions, and neither can see the other's.

{lesson.claim("Two threads can each be handling a different exception at the same time, and sys.exception() gives each of them its own answer while the main thread sees None")}
""")


lesson.code("""
def hold(name, box, gate):
    \"\"\"Raise something, catch it, and while still inside the except block, look at it.\"\"\"
    try:
        raise ValueError(name)
    except ValueError:
        gate.wait()
        box[name] = repr(sys.exception())


box = {}
gate = threading.Barrier(3)
helpers = [threading.Thread(target=hold, args=(name, box, gate)) for name in ("one", "two")]

try:
    for one in helpers:
        one.start()
    gate.wait()
    for one in helpers:
        one.join()
except RuntimeError:
    print("  this runtime cannot start a thread, so there is nothing to look at")
else:
    for name in sorted(box):
        print(f"  thread {name} is handling {box[name]}")
    print(f"  the main thread is handling {sys.exception()!r}")
""")


lesson.md(f"""
Both threads were inside an `except` block at the same instant, which is what the barrier is for, and each one got its own answer. There is no process wide idea of the current exception, and there could not be.

## One function that reads the whole runtime

Almost everything in the C API works on the current thread or the current interpreter. A few functions deliberately do not, and `sys._current_frames` is the clearest one: it walks the runtime's list of interpreters and, for every interpreter, every thread state on it {cite("Python/pystate.c:2692-2731@v3.15.0rc1#_PyThread_CurrentFrames")}. It is a debugging tool, and a debugger that could only see its own interpreter would not be much of a debugger.

No cell in this lesson calls it from inside a second interpreter, and the reason is worth saying out loud rather than quietly avoiding. On a build with the GIL, doing that crashes the process outright. The function builds frame objects for frames belonging to other interpreters, and on such a build each interpreter allocates from its own pools, so an object made against one pool gets freed against another. It is not an exception you can catch, it is an abort. That is issue #179 in this repository, found while writing this lesson.

The general shape of the mistake is worth more than the specific bug. When you read the runtime instead of your own interpreter, you are reading memory that somebody else owns, and every rule this lesson has laid out is about who owns what.
""")


lesson.md(f"""
## What an interpreter costs

Two recordings, the same program, run in two containers built from the same source. One is an ordinary release build with the GIL. The other was configured with `--disable-gil`, which matters here because the two builds do not allocate the same way: one gives each interpreter its own obmalloc pools, the other uses mimalloc heaps.

{recording(WITH_LOCK)}

{recording(WITHOUT_LOCK)}

{figure("what-an-interpreter-costs", "bars of microseconds to make one, comparing an operating system thread against a whole interpreter on a build with the lock and a build without")}

An operating system thread takes a few hundred microseconds. An interpreter takes about fifty times that, and it keeps a couple of megabytes of resident memory for as long as you hold it. The free threaded build charges more for both, and the reason is the allocator rather than noise.

Fifty times sounds like a verdict against interpreters, and it is not. It is a verdict against making them in a loop. An interpreter is something you make a few of at startup and keep, in the way you would a process, and C08 measured what you get back for that. If you find yourself creating one per unit of work, you have picked the wrong tool, and a thread or a task is the right one.

The other number in those recordings is the module count. A new interpreter starts with 55 modules on that build and imports every one of them itself. That is not a tax you can avoid, it is the thing you asked for: its own `sys.modules` is exactly why it does not have to wait for yours.

{lesson.claim("Making an interpreter costs roughly fifty times what making an operating system thread costs, and a build without the GIL charges more for both because mimalloc heaps and obmalloc pools do not price an extra interpreter the same way", unobservable="it compares two builds of the same source in two containers, and one interpreter cannot be both of them")}
""")


lesson.md("""
## Try it yourself

Four things, in rough order of how much you will learn.

Take the id cell and add rows of your own. Try `()`, the empty tuple. Try `int` against `type(5)`. Try a class you define in the cell. Then try `sys.intern("something unusual")` on both sides and work out why interning does not help.

Run the range cell on 3.14 and on 3.15 if you have both, and watch the edge move from 256 to 1024. That is one constant in one header, and it is the difference between a great deal of arithmetic allocating and not allocating.

In the per interpreter cell, add `("the id of sys.stdout", id(sys.stdout), ...)` and think about what you expect before you run it. Then try importing a module in the child and asking the parent whether it can see it.

Put `import signal; signal.signal(signal.SIGUSR1, signal.SIG_IGN)` at the top of a script and run it under `python -X importtime`. Then move the same two lines into a thread and watch the error message tell you the exact two conditions from the C.

## What you now know

There are three levels. One runtime per process, interpreters inside it, threads inside those. Every piece of state lives at exactly one of them.

The runtime holds a small, fixed set of objects that every interpreter shares: `None`, the booleans, the small ints, the one character strings, the fixed identifier strings, and the static type objects. They are fields of a struct rather than allocations, which is why they are immortal and why their addresses match everywhere.

Where the small int cache ends is a `#define`, not a policy. It moved from 256 to 1024 in 3.15.

An interpreter owns its own `sys.modules`, its own builtins, its own import lock, its own warnings filters, its own recursion limit and its own `atexit` list. Changing any of them is invisible to every other interpreter in the process.

A thread owns the exception it is handling and the frames it is running. There is no process wide answer to what the current exception is.

Signals are the exception. One table per process, and the only writer allowed is the main thread of the main interpreter, which is two conditions in one line of C.

An interpreter is not a heavier thread. It costs about fifty times as much to create and a couple of megabytes to keep, so you make a few and hold them.

## What is next

This lesson said a new interpreter imports dozens of modules of its own and left it there. R03 opens that up. The import system is the largest piece of Python written in Python, it has a documented protocol that you can extend, and it is running long before you ever type `import`.

Start with what happens between `import x` and the module object appearing in `sys.modules`, which turns out to be four separate steps with a hook on each one.
""")


raise SystemExit(lesson.save())
