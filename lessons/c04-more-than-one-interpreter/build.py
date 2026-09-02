#!/usr/bin/env python
"""C04. More than one interpreter in one process.

The fourth concurrency lesson, and the first one that stops assuming a process has exactly one
interpreter in it. C01 measured the GIL, C02 measured what it protects, and C03 showed that a
thread is a struct on a list hanging off the interpreter. This lesson goes one level up and
finds that the interpreter is a struct on a list too, hanging off the runtime.

Once you can see that list, the rest is a tour of what changes when it has more than one entry.
Each interpreter gets a GIL of its own, so the switch interval stops being a global setting.
Almost nothing is shared, and the small set that is turns out to be exactly the immortal
objects from M05. Values cross between interpreters as copies, through a queue that neither of
them owns. And a subinterpreter refuses a handful of things the main one allows, every refusal
tracing back to one field in a config struct that fits on a screen.

The last section is the one M8 exists for: the same four jobs, in four threads either way, with
one interpreter and with four, recorded on a build that has a GIL and a build that does not.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording

lesson = Lesson("c04-more-than-one-interpreter", "c04")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("c04-more-than-one-interpreter").figure

WITH_THE_LOCK = "c04-four-cores-with-the-lock"
WITHOUT_THE_LOCK = "c04-four-cores-without-the-lock"


lesson.md(f"""
# C04. More than one interpreter in one process

{badge}

Three lessons in a row have talked about threads sharing one interpreter, and none of them ever questioned the "one". A process runs one Python, that Python has one GIL, one `sys.modules`, one set of objects, and threads take turns inside it.

That has not been true for a while. A process can hold several interpreters at once, each with its own lock, its own modules and its own objects, all in the same address space and all reachable from ordinary Python.

{figure("two-ways-to-arrange-four-threads", "four threads under one interpreter on the left and four threads under four interpreters on the right")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/pystate.c:2650-2669@v3.15.0rc1`.

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

Every cell in this lesson needs to make a second interpreter, and not every runtime will let you. A browser tab in particular will not. The first cell checks once, and the rest of them look at that answer and say so rather than printing nonsense. In Colab or from a checkout, everything runs.

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
## The list one level up

C03 ended on a list. Every thread has a {term("thread state")}, and the interpreter keeps them all on a linked list with the newest at the front.

The same shape appears one level up. Every interpreter has an {term("interpreter state")}, and the runtime keeps them all on a linked list with the newest at the front {cite("Include/internal/pycore_runtime_structs.h:184-201@v3.15.0rc1#pyinterpreters")}. That struct is four fields: a mutex, the head of the list, a separate pointer to the main interpreter, and the counter that hands out ids. The comment in the source says "newest first" out loud.

{figure("the-interpreter-list", "the runtime's head pointer and three interpreters chained by their next pointers, newest first")}

So there are three levels now, not two, and the fields you have already met sort themselves out between them.

{figure("who-owns-what", "five fields, which of the runtime, an interpreter or a thread each one hangs off, and how many exist")}

Walking the interpreter list needs the same trick C03 used for the thread list. The functions are public C API, so `ctypes` can call them without a debugger and without a C compiler {cite("Python/pystate.c:2650-2669@v3.15.0rc1#PyInterpreterState_Head")}. There is a comment right above the first one, credited to David Beazley, telling you not to use it unless you know what you are doing. Reading it is fine.

Each interpreter has an id, handed out by that counter {cite("Python/pystate.c:1294-1302@v3.15.0rc1#PyInterpreterState_GetID")}, and each one has its own thread list, reached by the same call C03 used {cite("Python/pystate.c:2671-2679@v3.15.0rc1#PyInterpreterState_ThreadHead")}. Nesting one walk inside the other gives you the whole picture of the process in about twenty lines.

Making an interpreter from Python is one call in the standard library {cite("Lib/concurrent/interpreters/__init__.py:63-66@v3.15.0rc1#create")}. The cell below makes two, runs something in one of them, and closes them, printing the list at each step.

{lesson.claim("The runtime keeps its interpreters on a linked list with the newest first, each interpreter has its own list of thread states, and both lists shrink again when the interpreters are closed")}
""")


lesson.code(
    """
import ctypes
import threading

api = ctypes.pythonapi
ONE_ONLY = "  this build can only ever have one interpreter, so there is nothing more to see"


def ask(name, args, result):
    \"\"\"Point ctypes at one C API function. Every one used here is public and documented.\"\"\"
    fn = getattr(api, name)
    fn.argtypes = args
    fn.restype = result
    return fn


first_interp = ask("PyInterpreterState_Head", [], ctypes.c_void_p)
next_interp = ask("PyInterpreterState_Next", [ctypes.c_void_p], ctypes.c_void_p)
main_interp = ask("PyInterpreterState_Main", [], ctypes.c_void_p)
interp_id = ask("PyInterpreterState_GetID", [ctypes.c_void_p], ctypes.c_int64)
first_state = ask("PyInterpreterState_ThreadHead", [ctypes.c_void_p], ctypes.c_void_p)
next_state = ask("PyThreadState_Next", [ctypes.c_void_p], ctypes.c_void_p)
state_id = ask("PyThreadState_GetID", [ctypes.c_void_p], ctypes.c_uint64)


def walk():
    \"\"\"Follow the runtime's list of interpreters, and each interpreter's list of threads.\"\"\"
    found = []
    interp = first_interp()
    while interp:
        threads = []
        state = first_state(interp)
        while state:
            threads.append(state_id(state))
            state = next_state(state)
        found.append((interp_id(interp), threads))
        interp = next_interp(interp)
    return found


def second_one_works():
    \"\"\"Some runtimes refuse to make a second interpreter. A browser tab is one of them.\"\"\"
    try:
        import concurrent.interpreters as maybe

        probe = maybe.create()
        probe.close()
    except Exception:
        return False
    return True


MORE_THAN_ONE = second_one_works()

print("  the main interpreter sits at", hex(main_interp()))
print("  what the runtime has right now:", walk())
if not MORE_THAN_ONE:
    print(ONE_ONLY)
else:
    import concurrent.interpreters as ci

    kids = [ci.create(), ci.create()]
    print("  after making two more:        ", walk())
    stop, ready = ci.create_queue(), ci.create_queue()
    kids[0].prepare_main(stop=stop, ready=ready)
    busy = threading.Thread(target=kids[0].exec, args=("ready.put(1)\\nstop.get()\\n",))
    busy.start()
    ready.get()
    print("  while one of them is running: ", walk())
    stop.put(1)
    busy.join()
    for kid in kids:
        kid.close()
    print("  after closing both:          ", walk())
""",
    varies=(
        "the address is wherever this process happened to put the main interpreter, and the "
        "thread state ids depend on how many threads the runtime has already started, but the "
        "shape of the list and the order of the ids are the same everywhere"
    ),
)


lesson.md(f"""
Two things in that output are worth a second look.

The ids of the new interpreters count up and never come back, the same way thread state ids did in C03. Closing an interpreter does not free its id for reuse.

The thread state ids do come back, though, because they are handed out per interpreter rather than per process. A brand new interpreter starts counting at one again, so the same thread state id can name a thread in interpreter 0 and a different thread in interpreter 2 at the same moment. If you want something unique across the whole process you need the pair.

## Each one gets its own lock

Here is the part that makes the rest of the lesson possible.

The {term("GIL")} is not a global variable. It hangs off the interpreter, in a small struct called `_ceval_state` that also carries the flag saying whether this interpreter owns its lock or borrows the main one {cite("Include/internal/pycore_interp_structs.h:107-116@v3.15.0rc1#_ceval_state")}. Startup looks at that flag and either points the interpreter at the main lock or builds it a fresh one {cite("Python/ceval_gil.c:502-520@v3.15.0rc1#_PyEval_InitGIL")}. Building a fresh one is a handful of lines, and the last of them sets the {term("switch interval")} to the default five milliseconds {cite("Python/ceval_gil.c:480-500@v3.15.0rc1#init_own_gil")}.

Which means the switch interval is per interpreter as well, because it is a field on the lock, and the lock belongs to the interpreter {cite("Python/ceval_gil.c:424-438@v3.15.0rc1#_PyEval_SetSwitchInterval")}. C01 spent a whole section turning that dial. It turns out the dial you were turning was never the process's.

Whether an interpreter gets its own lock is a choice made when it is created, and there are three options: inherit the main one, take one of your own, or leave it to the runtime to decide {cite("Include/cpython/pylifecycle.h:40-64@v3.15.0rc1#_PyInterpreterConfig_INIT")}. `concurrent.interpreters` always asks for its own. The cell below proves it without timing anything at all: set the interval in one interpreter and read it back in the other.

{lesson.claim("Each interpreter created by concurrent.interpreters has a GIL of its own, so sys.setswitchinterval in one of them does not change the value the other one reads")}
""")


lesson.code(
    """
if not MORE_THAN_ONE:
    print(ONE_ONLY)
else:
    post = ci.create_queue()
    kid = ci.create()
    kid.prepare_main(post=post)

    def kid_interval():
        kid.exec("import sys; post.put(sys.getswitchinterval())")
        return post.get()

    was = sys.getswitchinterval()
    print("  both start at the default:  main", was, " the kid", kid_interval())
    sys.setswitchinterval(0.25)
    print("  main sets its own to 0.25:  main", sys.getswitchinterval(), " the kid", kid_interval())
    kid.exec("import sys; sys.setswitchinterval(0.001)")
    print("  the kid sets its own:       main", sys.getswitchinterval(), " the kid", kid_interval())
    sys.setswitchinterval(was)
    kid.close()
""",
    varies=(
        "the default is five milliseconds on a stock build but a runtime is free to start "
        "somewhere else, and the point is that the two columns move independently rather than "
        "what either of them starts at"
    ),
)


lesson.md(f"""
Two locks, two intervals, one process. That is the whole idea, and everything below is a consequence of it.

## What they still share

Two interpreters in one process share an address space, so the question is not whether they can see each other's memory. They can. The question is which objects there is only one of.

The rule is written down in a header, and it is short: only immutable objects may be runtime global, everything else has to be per interpreter {cite("Include/internal/pycore_global_objects.h:12-28@v3.15.0rc1#_Py_GLOBAL_OBJECT")}. The set that qualifies is fixed at build time and is smaller than you would guess: the small ints from -5 up to 1024, the empty bytes and every one byte bytes object, a table of short strings, the empty tuple, and the singletons {cite("Include/internal/pycore_runtime_structs.h:96-125@v3.15.0rc1#_Py_static_objects")}.

If that list sounds familiar it is because M05 already gave it a name. Those are the {term("immortal object")}s, the ones whose reference count is never touched. The reason is now visible: an object shared by two interpreters cannot have a count that either of them is allowed to change, so the only objects that can be shared are the ones nobody counts.

{figure("shared-or-a-copy", "the objects that exist once per process on the left and the ones that exist once per interpreter on the right")}

The cell asks for the address of the same expression in both interpreters and prints them side by side.

{lesson.claim("The singletons, the small ints, the one character strings and the built in types have one address in both interpreters, and everything else including sys has a different address in each")}
""")


lesson.code(
    """
CASES = [
    ("None", "None"),
    ("the empty tuple", "()"),
    ("42, a small int", "42"),
    ("1000, still small", "1000"),
    ("999983, not small", "999983"),
    ('"x", one character', '"x"'),
    ('"cpython internals"', '"cpython internals"'),
    ("the str type", "str"),
    ("the sys module", "__import__('sys')"),
    ("a fresh list", "[]"),
]

if not MORE_THAN_ONE:
    print(ONE_ONLY)
else:
    post = ci.create_queue()
    kid = ci.create()
    kid.prepare_main(post=post)
    for _, expr in CASES:
        kid.exec(f"post.put(id({expr}))")
    print(f"  {'the object':22}{'here':>14}{'in the kid':>14}   the same one?")
    for label, expr in CASES:
        mine, theirs = id(eval(expr)), post.get()
        print(f"  {label:22}{mine:>14}{theirs:>14}   {mine == theirs}")
    kid.close()
""",
    varies=(
        "every address is wherever this process put the object, and how wide the numbers are "
        "depends on the build, but which rows say True is the same on every build that can make "
        "a second interpreter"
    ),
)


lesson.md(f"""
The row for 1000 is the one to watch. It is inside the small int cache on a default build, so both interpreters get the same object. On a {term("free threaded build")} the cache is wider, which moves the boundary rather than removing it. Either way there is a boundary, and 999983 is past it.

## Getting a value across

If almost nothing is shared, passing something between interpreters cannot mean passing a pointer. It means copying.

The runtime knows how to copy a small set of types on its own, and the registration list is right there in one function: `None`, `int`, `bytes`, `str`, `bool`, `float`, and tuples as a fallback, with a comment noting that code objects and functions are deliberately not in the list {cite("Python/crossinterp_data_lookup.h:790-829@v3.15.0rc1#_register_builtins_for_crossinterpreter_data")}. An object of one of those types is a {term("shareable object")}, and you can ask about any object directly {cite("Modules/_interpretersmodule.c:1330-1348@v3.15.0rc1#is_shareable")}.

A queue is more relaxed than that, because it can fall back to pickling, so a list will go across. But going across means being taken apart on the way in and built again on the way out, and what comes out the other side is a different object.

{figure("across-the-gap", "a list turned into bytes on the way into a queue and built again as a new object on the way out")}

That is not a limitation of the queue, it is the point. If the receiving interpreter got a pointer to your list, two interpreters with two locks would be mutating one object with neither lock helping.

{lesson.claim("A queue moves a list between interpreters as a copy, so the object on the other side has a different address and changes made to it are not visible back here")}
""")


lesson.code(
    """
if not MORE_THAN_ONE:
    print(ONE_ONLY)
else:
    print("  what the runtime knows how to hand across on its own:")
    for thing in [None, 42, "a string", b"bytes", 1.5, (1, 2), [], {}, sys]:
        print(f"    {type(thing).__name__:10} {ci.is_shareable(thing)}")

    post = ci.create_queue()
    kid = ci.create()
    kid.prepare_main(post=post)
    mine = [1, 2, 3]
    post.put(mine)
    kid.exec(\"\"\"
got = post.get()
got.append("added by the kid")
post.put((id(got), tuple(got)))
\"\"\")
    there, contents = post.get()
    print()
    print("  the list here is at", id(mine), "and in the kid it is at", there)
    print("  the kid appended to what it got:", contents)
    print("  the list here has not changed:  ", mine)
    try:
        post.put(sys)
        print("  a module went across")
    except ci.NotShareableError:
        print("  a module will not go across at all, not even as a copy")
    kid.close()
""",
    varies=(
        "the two addresses are wherever the two interpreters put their copies, and they are "
        "different numbers on every run, while the True and False column and the last three "
        "lines are the same everywhere"
    ),
)


lesson.md(f"""
## What a subinterpreter is not allowed to do

A {term("subinterpreter")} is not just a second interpreter, it is a second interpreter created with a particular config, and the config is a struct with seven fields in it {cite("Include/cpython/pylifecycle.h:44-53@v3.15.0rc1#PyInterpreterConfig")}. Six of them are flags. `concurrent.interpreters` uses the strictest preset there is, and every refusal you can get out of a subinterpreter traces back to one of those flags being zero.

{figure("the-isolated-config", "the seven settings in the isolated config and the operation each one turns off")}

The flags are stored on the interpreter as a bit field {cite("Include/internal/pycore_interp.h:84-97@v3.15.0rc1#Py_RTFLAGS_FORK")}, and the code that says no reads a bit and raises. Daemon threads are checked in the thread module {cite("Modules/_threadmodule.c:1877-1887@v3.15.0rc1#thread_daemon_threads_allowed")}, and the message you see comes from `threading.py` on the way in {cite("Lib/threading.py:1061-1070@v3.15.0rc1#daemon")}. `os.fork` reads a different bit in the same field {cite("Modules/posixmodule.c:8660-8672@v3.15.0rc1#fork")}, and `os.execv` reads another.

Imports are the interesting one. A C extension has to say whether it can cope with more than one interpreter, and the import machinery refuses the ones that have not said so {cite("Python/import.c:1604-1616@v3.15.0rc1#_PyImport_CheckSubinterpIncompatibleExtensionAllowed")}. Saying so means a slot in the module definition {cite("Include/moduleobject.h:78-89@v3.15.0rc1#Py_MOD_PER_INTERPRETER_GIL_SUPPORTED")}, right next to the free threading slot C02 was about. A module that still uses the old single phase init cannot say anything at all, and `readline` is one of those, which is why it is the easy example {cite("Modules/readline.c:1620-1645@v3.15.0rc1#readlinemodule")}.

The cell tries six things inside a subinterpreter and reports what came back.

{lesson.claim("Inside a subinterpreter an ordinary thread and a nested interpreter are allowed, while a daemon thread, os.fork, os.execv and importing readline all raise")}
""")


lesson.code(
    """
TRIES = {
    "start an ordinary thread": "import threading\\nthreading.Thread(target=int).start()",
    "start a daemon thread": "import threading\\nthreading.Thread(target=int, daemon=True).start()",
    "call os.fork": "import os\\nos.fork()",
    "call os.execv": "import os\\nos.execv('/bin/true', ['/bin/true'])",
    "import readline": "import readline",
    "make another interpreter": "import concurrent.interpreters as c\\nc.create().close()",
}

if not MORE_THAN_ONE:
    print(ONE_ONLY)
else:
    post = ci.create_queue()
    kid = ci.create()
    kid.prepare_main(post=post)
    for label, code in TRIES.items():
        body = "".join(f"    {line}\\n" for line in code.split("\\n"))
        kid.exec(
            "try:\\n"
            + body
            + '    post.put("allowed")\\n'
            + "except BaseException as exc:\\n"
            + '    post.put(type(exc).__name__ + ": " + str(exc)[:52])\\n'
        )
        print(f"  {label:26} {post.get()}")
    kid.close()
""",
    varies=(
        "the exact wording of each message can change between releases and the fork and exec "
        "rows depend on the platform having those calls at all, but which rows are allowed and "
        "which are refused is the same on any build that can make a second interpreter"
    ),
)


lesson.md(f"""
Notice the last row. A subinterpreter can make another subinterpreter, and that one is a sibling on the runtime's list rather than a child. There is only ever one list.

## What it actually buys

Everything so far has been about isolation. This section is about the reason anyone puts up with it.

Four jobs that do nothing but count, run in four threads. On a default build those four threads take turns holding one lock, so they finish in roughly the time one thread would have taken. Give each job its own interpreter and the four threads hold four different locks, so they can run at once.

The comparison has to be done carefully. It is tempting to time four threads against one thread and call the difference the cost of the GIL, but that is not a fair test, because an operating system does not schedule a lone thread the way it schedules four. On this laptop a single threaded baseline can come out slower than a two threaded one, which is nonsense, and the reason is core placement rather than anything in Python. Both sides of the cell below use four operating system threads. The only thing that changes is how many interpreters those threads are running in.

{lesson.claim("Four counting jobs in four threads and four interpreters finish in noticeably less wall time than the same four jobs in four threads and one interpreter, on a build that has a GIL")}
""")


lesson.code(
    """
import time

JOBS = 4
SPIN = "n = 3000000\\nwhile n:\\n    n -= 1\\n"
BLOB = compile(SPIN, "<spin>", "exec")


def in_threads():
    \"\"\"Four jobs, four operating system threads, all of them in this interpreter.\"\"\"
    hands = [threading.Thread(target=exec, args=(BLOB, {})) for _ in range(JOBS)]
    for hand in hands:
        hand.start()
    for hand in hands:
        hand.join()


def in_interpreters(kids):
    \"\"\"The same four jobs and the same four threads, one interpreter each.\"\"\"
    hands = [threading.Thread(target=kid.exec, args=(SPIN,)) for kid in kids]
    for hand in hands:
        hand.start()
    for hand in hands:
        hand.join()


def best(work, rounds=5):
    seen = []
    for _ in range(rounds):
        started = time.perf_counter()
        work()
        seen.append(time.perf_counter() - started)
    return min(seen)


if not MORE_THAN_ONE:
    print(ONE_ONLY)
else:
    crew = [ci.create() for _ in range(JOBS)]
    in_threads()
    in_interpreters(crew)
    together = best(in_threads)
    apart = best(lambda: in_interpreters(crew))
    for kid in crew:
        kid.close()
    print(f"  {JOBS} jobs, {JOBS} threads, one interpreter   {together * 1000:7.0f} ms")
    print(f"  {JOBS} jobs, {JOBS} threads, {JOBS} interpreters   {apart * 1000:7.0f} ms")
    print(f"  the second arrangement finished {together / apart:.2f} times faster")
    print(f"  the lock is on here: {sys._is_gil_enabled()}")
""",
    varies=(
        "both timings depend on the machine and on how many cores it is willing to give this "
        "process, so the milliseconds move a lot from run to run, and the ratio depends on "
        "whether the build has a GIL at all"
    ),
)


lesson.md(f"""
A laptop is a poor place to measure that, because the operating system keeps moving the work between cores of different speeds. The two recordings below run the same program in a fixed container with four cores, once on a build with a GIL and once on a build without one. The ratio is what matters, and the two ratios are the point of this lesson.

{recording(WITH_THE_LOCK)}

{recording(WITHOUT_THE_LOCK)}

Two ways to use four cores from one Python process, and the recordings show them side by side. Give each job its own interpreter and you get about twice the throughput on a build that has a GIL. Take the GIL away instead and the extra interpreters buy almost nothing, because four threads in one interpreter were already running at once. The startup that decides which of those two worlds you are in is one line, reading one flag {cite("Python/pylifecycle.c:638-653@v3.15.0rc1#init_interp_create_gil")}.

{lesson.claim("On a free threaded build the same two arrangements land close together, because four threads in one interpreter were already running on four cores", unobservable="it needs a build configured with --disable-gil, which is not something a reader can switch on in the interpreter they already have")}
""")


lesson.md("""
## Try it yourself

Four things, roughly in order of how much they will teach you.

Run the last cell on a free threaded build if you can get one, and compare your ratio with the recordings. `uv python install 3.15.0rc1+freethreaded` is one way. Seeing the same script give two different answers on two builds of the same version is the fastest way to understand what the GIL was costing.

In the first cell, start a thread inside the subinterpreter instead of running `exec` from the main thread, and walk the list while both are alive. You will see thread state ids in two different interpreters that happen to be the same number. That is the per interpreter counter, and it is a good reason not to use those ids as a key.

Put a dict on the queue instead of a list. It goes across, because the queue can pickle it. Now put something that cannot be pickled, like an open file, and read the error. The line between what crosses and what does not is not the same line as `is_shareable`, and it is worth seeing both.

Import a third party C extension inside a subinterpreter. Many of them fail, and the message tells you which stage refused. That message is the single best way to find out whether a package you depend on is ready for any of this.

## What you now know

A process can hold more than one interpreter. They live on a linked list hanging off the runtime, newest first, exactly like the thread states hang off an interpreter, and you can walk both lists from Python with public C API calls.

Interpreter ids count up across the process and are never reused. Thread state ids count up per interpreter, so they repeat.

The GIL is a field on the interpreter, not a global. So is the switch interval, which means `sys.setswitchinterval` was always a per interpreter setting and you had no way to tell until now.

Almost nothing is shared. The objects that exist once per process are exactly the immortal ones from M05, and that is not a coincidence: an object with no reference count is the only kind two interpreters can safely both point at.

Values cross as copies. A small set of types the runtime knows natively, anything picklable through a queue, and the object on the other side is a different object at a different address.

A subinterpreter refuses daemon threads, `fork`, `exec` and C extensions that have not opted in. Every one of those refusals is one flag in a config struct with seven fields.

And the payoff is real but conditional. Four interpreters run four counting jobs about twice as fast as one interpreter does on a build with a GIL, and buy almost nothing on a build without one.

## What is next

C05 goes back down to a single thread and looks at the one word that lets anything interrupt it. C01 named it in passing, the eval breaker, and then went back to timing the lock. It turns out to be how Ctrl-C works, how the garbage collector gets a turn, how one thread throws an exception into another, and how a debugger in a completely different process can make this one run a script. All of that is eight bits and one check in the eval loop.
""")


raise SystemExit(lesson.save())
