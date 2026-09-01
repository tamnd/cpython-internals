#!/usr/bin/env python
"""O12. The objects that come back.

The twelfth lesson of the object model part, and the one that follows the last line of O11.
Small tuples are not thrown away when you are done with them, and neither are floats, lists,
dicts, iterators, slices, ranges or half a dozen other things.

Freeing an object is not one decision, it is three. Is this exactly the base type. Does that
type keep a stash of dead ones. Is the stash under its cap. Only if the answer to any of those
is no does the memory actually go back to the allocator.

The lesson watches an address come back, proves the reuse is by type rather than by size,
reads the free list contents straight out of the running interpreter, measures three caps
without opening the header, and finds the one thing that empties them all.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("o12-the-objects-that-come-back", "o12")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("o12-the-objects-that-come-back").figure


lesson.md(f"""
# O12. The objects that come back

{badge}

O11 ended on a loose thread. Small tuples are not thrown away when you drop them, they go on a list of dead tuples and the next one that comes along is handed the same memory.

That turns out not to be a tuple thing. Floats do it, lists do it, dicts do it, iterators do it, and there is a header listing twenty two of them.

{figure("where-a-dropped-object-goes", "the three questions asked when the last reference to an object goes away")}

So `del` is a much softer word than it sounds. The object stops being reachable and its reference count reaches zero, but the memory usually stays exactly where it was, waiting for the next object of the same type.

This lesson watches that happen, then proves it is really happening rather than being an accident of the allocator, then reads the stashes out of the running interpreter and counts what is in them.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Include/internal/pycore_freelist.h:52-63@v3.15.0rc1#_PyFreeList_Push`.

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

Everything below was checked against the version this cell prints and against 3.14. The caps have not moved between the two, and neither has anything else in this lesson.
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
## The address you just gave back is the one you get next

Start with the simplest possible version. Build an object, write down where it is, drop it, build another one of the same kind, and look at where that one is.

`id` is the address on CPython, so this is a memory question asked in ordinary Python. Two objects can only share an address if the first one is really gone, so there is no ambiguity about what is being measured.

{lesson.claim("dropping an object and immediately building another of the same type usually hands you the same memory, because the type keeps a stash of dead objects rather than returning them to the allocator")}
""")


lesson.code("""
def addresses(make, rounds=5):
    \"\"\"Where five objects land, when each is dropped before the next is made.\"\"\"
    seen = []
    for _ in range(rounds):
        obj = make()
        seen.append(id(obj))
        del obj
    return seen


kinds = [
    ("float", lambda: float(str(1.5))),
    ("list", lambda: [1, 2, 3]),
    ("tuple of 3", lambda: tuple([1, 2, 3])),
    ("set", lambda: {1, 2, 3}),
]

for label, make in kinds:
    seen = addresses(make)
    print(f"  {label:11} five in a row, all at one address  {len(set(seen)) == 1}")
""")


lesson.md(f"""
Five objects, one address, four times over.

The obvious objection is that this proves nothing about types. CPython has its own allocator underneath, {term("obmalloc", "obmalloc")}, and it hands out {term("block", "blocks")} by size. If you free 56 bytes and immediately ask for 56 bytes, of course you get the same 56 bytes back. Nothing about lists or floats needs to be involved.

That objection is worth taking seriously, and it has a clean test. The allocator only knows sizes. A free list only knows types. So find two different types that are exactly the same size and see whether the memory crosses between them.

A list and a one item tuple are both 56 bytes on a 64 bit build. Drop one, ask for the other.

{figure("not-the-same-as-the-allocator", "the allocator hands out blocks by size, a free list hands out objects by type")}

{lesson.claim("the reuse is per type rather than per size, so a dropped list can be reused as another list but never as a tuple of the same number of bytes")}
""")


lesson.code(
    """
both = f"{sys.getsizeof([])} bytes and {sys.getsizeof((None,))} bytes"
print(f"  a list and a one item tuple are {both}")
print()

dropped = []
where = id(dropped)
del dropped
same_size = tuple([None])
print(f"  a fresh 1-tuple lands on the dropped list's address  {id(same_size) == where}")
del same_size

dropped = []
where = id(dropped)
del dropped
same_type = [1]
print(f"  a fresh list lands on the dropped list's address     {id(same_type) == where}")
""",
    varies="A list and a one item tuple are both 56 bytes on a 64 bit build and both 28 on a "
    "32 bit one, so the sizes stay equal and the answers stay the same.",
)


lesson.md("""
Same number of bytes, and the tuple does not get them. Another list does.

That is the whole argument. The allocator would have handed those bytes to anything that asked for the right size. Something above the allocator caught the list on its way out and kept it for lists.

## Reading the stashes out of a running interpreter

You do not have to infer any of this. CPython will tell you what is on each free list right now.

`sys._debugmallocstats` prints a long report about the allocator, and near the top it lists every free list with a count. The catch is that it writes to C level standard error rather than to `sys.stderr`, so redirecting `sys.stderr` in Python catches nothing. You have to redirect file descriptor 2 itself, which `os.dup2` does.
""")


lesson.code(
    """
import os
import tempfile


def freelist_report():
    \"\"\"sys._debugmallocstats writes to C level stderr, so catch fd 2 rather than sys.stderr.\"\"\"
    with tempfile.TemporaryFile() as sink:
        saved = os.dup(2)
        os.dup2(sink.fileno(), 2)
        try:
            sys._debugmallocstats()
        finally:
            os.dup2(saved, 2)
            os.close(saved)
        sink.seek(0)
        return sink.read().decode()


for line in freelist_report().splitlines():
    if " free " in line and "Tuple" not in line:
        print("  " + " ".join(line.split()[:3]))
""",
    varies="These are whatever happens to be lying around when you run the cell, so they are "
    "different on every runtime and often different between two runs of the same one. The "
    "four names are the point, not the four numbers.",
)


lesson.md(f"""
Four lines, four counts, read out of the interpreter you are sitting in.

Now make some garbage and watch a number move. Three hundred floats, created and then dropped all at once.

{lesson.claim("each free list has a fixed cap, and a float free list fills to exactly a hundred no matter how many floats you drop")}
""")


lesson.code(
    """
import gc


def held(kind):
    \"\"\"How many dead objects of one kind are currently on its free list.\"\"\"
    for line in freelist_report().splitlines():
        if f" free {kind} " in line:
            return int(line.split()[0])
    return 0


gc.collect()
print(f"  after a collection, floats held  {held('PyFloatObjects')}")

junk = [float(n) + 0.5 for n in range(300)]
print(f"  300 floats made and still alive  {held('PyFloatObjects')}")

del junk
print(f"  and dropped                      {held('PyFloatObjects')}")
""",
    varies="The first number is whatever the collection happened to leave behind, usually a "
    "handful, and it moves between versions and between runs. The hundred does not.",
)


lesson.md(f"""
Three hundred floats died and exactly a hundred of them are still sitting there.

A hundred is `Py_floats_MAXFREELIST`, and it is one line in a header full of similar lines, {cite("Include/internal/pycore_freelist_state.h:11-33@v3.15.0rc1#PyTuple_MAXSAVESIZE")}. Twenty two of them, one per type, and the numbers are not tidy: a hundred for floats and ints, eighty for lists and dicts, ten for iterators, six for ranges, two hundred and fifty five for contexts, and one for slices.

{figure("how-many-each-type-keeps", "the free list caps for the common types, from one for slices to two hundred and fifty five for contexts")}

The stash itself is two words: a pointer to the first dead object and a count, {cite("Include/internal/pycore_freelist_state.h:36-44@v3.15.0rc1")}. There is no array and no container. The chain runs through the dead objects themselves, using the first word of each one to point at the next, and the comment in the header says exactly which field that overwrites: the reference count.

{figure("the-chain-lives-in-the-dead-objects", "the chain is threaded through the first word of each dead object")}

That is a nice piece of design. A dead object has no use for a reference count, so the space is free. Pushing is three assignments, {cite("Include/internal/pycore_freelist.h:52-63@v3.15.0rc1#_PyFreeList_Push")}, and popping is two plus a call to `_Py_NewReference`, which is what puts a fresh count of one back where the link was, {cite("Include/internal/pycore_freelist.h:86-95@v3.15.0rc1#_PyFreeList_Pop")}.

You can see both ends of it in `float`. Making one starts with a pop and only calls the allocator if the stash is empty, {cite("Objects/floatobject.c:124-137@v3.15.0rc1#PyFloat_FromDouble")}. Freeing one is a single macro that pushes, and falls back to actually freeing if the stash is full, {cite("Objects/floatobject.c:229-234@v3.15.0rc1#_PyFloat_ExactDealloc")}.
""")


lesson.md(f"""
## Measuring the caps without opening the header

Reading `100` off a report is not the same as measuring it. Here is a way to get the same number from outside, which also happens to be a second proof that free lists are per type.

Drop a large batch of one type, then allocate the same number of a different type that happens to be the same size, and count how many of them land on the addresses the first batch had. Everything the free list kept is invisible to the second type. Everything it let go is fair game for the allocator, and the second type will find it.

So the number that lands is the batch size minus the cap.

A float is 24 bytes and a small int is 28, which fall in the same allocator size class, so an int can reuse a float's block. A list and a one item tuple are 56 each. That gives two independent measurements.

{lesson.claim("the cap on a free list can be measured from Python, as the number of dropped objects a different type of the same size can reach")}
""")


lesson.code(
    """
def spillover(make_a, make_b, count):
    \"\"\"How many of count dropped a-objects a batch of b-objects can reach.\"\"\"
    gc.collect()
    batch = [make_a(n) for n in range(count)]
    addresses = {id(item) for item in batch}
    del batch
    others = [make_b(n) for n in range(count)]
    landed = sum(1 for item in others if id(item) in addresses)
    del others
    return landed


print("  dropped   floats an int can reach   lists a tuple can reach")
for count in [40, 80, 120, 200, 300]:
    floats = spillover(lambda n: float(n) + 0.5, lambda n: 10**8 + n, count)
    lists = spillover(lambda n: [n], lambda n: tuple([n]), count)
    print(f"  {count:7}   {floats:22}   {lists:22}")
""",
    varies="The exact float numbers can be one out either way, because the measurement itself "
    "allocates a float or two. The step at a hundred and the step at eighty are the point.",
)


lesson.md("""
Drop forty floats and an int can reach none of them, because all forty are on the float free list. Drop three hundred and an int can reach about two hundred, because only a hundred were kept. The crossover is the cap, and it is a hundred for floats and eighty for lists, which is what the header says.

The lists column is exact: `count - 80` every time. The floats column is a point or two high, because building the second batch frees a float or two of its own along the way.

## Twenty lists for tuples, one per size

Tuples are the odd one out, and O11 hinted at why. A tuple's size is part of its allocation, so one stash would be useless: you cannot hand a dead tuple of nine items to something that wants three.

So tuples get an array of stashes, one for every size from one item up to twenty, and `tuple_alloc` indexes it with `size - 1`. The report lists them separately, which means the boundary is something you can read rather than something you have to trust.
""")


lesson.code("""
sizes = []
for line in freelist_report().splitlines():
    if "sized PyTupleObjects" in line:
        sizes.append(int(line.split()[2].split("-")[0]))

print(f"  tuple sizes with a free list  {min(sizes)} up to {max(sizes)}")
print(f"  how many lists that is        {len(sizes)}")
print(f"  is there one for 21 items     {21 in sizes}")
""")


lesson.md(f"""
Twenty lists, sizes one through twenty, and nothing above that. `PyTuple_MAXSAVESIZE` is 20, {cite("Objects/tupleobject.c:36-62@v3.15.0rc1#tuple_alloc")}.

{figure("one-list-per-tuple-size", "sizes one to twenty each get a free list and nothing larger does")}

The boundary shows up in addresses too, and the way it shows up is worth walking through slowly.

A tuple of nineteen items is 200 bytes and one of twenty is 208. The allocator rounds up to a multiple of sixteen, so both land in its 208 byte class, and if only the allocator were involved, dropping a nineteen would give its memory straight to a twenty.

A tuple of twenty one is 216 bytes and one of twenty two is 224. Same story, both in the 224 byte class.

So the two pairs look identical from the allocator's point of view. They are not identical, because one pair is inside the free list range and the other is outside it.

{lesson.claim("tuples of one to twenty items each have their own free list, so two neighbouring sizes in that range never share memory even when the allocator would let them, while two neighbouring sizes above twenty do")}
""")


lesson.code(
    """
def then(first, second):
    \"\"\"Drop a tuple of one size, make one of the next, and see if the memory is the same.\"\"\"
    dropped = tuple([0] * first)
    where = id(dropped)
    del dropped
    return id(tuple([0] * second)) == where


print("  sizes    same allocator class   same memory")
for first in [19, 21]:
    second = first + 1
    a, b = sys.getsizeof(tuple([0] * first)), sys.getsizeof(tuple([0] * second))
    print(f"  {first} then {second}   {a} and {b} bytes    {then(first, second)}")
""",
    varies="The byte counts are smaller on a 32 bit build and the allocator rounds in eight "
    "byte steps rather than sixteen, so neither pair shares a size class there and the last "
    "column reads False for both. The reason the first row is False is the same either way.",
)


lesson.md(f"""
Nineteen and twenty do not share, because the free list caught the nineteen and put it on the nineteen shelf, where nothing asking for twenty will ever look.

Twenty one and twenty two do share, because neither has a shelf. They went back to the allocator, which does not care what shape a tuple is, only that 216 and 224 both round to 224.

## A subclass does not get the deal

Look at the last few lines of `list_dealloc`. The push onto the free list is inside an `if`, and the test is {term("exact type check", "`PyList_CheckExact`")} rather than `PyList_Check`, {cite("Objects/listobject.c:565-578@v3.15.0rc1")}.

That distinction matters everywhere in CPython. `PyList_Check` says yes to anything inheriting from `list`. `PyList_CheckExact` says yes only to `list` itself. A subclass can have extra fields, a different size and its own deallocation function, so recycling one as if it were a plain list would be wrong.

The consequence is that a subclass quietly loses the optimisation, and the report will show it.

{lesson.claim("only exact instances of a type go on its free list, so a subclass of list or float is freed normally and the stash stays empty")}
""")


lesson.code(
    """
class MyList(list):
    pass


class MyFloat(float):
    pass


rounds = [
    ("plain lists", lambda n: [n], "PyListObjects"),
    ("list subclass", lambda n: MyList([n]), "PyListObjects"),
    ("plain floats", lambda n: float(n) + 0.5, "PyFloatObjects"),
    ("float subclass", lambda n: MyFloat(n + 0.5), "PyFloatObjects"),
]

for label, make, kind in rounds:
    gc.collect()
    junk = [make(n) for n in range(300)]
    del junk
    print(f"  300 {label:15} dropped, {held(kind):3} on the free list afterwards")
""",
    varies="The two subclass rows print two or three depending on the version, because that "
    "is the interpreter's own leftovers rather than anything the loop made. The eighty and "
    "the hundred are the same everywhere.",
)


lesson.md(f"""
Three hundred plain lists leave eighty behind. Three hundred subclass instances leave two or three, which is the interpreter's own background noise rather than anything from the loop.

This is a small thing on its own and a large thing in aggregate. Subclassing a builtin is a normal thing to do and it costs you a fast path you never knew you had. It is the same shape of surprise as O08, where an instance that gets an attribute assigned outside `__init__` falls off the shared key layout.

## Who empties them

A free list holds dead objects forever, which is fine until it is not. The header comment says the reason: objects sitting on a free list keep an allocator {term("arena", "arena")} occupied, and an arena can only go back to the operating system when every {term("pool", "pool")} inside it is empty, {cite("Python/gc_gil.c:6-15@v3.15.0rc1#_PyGC_ClearAllFreeLists")}.

So something has to clear them, and the cycle collector does. But not on every pass. The call is guarded, and the guard is the interesting part, {cite("Python/gc.c:1607-1612@v3.15.0rc1")}.

{figure("who-empties-them", "generations zero and one leave the free lists alone and generation two clears them")}

Three {term("generation", "generations")}, and only a collection of the oldest one empties the stashes. `gc.collect()` with no argument collects the oldest, so the common call does clear them. `gc.collect(0)` does not.

{lesson.claim("free lists are emptied by the cycle collector only when it collects the oldest generation, so gc.collect(0) leaves them full and a bare gc.collect() empties them")}
""")


lesson.code(
    """
for generation in [0, 1, 2]:
    gc.collect()
    junk = [float(n) + 0.5 for n in range(300)]
    del junk
    before = held("PyFloatObjects")
    gc.collect(generation)
    after = held("PyFloatObjects")
    print(f"  gc.collect({generation}): {before} floats held, {after} afterwards")
""",
    varies="The number left after the oldest generation is collected is whatever the collection "
    "itself allocated, a handful either way. What matters is that it is no longer a hundred.",
)


lesson.md("""
Generations zero and one leave the hundred untouched. Generation two takes it down to nothing.

This is why memory usage sometimes drops after a garbage collection that had no cycles to find. The collector did not free your objects. It emptied twenty two stashes of objects that were already dead.
""")


lesson.md("""
## Try it yourself

Three things to poke at.

The first is the slice free list, which has a cap of one. Build two slices, note both addresses, drop them both, and build two more. Only one address should come back. It is the smallest free list in the interpreter and the easiest to fill.

The second is the iterator free lists. `iter([])` and `iter(())` each have one with a cap of ten. Write a loop that makes and drops fifteen list iterators and use the report to watch the count stop at ten. Then check whether an iterator over a subclass of list gets the same treatment.

The third is a timing question. Making and dropping a tuple of twenty items goes through a free list and making one of twenty one does not, so the second should cost a little more. Use `timeit` on `tuple(src)` for sizes seventeen through twenty four and see whether the step is visible above the noise on your machine. It is small, and copying one more pointer costs something too, so this is more of an honest look at how hard microbenchmarks are than a clean result.
""")


lesson.md("""
## What just happened

Dropping an object does not usually free its memory. Twenty two types keep a stash of their own dead objects and hand the memory straight to the next one, and the stash is not a container, it is a chain threaded through the first word of each dead object, where the reference count used to be.

The reuse is by type and not by size, which you can see by dropping a list and asking for a tuple of exactly the same number of bytes. The tuple does not get it. Another list does.

Every stash has a cap. A hundred floats, eighty lists, eighty dicts, ten iterators, one slice. You can read the counts out of a running interpreter with `sys._debugmallocstats`, once you redirect file descriptor 2 rather than `sys.stderr`, and you can measure the caps from outside by counting how many dropped objects a different type of the same size can still reach.

Tuples get twenty stashes rather than one, indexed by size, because a tuple's length is part of its allocation. Neighbouring sizes inside that range never share memory even when the allocator would allow it. Neighbouring sizes above it do.

None of this applies to subclasses. The push is guarded by an exact type check, so subclassing `list` costs you the free list.

The cycle collector empties every stash, but only when it collects the oldest generation. `gc.collect(0)` leaves them alone.

## What is next

O13 is weak references, and it follows on directly. This lesson was about objects that outlive their last reference by accident of how memory is managed. A weak reference is the deliberate version of the opposite problem: a way to point at an object without being a reason it stays alive, and the only way from Python to watch the moment one actually dies.

That matters here because it is the tool that turns everything in this lesson from an inference about addresses into a direct observation. A weak reference to an object on a free list is dead, even though the memory is still there and still holding the shape of what used to be an object.
""")


raise SystemExit(lesson.save())
