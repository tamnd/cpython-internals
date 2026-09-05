#!/usr/bin/env python
"""C07. The lock that comes back.

The seventh concurrency lesson, and the one that takes apart an assumption the previous six were
happy to leave standing: that a build either has the GIL or does not, and that is that.

It is not that. `sys._is_gil_enabled()` is a question about right now, not about the binary, and
the answer can change after your program has started. There are four polite ways to change it,
and one rude one, which is importing a compiled module that never said whether it was safe to run
without the lock. That import turns the lock back on for the whole process, permanently, and
prints one warning on its way past.

The second half is the bill. Every atomic count, every shared check and every per thread heap in
C06 is real work on a program with one thread, so the two Tier 1 recordings run eight ordinary
single threaded workloads on both builds and put the numbers next to each other.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording

lesson = Lesson("c07-the-lock-that-comes-back", "c07")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("c07-the-lock-that-comes-back").figure

WITHOUT_THE_LOCK = "c07-what-one-thread-pays"
WITH_THE_LOCK = "c07-what-one-thread-pays-with-the-lock"


lesson.md(f"""
# C07. The lock that comes back

{badge}

Ask most people whether their Python has the GIL and they will answer with a build. It was compiled with the lock or it was compiled without it, and that settles the matter for the life of the process.

It does not settle it. A build compiled without the lock can be running with the lock on, and it can start that way, or arrive there halfway through your program because of a single import. The switch has a counter behind it, turning it on stops every thread in the process, and the most common way it gets turned on is nobody asking for it at all.

The second half of the lesson is the bill for all of this. Everything C06 showed costs something on a program that only ever has one thread, and it is worth knowing how much.

{figure("two-questions-that-sound-like-one", "two columns, was it built without the lock and is the lock on right now")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/ceval_gil.c:1080-1114@v3.15.0rc1`.

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

Most of this lesson runs anywhere, including a browser tab, because most of it is asking the runtime about itself. Two cells want to start a second interpreter and one wants a C compiler, and each of those says so and skips itself when it cannot. You are almost certainly on a build that still has the lock, which is the useful half of the comparison to be standing in.

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
## A build decision and a live setting

Start by separating the two questions that usually get run together.

The first is about the binary. When CPython is configured with `--disable-gil` it defines `Py_GIL_DISABLED`, and that shows up in `sysconfig` and in the {term("abi flags")}, which are the letters that go into the file name of every compiled module the build can load. A free threaded build has a `t` there, an ordinary one has nothing, and the two cannot load each other's modules because they disagree about the shape of every object header.

The second question is about this instant. `sys._is_gil_enabled()` does not read a compile time constant, it reads a field on the running interpreter {cite("Python/sysmodule.c:2658-2675@v3.15.0rc1#sys__is_gil_enabled_impl")}.

{lesson.claim("Whether a build was compiled without the lock and whether the lock is on right now are two separate questions with two separate answers")}
""")


lesson.code(
    """
import sysconfig

SUFFIX = sysconfig.get_config_var("EXT_SUFFIX") or ".so"

print(f"  built without the lock: {bool(sysconfig.get_config_var('Py_GIL_DISABLED'))}")
print(f"  the abi flags on this build: {getattr(sys, 'abiflags', '')!r}")
print(f"  the lock is on right now: {sys._is_gil_enabled()}")
print(f"  compiled modules here have to be named: something{SUFFIX}")
""",
    varies=(
        "the extension suffix names the platform and the interpreter version, so it is different "
        "on every machine, and the abi flags are empty on an ordinary build and t on a free "
        "threaded one"
    ),
)


lesson.md(f"""
On an ordinary build the first line is False and the third is True, and there is no way to change either of them. On a free threaded build the first is True and the third starts as False and is up for grabs.

## Four ways to ask for the other one

There are exactly four ways to say something about the lock before a program starts: `-X gil=1`, `-X gil=0`, and the same two as `PYTHON_GIL` in the environment. They are read in one place during startup {cite("Python/initconfig.c:1971-2000@v3.15.0rc1#config_read_gil")}, and the command line wins over the environment.

The interesting case is what an ordinary build does with `-X gil=0`. It could ignore it, or warn, or pretend. It does none of those. It refuses to start, with a fatal error, which is a much better answer than any of the alternatives: if your program is asking to run without the lock, quietly giving it the lock means quietly giving it wrong assumptions.

The next cell starts five child interpreters and asks each one the same question. It needs to start a process, so it skips itself in a browser tab.

{lesson.claim("A build that has the lock refuses to start at all when asked to run without it, rather than ignoring the request")}
""")


lesson.code(
    """
import os
import subprocess

ASK = "import sys; print(sys._is_gil_enabled())"


def child(args=(), env=None):
    \"\"\"Start a fresh interpreter with these arguments and ask it about the lock.\"\"\"
    room = dict(os.environ)
    room.pop("PYTHON_GIL", None)
    if env:
        room.update(env)
    try:
        done = subprocess.run(
            [sys.executable, *args, "-c", ASK],
            capture_output=True,
            text=True,
            env=room,
            timeout=60,
        )
    except OSError:
        return "this runtime cannot start another process"
    if done.returncode:
        said = done.stderr.strip().splitlines() or ["no message"]
        return f"refused: {said[0]}"
    return f"the lock is on: {done.stdout.strip()}"


if not sys.executable:
    print("  there is no interpreter to start here, so there is nothing to ask")
else:
    for label, answer in [
        ("plain", child()),
        ("with -X gil=1", child(["-X", "gil=1"])),
        ("with -X gil=0", child(["-X", "gil=0"])),
        ("with PYTHON_GIL=1", child(env={"PYTHON_GIL": "1"})),
        ("with PYTHON_GIL=0", child(env={"PYTHON_GIL": "0"})),
    ]:
        print(f"  {label:18} {answer}")
""",
    varies=(
        "an ordinary build refuses the two requests to drop the lock and a free threaded build "
        "honours all four, and the exact wording of the refusal comes from the runtime"
    ),
)


lesson.md(f"""
{figure("four-ways-to-ask-for-the-other-one", "a table of five ways of asking and what each one does on each of the two builds")}

{lesson.claim("On a free threaded build all four requests are honoured, so the same binary can be started with the lock on or off", unobservable="it needs an interpreter configured with --disable-gil, which is a separate build rather than a flag you can turn on in the one you already have")}

## The import that turns it back on

Now the part nobody asks for.

An extension module is a shared library with an init function in it. When you import one, CPython loads the library and calls that function, and the function can do anything: allocate, call back into Python, keep global state. If the module was written in 2015 it was written for a world with one big lock, and it may well be keeping global state that two threads would corrupt.

The trouble is that CPython cannot ask until after it has run the init function, because the answer is something the init function provides. So it does the safe thing in the wrong order. Before the library is loaded it turns the lock on {cite("Python/ceval_gil.c:1080-1114@v3.15.0rc1#_PyEval_EnableGILTransient")}, which is a {term("transient GIL")}: on for now, meant to come off again. Then it runs the init function, and only then asks the module what it thinks {cite("Python/import.c:1618-1643@v3.15.0rc1#_PyImport_CheckGILForModule")}.

If the module declared that it does not need the lock, the transient enable is undone and everything carries on {cite("Python/ceval_gil.c:1152-1180@v3.15.0rc1#_PyEval_DisableGIL")}. If it said nothing, the enable is made permanent and a warning goes out naming the module {cite("Python/import.c:1645-1660@v3.15.0rc1#_PyImport_EnableGILAndWarn")} {cite("Python/ceval_gil.c:1132-1150@v3.15.0rc1#_PyEval_EnableGILPermanent")}.

{figure("what-an-import-does-to-the-lock", "five steps from turning the lock on to keeping it on and warning")}

The next cell writes the smallest extension module that will compile, builds it, and imports it. Two lines of real content: a module definition and an init function. It is old fashioned only in what it does not say.

{lesson.claim("On a build that has the lock, importing an extension that says nothing about threads changes nothing and produces no warning")}
""")


lesson.code(
    """
import tempfile
import warnings

SOURCE = \"\"\"
#include <Python.h>

static struct PyModuleDef mod = {
    PyModuleDef_HEAD_INIT, "oldstyle", NULL, -1, NULL, NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC
PyInit_oldstyle(void)
{
    return PyModule_Create(&mod);
}
\"\"\"


def compile_it():
    \"\"\"Build the smallest extension that will compile, and say where it landed.\"\"\"
    work = tempfile.mkdtemp()
    source = os.path.join(work, "oldstyle.c")
    with open(source, "w") as handle:
        handle.write(SOURCE)
    line = (sysconfig.get_config_var("CC") or "cc").split()
    line += ["-shared", "-fPIC"]
    if sys.platform == "darwin":
        line += ["-undefined", "dynamic_lookup"]
    line += ["-I", sysconfig.get_path("include"), source]
    line += ["-o", os.path.join(work, "oldstyle" + SUFFIX)]
    try:
        done = subprocess.run(line, capture_output=True, text=True, timeout=180)
    except OSError:
        return None
    return None if done.returncode else work


built = compile_it() if sys.executable else None
if built is None:
    print("  no working compiler here, so there is nothing to build and import")
else:
    sys.path.insert(0, built)
    print(f"  before the import, the lock is on: {sys._is_gil_enabled()}")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        import oldstyle  # noqa: F401
    print(f"  warnings the import produced: {len(caught)}")
    for one in caught:
        print(f"    {one.message}")
    print(f"  after the import, the lock is on: {sys._is_gil_enabled()}")
""",
    varies=(
        "the cell needs a C compiler and the headers for this interpreter, and says so and skips "
        "itself when either is missing, and on a build that has the lock nothing changes while on "
        "a free threaded build the import prints a warning and flips the last line to True"
    ),
)


lesson.md(f"""
On a free threaded build the warning reads: the global interpreter lock has been enabled to load module `oldstyle`, which has not declared that it can run safely without the GIL. The last line comes back True, and it stays True. There is no way to undo it from Python.

{lesson.claim("Importing one compiled module that has not declared itself safe turns the lock on for the rest of the process, on a build that started without it", unobservable="the flip only happens on an interpreter configured with --disable-gil, and this notebook cannot become one")}

Turning it on is not a cheap flag flip either. The counter behind it starts at zero, and going from zero to one has to {term("stop the world")}: the calling thread detaches, every other thread is brought to a halt, the counter goes up, and everything starts again {cite("Python/ceval_gil.c:1105-1130@v3.15.0rc1#_PyThreadState_Attach")}. A permanent enable sets the counter to `INT_MAX` so that no later import can ever bring it back down.

{figure("the-counter-behind-the-switch", "a table of the three values the enabled counter can hold and what each means")}

## Who has to declare anything

The declaration itself is one slot in the module's slot table: `Py_mod_gil` set to `Py_MOD_GIL_NOT_USED` {cite("Include/moduleobject.h:85-89@v3.15.0rc1#Py_MOD_GIL_NOT_USED")}. That is the whole {term("thread safety declaration")}. It is a promise by the author, not something the runtime checks, and there is nothing stopping anyone from making it wrongly.

Saying nothing is not neutral, and that asymmetry is the design. A module written before free threading existed could not have said anything, so silence has to mean the cautious answer.

Which raises a fair question: how much of what you already imported would this catch? Not as much as you might think, because most of the standard library that looks like C is compiled straight into the binary rather than loaded as a separate library, and nothing built in has to declare anything.

{lesson.claim("Most of what a fresh interpreter has loaded is built into the binary rather than being a separate shared library that would have to declare itself")}
""")


lesson.code(
    """
compiled = []
frozen = []
for name, module in sorted(sys.modules.items()):
    origin = getattr(getattr(module, "__spec__", None), "origin", None)
    if origin and origin.endswith(SUFFIX):
        compiled.append(name)
    elif origin in ("built-in", "frozen"):
        frozen.append(name)

print(f"  modules loaded right now: {len(sys.modules)}")
print(f"  built into the binary, so nothing to declare: {len(frozen)}")
print(f"  separate libraries, each of which has to declare: {len(compiled)}")
print(f"  the first few of those: {', '.join(compiled[:6]) or 'none'}")
""",
    varies=(
        "how many modules are loaded depends on the runtime and on what imported this notebook, "
        "and a browser build has almost everything compiled in"
    ),
)


lesson.md(f"""
The count that matters is the third one, and in a plain interpreter it is small. It gets much larger the moment you import numpy or anything that ships wheels, which is why the free threading rollout has been mostly a packaging problem rather than a CPython one.

## What it costs when you only have one thread

Now the bill.

None of C06 was free. A reference count that used to be a plain add is an atomic one. Containers check whether they are shared. The object allocator was swapped out, because pymalloc's shared pools are only safe when one thread runs at a time, so a free threaded build uses {term("mimalloc")} with a heap per thread instead {cite("Objects/obmalloc.c:428-443@v3.15.0rc1#PYOBJ_ALLOC")}. That swap is not optional: building without the lock and without mimalloc is a compile error {cite("Objects/obmalloc.c:28-32@v3.15.0rc1#WITH_MIMALLOC")}.

A program with one thread pays for all of it and gets nothing back. So the two recordings below run eight ordinary single threaded workloads, nothing shared and nothing concurrent, on the two builds. Same program, same image pipeline, same four core container.

{recording(WITHOUT_THE_LOCK)}

{recording(WITH_THE_LOCK)}

{figure("eight-workloads-on-one-thread", "bars of how long each of eight workloads took without the lock against the same workload with it")}

The answer is not one number, which is the honest version of it. Recursion, attribute reads, calls and sorting are slower without the lock, by somewhere between a tenth and a half. That is the atomic counting showing up exactly where you would expect: in the code that touches the most objects per unit of work.

The two that go the other way are the surprise, and they are both about making things rather than reading them. Three hundred thousand list appends were three times faster without the lock, and a hundred thousand f-strings were a third faster. Neither of those has anything to do with threads. That is mimalloc against pymalloc, in a benchmark where allocation is most of the work.

{lesson.claim("A build with no lock is somewhat slower on single threaded work that touches many objects, and faster on work dominated by allocation, because removing the lock also changed the allocator", unobservable="it takes two builds of the same source with the same optimisation flags on the same hardware, and one interpreter cannot be both of them")}

{figure("the-allocator-underneath", "two columns, the object allocator each of the two builds uses and what follows from it")}

So the cost is real but it is not a wall, and part of what looks like the cost of free threading is really the cost of the allocator that came with it.
""")


lesson.md("""
## Try it yourself

Four things, roughly in order of how much they will teach you.

Get a free threaded build and run this whole notebook on it. `uv python install 3.15.0rc1+freethreaded` is one way. Every cell in this lesson prints a different story on it, and the third one prints the warning that is the point of the whole lesson.

On that build, add `Py_mod_gil` to the module in the third cell and watch the warning go away. It means switching to a multi phase init with a slot table, which is about fifteen more lines of C, and it is the exact change every extension author has had to make.

Run the third cell twice in the same session on a free threaded build. The second import is a no op, because the module is already in `sys.modules`, so the lock does not get enabled twice. Then try importing a second module that also says nothing, and notice that the counter is already at its maximum.

Take the eight workloads out of the recordings and run them on your own machine on both builds. The ratios move, sometimes a lot, and finding out which way they move on your hardware is more useful than trusting the bars above.

## What you now know

Whether a build was compiled without the lock and whether the lock is on right now are two different questions. `sysconfig` answers the first, `sys._is_gil_enabled()` answers the second, and the second can change while your program runs.

The abi flags carry a `t` on a free threaded build, and that letter goes into the file name of every compiled module, which is what keeps the two kinds of build from loading each other's wheels.

There are four ways to ask for a lock state at startup, two on the command line and two in the environment. An ordinary build refuses outright when asked to drop the lock, rather than ignoring the request.

Importing an extension module turns the lock on before running its init function, because the runtime cannot ask whether the module is safe until after that function has run.

If the module declared `Py_mod_gil` as not used, the lock goes off again. If it said nothing, the lock stays on for the rest of the process and a warning names the module.

Saying nothing is not neutral. It is read as asking for the lock, because a module written before free threading existed had no way to say anything.

The lock is a counter rather than a flag, and raising it from zero has to stop every thread in the process first.

Removing the lock also forced a change of object allocator, from pymalloc to mimalloc with a heap per thread. That is why single threaded allocation heavy code can be faster on a free threaded build even though most other code is a little slower.

## What is next

C08 closes the concurrency run by putting the two halves together. Everything so far has been one interpreter with several threads in it. The other shape is several interpreters in one process, each with its own state and no shared objects at all, which is what `concurrent.interpreters` gives you. That is a different answer to the same problem, it has been in the tree far longer than free threading has, and the two of them make very different trades.
""")


raise SystemExit(lesson.save())
