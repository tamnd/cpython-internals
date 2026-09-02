#!/usr/bin/env python
"""M09. What will not go away.

The last of the memory lessons, and the practical one. M01 through M08 were about how CPython
decides what to free. This one is about what to do when it decides not to free something you
expected it to, which is a procedure rather than a mechanism.

Four questions in order, six tools, and the two chains that catch real code: an exception saved
in a variable, and a cache that keeps self alive. Everything here runs anywhere, including in a
browser, so there are no recordings.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("m09-what-will-not-go-away", "m09")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("m09-what-will-not-go-away").figure


lesson.md(f"""
# M09. What will not go away

{badge}

Eight lessons on how CPython decides what to free. This one is about the afternoon where it decided not to free something and you cannot work out why.

The good news is that this is a procedure, not a mystery. There are four questions, they have to be asked in order, and each answer tells you which question is next.

{figure("four-questions-in-order", "the four questions to ask in order, each with the tool that answers it")}

The bad news is that every tool here has a blind spot, and none of them say so. Most of this lesson is about what each one cannot see, because that is where the afternoon goes.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/gc.c:1665-1684@v3.15.0rc1`.

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

Every cell runs on the interpreter you already have, including in a browser. Nothing here needs a special build, a debug build or a second process, which is a nice change after M08.

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
## Question one, is anything actually growing

Before anything else, get a number. The usual instinct is to watch the process size in Activity Monitor or `top`, and that number is a bad first measurement, because M02 explained why: `pymalloc` keeps arenas around after the objects in them are gone, so a program can free everything and still look enormous to the operating system.

`sys.getallocatedblocks()` is the number to start with. It counts blocks the interpreter has handed out and not taken back, so it drops the moment your objects are freed, whatever the allocator does with the pages afterwards {cite("Python/sysmodule.c:2051-2064@v3.15.0rc1#sys_getallocatedblocks_impl")}.

Not every build keeps that count, so the cell checks before it reports. A browser is one of the builds that does not.

{lesson.claim("Making a hundred thousand objects and then dropping them puts sys.getallocatedblocks back within a handful of where it started")}
""")


lesson.code(
    """
import gc

gc.collect()
start = sys.getallocatedblocks()

hoard = [[] for _ in range(100000)]
peak = sys.getallocatedblocks()

del hoard
gc.collect()
after = sys.getallocatedblocks()

if start == 0 and peak == 0:
    print("  this build does not keep the count, so the number is always 0")
    print("  a browser is one of those, and so is a build made without pymalloc")
else:
    print(f"  blocks at the start    {start}")
    print(f"  blocks while holding   {peak}  which is {peak - start} more")
    print(f"  blocks after dropping  {after}  which is {after - start} more")
""",
    varies="The absolute numbers are whatever your session has already done. The two "
    "differences are the point, and the second one should be close to zero. In a browser the "
    "count is not kept at all and you get the short version.",
)


lesson.md(f"""
Run that with the process size next to it some time. The blocks go back down and the resident size usually does not, and that difference is the single most common thing mistaken for a leak.

## Question two, does a pass free it

If the blocks stay up, the next question is whether the collector can get it. `gc.collect()` returns how many objects it freed, so calling it by hand and looking at the number splits the problem in two: either you have a cycle the collector will eventually get to, or you have something that is genuinely still referenced.

Here is a shape that turns up constantly in real code. A parent keeps a list of children, and each child keeps a reference back to its parent. Nothing looks wrong with it and it makes a cycle every time.

{lesson.claim("A parent holding a list of children that each point back at it is unreachable garbage the moment the function returns, and one collection frees five objects")}
""")


lesson.code("""
class Parent:
    def __init__(self):
        self.children = []


class Child:
    def __init__(self, parent):
        self.parent = parent
        parent.children.append(self)


def build_a_family():
    parent = Parent()
    for _ in range(3):
        Child(parent)


gc.collect()
build_a_family()
print(f"  objects the pass freed  {gc.collect()}")
print("  one parent, one list, three children, all of them holding each other")
""")


lesson.md(f"""
That number tells you it was a cycle, but not what was in it. For that you need to stop the collection from actually freeing things.

{term("DEBUG_SAVEALL")} does exactly that. With the flag set, a pass appends every object it was about to free to `gc.garbage` and clears nothing {cite("Python/gc.c:1082-1110@v3.15.0rc1#delete_garbage")}. So after one collection you are holding the exact set of objects that were only kept alive by each other, and you can look at them.

{lesson.claim("With DEBUG_SAVEALL set, the same collection leaves five objects in gc.garbage, and they are the parent, its list, and the three children")}
""")


lesson.code("""
import collections

gc.collect()
gc.set_debug(gc.DEBUG_SAVEALL)
build_a_family()
freed = gc.collect()

kinds = collections.Counter(type(o).__name__ for o in gc.garbage)
print(f"  the pass found  {freed}  objects")
for name, count in sorted(kinds.items()):
    print(f"    {count} x {name}")

gc.garbage.clear()
gc.set_debug(0)
gc.collect()
""")


lesson.md(f"""
Remember to clear the list and turn the flag off, as the cell does. While it is set, nothing the collector finds is ever freed, so you have swapped a leak you were investigating for one you built.

## The trap in gc.garbage

You may have read that a class with a `__del__` method makes its cycles uncollectable and dumps them in `gc.garbage`. That was true a long time ago. It is worth being clear about, because it sends people looking in an empty list.

The check the collector makes is `has_legacy_finalizer`, and it is one line: does the type have a `tp_del` slot {cite("Python/gc.c:678-683@v3.15.0rc1#has_legacy_finalizer")}. A `__del__` written in Python fills in `tp_finalize`, not `tp_del`, and has done since PEP 442 landed in 3.4. Nothing you write in Python ends up in `gc.garbage` by that route {cite("Python/gc.c:1011-1039@v3.15.0rc1#handle_legacy_finalizers")}.

{figure("how-things-reach-gc-garbage", "the four routes into gc.garbage and how likely each one is to be yours")}

{lesson.claim("A cycle of two objects whose class defines __del__ is collected normally and leaves gc.garbage empty")}
""")


lesson.code("""
class Noisy:
    def __del__(self):
        pass


gc.collect()
gc.garbage.clear()

first, second = Noisy(), Noisy()
first.peer = second
second.peer = first
del first, second

print(f"  objects the pass freed   {gc.collect()}")
print(f"  objects in gc.garbage    {len(gc.garbage)}")
print("  the __del__ ran, the cycle went away, and the list stayed empty")
""")


lesson.md(f"""
If `gc.garbage` is not empty in a real program, it is worth taking seriously, because it means a C extension is still using the old slot. That is rare, and it is a bug report.

## Question three, who is holding it

This is the one you actually want answered, and the tool for it is `gc.get_referrers`. Give it an object and it hands back everything that points at it.

It is worth knowing what it does, because how it works is the same as what it cannot do. It walks every tracked object in every generation and calls that object's `tp_traverse`, checking whether the thing you asked about comes up {cite("Python/gc.c:1665-1684@v3.15.0rc1#gc_referrers_for")} {cite("Python/gc.c:1686-1702@v3.15.0rc1#_PyGC_GetReferrers")}. There is no index and no back pointer anywhere. It is a walk of the whole heap, every time you call it {cite("Modules/gcmodule.c:242-260@v3.15.0rc1#gc_get_referrers_impl")}.

Two consequences. It is slow enough that you would not put it in a loop. And a {term("referrer")} that the collector cannot see does not exist as far as it is concerned, which brings back something M07 taught you: a tuple of only immutable things gets untracked. It can be holding your object and it will never turn up in the answer.

{lesson.claim("A tuple that is still tracked turns up in gc.get_referrers for the object it holds, and an untracked tuple holding the same object does not")}
""")


lesson.code(
    """
target = 1.2345e300
tracked_holder = (target, [])
untracked_holder = (target, "just a string")

gc.collect()
gc.collect()
print(f"  is the first tuple tracked   {gc.is_tracked(tracked_holder)}")
print(f"  is the second tuple tracked  {gc.is_tracked(untracked_holder)}")

found = gc.get_referrers(target)
print(f"  referrers reported           {sorted(type(o).__name__ for o in found)}")
print(f"  the tracked tuple is there   {any(o is tracked_holder for o in found)}")
print(f"  the untracked one is there   {any(o is untracked_holder for o in found)}")
""",
    varies="The list of type names picks up whatever else in your session happens to be "
    "holding that number, usually a dict for the namespace this cell is running in. The two "
    "lines under it are the part that matters, and they read True and then False.",
)


lesson.md(f"""
So a `gc.get_referrers` result that comes back empty means one of two things, and it does not tell you which: nothing is holding your object, or something is holding it that the collector cannot see.

## What an object holds, the other direction

`gc.get_referents` is the same idea pointing the other way, and it is cheap, because it just calls one object's `tp_traverse` and collects whatever comes out {cite("Modules/gcmodule.c:262-288@v3.15.0rc1#append_referrents")} {cite("Modules/gcmodule.c:290-322@v3.15.0rc1#gc_get_referents_impl")}.

The same blind spot applies, and it is easier to see here.

{lesson.claim("gc.get_referents on a long string returns nothing at all, even though the string is holding a large amount of memory")}
""")


lesson.code("""
big_string = "x" * 5000000

print(f"  the string holds       {sys.getsizeof(big_string)} bytes")
print(f"  what the collector sees {gc.get_referents(big_string)}")
print(f"  is it even tracked      {gc.is_tracked(big_string)}")
print()

instance = Parent()
print(f"  referents of an instance {sorted(type(o).__name__ for o in gc.get_referents(instance))}")
print("  the list is its one attribute and the type is its class")
""")


lesson.md(f"""
Five megabytes, no referents, not even tracked. `str` has no `tp_traverse` because it cannot hold another object, and the collector's graph is a graph of objects rather than of memory.

{figure("the-graph-you-can-walk", "what the referrer tools can see against what actually holds memory")}

This is the single most useful thing to keep in mind while doing this. You are walking the collector's graph. It is a very good approximation of the real one and it is not the real one.

## The exception that keeps a function alive

Now two chains that catch real code. Here is the first.

When an exception propagates, each frame it passes through gets added to the traceback, and the traceback object holds a strong reference to the frame {cite("Python/traceback.c:79-98@v3.15.0rc1#tb_create_raw")} {cite("Python/traceback.c:311-330@v3.15.0rc1#PyTraceBack_Here")}. The frame holds every local variable in it. So an exception you saved in a variable is holding everything that was in scope when it was raised, however large.

{figure("the-exception-chain", "one saved exception holding a traceback holding a frame holding every local")}

{lesson.claim("An object that only exists as a local variable in a function that raised is still alive afterwards if the exception was saved, and dies as soon as the exception is dropped")}
""")


lesson.code("""
import weakref


class Payload:
    pass


def does_some_work():
    payload = Payload()
    watch = weakref.ref(payload)
    try:
        raise ValueError("something went wrong")
    except ValueError as problem:
        return watch, problem


gc.collect()
watch, saved = does_some_work()
chain = [type(saved).__name__, type(saved.__traceback__).__name__]
chain.append(type(saved.__traceback__.tb_frame).__name__)
print(f"  the chain                        {' -> '.join(chain)}")
print(f"  payload is in the frame's locals {'payload' in saved.__traceback__.tb_frame.f_locals}")
print(f"  payload alive, exception held    {watch() is not None}")

del saved
gc.collect()
print(f"  payload alive, exception dropped {watch() is not None}")
""")


lesson.md(f"""
This is why `except ValueError as problem:` deletes `problem` for you at the end of the block. The language does it because otherwise every caught exception would keep a frame alive until the next assignment. It only helps inside the block, though. The moment you store the exception somewhere that outlives it, you own the whole chain again.

The same thing applies to `sys.exc_info()`, to a logging call that keeps the exception, and to any error object you put in a list to look at later.

## The cache that keeps self alive

The second chain is `functools.lru_cache` on a method, and it catches people because it looks like an optimisation rather than a decision about lifetimes.

An `lru_cache` keys its dictionary on the arguments. With no keyword arguments and `typed` off, the key it builds is the argument tuple itself {cite("Modules/_functoolsmodule.c:1237-1256@v3.15.0rc1#lru_cache_make_key")}, and that tuple goes into a dictionary the wrapper owns {cite("Modules/_functoolsmodule.c:1309-1330@v3.15.0rc1#infinite_lru_cache_wrapper")}. The wrapper is created once when the class body runs, so it lives as long as the class does.

On a method, the first argument is `self`. So every instance you ever call that method on is in a tuple in a dictionary on the class, and none of them are ever going away.

This is well enough known that the linter this repository uses has a rule for it, B019, and the cell below has to switch it off to make the point.

{lesson.claim("An instance whose cached method has been called once stays alive after every reference to it is dropped, and the referrer holding it is a tuple")}
""")


lesson.code("""
import functools


class Service:
    @functools.lru_cache(maxsize=None)  # noqa: B019, UP033
    def lookup(self, key):
        return key.upper()


gc.collect()
service = Service()
watch = weakref.ref(service)
service.lookup("anything")

del service
gc.collect()
print(f"  instance alive after del  {watch() is not None}")
print(f"  what is holding it        {sorted(type(o).__name__ for o in gc.get_referrers(watch()))}")
print(f"  the cache                 {Service.lookup.cache_info()}")

Service.lookup.cache_clear()
gc.collect()
print(f"  instance alive after clear {watch() is not None}")
""")


lesson.md(f"""
A `tuple`, which is the key. That is `lru_cache_make_key` returning the argument tuple unchanged, and `self` is the first thing in it.

The fix is not to stop using the cache. It is to put the cache somewhere with the right lifetime: a `functools.cached_property` on the instance, a per instance cache built in `__init__`, or a plain function taking only the values it needs.

## Question four, where did it come from

The last question is the one `gc` cannot answer at all. You have found the object, you know what is holding it, and you still do not know which line of your program made it.

`tracemalloc` answers that, and the way it does it explains both its power and its cost. Starting it replaces the interpreter's memory allocators with wrappers of its own {cite("Python/tracemalloc.c:805-840@v3.15.0rc1#_PyTraceMalloc_Start")}, which is the same `PyMem_SetAllocator` mechanism M01 introduced. Every allocation after that captures the current Python stack and files it away {cite("Python/tracemalloc.c:499-530@v3.15.0rc1#tracemalloc_alloc")}. That is why it can tell you the exact line, and why it is not something you leave on.

{lesson.claim("Comparing two tracemalloc snapshots taken either side of an allocation reports the line that did it, with a size close to what was allocated")}
""")


lesson.code(
    """
import tracemalloc

tracemalloc.start()
before = tracemalloc.take_snapshot()

kept = [bytearray(1000) for _ in range(2000)]

after = tracemalloc.take_snapshot()
biggest = after.compare_to(before, "lineno")[0]
tracemalloc.stop()

print(f"  bytes we asked for       {2000 * 1000}")
print(f"  biggest growth reported  {biggest.size_diff} bytes in {biggest.count_diff} blocks")
print(f"  where                    {biggest.traceback[0].filename}:{biggest.traceback[0].lineno}")
del kept
""",
    varies="The reported size is a little over two megabytes, because every bytearray carries a "
    "header as well as its thousand bytes. The filename depends on how you are running this: a "
    "notebook gives you a cell name, a script gives you the script.",
)


lesson.md(f"""
In a real investigation you would take the first snapshot after startup, let the program do whatever it does for a while, take the second, and read the top ten. The line at the top is usually where the object is made rather than where it is kept, which is worth remembering, but it is a much better starting point than nothing.

{figure("which-tool-answers-what", "six tools with the question each answers and what each costs")}

## Try it yourself

Three things.

Take the parent and child cell and give `Child` a `weakref.ref(parent)` instead of a plain reference. The cycle goes away and `gc.collect()` returns 0, because a weak reference is not an edge in the graph. This is the standard fix for a parent link, and M07's lesson on weak references covers what you give up.

Put `gc.get_referrers` in a timing loop and see what a heap walk costs. Make a hundred thousand objects first, then time one call. Then try `gc.get_referents` on the same object and compare. The difference between a whole heap walk and one `tp_traverse` is the difference between a tool you can call and one you can call in a loop.

Take the `lru_cache` example and change `maxsize=None` to `maxsize=1`, then make two instances and call the method on each. The first instance is evicted when the second arrives, so it dies, and the cache turns from a leak into a leak with a bound on it. That is often enough in practice, and it is a much smaller change than restructuring the code.

## What you now know

Ask the four questions in order. Is anything growing, does a pass free it, who is holding it, where did it come from. Skipping to the third one is how the afternoon goes.

`sys.getallocatedblocks()` is a better first number than the process size, because `pymalloc` keeps arenas after the objects in them are freed, so the operating system's number lags a long way behind the truth.

`gc.collect()` returns what it freed, which splits the problem into a cycle you can wait for and a reference you have to find. `gc.set_debug(gc.DEBUG_SAVEALL)` gets you the actual objects, because it appends them to `gc.garbage` instead of clearing them. Turn it off and empty the list afterwards, or you have built a leak while looking for one.

`gc.garbage` is empty in modern Python and that is normal. The check is `tp_del`, which a `__del__` written in Python does not fill in. If the list is ever not empty, that is a C extension and it is a bug.

`gc.get_referrers` walks every tracked object in every generation and calls `tp_traverse` on each. That makes it a whole heap walk per call, and blind to anything untracked, so an empty answer proves nothing.

`gc.get_referents` is the cheap direction, one `tp_traverse`. A five megabyte string has no referents and is not even tracked, because the collector's graph is a graph of objects and not of memory.

A saved exception holds its traceback, which holds the frame, which holds every local in the function that raised. That is why `except X as e:` deletes `e` at the end of the block.

`lru_cache` on a method keys on the argument tuple, and `self` is the first argument, so the class holds every instance the method was ever called on. `cache_clear()` releases them, and a bounded `maxsize` turns it into a bounded problem.

`tracemalloc` answers where, by swapping the allocators for wrappers that record the Python stack on every allocation. Expensive, exact, and the only one of these that names a line.

## What is next

That is the memory part done: three doors into the heap, arenas and pools and blocks, a heap for every thread, ownership, immortality, two counts on one object, the cycle collector, the same collector without a GIL, and now finding what will not go away.

What is left of M7 is not lessons. It is the blueprints, the ones that have to say the ownership protocol and the collector's algorithm precisely enough that somebody could write them again in another language and pass CPython's own tests. Everything in these nine lessons is the evidence those documents get to lean on.
""")


raise SystemExit(lesson.save())
