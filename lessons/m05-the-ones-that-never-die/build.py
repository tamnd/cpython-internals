#!/usr/bin/env python
"""M05. The ones that never die.

The fifth lesson of the memory part, and the other half of M04. M04 was the rule: every holder
adds one, and at zero the object goes. This one is about the objects the rule skips entirely.

O01 already read the count out of the object header and explained why an immortal object parks
at three billion and what the two flag bits above it mean. This lesson does not repeat that. It
is about which objects get the treatment, how you find the edge of the set from Python, the one
edge that moved between 3.14 and 3.15, and why you are not allowed to add to it yourself.

Everything here runs in place with no subprocess and no environment variable, so it works in a
browser as well as on a desktop build.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("m05-the-ones-that-never-die", "m05")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("m05-the-ones-that-never-die").figure


lesson.md(f"""
# M05. The ones that never die

{badge}

M04 finished with a rule that sounded absolute. Every holder adds one to an object's count, and the moment the count reaches zero the object is destroyed. There is a set of objects that rule does not apply to at all.

`None` is one of them. Put it into a hundred thousand containers and its count does not move once.

{figure("held-a-hundred-thousand-times", "None and an ordinary list, each put into a hundred thousand containers")}

That is not a special case inside the list or the dictionary. It is one very large number written into the object before your code starts, and every reference operation in the interpreter checks for it and then does nothing.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Include/refcount.h:47-50@v3.15.0rc1`.

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

Every cell here runs everywhere, including in a browser, with no subprocess and no special build. Two of them give a different answer on 3.14 than on 3.15, and both are marked where they appear, because the difference is the interesting part rather than a problem.

As in M04, some cells read raw memory through `ctypes`. A wrong address there is a crash rather than an exception, so read what a cell does before you change it.

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
## Some counts never move

Start by watching the thing happen.

The check is short. On a 64 bit build an object is {term("immortal object", "immortal")} if its count has climbed past two to the power of 31, and on a 32 bit build the line is two to the power of 30 {cite("Include/refcount.h:125-136@v3.15.0rc1#_Py_IsImmortal")}. Nothing real ever gets that many holders, so a count up there is a marker rather than a number.

The value they are parked at is `3ULL << 30` {cite("Include/refcount.h:47-50@v3.15.0rc1#_Py_IMMORTAL_INITIAL_REFCNT")}, which is a bit over three billion. O01 took that number apart byte by byte, including the two extra flag bits that some of them carry.

{lesson.claim("Putting an immortal object into a hundred thousand containers leaves its count exactly where it was, while an ordinary object's count goes up by a hundred thousand")}
""")


lesson.code(
    """
import ctypes

MINIMUM = 1 << (30 if ctypes.sizeof(ctypes.c_void_p) == 4 else 31)


def count_at(at):
    return ctypes.c_ssize_t.from_address(at).value


def forever(thing):
    return count_at(id(thing)) >= MINIMUM


mine = ["an ordinary list"]
AT_NONE, AT_MINE = id(None), id(mine)

print("  to start with:")
print(f"    None  {count_at(AT_NONE)}")
print(f"    mine  {count_at(AT_MINE)}")

holders = [[None, mine] for _ in range(100000)]
print("  after both go into a hundred thousand containers:")
print(f"    None  {count_at(AT_NONE)}")
print(f"    mine  {count_at(AT_MINE)}")

del holders
print("  and after every one of those containers is dropped:")
print(f"    None  {count_at(AT_NONE)}")
print(f"    mine  {count_at(AT_MINE)}")
""",
    varies="The exact number next to None depends on what the interpreter did before your code "
    "started, and on whether anything loaded a C extension built before these checks existed. "
    "The part that matters is that all three readings of it are the same.",
)


lesson.md(f"""
A hundred thousand increfs and a hundred thousand decrefs, and the number next to `None` is character for character the same three times.

That is the whole point. Every one of those operations on `mine` was a write to the same eight bytes of memory. Every one of them on `None` was a comparison that decided to do nothing.

{lesson.claim("an incref on an object shared between threads is a write to a cache line that every other thread wants at the same time, which is the cost immortality removes", unobservable="the cost is a hardware effect between cores, so from inside Python you can see that the write does not happen, which is what the cell above shows, but not what the write would have cost")}

## Who is on the list

So which objects get this and which do not. There is no flag you can set and no rule about types. It is a hand picked set, and the pattern behind the picking is worth seeing directly.

{figure("who-is-on-the-list", "a list of objects sorted into the ones that never die and the ordinary ones")}

{lesson.claim("None, True, the small integers, the empty tuple, the one character strings and every built in type and exception never die, while a function object, a module and anything you built yourself are ordinary")}
""")


lesson.code("""
made_here = "".join(["a", " ", "s", "t", "r", "i", "n", "g"])

roster = [
    ("None", None),
    ("True", True),
    ("the number 5", 5),
    ("the number 100000", 100000),
    ("Ellipsis", ...),
    ("NotImplemented", NotImplemented),
    ("the empty tuple", ()),
    ("the empty string", ""),
    ("the string a", "a"),
    ("the type int", int),
    ("the type object", object),
    ("ValueError", ValueError),
    ("the print function", print),
    ("the sys module", sys),
    ("a list I made", mine),
    ("a string I built", made_here),
]

for label, thing in roster:
    print(f"  {label:22} {'never dies' if forever(thing) else 'ordinary'}")

print()
print("  and the interpreter gives the same answer when you ask it directly:")
for label, thing in roster[:3] + roster[-2:]:
    print(f"    {label:22} {forever(thing)!s:5} against {sys._is_immortal(thing)}")
""")


lesson.md(f"""
`sys._is_immortal` is the interpreter's own answer {cite("Python/sysmodule.c:1049-1054@v3.15.0rc1#sys__is_immortal_impl")}, and it agrees with the memory read every time. It has a leading underscore because it is a debugging aid rather than something to build on, but it is a useful way to check that your own reading of the header is right.

Notice what sorted itself out. The number 5 never dies and the number 100000 does. `int` and `ValueError` never die and `print` does not. There is a shape to that, and the next section is about it.

Here is the same split across the whole of `builtins`, which is a big enough sample to see the pattern rather than guess at it.

{lesson.claim("every built in function in builtins is an ordinary object, and the only built in classes that are ordinary are the ones built at run time rather than compiled into the binary")}
""")


lesson.code(
    """
import builtins

entries = vars(builtins)
classes = [name for name, value in entries.items() if isinstance(value, type)]
plain = [name for name, value in entries.items() if type(value).__name__.startswith("builtin_")]

alive = sum(forever(value) for value in entries.values())
print(f"  builtins has {len(entries)} entries and {alive} of them never die")
print()

kept = sum(forever(entries[name]) for name in classes)
print(f"  of the {len(classes)} types and exception classes, {kept} never die")

kept = sum(forever(entries[name]) for name in plain)
print(f"  of the {len(plain)} plain functions, {kept} never die")
print()

HEAPTYPE = 1 << 9
print("  the classes that are the exception, and what they have in common:")
for name in [name for name in classes if not forever(entries[name])]:
    made = bool(entries[name].__flags__ & HEAPTYPE)
    print(f"    {name:16} built at run time rather than compiled in: {made}")
""",
    differs="The exact totals move between releases because builtins gains and loses entries, "
    "and 3.15 has a few more than 3.14. The split is the part that stays put: every function is "
    "out, and the only classes that are out are the ones built at run time.",
)


lesson.md(f"""
So the rule for classes is not about being built in, it is about where the object lives. A {term("static type")} sits inside the binary itself and there is nothing to free, so it is immortal for nothing. A {term("heap type")} was allocated while the interpreter started, like the two the cell just found, and it gets counted like anything else. The functions are all ordinary for the same reason: each one is an object made at startup, the same way your own functions are made when your module is imported.

## The set is small on purpose

Every one of these objects is never freed. That is not a side effect, it is the definition: the count never comes back down, so nothing ever reaches zero, so the destructor never runs. For the life of the process, that memory stays.

Which means the set cannot be large, and it is not.

{figure("the-fixed-set", "the four groups of objects that never die and roughly how many are in each")}

Two of the groups are just tables built before your code runs. There are 256 one character strings, one for every byte value, and indexing or slicing a string of ASCII hands one back rather than building anything {cite("Objects/unicodeobject.c:1809-1814@v3.15.0rc1#get_latin1_char")}. That is the {term("single character cache")}.

{lesson.claim("Exactly 256 one character strings never die, the empty tuple and the empty bytes never die, and a one item tuple built the same way is ordinary")}
""")


lesson.code("""
chars = [n for n in range(400) if forever(chr(n))]
print(f"  one character strings that never die: {min(chars)} through {max(chars)}")
print(f"  which is {len(chars)} of the 400 I checked")
print()

for n in (0, 127, 255, 256, 257):
    print(f"    chr({n:3})  {'never dies' if forever(chr(n)) else 'ordinary'}")

print()
print("  and the empty ones, which are worth knowing about:")
for label, thing in [
    ("()", ()),
    ("(1,)", (1,)),
    ("b''", b""),
    ("b'a'", b"a"),
    ("''", ""),
    ("frozenset()", frozenset()),
    ("[]", []),
    ("{}", {}),
]:
    print(f"    {label:14} {'never dies' if forever(thing) else 'ordinary'}")
""")


lesson.md(f"""
An empty tuple never dies because there is only ever one of them, so every expression that produces an empty tuple hands back the same object. A one item tuple is a real allocation like anything else. An empty list is not on the list either, and could not be, because you can append to it.

## Where the small integers stop

The other pre built table is the small integers {cite("Include/internal/pycore_runtime_structs.h:96-98@v3.15.0rc1#_PY_NSMALLPOSINTS")}. Anything in the range is handed out rather than made {cite("Include/internal/pycore_long.h:61-68@v3.15.0rc1#_PY_IS_SMALL_INT")}, which is why two separate calculations that land on the same small number give you the same object.

The range is a compile time constant, and it moved in 3.15. You do not have to take anyone's word for where it is now, because you can find the edge from Python with a binary search over the count.

{figure("where-the-cache-stops", "the small integer range on 3.14 against the range on 3.15")}

{lesson.claim("A binary search over the reference count finds the top of the small integer range, and it is 256 on 3.14 and 1024 on 3.15")}
""")


lesson.code(
    """
low, high = 0, 1000000
while low < high:
    mid = (low + high + 1) // 2
    if forever(mid):
        low = mid
    else:
        high = mid - 1

bottom = 0
while forever(bottom - 1):
    bottom -= 1

print(f"  the largest integer that never dies is {low}")
print(f"  and {low + 1} is an ordinary object")
print(f"  going the other way the range stops at {bottom}")
print()

for n in (100, 300, 1024, 1025):
    left, right = int(str(n)), int(str(n))
    print(f"    {n:5}  built twice, same object {left is right!s:5}  never dies {forever(n)}")

print()
size = sum(sys.getsizeof(n) for n in range(bottom, low + 1))
size += sum(sys.getsizeof(chr(n)) for n in range(256))
print(f"  keeping all {low - bottom + 1} integers and 256 strings forever costs {size // 1024} KB")
""",
    differs="This is the cell where the two versions part company. 3.14 stops at 256 and 3.15 "
    "stops at 1024, so the number 300 is a shared object on one and a fresh allocation on the "
    "other, and the memory the tables never give back is about three times larger on 3.15.",
)


lesson.md(f"""
Thirty odd kilobytes, given up once at startup and never returned. That is the whole bill for the two tables, and it buys every arithmetic result under a thousand and every one character string for free.

It is also a good reason not to write code that depends on where the edge is. Any tutorial that says `a is b` works up to 256 was correct when it was written and is now wrong, and there was no warning and no deprecation, because none was needed. Nothing documented ever changed.

## Interned is not the same as immortal

Now the part that gets muddled most often, because two different ideas share a lot of vocabulary.

{term("interning")} is about sharing. One copy of a string is kept in a table and everything that wants that text gets a pointer to that one copy, so comparing them is an address comparison rather than a character by character walk.

Immortality is about freeing. It says the count is never touched, so the object is never destroyed.

A string can be either, both or neither, and the two flags sit in different places in the object.

{figure("two-flags-not-one", "four strings sorted by whether they are interned and whether they never die")}

{lesson.claim("A name used in your code is both interned and immortal, while a plain string constant in the same code is interned and ordinary")}
""")


lesson.code("""
a_name_i_use = 1

for text in ["a_name_i_use", "zzz_only_a_constant", "print", "__name__", "hello there friend"]:
    kind = "never dies" if forever(text) else "ordinary"
    print(f"  {text:22} interned {sys._is_interned(text)!s:5} {kind}")

print()
print("  and the ones that never die are not all parked at the same number:")
for text in ["a_name_i_use", "print", "__name__"]:
    print(f"    {text:14} {count_at(id(text))}")
""")


lesson.md(f"""
Look at the second row. `zzz_only_a_constant` appears in that cell only as a string constant, never as the name of anything, and it comes out interned but ordinary. `a_name_i_use` is a name, and it comes out interned and immortal.

That is exactly what the compiler does. When a code object is built, the names go through one function that interns them and immortalises them {
    cite("Objects/codeobject.c:181-197@v3.15.0rc1#intern_strings")
}, and the constants go through a different one that interns some of them and leaves them ordinary {
    cite("Objects/codeobject.c:199-218@v3.15.0rc1#intern_constants")
}. One call each, two different words in the name, and the whole difference in behaviour follows from that.

The reason for the split is that names are looked up constantly and forever, and a string constant might be used once. {
    term("immortalization")
} is the step that flips an already living object over {
    cite("Objects/unicodeobject.c:14196-14214@v3.15.0rc1#immortalize_interned")
}.

The numbers at the bottom of that cell are not all the same, for the reason O01 gave: `__name__` was allocated inside the binary itself, while `print` and the name from your own cell were immortalised at run time, and the flag bits above the count record which of the two happened.

## What it buys, and what it costs

{
    figure(
        "what-it-buys-and-costs",
        "what immortality gives the interpreter against what it takes away",
    )
}

The thing bought is not really speed on one core. On a single thread an incref is a load, an add and a store to memory that is already in cache, and skipping it saves very little. The thing bought is that no thread ever has to write to the object at all, so a hundred threads can share `None` without any of them touching the same cache line, and without any lock or atomic instruction.

That is why the free threaded build leans on this much harder than the ordinary one does. There, every interned string is made immortal, not just the names {
    cite("Objects/unicodeobject.c:14271-14282@v3.15.0rc1#Py_GIL_DISABLED")
}, because a shared mutable count is exactly the thing that build is trying to get rid of.

{
    lesson.claim(
        "in the free threaded build every interned string is immortal, not just the ones used as names, because a shared count is the thing that build exists to avoid",
        unobservable="it is a compile time branch on Py_GIL_DISABLED, so seeing it needs a free threaded interpreter, which is a separate build rather than a flag you can pass",
    )
}

The cost is that nothing on the list is ever freed, which is why you are not allowed to add to it. There is no function in `sys` for it and no argument anywhere that turns it on. The closest thing that exists is `sys.intern`, and it is worth watching what it actually does, because a lot of people expect it to do more.

{
    lesson.claim(
        "sys.intern puts your string into the shared table without making it immortal, and when the text is already in there it hands back the object that was there instead of yours"
    )
}
""")


lesson.code("""
built = "".join(["something", "_", "new", "_", "here"])
print(f"  freshly built   interned {sys._is_interned(built)!s:5} never dies {forever(built)}")

locked = sys.intern(built)
print(f"  after intern    interned {sys._is_interned(locked)!s:5} never dies {forever(locked)}")
print(f"  and it kept the object you gave it: {locked is built}")
print()
print("  now the same call, on text that is already in the table:")

again = "".join(["a_name", "_i_use"])
shared = sys.intern(again)
print(f"    you got a different object back: {shared is not again}")
print(f"    and that one never dies:         {forever(shared)}")
""")


lesson.md(f"""
`sys.intern` calls the mortal version of the interning function on purpose {cite("Python/sysmodule.c:1004-1019@v3.15.0rc1#sys_intern_impl")}. Your string goes into the shared table and can come back out of it when nothing is using it any more. If it immortalised instead, a program that interned user input would leak, one string at a time, with no way to stop it.

The second half of that cell is the other thing it does. `a_name_i_use` was a name earlier in this notebook, so the interpreter already had an immortal copy of that text, and asking to intern an equal string got that copy back rather than registering yours. Same call, two outcomes, and which one you get depends on what happened to be in the table already.

So there is no way in. That is a design decision rather than an oversight, and it is the right one, because there is also no way back out.

## Try it yourself

Three things.

Find the edge of the single character cache the way you found the integer one, but for `bytes`. Try `bytes([n])` for a range of `n` and see whether the answer matches the string table or not. It is a different table in the source, and it does not have to agree.

Take a function you wrote, look at `f.__code__.co_names` and `f.__code__.co_consts`, and run `forever` over both. Everything in the first list will be immortal and most of the second will not be, which is the compiler split from earlier in this lesson, visible on your own code.

Print `sys.getrefcount(None)` next to `count_at(id(None))`. One of them is one higher than the other, exactly as M04 said, and on a number this size the difference is completely meaningless. That is a good illustration of why quoting `sys.getrefcount` for an immortal object teaches nothing.

## What you now know

Some objects have a reference count that nothing ever changes. The count is parked above a threshold, every incref and decref checks for it first, and both do nothing when they find it.

You can tell which ones from Python, either by reading the header with `ctypes` and comparing against the threshold, or by asking `sys._is_immortal`. The two always agree.

The set is `None`, `True`, `False`, a run of small integers, the 256 one character strings, the empty tuple and empty string, and everything compiled into the binary, which is every built in type and every exception class. Functions, modules and anything you build are not on it.

The set has to be small because nothing on it is ever freed. The two pre built tables together cost about thirty kilobytes that the process never gives back.

The top of the small integer range moved from 256 to 1024 in 3.15, and you can find it yourself with a binary search rather than looking it up.

Interned and immortal are two separate things. Names in your code are both, because the compiler runs them through the immortalising version. String constants in the same code are interned and ordinary. `sys.intern` gives you the first and never the second.

The reason all of this exists is that a reference count is a write, and a write to a shared object is a cache line that every core wants. Immortality is how the interpreter stops paying for that on the objects every thread touches.

## What is next

M06 is about the middle ground. Immortality works for a few hundred objects that are shared by everything, but it cannot work for the millions that are not. The free threaded build handles those with two more tricks, deferred counting and biased counting, which between them let most reference operations stay unsynchronised while still being correct when two threads collide.
""")


raise SystemExit(lesson.save())
