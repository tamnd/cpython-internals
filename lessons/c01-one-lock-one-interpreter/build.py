#!/usr/bin/env python
"""C01. One lock, one interpreter.

The first of the concurrency lessons. Everybody has heard of the GIL and almost nobody has
measured it, so this lesson measures it: two threads adding numbers, two threads sleeping, one
long call into C, and the switch interval turned up and down.

The point that is hard to get from an explanation is that the lock is only ever released at a
periodic check, which happens on backward jumps. That is why one call to `list.sort` cannot be
interrupted no matter what `sys.setswitchinterval` says, and it is the cell most likely to
change how a reader thinks about their own code.

Two recordings from the free threaded image run the same benchmarks with no lock at all, which
is the side by side this milestone asks for.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording

lesson = Lesson("c01-one-lock-one-interpreter", "c01")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("c01-one-lock-one-interpreter").figure

NO_LOCK = "c01-the-same-work-without-the-lock"
NOTHING_TO_WAIT_FOR = "c01-nothing-to-wait-for"


lesson.md(f"""
# C01. One lock, one interpreter

{badge}

Your machine has several cores. Start two Python threads that both add up a few million numbers and they will finish in about the time it would have taken to do both jobs one after the other, on one core, with the others idle.

That is the GIL, and it is the most talked about and least measured thing in CPython. This lesson measures it. Nine cells, all of which run on the Python you already have.

{figure("the-handoff", "the six steps a waiting thread and a running thread go through to hand the lock over")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/ceval_gil.c:285-290@v3.15.0rc1`.

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

Most of this lesson runs anywhere. One thing does not: a browser tab cannot start a thread at all, so the timing cells check first and say so rather than printing nonsense. If you are reading this in Colab or from a checkout, everything runs.

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
## Is there a lock here at all

Two questions before any measuring. Is the {term("GIL")} on, and can this runtime make threads.

The first one has an answer in the standard library. `sys._is_gil_enabled()` returns `True` on every ordinary build, and the underscore is there because it only becomes an interesting question on the free threaded build, where it can be `False` {cite("Python/sysmodule.c:2665-2674@v3.15.0rc1#sys__is_gil_enabled_impl")}.

The second one matters because a browser has no threads to give you. `threading.Thread(...).start()` raises `RuntimeError` there, which is catchable, so one small probe at the top saves every cell below from guessing.

While we are here, `sys.getswitchinterval()` reports the {term("switch interval")} in seconds. Remember the number it prints, because a later section spends a while on it.

{lesson.claim("sys._is_gil_enabled() is True on an ordinary build and the switch interval is five thousandths of a second")}
""")


lesson.code(
    """
import threading
import time


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

print(f"  is the GIL on right now      {sys._is_gil_enabled()}")
print(f"  switch interval in seconds   {sys.getswitchinterval()}")
print(f"  can this build make threads  {THREADS_WORK}")
""",
    varies=(
        "a browser build cannot start a thread, so the last line is False there and every "
        "timing cell below prints a note instead of a number"
    ),
)


lesson.md(f"""
## Two threads, no faster

Here is the benchmark everybody has heard about. A function that adds up two million numbers, run twice one after the other, and then the same two runs on two threads.

The two threads really do both exist, both really do run, and the total time really does not move. On a laptop with ten cores, the second core sits there doing nothing.

{lesson.claim("The same work on two threads takes about as long as doing it twice in a row, and often a little longer")}
""")


lesson.code(
    """
def spin(n):
    total = 0
    for i in range(n):
        total += i
    return total


WORK = 2_000_000
NO_THREADS = "  this build cannot start a thread, so there is nothing to time here"


def on_threads(count, target, *args):
    \"\"\"Run target on count threads at once and give back the time all of them took.\"\"\"
    threads = [threading.Thread(target=target, args=args) for _ in range(count)]
    start = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return time.perf_counter() - start


def one_by_one(count, target, *args):
    \"\"\"The same work as on_threads, done one piece after the other on this thread.\"\"\"
    start = time.perf_counter()
    for _ in range(count):
        target(*args)
    return time.perf_counter() - start


def fastest(how, count, target, *args):
    \"\"\"Best of three, because a single timing on a laptop is close to a coin toss.\"\"\"
    return min(how(count, target, *args) for _ in range(3))


if not THREADS_WORK:
    print(NO_THREADS)
else:
    spin(WORK)
    in_a_row = fastest(one_by_one, 2, spin, WORK)
    together = fastest(on_threads, 2, spin, WORK)
    print(f"  the work twice, one after the other  {in_a_row * 1000:.0f} ms")
    print(f"  the same work on two threads         {together * 1000:.0f} ms")
    print(f"  speedup                              {in_a_row / together:.2f}x")
""",
    varies=(
        "the times depend entirely on the machine, and the speedup lands near 1.0 on every "
        "build with a GIL, usually a little under it because handing the lock back and forth "
        "is not free"
    ),
)


lesson.md(f"""
## The same two threads, sleeping

Now change one thing. Instead of adding numbers, each thread sleeps for three tenths of a second. Nothing else about the code moves.

{figure("adding-versus-waiting", "the same two threads doing CPU work on the left and waiting on the right, with the speedup for each")}

This time the two threads take half as long as doing it in a row, which is exactly what you would have hoped for the first time.

The reason is one macro. Anything in CPython that is about to wait wraps the waiting in `Py_BEGIN_ALLOW_THREADS` and `Py_END_ALLOW_THREADS`, which expand to saving the thread state, letting go of the lock, and taking it back afterwards {cite("Include/ceval.h:119-125@v3.15.0rc1#Py_BEGIN_ALLOW_THREADS")}. `time.sleep` is one of them, and so is every socket read, every file read and every database driver worth using {cite("Modules/timemodule.c:2266-2278@v3.15.0rc1#Py_BEGIN_ALLOW_THREADS")}.

So the rule of thumb is not "threads are useless in Python". It is that threads help when they are waiting for somebody else and not when they are computing.

{lesson.claim("Two threads that sleep take about half as long as sleeping twice in a row")}
""")


lesson.code(
    """
if not THREADS_WORK:
    print(NO_THREADS)
else:
    napping = one_by_one(2, time.sleep, 0.3)
    together = on_threads(2, time.sleep, 0.3)
    print(f"  sleeping twice, one after the other  {napping * 1000:.0f} ms")
    print(f"  the same two sleeps on two threads   {together * 1000:.0f} ms")
    print(f"  speedup                              {napping / together:.2f}x")
""",
    varies=(
        "the sleeps are fixed so the numbers are close to 600 ms and 300 ms everywhere, but "
        "the exact overshoot depends on how quickly the operating system wakes a thread"
    ),
)


lesson.md(f"""
## What the lock is actually made of

For something with this reputation it is a small struct, and reading it takes a minute {cite("Include/internal/pycore_gil.h:22-61@v3.15.0rc1#_gil_runtime_state")}.

{figure("what-the-lock-is-made-of", "the six fields of struct _gil_runtime_state and what each one is for")}

`locked` is the lock. It is an integer holding 0 or 1, and everything else in the struct is machinery for handing it over without threads burning cores spinning on it.

One thing worth noticing early. That struct lives at `interp->ceval.gil`, hanging off an interpreter rather than off the process {cite("Python/ceval_gil.c:424-438@v3.15.0rc1#_PyEval_SetSwitchInterval")}. The name says global, and it has not been global for a while. A process running two subinterpreters can have two of these, which is the whole reason PEP 734 exists and is where the R lessons pick this up again.
""")


lesson.md(f"""
## Who asks for it, and when

Here is the part that explains most of the surprising behaviour. A thread holding the lock does not give it up because it is being polite. It gives it up because somebody asked, and the asking has a delay built into it.

A thread that wants the lock calls `take_gil` {cite("Python/ceval_gil.c:285-290@v3.15.0rc1#take_gil")}. It does not spin. It waits on a condition variable with a timeout of exactly one switch interval. If it gets woken because the holder let go, fine, it takes the lock. If it times out and nothing has changed hands in the meantime, it sets a bit on the holder's {term("eval breaker")} that means "please drop this" {cite("Python/ceval_gil.c:328-364@v3.15.0rc1#COND_TIMED_WAIT")}.

That "nothing has changed hands" test is `switch_number`, a counter that goes up every time the lock moves to a different thread {cite("Python/ceval_gil.c:383-395@v3.15.0rc1#switch_number")}. Without it, a thread that woke up for an unrelated reason would keep asking a thread that has already been handing the lock around perfectly happily.

The other end is `drop_gil`, which sets `locked` back to 0 and signals the condition variable {cite("Python/ceval_gil.c:202-214@v3.15.0rc1#drop_gil_impl")}. If somebody had asked for the drop, the releasing thread then waits until `last_holder` is somebody other than itself before carrying on {cite("Python/ceval_gil.c:259-274@v3.15.0rc1#switch_cond")}. That extra wait exists because without it, on a machine with spare cores, the thread that just released the lock would often be the first one back to grab it, and the thread that asked would wait all over again. The comment at the top of the file has the full story and is worth the five minutes {cite("Python/ceval_gil.c:20-37@v3.15.0rc1#gil_drop_request")}.
""")


lesson.md(f"""
## The one place a thread can let go

So a waiting thread sets a bit. When does the running thread look at it?

Not between every instruction, which is what most explanations say. The eval breaker is checked by a `_CHECK_PERIODIC` instruction {cite("Python/bytecodes.c:158-161@v3.15.0rc1#_CHECK_PERIODIC")}, and the compiler puts one of those in front of backward jumps and function resumes and nowhere else {cite("Python/bytecodes.c:3585-3589@v3.15.0rc1#JUMP_BACKWARD")}. The instruction reads one word, and only if some bit in it is set does it do anything at all {cite("Python/ceval_macros.h:520-528@v3.15.0rc1#check_periodics")}. That is the {term("periodic check")}, and it is the only route from running code to letting go of the lock {cite("Python/ceval_gil.c:1414-1422@v3.15.0rc1#_PY_GIL_DROP_REQUEST_BIT")}.

{figure("where-the-check-happens", "the chain from a backward jump instruction to the thread releasing the lock")}

The consequence is large. If a thread is inside a single call into C, there are no backward jumps, so there is no periodic check, so the lock cannot be dropped however long the call takes. `sys.setswitchinterval` has nothing to say about it.

The cell below runs a ticking thread that does nothing but write down the time, so a pause shows up as a gap. Then it gives the main thread two jobs of roughly the same length: a loop written in Python, and one call to `list.sort`.

{lesson.claim("A loop written in Python lets the other thread in many times over, while one call to list.sort holds the lock for almost the entire call")}
""")


lesson.code(
    """
import itertools

ticks = []
stop = False


def ticker():
    \"\"\"Do nothing but note the time, so a pause turns into a gap in the list.\"\"\"
    while not stop:
        ticks.append(time.perf_counter())


def longest_gap(marks):
    \"\"\"The longest the ticker went without a turn, which is how long it was shut out.\"\"\"
    return max((b - a for a, b in itertools.pairwise(marks)), default=0.0)


if not THREADS_WORK:
    print(NO_THREADS)
else:
    helper = threading.Thread(target=ticker)
    helper.start()
    time.sleep(0.05)

    data = [(i * 2654435761) % 4000037 for i in range(1_500_000)]

    ticks.clear()
    start = time.perf_counter()
    spin(3_000_000)
    end = time.perf_counter()
    loop_took = end - start
    loop_ticks = [mark for mark in ticks if mark <= end]

    ticks.clear()
    start = time.perf_counter()
    data.sort()
    end = time.perf_counter()
    sort_took = end - start
    sort_ticks = [mark for mark in ticks if mark <= end]

    stop = True
    helper.join()

    measured = (
        ("a loop written in python", loop_took, loop_ticks),
        ("one call to list.sort", sort_took, sort_ticks),
    )
    for what, took, marks in measured:
        pause = longest_gap(marks)
        print(f"  {what} took {took * 1000:.0f} ms")
        print(f"    longest the other thread sat still  {pause * 1000:.1f} ms")
        print(f"    which is this much of the whole call {pause / took:.0%}")
""",
    varies=(
        "the two jobs take different times on different machines and the longest pause during "
        "the Python loop depends on how the operating system schedules threads, but the sort "
        "line lands near 100 percent everywhere because there is no periodic check inside it"
    ),
)


lesson.md(f"""
## The switch interval is not a fairness dial

`sys.setswitchinterval` is usually described as how often threads take turns, and people reach for a smaller number when threads look unfair {cite("Python/sysmodule.c:1314-1325@v3.15.0rc1#sys_setswitchinterval_impl")}. Knowing what `take_gil` does with it says otherwise: it is how long a waiting thread stays patient before it asks. Making it smaller does not make turns happen more often, it makes waiting threads more impatient, and every handoff costs a stop and a start.

The cell runs two counting threads for four tenths of a second at four different intervals and reports what each one got done {cite("Python/sysmodule.c:1334-1339@v3.15.0rc1#sys_getswitchinterval_impl")}.

{figure("the-switch-interval-trade", "four switch interval settings with the total work done and how evenly the two threads shared it")}

The bottom row is the one to look at. Half a second is longer than the whole measurement, so the second thread sits in `take_gil` waiting out an interval that never expires, and it finishes the run having done nothing at all.

{lesson.claim("Turning the switch interval down to a microsecond costs roughly half the total work, and turning it up to half a second means one of the two threads never runs")}
""")


lesson.code(
    """
def count_until(box, index, deadline):
    \"\"\"Add one to a counter until the clock runs out, then report the total.\"\"\"
    n = 0
    while time.perf_counter() < deadline:
        n += 1
    box[index] = n


def share(interval, seconds=0.4):
    \"\"\"How much two counting threads get done in `seconds` at a given switch interval.\"\"\"
    before = sys.getswitchinterval()
    sys.setswitchinterval(interval)
    try:
        box = [0, 0]
        deadline = time.perf_counter() + seconds
        threads = [threading.Thread(target=count_until, args=(box, i, deadline)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        sys.setswitchinterval(before)
    return box


if not THREADS_WORK:
    print(NO_THREADS)
else:
    for interval in (0.000001, 0.005, 0.05, 0.5):
        first, second = share(interval)
        each = f"{first:>9,} and {second:>9,}"
        print(f"  interval {interval:<9} total {first + second:>10,}   {each}")
""",
    varies=(
        "the counts depend on how fast the machine is, and the split between the two threads "
        "moves from run to run, but the microsecond row is always well under the default row "
        "and the half second row always leaves one thread on zero"
    ),
)


lesson.md(f"""
## The same benchmarks with no lock at all

Everything above is a property of one build. The free threaded build takes the lock out, and the way to see what that changes is to run the identical programs on it.

{figure("two-builds-one-benchmark", "the same two thread benchmark on the ordinary build and on the free threaded build")}

That build is not a flag you can turn on at runtime, so these two come from the published free threaded image, recorded in CI, program and output both {cite("Include/internal/pycore_gil.h:22-61@v3.15.0rc1#_gil_runtime_state")}.

First, the two thread benchmark. Two threads, twice as fast, on the same source that got 1.0x above. The four thread row is lower than four because the machine running it has four shared cores under emulation, not because of anything in the interpreter.

{lesson.claim("On the free threaded build the same two thread benchmark comes out about twice as fast", unobservable="the build has to be configured with --disable-gil, which is a different interpreter rather than a runtime setting")}

{recording(NO_LOCK)}

Second, the long C call. On the build you have, a call to `list.sort` holds the lock for essentially the whole call and the other thread stops dead. With no lock, there is nothing for the other thread to be waiting for, and it keeps counting the entire way through.

{lesson.claim("On the free threaded build the second thread keeps running all the way through somebody else's long C call", unobservable="the same reason, since on any build with a GIL the answer is decided by the lock rather than by the machine")}

{recording(NOTHING_TO_WAIT_FOR)}
""")


lesson.md("""
## Try it yourself

Four things, in rough order of how much they will teach you.

Change `WORK` in the two thread cell from two million to twenty million and run it again. The speedup stays near 1.0, which is the point: this is not a warmup artifact or a measurement that goes away when the numbers get bigger.

Add a third and fourth thread to the sleeping cell by calling `on_threads(4, time.sleep, 0.3)`. Four threads sleeping for three tenths of a second still take three tenths of a second. Then do the same to the adding cell and watch the total stay flat.

In the `list.sort` cell, replace `data.sort()` with `sorted(data, key=lambda x: x)`. Now there is a Python function being called for every comparison, so there are function resumes, so there are periodic checks. The longest pause should collapse from most of the call to a few milliseconds, and the sort itself gets much slower. That is the same trade the interpreter makes everywhere.

In the switch interval cell, add `0.000000001` to the tuple. It is clamped: `take_gil` treats anything under one microsecond as one microsecond, so the row comes out the same as the first one.

## What you now know

The GIL is one boolean plus the machinery to hand it over, and it lives on the interpreter rather than on the process.

A thread that wants it waits one switch interval on a condition variable before it asks. Five milliseconds is the default, and the number is a trade against the cost of handing the lock over, not a fairness setting.

The asking is a bit on the holder's eval breaker, and the holder only looks at that word during a periodic check, which happens at backward jumps and function resumes. A single call into C has neither, so it cannot be interrupted.

Threads that compute get no faster, because only one of them can hold the lock. Threads that wait get much faster, because everything that waits releases the lock first, through one macro pair that is easy to find in any C extension.

The free threaded build runs the same programs with real parallel speedup, and it is a different interpreter rather than a setting.

## What is next

C02 goes into that different interpreter properly: what PEP 703 actually removed, what it had to add back, and why an object header got bigger.
""")


raise SystemExit(lesson.save())
