#!/usr/bin/env python
"""C08. Sending work to another interpreter.

The last concurrency lesson, and the practical half of C04. C04 built a second interpreter and
showed that almost nothing is shared between it and the first one. This one asks the question
that follows: if nothing is shared, how do you give it a job, and what does the handover cost?

The answers are more interesting than they sound. A function can only cross if it reads no
globals. A lambda cannot be pickled and crosses anyway, which means there is a third route
nobody talks about. An exception raised over there does not come back, a snapshot of it does.
And a queue is fast enough for small values and slow enough for big ones that the shape of your
workload, not the number of your cores, decides whether any of this is worth doing.

The two Tier 1 recordings split two workloads three ways on both builds, which is what turns the
last point from an opinion into a table.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording

lesson = Lesson("c08-sending-work-to-another-interpreter", "c08")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("c08-sending-work-to-another-interpreter").figure

WITH_THE_LOCK = "c08-three-ways-to-split-the-work"
WITHOUT_THE_LOCK = "c08-three-ways-without-the-lock"


lesson.md(f"""
# C08. Sending work to another interpreter

{badge}

C04 made a second interpreter and found that the two of them share almost nothing. That was the good news and the bad news in one sentence. The good news is that two interpreters cannot corrupt each other's objects. The bad news is that you now have a worker you cannot hand anything to.

So this lesson is about the handing over. Which functions can go across, what happens to their arguments on the way, what comes back when the far side raises, and how many of these trips a second you can afford. The last one matters most, because there are workloads where four interpreters finish in a third of the time and others where they take forty times longer, and the difference is not the work. It is the arguments.

{figure("what-happens-to-an-argument", "an object reduced to bytes, carried across, and built again as a different object on the far side")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/crossinterp.c:530-558@v3.15.0rc1`.

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

Every cell in this lesson wants a second interpreter, and some runtimes will not give you one. A browser tab is the usual example. Each cell checks first and says so rather than failing, so the notebook still reads through on a runtime that cannot run it. On a normal desktop CPython 3.14 or newer, all of it runs.

The two recordings at the end come from containers rather than from your machine, because they are a comparison between two builds and one interpreter cannot be both.

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
## What can be handed over

The obvious way to give another interpreter a job is `Interpreter.exec`, which takes a string of source and runs it {cite("Lib/concurrent/interpreters/__init__.py:197-217@v3.15.0rc1#exec")}. That works, and C04 used it, but writing your program as strings gets old fast.

The better way is `Interpreter.call`, which takes an actual function object and its arguments {cite("Lib/concurrent/interpreters/__init__.py:225-238@v3.15.0rc1#call")}. It looks like calling a function. It is not, and the difference shows up the first time you try it with a function that reads a module level name.

A function is not a lump of code. It is code plus a pointer to the globals dictionary it was defined against, and that dictionary belongs to the interpreter it was made in. There is no way to send it. So the runtime sends the code on its own and gives it an empty globals dictionary on the far side, which only works if the function never looks anything up there {cite("Python/crossinterp_data_lookup.h:715-730@v3.15.0rc1#stateless")}. CPython calls such a thing a {term("stateless function")}, and the check is exactly that: no globals, no closure {cite("Python/crossinterp_data_lookup.h:755-780@v3.15.0rc1#_PyFunction_GetXIData")}.

Builtins are fine, because they are not found in the globals dictionary. A function that calls `sum` or `range` will cross. A function that calls itself by name will not, because a recursive call is a global lookup like any other. That one catches everybody.

{lesson.claim("Interpreter.call accepts a function that reads no module level names and a lambda, and refuses both a function that reads a global and a closure, with a message naming statelessness as the reason")}
""")


lesson.code("""
TAX = 3


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
ONE_ONLY = "  this runtime cannot make a second interpreter, so there is nothing to send work to"


def doubled(n):
    return n * 2


def taxed(n):
    return n * TAX


def make_adder(k):
    def add(n):
        return n + k

    return add


if not MORE_THAN_ONE:
    print(ONE_ONLY)
else:
    import concurrent.interpreters as ci

    worker = ci.create()
    for what, work in [
        ("a function with no globals", doubled),
        ("a lambda", lambda n: n + 1),
        ("a function reading a global", taxed),
        ("a closure over a local", make_adder(10)),
    ]:
        try:
            print(f"  {what:30} returned {worker.call(work, 5)}")
        except Exception as trouble:
            print(f"  {what:30} {type(trouble).__name__}: {trouble}")
    worker.close()
""")


lesson.md(f"""
The two that failed both failed for the same reason wearing different clothes. `taxed` needs `TAX`, which lives in this interpreter's globals. `add` needs `k`, which lives in a closure cell. Neither of those can travel, so neither function can.

## Three routes and the order they are tried

Arguments have the same problem, and the runtime solves it with a chain of fallbacks that is worth knowing by name. It is one switch statement {cite("Python/crossinterp.c:530-558@v3.15.0rc1#_PyObject_GetXIData")}, and it tries three things in order.

First, the direct route. A handful of types have a purpose written routine that turns them into plain bytes, and the registration list is short enough to read in one go: `None`, `int`, `bytes`, `str`, `bool`, `float`, and tuples of those {cite("Python/crossinterp_data_lookup.h:798-831@v3.15.0rc1#REGISTER")}. Those are the {term("shareable object")}s, and `is_shareable` is asking exactly this question.

Second, if the object is a function, the stateless route from the last section.

Third, pickle. This is the one that makes lists and dicts work, and it is also the one that quietly costs the most.

What the runtime produces at the end of any of those three is called {term("cross interpreter data")}, xidata in the source, and it is just bytes plus instructions for rebuilding. Nothing is shared, ever. The object on the far side is a new object at a new address.

The order is what makes the next cell interesting. A lambda cannot be pickled, and `is_shareable` says no, and a queue takes it anyway. That is only possible because there is a route between those two.

{lesson.claim("A lambda is not shareable and cannot be pickled, and a queue carries it regardless, which means the queue is trying something that is neither the direct route nor pickle")}
""")


lesson.code("""
import pickle
import threading

if not MORE_THAN_ONE:
    print(ONE_ONLY)
else:
    post = ci.create_queue()
    print(f"  {'what is being sent':24} {'direct':7} {'pickle':7} {'queue'}")
    for what, thing in [
        ("an int", 5),
        ("a list", [1, 2]),
        ("a dict", {"a": 1}),
        ("a stateless function", doubled),
        ("a lambda", lambda n: n + 1),
        ("a lock", threading.Lock()),
        ("a module", sys),
    ]:
        direct = ci.is_shareable(thing)
        try:
            pickle.dumps(thing)
            picklable = True
        except Exception:
            picklable = False
        try:
            post.put(thing)
            post.get()
            crossed = "yes"
        except Exception as trouble:
            crossed = type(trouble).__name__
        print(f"  {what:24} {direct!s:7} {picklable!s:7} {crossed}")
""")


lesson.md(f"""
{figure("the-three-routes-across", "a table of what is being sent, which of the three routes carries it, and what arrives on the far side")}

Read the lambda row again. Both of the routes you have heard of say no, and it goes across. Read the lock row too: all three say no, and that is the correct answer, because a lock is a promise about one address space's threads and it would mean nothing on the other side.

The list and dict rows are the ones to worry about. They cross, so nothing warns you, and they cross by being pickled. Hold that thought until the section on cost.

## What comes back when it goes wrong

An exception is an object, and objects do not cross. So when code fails in another interpreter, what you get here is a wrapper called `ExecutionFailed` carrying a snapshot: the type's name, the message, and the formatted traceback as text {cite("Lib/concurrent/interpreters/__init__.py:35-57@v3.15.0rc1#ExecutionFailed")}.

This is not a detail. It means `except ValueError` will not catch a `ValueError` raised over there, because nothing of that class ever arrived. You catch `ExecutionFailed` and read `excinfo.type.__name__` out of it, which is a string.

{lesson.claim("An exception raised in another interpreter arrives here as an ExecutionFailed carrying a snapshot, so the object it describes is not an instance of the class it names")}
""")


lesson.code("""
if not MORE_THAN_ONE:
    print(ONE_ONLY)
else:
    worker = ci.create()
    try:
        worker.exec("raise ValueError('the far side did not like that')")
    except ci.ExecutionFailed as failed:
        print(f"  what was raised here:        {type(failed).__name__}")
        print(f"  what it says happened there: {failed.excinfo.type.__name__}")
        print(f"  the message it carried:      {failed.excinfo.msg!r}")
        print(f"  is it a real ValueError:     {isinstance(failed.excinfo, ValueError)}")
    print(f"  would except ValueError catch it: {issubclass(ci.ExecutionFailed, ValueError)}")
    worker.close()
""")


lesson.md(f"""
The last line is the one that bites in real code. `ExecutionFailed` is an `InterpreterError`, not a `ValueError`, so an existing `try` block around the call will not do what it looks like it does.

## The modules that will not come with you

C07 ended on `Py_mod_gil`, the slot a compiled module fills in to say it is safe without the lock. There is a second slot right next to it in the same header, and it answers a different question: is this module safe in more than one interpreter {cite("Include/moduleobject.h:78-89@v3.15.0rc1#Py_MOD_MULTIPLE_INTERPRETERS_SUPPORTED")}?

The rule is the same shape as C07's. Saying nothing counts as no, because a module written before subinterpreters were usable could not have said anything. The import machinery checks the answer and refuses the import outright rather than warning {cite("Python/import.c:1587-1616@v3.15.0rc1#_PyImport_CheckSubinterpIncompatibleExtensionAllowed")}, and the reason it can be strict here and lenient in C07 is that a {term("subinterpreter")} created by `concurrent.interpreters` asks for the strict configuration on purpose {cite("Modules/_interpretersmodule.c:389-414@v3.15.0rc1#init_named_config")}.

Most of the standard library is fine. The ones that are not tend to be old modules holding process wide state that was never meant to be duplicated.

{lesson.claim("Some compiled standard library modules import normally in the main interpreter and raise ImportError in a subinterpreter, with a message saying the module does not support loading in subinterpreters")}
""")


lesson.code(
    """
if not MORE_THAN_ONE:
    print(ONE_ONLY)
else:
    worker = ci.create()
    for name in ["json", "decimal", "ctypes", "sqlite3", "readline", "_tkinter"]:
        try:
            __import__(name)
        except ImportError:
            print(f"  {name:10} not present in this runtime, so there is nothing to test")
            continue
        try:
            worker.exec(f"import {name}")
            print(f"  {name:10} imported over there too")
        except ci.ExecutionFailed as failed:
            print(f"  {name:10} {failed.excinfo.type.__name__}: {failed.excinfo.msg}")
    worker.close()
""",
    varies=(
        "which of these modules exist at all depends on how your Python was built, and a build "
        "without readline or tkinter reports them as missing rather than as refused"
    ),
)


lesson.md(f"""
## How narrow the channel is

Now the number that decides everything. A queue is the normal way to move values between interpreters, and every value on it goes through the three route chain in both directions: taken apart on the way in, built again on the way out.

For the types with a direct route that is cheap. For everything else it is pickle, and pickle is a real serialiser doing real work per item.

The cell below puts one value on a queue and takes it straight off again, twenty thousand times, for three payloads that take different routes.

{lesson.claim("A small int and a thousand byte string make round trips through a queue roughly ten times faster than a hundred item list does, because the first two take the direct route and the third has to be pickled and rebuilt")}
""")


lesson.code(
    """
import time

if not MORE_THAN_ONE:
    print(ONE_ONLY)
else:
    post = ci.create_queue()
    for what, payload in [
        ("a small int", 7),
        ("a 1000 byte string", "x" * 1000),
        ("a 100 item list", list(range(100))),
    ]:
        rounds = 20000
        started = time.perf_counter()
        for _ in range(rounds):
            post.put(payload)
            post.get()
        rate = rounds / (time.perf_counter() - started)
        print(f"  {what:20} {rate / 1000:7.0f} thousand round trips a second")
""",
    varies=(
        "the rates depend on your machine and on what else it is doing, but the gap between the "
        "first two rows and the third one is there on every machine"
    ),
)


lesson.md(f"""
{figure("what-one-crossing-costs", "bars of queue round trips a second for a small int, a thousand byte string and a hundred item list")}

A thousand byte string is a hundred times more data than a small int and costs almost nothing extra, because copying bytes is fast. A hundred item list is a tenth of that data and costs ten times more, because a hundred items means a hundred pickle operations and a hundred objects built on the far side. What you pay for is items, not bytes.

## A pool of interpreters

You would not write the queue plumbing by hand, and you do not have to. `InterpreterPoolExecutor` is an {term("interpreter pool")} with the same shape as the thread and process pools, so `submit` and `map` work the way you already know. Each worker makes one interpreter when it starts {cite("Lib/concurrent/futures/interpreter.py:59-71@v3.15.0rc1#initialize")} and every job goes across as an `Interpreter.call` {cite("Lib/concurrent/futures/interpreter.py:82-91@v3.15.0rc1#run")}, which is why the stateless rule from the first cell applies to everything you submit.

The cell below runs two jobs on four workers. One does a pile of arithmetic on a single integer argument, so almost nothing crosses. The other adds up a long list, so the argument is the whole job.

{lesson.claim("Four interpreters beat one on work with a small argument and lose badly on work whose argument is a large list, on the same machine in the same cell")}
""")


lesson.code(
    """
def spin(n):
    total = 0
    for i in range(n):
        total += i * i
    return total


def add_up(numbers):
    return sum(numbers)


def timed(run):
    started = time.perf_counter()
    run()
    return time.perf_counter() - started


SMALL = [500000] * 4
BIG = [list(range(200000)) for _ in range(4)]

if not MORE_THAN_ONE:
    print(ONE_ONLY)
else:
    from concurrent.futures import InterpreterPoolExecutor

    for what, work, jobs in [("arithmetic", spin, SMALL), ("adding up a list", add_up, BIG)]:
        one = timed(lambda: [work(job) for job in jobs])  # noqa: B023
        with InterpreterPoolExecutor(max_workers=4) as pool:
            four = timed(lambda: list(pool.map(work, jobs)))  # noqa: B023
        print(f"  {what:18} one at a time {one * 1000:5.0f} ms", end="")
        print(f", four interpreters {four * 1000:5.0f} ms")
""",
    varies=(
        "the timings depend on how many cores you have and what else is running, and on a laptop "
        "the arithmetic row can come out closer than it should, but the second row is slower with "
        "four workers than with one on every machine"
    ),
)


lesson.md(f"""
Same pool, same four workers, opposite verdicts. The second row is the crossing cost, and it is not small.

The two recordings below take that further. Same two workloads, three arrangements each, run on a four core container on both builds so the numbers are comparable.

{recording(WITH_THE_LOCK)}

{recording(WITHOUT_THE_LOCK)}

{figure("two-workloads-with-the-lock", "bars of threads and interpreters against running one at a time, on a build that has the lock")}

{figure("two-workloads-with-no-lock", "the same four bars on a build with no lock, where threads have moved and interpreters have not")}

On the build with the lock the story is the one everybody expects. Four threads do nothing at all for the arithmetic, 494 ms against 507 ms, because that is what the lock means. Four interpreters cut it to 208 ms, a bit under two and a half times. Then the list job: 6 ms one at a time, 255 ms across four interpreters. Forty two times slower for using more cores.

On the build with no lock the arithmetic flips. Threads now do the job in 179 ms, better than the interpreters at 359 ms, because threads share their objects and interpreters have to copy theirs. The list job is still ruined by the crossing, 16 ms against 380 ms.

{lesson.claim("Interpreters win the compute job on a build with the lock and lose it to plain threads on a build without one, while the data heavy job is slower across interpreters on both builds", unobservable="it is a comparison between two separate builds of the same source on the same hardware, and one interpreter cannot be both of them")}

{figure("which-one-to-reach-for", "a table of workload shapes against what to reach for on each of the two builds")}

So the summary is not a ranking. It is a question about your workload. If each job does a lot of work on a small argument, interpreters are good, and on a build with the lock they are the only thing that works. If each job carries a lot of data, the copying eats the parallelism and you are better off doing nothing clever at all.
""")


lesson.md("""
## Try it yourself

Four things, in rough order of how much you will learn.

Take the pool cell and change `SMALL = [500000] * 4` upwards, to five million or fifty. Somewhere in there the arithmetic row goes from a small win to a large one, because the fixed cost of making four interpreters stops mattering. Find roughly where.

Change `BIG` to send the length instead of the list, and have `add_up` build its own list with `sum(range(n))`. Same answer, same total work, and the whole crossing cost disappears. This is the single most useful trick with interpreters: send the recipe, not the ingredients.

Write a recursive function at the top of a cell and try to `call` it. Then rewrite it with an inner helper so the recursion is a local name rather than a global one, and try again. Watching that fix work is the clearest way to understand what stateless means.

If you can get a free threaded build, run the pool cell on it and compare against the recordings. Your laptop is not a four core container, so your numbers will differ, and the shape of the difference is the interesting part.

## What you now know

Two interpreters share almost nothing, so handing work over always means copying, and the copying is the part you have to budget for.

`Interpreter.call` sends a function by sending its code, which only works if the function reads no globals and closes over nothing. Builtins are fine. Recursion by name is not.

Arguments go through a chain of three routes, tried in order: a purpose written one for a small list of types, then the function route, then pickle. A lambda proves the middle one exists, because it fails the other two and crosses anyway.

An exception from another interpreter arrives as an `ExecutionFailed` carrying a snapshot rather than the exception itself, so your existing `except` clauses will not catch what they look like they catch.

A compiled module has to declare that it is safe in more than one interpreter, and if it says nothing the import is refused rather than warned about, which is stricter than the equivalent rule for the lock in C07.

A queue does over a million round trips a second for a small value and about a hundred thousand for a hundred item list. The cost tracks the number of items, not the number of bytes.

`InterpreterPoolExecutor` gives you the familiar pool interface, and the stateless rule applies to everything you submit through it.

Whether interpreters pay is a question about your workload and your build. Lots of work with small arguments on a build with the lock is the case they were made for. Small work with big arguments is the case where they cost you forty times.

## What is next

That is the end of the concurrency run. Eight lessons ago the GIL was a single fact about CPython, and it has turned out to be a counter, a per object policy, a build flag, an import time decision, and a thing you can sidestep entirely by having more than one of them.

The next run of lessons goes underneath all of it, to the runtime itself. What actually happens between the process starting and your first line running, where the state that every lesson so far has been poking at is kept, how the import system finds anything, and what has to be unwound at shutdown. It is the layer that makes everything else possible, and it is the one nobody reads.
""")


raise SystemExit(lesson.save())
