#!/usr/bin/env python
"""M08. Stop the world.

The eighth lesson of the memory part, and the second half of M07. M07 took the cycle collector
apart on the ordinary build: three lists, a counter, a promotion on every survival, and a brake
on the expensive pass. This lesson runs the same experiments on the free threaded build and gets
different answers to almost all of them, because that build does not keep the three lists at all.

Everything here runs on any build. Three of the answers only exist on a build made without the
GIL, and those arrive as recordings, run in the image this project publishes:
`m08-no-lists-to-be-in`, `m08-the-count-another-thread-cannot-see` and
`m08-nothing-runs-while-it-walks`.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording

lesson = Lesson("m08-stop-the-world", "m08")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("m08-stop-the-world").figure

NO_LISTS = "m08-no-lists-to-be-in"
STALE_COUNT = "m08-the-count-another-thread-cannot-see"
NOTHING_RUNS = "m08-nothing-runs-while-it-walks"


lesson.md(f"""
# M08. Stop the world

{badge}

M07 spent a whole lesson on three lists. An object starts in the first one, gets promoted every time it survives a pass, and never comes back down, which is why a cycle that has been alive for a while cannot be freed by a pass over the youngest list.

On the {term("free threaded build")} those three lists do not exist.

{figure("two-shapes-of-heap", "the ordinary build's three linked lists against the free threaded build's single heap")}

This lesson runs M07's experiments again on that build. The `gc` module still answers all the same questions, because the language documents them, but several of the answers stop meaning what they used to. Then it gets to the part that has no equivalent on the ordinary build at all, which is what happens to the other threads while a collection is running.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/gc_free_threading.c:1995-2015@v3.15.0rc1`.

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

Every cell runs on the interpreter you already have, including in a browser. There is nothing to build and nothing to install beyond the cell above.

Three of the things this lesson is about only exist in a build made without the GIL, and you almost certainly are not running one. Those three arrive as recordings: the program, and what it printed when it ran in the image this project publishes. You can read the program, run the parts of it that work on your own build, and pull the same image if you want to see it for yourself.

None of the cells here start threads, so all of them work in a browser too.

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
## Which build you are on

Two ways to ask, and they answer slightly different questions. `sys._is_gil_enabled()` tells you whether the GIL is switched on right now. The build setting tells you whether this interpreter was compiled with the option at all.

{lesson.claim("An ordinary CPython build reports that the GIL is enabled and has no Py_GIL_DISABLED setting, and a free threaded build reports the opposite")}
""")


lesson.code("""
import sysconfig

print(f"  sys._is_gil_enabled()          {sys._is_gil_enabled()}")
print(f"  Py_GIL_DISABLED build setting  {sysconfig.get_config_var('Py_GIL_DISABLED')}")

if sysconfig.get_config_var("Py_GIL_DISABLED"):
    print("  you are on a free threaded build, so the cells below will match the recordings")
else:
    print("  you are on an ordinary build, so the cells below show the other half of each")
    print("  comparison and the recordings show what the free threaded build does")
""")


lesson.md(f"""
## Three lists, or none

`struct _gc_runtime_state` is where the collector keeps its state, and the shape of it depends on which build you compiled. On an ordinary build it holds an array of three `gc_generation` structures, each with a threshold, a count, and the head of a linked list that objects get chained onto. On a free threaded build it holds a `young` and two `old` structures with the thresholds and counts, and no lists {cite("Include/internal/pycore_interp_structs.h:228-234@v3.15.0rc1#generations")}.

The thresholds are the same numbers on both, 2000 and 10 and 10 {cite("Include/internal/pycore_interp_structs.h:279-286@v3.15.0rc1#GC_GENERATION_INIT")}. They are just counting something with nothing underneath it.

So where does the collector find your object? It asks the memory allocator. Every thread on this build gets its own {term("mimalloc heap")}, and one of those heaps is reserved for objects the collector cares about, so a pass means walking the allocator's own pages rather than following a chain the interpreter maintained {cite("Python/gc_free_threading.c:368-395@v3.15.0rc1#gc_visit_heaps_lock_held")}.

That removes a pointer pair from every tracked object, which is the sixteen bytes M06 measured. What was in the list is now a bit in the object header instead {cite("Include/internal/pycore_gc.h:39-45@v3.15.0rc1#_PyGC_BITS_TRACKED")}.

{figure("the-bits-that-replaced-the-lists", "the seven collector bits packed into one byte of the free threaded object header")}

M06 found that byte by reading memory: `ob_gc_bits` sits at offset 11, right after `ob_mutex`. Seven of its eight bits are spoken for, and four of them are things the collector writes during a pass.

## The same three cells, different answers

Here is M07's promotion cell again, unchanged. On an ordinary build it prints 0, then 1, then 2.

{lesson.claim("gc.get_objects takes a generation, and on an ordinary build the three generations hold different numbers of objects and an ordinary dictionary is in exactly one of them")}
""")


lesson.code(
    """
import gc

gc.disable()
gc.collect()
mine = {"tag": "follow me"}


def generations_holding(obj):
    return [g for g in range(3) if any(o is obj for o in gc.get_objects(generation=g))]


print(f"  objects in each generation  {[len(gc.get_objects(generation=g)) for g in range(3)]}")
print(f"  as soon as it exists        generations {generations_holding(mine)}")
gc.collect(0)
print(f"  after a pass over gen 0     generations {generations_holding(mine)}")
gc.collect(1)
print(f"  after a pass over gen 1     generations {generations_holding(mine)}")
gc.enable()
""",
    varies="How many objects your session has is your session's business. What matters is that "
    "the three numbers are different from each other and that the dictionary is in one "
    "generation at a time. On the build Pyodide ships the middle line reads 2 rather than 1, "
    "for the reason M07 described.",
)


lesson.md(f"""
And here is M07's ageing cell, also unchanged. On an ordinary build the old cycle survives, because it is not in the list that pass walks.

{lesson.claim("On an ordinary build a cycle made a moment ago is freed by gc.collect(0) and an identical cycle that has survived five passes is not")}
""")


lesson.code("""
import weakref


class Node:
    def __init__(self):
        self.peer = None


def make_cycle():
    left, right = Node(), Node()
    left.peer = right
    right.peer = left
    return left


gc.collect()
fresh = make_cycle()
watch_fresh = weakref.ref(fresh)
del fresh
gc.collect(0)
print(f"  a cycle made a moment ago, freed by gc.collect(0)  {watch_fresh() is None}")

gc.collect()
older = make_cycle()
watch_older = weakref.ref(older)
for _ in range(5):
    gc.collect(0)
del older
gc.collect(0)
print(f"  a cycle that survived five passes, same call       {watch_older() is None}")
""")


lesson.md(f"""
Now the same two cells on the other build.

{lesson.claim("On a free threaded build all three generations report the same objects, a new dictionary is in all three at once, and gc.collect(0) frees a cycle that has survived five passes", unobservable="generations only stop being lists in a build configured with --disable-gil, so what follows is a recording rather than a cell you run")}

{recording(NO_LISTS)}

The generation argument is still accepted. `gc.get_objects` just hands it to a function that ignores it and walks the whole heap, stopping every other thread to do so {cite("Python/gc_free_threading.c:2435-2451@v3.15.0rc1#_PyGC_GetObjects")}. And `gc.collect(0)` runs the same collection `gc.collect(2)` would; the generation number only decides which counters get reset afterwards {cite("Python/gc_free_threading.c:2064-2078@v3.15.0rc1#gc_collect_internal")}.

{figure("same-question-two-answers", "five questions from M07 with the answer each build gives")}

Which is a real trade. There is no cheap young pass on this build, so a program making a lot of short lived garbage cannot get away with a quick look at the recent stuff. Every pass is the expensive one. In exchange, no cycle is ever invisible because of its age, and nothing has to maintain a linked list under concurrent allocation.

## The count nobody owns

M07 established that the counter is tracked objects alive right now, and that it is exact. On this build the first part holds and the second does not.

The problem is that an atomic add on one shared word, for every tracked object any thread makes, would put a contention point on one of the hottest paths in the interpreter. So each thread keeps a private running total and only pushes it into the shared count once it has built up 512 {cite("Python/gc_free_threading.c:44-46@v3.15.0rc1#LOCAL_ALLOC_COUNT_THRESHOLD")} {cite("Python/gc_free_threading.c:2017-2037@v3.15.0rc1#record_allocation")}. Deallocations go the same way, with the sign flipped {cite("Python/gc_free_threading.c:2039-2062@v3.15.0rc1#record_deallocation")}.

{figure("the-count-nobody-owns", "an allocation raising a thread local counter that only reaches the shared count every 512 objects")}

Reading it from the thread that did the allocating hides all of this, because `gc.get_count` flushes the calling thread's own buffer before it answers {cite("Modules/gcmodule.c:215-240@v3.15.0rc1#gc_get_count_impl")}. So the exactness you see below is real on both builds.

{lesson.claim("Making a number of tracked objects and immediately reading gc.get_count from the same thread moves the first number by exactly that many")}
""")


lesson.code(
    """
gc.disable()
gc.collect()
base = gc.get_count()[0]
kept = []

print("  objects made    change gc.get_count reports")
for target in (200, 400, 600, 800, 1000, 1200):
    while len(kept) < target:
        kept.append([])
    print(f"  {target:>12}    {gc.get_count()[0] - base:>26}")
del kept
gc.enable()
""",
    varies="The right hand column should match the left one almost exactly, give or take a "
    "handful of objects the loop itself made. Reading from the allocating thread is exact on "
    "every build, which is the point of the recording below.",
)


lesson.md(f"""
Now read it from a thread that is not the one allocating.

{lesson.claim("On a free threaded build a helper thread that has made 400 tracked objects moves the count another thread reads by about 5, and the number the reader sees only moves in steps of 512", unobservable="the per thread allocation buffer only exists in a build configured with --disable-gil, so what follows is a recording rather than a cell you run")}

{recording(STALE_COUNT)}

The number the watching thread sees goes 5, 5, 517, 517, 517, 1029, and so on. It is not wrong so much as behind, by up to 512 for every other thread that is running.

Which is fine, because of what the number is for. Nothing reads it to make a decision that has to be correct. It is read to decide whether to schedule a collection, and being a few hundred objects late on that is not a problem {cite("Python/gc_free_threading.c:1995-2015@v3.15.0rc1#gc_should_collect")}.

That function is worth a second look, because the brake M07 spent a section on has moved. On the ordinary build the quarter rule only guards the full pass. Here there is only one kind of pass, so the same rule guards all of them: a collection is skipped unless the young count has reached a quarter of the objects that survived the last one.

## Stop the world

Here is the part with no equivalent on the ordinary build.

The collector has to work out which objects are only kept alive by each other. Doing that means comparing every object's reference count against the number of references it can find, which only works if nothing is taking or dropping a reference while it looks. On the ordinary build the GIL supplies that for free. Here it has to be arranged.

So the collection starts by stopping every other thread {cite("Python/gc_free_threading.c:2064-2078@v3.15.0rc1#gc_collect_internal")}, and does not start them again until it has found the garbage {cite("Python/gc_free_threading.c:2141-2161@v3.15.0rc1#_PyEval_StartTheWorld")}. Finalizers and weakref callbacks run afterwards, with the world going again, because those are arbitrary Python code and running them with everything parked is a good way to deadlock.

{term("stop the world")} sounds like a special mechanism and it is not. A thread that is running Python gets a bit set on its eval breaker, the same word M07 watched the collector get scheduled through, and it parks itself between two bytecode instructions {cite("Include/internal/pycore_ceval.h:348-353@v3.15.0rc1#_PY_EVAL_PLEASE_STOP_BIT")}. A thread that is already blocked in C, waiting on a socket or a lock, is marked parked where it stands and never woken at all {cite("Python/pystate.c:2385-2406@v3.15.0rc1#park_detached_threads")}. The collector then waits in one millisecond steps until the last one has stopped {cite("Python/pystate.c:2408-2443@v3.15.0rc1#stop_the_world")}.

{figure("what-stopping-costs", "how each kind of thread gets stopped and what stopping it costs")}

How long they stay stopped is how long the pass takes, and you can measure that on any build.

{lesson.claim("A full pass over a heap with two hundred thousand cycles on it takes a measurable number of milliseconds, and a pass over the same heap once those cycles are gone takes almost none")}
""")


lesson.code(
    """
import time

gc.disable()
gc.collect()

heap = []
for _ in range(200000):
    left, right = Node(), Node()
    left.peer = right
    right.peer = left
    heap.append(left)

started = time.perf_counter()
gc.collect()
took = time.perf_counter() - started
print(f"  cycles on the heap             {len(heap)}")
print(f"  one full pass over it          {took * 1000:.0f} ms")

del heap
gc.collect()
started = time.perf_counter()
gc.collect()
print(f"  and over an empty one          {(time.perf_counter() - started) * 1000:.0f} ms")
gc.enable()
""",
    varies="The milliseconds depend entirely on your machine, and in a browser they are "
    "roughly double. The shape is what matters: the first number is a real amount of time and "
    "the second is close to nothing, because the cost of a pass is the size of the heap.",
)


lesson.md(f"""
That number is a pause on a free threaded build. Every other thread in the process is parked for it, whatever it was doing.

{lesson.claim("Three threads spinning in a loop that touches nothing lose almost exactly three times the time the collector spends, which is what being stopped for the whole pass looks like", unobservable="measuring this needs several threads running Python at once, which only happens in a build configured with --disable-gil")}

{recording(NOTHING_RUNS)}

The two totals line up almost perfectly. Three threads, five passes, and the time they lost between them is three times what the collector spent, which is the arithmetic you get when all three are stopped for all of it. None of those threads shared a single object with the heap being walked.

## Why it can afford to walk everything

A build with no generations walks the whole heap on every pass, and the pause above is what that costs. So there has to be something making it cheaper than it sounds, and there is.

Before the real pass starts, the collector does a quick sweep from a known root, follows every reference it can reach, and sets the alive bit on everything it lands on {cite("Python/gc_free_threading.c:1376-1401@v3.15.0rc1#gc_mark_alive_from_roots")}. The pass proper then skips anything wearing that bit. In most programs that is nearly everything, because nearly everything really is reachable from `sys.modules`.

{figure("mark-alive-first", "the mark alive sweep setting a bit that lets the real pass skip most of the heap")}

The {term("mark alive pass")} is the reason this build's collector is not ruinous, and it is also why `gc.freeze()` turns it off. A frozen object is skipped anyway, so marking it alive is wasted work, and worse, writing the bit defeats the whole point of freezing before a fork {cite("Python/gc_free_threading.c:2099-2116@v3.15.0rc1#freeze_active")}.

Freezing itself is different here too. On the ordinary build it moves objects between lists. Here there are no lists, so it walks the heap once and sets a bit on each object {cite("Python/gc_free_threading.c:2453-2462@v3.15.0rc1#visit_freeze")}.

On 3.15 you can see roughly how much a pass considered, because `gc.get_stats()` gained a candidates field.

{lesson.claim("gc.get_stats reports a candidates count on 3.15, and after a full pass over a large heap that count is at least as large as the number of objects the collector is tracking")}
""")


lesson.code(
    """
gc.collect()
tracked = len(gc.get_objects())
stats = gc.get_stats()[2]

if "candidates" in stats:
    print(f"  objects the collector is tracking     {tracked}")
    print(f"  candidates all full passes have seen  {stats['candidates']}")
    print(f"  full passes so far                    {stats['collections']}")
    print(f"  seconds spent in them                 {stats['duration']:.4f}")
else:
    print("  this version does not report candidates, so there is nothing to compare")
    print(f"  objects the collector is tracking      {tracked}")
""",
    differs="On 3.14 there is no candidates field and the cell prints the short version. The "
    "counts themselves are whatever your session has done, so they will not match anybody "
    "else's.",
)


lesson.md(f"""
## What deferred counting does to the collector

M06 introduced deferred reference counting: for functions, classes and modules, the interpreter stops counting references taken from the evaluation stack, so the count on those objects is wrong on purpose.

That is a problem for a collector that works by comparing counts. Its fix is to walk every thread's stack and add one for each deferred reference it finds there, which puts the count back to what it should be for the duration of the pass {cite("Python/gc_free_threading.c:445-478@v3.15.0rc1#gc_visit_thread_stacks")}.

There is a corner where it cannot do that. A thread caught in the middle of closing a stack reference has a frame with no valid stack pointer, and the collector cannot read that frame safely. When it sees one, it gives up on collecting any object with deferred counting at all for that pass and treats them as reachable. Nothing leaks; the pass just does less.

This is the sort of thing that only shows up when you go looking. It is also why the free threaded collector is a good deal more code than the ordinary one for the same job.

## Try it yourself

Three things.

Take the timing cell and change 200000 to 20000, then to 2000000 if your machine has the memory. The pass time should track the number of cycles almost linearly, which is what walking everything means. Then run it once with `gc.freeze()` called just before, and see how much of the cost was walking objects that were never going to be freed.

Pull the image and run the recordings yourself: `docker run --rm -i ghcr.io/tamnd/cpython-internals/cpython:freethreaded python3 -` and paste in any of the three programs. The counter one is the most fun to change, because you can add a second helper thread and watch the reader fall behind by 1024 instead of 512.

Take the stop the world program and give the spinning threads something to do that blocks, like `time.sleep(0.001)` in the loop. A sleeping thread is parked without being woken, so the time it loses should drop sharply even though the collector is doing exactly the same work.

## What you now know

The free threaded build does not keep the collector's three lists. `struct _gc_runtime_state` has the thresholds and the counts and nothing to hang objects off.

The collector finds objects by walking the memory allocator's heaps instead. What used to be a place in a linked list is now a bit in `ob_gc_bits`, the byte M06 found at offset 11.

So every pass walks everything. `gc.get_objects(generation=N)` returns the whole heap for all three values of N, and `gc.collect(0)` frees a cycle no matter how many passes it has survived. The generation argument is accepted and ignored.

The counter is approximate. Each thread buffers 512 allocations before touching the shared count, so a thread reading it sees another thread's work up to 512 objects late. Reading it from the thread that did the allocating is exact, because that flushes first.

A collection stops every other thread. Threads running Python park between bytecode instructions on an eval breaker bit; threads blocked in C are marked parked without being woken. They stay stopped for the whole search, and only start again before finalizers run.

Three spinning threads lose about three times what the collector spends, which is what being stopped for all of it looks like.

The thing that makes walking everything affordable is a mark alive sweep from a known root, which sets a bit on everything obviously reachable so the real pass can skip it. `gc.freeze()` turns that sweep off, because a frozen object would be skipped anyway and writing the bit is exactly what freezing exists to avoid.

Deferred reference counting makes the counts wrong on purpose, so the collector walks every thread's stack and adds them back for the duration of the pass.

## What is next

M09 is the last of the memory lessons, and it is the practical one. Everything so far has been about how CPython decides what to free. That lesson is about what to do when it decides not to free something you expected it to, which happens more often than the machinery would suggest and almost never for the reason you first guess.
""")


raise SystemExit(lesson.save())
