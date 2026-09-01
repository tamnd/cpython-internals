#!/usr/bin/env python
"""O13. Pointing at something without holding it.

The thirteenth lesson of the object model part, and the one O12 promised at the end. Every
ordinary reference in Python is a claim on an object. A weak reference is the deliberate
exception: a pointer that the reference count does not know about.

The lesson measures that the count really is untouched, reads off which types can be pointed
at this way and why the rest cannot, finds where the pointer is kept for a class you wrote,
watches five callbacks run in the order the chain puts them in, and then goes back to O12 and
shows an address being reused while the weak reference to the old occupant says None.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("o13-pointing-without-holding", "o13")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("o13-pointing-without-holding").figure


lesson.md(f"""
# O13. Pointing at something without holding it

{badge}

Every ordinary reference in Python is a claim on an object. Bind a name to it, put it in a list, pass it to a function, and the {term("reference count", "count")} goes up. While your reference exists the object cannot be freed. That is the deal, and almost always it is the deal you want.

A {term("weak reference", "weak reference")} is the exception. It lets you reach an object without being a reason it is still there. The header calls it a stealth reference, which is a good name for it.

{figure("a-reference-that-does-not-count", "an ordinary name against a weak reference, four differences side by side")}

That sounds like a small convenience for caches. It is also the only way to watch an object die from inside Python, because any reference that could tell you is itself a reason it has not.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Include/cpython/weakrefobject.h:8-18@v3.15.0rc1#wr_object`.

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

Everything below was checked against the version this cell prints and against 3.14. Nothing in this lesson moved between the two.
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
## A reference that does not count

The claim is easy to state and easy to check. Taking a weak reference to an object does not change how many references the interpreter thinks there are.

The C struct says so in a comment, right above the field that holds the pointer, {cite("Include/cpython/weakrefobject.h:8-18@v3.15.0rc1#wr_object")}. The field is a plain `PyObject *` like any other, and the only thing that makes it different is that nobody incremented anything when it was stored.

`sys.getrefcount` counts one extra for the argument it was just handed, so the numbers below subtract that one back off.

{lesson.claim("creating a weak reference to an object leaves its reference count exactly where it was, while binding an ordinary name adds one")}
""")


lesson.code("""
import weakref


class Cache:
    \"\"\"An ordinary class, which is all it takes to be weakly referenceable.\"\"\"


data = Cache()
print(f"  references to it right now          {sys.getrefcount(data) - 1}")

watcher = weakref.ref(data)
print(f"  after taking a weak reference       {sys.getrefcount(data) - 1}")
print(f"  and the weak reference finds it     {watcher() is data}")

alias = data
print(f"  after binding one more plain name   {sys.getrefcount(data) - 1}")
""")


lesson.md(f"""
One before, one after, two once a second real name exists. The weak reference is there and works, and the bookkeeping never noticed.

Calling the weak reference is what gets you the object. `watcher` is not the object, it is a small thing you ask. That is the whole interface while the object is alive, and it becomes interesting the moment the object is not.

## What you can point at, and what you cannot

Try `weakref.ref([1, 2, 3])` and you get a `TypeError`. That surprises people, because a list is about as ordinary an object as there is.

The reason is that the chain of weak references has to be stored somewhere, and the only sensible place is inside the object being pointed at. A type that has no room for that one pointer cannot support weak references at all. The test in the interpreter is one line long, {cite("Include/internal/pycore_object.h:871-874@v3.15.0rc1#_PyType_SUPPORTS_WEAKREFS")}.

Python shows you the number that test reads. `__weakrefoffset__` is how far into the object the pointer lives, and zero means there is no such place.

{figure("who-can-be-weakly-referenced", "a table of types with their weakref offsets, showing which ones support weak references")}

{lesson.claim("a type supports weak references exactly when its __weakrefoffset__ is not zero, which is why list, dict, tuple, int and str all refuse")}
""")


lesson.code(
    """
class Plain:
    \"\"\"A class you write gets weak reference support without asking for it.\"\"\"


class WithSlots:
    __slots__ = ("value",)


class SlotsAndWeakref:
    __slots__ = ("__weakref__", "value")


def a_function():
    pass


candidates = [
    ("a class you wrote", Plain),
    ("__slots__ without it", WithSlots),
    ("__slots__ with it", SlotsAndWeakref),
    ("set", set),
    ("function", type(a_function)),
    ("type", type),
    ("list", list),
    ("dict", dict),
    ("int", int),
]

for label, kind in candidates:
    offset = kind.__weakrefoffset__
    print(f"  {label:22} offset {offset:5}   can be pointed at {offset != 0}")
""",
    varies="The offsets are byte counts, so on a 32 bit build every non zero one halves and a "
    "class you wrote reads minus sixteen rather than minus thirty two. Which types read zero is "
    "the same everywhere, because that is a question about layout and not about word size.",
)


lesson.md(f"""
Two things in there are worth stopping on.

The first is that `set` gets a positive offset and `list` gets zero. Both are builtin containers written in C, so this is not a rule about builtins, it is a decision made once per type by whoever wrote it. Somebody thought sets were worth the extra pointer and lists were not.

The second is the negative number. A class you write does not keep the pointer inside the object at all.

## Where the pointer actually lives

For a class defined in Python the weak reference pointer is stored in front of the object, in the same {term("GC pre header", "pre header")} area that holds the {term("instance dictionary", "instance dictionary")}. The offset is negative because the object's own address points past all of that, {cite("Include/internal/pycore_object.h:922-928@v3.15.0rc1#MANAGED_WEAKREF_OFFSET")}. The type gets that offset assigned when the class is built, {cite("Objects/typeobject.c:4688-4692@v3.15.0rc1#MANAGED_WEAKREF_OFFSET")}.

{figure("where-the-pointer-lives", "the four words in front of an instance, weakref list, instance dictionary and two words of GC pre header")}

You can measure the whole arrangement with `sys.getsizeof`, which counts the pre header, without needing to know any of the C.

{lesson.claim("adding __weakref__ to a class with __slots__ costs sixteen bytes rather than eight, because the pointer lives in a pre header that is allocated two words at a time")}
""")


lesson.code(
    """
class Empty:
    __slots__ = ()


class OneSlot:
    __slots__ = ("value",)


class OneSlotAndWeakref:
    __slots__ = ("__weakref__", "value")


shapes = [
    ("__slots__ = ()", Empty),
    ("one slot", OneSlot),
    ("one slot plus __weakref__", OneSlotAndWeakref),
    ("no __slots__ at all", Plain),
]

for label, kind in shapes:
    size = sys.getsizeof(kind())
    print(f"  {label:26} {size:3} bytes   offset {kind.__weakrefoffset__:4}")
""",
    varies="Every byte count halves on a 32 bit build, because all of these are counts of "
    "pointers. The shape of the result is the same: adding __weakref__ costs two words, not one.",
)


lesson.md(f"""
Thirty two bytes for an instance with no slots at all, forty once it has one, and fifty six once it can also be weakly referenced. That last step is sixteen bytes for what is one pointer, because the pre header comes in a pair and adding `__weakref__` buys both halves.

The plain class with no `__slots__` sits at forty eight and gets the same negative offset for free. It already had the pre header, for the dictionary.

So if you reached for `__slots__` to save memory and then added `__weakref__` back, that is the price. Worth knowing before you do it rather than after.

## Ask twice and you get the same object

Weak references chain off the object in a doubly linked list, {cite("Include/cpython/weakrefobject.h:25-31@v3.15.0rc1#wr_next")}. The object holds one pointer, which is the head of that chain.

That chain is kept in a particular order, and the order is not an accident. A weak reference with no callback is interchangeable with any other weak reference with no callback, so the interpreter keeps at most one of those and hands it back again rather than making another, {cite("Objects/weakrefobject.c:326-353@v3.15.0rc1#try_reuse_basic_ref")}. It lives at the head of the chain so it can be found in one step, and everything with a callback is inserted in front of the rest, {cite("Objects/weakrefobject.c:373-397@v3.15.0rc1#insert_weakref")}.

{figure("the-list-of-weak-references", "the chain hanging off an object, with the callback free reference at the head")}

{lesson.claim("asking twice for a weak reference with no callback gives you the same object back, while two with callbacks are always two separate objects")}
""")


lesson.code("""
target = Plain()

first = weakref.ref(target)
second = weakref.ref(target)
print(f"  two plain weak references are one object  {first is second}")

with_callback = weakref.ref(target, lambda ref: None)
another_callback = weakref.ref(target, lambda ref: None)
print(f"  two with callbacks are two objects        {with_callback is another_callback}")
print(f"  weak references to it in total            {weakref.getweakrefcount(target)}")

names = {id(first): "no callback"}
names[id(with_callback)] = "callback 0"
names[id(another_callback)] = "callback 1"
chain = [names[id(ref)] for ref in weakref.getweakrefs(target)]
print(f"  the order the chain is in                 {chain}")
""")


lesson.md(f"""
Three weak references for four calls, because the first two collapsed into one. And the callback that was created second sits in front of the one created first, which is what "inserted in front of the rest" means when you do it twice.

That ordering is about to matter, because it is the order the callbacks run in.

## Watching the moment it dies

When the reference count of an object reaches zero, its deallocation walks the chain, {cite("Objects/weakrefobject.c:1007-1044@v3.15.0rc1#PyObject_ClearWeakRefs")}. It does two passes rather than one, and the split is the important part.

The first pass breaks every weak reference, pointing each one at `None`. Only after all of them are broken does the second pass run the callbacks, {cite("Objects/weakrefobject.c:1077-1083@v3.15.0rc1#handle_callback")}.

{figure("what-happens-when-it-dies", "reference count reaches zero, break every reference, then run the callbacks, then free")}

So a {term("weakref callback", "callback")} is handed the weak reference, and calling it gives `None`. Every time, by design. The comment in the collector spells out why: clearing first is what stops a callback from making the doomed object reachable again, and it also stops a callback running twice, {cite("Python/gc.c:781-787@v3.15.0rc1")}.

{lesson.claim("by the time a weakref callback runs, every weak reference to the object has already been broken, so calling the reference it is handed always gives None")}
""")


lesson.code("""
notes = []
doomed = Plain()
watchers = [weakref.ref(doomed, lambda ref, n=n: notes.append((n, ref()))) for n in range(5)]

print(f"  before, the object is still there    {watchers[0]() is doomed}")

del doomed

broken = all(ref() is None for ref in watchers)
print(f"  after, every reference is broken     {broken}")
print(f"  callbacks that ran                   {len(notes)}")
print(f"  the order they ran in                {[n for n, _ in notes]}")
print(f"  what ref() gave each of them         {[value for _, value in notes]}")
""")


lesson.md(f"""
Five out of five ran, newest first, and every one of them was handed a reference that already said `None`.

That last column is the thing people get wrong. A callback is not a chance to look at the object one more time. The object is gone. What you get is a notification that it went, plus whatever you closed over yourself when you set the callback up.

## The one thing free lists could not show you

O12 spent a whole lesson inferring things from addresses. Drop an object, make another, see the same `id`, conclude that the memory was reused. That is a sound inference but it is still an inference, because `id` only tells you about addresses and never about objects.

A weak reference closes the gap. It knows about the object rather than the address, so it can tell you the old occupant is gone even while the address is handing out the same bytes.

To show both at once you need something with a {term("free list", "free list")} that also supports weak references, and there is exactly one convenient candidate. A {term("bound method", "bound method")} is built fresh every time you look it up, it has a free list capped at twenty, {cite("Include/internal/pycore_freelist_state.h:33@v3.15.0rc1#Py_pymethodobjects_MAXFREELIST")}, and unlike a list or a tuple it can be weakly referenced.

{figure("the-memory-is-back-but-the-object-is-not", "a bound method dropped and taken again, same address and a dead weak reference")}

{lesson.claim("a dropped bound method leaves its memory on a free list, so the next one lands on the same address, while a weak reference to the old one correctly reports it gone")}
""")


lesson.code("""
class Session:
    def close(self):
        \"\"\"Looking this up on an instance builds a new bound method object each time.\"\"\"


session = Session()
handler = session.close
where = id(handler)
watcher = weakref.ref(handler)

supported = type(handler).__weakrefoffset__ != 0
print(f"  a bound method can be weakly referenced  {supported}")
print(f"  and right now the reference finds it     {watcher() is handler}")

del handler
print(f"  drop it and the reference gives          {watcher()}")

again = session.close
print(f"  a fresh one lands on the same address    {id(again) == where}")
print(f"  and the old reference still gives        {watcher()}")
""")


lesson.md(f"""
Same address, dead reference. Both true at once, and neither one is a mistake.

This is worth holding on to whenever you are reasoning about memory from Python. `id` is a question about a location. Identity, in the sense you actually care about, is a question about an object, and the two only line up while the object is alive. As soon as it is not, an address can be reused by something else and `id` will happily tell you they are the same.

## When the callback does not run

Callbacks are not a guarantee. There is one case where the object is definitely collected and the callback definitely does not run, and it is worth knowing about because it looks like a bug the first time you hit it.

If the weak reference is itself part of the garbage being collected, the collector skips its callback. The reasoning is written out at length in the collector and comes down to two points: the callback is not needed, because the weak reference is going away too, and it might not be safe, because a callback that is also part of the cycle could reach back into it, {cite("Python/gc.c:861-890@v3.15.0rc1")}.

{lesson.claim("a weakref callback runs when the weak reference outlives the object, and is skipped when the weak reference is part of the same garbage being collected")}
""")


lesson.code("""
import gc


class Node:
    \"\"\"One half of a reference cycle, which only the collector can take apart.\"\"\"


fired = []
left = Node()
right = Node()
left.other = right
right.other = left

outside = weakref.ref(left, lambda ref: fired.append("held outside the cycle"))
right.watcher = weakref.ref(left, lambda ref: fired.append("held inside the cycle"))

del left, right
gc.collect()

print(f"  callbacks that ran   {len(fired)} of 2")
for note in fired:
    print(f"    {note}")
""")


lesson.md(f"""
One of two. The weak reference stored on `right` was collected along with everything else, so its callback was never called. The one held by a live name outlived the object and ran normally.

There is a second way a callback can fail to do what you expect, which is by raising. Nothing is calling the callback in the ordinary sense, so there is nowhere for the exception to go. It is reported as unraisable and then dropped, {cite("Objects/weakrefobject.c:987-999@v3.15.0rc1#handle_callback")}.

You can see it without any stderr noise by swapping in your own `sys.unraisablehook` for the duration.

{lesson.claim("an exception raised inside a weakref callback is reported through sys.unraisablehook and does not propagate to whatever was running at the time")}
""")


lesson.code("""
def explode(ref):
    \"\"\"A callback that fails, which happens more often than anyone plans for.\"\"\"
    raise ValueError("the callback could not finish")


caught = []
original_hook = sys.unraisablehook
sys.unraisablehook = lambda unraisable: caught.append(unraisable.exc_value)

fragile = Plain()
attached = weakref.ref(fragile, explode)
del fragile

sys.unraisablehook = original_hook

print(f"  the callback raised     {type(caught[0]).__name__}: {caught[0]}")
print("  the code around it      carried on to this line")
print(f"  and the reference says  {attached()}")
""")


lesson.md("""
The exception happened, it was reported, and the deletion that triggered it completed anyway. If you write a callback that can fail, nothing downstream will find out unless you arrange for it yourself.

## Try it yourself

Three things to poke at.

The first is `weakref.proxy`. It is a weak reference that reads through, so `proxy.attribute` works as if you were holding the object. Take one, drop the object, and try to use it. It raises `ReferenceError` rather than returning `None`, which makes it the right choice when a silent `None` would be worse than a loud failure. Check whether asking twice for a proxy reuses one object the way `weakref.ref` does.

The second is `weakref.WeakValueDictionary`. Put an object in one, look at `list(the_dict)`, drop your own reference, and look again. Then work out how the entry removes itself, and whether the answer involves anything from this lesson.

The third is a design question with a measurable answer. `weakref.finalize` gives you a callback with an `alive` flag and no weak reference to keep hold of. Read `Lib/weakref.py` and find where it stores things so the finalizer does not get collected along with the object. Then check what `alive` says before and after the object goes.

## What just happened

A weak reference is a pointer the reference count does not know about, which is why it can reach an object without keeping it alive. The struct calls it a stealth reference.

Whether you can take one is decided per type by whether there is room for a pointer, and Python tells you the answer as `__weakrefoffset__`. Zero means no, which is why lists, dicts, tuples, ints and strings all refuse. Sets, functions and types say yes with a real field in the struct.

A class you write says yes too, at a negative offset, because the pointer is kept in the pre header in front of the object next to the instance dictionary. Adding `__weakref__` to a class with `__slots__` costs sixteen bytes rather than eight, because that pre header is allocated two words at a time.

Weak references chain off the object in a doubly linked list. The callback free one is a single shared object at the head of the chain, and every one with a callback is inserted in front of the rest, so callbacks run newest first.

When the object dies, every weak reference is broken before any callback runs. A callback is handed a reference that already says `None`, which is what stops it bringing the object back.

Two ways a callback can quietly not do what you meant. If the weak reference is part of the same cycle being collected, the callback is skipped. If the callback raises, the exception is reported as unraisable and goes no further.

And the piece O12 was missing: a bound method has both a free list and weak reference support, so you can watch an address come straight back while a weak reference to the old occupant correctly reports it gone.

## What is next

O14 is finalization, which is the last lesson of this part and the other half of what happens when an object goes away.

A weak reference callback runs after the object is gone and cannot touch it. A `__del__` method runs before, on the object itself, while it is still whole. That single difference is where all the difficulty lives. It means a finalizer can store `self` somewhere and bring a doomed object back, and it means the collector has to run finalizers on a cycle before it can free any of it, and decide what to do if the cycle survives.
""")


raise SystemExit(lesson.save())
