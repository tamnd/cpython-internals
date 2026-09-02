#!/usr/bin/env python
"""M04. Who owns what.

The fourth lesson of the memory part. M01 to M03 were about where memory comes from. This one
is about what decides when it goes back, which is a single number per object and a protocol for
who is allowed to change it.

O01 already read the count out of the object header byte by byte. This lesson does not repeat
that. It is about the rules: what adds one, what does not, what happens the instant it reaches
zero, and the two places where the rules produce results that surprise people.

Everything here runs in place with no subprocess and no environment variable, so this is one of
the few memory lessons that works fully in a browser as well.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("m04-who-owns-what", "m04")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("m04-who-owns-what").figure


lesson.md(f"""
# M04. Who owns what

{badge}

Every object in your program carries a number saying how many things are pointing at it. When that number reaches zero the object is destroyed on the spot, in the middle of whatever line of code took the last reference away.

{figure("zero-means-now", "the last holder letting go, the count reaching zero and the destruction spreading")}

That is the whole memory management story for the great majority of objects. The cycle collector everyone talks about is the exception, not the rule, and it exists only because of one gap in this design that you will be able to measure by the end of the lesson.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Include/refcount.h:417-430@v3.15.0rc1`.

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

Nothing here needs a second interpreter, an environment variable or a special build, so every cell runs everywhere, including in a browser. It does read raw memory through `ctypes`, which means a wrong address would be a crash rather than an exception, so read what a cell does before you change it.

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
## The number you read is one too high

Start with the tool everybody reaches for first, and the thing it does that trips people up. `sys.getrefcount` says so in its own docstring {cite("Python/sysmodule.c:2015-2033@v3.15.0rc1#sys_getrefcount_impl")}: the answer is one higher than you expect, because passing the object to it is itself a reference.

There is a way around that. The count is the first field of the object, so once you have an address you can read it without passing the object anywhere {cite("Include/refcount.h:105-117@v3.15.0rc1#_Py_REFCNT")}. Take `id(thing)` first, hold on to the plain integer, and read from that.

{figure("the-extra-one", "sys.getrefcount and a direct memory read of the same object, one apart")}

{lesson.claim("A memory read of the count is exactly one lower than sys.getrefcount, and the difference is the argument")}
""")


lesson.code("""
import ctypes

thing = ["nobody else has a pointer to this"]
AT = id(thing)


def count():
    return ctypes.c_ssize_t.from_address(AT).value


print(f"  sys.getrefcount(thing)   {sys.getrefcount(thing)}")
print(f"  the memory at id(thing)  {count()}")
print()
print("  one name is holding it, so 1 is the honest answer")
""")


lesson.md(f"""
One name, one reference. `sys.getrefcount` said two because for the moment it was running, two things were pointing at that list: your name and its own argument.

## What takes a reference

Now the rule that makes the whole thing work: every holder holds exactly one, and no holder is special {cite("Include/refcount.h:285-292@v3.15.0rc1#ob_refcnt")}.

It does not matter whether the holder is a name, a slot in a list, a value in a dictionary, an attribute, a captured variable in a closure or a default argument. Each one is worth one, and each one gives it back when it lets go.

{figure("what-takes-a-reference", "eight different ways of holding an object, each worth exactly one")}

{lesson.claim("Every distinct way of holding an object adds exactly one to its count, and removing the holder takes exactly one away")}
""")


lesson.code("""
def show(label):
    print(f"  {label:32} {count()}")


show("just the name")

second = thing
show("plus a second name")
del second

box = [thing]
show("plus an item in a list")
del box

table = {"k": thing}
show("plus a value in a dict")
del table

pair = (thing,)
show("plus an item in a tuple")
del pair


class Holder:
    pass


owner = Holder()
owner.attr = thing
show("plus an attribute")
del owner


def make_closure():
    captured = thing

    def inner():
        return captured

    return inner


held = make_closure()
show("plus a closure capture")
del held


def with_default(x=thing):
    return x


show("plus a default argument")
del with_default

show("back to just the name")
""")


lesson.md(f"""
Up one, down one, eight times, and back where it started. Nothing is approximate about this. If a holder ever forgot to give its one back, the object would sit in memory forever, and if a holder gave back one it never took, the object would be destroyed while somebody was still using it.

## Owned or borrowed

Which brings us to the distinction the whole protocol turns on.

A {term("new reference")} is one the count went up for. You have it, you are responsible for it, and you have to put it back down when you are done. A {term("borrowed reference")} is a pointer at an object whose count did not move for you. You owe nothing, and it is valid only for as long as whoever does own it keeps owning it.

{figure("owned-or-borrowed", "an owned reference against a borrowed one")}

The C API has both kinds, sometimes for the same operation. `PyList_GetItem` hands back a borrowed pointer straight out of the list, while `PyList_GetItemRef` wraps the same pointer in `Py_NewRef` and gives you an owned one {cite("Objects/listobject.c:380-419@v3.15.0rc1#PyList_GetItemRef")}.

The interesting part is that the interpreter does this too, and you can see it in ordinary bytecode. `LOAD_FAST` copies a local onto the stack and bumps the count. `LOAD_FAST_BORROW` copies the same pointer and does not {cite("Python/bytecodes.c:283-291@v3.15.0rc1#LOAD_FAST_BORROW")}, because the local variable is going to keep holding it for the whole time the value sits on the stack, so a second reference would be wasted work.

{lesson.claim("The compiler picks the borrowing form of a local variable load wherever the local outlives the value on the stack, and the opcode name says so")}
""")


lesson.code("""
import dis


def adds(x, y):
    return x + y


def stores(x):
    y = x
    return y


def calls(x):
    return len(x)


for fn in (adds, stores, calls):
    names = [one.opname for one in dis.get_instructions(fn)]
    print(f"  {fn.__name__:8} {' '.join(names)}")

print()
print("  the ones with BORROW in the name did not touch any count")
""")


lesson.md(f"""
Look at `stores`. The one load that is a plain `LOAD_FAST` is the one being stored into another local, which needs a reference of its own. Every other load in these three functions borrows.

This is worth knowing for a reason beyond curiosity. Reference counting is the single most frequent thing the interpreter does, so the work of not doing it shows up directly in how fast Python runs.

## Zero means now

The other half of the protocol is what happens when the last holder lets go. It is three lines of C {cite("Include/refcount.h:417-430@v3.15.0rc1#Py_DECREF")}: subtract one, and if the result is zero, call the type's destructor {cite("Objects/object.c:3289-3320@v3.15.0rc1#_Py_Dealloc")}.

There is no queue, no sweep and no later. It happens inside the instruction that dropped the count, before the next one runs. And because destroying an object releases everything it was holding, one death sets off the next.

{lesson.claim("A rebinding destroys the old value before the next statement runs, and a container destroys its contents in reverse order")}
""")


lesson.code("""
class Loud:
    def __init__(self, name):
        self.name = name

    def __del__(self):
        print(f"      gone: {self.name}")


def timing():
    holder = [Loud("first"), Loud("second"), Loud("third")]
    print("    the line before the rebinding")
    holder = None
    print("    the line after it")
    return holder


timing()
print()
print("  three destructors ran between two prints on adjacent lines")
""")


lesson.md(f"""
Three objects destroyed in the gap between two `print` calls, in the reverse of the order they went into the list.

## Which is why the last one is delicate

Now the consequence, and it is the one that bites people who write `__del__`.

Your destructor runs synchronously, in the middle of somebody else's work. If it was a dictionary value being replaced, the dictionary has already been updated and your code sees the new state. The C code doing the replacing cannot afford to call your Python in the middle of its own update, so it finishes rearranging itself first and drops the old value afterwards.

You can read the pattern in `dict.clear` {cite("Objects/dictobject.c:3073-3098@v3.15.0rc1#clear_lock_held")}. It saves the old keys and values, points the dictionary at an empty table, and only then starts dropping the references. By the time your destructor runs, the dictionary is already empty.

{figure("what-the-del-sees", "what a destructor sees for a replacement and for a clear")}

{lesson.claim("A destructor triggered by replacing or clearing a container sees the container in its finished state, never a half updated one")}
""")


lesson.code("""
class Nosy:
    def __init__(self, name):
        self.name = name
        self.where = None

    def __del__(self):
        print(f"      {self.name} is going, and sees {self.where!r}")


box = ["placeholder"]
box[0] = Nosy("replaced in a list")
box[0].where = box
box[0] = "the new value"

table = {}
table["k"] = Nosy("replaced in a dict")
table["k"].where = table
table["k"] = "the new value"

emptied = [Nosy("cleared from a list")]
emptied[0].where = emptied
emptied.clear()

wiped = {}
wiped["k"] = Nosy("cleared from a dict")
wiped["k"].where = wiped
wiped.clear()

print()
print("  four destructors, and not one of them saw a container mid update")
""")


lesson.md(f"""
This is not a small courtesy. Anything your destructor does, including raising, iterating the container or putting the object back somewhere, has to happen against a structure that makes sense. {term("reentrancy")} is the word for a piece of code being entered again while it is still running, and getting it wrong here would mean a dictionary being read while half of it points at freed memory.

## Where counting alone stops

One gap, and it is the reason the cycle collector exists.

Counting works when the pointers form a chain. Drop the front of the chain and every link falls in turn. It stops working the moment the pointers form a loop, because then each object is being held up by another object that nobody can reach.

{figure("stuck-at-one", "a chain of three collapsing against a loop of two that does not")}

Nothing about the count is wrong here. Both objects genuinely do have one thing pointing at them. The count simply cannot tell the difference between a pointer from something reachable and a pointer from something that is itself garbage.

{lesson.claim("Two objects that hold each other keep a count of one apiece after every name for them is gone, and nothing in the counting rules will ever take it to zero")}
""")


lesson.code(
    """
import gc


class Quiet:
    def __init__(self, name):
        self.name = name
        self.other = None


first = Quiet("first")
last = Quiet("last")
first.other = last
last.other = first

at_first, at_last = id(first), id(last)


def count_at(at):
    return ctypes.c_ssize_t.from_address(at).value


print(f"  while both names exist   {count_at(at_first)} and {count_at(at_last)}")
del first, last
print(f"  after both names go      {count_at(at_first)} and {count_at(at_last)}")
print()
print("  nothing can reach either one, and neither will ever reach zero")
print(f"  gc.collect() found {gc.collect()} objects, these two among them")
""",
    varies="The number the collector reports depends on what else in your session had become "
    "unreachable by the time you ran the cell, so it is often larger than two. The two counts "
    "above it are the part that does not move.",
)


lesson.md("""
Two objects, unreachable from any name in the program, both sitting at a count of one. Without something else running, that memory is gone for the life of the process.

That something else is the cycle collector, and M07 is about how it finds these. It is worth noticing now that it has a genuinely hard job: it has to work out that the only pointers keeping these two alive come from each other, without a list of who points at what.

## Try it yourself

Three things, and the first takes a minute.

Read the count of an object you did not make, like a module or a function you imported, and see how many things in the interpreter are holding it. `count_at(id(sys))` will do. Then check that against `len(gc.get_referrers(sys))`, which lists the ones the collector knows about. The two numbers will not match, and the gap is the references held by things the collector does not track.

Add a `__del__` to the `Quiet` class in the last cell and run it again. The two objects still get collected, and this tells you something specific about how the collector handles objects with destructors, which has changed more than once in CPython's history and is now different from what a lot of older advice says.

Take the `stores` function from the bytecode cell and give it more locals, more assignments between them, and a loop. Watch which loads borrow and which do not. There is a rule behind it and you can work out most of it from examples.

## What you now know

Every object carries a count of how many things are pointing at it, and it is the first field in the object, readable from Python with an address and `ctypes`.

`sys.getrefcount` always answers one high, because being passed as an argument is itself a reference. Reading the memory at `id(thing)` avoids that, and gives the number you actually meant to ask for.

Every holder is worth exactly one. A name, a list slot, a dictionary value, a tuple item, an attribute, a closure capture and a default argument all count the same, and all give their one back when they let go.

A reference is either owned, meaning the count moved for you and you owe it back, or borrowed, meaning it did not and you do not. Both exist in the C API, sometimes for the same operation, and both exist in the bytecode, where `LOAD_FAST_BORROW` is the interpreter skipping work it does not need to do.

When a count reaches zero the object is destroyed immediately, inside the instruction that dropped it, and destroying an object drops everything it was holding, so one death causes the next. A container finishes rearranging itself before it drops anything, so a destructor never sees a half updated structure.

Two objects that point at each other stay at a count of one apiece with nothing able to reach them. That single gap is the entire reason CPython has a garbage collector at all.

## What is next

M05 is about the objects that opt out. `None`, `True`, the small integers and a lot of the strings CPython uses internally never have their counts touched, because a count sitting in a shared object is a cache line every thread wants to write to. The mechanism is one very large number and two flag bits, and it is what made free threading possible at all.
""")


raise SystemExit(lesson.save())
