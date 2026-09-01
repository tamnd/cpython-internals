#!/usr/bin/env python
"""O14. The last thing an object does.

The fourteenth and last lesson of the object model part. O13 was about being told an object
died. This one is about the object getting a turn first.

A `__del__` method is the mirror image of a weakref callback. The callback runs after the
object is gone and is handed a reference that says None. A finalizer runs before anything is
freed, on the object itself, with every attribute still set. Almost everything surprising about
`__del__` follows from that one difference, including the fact that it can cancel the death it
was called about.

The lesson shows a finalizer reading its own attributes, shows the two death paths running the
same two things in opposite orders, resurrects an object and then a whole cycle, and finishes
on the two ways to do this that do not need `__del__` at all.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("o14-the-last-thing-an-object-does", "o14")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("o14-the-last-thing-an-object-does").figure


lesson.md(f"""
# O14. The last thing an object does

{badge}

O13 ended on a hard rule. A {term("weakref callback", "weakref callback")} runs after the object is gone, is handed a reference that already says `None`, and can do nothing about any of it.

A `__del__` method is the other end of the same event. It runs before anything is freed, it is handed the object as `self`, and every attribute is still set. It is not a notification. It is a last turn at the wheel.

{figure("two-ways-to-be-told", "a weakref callback against a __del__ method, four differences side by side")}

That difference explains everything odd about {term("finalizer", "finalizers")}, including the part most advice about them is still wrong about.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/gc.c:1041-1076@v3.15.0rc1#finalize_garbage`.

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

Everything below was checked against the version this cell prints and against 3.14. One cell differs between the two, and it says so where it appears.
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
## A finalizer runs on the object, not after it

Start with the thing that makes `__del__` useful at all. When it runs, the object is whole.

That is not obvious. By the time `__del__` is called the reference count has already reached zero, so in every sense that matters the object is dead. But nothing has been cleared yet. The attributes are still set, other objects it points at are still there, and `self` is a normal reference that works like any other.

{figure("what-a-finalizer-can-still-see", "what is still true while a finalizer runs, self, attributes, neighbours and weak references")}

{lesson.claim("a __del__ method runs with every attribute of the object still set, because clearing happens after finalizers rather than before")}
""")


lesson.code("""
import gc
import weakref

events = []


class Connection:
    \"\"\"Something holding a resource, which is the case __del__ exists for.\"\"\"

    def __init__(self, name):
        self.name = name
        self.buffer = [1, 2, 3]

    def __del__(self):
        events.append(f"self.name is still {self.name}")
        events.append(f"self.buffer is still {self.buffer}")


link = Connection("db")
del link

for note in events:
    print(f"  {note}")
""")


lesson.md(f"""
Both attributes readable, inside a method running on an object whose count is zero.

This is why the temptation to use `__del__` for cleanup is so strong. It looks exactly like a destructor from a language that has them. The rest of this lesson is about the ways that comparison breaks down.

## The same two things, in opposite orders

An object can die two ways. Its {term("reference count", "count")} can reach zero, or the {term("cycle collector", "cycle collector")} can find it in a group that only points at itself. Both end up freeing it, and both run finalizers and weakref callbacks along the way.

They run them in opposite orders.

On the count path, deallocation calls the finalizer first and clears the weak references afterwards, {cite("Objects/typeobject.c:2794-2815@v3.15.0rc1#PyObject_CallFinalizerFromDealloc")}. On the collector path it is the other way round: callbacks first, then finalizers, {cite("Python/gc.c:1554-1581@v3.15.0rc1")}.

{figure("which-runs-first", "a table of the two death paths and which of the two things each runs first")}

{lesson.claim("a weakref callback runs after __del__ when the reference count reached zero, and before __del__ when the cycle collector did the freeing")}
""")


lesson.code("""
order = []


class Watched:
    def __del__(self):
        order.append("__del__")


single = Watched()
attached = weakref.ref(single, lambda ref: order.append("weakref callback"))
del single
print(f"  the count reached zero      {order}")

order.clear()
left = Watched()
right = Watched()
left.other = right
right.other = left
outside = weakref.ref(left, lambda ref: order.append("weakref callback"))
del left, right
gc.collect()
print(f"  the collector found a cycle {order}")
""")


lesson.md(f"""
Neither order is a bug. They are two different pieces of code that happen to do the same two jobs, and nobody ever needed them to agree.

It does mean you cannot write a callback and a `__del__` that depend on each other, because which one goes first depends on how the object happened to die, and that is usually not something you control.

## What a weak reference sees while a finalizer runs

There is a follow up question worth asking here, because O13 was so definite about it. A weakref callback always sees `None`. Does a plain weak reference with no callback also see `None` during `__del__`?

On the count path, no. The finalizer runs before the weak references are cleared, so a weak reference taken earlier still finds the object.

On the collector path this changed recently. The collector used to clear every weak reference before running finalizers, which broke type caches in a way that could crash, so 3.15 delays clearing the ones without callbacks until after the finalizers have run, {cite("Python/gc.c:788-796@v3.15.0rc1")}.

{lesson.claim("a weak reference with no callback still finds the object during __del__ on the reference count path, and on 3.15 it does on the collector path too, which is a change from 3.14")}
""")


lesson.code(
    """
seen = []


class Peek:
    def __init__(self, name):
        self.name = name

    def __del__(self):
        if self.name == "watched":
            seen.append(watcher() is not None)


single = Peek("watched")
watcher = weakref.ref(single)
del single
print(f"  the count reached zero      the weak reference still finds it {seen[0]}")

seen.clear()
left = Peek("watched")
right = Peek("other")
left.other = right
right.other = left
watcher = weakref.ref(left)
del left, right
gc.collect()
print(f"  the collector found a cycle the weak reference still finds it {seen[0]}")
""",
    differs="On 3.14 the second line reads False. The collector there cleared every weak "
    "reference before running finalizers, and 3.15 changed it so the ones without callbacks "
    "survive until afterwards.",
)


lesson.md(f"""
So a weak reference is not a reliable way to ask whether you are inside a finalizer. Use `gc.is_finalized` for that, which is what the next section is about.

## Bringing an object back from the dead

Here is the part that has no equivalent anywhere else in Python. `__del__` is handed `self`, and `self` is a perfectly ordinary reference. Store it somewhere and the object is reachable again. The death is cancelled.

The interpreter is expecting this. Before calling the finalizer it bumps the count temporarily, and afterwards it checks whether anything else grabbed a reference in the meantime, {cite("Objects/object.c:594-630@v3.15.0rc1#PyObject_CallFinalizerFromDealloc")}. If something did, deallocation stops and the object carries on living.

The obvious question is what happens the second time. The answer is a single bit on the object, set before the finalizer is called rather than after, {cite("Include/internal/pycore_gc.h:166-181@v3.15.0rc1#_PyGC_SET_FINALIZED")}. The check for it is right at the top of the call, {cite("Objects/object.c:577-592@v3.15.0rc1#PyObject_CallFinalizer")}.

{figure("a-finalizer-runs-at-most-once", "the finalized bit set before the call, so a resurrected object is never finalized twice")}

`gc.is_finalized` reads that bit, so you can watch the whole thing from Python.

{lesson.claim("a __del__ method that stores self cancels the deallocation, and the object is never finalized again because the finalized bit is set before the call rather than after")}
""")


lesson.code("""
saved = []
calls = []


class Zombie:
    \"\"\"A finalizer that keeps self, which cancels the death it was told about.\"\"\"

    def __del__(self):
        calls.append("__del__")
        saved.append(self)


doomed = Zombie()
watcher = weakref.ref(doomed)
del doomed

print(f"  __del__ has run this many times  {len(calls)}")
print(f"  and the object is still around   {watcher() is saved[0]}")
print(f"  already marked as finalized      {gc.is_finalized(saved[0])}")

saved.clear()
gc.collect()

print(f"  after really dropping it         {watcher()}")
print(f"  __del__ calls in total           {len(calls)}")
""")


lesson.md(f"""
One call, not two. The object came back, lived for as long as `saved` held it, and then went away quietly with no second finalization.

That bit is also why the flag is set before the call and not after. If it were set afterwards, a finalizer that raised would leave the object unmarked and eligible to be finalized again later.

## A cycle with finalizers used to be a leak

For a long time the standard advice was to never write `__del__` on anything that might end up in a reference cycle. The advice was correct at the time. The collector skipped any cycle containing an object with a finalizer, put the whole group in `gc.garbage`, and left it there, because it had no way to choose a safe order to run the finalizers in.

That changed in Python 3.4. Finalizers now run first, each object at most once, and only then does the collector break the cycle, {cite("Python/gc.c:1041-1076@v3.15.0rc1#finalize_garbage")}.

{figure("what-changed-in-python-34", "the old behaviour of skipping cycles with finalizers against the current behaviour")}

{lesson.claim("a reference cycle whose objects have __del__ methods is collected normally, every finalizer runs, and gc.garbage stays empty")}
""")


lesson.code("""
notes = []


class Node:
    def __init__(self, name):
        self.name = name

    def __del__(self):
        notes.append(f"{self.name} was finalized and could still see {self.other.name}")


gc.collect()

left = Node("left")
right = Node("right")
left.other = right
right.other = left
del left, right

freed = gc.collect()
for note in sorted(notes):
    print(f"  {note}")
print(f"  objects the collector freed  {freed}")
print(f"  left behind in gc.garbage    {gc.garbage}")
""")


lesson.md(f"""
Both finalizers ran, both could still reach the other object, the cycle was broken, and `gc.garbage` is empty.

That last line is the one to remember. On any Python released this decade, `gc.garbage` being non empty means you turned on `gc.set_debug(gc.DEBUG_SAVEALL)`, not that something leaked.

## Resurrecting a whole cycle

Resurrection and cycles combine in a way that is worth seeing once, because the numbers look wrong until you know what is going on.

If the finalizers in a cycle store `self`, the whole group comes back. The collector runs the finalizers, then looks again to see what is still unreachable, and anything that came back is moved to the old generation to be looked at another time, {cite("Python/gc.c:1221-1236@v3.15.0rc1#handle_resurrected_objects")}.

So the collection that ran the finalizers frees nothing at all.

{figure("the-order-a-collection-runs-in", "the five steps of a collection in order, callbacks, finalizers, resurrection check, clearing, freeing")}

{lesson.claim("if the finalizers in a cycle store self, that collection frees nothing, and a later one frees the objects without calling any finalizer again")}
""")


lesson.code("""
rescued = []


class Escape:
    def __init__(self, name):
        self.name = name

    def __del__(self):
        rescued.append(self)


gc.collect()

first = Escape("first")
second = Escape("second")
first.other = second
second.other = first
del first, second

print(f"  that collection freed        {gc.collect()}")
print(f"  objects that came back       {sorted(item.name for item in rescued)}")
print(f"  already marked as finalized  {[gc.is_finalized(item) for item in rescued]}")

rescued.clear()

print(f"  a second collection freed    {gc.collect()}")
print(f"  and gc.garbage is            {gc.garbage}")
""")


lesson.md(f"""
Zero freed, then two freed on the next pass with no finalizer running a second time.

If you ever see a `gc.collect()` return zero while memory is obviously going down afterwards, this is one of the things that can cause it.

## Two ways to do this without __del__

Everything above is a description of how `__del__` behaves, not a recommendation to use it. There are two better options and they cover almost every real case.

The first is a `try` and `finally` inside a generator. Dropping a half consumed generator closes it, which raises `GeneratorExit` at the paused `yield` and runs the `finally` block. That happens through exactly the same machinery, {cite("Objects/genobject.c:210-218@v3.15.0rc1#PyObject_CallFinalizerFromDealloc")}, so it inherits all the guarantees and none of the awkwardness, because the cleanup code is written where you can see it.

The second is `weakref.finalize`, which gives you a callback plus an `alive` flag and no method on your class at all. It holds its state in a registry rather than on the object, specifically so the finalizer cannot become part of a cycle, {cite("Lib/weakref.py:442-465@v3.15.0rc1#finalize")}.

{lesson.claim("dropping a half consumed generator runs its finally block, and weakref.finalize gives the same effect for an ordinary object without defining __del__")}
""")


lesson.code("""
log = []


def rows():
    \"\"\"A generator with cleanup, which is finalization written where you can see it.\"\"\"
    try:
        yield 1
        yield 2
    finally:
        log.append("the finally block ran")


stream = rows()
next(stream)
del stream
print(f"  dropping a half consumed generator  {log}")


class Plain:
    pass


target = Plain()
handle = weakref.finalize(target, log.append, "weakref.finalize ran")
print(f"  the handle says alive               {handle.alive}")

del target

print(f"  and afterwards                      {handle.alive}")
print(f"  what got logged                     {log[-1]}")
""")


lesson.md("""
Both do the job, neither needs a `__del__`, and neither can accidentally resurrect anything.

Use `__del__` when you genuinely need the object itself during cleanup. Use one of these when you do not, which is most of the time.

## Try it yourself

Three things to poke at.

The first is the exception behaviour. Write a `__del__` that raises and see what happens. It goes through `sys.unraisablehook` and does not propagate, the same as a weakref callback in O13, and for the same reason: nothing called it, so there is nowhere to send it. Then check whether the rest of the deallocation still finished.

The second is `gc.set_debug(gc.DEBUG_SAVEALL)`. Turn it on, build a cycle, collect, and look at `gc.garbage`. This is the one way to get objects in there on a modern Python, and it is a useful way to see exactly what a collection found. Remember to clear it and turn the flag back off.

The third is a question about cost. Does defining `__del__` make your instances bigger, or change whether they are tracked by the collector? Check both with `sys.getsizeof` and `gc.is_tracked`, on a class with a finalizer and one without. The answer is more interesting for what it rules out than for what it shows.

## What just happened

A finalizer runs on the object rather than after it. Every attribute is still set, because clearing happens after finalization rather than before. That is the whole difference between `__del__` and a weakref callback, and everything else follows from it.

An object can die two ways, and the two paths run finalizers and weakref callbacks in opposite orders. Count reaches zero: `__del__` first. Collector finds a cycle: callbacks first. So you cannot write one that depends on the other.

A weak reference with no callback still finds the object during `__del__`. On the collector path that is new in 3.15, which changed it to stop a type cache bug.

Because `__del__` is handed `self`, it can store it and cancel the deallocation. The interpreter expects this and checks for it. The finalized bit is set before the call rather than after, so a resurrected object is never finalized twice, and `gc.is_finalized` lets you read that bit.

Cycles containing finalizers have been collected normally since Python 3.4. Every finalizer runs, the cycle is then broken, and `gc.garbage` stays empty. Most advice about `__del__` still assumes otherwise.

If the finalizers in a cycle resurrect it, that collection frees nothing and reports zero. A later one frees everything without calling a finalizer again.

And two ways to avoid all of it: `try` and `finally` in a generator, and `weakref.finalize`.

## What is next

That is the object model finished. Fourteen lessons from the sixteen byte header in O01 to this one, and the through line was the same the whole way: everything in Python is a pointer to a struct that starts with a count and a type, and every feature you use is a decision made once, in C, about what to put after those two fields.

M5 is the interpreter, and it is where the object model stops being the subject and starts being the material. The eval loop is a switch over bytecode that spends almost all of its time doing what the last fourteen lessons described: reading a type pointer, finding a slot, calling through it, and adjusting a reference count. Knowing what those things are is what makes the loop readable rather than a wall of macros.

It starts with the frame, which is the object that holds a running function's locals, its value stack, and its place in the call chain.
""")


raise SystemExit(lesson.save())
