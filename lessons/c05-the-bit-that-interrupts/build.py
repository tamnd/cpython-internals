#!/usr/bin/env python
"""C05. The bit that interrupts a running thread.

The fifth concurrency lesson, and the one that goes back to a single thread. C01 named the eval
breaker in one sentence and then spent the rest of the lesson timing the GIL. This lesson takes
that word of bits seriously, because five separate features in CPython are built on it and none
of them look related from the outside.

The shape is always the same. Somebody sets a bit and returns immediately. The thread that owns
the bit notices at its next periodic check and does the work. That is how Ctrl-C reaches a
Python function, how the garbage collector gets a turn, how one thread throws an exception into
another, how a C extension asks the main thread to do something, and how a debugger in a
different process makes this one run a script.

The interesting consequence is the one about waiting. A thread inside a single long call into C
never reaches a check, so everything queued up behind that word waits for the call to return.
Both Tier 1 recordings are that, measured in a container: an injected script arrives in about
three milliseconds if the target is running bytecode, and about three seconds if it is not.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording

lesson = Lesson("c05-the-bit-that-interrupts", "c05")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("c05-the-bit-that-interrupts").figure

WITH_THE_LOCK = "c05-the-message-that-waited"
WITHOUT_THE_LOCK = "c05-the-same-message-without-the-lock"


lesson.md(f"""
# C05. The bit that interrupts a running thread

{badge}

Press Ctrl-C while Python is running and something has to stop the program. The operating system does not stop it. It calls a small C function, and that function does almost nothing: it writes down which signal arrived and sets one bit. Nothing has been interrupted yet.

The interpreter finds that bit the next time it looks, and it only looks in a few specific places. If the thread is halfway through one long call into C, it will not look for a while, and your Ctrl-C sits there waiting.

That one word of bits is the eval breaker. C01 named it and moved on. It turns out to be how the collector gets a turn, how one thread throws an exception into another, and how a debugger in another process makes this one run a script.

{figure("where-a-thread-stops-to-look", "two columns, the places a running thread checks for interruptions and the places it does not")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/ceval_macros.h:520-528@v3.15.0rc1`.

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

Most of this lesson needs a second thread, and the last cell needs a second process. A browser tab has neither, so each cell checks once and says so instead of failing. In Colab or from a checkout, everything runs.

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
## Where a running thread stops to look

Every {term("thread state")} carries one machine word called `eval_breaker` {cite("Include/cpython/pystate.h:66-77@v3.15.0rc1#eval_breaker")}. It sits three fields into the struct, right next to the list pointers from C03, and the low eight bits of it are eight separate requests {cite("Include/internal/pycore_ceval.h:345-357@v3.15.0rc1#_PY_GC_SCHEDULED_BIT")}.

{figure("one-word-eight-bits", "the eight bits of the eval breaker, who sets each one and what the thread does about it")}

Eight unrelated features, one word. That is the whole trick. Setting a bit is an atomic or, clearing it is an atomic and {cite("Include/internal/pycore_ceval.h:359-376@v3.15.0rc1#_Py_eval_breaker_bit_is_set")}, and the eval loop only has to ask one question instead of eight.

The question is asked by `_CHECK_PERIODIC`, which is three lines: read the word, mask off the eight bits, and if anything is left, go and deal with it {cite("Python/ceval_macros.h:520-528@v3.15.0rc1#check_periodics")}. That is the {term("periodic check")}, and it is not a timer. It is an instruction, written into the bytecode in the places where a loop could otherwise run forever {cite("Python/bytecodes.c:158-173@v3.15.0rc1#_CHECK_PERIODIC")}.

The main place is the backward jump at the end of a loop {cite("Python/bytecodes.c:3585-3600@v3.15.0rc1#JUMP_BACKWARD")}. But there is a second backward jump that deliberately does not check, and the comment above it explains why: in a `yield from` or `await` chain, an interruption should be handled by the innermost generator, not by whoever is delegating to it {cite("Python/bytecodes.c:3697-3705@v3.15.0rc1#JUMP_BACKWARD_NO_INTERRUPT")}.

{figure("two-backward-jumps", "JUMP_BACKWARD which checks the eval breaker beside JUMP_BACKWARD_NO_INTERRUPT which does not")}

You can see both from Python with `dis`, and count them across a real module while you are there.

{lesson.claim("An ordinary while loop compiles to JUMP_BACKWARD and a yield from loop compiles to JUMP_BACKWARD_NO_INTERRUPT, and a module built around delegation has more of the second kind than the first")}
""")


lesson.code("""
import asyncio.base_events
import dis
import types


def loop():
    n = 0
    while n < 10:
        n += 1


def delegate(inner):
    yield from inner


def code_under(thing):
    \"\"\"Every code object inside this one, including the ones for nested functions.\"\"\"
    seen = [thing]
    while seen:
        code = seen.pop()
        yield code
        seen += [c for c in code.co_consts if isinstance(c, types.CodeType)]


def backward_jumps(code):
    \"\"\"Count the two backward jumps, the one that checks and the one that refuses to.\"\"\"
    tally = {"JUMP_BACKWARD": 0, "JUMP_BACKWARD_NO_INTERRUPT": 0}
    for inner in code_under(code):
        for step in dis.get_instructions(inner, adaptive=False):
            if step.opname in tally:
                tally[step.opname] += 1
    return tally


def every_function(module):
    \"\"\"Every function a module defines, including the ones that are methods on its classes.\"\"\"
    for value in vars(module).values():
        yield value
        if isinstance(value, type):
            yield from vars(value).values()


print("  a plain while loop: ", backward_jumps(loop.__code__))
print("  a yield from loop:  ", backward_jumps(delegate.__code__))

WHOLE = {"JUMP_BACKWARD": 0, "JUMP_BACKWARD_NO_INTERRUPT": 0}
for thing in every_function(asyncio.base_events):
    body = getattr(thing, "__code__", None)
    if body is not None:
        for key, count in backward_jumps(body).items():
            WHOLE[key] += count
print("  every loop in asyncio.base_events:", WHOLE)
""")


lesson.md(f"""
## How late a Ctrl-C can be

A {term("signal handler")} written in Python is not what the operating system calls. The kernel calls a C function, and that function records which signal arrived and calls one line that sets `_PY_SIGNALS_PENDING_BIT` on the main thread's word {cite("Python/ceval_gil.c:665-672@v3.15.0rc1#_PyEval_SignalReceived")}. Then it returns, and your program carries on as if nothing happened.

{figure("the-long-way-round-a-signal", "five steps from pressing Ctrl-C to a Python handler running, with the wait in the middle")}

Your Python function runs later, from the periodic check, out of a branch that only exists to call it {cite("Python/ceval_gil.c:827-842@v3.15.0rc1#handle_signals")}. The comment at the top of the signal module states the three rules plainly: only the main thread may install a handler, only the main thread runs one, and the operating system may deliver the signal to any thread it likes {cite("Modules/signalmodule.c:80-101@v3.15.0rc1#signal")}. Try to register a handler from a worker and you get a `ValueError` saying signal only works in the main thread of the main interpreter {cite("Modules/signalmodule.c:496-508@v3.15.0rc1#_Py_ThreadCanHandleSignals")}.

The cell below raises `SIGINT` from a worker thread fifty milliseconds in, twice. The first time the main thread is inside one call to `list.sort`. The second time it is running an ordinary Python loop. Same signal, same delay, and the gap between the two answers is the periodic check.

{lesson.claim("A signal raised while the main thread is inside a single call to list.sort is not handled until that call returns, and the Python handler runs on the main thread even though a worker thread raised the signal")}
""")


lesson.code(
    """
import random
import signal
import threading
import time

NO_THREADS = "  this build cannot start a thread, so there is nothing to fire the signal"
rang = []


def note_it(number, frame):
    \"\"\"The Python level handler. It runs from the periodic check, never from the C one.\"\"\"
    rang.append((time.perf_counter(), threading.current_thread().name))


def threads_work():
    \"\"\"Some runtimes cannot start a thread at all. A browser tab is one of them.\"\"\"
    try:
        probe = threading.Thread(target=int)
        probe.start()
        probe.join()
    except RuntimeError:
        return False
    return True


THREADS_WORK = threads_work()


def ring_the_bell(after):
    \"\"\"Raise SIGINT from a worker thread, so the main thread is definitely busy.\"\"\"
    time.sleep(after)
    signal.raise_signal(signal.SIGINT)


def wait_for_it(busy):
    \"\"\"Time the gap between the signal being raised and the handler getting to run.\"\"\"
    rang.clear()
    threading.Thread(target=ring_the_bell, args=(0.05,)).start()
    started = time.perf_counter()
    busy()
    while not rang:
        pass
    return (rang[0][0] - started) * 1000, rang[0][1]


if not THREADS_WORK:
    print(NO_THREADS)
else:
    was = signal.signal(signal.SIGINT, note_it)
    pile = list(range(3000000))
    random.shuffle(pile)
    late, who = wait_for_it(pile.sort)
    print(f"  raised 50 ms in, during one call to list.sort:  handled at {late:.0f} ms")
    soon, who = wait_for_it(lambda: None)
    print(f"  raised 50 ms in, during an ordinary Python loop: handled at {soon:.0f} ms")
    print("  a worker thread raised both of them, and the handler ran on:", who)
    signal.signal(signal.SIGINT, was)
""",
    varies=(
        "both numbers are timings on whatever machine is running the notebook, so they move "
        "from run to run, and how long the sort takes depends on the machine as much as on "
        "the build"
    ),
)


lesson.md(f"""
## Throwing an exception into another thread

Python has no way to stop a thread. It has something slightly stranger: a way to leave an exception on another thread's state and let that thread raise it itself.

`PyThreadState_SetAsyncExc` takes a thread id and an exception class. It walks the interpreter's thread list looking for a state whose `thread_id` matches, stores the class on that state and sets `_PY_ASYNC_EXCEPTION_BIT` {cite("Python/pystate.c:2544-2580@v3.15.0rc1#PyThreadState_SetAsyncExc")}. Then it returns the number of thread states it matched, which is one on a good day. The target picks the exception up at its next periodic check, out of the last branch in the list {cite("Python/ceval_gil.c:1414-1429@v3.15.0rc1#_PY_ASYNC_EXCEPTION_BIT")}, and raising it clears the field again with an atomic exchange so it can only fire once {cite("Python/ceval_gil.c:1438-1451@v3.15.0rc1#_PyEval_RaiseAsyncExc")}.

This is the {term("asynchronous exception")}, and the header comment above it is unusually candid. It says the feature was requested by Just van Rossum and Alex Martelli, that there is no Python level API for it, and that if you want one you should write an extension or use `ctypes`. So that is what the cell does.

The thread id it wants is the recycled `ident` from C03, not the never reused state id, which is worth remembering if you ever hold on to one of these.

Two targets. One spins in a Python loop, one calls `time.sleep(1.5)` once. Both get the same nudge at the same moment.

{lesson.claim("An exception set on another thread is raised at that thread's next periodic check, so a thread spinning in Python stops almost immediately and a thread inside one call to time.sleep does not stop until the sleep is over")}
""")


lesson.code(
    """
import ctypes

api = ctypes.pythonapi
api.PyThreadState_SetAsyncExc.argtypes = [ctypes.c_ulong, ctypes.py_object]
api.PyThreadState_SetAsyncExc.restype = ctypes.c_int


class Nudge(Exception):
    \"\"\"Something to throw at another thread from outside it.\"\"\"


caught = {}
give_up = threading.Event()


def busy_loop():
    try:
        while not give_up.is_set():
            pass
    except BaseException as exc:
        caught["a Python loop"] = type(exc).__name__


def long_sleep():
    try:
        time.sleep(1.5)
        caught["one call to time.sleep"] = "slept the whole way through"
    except BaseException as exc:
        caught["one call to time.sleep"] = type(exc).__name__


def nudge(target):
    \"\"\"Ask the interpreter to raise Nudge in another thread, and time how long it takes.\"\"\"
    hand = threading.Thread(target=target)
    hand.start()
    time.sleep(0.2)
    started = time.perf_counter()
    found = api.PyThreadState_SetAsyncExc(hand.ident, ctypes.py_object(Nudge))
    hand.join(4)
    give_up.set()
    hand.join(4)
    return found, (time.perf_counter() - started) * 1000


if not THREADS_WORK:
    print("  this build cannot start a thread, so there is nothing to interrupt")
else:
    for target in (busy_loop, long_sleep):
        found, waited = nudge(target)
        print(f"  {target.__name__:10} thread states matched: {found}, took {waited:6.0f} ms")
    for label, what in sorted(caught.items()):
        print(f"  the thread running {label:22} ended with {what}")
""",
    varies=(
        "the two timings are measured on whatever machine is running the notebook, and the "
        "first one is small enough that scheduling noise moves it around"
    ),
)


lesson.md(f"""
## Asking the main thread to run something

The same shape shows up a third time, and this one is a public C API that extension authors actually use. `Py_AddPendingCall` takes a C function pointer, puts it on a small ring buffer, sets `_PY_CALLS_TO_DO_BIT` and returns {cite("Python/ceval_gil.c:810-825@v3.15.0rc1#Py_AddPendingCall")}. It does not run anything. It is safe to call from a signal handler or from a thread that does not hold the GIL, precisely because it does so little {cite("Python/ceval_gil.c:779-808@v3.15.0rc1#_PyEval_AddPendingCall")}.

There is one detail worth pointing at. `Py_AddPendingCall` always targets the main thread of the main interpreter, whoever calls it. The newer `_PyEval_AddPendingCall` can aim at the calling thread instead, and the older public one passes a flag that means main thread only. So a {term("pending call")} asked for by a worker runs somewhere else.

{figure("who-asks-and-who-runs", "five ways to set a bit, whose eval breaker each one lands on and which thread does the work")}

The cell schedules one from a thread named Worker and prints where it actually ran.

{lesson.claim("A pending call scheduled from a worker thread runs on the main thread, because Py_AddPendingCall always leaves the work for the main thread of the main interpreter")}
""")


lesson.code(
    """
CALLBACK = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p)
api.Py_AddPendingCall.argtypes = [CALLBACK, ctypes.c_void_p]
api.Py_AddPendingCall.restype = ctypes.c_int

ran_on = []


def pending_body(ignored):
    \"\"\"A C callback, and it runs from the periodic check like everything else here.\"\"\"
    ran_on.append(threading.current_thread().name)
    return 0


HELD = CALLBACK(pending_body)


def schedule_it():
    time.sleep(0.05)
    ran_on.append(("asked from", threading.current_thread().name))
    api.Py_AddPendingCall(HELD, None)


if not THREADS_WORK:
    print("  this build cannot start a thread, so there is nobody to schedule from")
else:
    ran_on.clear()
    threading.Thread(target=schedule_it, name="Worker").start()
    started = time.perf_counter()
    while len(ran_on) < 2:
        pass
    print("  who asked for it: ", ran_on[0])
    print("  who ran it:       ", ran_on[1])
    print(f"  it ran {(time.perf_counter() - started) * 1000:.0f} ms after the thread started")
""",
    varies=(
        "the last line is a timing on whatever machine is running the notebook, and it is "
        "dominated by the fifty milliseconds the worker sleeps before it asks"
    ),
)


lesson.md(f"""
## The collector is a bit too

M07 covered the cycle collector in detail and left one thing unsaid: the allocator never runs a collection. When generation zero passes its threshold, `_PyObject_GC_Link` calls `_Py_ScheduleGC`, and all that does is set `_PY_GC_SCHEDULED_BIT` {cite("Python/gc.c:1964-1993@v3.15.0rc1#_PyObject_GC_Link")}. The collection happens later, from the periodic check, on whichever thread gets there first.

Which means a piece of code that allocates a great many objects without ever reaching a check will not be collected during. The cell below builds sixty thousand small dictionaries twice. Once with `json.loads`, which is one call into C from start to finish. Once with a list display, which is a Python loop with a backward jump in it.

{figure("one-call-or-sixty-thousand-steps", "one collection during json.loads against eighty nine during the equivalent list display")}

Same objects, same count, same allocator, and the collector runs a completely different number of times.

{lesson.claim("Building the same sixty thousand dictionaries from C runs the cycle collector far fewer times than building them from Python, because a single C call never reaches a periodic check")}
""")


lesson.code(
    """
import gc
import json

collections = []


def took_note(phase, info):
    if phase == "start":
        collections.append(info["generation"])


SHAPE = [{"a": [1, 2, 3], "b": {"c": 4}} for _ in range(60000)]
TEXT = json.dumps(SHAPE)
del SHAPE
gc.collect()
print("  the collector is scheduled when generation zero passes", gc.get_threshold()[0])

gc.callbacks.append(took_note)
collections.clear()
started = time.perf_counter()
parsed = json.loads(TEXT)
in_c = time.perf_counter() - started
runs_in_c = len(collections)

collections.clear()
started = time.perf_counter()
built = [{"a": [1, 2, 3], "b": {"c": 4}} for _ in range(60000)]
in_py = time.perf_counter() - started
runs_py = len(collections)
gc.callbacks.remove(took_note)

print(f"  json.loads built them in {in_c * 1000:5.0f} ms, collector ran {runs_in_c:3} times")
print(f"  a list display did it in {in_py * 1000:5.0f} ms, collector ran {runs_py:3} times")
print("  the two of them built the same number of dicts:", len(parsed) == len(built))
""",
    varies=(
        "the two timings depend on the machine, and the number of collections is much smaller "
        "on a free threaded build because that build counts allocations per thread and only "
        "touches the shared counter now and then"
    ),
)


lesson.md(f"""
On a free threaded build the second number drops to a handful. That build does not bump a shared counter on every allocation, because a shared counter written by every thread is exactly the kind of contention PEP 703 was trying to remove. It counts into a small per thread total first and only pushes into the shared one when that total gets big enough {cite("Python/gc_free_threading.c:2017-2037@v3.15.0rc1#record_allocation")}. Fewer trips to the shared counter means fewer chances to notice the threshold, so the same work schedules far fewer collections.

That is the general lesson of this whole word of bits, stated once: asking is cheap and the answer is late. Every branch that reads it lives in one function, checked in a fixed order, and the whole of `_Py_HandlePending` is short enough to read in one sitting {cite("Python/ceval_gil.c:1356-1395@v3.15.0rc1#_Py_HandlePending")}.
""")


lesson.md(f"""
## A script the process never asked for

The newest bit user is the one that sounds impossible. `sys.remote_exec` takes the process id of some other Python process and the path of a script, and that other process runs the script {cite("Python/sysmodule.c:2469-2497@v3.15.0rc1#sys_remote_exec_impl")}. This is how a debugger attaches to a program that is already running without having been started under the debugger.

There is no magic in it. The caller writes the path into a known spot in the target's memory and sets a bit on the target's eval breaker. The docstring says so in as many words: the script runs on the target's main thread at the next available opportunity, similarly to how signals are handled.

So the same rule applies, across a process boundary this time. If the target is running bytecode the script arrives almost immediately. If the target is inside one long call into C, the script waits for that call to finish, and there is nothing anybody can do about it from the outside.

Most operating systems only allow this between processes owned by the same user, and macOS will not allow it at all without root or a special entitlement, so the cell below prints an honest message on a Mac rather than pretending.
""")


lesson.code(
    """
import pathlib
import subprocess
import tempfile

WAITING = \"\"\"
import time

while True:
    time.sleep(0.02)
\"\"\"


def inject():
    \"\"\"Ask a child process to run a script it never asked for, and time the reply.\"\"\"
    if not sys.executable or not hasattr(sys, "remote_exec"):
        return "this build has no sys.remote_exec, so there is nothing to try"
    note = pathlib.Path(tempfile.mkdtemp()) / "hello.py"
    note.write_text("print('a script the child never imported', flush=True)")
    try:
        child = subprocess.Popen(
            [sys.executable, "-c", WAITING],
            stdout=subprocess.PIPE,
            text=True,
        )
    except OSError:
        return "this build cannot start another process, so there is nothing to try"
    try:
        started = time.perf_counter()
        sys.remote_exec(child.pid, str(note))
        said = child.stdout.readline().strip()
        return f"{said!r} arrived {(time.perf_counter() - started) * 1000:.0f} ms later"
    except PermissionError:
        return "this operating system will not let one process do this to another"
    finally:
        child.kill()
        child.wait()


print(" ", inject())
""",
    varies=(
        "what this prints depends entirely on the operating system, which decides whether one "
        "process may do this to another at all, and the timing on the machines that allow it "
        "is a timing like any other"
    ),
)


lesson.md(f"""
The two recordings below run the real version of that in a container, where it is allowed. Two children, one program each. The first spins in a Python loop, the second calls `sort` once on a list of nine million shuffled integers. Both are asked to print the same line.

{recording(WITH_THE_LOCK)}

{recording(WITHOUT_THE_LOCK)}

Three milliseconds against three seconds, from the same call, on the same machine, a moment apart. The only difference is what the target happened to be doing.

The second recording is the same program on a build with no GIL, and it comes out the same shape. That is the point of running it twice. The eval breaker is easy to file away as part of the GIL, because that is where most people meet it, but the lock is only one of the eight bits. Take the lock away and the other seven still work exactly as before.

{lesson.claim("An injected script arrives about a thousand times later when the target is inside one long call into C than when it is running ordinary bytecode", unobservable="macOS refuses to let one process do this to another without root or a special entitlement, so a reader on a Mac cannot run it at all")}

{lesson.claim("Removing the GIL changes none of this, because the lock is one bit out of eight and the periodic check is what the other seven are waiting for", unobservable="it needs a build configured with --disable-gil, which is not something a reader can switch on in the interpreter they already have")}
""")


lesson.md("""
## Try it yourself

Four things, roughly in order of how much they will teach you.

Take the second cell and replace `list.sort` with something slower, like a regular expression that backtracks badly, and watch the handled-at number follow it. Then try the same thing with `time.sleep`, which is a long C call that does release the GIL, and notice that it still cannot be interrupted early. Releasing the lock and reaching a check are two different things, and this is the cheapest way to feel the difference.

In the third cell, aim the nudge at a thread that is blocked reading from a socket. Nothing happens until the read returns. This is why every "how do I kill a thread in Python" answer on the internet comes with a warning, and now you know precisely which warning.

Run the fifth cell on a free threaded build and compare the number of collections. `uv python install 3.15.0rc1+freethreaded` is one way to get one. The counting scheme changed for a reason that has nothing to do with the collector and everything to do with contention.

Write a tiny script that prints something, start a long running Python program in another terminal, and use `sys.remote_exec` on it. On Linux it usually just works. Once you have seen a process run a file it never imported, `python -m pdb -p` stops looking like magic.

## What you now know

Every thread state has one word called the eval breaker, and eight bits of it are eight unrelated requests: stop, a signal arrived, callbacks are pending, merge reference counts, run the collector, throw away cold JIT traces, drop the lock, raise an exception.

Nothing in that list happens when it is asked for. Setting a bit is one atomic instruction and returns immediately. The work happens at the target thread's next periodic check.

The periodic check is an instruction, not a timer. It is compiled into backward jumps and into the resume at the top of a function, so a thread that never loops and never returns never reaches one.

`JUMP_BACKWARD_NO_INTERRUPT` exists so that `yield from` and `await` chains do not handle an interruption in the wrong generator, and asyncio is full of them.

A Python signal handler is not what the operating system calls. The kernel calls a C function that sets a bit, and your function runs later, always on the main thread, no matter which thread received the signal.

`PyThreadState_SetAsyncExc` leaves an exception on another thread's state and that thread raises it itself, at its next check, once.

`Py_AddPendingCall` leaves a C callback for the main thread of the main interpreter, whoever asked.

The allocator never collects. It sets a bit past the threshold and somebody else does the work, which is why one long C call can allocate a great deal without a single collection running.

And `sys.remote_exec` is the same idea across a process boundary, which is why an injected script can be a thousand times later against a target that is not running bytecode.

## What is next

C06 stays on the free threaded build and looks at what replaced the lock. If two threads may run Python at the same instant, then every container in the standard library needs an answer for what happens when both reach for it, and the answers turn out to be different for a list, a dict and a set. The interesting part is how much of it is not locking at all.
""")


raise SystemExit(lesson.save())
