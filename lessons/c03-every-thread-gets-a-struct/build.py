#!/usr/bin/env python
"""C03. Every thread gets a struct.

The third concurrency lesson, and the one that stops treating a thread as a black box. C01
measured the lock and C02 measured what it was protecting. Both of them talked about threads
handing something over without ever saying what a thread is to the interpreter.

It is a struct. A `PyThreadState`, one per thread, holding the frame that thread is running,
the exception it is handling, its recursion budget and its `threading.local` values. They are
all on one linked list hanging off the interpreter, and this lesson walks that list from
Python with `ctypes`, which turns out to be about fifteen lines.

Once the list is on screen the rest follows: why `threading.get_ident()` repeats and the state
id does not, why `sys._current_frames()` is keyed the way it is, and what shutdown does to a
daemon thread, which is one store into one field of that same struct.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording

lesson = Lesson("c03-every-thread-gets-a-struct", "c03")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("c03-every-thread-gets-a-struct").figure

THE_DAEMON = "c03-the-daemon-that-never-came-back"


lesson.md(f"""
# C03. Every thread gets a struct

{badge}

C01 measured the lock and C02 measured what it was keeping safe. Both lessons kept saying things like "a thread hands the lock over" without ever saying what a thread is to the interpreter.

It is a struct, and you can go and look at it. This lesson walks the interpreter's own list of threads from Python, using about fifteen lines of `ctypes` and nothing else.

{figure("what-a-thread-is-here", "the operating system's idea of a thread on one side and the interpreter's on the other")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Include/cpython/pystate.h:66-101@v3.15.0rc1`.

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

Most of this lesson runs anywhere. Two things do not: a browser tab cannot start a thread, and it cannot start another process either. Those cells check first and say so rather than printing nonsense. In Colab or from a checkout, everything runs.

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
## One struct per thread

Start with the thing itself. Every thread running Python has a {term("thread state")}, which in C is a `PyThreadState` {cite("Include/cpython/pystate.h:66-101@v3.15.0rc1#_ts")}. It is a plain struct with about forty fields in it, and the first three are the ones this section is about: a `prev` pointer, a `next` pointer, and the interpreter it belongs to.

{figure("what-rides-on-the-state", "nine fields of one thread state, from the list pointers at the bottom to the state field at the top")}

The `prev` and `next` are there because the interpreter keeps every thread state on one linked list. The head of it lives on the interpreter, next to a counter used to hand out ids {cite("Include/internal/pycore_interp_structs.h:867-881@v3.15.0rc1#pythreads")}. Making a thread state bumps that counter, takes a lock, and pushes the new state onto the front {cite("Python/pystate.c:1632-1671@v3.15.0rc1#new_threadstate")}, so the list runs newest to oldest and the last thing on it is always the main thread {cite("Python/pystate.c:1618-1630@v3.15.0rc1#add_threadstate")}.

{figure("the-list-newest-first", "the interpreter's head pointer and four thread states chained by their next pointers")}

None of that is hidden. Four of the functions that walk it are public C API, which means `ctypes` can call them {cite("Python/pystate.c:2671-2679@v3.15.0rc1#PyInterpreterState_ThreadHead")}. The cell below asks for the current thread's state, asks which interpreter it belongs to, and then follows the chain, printing the id of every state it finds {cite("Python/pystate.c:2135-2140@v3.15.0rc1#PyThreadState_GetID")}.

Watch the list grow when three threads start and shrink back when they finish.

{lesson.claim("Every thread has its own PyThreadState, the interpreter keeps them all on one linked list with the newest at the front, and a state leaves the list when its thread finishes")}
""")


lesson.code(
    """
import ctypes
import threading

api = ctypes.pythonapi
NO_THREADS = "  this build cannot start a thread, so the list will never have more than one"


def ask(name, args, result):
    \"\"\"Point ctypes at one C API function. Every one used here is public and documented.\"\"\"
    fn = getattr(api, name)
    fn.argtypes = args
    fn.restype = result
    return fn


current_state = ask("PyThreadState_Get", [], ctypes.c_void_p)
state_id = ask("PyThreadState_GetID", [ctypes.c_void_p], ctypes.c_uint64)
interpreter_of = ask("PyThreadState_GetInterpreter", [ctypes.c_void_p], ctypes.c_void_p)
first_state = ask("PyInterpreterState_ThreadHead", [ctypes.c_void_p], ctypes.c_void_p)
next_state = ask("PyThreadState_Next", [ctypes.c_void_p], ctypes.c_void_p)

INTERP = interpreter_of(current_state())


def walk():
    \"\"\"Follow interp->threads.head and then ->next, the way the interpreter walks it.\"\"\"
    found = []
    state = first_state(INTERP)
    while state:
        found.append(state_id(state))
        state = next_state(state)
    return found


def threads_work():
    \"\"\"Some runtimes cannot start a thread at all. A browser tab is one of them.\"\"\"
    try:
        probe = threading.Thread(target=lambda: None)
        probe.start()
        probe.join()
    except RuntimeError:
        return False
    return True


THREADS_WORK = threads_work()


def park(count, body=None):
    \"\"\"Start count threads and hold every one of them still until release() lets them go.\"\"\"
    ready = threading.Semaphore(0)
    go = threading.Event()

    def pause():
        ready.release()
        go.wait()

    def wrapper():
        if body is None:
            pause()
        else:
            body(pause)

    hands = [threading.Thread(target=wrapper) for _ in range(count)]
    for hand in hands:
        hand.start()
    for _ in hands:
        ready.acquire()
    return hands, go


def release(hands, go):
    go.set()
    for hand in hands:
        hand.join()


here = current_state()
print("  this thread's state sits at", hex(here), "and its id is", state_id(here))
print("  the interpreter it belongs to sits at", hex(INTERP))
print("  ids on the list right now:", walk())
if not THREADS_WORK:
    print(NO_THREADS)
else:
    crew = park(3)
    print("  with three more threads parked:", walk())
    release(*crew)
    print("  once those three have finished:", walk())
""",
    varies=(
        "the two addresses are wherever this process happened to put them, and the ids depend "
        "on how many threads the runtime has already started, which is one in a plain script "
        "and several in a notebook kernel"
    ),
)


lesson.md(f"""
## Three numbers, and only one of them is yours to trust

There are three ways to ask which thread you are, and they are not interchangeable.

The first is the state id you just printed. The interpreter hands those out itself, one higher each time, under the same lock that pushes the state onto the list. It never reuses one.

The other two come from the operating system, and they get filled in later. A thread state is created by whoever asked for the thread, but `thread_id` and `native_thread_id` are written by the new thread itself, the first time it binds to its state {cite("Python/pystate.c:162-192@v3.15.0rc1#bind_tstate")}. They are the two fields sitting next to the scratch dict in the header {cite("Include/cpython/pystate.h:161-172@v3.15.0rc1#native_thread_id")}.

`threading.get_ident()` returns the first of those, and the documentation is honest about it: the value may be recycled when a thread exits. The cell below is that sentence made uncomfortable. Three threads, joined, three more, joined, three more. The state ids climb. The idents come back around.

{figure("three-numbers-one-thread", "the three identifiers, who writes each one, when, and whether it ever gets handed out twice")}

If you have ever keyed a dictionary on `threading.get_ident()` and kept it after the thread finished, this is the bug.

{lesson.claim("A thread state id is never handed out twice, while threading.get_ident() is, so the same ident can name two different threads over the life of one program")}
""")


lesson.code(
    """
def one_wave(size):
    \"\"\"Start size threads at once, and have each of them report the three numbers.\"\"\"
    seen = []
    guard = threading.Lock()

    def report(pause):
        state = current_state()
        with guard:
            seen.append((state_id(state), threading.get_ident(), threading.get_native_id()))
        pause()

    crew = park(size, report)
    release(*crew)
    return sorted(seen)


if not THREADS_WORK:
    print(NO_THREADS)
else:
    print(f"  {'wave':<6}{'state id':>10}{'get_ident()':>16}{'get_native_id()':>18}")
    for wave in (1, 2, 3):
        for state, ident, native in one_wave(3):
            print(f"  {wave:<6}{state:>10}{ident:>16}{native:>18}")
""",
    varies=(
        "the ids depend on how many threads this runtime has already made, and the idents and "
        "native ids are whatever the operating system handed out, but the state ids climb and "
        "the idents repeat from one wave to the next on any build"
    ),
)


lesson.md(f"""
## sys._current_frames is that same walk

`sys._current_frames()` gives you a dict from thread to frame, and it is worth knowing where that dict comes from. It stops every thread, takes the lock on the list, walks it, and for each state reads `current_frame` and uses `thread_id` as the key {cite("Python/pystate.c:2691-2730@v3.15.0rc1#_PyThread_CurrentFrames")}.

So it is the walk from the first cell, with two fields read instead of one. That also explains the keys: they are `thread_id`, the recycled one, which is why the dict matches `threading.get_ident()` and not the state ids.

The cell parks three threads and prints all three views at once.

{lesson.claim("The keys of sys._current_frames() are exactly the idents of the live threads, because the dict is built by walking the same list of thread states")}
""")


lesson.code(
    """
def three_views():
    \"\"\"The same set of threads, seen through the C list, through sys, and through threading.\"\"\"
    print("  ids on the interpreter's list:", sorted(walk()))
    frames = sorted(sys._current_frames())
    idents = sorted(hand.ident for hand in threading.enumerate())
    print("  keys in sys._current_frames():", frames)
    print("  idents from threading:       ", idents)
    print("  the last two are the same set:", frames == idents)


if not THREADS_WORK:
    three_views()
else:
    crew = park(3)
    three_views()
    release(*crew)
""",
    varies=(
        "the ids and idents are whatever this run produced, and the count depends on whether "
        "anything else in the runtime is holding threads open, but the last line is True "
        "everywhere"
    ),
)


lesson.md(f"""
## What only this thread can see

Once you know a thread has its own struct, a lot of Python stops being magic.

`threading.local` is the obvious one. Each thread state holds a small key object, and every `threading.local` is a dict from those keys to that thread's values {cite("Modules/_threadmodule.c:1376-1388@v3.15.0rc1#threading_local_key")}. The key is made on first use and lives on the state {cite("Modules/_threadmodule.c:1600-1623@v3.15.0rc1#create_localdummies")}, so when the thread goes, its values go with it.

There is a second, older per thread dict, and `PyThreadState_GetDict()` hands it straight to you {cite("Python/pystate.c:2101-2108@v3.15.0rc1#PyThreadState_GetDict")}. The interpreter uses it for its own bookkeeping, and there is one use of it you have definitely seen. When you print a list that contains itself, the `...` comes from a list of objects currently being printed, kept in this dict, on this thread {cite("Objects/object.c:3106-3137@v3.15.0rc1#Py_ReprEnter")}. That is why two threads can print two self referential structures at once without confusing each other.

The exception being handled is on the state too, which is what `sys._current_exceptions()` reads, using the same walk as before. The cell parks a worker inside an `except` block and asks from the main thread.

{lesson.claim("The threading.local values, the scratch dict and the exception being handled all live on the thread state, so one thread never sees another thread's")}
""")


lesson.code(
    """
state_dict = ask("PyThreadState_GetDict", [], ctypes.c_void_p)


def scratch():
    \"\"\"The dict PyThreadState_GetDict() hands back, which belongs to this thread alone.\"\"\"
    return ctypes.cast(state_dict(), ctypes.py_object).value


local = threading.local()
local.note = "written by the main thread"

loop = []
loop.append(loop)
print("  a list holding itself prints as", repr(loop))
print("  and now this thread's scratch dict holds", sorted(scratch()))

answers = {}


def look(pause):
    local.note = "written by the worker"
    scratch()["mine"] = "and this key is the worker's"
    answers["note"] = local.note
    answers["keys"] = sorted(scratch())
    try:
        raise ValueError("held open inside the worker")
    except ValueError:
        pause()


if not THREADS_WORK:
    print(NO_THREADS)
else:
    crew = park(1, look)
    print("  the worker's local.note:  ", answers["note"])
    print("  the main thread's is still:", local.note)
    print("  the worker's scratch dict:", answers["keys"])
    print("  the main thread's:        ", sorted(scratch()))
    for ident, held in sorted(sys._current_exceptions().items()):
        print(f"  thread {ident} is handling {held!r}")
    release(*crew)
""",
    varies=(
        "the idents are whatever the operating system handed out, and how many threads show up "
        "in the last two lines depends on what else the runtime is keeping alive, but only the "
        "worker is ever holding an exception"
    ),
)


lesson.md(f"""
## Attaching and detaching

Now the field the whole of C01 was really about.

A thread state has an `int` called `state`, and it holds one of four values {cite("Include/internal/pycore_pystate.h:20-49@v3.15.0rc1#_Py_THREAD_SUSPENDED")}. Attached means the thread is running Python. Detached means it is not, either because it is sitting in a C function or because it is waiting for something. The other two are done to a thread rather than by it.

{figure("attached-detached-suspended", "the four values the state field can hold, who is allowed to write each one, and what the thread is doing in it")}

{term("attach and detach")} is the whole handshake. Attaching takes the lock, sets the field, and marks the state active {cite("Python/pystate.c:2225-2251@v3.15.0rc1#_PyThreadState_Attach")}. Detaching does the reverse and releases the lock last {cite("Python/pystate.c:2284-2300@v3.15.0rc1#detach_thread")}. On a build with the {term("GIL")} the setting of the field is a plain store, because only one thread can be doing it. On the {term("free threaded build")} it is a compare and exchange, because several can {cite("Python/pystate.c:2178-2191@v3.15.0rc1#tstate_try_attach")}.

And `Py_BEGIN_ALLOW_THREADS`, the macro C01 spent a section on, is exactly this. It expands to `PyEval_SaveThread`, which is one line: detach {cite("Python/ceval_gil.c:642-663@v3.15.0rc1#PyEval_SaveThread")}. The matching `PyEval_RestoreThread` attaches again. "Release the GIL" and "detach the thread state" are the same sentence said two ways, and the second one is the one that is still true when there is no GIL.

There is a nice detail hiding in the attach path. C02 showed that a {term("critical section")} is allowed to let go of its lock partway through. That is where it happens: detaching suspends whatever critical sections the thread was holding, and attaching picks them back up {cite("Python/pystate.c:2302-2306@v3.15.0rc1#_PyThreadState_Detach")}. The stack of them is one more field on the thread state.

The third value, suspended, is what {term("stop the world")} does. A thread asked to suspend does not stop where it is. It carries on to its next {term("periodic check")}, and only then parks itself and waits {cite("Python/pystate.c:2204-2223@v3.15.0rc1#tstate_wait_attach")}. The collector lessons in M7 leaned on this without saying where it lived. It lives here, in one int.

{lesson.claim("Py_BEGIN_ALLOW_THREADS is a detach of the thread state and Py_END_ALLOW_THREADS is an attach, which is why releasing the GIL and detaching are the same operation", unobservable="both macros are C, and the only thing visible from Python is that a C function which uses them lets other threads run")}
""")


lesson.md(f"""
## The thread that never attaches again

The fourth value is the one with consequences you have probably hit.

When the interpreter shuts down it does not ask the other threads to stop. It writes a 3 into the `state` field of each of them and moves on {cite("Python/pystate.c:2341-2348@v3.15.0rc1#_PyThreadState_SetShuttingDown")}. A {term("daemon thread")} that is in the middle of a loop keeps going, because nothing has interrupted it yet. Then it reaches its next periodic check, tries to attach, reads the 3, and is hung where it stands {cite("Python/pystate.c:3199-3212@v3.15.0rc1#_PyThreadState_HangThread")}.

Hung, not stopped. No exception is raised in it, so no `finally` runs, no `with` block exits, and nothing it was holding is released {cite("Python/pystate.c:3191-3204@v3.15.0rc1#_PyThreadState_MustExit")}.

{figure("the-daemon-at-shutdown", "the main thread returning, shutdown writing to every other state, and the daemon getting hung at its next check")}

The cell starts a child interpreter with a daemon thread counting in a loop, lets the main thread sleep briefly and return, and reads back what the child managed to print. The count it reaches is different every run. Whether the `finally` block ran is not.

{lesson.claim("A daemon thread still running at shutdown is hung at its next periodic check, and its finally blocks do not run")}
""")


lesson.code(
    """
import subprocess

CHILD = \"\"\"
import threading
import time


def body():
    n = 0
    try:
        while True:
            n += 1
            if n % 1000000 == 0:
                print("the daemon reached", n, flush=True)
    finally:
        print("the daemon's finally ran", flush=True)


threading.Thread(target=body, daemon=True).start()
time.sleep(0.3)
print("the main thread is done", flush=True)
\"\"\"


def run_child():
    \"\"\"Start another copy of this interpreter and collect everything it printed.\"\"\"
    if not sys.executable:
        return None
    try:
        done = subprocess.run(
            [sys.executable, "-c", CHILD],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except OSError:
        return None
    return done.stdout.strip().splitlines()


said = run_child()
if said is None:
    print("  this build cannot start another process, so there is nothing to try here")
else:
    print("  the child printed", len(said), "lines, and the last one was:", said[-1])
    print("  did the daemon reach its finally block:", any("finally" in line for line in said))
""",
    varies=(
        "how far the daemon counts before the main thread returns depends entirely on the "
        "machine, so the number of lines moves from run to run, while the last line and the "
        "answer on the last line do not"
    ),
)


lesson.md(f"""
That is a property of the thread state rather than of the lock, so it should look the same on a build that has no lock at all. The recording checks that on the free threaded image.

{recording(THE_DAEMON)}
""")


lesson.md("""
## Try it yourself

Four things, roughly in order of how much they will teach you.

Change the daemon thread in the last cell to `daemon=False` and run it again. The child takes a lot longer, prints far more, and its `finally` does run, because shutdown waits for it. That is the entire difference between the two kinds of thread.

Put a `with open(...)` around the daemon's loop instead of the `try`. The file is still open when the thread is hung, and the process exits anyway. It is worth seeing once, because it is the reason "the daemon will clean up after itself" is never true.

In the second cell, print `id(threading.current_thread())` alongside the other three numbers. Python object ids get recycled too, and for the same reason: the memory comes back around. Three of your four numbers are addresses wearing different hats.

Start a thread that does nothing but sleep for a long time, and walk the list from the main thread while it sleeps. Its state is still there. A sleeping thread is detached, not gone, which is the difference between a thread state and a running thread.

## What you now know

A thread, to CPython, is a struct. `PyThreadState` holds the frame it is running, the exception it is handling, its recursion budget, its scratch dict, the key its `threading.local` values hang off, and its place in a list.

That list hangs off the interpreter, newest first, and you can walk it from Python with five public C API calls and no debugger.

There are three numbers that name a thread. The state id is the interpreter's, counts up, and is never reused. `threading.get_ident()` and `get_native_id()` come from the operating system and both get handed out again after a thread exits.

`sys._current_frames()` and `sys._current_exceptions()` are that same walk with a different field read out, which is why they are keyed by ident.

The `state` field is where the GIL handshake actually happens. Attached and detached are the two the thread moves between itself, and `Py_BEGIN_ALLOW_THREADS` is a detach. Suspended is what stopping the world does to a thread. Shutting down is what finalization does, and a daemon thread that reads it is hung on the spot with none of its cleanup run.

## What is next

C04 stays on the object header and picks up the thing C02 left out. Free threading could not keep one reference count per object updated by every thread without the counter becoming the bottleneck, so it keeps two: one the owning thread can change without any locking at all, and one everybody else has to share. The owning thread is named by `ob_tid`, which is the id from this lesson turning up in every object in the heap.
""")


raise SystemExit(lesson.save())
