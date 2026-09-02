#!/usr/bin/env python
"""C02. What the lock was actually protecting.

The second concurrency lesson, and the one that changes what a reader thinks their own code was
getting from the GIL. A counter incremented by four threads comes out exactly right on an
ordinary build. Put a function call between the read and the write and it stops being right,
with the lock still on and nothing else changed.

So the safety was never a property of the assignment. It was a property of where the interpreter
is allowed to hand the lock over, which is the C01 result showing up in code people actually
write. What the free threaded build removed was that accident. What it added back is a one byte
mutex in every object header and a deadlock avoidance layer on top, which is why a list still
never loses an append.

Two recordings from the free threaded image finish it: per object locks measured by contending
on one list against four, and the same racing counter on the same binary with the lock switched
back on.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording

lesson = Lesson("c02-what-the-lock-was-protecting", "c02")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("c02-what-the-lock-was-protecting").figure

ONE_LOCK_EACH = "c02-one-lock-each-or-one-between-them"
SWITCHED_BACK_ON = "c02-the-lock-switched-back-on"


lesson.md(f"""
# C02. What the lock was actually protecting

{badge}

"The GIL makes Python thread safe" is one sentence covering two completely different claims, and only one of them was ever true.

This lesson separates them, using a counter that four threads add to. On the build you are almost certainly running, that counter comes out exactly right. Change one thing that looks like it could not possibly matter and it stops coming out right, with the lock still on.

{figure("two-kinds-of-safety", "the interpreter's own data structures on one side and your own variables on the other, with only the first one actually promised")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Include/cpython/pylock.h:12-35@v3.15.0rc1`.

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
## A counter that comes out right

Here is the oldest threading exercise there is. Four threads, a shared number, each thread adds one to it a hundred thousand times. The right answer is four hundred thousand.

In most languages you would get some number smaller than that, because `counter = counter + 1` is three steps: read it, add one, write it back. If another thread reads between your read and your write, one of the two increments disappears. That is a {term("race condition")}, and it is the first thing anybody learns about threads.

Run it on this Python and you get exactly four hundred thousand. Every time.

The cell turns the {term("switch interval")} down to a microsecond first. C01 spent a section on that number: it is how long a thread waiting for the {term("GIL")} sits patiently before it asks for it. Turning it down means threads hand the lock over as often as they possibly can, which is the setting most likely to lose an increment. It still does not.

{lesson.claim("Four threads each adding one to the same global a hundred thousand times end up with exactly four hundred thousand on an ordinary build, even with the switch interval turned all the way down")}
""")


lesson.code(
    """
import threading

ROUNDS = 100_000
THREADS = 4
WANT = ROUNDS * THREADS
NO_THREADS = "  this build cannot start a thread, so there is nothing to race here"


def threads_work():
    \"\"\"Some builds cannot start a thread at all. A browser tab is one of them.\"\"\"
    try:
        probe = threading.Thread(target=lambda: None)
        probe.start()
        probe.join()
    except RuntimeError:
        return False
    return True


THREADS_WORK = threads_work()
counter = 0


def race(target):
    \"\"\"Run `target` on THREADS threads with the switch interval as low as it will go.\"\"\"
    global counter
    before = sys.getswitchinterval()
    sys.setswitchinterval(0.000001)
    try:
        counter = 0
        hands = [threading.Thread(target=target) for _ in range(THREADS)]
        for hand in hands:
            hand.start()
        for hand in hands:
            hand.join()
    finally:
        sys.setswitchinterval(before)
    return counter


def plain():
    global counter
    for _ in range(ROUNDS):
        counter = counter + 1


if not THREADS_WORK:
    print(NO_THREADS)
else:
    print(f"  asked for {WANT:,} increments")
    print(f"  ended up with {race(plain):,}")
""",
    varies=(
        "on an ordinary build this comes out exactly right every time, and on a free threaded "
        "build it comes out short, because nothing here is protecting the counter and the two "
        "builds differ in whether anything else is"
    ),
)


lesson.md(f"""
## The same counter, one call further apart

Now change one thing. Instead of `counter = counter + 1`, write `counter = add_one(counter)`, where `add_one` returns its argument plus one. Same arithmetic, same threads, same interval, same lock.

It stops coming out right. Roughly half the increments go missing.

Then a third version, which reads the counter, runs a loop that goes round exactly once and does nothing, and writes the value back. That one loses even more.

{figure("where-the-count-goes-wrong", "three ways of writing the same increment, what sits between the read and the write in each, and how many increments survive")}

The reason is the whole of C01 in one line. A running thread only gives up the GIL at a {term("periodic check")}, and the compiler emits one of those at backward jumps and at function resumes and nowhere else {cite("Python/bytecodes.c:158-161@v3.15.0rc1#_CHECK_PERIODIC")}. `counter = counter + 1` has neither, so no other thread can get in partway through it. Add a call and there is a function resume. Add a loop and there is a backward jump. Now there is somewhere for the lock to move, and increments start disappearing.

So the counter was never safe. It was unreachable, which looks the same right up until you refactor the line.

{lesson.claim("Putting a function call or a one pass loop between the read and the write makes the same counter start losing increments, on the same build with the same lock")}
""")


lesson.code(
    """
def add_one(value):
    return value + 1


def through_a_call():
    global counter
    for _ in range(ROUNDS):
        counter = add_one(counter)


def with_a_loop():
    global counter
    for _ in range(ROUNDS):
        value = counter
        for _ in range(1):
            pass
        counter = value + 1


shapes = (
    ("nothing in between", plain),
    ("a call in between", through_a_call),
    ("a loop in between", with_a_loop),
)

if not THREADS_WORK:
    print(NO_THREADS)
else:
    for name, work in shapes:
        got = race(work)
        print(f"  {name:<20} {got:>8,} of {WANT:,}   {got / WANT:>6.0%} survived")
""",
    varies=(
        "the first row is exact on any build with a GIL and short on a free threaded one, and "
        "the other two are short everywhere, but how short depends on how the operating system "
        "schedules the four threads on this particular machine"
    ),
)


lesson.md(f"""
## The list that never loses anything

Try the same shape with a list. Four threads, four hundred thousand `append` calls each, all into one list. Count what ended up in it.

You get all of them. Not most of them, all of them, and not by luck. `list.append` grows an array and writes into it, which is a read and a write of the list's internals, and two threads doing that at once could easily leave one item on the floor or the length wrong.

This one is a promise, and it is a promise on both builds. On the build with the {term("GIL")} it holds because only one thread runs at a time. On the {term("free threaded build")} it holds because the append is wrapped in a {term("critical section")} that takes that particular list's own lock {cite("Objects/listobject.c:538-550@v3.15.0rc1#PyList_Append")}.

The nicest part is where that wrapping comes from. The method is declared in an {term("Argument Clinic")} block with the line `@critical_section` above it {cite("Objects/listobject.c:1222-1239@v3.15.0rc1#list_append_impl")}, and a script turns that one word into the C that takes the lock {cite("Objects/clinic/listobject.c.h:115-126@v3.15.0rc1#Py_BEGIN_CRITICAL_SECTION")}. B04 is the lesson about how much of CPython is written that way, and this is one of the better examples of why.

{lesson.claim("Four threads appending to the same list lose nothing, on any build, because the append itself takes a lock")}
""")


lesson.code(
    """
APPENDS = 400_000


def fill(target):
    for _ in range(APPENDS):
        target.append(1)


if not THREADS_WORK:
    print(NO_THREADS)
else:
    shared = []
    fillers = [threading.Thread(target=fill, args=(shared,)) for _ in range(THREADS)]
    for filler in fillers:
        filler.start()
    for filler in fillers:
        filler.join()
    print(f"  appends asked for {APPENDS * THREADS:>10,}")
    print(f"  items in the list {len(shared):>10,}")
""",
    varies=(
        "the two numbers are equal on every build, and the only thing that changes between "
        "builds is how long the cell takes to run"
    ),
)


lesson.md(f"""
## The lock that fits in one byte

So where does a list keep its lock. In the object itself.

O01 took the {term("object header")} apart and found the free threaded one is twice the size, with an `ob_mutex` field in it {cite("Include/object.h:156-167@v3.15.0rc1#ob_mutex")}. That field is a `PyMutex`, and a `PyMutex` is one byte {cite("Include/cpython/pylock.h:12-35@v3.15.0rc1#PyMutex")}.

Two bits of that byte are used. One says whether somebody is holding it. The other says whether anybody is parked waiting for it.

{figure("one-byte-of-lock", "the four states of the one byte mutex and what a thread does in each")}

Taking a free one is a single compare and exchange instruction, with no system call and no allocation {cite("Include/cpython/pylock.h:46-59@v3.15.0rc1#_PyMutex_Lock")}. That is the whole reason this design is possible. A lock cheap enough to take and release millions of times a second is a lock you can afford to put inside every object, instead of one big one you take at the door.

{lesson.claim("Every object on the free threaded build carries its own one byte lock, and taking an uncontended one is a single instruction", unobservable="the field only exists in a build configured with --disable-gil, and there is no Python level way to look at it even there")}

That is a {term("per object lock")}. The rest of the design is about what you do when you need two of them.
""")


lesson.md(f"""
## Two objects at once

Locks that live in objects have the usual problem. Thread A takes list `a` and then wants `b`. Thread B takes `b` and then wants `a`. Nobody moves again.

The usual fix is a rule about the order locks are taken in, which somebody eventually breaks. CPython does something else. A {term("critical section")} is allowed to let go of its lock partway through, and an inner one suspends the outer ones instead of nesting inside them {cite("Include/critical_section.h:7-22@v3.15.0rc1#Py_BEGIN_CRITICAL_SECTION2")}. A thread therefore never sits waiting for one lock while holding another, so there is no cycle to get stuck in.

{figure("locking-two-at-once", "two threads deadlocking on nested locks, against the pair of locks taken together")}

Which does mean you cannot nest two of them and expect to hold both. So there is a separate macro for that case, and `list_a + list_b` is one of the places that uses it {cite("Objects/listobject.c:810-816@v3.15.0rc1#Py_BEGIN_CRITICAL_SECTION2")}.

And on your build all of this compiles to nothing at all. `Py_BEGIN_CRITICAL_SECTION` is redefined as an opening brace and `Py_END_CRITICAL_SECTION` as a closing one {cite("Include/cpython/critical_section.h:44-61@v3.15.0rc1#Py_BEGIN_CRITICAL_SECTION")}. The GIL is already doing the job, so the annotations are free. That is what lets one source tree serve both builds.
""")


lesson.md(f"""
## One lock each, or one lock between them

Per object locks have a consequence you can measure. If four threads append to four different lists, they take four different locks and never wait for each other. If four threads append to the same list, they all queue on one byte.

On the build you have, those two cases are the same measurement, because the GIL makes them the same. The cell below shows that: both come out around the same time and neither is faster than one thread doing all the work.

{lesson.claim("On a build with the GIL, four threads sharing one list and four threads with a list each take about the same time as each other")}
""")


lesson.code(
    """
import time

TRIES = 5


def one_list(count):
    \"\"\"One list, handed to every thread, so every append lands on the same object.\"\"\"
    shared = []
    return [shared] * count


def a_list_each(count):
    \"\"\"A list per thread, so no two threads ever want the same lock.\"\"\"
    return [[] for _ in range(count)]


def best(make_targets, count):
    \"\"\"Fastest wall clock time out of TRIES runs, because one timing is a coin toss.\"\"\"
    times = []
    for _ in range(TRIES):
        targets = make_targets(count)
        crew = [threading.Thread(target=fill, args=(target,)) for target in targets]
        start = time.perf_counter()
        for hand in crew:
            hand.start()
        for hand in crew:
            hand.join()
        times.append(time.perf_counter() - start)
    return min(times)


if not THREADS_WORK:
    print(NO_THREADS)
else:
    fill([])
    one = best(a_list_each, 1)
    print(f"  one thread, one list        {one * 1000:>7.0f} ms")
    for label, make in (("the same list", one_list), ("a list each", a_list_each)):
        took = best(make, THREADS)
        rate = THREADS * one / took
        print(f"  {THREADS} threads, {label:<14} {took * 1000:>7.0f} ms   {rate:.2f}x")
""",
    varies=(
        "the times depend on the machine, and on an ordinary build the two speedup figures land "
        "near each other and well under one, because only one thread is appending at a time "
        "whichever list it is appending to"
    ),
)


lesson.md(f"""
Now the same program on the free threaded image, where the locks are real.

{figure("same-list-or-a-list-each", "one thread against four sharing a list against four with a list each, as a bar chart of milliseconds")}

Four threads with their own lists get most of the parallel speedup. Four threads sharing one list are slower than one thread doing all the work, because every append now costs a contended lock on top of the work.

{lesson.claim("Without the GIL, four threads appending to four lists get real speedup while four threads appending to one list are slower than one thread doing all of it", unobservable="both halves of this only differ on a build configured with --disable-gil, and on any other build they are the same measurement taken twice")}

{recording(ONE_LOCK_EACH)}
""")


lesson.md(f"""
## The lock can come back

One more thing, and it is the part that surprises people who assume free threading is a one way door.

A free threaded interpreter can turn its GIL back on. There are two ways in. The first is a flag at startup, `-X gil=1` or the `PYTHON_GIL` environment variable {cite("Python/initconfig.c:1970-1990@v3.15.0rc1#PYTHON_GIL")}. The same parser reads both, and it is worth knowing what it does on your build: `-X gil=1` is quietly accepted and does nothing, and `-X gil=0` is a hard error, because your interpreter has no GIL to remove.

{lesson.claim("On an ordinary build, -X gil=1 is accepted and does nothing while -X gil=0 refuses to start the interpreter at all")}
""")


lesson.code(
    """
import subprocess

ASK = "import sys; print('started, and the lock is on:', sys._is_gil_enabled())"


def start_python(setting):
    \"\"\"Start another copy of this interpreter with -X gil set, and report what it said.\"\"\"
    if not sys.executable:
        return None
    try:
        done = subprocess.run(
            [sys.executable, "-X", f"gil={setting}", "-c", ASK],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except OSError:
        return None
    return (done.stdout + done.stderr).strip().splitlines()[0]


for setting in ("1", "0"):
    said = start_python(setting)
    if said is None:
        print("  this build cannot start another process, so there is nothing to try here")
        break
    print(f"  -X gil={setting}  {said}")
""",
    varies=(
        "on an ordinary build the first line starts the interpreter and the second is a fatal "
        "error, and on a free threaded build both start and report the lock as on and off "
        "respectively"
    ),
)


lesson.md(f"""
The second way in is stranger, and it happens after the interpreter is already running.

An extension module written in C declares whether it is safe without the lock, using a slot called `Py_mod_gil` {cite("Include/moduleobject.h:85-89@v3.15.0rc1#Py_MOD_GIL_NOT_USED")}. Module setup reads that slot and remembers the answer {cite("Objects/moduleobject.c:471-476@v3.15.0rc1#Py_mod_gil")}. If a module does not say, the import machinery assumes the worst and turns the GIL on for the whole interpreter, warning as it goes {cite("Python/import.c:1618-1643@v3.15.0rc1#_PyImport_CheckGILForModule")}.

{figure("the-lock-coming-back", "an extension import with no Py_mod_gil slot leading to the GIL being switched on for the rest of the run")}

That switch is permanent for the rest of the process {cite("Python/import.c:1645-1665@v3.15.0rc1#_PyImport_EnableGILAndWarn")}. The counter it keeps goes to `INT_MAX` and never comes down {cite("Python/ceval_gil.c:1132-1150@v3.15.0rc1#_PyEval_EnableGILPermanent")}, which is the difference between this and the ordinary case where the count goes up and down as modules that need the lock are loaded and dropped {cite("Python/ceval_gil.c:1152-1191@v3.15.0rc1#_PyEval_DisableGIL")}.

So one unported extension deep in your dependencies can put the lock back, and the only sign is a `RuntimeWarning` on import. `sys._is_gil_enabled()` is worth calling after your imports rather than before them.

The recording runs the three counters from earlier on the free threaded image, twice, in child processes of the same binary. Once with the lock off, where all three lose increments. Once with `-X gil=1`, where the first one goes back to being exactly right and the other two do not.

{lesson.claim("The same free threaded binary started with -X gil=1 gets the exact answer for the plain counter back, and still loses increments for the other two shapes", unobservable="only a build configured with --disable-gil accepts the flag at all, so the two halves cannot be run on one ordinary interpreter")}

{recording(SWITCHED_BACK_ON)}
""")


lesson.md("""
## Try it yourself

Four things, roughly in order of how much they will teach you.

Take the `with_a_loop` version and delete the inner loop, leaving the read and the write on separate lines with nothing between them. It goes back to being exactly right. Two statements are no less atomic than one, because atomicity was never the thing doing the work.

Put `counter += 1` in as a fourth shape. It is the same as `plain` on an ordinary build, and it is worth confirming that yourself rather than taking it on trust, because the `+=` spelling is the one people assume is special.

Swap the list in the append cell for a `dict`, setting `d[i] = i` from four threads with non overlapping ranges of `i`. Count the keys at the end. Dicts carry the same annotations as lists, so the count is exact, and O07 is the lesson about what is being protected in there.

Wrap the increment in a `threading.Lock`. Every shape becomes exact on every build, and the cell gets a lot slower. That is the actual answer, and it always was: if two threads share a variable, lock it yourself.

## What you now know

"The GIL makes Python thread safe" is two claims. The interpreter's own data structures are safe, and always were, and still are. Your own variables never were.

A counter incremented by four threads comes out exactly right on an ordinary build, and stops being right the moment a function call or a loop appears between the read and the write. Nothing about the lock changed. The only thing that changed is whether there is a periodic check in the middle, which is where the interpreter is allowed to hand the lock over.

Free threading replaced the one big lock with a one byte mutex in every object header, cheap enough to take millions of times a second because an uncontended one is a single instruction.

Deadlock is avoided by letting a critical section suspend itself rather than by ordering the locks, and by a separate macro for the cases that genuinely need two objects at once. On a build with the GIL all of it compiles to a pair of braces.

Locks in objects means contention is per object. Four threads on four lists scale. Four threads on one list are slower than one thread.

And the lock can come back, either from a flag at startup or from importing one C extension that has not declared itself safe, which turns it on permanently for the whole interpreter with nothing but a warning.

## What is next

C03 goes down one more level, to what a thread actually is to the interpreter. Every one of them has a `PyThreadState`, they hang off the interpreter in a list, and attaching and detaching from that list is what the GIL handoff in C01 was really doing.
""")


raise SystemExit(lesson.save())
