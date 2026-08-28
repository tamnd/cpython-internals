#!/usr/bin/env python
"""T08. Everything is an object.

The first seven lessons followed one line of Python from text to a running instruction.
This one turns around and looks at the values those instructions were pushing and popping.

The spine is `pyxray/src/pyxray/obj.py`, which is the object header as far as Python can
see it, plus the probes for the small integer cache and the intern table. Every number in
this lesson is measured by a cell rather than quoted from prose, because two of the numbers
a reader would expect to be constants moved in 3.15.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of
them. `just lessons` checks that the committed notebook still matches this file.

The pictures come from `diagrams.py` in this directory. They are looked up on disk rather
than imported, so a diagram that has not been built yet fails here instead of producing a
notebook full of broken images.
"""

from nbbuild import Lesson
from nbdiagram import Diagrams

lesson = Lesson("t08-everything-is-an-object", "t08")
badge = lesson.badge
cite = lesson.cite
figure = Diagrams("t08-everything-is-an-object").figure

lesson.md(f"""
# T08. Everything is an object

{badge}

T07 ended with the interpreter loop pushing and popping things. This lesson is about the things.

{figure("where-we-are", "the eight stages of the pipeline with none of them highlighted")}

Notice that nothing is lit up. The earlier lessons each owned one box in that picture. This one is about what travels along every arrow between them, which is the same kind of value at every stage: a `PyObject`.

You have probably read the sentence "everything in Python is an object" and nodded at it. It is more literal than it sounds. An integer is an object. A string is an object. A function is an object. The type of a function is an object. The module you are in is an object, and so is the frame you are running in. All of them start with the same two fields in memory, and that is what lets one interpreter loop push any of them around without knowing what they are.

By the end you will be able to answer four questions about any value on your screen, you will know why `257 is 257` says True for a reason that has nothing to do with the answer everybody gives, and you will know why `sys.getrefcount` started giving different answers for the same object in 3.14.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Include/object.h:127-150@v3.15.0rc1#_object`.

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

Two of the numbers in this lesson changed in 3.15. Everything here was checked against the version this cell prints, and against 3.14, and it says out loud where the two disagree.
""")


lesson.code("""
import pyxray

pyxray.show()
""")


lesson.md("""
## Predict first

Before anything else, four one line questions. Write your four answers down somewhere, then run the cell.

Does `256 is 256` say True? Does `257 is 257`? Does `"a" * 1 is "a"`? Does `[] is []`?

Guessing badly here is the useful outcome. Three of these four have an answer that is right for a reason almost nobody gets right, and the rest of the lesson is about that gap.
""")


lesson.code("""
one = 256
two = 256
print("256 is 256      ->", one is two)

three = 257
four = 257
print("257 is 257      ->", three is four)

letter = "a"
built = "a" * 1
print("'a' * 1 is 'a'  ->", built is letter)

first = []
second = []
print("[] is []        ->", first is second)
""")


lesson.md("""
True, True, True, False.

If you predicted False for the second one because you read somewhere that the cache stops at 256, you had the right idea and the wrong experiment. If you predicted True because you read that 3.15 raised the limit, you got the right answer for the wrong reason. We will come back to this once there is enough on the table to explain it properly.

## What every object starts with

Here is what sits in front of every value in a running Python.
""")


lesson.md(f"""
{figure("the-header", "the object header as three stacked fields: refcount, type pointer, then the type specific data")}

Two fields, then whatever the specific type needs. The C is {cite("Include/object.h:127-150@v3.15.0rc1#_object")}, and it is shorter than most people expect for the most important struct in the codebase.

That shape is the whole trick. The interpreter loop from T07 pushes and pops `PyObject *`, which is a pointer to those two fields. It never needs to know whether the thing on the end of the pointer is a dictionary or a socket. When it needs behaviour it follows `ob_type` and asks the type. When it is done with a value it decrements `ob_refcnt`.

The free threaded build has a wider header, because a plain increment is not safe when two threads do it at once: {cite("Include/object.h:156-170@v3.15.0rc1#_object")}. Same idea, more fields. Everything below is about the ordinary build.
""")


lesson.md(f"""
## Four questions

There are exactly four things Python will tell you about the header, and each one is easy to over read.

{figure("four-questions", "a table of id, type, getrefcount and getsizeof with what each one does not tell you")}

The last column is the one worth memorising. Every popular confusion about identity, memory and lifetime lives in that column.

`pyxray.obj.header` asks all four at once and prints them as a sentence.
""")


lesson.code("""
from pyxray import obj

for value in [None, 42, "hello", [1, 2, 3], {"a": 1}, obj.header]:
    print(obj.header(value).describe())
""")


lesson.md("""
Read the last line. `obj.header` is a function, and a function has an address, a type, a reference count and a size just like a list does. That is the sentence "everything is an object" turned into something you can print.

Two things in that output are worth pausing on. `None` reports that its reference count is parked rather than reporting a number, which we get to below. And the ints and the strings say they are not tracked by the cycle collector, because an int cannot hold a reference to anything, so it can never be part of a cycle, so the collector does not carry the extra header for it. The collector is opt in per type rather than universal, and T09 is where that becomes the whole story.

## Two questions that look alike

`==` and `is` get taught next to each other and they are not related.
""")


lesson.md(f"""
{figure("is-versus-equals", "== calls the type, is compares two addresses, side by side")}

`==` is a method call. `int.__eq__` compares values, `str.__eq__` compares characters, and your own class can make it mean whatever you like.

`is` compares two addresses. The instruction is {cite("Python/bytecodes.c:3363-3370@v3.15.0rc1#_IS_OP")}, and the whole implementation is one call to `Py_Is`, which is a pointer comparison. No type is consulted and no method is called, which is why you cannot override it and why it is fast.

So `a is b` is asking "are these two names pointing at the same object", and `a == b` is asking "do these two objects agree that they are equal". Different questions with different answers.
""")


lesson.code("""
a = [1, 2, 3]
b = [1, 2, 3]
c = a

print("a == b", a == b, "  same contents")
print("a is b", a is b, "  different objects")
print("a is c", a is c, "  same object")
print()
print("id(a)", hex(id(a)))
print("id(b)", hex(id(b)))
print("id(c)", hex(id(c)))
""")


lesson.md("""
`c = a` did not copy anything. It bound a second name to the same object, which is why the two ids match, and why appending to `a` changes what `c` sees.

The rule for which one to use is short. Use `is` for `None`, `True`, `False` and sentinel objects you made yourself, because for those you genuinely mean "this exact object". Use `==` for everything else.

## The shelf

Now the small integers.
""")


lesson.md(f"""
{figure("the-shelf", "the small integer cache drawn as a row of prebuilt boxes with everything past the end built fresh")}

CPython builds a block of integer objects while it is starting up, before your code runs, and hands out pointers into that block whenever an arithmetic result lands in range. The handing out is one line: {cite("Objects/longobject.c:60-65@v3.15.0rc1#get_small_int")}, which indexes an array rather than allocating anything.

The size of the array is a number in a header file: {cite("Include/internal/pycore_runtime_structs.h:96-98@v3.15.0rc1#_PY_NSMALLPOSINTS")}. That is where the famous 256 came from, and it is why the famous 256 is now wrong. On 3.15 it is 1025.

It exists because small integers are everywhere. Loop counters, list lengths, indexes, flags. Allocating a fresh object for every `i + 1` in a program would be a lot of allocation for a handful of distinct values.

Rather than trusting either number, ask your own interpreter. `pyxray.obj.small_int_range` walks outward from zero until the sharing stops.
""")


lesson.code("""
from pyxray import obj

low, high = obj.small_int_range()
print(f"this interpreter shares integers from {low} to {high}")

for value in [-6, -5, 0, 255, 256, 257, 1024, 1025]:
    shared = "shared" if obj.shares_identity(value) else "built fresh"
    print(f"   {value:>6}   {shared}")
""")


lesson.md("""
Note how the probe builds its integers. It uses `int(str(n))` rather than writing the literal twice, and that is not decoration.

## Two reasons to say True

Here is the thing the famous example gets wrong.
""")


lesson.md(f"""
{figure("two-reasons-to-say-true", "a = 257 answered by the compiler, a = int('257') answered by the cache")}

When you write `a = 257` and `b = 257` in the same cell, both lines compile into one code object, and the compiler stores each distinct constant once. Both `LOAD_CONST` instructions then point at the same object. That happens no matter how big the number is, and it has nothing to do with the cache.

You can see it directly in `co_consts`.
""")


lesson.code("""
source = "a = 257\\nb = 257\\n"
code = compile(source, "<demo>", "exec")

print("constants the compiler kept:", code.co_consts)

scope = {}
exec(code, scope)
print("a is b ->", scope["a"] is scope["b"], "  because there is one constant, not two")
""")


lesson.md("""
One 257 in the tuple, two instructions loading it. The cache never came into it.

Now the same question asked in a way the compiler cannot answer ahead of time.
""")


lesson.code("""
def fresh(text):
    return int(text)


print("int('257') twice  ->", fresh("257") is fresh("257"))
print("int('10') twice   ->", fresh("10") is fresh("10"))
print("int('99999') twice->", fresh("99999") is fresh("99999"))
""")


lesson.md(f"""
That last block is measuring the shelf. On 3.15 the first two say True and the third says False. On 3.14 the first says False, because 257 is past the old limit.

So `257 is 257` says True on both versions for a compiler reason, and it would still say True if the cache were deleted tomorrow. Every tutorial that uses it to demonstrate the cache is demonstrating something else and getting away with it.

The practical lesson is the one the CPython docs have always stated: identity of immutable values is not something the language promises. It is an implementation detail that has already changed once inside this project's own lifetime.

## Strings get the same treatment, with a rule

Strings have their own version of the shelf, called the intern table. It is a hash table hanging off the interpreter state, at {cite("Include/internal/pycore_runtime_structs.h:91-94@v3.15.0rc1#_Py_cached_objects")}, and a string in it is shared by everything that asks for an equal string.

Not every string goes in. The rule is about what the string looks like.
""")


lesson.md(f"""
{figure("what-gets-interned", "six string literals with whether they are interned and why")}

The check is fifteen lines and it is exactly what you would guess if you knew what interning was for: {cite("Objects/codeobject.c:116-137@v3.15.0rc1#should_intern_string")}. ASCII, and every character alphanumeric or an underscore. In other words, strings shaped like identifiers.

That is the point of the whole thing. Attribute lookups, variable names, keyword arguments and dictionary keys are compared constantly while your program runs, and comparing two pointers is faster than comparing two sets of characters. Strings shaped like names get pooled because those are the ones the interpreter compares. A sentence with a space in it is not worth the table entry.

`pyxray.obj.is_interned` asks the question without changing the answer, which takes a little care: interning the string you were handed would put it in the table, and every call after the first would say True regardless of the truth.
""")


lesson.code("""
from pyxray import obj

for text in ["", "a", "append", "_private", "x1", "hello world", "a-b"]:
    print(f"{text!r:<15} interned: {obj.is_interned(text)}")
""")


lesson.md("""
That is the same list as the table above, measured on your interpreter rather than quoted at you.

Two things worth knowing. Strings you build at runtime are not interned, even when they are identifier shaped, because the interning happens when a code object is created and a string built by `join` was never a constant in one. And `sys.intern` lets you put one in yourself, which is worth doing if you are about to compare the same string a few million times and worth ignoring otherwise.
""")


lesson.code("""
import sys

from pyxray import obj

built = "".join(["app", "end"])
print("built at runtime, interned:", obj.is_interned(built))

kept = sys.intern(built)
print("after sys.intern, interned:", obj.is_interned(built))
print("and it handed back the same object:", kept is built)
""")


lesson.md("""
## Counting who is holding it

The reference count is the first field in the header, and it is the number that decides when an object goes away. Every place holding the object adds one. When it hits zero the object is freed on the spot.

Asking for it is where it gets interesting.
""")


lesson.md(f"""
{figure("borrowed-or-not", "LOAD_FAST_BORROW adds nothing, LOAD_GLOBAL adds one, side by side")}

`sys.getrefcount` is documented as reporting one more than you expect, because passing the object to the function creates a reference. Every tutorial written before 3.14 says to subtract one and move on.

In 3.14 that stopped being reliable. `LOAD_FAST_BORROW` arrived, and loading a local variable now hands the interpreter a borrowed reference rather than a counted one, since the frame is already holding the object and cannot stop holding it during the call. Loading a global still takes a real reference, because nothing guarantees the global survives.

So the correction depends on the instruction that pushed the argument, and the same code gives a different number depending on whether the name was local or global.
""")


lesson.code("""
import sys

from pyxray import obj

GLOBAL_LIST = [1, 2, 3]


def compare():
    local_list = [1, 2, 3]
    print("            sys.getrefcount   pyxray")
    print(f"local       {sys.getrefcount(local_list):>13}   {obj.refcount(local_list):>6}")
    print(f"global      {sys.getrefcount(GLOBAL_LIST):>13}   {obj.refcount(GLOBAL_LIST):>6}")


compare()
""")


lesson.md("""
Both lists are held in exactly one place. The raw numbers disagree and the corrected ones do not.

`pyxray.obj.refcount` gets there by disassembling the caller, looking at the instruction immediately before the call, and subtracting one only if that instruction took a real reference. That sounds like a lot of work for one number, and it is, but a lesson that shows a beginner 0 references for a variable they just bound is teaching them to distrust the number instead of understand it.

Watch the count move.
""")


lesson.code("""
from pyxray import obj


def show(label, value):
    print(f"{label:<28} {obj.refcount(value)}")


def watch():
    thing = [1, 2, 3]
    show("just bound", thing)

    holder = [thing, thing]
    show("also in a list twice", thing)

    box = {"key": thing}
    show("also in a dict", thing)

    holder.clear()
    show("list cleared", thing)

    del box
    show("dict gone", thing)


watch()
""")


lesson.md("""
One, three, four, two, one. Nothing clever is happening. Each container that holds the object holds a reference, and dropping the container drops the reference.

The whole thing is wrapped in a function on purpose. At the top level of a notebook, a name lives in the module dictionary, and that dictionary holds a reference too, so every number above would be one higher and the first one would read 2 for a thing you just made. That is a good example of the trap in the third column of the table: the count is real, and working out which places it is counting is on you.

You can also ask the other direction: what is holding this thing right now.
""")


lesson.code("""
from pyxray import obj

target = ["watch me"]
somewhere = {"target": target}
elsewhere = [target]

for holder in obj.referrers(target):
    print(holder)
""")


lesson.md(f"""
Two dicts and a list. The list and one of the dicts are the two containers the cell built. The other dict is the notebook's own namespace, which is holding `target` because `target` is a name at the top level, and that is the extra reference the previous cell went out of its way to avoid.

`gc.get_referrers` is what does the work here, and `pyxray` filters out the frames, because the frame you are asking from is holding the object precisely because you are asking, and that is an artifact rather than an answer.

## The objects that are never freed

Some objects have their reference count parked at a value the interpreter never decrements. `None`, `True`, `False`, the small integers, the interned strings and every type object are immortal. The check is a sign test: {cite("Include/refcount.h:125-136@v3.15.0rc1#_Py_IsImmortal")}.

The reason is threading. Incrementing a shared counter means writing to a cache line, and every core touching `None` a million times a second means those cores fighting over one cache line. Freezing the count for objects that will never be freed anyway makes the write unnecessary. This landed in 3.12 and it is what made the free threaded build plausible.

It also means `sys.getrefcount(None)` returns an enormous number that is not a count of anything, which is why `pyxray` reports nothing for those rather than printing it next to a paragraph about reference counting.
""")


lesson.code("""
import sys

from pyxray import obj


def report(label, value):
    if obj.is_immortal(value):
        print(f"{label:<15} immortal, raw count reads {sys.getrefcount(value)}")
    else:
        print(f"{label:<15} ordinary, {obj.refcount(value)} reference(s)")


report("None", None)
report("True", True)
report("the int 5", 5)
report("str", str)
report("a fresh list", [])
""")


lesson.md(f"""
## How big is it

The last of the four questions. `sys.getsizeof` asks the object itself, by calling its `__sizeof__` method, and then adds the garbage collector's pre header if the type has one: {cite("Python/sysmodule.c:1931-1946@v3.15.0rc1#_PySys_GetSizeOf")}.

Start with things that are holding nothing at all.
""")


lesson.md(f"""
{figure("sizes", "a bar chart of the size of None, 42, a one character string, an empty tuple, list and dict")}

Those are the header plus whatever the type needs in order to exist. An int carries a sign, a length and at least one digit. A one character string carries its length, its hash, a flag saying it is ASCII, and the character. A list carries a length, a pointer to its array of slots, and a capacity.

Now watch a list fill up.
""")


lesson.md(f"""
{figure("sizes-grow", "a bar chart of an empty list against lists of ten, a hundred and a thousand items")}

Eight bytes per slot, which is one pointer on a 64 bit machine. The list is storing pointers rather than values, which is why a thousand integers cost the list eight thousand bytes no matter how big those integers are.

That last part is the trap in the fourth question. `sys.getsizeof` reports the object's own bytes and nothing it points at.
""")


lesson.code("""
import sys

small = [1, 2, 3]
big = [10**100, 10**100, 10**100]

print("list of three small ints:", sys.getsizeof(small), "bytes")
print("list of three huge ints: ", sys.getsizeof(big), "bytes")
print()
print("one huge int on its own: ", sys.getsizeof(big[0]), "bytes")
print()
really = sys.getsizeof(big) + sum(sys.getsizeof(n) for n in big)
print("the second list really costs about", really, "bytes")
""")


lesson.md("""
The two lists are the same size, because they are the same three pointers. Everything that makes the second one expensive is on the other end of those pointers, and `getsizeof` will not follow them for you. There is no function in the standard library that will, because "how big is this really" runs into shared objects and cycles and quickly stops having one answer.

## Try it yourself

**One.** Find the exact integer where sharing stops on your interpreter without using `small_int_range`. Then explain why writing the literal twice in one cell gives you the wrong boundary.

**Two.** `sys.getsizeof([])` is 56 and `sys.getsizeof([1])` is not 64. Find out what it actually is, then append items one at a time and print the size whenever it changes. The pattern you get is the list's growth strategy, and it is in `Objects/listobject.c` if you want to check your reading.

**Three.** Build two equal strings that are not the same object, then intern both and check what `is` says. Then do it again with strings containing a space, and explain the difference.

**Four.** Take a class of your own, give it `__eq__`, and find a case where `a == b` is True and `a is b` is False. Then find out what happens to that class in a `set` and work out why `__hash__` disappeared.

**Five.** Write a function that takes any object and prints its reference count, then call it with the same list from a local variable, from a global, and from inside a list comprehension. Predict the three raw numbers before you run it.

## What just happened

Every value in a running Python starts with the same two fields: a reference count and a pointer to its type. That is what lets one interpreter loop push around integers, sockets and functions without knowing which is which.

There are four questions you can ask about an object and each has a sharp edge. `id` tells you where it is and nothing about equal objects elsewhere. `type` tells you where the behaviour lives and nothing about which instance you have. `getrefcount` tells you how many places hold it, plus however many the asking cost. `getsizeof` tells you the object's own bytes and nothing about what it points at.

`is` compares addresses and `==` calls a method. They are unrelated questions and the answers agreeing is a coincidence you should not build on.

CPython shares small integers and identifier shaped strings, because those are the values programs use constantly. Both are implementation details, both have moved, and the famous `257 is 257` example measures the compiler rather than the cache.

Reference counting is a count of holders, and in 3.14 the cost of asking stopped being a constant. Immortal objects opt out of counting entirely, which is what made the free threaded build possible.

## Where this goes next

You now know what a reference count is and when it hits zero. T09 is about what happens next: where the memory came from, why freeing it does not hand it back to the operating system, and what the cycle collector is for given that reference counting already frees things.
""")


raise SystemExit(lesson.save())
