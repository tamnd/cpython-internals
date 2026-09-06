#!/usr/bin/env python
"""R08. When the interpreter stops.

The last of the lessons about the runtime as a thing with a lifetime. R01 asked what has already
happened before your first line. This one asks what is still to come after your last one: the
threads that get joined, the atexit callbacks that come back in reverse, the finalizers that run
in a world with an empty `sys.modules`, and the two ways to end a process that quietly skip work
you asked for.

Every cell starts a child interpreter, because a notebook cannot watch its own shutdown.

The two Tier 1 recordings are a release build and a debug build running the same nine endings.
The debug one adds the part that cannot be argued with: one daemon thread running a function
from your own module leaves 12680 references alive at the end, and none of your finalizers run.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording

lesson = Lesson("r08-when-the-interpreter-stops", "r08")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("r08-when-the-interpreter-stops").figure

ON_RELEASE = "r08-what-the-end-still-runs"
ON_DEBUG = "r08-what-the-end-leaves-behind"


lesson.md(f"""
# R08. When the interpreter stops

{badge}

Your program reaches its last line. Nothing else of yours is going to run, and the process has not exited yet. What happens in between is a fixed sequence in one C function, and it is the part of the runtime that makes the fewest promises.

Most of the time you never notice. You notice when a log file comes out empty, when a temporary directory is still there in the morning, or when something you registered simply did not happen. All three of those are the same fact seen from different sides: the end of a program is not a normal place to be running Python, and the further into it you get, the less of Python is left.

{figure("the-order-of-the-end", "a pipeline from your last line through joining threads and running atexit callbacks to tearing down modules and objects")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/pylifecycle.c:2380-2419@v3.15.0rc1`.

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

Every cell below starts a fresh child interpreter and lets it die, because a notebook cannot watch its own shutdown. By the time this kernel starts finalising there is nobody left to print the answer.

Some runtimes cannot start a process at all. A browser tab is the usual example. Each cell checks first and says so rather than failing, so the notebook still reads through on a runtime that cannot run it.

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
## The order of the end

{term("interpreter finalisation")} is one function, {cite("Python/pylifecycle.c:2380-2419@v3.15.0rc1#_Py_Finalize")}, and reading it top to bottom is the fastest way to understand shutdown. The first thing it does is the part you can still take part in: {cite("Python/pylifecycle.c:2272-2311@v3.15.0rc1#make_pre_finalization_calls")} waits for your threads, then runs your atexit callbacks. Everything after that is teardown.

The wait is not the operating system joining threads. It is a call into Python: {cite("Python/pylifecycle.c:3843-3862@v3.15.0rc1#wait_for_thread_shutdown")} calls `threading._shutdown`, which joins every non daemon thread you started. So your threads run to completion first, and only then does anything else on this list happen.

{lesson.claim("Your threads finish first, then your atexit callbacks, then the finalizers on your module globals.")}
""")


lesson.code("""
import os
import subprocess

PLAIN = os.environ | {"PYTHON_COLORS": "0"}

ORDER = \"\"\"
import atexit, sys, threading, time


def note(label):
    print(f"  {label:38} is_finalizing={sys.is_finalizing()}")


class Late:
    def __del__(self):
        note("a finalizer on a module global")


def worker():
    time.sleep(0.2)
    note("a thread you started, finishing")


atexit.register(note, "an atexit callback, registered first")
atexit.register(note, "an atexit callback, registered second")
keeper = Late()
threading.Thread(target=worker).start()
note("your last line")
\"\"\"


def child(code, flags=()):
    \"\"\"Start a fresh interpreter, run that program, and hand back everything it did.\"\"\"
    return subprocess.run(
        [sys.executable, *flags, "-c", code],
        capture_output=True,
        text=True,
        timeout=120,
        env=PLAIN,
    )


def children_work():
    \"\"\"Some runtimes cannot start a process at all. A browser tab is one of them.\"\"\"
    try:
        child("pass")
    except Exception:
        return False
    return True


CHILDREN = children_work()
NO_CHILDREN = "  this runtime cannot start another interpreter, so there is nothing to watch"

print(NO_CHILDREN if not CHILDREN else child(ORDER).stdout, end="")
""")


lesson.md(f"""
That last column is the {term("finalizing flag")}, which you can read as `sys.is_finalizing()`. It is `False` while your callbacks run and `True` by the time the finalizer does, because the flag is set after the pre finalization calls are over. That makes it the honest test for whether the usual rules still apply.

## The callbacks come back in reverse

An {term("atexit callback")} is the last hook you get while Python is still fully working. There is one detail worth knowing and one worth being careful about.

The detail: `register` does not append. It does `PyList_Insert(callbacks, 0, ...)`, {cite("Modules/atexitmodule.c:202-213@v3.15.0rc1#PyList_Insert")}, so the list is walked in the reverse of the order you built it. That is deliberate, and it is the right default. If you opened a file and then a writer on top of it, you want the writer closed first.

The care: {cite("Modules/atexitmodule.c:102-141@v3.15.0rc1#atexit_callfuncs")} copies the list before it walks it, and empties the original afterwards. Anything registered from inside a callback goes on a list nobody reads again.

{figure("atexit-is-a-stack", "three atexit register calls stacked with the last one registered drawn on top")}

{lesson.claim("Callbacks run newest first, and one registered during shutdown never runs at all.")}
""")


lesson.code("""
ATEXIT = \"\"\"
import atexit


def note(label):
    print(f"  {label}")


def registers_another():
    note("the middle callback, which registers another one from inside itself")
    atexit.register(note, "the callback registered during shutdown")


atexit.register(note, "the first callback registered")
atexit.register(registers_another)
atexit.register(note, "the last callback registered")
print(f"  {atexit._ncallbacks()} callbacks are registered and the program is over")
\"\"\"

print(NO_CHILDREN if not CHILDREN else child(ATEXIT).stdout, end="")
""")


lesson.md(f"""
## What a finalizer can still reach

After the callbacks, the interpreter starts taking things apart. Modules are torn down, and then the module dict itself is emptied: {cite("Python/pylifecycle.c:1931-1948@v3.15.0rc1#finalize_clear_modules_dict")}. Before that there is a smaller pass that removes the entries most likely to be holding something alive, including `sys.path` and `sys.meta_path`: {cite("Python/pylifecycle.c:1683-1702@v3.15.0rc1#finalize_modules_delete_special")}.

Emptying `sys.meta_path` is what turns the import system off. There is no flag for it. The import machinery finds the list missing and raises: {cite("Lib/importlib/_bootstrap.py:1196-1210@v3.15.0rc1#meta_path")}.

So a `__del__` that runs this late is in an odd position. Your own module's globals are fine, because they are exactly what is being freed. Everything reached through the import system is gone, including modules you imported at the top of the file.

{lesson.claim("A finalizer running during shutdown can read your module globals but cannot import anything, not even a module already imported.")}
""")


lesson.code(
    """
LATE = \"\"\"
import json, sys

MESSAGE = "still readable, it is what is being taken apart"


class Late:
    def __del__(self):
        print("  sys.is_finalizing()   ", sys.is_finalizing())
        print("  a module global       ", MESSAGE)
        print("  len(sys.modules)      ", len(sys.modules))
        try:
            import json
            print("  import json           ", "worked")
        except ImportError as unhappy:
            print("  import json           ", unhappy)


keeper = Late()
print("  before shutdown, len(sys.modules) is", len(sys.modules), "and json is imported")
\"\"\"

print(NO_CHILDREN if not CHILDREN else child(LATE).stdout, end="")
""",
    varies=(
        "The count before shutdown depends on how the child was started as much as on the "
        "version. A plain 3.14 gets 58 where a plain 3.15 gets 61, and a notebook kernel passes "
        "on enough environment to move it again. What the finalizer sees is the same everywhere."
    ),
)


lesson.md(f"""
{figure("what-a-late-finalizer-can-reach", "a table of five things a finalizer might try during shutdown and what each one gives back")}

This is the shape of a whole class of bug. A `__del__` or a `weakref` callback that imports something, or calls a function that imports something, works in every test you write and fails only on the way out, where the failure is printed and thrown away.

## When something raises on the way out

Which raises the next question: what does happen to an exception at this point? There is no code left to catch it and no sensible way to report it, so both paths take the same way out. `atexit` uses `PyErr_FormatUnraisable` and carries on with the next callback. A failing `__del__` is reported the same way.

The part that catches people is the exit status.

{lesson.claim("An exception in an atexit callback or a finalizer is printed and ignored, and the process still exits with status zero.")}
""")


lesson.code("""
import re

ERRORS = \"\"\"
import atexit


class Breaks:
    def __del__(self):
        raise RuntimeError("this finalizer raised")


def unhappy():
    raise ValueError("this atexit callback raised")


atexit.register(unhappy)
keeper = Breaks()
print("  two things are set up to fail on the way out")
\"\"\"

if not CHILDREN:
    print(NO_CHILDREN)
else:
    done = child(ERRORS)
    print(done.stdout, end="")
    print("  exit status:", done.returncode)
    for line in done.stderr.splitlines():
        if line and not line.startswith((" ", "Traceback")):
            print("  " + re.sub(r" at 0x[0-9a-f]+", "", line))
""")


lesson.md(f"""
Both failures were printed and neither changed the answer the shell gets. If your cleanup runs at exit and you rely on the status code to tell you it worked, it will not.

## The thread that stops your finalizers

Now the case that is genuinely surprising. A daemon thread is one the interpreter does not wait for, so the usual advice is that it just stops wherever it is. That is true, but it is not the whole story.

`threading._shutdown` returns without waiting, the atexit callbacks run, and then teardown begins. Meanwhile the daemon thread still has a stack, and every frame on that stack holds a reference to the globals of the module its function was defined in. If that module is yours, your module dict cannot be cleared, so nothing in it is freed and none of its finalizers run.

Which means the same thread, started two ways, gives two different endings. Pass `time.sleep` and the frame belongs to the standard library. Pass a function of your own and it belongs to you.

{lesson.claim("One daemon thread running a function from your own module stops every finalizer in that module from running.")}
""")


lesson.code("""
DAEMON = \"\"\"
import threading, time


def snooze():
    time.sleep(30)


class Late:
    def __del__(self):
        print("  the finalizer ran")


keeper = Late()
threading.Thread(TARGET, daemon=True).start()
print("  a daemon thread is running and the program is over")
\"\"\"

if not CHILDREN:
    print(NO_CHILDREN)
else:
    for what, target in [
        ("time.sleep, a function from the standard library", "target=time.sleep, args=(30,)"),
        ("snooze, a function defined in the program itself", "target=snooze"),
    ]:
        print(" ", what)
        print(child(DAEMON.replace("TARGET", target)).stdout, end="")
""")


lesson.md(f"""
{figure("the-thread-that-holds-your-globals", "the two ways to start the same daemon thread side by side, one letting finalizers run and one not")}

Nothing is broken here. The thread is alive, its frame is real, and the reference it holds is a real reference. It is just that the thing keeping your objects alive is somewhere you would never think to look.

## The one collection that still happens

There is exactly one garbage collection in the middle of all this: `PyGC_Collect()`, called once between the thread cleanup and the module teardown, {cite("Python/pylifecycle.c:2460-2485@v3.15.0rc1#PyGC_Collect")}. It is a full collection of every generation, and it is what breaks the cycles that would otherwise keep whole object graphs alive past the point where anything can free them.

You can watch it with `gc.callbacks`, which is still installed at that point.

{lesson.claim("One full collection of generation two runs during shutdown, and the finalizing flag is already set when it does.")}
""")


lesson.code("""
COLLECT = \"\"\"
import gc, sys


def watch(phase, info):
    if phase == "stop":
        print(f"  collected generation {info['generation']}, is_finalizing={sys.is_finalizing()}")


gc.callbacks.append(watch)


class Node:
    pass


for _ in range(3):
    one, two = Node(), Node()
    one.peer, two.peer = two, one

print("  three cycles were left behind and nothing has collected them yet")
\"\"\"

print(NO_CHILDREN if not CHILDREN else child(COLLECT).stdout, end="")
""")


lesson.md(f"""
## The interpreter you forgot to close

One more thing happens before any of the above: {cite("Python/pylifecycle.c:2843-2872@v3.15.0rc1#finalize_subinterpreters")} looks for interpreters you created and never closed, warns about each one, and finalises them for you. Each gets the full treatment, its own atexit callbacks included, before the main interpreter carries on with its own ending.

{lesson.claim("A subinterpreter you never closed is finalised for you, with a RuntimeWarning, before the main interpreter finishes.")}
""")


lesson.code("""
SUBS = \"\"\"
import concurrent.interpreters as interpreters

kid = interpreters.create()
kid.exec("import atexit")
kid.exec("atexit.register(print, '  the second interpreter ran its own atexit callback')")
print("  a second interpreter is open and nobody closed it", flush=True)
\"\"\"

if not CHILDREN:
    print(NO_CHILDREN)
else:
    done = child(SUBS)
    print(done.stdout, end="")
    for line in done.stderr.splitlines():
        print("  " + line.strip())
""")


lesson.md(f"""
The warning is worth taking seriously. Being finalised at shutdown is not the same as being closed, because by then the main interpreter is already on its way out and the order between the two is not something you control.

## Nine endings on a build from the pinned source

Everything above ran one case at a time on whatever interpreter you have. Here is the same set of hazards run together in a container, against a release build made from the pinned source. There is also `Py_FinalizeEx`, {cite("Python/pylifecycle.c:2604-2612@v3.15.0rc1#Py_FinalizeEx")}, which is the same function with a return value, for embedders who want to know whether flushing worked.

{recording(ON_RELEASE)}

{figure("what-each-ending-runs", "a table of nine ways a process can end with whether atexit, the finalizer and the exit status came out as expected")}

Eight of nine ran their atexit callback and seven ran their finalizer. The two gaps are `os._exit`, which you asked for, and the daemon thread, which you did not.

Now the same program on a debug build, which counts what was still alive when the interpreter stopped.

{recording(ON_DEBUG)}

{figure("what-was-left-behind", "a bar chart of references left over for three programs, two at zero and the daemon thread one at 12680")}

Holding five thousand objects in a module global costs nothing at the end, because the module gets cleared and they all go. Holding the same five thousand behind a running daemon thread leaves every one of them alive, along with everything the module dict reaches. That is the difference between an ending and a program that simply stopped.

## Try it yourself

**One.** Give the daemon thread a function defined in a second module of your own and import it. Whose finalizers stop running, yours or the other module's? Work out from that which module dict the frame is actually holding.

**Two.** Register an atexit callback that calls `sys.exit(1)`. Read `atexit_callfuncs` and predict what happens before you run it.

**Three.** Put a `weakref.finalize` on an object next to a `__del__` on another and see which of the two runs first. Then move one of them into a class defined in the standard library and try again.

**Four.** Run the late finalizer cell under `-X importtime`. The import that fails still costs something. Find out what.

## What you now know

Shutdown is one function read top to bottom. The first thing it does is join your non daemon threads by calling into `threading._shutdown`, then run your atexit callbacks. Everything after that is teardown, and the finalizing flag goes up in between, which is why `sys.is_finalizing()` is `False` in a callback and `True` in a late `__del__`.

Atexit callbacks run newest first, because `register` inserts at the front of a list. The list is copied and then emptied, so registering a callback from inside one is a quiet no op.

Once teardown starts, `sys.meta_path` is cleared and the import system stops working. A finalizer can still read the globals of its own module, because those are what is being freed, but any import raises `ImportError` and says why. Exceptions from both callbacks and finalizers are printed and ignored, and the exit status stays zero, so a shell script cannot tell that your cleanup failed.

Two endings skip work you asked for. `os._exit` skips all of it by design. A daemon thread running a function from your own module skips your finalizers by accident, because its stack frame holds your module's globals and stops the module dict being cleared. On a debug build that one costs 12680 references left alive, against zero for the same objects held any other way.

## What is next

R09 is the last of the runtime lessons, and it turns everything here around. Instead of watching from Python while the interpreter takes itself apart, it writes the C that has to survive it: reference counting on error paths, `tp_traverse` and `tp_clear` and `tp_finalize` on a container type, and what all of that has to look like on a build with no global interpreter lock.
""")


raise SystemExit(lesson.save())
