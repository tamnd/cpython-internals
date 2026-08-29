#!/usr/bin/env python
"""T09. Memory appears and disappears.

T08 ended at the reference count. This lesson follows what happens when it reaches zero,
then finds the one shape where it never does, and then goes underneath both to the
allocator that hands out the bytes in the first place.

The spine is `pyxray/src/pyxray/heap.py`, which does three things the standard library
will not do for you: watch an object die without keeping it alive, find the reference
cycles in a graph you built, and say which collector generation is holding something.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of
them. `just lessons` checks that the committed notebook still matches this file.

The pictures come from `diagrams.py` in this directory. They are looked up on disk rather
than imported, so a diagram that has not been built yet fails here instead of producing a
notebook full of broken images.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("t09-memory-appears-and-disappears", "t09")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("t09-memory-appears-and-disappears").figure

lesson.md(f"""
# T09. Memory appears and disappears

{badge}

T08 finished on the {term("reference count")}: a small number in front of every object saying how many places are holding it. This lesson is about what happens when that number reaches zero, and about the one situation where it never does.

{figure("where-we-are", "the eight stages of the pipeline with none of them highlighted")}

Nothing is highlighted again, for the same reason as last time. This is not a stage of the pipeline, it is what happens to the values underneath every stage, all the time, while the pipeline runs.

Most languages you have used have a garbage collector and you have never had to think about when it runs. Python is different in one important way: most of the freeing happens immediately, at a moment you can predict exactly, and only a small leftover case needs a collector at all. Knowing which is which is the difference between a `close()` you can rely on and one you cannot.

By the end you will be able to watch an object die, build one that refuses to, explain the trick the collector uses to tell garbage from live data, and say why freeing a big list does not make your process smaller.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Include/refcount.h:417-429@v3.15.0rc1#Py_DECREF`.

Read it as four parts: the file, the lines, the release those line numbers belong to, and the name of the thing they are inside.

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

Everything below was checked against the version this cell prints and against 3.14. Where the two disagree, the lesson says so.
""")


lesson.code(
    """
import pyxray

pyxray.show()
""",
    differs=BANNER,
    quiet=True,
)


lesson.md("""
## Predict first

Two objects, each holding the other, and then both names go away.

```python
a = Node("a")
b = Node("b")
a.other = b
b.other = a
del a, b
```

Nothing in the program can reach either object any more. Are they gone?

Write your answer down, then run the cell.
""")


lesson.code("""
import gc
import weakref


class Node:
    def __init__(self, name):
        self.name = name
        self.other = None


gc.collect()

a = Node("a")
b = Node("b")
a.other = b
b.other = a

seen = weakref.ref(a)
del a, b

print("still there after both names went away ->", seen() is not None)
print("gc.collect() freed                     ->", gc.collect(), "objects")
print("still there now                        ->", seen() is not None)
""")


lesson.md(f"""
True, then 2, then False.

The two objects outlived every name that could reach them, and stayed in memory until something else came along and swept them up. If you had written this in a loop you would have a program whose memory use climbs and never comes back down until the collector decides to run.

That is the shape of this lesson. Most of the time Python frees things the instant you let go of them, and this is the case where it does not, so the rest of the material is about why, and about what sits underneath.

## The count that decides everything

Every object carries a count of how many places are currently holding it, and {lesson.claim("binding an object to a name adds one to its count and putting it in a container adds another, and dropping either takes one away again")}. When the count reaches zero the object is freed, right then, before the next line of your program runs.
""")


lesson.md(f"""
{figure("the-count-moves", "a table of six lines of Python and the reference count after each one")}

Here is the count moving. The demo is inside a function on purpose, because at the top level of a notebook the module's own dictionary holds an extra reference to everything and every number below would be one higher.
""")


lesson.code("""
from pyxray import obj


def watch():
    thing = [1, 2, 3]
    print(f"{'thing = [1, 2, 3]':<22} {obj.refcount(thing)}")

    holder = [thing]
    print(f"{'holder = [thing]':<22} {obj.refcount(thing)}")

    box = {"k": thing}
    print(f"{'box = {k: thing}':<22} {obj.refcount(thing)}")

    holder.clear()
    print(f"{'holder.clear()':<22} {obj.refcount(thing)}")

    del box
    print(f"{'del box':<22} {obj.refcount(thing)}")


watch()
""")


lesson.md(f"""
1, 2, 3, 2, 1. When `watch` returns, `thing` goes out of scope, the count reaches zero, and the list is freed before the next statement in the notebook starts.

The C behind that is very short for a piece of code the whole language rests on.

{cite("Include/refcount.h:417-429@v3.15.0rc1#Py_DECREF")}

It subtracts one, and if the result is zero it frees the object. Everything else in this lesson is a consequence of those two lines, including the gap in them, which is that neither line ever fires for two objects that are only holding each other.

The immortality check at the top is the 3.14 change T08 ended on. `None`, `True`, small integers and every interned string skip the count entirely, so this function does nothing at all for a large fraction of the objects it is called on.

The work at zero happens in one function.

{cite("Objects/object.c:3282-3300@v3.15.0rc1#_Py_Dealloc")}

The comment above it is worth reading. Freeing a list frees everything in it, which can free everything in those, and a long enough chain of that is a stack overflow in the C code. CPython watches how much C stack is left and, when it gets close, puts the object on a queue to be freed later instead. That mechanism is called the trashcan, and it is the reason deleting a linked list of a million nodes does not crash the interpreter.

## Watching the moment it dies

You cannot observe a free with an ordinary variable, because holding the object is exactly what stops it happening. What you need is a reference that does not count, which is what a {term("weak reference")} is for, and {lesson.claim("a weak reference lets you watch an object go without keeping it alive, because it is the one kind of reference that does not add to the count")}.
""")


lesson.code("""
from pyxray import heap


class Node:
    def __init__(self, name):
        self.name = name
        self.other = None


def plain():
    watcher = heap.Deaths()
    value = watcher.watch("value", Node("value"))
    print("after binding it  ", watcher.alive("value"))

    del value
    print("after del         ", watcher.alive("value"))
    print("freed so far      ", watcher.gone)


plain()
""")


lesson.md(f"""
`heap.Deaths` is a thin wrapper over `weakref.ref` with a callback, and the callback is the interesting part. It runs at the moment the object is freed, which means it runs from inside the {term("deallocation", "deallocator")}.

{cite("Objects/weakrefobject.c:1001-1024@v3.15.0rc1#PyObject_ClearWeakRefs")}

Look at the third condition in that check: `Py_REFCNT(object) != 0`. This function refuses to run unless the count is already zero. By the time your callback fires, the object is past saving, which is why a weakref callback is handed the dead reference rather than the object.

Not everything can be watched this way. `int`, `str` and `tuple` have no room for a weak reference list, and neither does a class using `__slots__` without `__weakref__` in it. Trying gets you a clear error rather than a confusing one.

## When `__del__` runs

If a class defines `__del__`, that method is its {term("finalizer")}, and it runs during the free. Because the free is immediate, so is `__del__`: {lesson.claim("a finalizer runs at the del itself, so its output lands in the middle of the surrounding prints rather than at the end of the function or the end of the program")}. This is the property that makes people say Python has deterministic destruction.
""")


lesson.code("""
class Loud:
    def __init__(self, name):
        self.name = name
        self.other = None

    def __del__(self):
        print(f"  {self.name} is being freed")


def timing():
    print("before")
    x = Loud("x")
    print("bound")
    del x
    print("after")


timing()
""")


lesson.md("""
The message lands between "bound" and "after", not at the end of the function and not at the end of the program.

It is worth being clear about how much you should lean on this. It is real, and it is genuinely useful, and it is also a CPython implementation detail. PyPy and other implementations do not reference count, so the same code there frees the object at some later point of the runtime's choosing. `with` blocks exist because they make the timing part of the language instead of part of the implementation. Use `__del__` for a last resort cleanup and `with` for cleanup you actually depend on.

## The shape counting cannot free
""")


lesson.md(f"""
{figure("a-cycle", "two objects holding each other, before and after their names go away")}

Both counts start at 2, one for the name and one for the other object. Dropping both names takes each count to 1 and stops there, so {lesson.claim("two objects that hold each other keep each other's count above zero after every name to them has gone, and counting alone never frees either one")}. What does free them is the collector: {lesson.claim("running gc.collect() by hand frees a pair that dropping their names did not")}.

None of this is exotic. A doubly linked list is full of {term("reference cycle", "reference cycles")}, and so is a tree whose nodes carry a parent pointer. An exception traceback holds the {term("frame")} and the frame holds the exception. A {term("closure")} that refers to the function it lives in is a cycle. Any real program makes these constantly.
""")


lesson.code(
    """
import gc


def compare():
    watcher = heap.Deaths()

    lonely = watcher.watch("lonely", Node("lonely"))
    left = watcher.watch("left", Node("left"))
    right = watcher.watch("right", Node("right"))
    left.other = right
    right.other = left

    del lonely, left, right
    print("after dropping all three names:")
    print(watcher.report())

    print()
    print("collector freed", gc.collect(), "objects")
    print(watcher.report())


compare()
""",
    varies="The number of objects the collector reports freeing counts whatever else the interpreter had waiting as well as the cycle, so it depends on the version and on what has already run. Which of the three nodes survive does not.",
)


lesson.md(f"""
`lonely` is already gone before the collector is asked anything. The other two need it.

{figure("two-ways-to-free", "reference counting and the cycle collector side by side")}

The important row is the last one on each side. Counting cannot free a cycle, and cycles are the only reason the {term("cycle collector")} exists. If you never made one, `gc.collect()` would have nothing to do.

## How the collector actually decides

The obvious way to write a garbage collector is to start from the things you know are alive, follow every reference, and free whatever you never reached. CPython does not do that, because it has no complete list of the roots. Instead it works out, for a group of candidate objects, whether the only things holding them are each other.
""")


lesson.md(f"""
{figure("the-subtract-trick", "the three steps the collector takes to tell garbage from live data")}

Step one takes a scratch copy of every candidate's real reference count, so the real counts are never touched.

{cite("Python/gc.c:393-412@v3.15.0rc1#update_refs")}

Step two walks each candidate and subtracts one from the scratch copy of everything it points at. `tp_traverse` is the function every container type implements to say what it holds, and it is the same thing `gc.get_referents` gives you from Python.

{cite("Python/gc.c:485-501@v3.15.0rc1#subtract_refs")}

The arithmetic is what pays off here. A scratch count of zero means every reference to that object came from inside the group. A count above zero means somebody outside is holding it, and that somebody was never on the candidate list, so it is alive and so is everything it can reach.

{cite("Python/gc.c:566-583@v3.15.0rc1#move_unreachable")}

You can run the same idea from Python: {lesson.claim("gc.get_referents plus a search for strongly connected components finds the same groups of objects that can all reach each other, which is what heap.cycles does")}.
""")


lesson.code("""
def find():
    first = Node("first")
    second = Node("second")
    third = Node("third")
    first.other = second
    second.other = third
    third.other = first

    for cycle in heap.cycles(first):
        print(cycle.describe())


find()
gc.collect()
""")


lesson.md(f"""
One cycle with three members, closed into a ring. The order the names print in is the order the search finished them in rather than the direction the references run, so read it as a membership list rather than a route.

`heap.cycles` hands back names rather than objects, which is a small decision worth explaining. Returning the objects would give you a fresh reference to each of them, and a tool for finding things that outlive their references should not be one of the reasons they are still here.

## `__del__` on a cycle

There used to be a nasty corner here. Before Python 3.4, a cycle whose members defined `__del__` could not be collected at all, because the collector had no safe order to run the finalizers in. Those objects went on a list called `gc.garbage` and stayed there for the life of the process.

PEP 442 fixed it. Finalizers now run before anything is freed, each one exactly once, and then the collection proceeds, so {lesson.claim("a cycle whose members define __del__ is collected like any other, with every finalizer run and gc.garbage left empty")}.
""")


lesson.code("""
def pep442():
    gc.collect()

    left = Loud("left")
    right = Loud("right")
    left.other = right
    right.other = left
    del left, right
    print("names gone, nothing has run yet")

    print("collector freed", gc.collect(), "objects")
    print("gc.garbage:", gc.garbage)


pep442()
""")


lesson.md(f"""
Both `__del__` methods run, `gc.garbage` stays empty, and the memory comes back. If you find advice online about avoiding `__del__` because it leaks cycles, it was written before 2014.

{cite("Python/gc.c:1041-1074@v3.15.0rc1#finalize_garbage")}

The `_PyGC_SET_FINALIZED` flag is what guarantees "exactly once". A finalizer is allowed to store `self` somewhere and bring the object back to life, and if that object dies again later the collector must not call the finalizer a second time.

## Generations

Running the whole subtract trick over every object in the process would be far too slow to do often. So {lesson.claim("the collector sorts objects into three groups by how long they have survived, and Python can be asked which group any object is in")}, and it looks at the young group far more often than the old one.
""")


lesson.md(f"""
{figure("generations", "the three collector generations and how often each is examined")}

The bet is that most objects die young, which is true of nearly every Python program. The temporary list inside a loop is gone before the loop turns over. Anything still here after two collections is probably going to stay, so it gets looked at rarely, and {lesson.claim("an object starts in the youngest group and moves up one place each time it survives a sweep")}.
""")


lesson.code("""
class Plain:
    def __init__(self):
        self.other = None


gc.collect()
value = Plain()

print("thresholds                 ", gc.get_threshold())
print("a fresh object is in       ", heap.generation_of(value))

gc.collect(0)
print("after one sweep of gen 0   ", heap.generation_of(value))

gc.collect(1)
print("after one sweep of gen 1   ", heap.generation_of(value))

print("what generation is 42 in?  ", heap.generation_of(42))
""")


lesson.md(f"""
`(2000, 10, 10)` and then 0, 1, 2, and `None`.

Read the thresholds as three different kinds of number. The first one is a count of objects: when allocations minus frees since the last pass exceeds 2000, generation 0 is examined. The other two are counts of collections: after 10 passes over generation 0, generation 1 gets a look, and after 10 of those, generation 2 does.

{cite("Include/internal/pycore_interp_structs.h:271-286@v3.15.0rc1#GC_GENERATION_INIT")}

The first number was 700 for many years and became 2000 in 3.13. If you have read a blog post quoting 700, that is why.

The `None` at the end is the other half of the story. {lesson.claim("the collector does not track an object that cannot hold a reference to another object, so an integer or a string is in no generation at all")}, because a thing that cannot point at anything can never be part of a cycle. Not tracking them is the single largest thing the collector does for performance, since it removes most of the objects in a typical program from consideration entirely.
""")


lesson.code("""
gc.collect()

for value in [42, "text", (1, 2), [1, 2], {"k": 1}, (1, [2])]:
    print(f"{value!s:<12} tracked: {gc.is_tracked(value)}")
""")


lesson.md(f"""
The two tuples are the interesting pair. A tuple is a container, so it starts out tracked, but a tuple holding only untracked things can never be on a cycle either. The collector notices this the first time it looks at one and stops tracking it. That is why `(1, 2)` prints False here and would print True if you built it and asked immediately, and why `(1, [2])` stays tracked forever.

## Where the bytes came from

Everything up to here has been about deciding when to free. Underneath that is a separate question: where the memory came from in the first place, and where it goes back to.

Python objects are small and there are a lot of them. A program that called the operating system's `malloc` for every 56 byte list would spend most of its time in the allocator. So CPython has its own allocator sitting on top, called {term("obmalloc")}, and it works in four layers.
""")


lesson.md(f"""
{figure("the-allocator-layers", "blocks inside a pool inside an arena inside the operating system")}

Your object sits in a {term("block")}. Blocks of the same size share a {term("pool")}, pools share an {term("arena")}, and only the arena ever talks to the operating system, which it does with one big request now and then rather than a small request constantly.

{cite("Include/internal/pycore_obmalloc.h:216-226@v3.15.0rc1#ARENA_BITS")}

{cite("Include/internal/pycore_obmalloc.h:232-241@v3.15.0rc1#POOL_BITS")}

There is a size limit on all of this: {lesson.claim("requests over 512 bytes go to the system allocator, and everything under that is rounded up to one of a fixed set of sizes")}.

{cite("Include/internal/pycore_obmalloc.h:156-164@v3.15.0rc1#SMALL_REQUEST_THRESHOLD")}

Under that limit, every request is rounded up to one of a fixed set of sizes.

{figure("size-classes", "the size classes small requests are rounded up to")}

{cite("Include/internal/pycore_obmalloc.h:128-146@v3.15.0rc1#ALIGNMENT")}

Rounding up is what makes reuse cheap. A pool holds blocks of exactly one size, so a freed block fits any future object in the same class without any searching, measuring or splitting. The cost is a few wasted bytes per object and the benefit is an allocator fast enough that nobody thinks about it.
""")


lesson.code(
    """
import ctypes
import sys

# The header picks the alignment from the pointer size, so this does too rather than
# writing 16 down. On a 32 bit build, which is what you get in a browser, it is 8.
ALIGNMENT = 16 if ctypes.sizeof(ctypes.c_void_p) > 4 else 8
THRESHOLD = 512


def rounded(want):
    return ALIGNMENT * ((want + ALIGNMENT - 1) // ALIGNMENT)


print("alignment here:", ALIGNMENT, "bytes")
print("size classes:  ", THRESHOLD // ALIGNMENT)
print()
for want in [1, 16, 17, 56, 88, 500, 512, 513]:
    served = "the system allocator" if want > THRESHOLD else rounded(want)
    print(f"ask for {want:>4} bytes -> {served}")

empty = sys.getsizeof([])
print()
print(f"an empty list is {empty} bytes, takes {rounded(empty)}, wastes {rounded(empty) - empty}")
""",
    varies="On a 32 bit build, which is what a browser gives you, the alignment is 8 rather than 16, there are 64 size classes rather than 32, and the rounded up numbers change with them.",
)


lesson.md(f"""
The last line of that cell is the arrangement charging its fee. On a 64 bit machine an empty list is 56 bytes and takes a 64 byte block, so 8 bytes go unused. A few wasted bytes per object, in exchange for never having to search for a block that fits.

## Giving it back

Freeing a large object usually does not make your process smaller, which catches most people out the first time they measure it.

{figure("giving-it-back", "the four steps between a count reaching zero and the operating system hearing about it")}

The block goes back to its pool.

{cite("Objects/obmalloc.c:2594-2607@v3.15.0rc1#insert_to_freepool")}

The pool stays in its arena. The arena goes back to the operating system only when every single pool inside it is empty, and even then only if it is not the last free arena, because a program that allocates and frees in a loop would otherwise thrash.

{cite("Objects/obmalloc.c:681-700@v3.15.0rc1#_PyMem_ArenaFree")}

{lesson.claim("one surviving object anywhere in an arena keeps the whole arena, which is why a process that peaked at two gigabytes usually still looks like it is using two gigabytes afterwards", unobservable="an arena is not an object and Python has no way to name one, and how much memory the operating system thinks the process holds is not a number the standard library reports")}. It is also why "Python has a memory leak" is usually "Python is holding onto arenas that are mostly empty", and why the next allocation is fast.

You can watch the counts move with `sys.getallocatedblocks`, which counts blocks handed out rather than bytes, and {lesson.claim("building ten thousand objects and then dropping them brings the count of blocks in use back to roughly where it started")}.
""")


lesson.code(
    """
before = heap.allocated()
kept = [Plain() for _ in range(10_000)]
after = heap.allocated()

del kept
gc.collect()
freed = heap.allocated()

print("blocks in use at the start ", before)
print("after building 10000       ", after)
print("after dropping them        ", freed)
""",
    varies="These are counts of blocks in your own process, so the two outer numbers depend on what the interpreter has already done. The 10000 that appear and then go away again is the part to read.",
)


lesson.md(f"""
The middle number is about ten thousand higher and the last one is back where it started, so the blocks came back. Whether the operating system ever hears about it is a separate question, and the answer is usually no.

The clearest way to see that the memory really is reused is to watch an address come back: {lesson.claim("freeing an object and immediately building another of the same size usually puts the new one at the address the old one had")}.
""")


lesson.code(
    """
gc.collect()

first = Plain()
where = id(first)
del first

second = Plain()
print("first object was at ", hex(where))
print("second object is at ", hex(id(second)))
print("same address reused ->", id(second) == where)
""",
    varies="Almost always True, but it is the allocator's choice rather than a promise. If anything else asked for a block of that size between the two lines, the second object goes somewhere else and this prints False.",
)


lesson.md(f"""
The same address, almost every time. The first object freed its block back to a pool, and the very next request for that size class got the same block. This is also a good reminder that `id()` is only unique among objects that are alive at the same moment, which is the footnote T08 put on it.

## What to reach for

{figure("what-to-reach-for", "a table of six questions and the tool that answers each one")}

Five of those six are in the standard library. The only thing this lesson needed its own code for is finding cycles, and that is because `gc` will tell you that it collected some objects but not which ones or what shape they were in.

## Try it yourself

**One.** Build a cycle with `gc.disable()` in force, in a loop, ten thousand times, and watch `sys.getallocatedblocks` climb. Then enable the collector and collect. Work out roughly how much memory each iteration was costing you.

**Two.** Write a class that resurrects itself in `__del__` by storing `self` in a module level list. Put two of them in a cycle, collect, and find out how many times each finalizer ran. Then explain the `_PyGC_SET_FINALIZED` flag from the source above without looking at it again.

**Three.** `gc.get_referrers(x)` tells you what is holding `x`. Use it on a list you have hidden inside a nested structure and find the container. Then work out why the answer includes a frame object and what that means for using this in a function.

**Four.** Find the size where an object stops coming from the pools and starts coming from the system allocator, using nothing but `sys.getallocatedblocks` and a loop over `bytes` objects of increasing length. The number will not be exactly 512 and working out the offset is the exercise.

**Five.** Take the tuple tracking result above and turn it into a rule. Build five containers, predict `gc.is_tracked` for each before and after a collection, and get all ten right.

## What just happened

Almost all freeing in CPython is immediate. The count drops to zero, the deallocator runs, and the memory is back before the next line of your program. That is why `__del__` fires when it does and why CPython feels different from a runtime with a tracing collector.

Counting has exactly one blind spot: a group of objects holding each other keeps every count above zero forever. The cycle collector exists for that case and no other.

It finds them by copying the counts, subtracting every reference that comes from inside the candidate group, and seeing what is left. Anything at zero was held only by its neighbours. Anything above zero has a holder outside the group and survives, along with everything it can reach.

It does this on a schedule based on three generations, because most objects die young and re-examining the survivors constantly would be wasted work. Objects that cannot hold references are not tracked at all, which removes most of a typical program from the problem.

Underneath both mechanisms is an allocator that hands out fixed size blocks from pools inside arenas. Freeing returns a block to a pool, and the arena goes back to the operating system only when it is completely empty, which is why your process rarely shrinks.

## Where this goes next

You now know what an object is and what happens to it from the moment it is built to the moment its memory is reused. T10 puts the whole first part together on one page: the pipeline from T02 through T07, the object model from T08, and this, drawn as one diagram you can keep next to you for the rest of the material.
""")


raise SystemExit(lesson.save())
