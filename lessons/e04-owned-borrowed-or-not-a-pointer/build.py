#!/usr/bin/env python
"""E04. Owned, borrowed, or not a pointer.

The fourth lesson of the interpreter part. E03 said a local variable is a numbered slot in
an array on the end of the frame. This one is about what is actually in that slot, which
since 3.14 is not a plain object pointer.

The hook is that a rule everybody learned stopped being true. `sys.getrefcount` used to
always report one more than you expected, because asking created a reference. In 3.14 and
later, asking about a local usually creates nothing, and the number goes down by one.

From there it is all one idea. Objects are aligned, so the bottom two bits of a pointer are
always zero, so they are free to carry a flag. One flag value means this slot did not count
its reference and releasing it should do nothing. Another means the word is not a pointer at
all.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("e04-owned-borrowed-or-not-a-pointer", "e04")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("e04-owned-borrowed-or-not-a-pointer").figure


lesson.md(f"""
# E04. Owned, borrowed, or not a pointer

{badge}

Here is a rule a lot of people know. `sys.getrefcount` always answers one higher than the truth, because passing the object to `getrefcount` is itself a reference.

That rule is out of date. Ask about a local variable inside a function and you now get the number without the extra one. Nothing about the object changed. What changed is that handing a local to a function no longer counts as taking a reference.

{figure("what-is-in-a-slot", "one machine word holding an owned pointer, a borrowed pointer, or a number")}

The slot a local lives in does not hold an object pointer any more. It holds a pointer with the bottom two bits used to say something about it, and sometimes it holds no pointer at all.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Include/internal/pycore_stackref.h:533-537@v3.15.0rc1#PyStackRef_Borrow`.

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

The change this lesson is about landed in 3.14, so the numbers below are the same on 3.14 and 3.15 and different on everything older. There is one section near the end that only 3.15 answers, and it says so.
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
## The number everybody quotes

Five ways of asking the same question about the same kind of object.

{lesson.claim("sys.getrefcount answers 1 for a local variable, without the extra one for the asking, because handing a local to a function does not create a reference")}
""")


lesson.code(
    """
def in_a_function():
    thing = object()
    return sys.getrefcount(thing)


def one_call_deeper(thing):
    return sys.getrefcount(thing)


def hands_it_on():
    thing = object()
    return one_call_deeper(thing)


def also_in_a_list():
    thing = object()
    box = [thing]
    count = sys.getrefcount(thing)
    box.clear()
    return count


def out_of_a_list():
    box = [object()]
    return sys.getrefcount(box[0])


at_module_level = object()

print(f"  a local, asked directly        {in_a_function()}")
print(f"  a local passed down a call     {hands_it_on()}")
print(f"  a local also stored in a list  {also_in_a_list()}")
print(f"  taken back out of the list     {out_of_a_list()}")
print(f"  a module level name            {sys.getrefcount(at_module_level)}")
""",
)


lesson.md(f"""
On 3.13 those five lines answered 2, 3, 3, 2 and 2. The first three all dropped.

{figure("what-getrefcount-says", "the same four questions answered differently by 3.13 and by 3.14 onward")}

The last two rows are the control. A module level name is loaded with `LOAD_GLOBAL`, which does take a reference, so it still answers 2. Taking the object back out of a list goes through a subscript, which also takes one, so that answers 2 as well. The rows that changed are the ones where the value came straight out of a local slot.

## What is actually in a slot

Every object in CPython is aligned in memory. The allocator never hands back an address that is not a multiple of four, and on a 64 bit machine almost everything lands on sixteen. That means the bottom two bits of any object pointer are zero, always, on every object, and carrying two bits that are always zero is a waste.

{lesson.claim("every object address is a multiple of four, so the bottom two bits of an object pointer are always zero and free to be used for something else")}
""")


lesson.code(
    """
for label, one in [
    ("a plain object", object()),
    ("a list", []),
    ("a dict", {}),
    ("a string", "some text"),
    ("a big integer", 12345678901234567890),
    ("a float", 1.5),
    ("a module", sys),
    ("None", None),
    ("the number 7", 7),
]:
    print(f"  {label:16} at {id(one):>14}   mod 4 {id(one) % 4}   mod 8 {id(one) % 8}")
""",
    varies="The addresses are different every run, and that is the whole point of printing "
    "them rather than asserting anything. The last column is the one to watch on a 32 bit "
    "build such as the browser one: some objects there land on 4 rather than 8, which is "
    "exactly why CPython takes two bits and not three.",
)


lesson.md(f"""
CPython takes two of those bits. A frame slot holds a {term("stack reference", "stack reference")}, which is that pointer with a two bit tag on the end, {cite("Include/internal/pycore_stackref.h:53-58@v3.15.0rc1#Py_TAG_REFCNT")}.

{figure("what-the-bottom-bits-say", "the four tag values and what releasing each one does")}

The interesting one is 01. It means this slot is holding the object but never counted it, so releasing the slot must not decrement anything. Releasing a reference is now a test on two bits followed by the decrement it used to do unconditionally, {cite("Include/internal/pycore_stackref.h:677-684@v3.15.0rc1#PyStackRef_CLOSE")}. Taking a borrow is even simpler: it is one bitwise or, {cite("Include/internal/pycore_stackref.h:533-537@v3.15.0rc1#PyStackRef_Borrow")}.

## Owned or borrowed, decided when you compile

Nothing at runtime decides which kind of load to do. The compiler does, one use site at a time, and you can read its answer off the disassembly. There are two instructions where 3.13 had one, {cite("Python/bytecodes.c:283-291@v3.15.0rc1#LOAD_FAST_BORROW")}.

{lesson.claim("the compiler picks LOAD_FAST or LOAD_FAST_BORROW for each use of a local, so the same variable can be loaded both ways in one function")}
""")


lesson.code(
    """
import dis

cases = {
    "return x": "def f(x):\\n    return x\\n",
    "len(x)": "def f(x):\\n    return len(x)\\n",
    "x + y": "def f(x, y):\\n    return x + y\\n",
    "[x]": "def f(x):\\n    return [x]\\n",
    "yield x": "def f(x):\\n    yield x\\n",
    "y = x": "def f(x):\\n    y = x\\n    return y\\n",
    "x[y]": "def f(x, y):\\n    return x[y]\\n",
    "print(x)": "def f(x):\\n    print(x)\\n",
}

for label, source in cases.items():
    namespace = {}
    exec(source, namespace)
    loads = [
        one.opname
        for one in dis.get_instructions(namespace["f"])
        if one.opname.startswith("LOAD_FAST")
    ]
    print(f"  {label:10} {' '.join(loads)}")
""",
)


lesson.md(f"""
Seven of those eight borrow every load. The odd one out is `y = x`, where the first load is a real one, and the reason is worth having in full.

A borrowed reference is only good for as long as the thing it was borrowed from stays put. The compiler makes that provable by fixing two lifetimes: a borrow pushed on the stack lives until the instruction that pops it finishes, and a local lives until something overwrites it or the frame goes away, {cite("Python/flowgraph.c:2826-2857@v3.15.0rc1#optimize_load_fast")}. So it can borrow whenever the value is consumed inside one instruction and never stored anywhere.

{figure("borrowed-or-owned", "four lines of Python and what the compiler proved about each one")}

`y = x` breaks that. The value ends up in a second slot, which outlives the `STORE_FAST` that put it there, so the load has to be a real one. `return x` looks like it should break it too, and does not, because `RETURN_VALUE` promotes a borrow to a counted reference on the way out.

## When a borrow is not allowed

The other half of the rule is about things that leave the stack for the heap. A list, a dictionary, a frame object, a generator. Anything stored in one of those has to be a counted reference, because the container can outlive the frame by any amount.

{figure("when-a-borrow-is-promoted", "four steps from wanting a local to deciding how to load it")}

The instruction that does the storing is the one that pays. `[x]` loads `x` borrowed, and then `BUILD_LIST` takes its own reference on the way in. You can watch that happen by counting.

{lesson.claim("a value loaded borrowed and then stored in a container gains a counted reference at the moment it is stored, and loses it again when the container drops it")}
""")


lesson.code(
    """
def watch():
    thing = object()
    yield "just a local", sys.getrefcount(thing)
    box = [thing]
    yield "after a list took it", sys.getrefcount(thing)
    box.append(thing)
    yield "after the same list took it twice", sys.getrefcount(thing)
    box.clear()
    yield "after the list let go", sys.getrefcount(thing)


for label, count in watch():
    print(f"  {label:36} {count}")
""",
)


lesson.md(f"""
## Immortal objects get the tag for free

`None` never needs counting. Neither do `True`, `False`, the small integers or any type object. They are {term("immortal object", "immortal")}, so nothing will ever free them and every increment and decrement spent on them is wasted work.

The tag makes that fall out for nothing. An object carries a flag saying it is immortal, and the value of that flag bit is deliberately the same as the value of the tag bit that means do not count. So building a stack reference from an immortal object is one bitwise and, with no branch and no test, {cite("Include/internal/pycore_stackref.h:553-569@v3.15.0rc1#PyStackRef_FromPyObjectSteal")}.

The number you see for one of those is a marker rather than a count. On a 64 bit build it is three shifted up by thirty, {cite("Include/refcount.h:44-48@v3.15.0rc1#_Py_IMMORTAL_INITIAL_REFCNT")}, which is large enough that no real object could reach it by accident.

{lesson.claim("the reference count of an immortal object is a fixed marker that does not move no matter how many references you take")}
""")


lesson.code(
    """
marker = sys.getrefcount(None)

for label, one in [("None", None), ("True", True), ("the number 7", 7), ("the type int", int)]:
    before = sys.getrefcount(one)
    holder = [one] * 100000
    after = sys.getrefcount(one)
    del holder
    steady = before == after == marker
    print(f"  {label:16} {before:>12} then {after:>12}   the same marker {steady}")

ordinary = ["a string nobody else has"]
before = sys.getrefcount(ordinary[0])
holder = ordinary * 100000
after = sys.getrefcount(ordinary[0])
del holder
print(f"  {'an ordinary str':16} {before:>12} then {after:>12}")
print()
print(f"  the marker is {marker}, and 3 << 30 is {3 << 30}")
""",
    varies="A 32 bit build uses a different marker. The browser one answers 1879048192, "
    "which is 7 shifted up by 28, because there is no room for the 64 bit value and "
    "statically allocated immortals get their own number there. It is still a marker, and "
    "it still does not move.",
)


lesson.md(f"""
## A slot with no object in it

The tag has one value left, and 3.15 started using it. If the bottom two bits are 11, the rest of the word is not a pointer but a number shifted up by two, {cite("Include/internal/pycore_stackref.h:432-438@v3.15.0rc1#PyStackRef_TagInt")}.

The first thing it is used for is the position a `for` loop has reached. Iterating a list used to mean the iterator object kept an index inside itself. From 3.15 `GET_ITER` pushes a {term("tagged integer", "tagged integer")} onto the value stack next to the iterator, and the loop counts there, {cite("Python/bytecodes.c:3777-3787@v3.15.0rc1#_GET_ITER")}.

There is no way to see the number from Python. But there is no way to hide an extra stack slot either, and `co_stacksize` is computed at compile time and sitting on every code object.

{lesson.claim("a for loop needs one more value stack slot in 3.15 than in 3.14, and the extra slot holds the loop position as a number rather than an object")}
""")


lesson.code(
    """
shapes = {
    "for i in x": "def f(x):\\n    for i in x:\\n        pass\\n",
    "for i in [1, 2]": "def f():\\n    for i in [1, 2]:\\n        pass\\n",
    "a comprehension": "def f(x):\\n    return [i for i in x]\\n",
    "a while loop": "def f(n):\\n    while n:\\n        n -= 1\\n",
}

for label, source in shapes.items():
    namespace = {}
    exec(source, namespace)
    print(f"  {label:18} co_stacksize {namespace['f'].__code__.co_stacksize}")
""",
    differs="On 3.14 the three loops need one slot fewer, so the first two read 2 and the "
    "comprehension reads 4. The while loop is 2 on both, because it never makes an "
    "iterator and so never pushes a position.",
)


lesson.md("""
The while loop is the control again. It does not iterate anything, so there is no position to keep, so it needs the same room on both versions.

The behaviour is unchanged, which is worth checking rather than believing. Break out of a loop halfway and the iterator still knows where you got to, because the position is written back to it on the way out.
""")


lesson.code(
    """
for name, source in [("a list", [1, 2, 3, 4, 5]), ("a tuple", (1, 2, 3, 4, 5))]:
    walker = iter(source)
    for item in walker:
        if item == 2:
            break
    print(f"  broke out of {name:8} and the rest is still {list(walker)}")
""",
)


lesson.md(f"""
## Why any of this exists

Saving one increment on `LOAD_FAST` sounds small. It is not, because `LOAD_FAST` is the most common instruction in almost every Python program, and because the increment is not always cheap.

{figure("why-any-of-this-exists", "reference counting under the GIL against reference counting in a free threaded build")}

With the {term("free threaded build", "free threaded build")} the picture changes completely. Two threads touching the same object have to agree on its count, so the increment becomes an atomic operation, and an object that many threads touch becomes a point of contention rather than just a cost. A shared function, a shared module, a shared type: exactly the objects a loop loads over and over. The tag is what lets the interpreter not touch the count at all.

The tag means something slightly different in that build, {cite("Include/internal/pycore_stackref.h:636-648@v3.15.0rc1#PyStackRef_IsHeapSafe")}, but the shape is the same: a bit that says do not count this one.

{lesson.claim("in the free threaded build a counted reference is an atomic operation, which is why avoiding one on every local load matters more there than it does under the GIL", unobservable="You would need a free threaded build and a machine with several cores to see the difference, and this notebook is running on neither.")}
""")


lesson.code(
    """
import sysconfig

print(f"  free threaded build   {bool(sysconfig.get_config_var('Py_GIL_DISABLED'))}")
print(f"  the GIL is on         {sys._is_gil_enabled()}")
print(f"  pointer size in bytes {sys.maxsize.bit_length() // 8 + 1}")
""",
    varies="A free threaded build answers True, False on the first two lines, and a browser "
    "build reports four bytes on the third. Everything earlier in this lesson holds either "
    "way, which is the point of doing it with a tag rather than with two interpreters.",
)


lesson.md("""
## Try it yourself

Three things to try.

The first is to hunt for a use of a local that has to be owned. The rule is that the value must end up somewhere that outlives the instruction loading it, so look for anything that stores. Assignment to another name is the obvious one. Try a `global` statement, a `nonlocal`, a default argument, a `with` binding, unpacking a tuple into two names. Some of them will surprise you.

The second is about generators. The compiler promotes a borrow to a real reference when a value escapes into the heap, and a generator's frame is on the heap. Write a generator that takes an argument and yields it, and one that takes an argument and closes over it, and compare the loads to the non generator versions.

The third is the tagged integer. It is deliberately hard to see, so try to catch it indirectly. Compare `co_stacksize` for a loop over a list against one over a generator, a dict, a file. Not every iterator gets the treatment, and the ones that do not are the ones where an index into the thing would mean nothing.

## What just happened

A frame slot does not hold an object pointer. It holds a pointer with the bottom two bits used as a tag, which is free because every object address is a multiple of eight.

Tag 00 means the slot owns a counted reference and releasing it should decrement. Tag 01 means the slot is only borrowing, and releasing it does nothing. Tag 11 means the word is not a pointer at all.

The compiler decides which one, per use of each variable, and you can read the decision off the disassembly as `LOAD_FAST` against `LOAD_FAST_BORROW`. It borrows whenever it can prove the value is consumed before the slot it came from could go away, which is nearly always.

That is why `sys.getrefcount` of a local answers one lower than it used to. Nothing about counting changed. The reference that the asking used to create is not created any more.

Values that escape into the heap cannot be borrowed, so storing into a list or a dict takes a real reference at the moment of storing, and the count goes up then.

Immortal objects get the tag for free, because the flag that marks an object immortal is the same bit as the tag that says do not count. Their count is a fixed marker, three shifted up by thirty, and it never moves.

From 3.15 the fourth tag value carries a small number instead of a pointer, and the first use of it is the position a `for` loop has reached. That is why a loop over a list needs one more value stack slot in 3.15 than it did in 3.14.

All of it exists because of the free threaded build, where a counted reference is an atomic operation and a shared object is a point of contention.

## What is next

E05 is exceptions, and specifically why a `try` block that never raises costs nothing at all. There is no setup instruction and no runtime bookkeeping. The compiler writes a separate table off to one side saying which ranges of code are covered by which handler, and the interpreter only reads it when something has already gone wrong. That table is on every code object and you can print it.
""")


raise SystemExit(lesson.save())
