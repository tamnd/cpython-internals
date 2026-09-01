#!/usr/bin/env python
"""O11. Two sizes and a growth curve.

The eleventh lesson of the object model part. O09 and O10 were about objects that hold their
data directly. This one is about the container that does not.

A list is a small fixed object holding a pointer to a separately allocated array, and it
carries two sizes rather than one: how many items you can see, and how many slots the array
has room for. Everything odd about lists comes out of that. A tuple is the other shape, one
object with the items inside it, and being immutable earns it a cached hash.

The lesson measures the exact growth curve, reimplements the formula from `list_resize` in
Python and checks it against reality, finds the point where a list shrinks, and reimplements
`tuple_hash` well enough to match the real thing on every input tried.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("o11-two-sizes-and-a-growth-curve", "o11")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("o11-two-sizes-and-a-growth-curve").figure


lesson.md(f"""
# O11. Two sizes and a growth curve

{badge}

Two questions to start with. Why can a tuple be a dict key when a list cannot? And why does appending a million items to a list take about as long per item as appending ten?

Both answers are the same answer, and it is about where the items are.

{figure("two-objects-not-one", "a list keeps its items somewhere else, a tuple keeps them inside itself")}

A tuple is one object. The items sit inside it, right after the header, and there is nowhere for them to go because a tuple never changes. A list is two objects: a small fixed one you hold a reference to, and an array somewhere else that it points at. That array is thrown away and reallocated as the list grows.

This lesson measures the array, works out the rule for how it grows, and then asks what a tuple gets in exchange for giving up the ability to change.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Objects/listobject.c:103-137@v3.15.0rc1#list_resize`.

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

Everything below was checked against the version this cell prints and against 3.14. Lists and tuples are one of the calmest corners of CPython and the two versions agree on every number here.
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
## A list is a small object pointing at a big one

The list struct has four things in it and none of them is an item, {cite("Include/cpython/listobject.h:5-22@v3.15.0rc1#PyListObject")}. There is the object header, there is `ob_item` which is a pointer to an array of pointers, and there is `allocated`, which is how many slots that array has. The count of items you can actually see is `ob_size`, which comes from the header.

{figure("what-a-list-holds", "the four fields of a list object")}

Two sizes, and they are almost never equal. The gap between them is called {term("over allocation", "over allocation")}, and the comment in the header spells out the rule the two sizes live by: `0 <= ob_size <= allocated`.

A tuple looks nothing like that, {cite("Include/cpython/tupleobject.h:5-13@v3.15.0rc1#PyTupleObject")}. There is a header, a cached hash, and then `ob_item[1]`, which is C's way of saying the items start here and there are as many as the header says. One object, one allocation, no pointer to follow.

The first consequence is easy to measure. An empty list and an empty tuple are two different sizes, and they grow differently.

{lesson.claim("a list is a fixed size object holding a pointer to a separately allocated array of item pointers, while a tuple holds its items inside the object itself")}
""")


lesson.code(
    """
import sys

print("  empty list   ", sys.getsizeof([]), "bytes")
print("  empty tuple  ", sys.getsizeof(()), "bytes")
print()
print("  items   list   tuple")
for count in [0, 1, 2, 3, 10]:
    items = list(range(count))
    print(f"  {count:5}   {sys.getsizeof(items):4}   {sys.getsizeof(tuple(items)):5}")
""",
    varies="Eight bytes per item on a 64 bit build and four on a 32 bit one, because an item "
    "is a pointer. The fixed part of each object halves on a 32 bit build too.",
)


lesson.md(f"""
An empty list is 56 bytes and an empty tuple is 48. The extra eight is `allocated`, the second size a tuple does not need.

Both then grow by eight bytes per item, because an item is a pointer either way. Neither container stores your objects. It stores the addresses of your objects, which is why a list of a million small integers is eight megabytes of pointers plus whatever those integers cost, and why `sys.getsizeof` on a list never tells you how much memory the list is really responsible for.

Notice that `sys.getsizeof` on a list counts the array too, even though the array is a separate allocation, {cite("Objects/listobject.c:3578-3592@v3.15.0rc1#list___sizeof___impl")}. It adds `allocated * sizeof(PyObject *)` to the struct size. That is what lets us see the second size from Python, and the whole rest of this lesson depends on it.
""")


lesson.md(f"""
## The growth curve, measured and then predicted

Now for the interesting part. Start with an empty list and append one item at a time, watching `sys.getsizeof` after each one. Most appends change nothing. Every so often the number jumps, and that jump is the array being thrown away and reallocated bigger.

The comment above `list_resize` gives the answer away before the code does, {cite("Objects/listobject.c:119-129@v3.15.0rc1")}. It says the growth pattern is 0, 4, 8, 16, 24, 32, 40, 52, 64, 76. Let us see whether that is still true.

{lesson.claim("appending to a list allocates room for about an eighth more than it needs plus six, rounded down to a multiple of four, so the array is reallocated a logarithmic number of times rather than once per append")}
""")


lesson.code("""
FIXED = sys.getsizeof([])
POINTER = sys.getsizeof((None,)) - sys.getsizeof(())


def slots(items):
    \"\"\"How many pointer slots the array has, read back out of getsizeof.\"\"\"
    return (sys.getsizeof(items) - FIXED) // POINTER


grown = []
jumps = []
previous = slots(grown)

for n in range(1, 90):
    grown.append(n)
    current = slots(grown)
    if current != previous:
        jumps.append((n, current))
        previous = current

print("  length at each jump  ", [n for n, _ in jumps])
print("  slots after the jump ", [s for _, s in jumps])
""")


lesson.md(f"""
The pattern in the comment, exactly. Ten reallocations to reach eighty nine items, and after that the gaps keep getting wider.

The line that produces those numbers is one expression, {cite("Objects/listobject.c:129@v3.15.0rc1")}: `newsize + (newsize >> 3) + 6`, then rounded down to a multiple of four. That is the new size plus an eighth of it plus six, and the rounding is there so the allocator gets a nice number.

Two things about that. The eighth is the important part, because growing by a constant fraction is what makes a long run of appends cheap on average. And the plus six is what stops tiny lists from reallocating on every single append, since an eighth of three is zero.

You can write it out and check it against the measurements.
""")


lesson.code("""
def predicted(newsize):
    \"\"\"list_resize, the one line that matters, in Python.\"\"\"
    return (newsize + (newsize >> 3) + 6) & ~3


print("  length   measured   predicted   match")
for length, measured in jumps:
    guess = predicted(length)
    print(f"  {length:6}   {measured:8}   {guess:9}   {measured == guess}")
""")


lesson.md(f"""
Every jump predicted from one line of arithmetic.

There is a second line right underneath it that this cell never triggers, {cite("Objects/listobject.c:130-134@v3.15.0rc1")}. If the list is growing by more than the overallocation would give it, which happens when you extend by a big chunk rather than appending one at a time, CPython skips the overallocation entirely and asks for just what is needed. Guessing ahead is only worth it when the caller is adding items one at a time.

{figure("what-append-does", "the four steps of a single append")}

Now the payoff. Because the array grows by a fraction of itself, the number of reallocations over a long run of appends grows with the logarithm of the length rather than with the length.
""")


lesson.code("""
def reallocations(count):
    \"\"\"How many times the array is thrown away over count appends.\"\"\"
    items = []
    seen = 0
    previous = slots(items)
    for n in range(count):
        items.append(n)
        current = slots(items)
        if current != previous:
            seen += 1
            previous = current
    return seen


print("  appends   reallocations")
for count in [100, 1000, 10000, 100000]:
    print(f"  {count:7}   {reallocations(count):13}")
""")


lesson.md("""
A hundred appends cost eleven reallocations. A hundred thousand cost sixty six. Every time the length goes up by a factor of ten, the reallocation count goes up by about nineteen, which is what a constant growth factor looks like from the outside.

That is the whole reason `list.append` is described as amortized constant time. Any individual append can be expensive, because it might be the one that copies a hundred thousand pointers to a new array. But those get rarer exactly as fast as they get more expensive, so the average stays flat.
""")


lesson.md(f"""
## How you built the list decides how much it wastes

If the length is known in advance, CPython does not guess. `list_preallocate_exact` asks for exactly the number of slots needed, rounded up to an even number because the allocator works in sixteen byte steps anyway, {cite("Objects/listobject.c:197-209@v3.15.0rc1#list_preallocate_exact")}.

So five items built five different ways can come out three different sizes, and none of that is visible in the language.

{figure("how-you-built-it-matters", "five ways to build a five item list and the slots each one ends up with")}
""")


lesson.code("""
def five_names(a, b, c, d, e):
    \"\"\"Five variables, which the compiler has to build one slot at a time.\"\"\"
    return [a, b, c, d, e]


appended = []
for n in range(5):
    appended.append(n)

ways = [
    ("five names", five_names(0, 1, 2, 3, 4)),
    ("five constants", [0, 1, 2, 3, 4]),
    ("list(range(5))", list(range(5))),
    ("five appends", appended),
    ("a comprehension", [n for n in range(5)]),
]

for label, items in ways:
    print(f"  {label:16} {slots(items):2} slots for {len(items)} items")
""")


lesson.md(f"""
Three answers for the same five items. The list of names gets exactly five, because the compiler emits a `BUILD_LIST 5` and that asks for five. The list of constants gets six, and so does `list(range(5))`, because both of them go through the extend path: the compiler turns a list of constants into an empty list plus one extend from a constant tuple, and extend calls `list_preallocate_exact`, which is the function that rounds up to an even number, {cite("Objects/listobject.c:1242-1259@v3.15.0rc1#list_extend_fast")}. The comprehension and the loop both went through `append`, so both overshot by three.

None of this is worth optimising in ordinary code. It is worth knowing when you are holding a few million lists, and it is worth knowing because it explains something that otherwise looks like a bug: two lists that are equal, made from the same items, reporting different sizes.

The array shrinks too, and there is an exact rule for when. The first thing `list_resize` does is check whether the current array is already usable, {cite("Objects/listobject.c:109-117@v3.15.0rc1")}. If the new size fits and is at least half the allocated size, it just updates `ob_size` and returns without touching memory. So a list shrinks its array only once it drops below half full.

{lesson.claim("shrinking a list reallocates its array only when the new length falls below half of what is allocated, so deleting exactly half the items of a full list frees nothing")}
""")


lesson.code(
    """
print("  keep   before   after   slots")
for keep in [501, 500, 499, 300]:
    items = list(range(1000))
    before = sys.getsizeof(items)
    del items[keep:]
    print(f"  {keep:4}   {before:6}   {sys.getsizeof(items):5}   {slots(items):5}")
""",
    varies="The byte counts halve on a 32 bit build, because an item slot is four bytes there "
    "rather than eight. The slot counts and the boundary between 500 and 499 are the same "
    "everywhere, because the rule is about slots and not about bytes.",
)


lesson.md("""
Keeping five hundred of a thousand frees nothing. Keeping four hundred and ninety nine drops the array from a thousand slots to five hundred and sixty four. One item either side of exactly half, and the behaviour is completely different.

This is worth remembering if you ever use a list as a queue by deleting from the front. The array does not give memory back until you are below half, and then it gives back a lot at once.
""")


lesson.md(f"""
## What a tuple gets for being unable to change

A tuple has no `allocated` field because it has no use for one. It cannot grow, so the number of items it has when it is made is the number it will have forever, and the items go straight into the object.

What it has instead is a {term("cached hash", "cached hash")} in a field called `ob_hash`, and that field is the point.

Hashing a tuple means hashing everything in it, which is proportional to its length. If tuples could change, the answer could not be kept, because any hash you stored would be a lie the moment somebody assigned to an item. Since they cannot change, the answer is computed on the first ask and stored, {cite("Objects/tupleobject.c:371-404@v3.15.0rc1#tuple_hash")}. The field starts at -1 and the function returns early if it is anything else.

{figure("why-a-tuple-can-cache-its-hash", "immutability, a cached hash, and being allowed in a dict")}

That is the real reason a tuple can be a dict key and a list cannot. It is not a rule somebody wrote down for tidiness. A mutable container has no stable hash to give.

The algorithm itself is xxHash, and the constants are right there in a header, {cite("Include/internal/pycore_tuple.h:65-75@v3.15.0rc1#_PyTuple_HASH_XXPRIME_1")}. There are two sets of them, one for 64 bit hashes and one for 32 bit, so the cell below picks whichever one this build uses. Then it walks the items exactly as the C loop does and compares.

{lesson.claim("a tuple's hash is xxHash over the hashes of its items, computed once and cached in the object, which is what makes a tuple usable as a dict key")}
""")


lesson.code("""
WIDTH = sys.hash_info.width
MASK = (1 << WIDTH) - 1

if WIDTH > 32:
    PRIME_1 = 11400714785074694791
    PRIME_2 = 14029467366897019727
    PRIME_5 = 2870177450012600261
    LEFT = 31
else:
    PRIME_1, PRIME_2, PRIME_5, LEFT = 2654435761, 2246822519, 374761393, 13


def rotate(value):
    \"\"\"_PyTuple_HASH_XXROTATE, left by 31 bits on a 64 bit build and 13 on a 32 bit one.\"\"\"
    return ((value << LEFT) | (value >> (WIDTH - LEFT))) & MASK


def tuple_hash(items):
    \"\"\"tuple_hash, the loop from Objects/tupleobject.c, in Python.\"\"\"
    acc = PRIME_5
    for item in items:
        acc = (acc + (hash(item) & MASK) * PRIME_2) & MASK
        acc = (rotate(acc) * PRIME_1) & MASK
    acc = (acc + (len(items) ^ (PRIME_5 ^ 3527539))) & MASK
    if acc == MASK:
        acc = 1546275796
    return acc - (1 << WIDTH) if acc >> (WIDTH - 1) else acc


for sample in [(), (1,), (1, 2, 3), ("a", "b"), (1, "x", 3.5), tuple(range(20))]:
    shown = str(sample) if len(str(sample)) < 24 else f"a tuple of {len(sample)}"
    print(f"  {shown:24} matches the real hash  {tuple_hash(sample) == hash(sample)}")
""")


lesson.md(f"""
Six shapes of tuple, six matches, including the empty one and one with a float in it.

One more thing about tuples, and it is a preview of the next lesson. Small tuples are not thrown away when you are done with them. Every size from one item up to twenty has a free list, and a tuple of that size is taken off the list rather than allocated, {cite("Include/internal/pycore_freelist_state.h:11-12@v3.15.0rc1#PyTuple_MAXSAVESIZE")}. You can see the boundary in the allocation code: it indexes the free list array with `size - 1`, {cite("Objects/tupleobject.c:36-62@v3.15.0rc1#tuple_alloc")}.

Look at what happens on the line right after a tuple is taken off that list. The cached hash is reset. A recycled tuple carries whatever hash the last tuple at that address had, and forgetting to clear it would be a very quiet and very bad bug, {cite("Include/internal/pycore_tuple.h:50-57@v3.15.0rc1#_PyTuple_Recycle")}.

The empty tuple is not on a free list at all, because there is only ever one of it. It is built into the interpreter and handed out, the same way the empty string is, {cite("Objects/tupleobject.c:64-72@v3.15.0rc1#tuple_get_empty")}.
""")


lesson.code("""
first = tuple()
second = tuple([])
third = ()[0:0]

print(f"  three ways to an empty tuple, all the same object  {first is second is third}")
print(f"  and it is immortal                                 {pyxray.obj.is_immortal(first)}")
print()

written_twice = ((1,), (1,))
built_at_runtime = tuple([1])
folded = written_twice[0] is written_twice[1]
fresh = built_at_runtime is not written_twice[0]
print(f"  two identical literals, one constant between them {folded}")
print(f"  but one built at runtime is a separate object     {fresh}")
""")


lesson.md("""
## Try it yourself

Three things to poke at.

The first is the growth curve past where the lesson stopped. Keep appending to a list until it holds a million items and print the length at every jump. The gaps get wide fast, and the ratio between one jump and the next settles down to something you can recognise.

The second is the shrink boundary from the other direction. Build a list of a thousand, then pop from the end one at a time and print `sys.getsizeof` whenever it changes. The rule is the same rule, but the sequence of sizes on the way down is not the reverse of the sequence on the way up, and working out why is the exercise.

The third is a small experiment about tuple hashing. Take a list of a few thousand tuples of two integers and put them all in a set, then do the same with the numbers swapped. If the hash treated the items as unordered, the two sets would collide badly. Time both, or just count the set's length. The rotate in the middle of the loop is what stops that from happening.
""")


lesson.md("""
## What just happened

A list is a fifty six byte object holding a pointer to an array somewhere else, and it tracks two sizes: how many items you can see, and how many slots the array has. A tuple is one object with the items inside it and only one size, because it never changes.

Appending to a list asks for the new size plus an eighth of it plus six, rounded down to a multiple of four. That produces the sequence 4, 8, 16, 24, 32, 40, 52, 64, 76, 92, which the lesson measures and then predicts from that one expression. Because the array grows by a fraction of itself, a hundred thousand appends cost sixty six reallocations rather than a hundred thousand.

If the length is known ahead of time the array is allocated to fit rather than guessed at, so a list built with `list(range(5))` and one built with five appends are the same list with different amounts of slack in it.

The array shrinks only when the length drops below half of what is allocated. Deleting exactly half the items of a full list frees nothing at all.

A tuple caches its hash in the object, which it is only allowed to do because it cannot change. That is what makes tuples usable as dict keys and lists not. The hash is xxHash over the item hashes, and the lesson reimplements it closely enough to match on every input tried.

Small tuples up to twenty items are recycled through free lists rather than freed, and the cached hash has to be cleared when one is reused.
""")


lesson.md("""
## What is next

O12 is the free lists, which the end of this lesson walked into. Tuples are not the only thing CPython refuses to hand back to the allocator. Floats, ints, dicts, list iterators, method objects and about a dozen other types each keep a pile of dead objects around for the next time one is needed, with a different cap on each pile. The lesson is about why that is worth doing, how to see it happening from Python, and what it means for the identity of objects you thought were new.
""")


raise SystemExit(lesson.save())
