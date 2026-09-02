#!/usr/bin/env python
"""M06. Two counts, one object.

The sixth lesson of the memory part. M04 gave the counting rule and M05 gave the objects the
rule skips. This one is about the objects it cannot skip, which is nearly all of them, and what
has to change about counting before two threads can run Python at the same time.

Most of this lesson runs on any build, because the problem is arithmetic and the arithmetic is
the same everywhere. The two things that need an interpreter built without the GIL are
recordings, run in the image this project publishes: `m06-the-count-that-is-not-there` for the
deferred marker and `m06-one-count-each-way` for the split count.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording

lesson = Lesson("m06-two-counts-one-object", "m06")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("m06-two-counts-one-object").figure

DEFERRED = "m06-the-count-that-is-not-there"
SPLIT = "m06-one-count-each-way"


lesson.md(f"""
# M06. Two counts, one object

{badge}

Here is the problem in one picture. Two threads each take a reference to the same object at the same moment. Both read the count, both add one, both write it back.

{figure("the-update-that-went-missing", "two threads reading a count of five and both writing six, losing one holder")}

Two holders, and the object thinks it has one. When the first of them lets go, the count hits zero, the object is destroyed, and the second thread is left holding a pointer into freed memory.

This is why CPython had a lock around the whole interpreter for thirty years. Not because dictionaries are hard to share, but because `count = count + 1` is three machine instructions and the middle one is where the day goes wrong.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Include/object.h:156-167@v3.15.0rc1`.

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

Every cell here runs everywhere, including in a browser, on the interpreter you already have. Nothing in this notebook needs a special build.

Two of the things this lesson is about only exist in a build made without the GIL, and you almost certainly are not running one. Those two arrive as recordings: the program, and what it printed when it ran in the image this project publishes. You can read the program, run the parts of it that work on your own build, and pull the same image if you want to see it for yourself.

Some cells read raw memory through `ctypes`. A wrong address there is a crash rather than an exception, so read what a cell does before you change it.

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
## Which build you are on

Start by finding out. There are two ways to ask and they should agree.

{lesson.claim("sys._is_gil_enabled and the Py_GIL_DISABLED build setting are two ways of asking the same question, and on an ordinary interpreter they say the lock is there")}
""")


lesson.code("""
import sysconfig

disabled = sysconfig.get_config_var("Py_GIL_DISABLED")

print(f"  sys._is_gil_enabled()   {sys._is_gil_enabled()}")
print(f"  Py_GIL_DISABLED         {disabled}")
print()

if sys._is_gil_enabled():
    print("  So there is one lock, and only one thread runs Python at a time.")
    print("  Every count in this notebook is a plain number that only one thread can touch.")
else:
    print("  So there is no lock, and the counts below are split in two.")
""")


lesson.md(f"""
`--disable-gil` is a configure flag, not a runtime setting, so this is a property of the binary you are running and there is nothing you can do to it from Python. That build is the {term("free threaded build")}, and everything after the next two sections is about what it had to change.

## What a count looks like today

On the build you are almost certainly running, an object starts with two machine words: the reference count, then a pointer to the type {cite("Include/object.h:139-149@v3.15.0rc1#ob_refcnt")}.

You can read both of them and check your own reading, which is worth doing before trusting anything else read out of memory.

{lesson.claim("The first word of an object is its reference count and the second is a pointer to its type, and an object with no contents of its own is exactly those two words and nothing else")}
""")


lesson.code("""
import ctypes

WORD = ctypes.sizeof(ctypes.c_void_p)

mine = ["one list, one name"]
AT = id(mine)


def word(at):
    return ctypes.c_ssize_t.from_address(at).value


print(f"  a machine word here is {WORD} bytes")
print(f"  the first word says      {word(AT)}")
print(f"  sys.getrefcount says     {sys.getrefcount(mine)}")
print(f"  the second word is the type: {word(AT + WORD) == id(list)}")
print()
print(f"  so the header is {2 * WORD} bytes, and object() is {sys.getsizeof(object())} bytes")
""")


lesson.md(f"""
`sys.getrefcount` reads one higher, because passing the object to it is itself a reference, which is the thing M04 spent a page on.

That count is not something you set. It moves constantly, on its own, as a side effect of ordinary code. Every name that points at the object, every list it goes into, and every function call it is passed to adds one for as long as that lasts.

{lesson.claim("Passing an object to a function adds one to its count for the duration of the call, and each extra level of nesting adds another")}
""")


lesson.code("""
def one_deep(thing):
    return sys.getrefcount(thing)


def two_deep(thing):
    return one_deep(thing)


print(f"  read from here                {sys.getrefcount(mine)}")
print(f"  read one function call down   {one_deep(mine)}")
print(f"  read two function calls down  {two_deep(mine)}")

holder = [mine] * 5
print(f"  and once it is in a list five times  {sys.getrefcount(mine)}")
del holder
print(f"  and after that list goes away        {sys.getrefcount(mine)}")
""")


lesson.md(f"""
That is the volume of the problem. A count going up and down a few times per line of Python, on every object your program touches, forever. Handing that to two threads without a plan is the picture this lesson opened with.

## Playing the race out by hand

You do not need two threads to see what goes wrong, because the failure is arithmetic. Read, add, write, twice over, with the two reads happening before either write.

{lesson.claim("Two reads of the same count followed by two writes leaves the count one lower than the number of holders, which is exactly one holder too few")}
""")


lesson.code("""
count = 5
print(f"  the object starts with {count} holders")

a_read = count
b_read = count
print(f"  thread A read {a_read} and thread B read {b_read}")

count = a_read + 1
print(f"  thread A wrote back {count}")

count = b_read + 1
print(f"  thread B wrote back {count}")

print()
print(f"  two threads took a reference, so the count should be {5 + 2}")
print(f"  it says {count}, so the object is short by {5 + 2 - count}")
print("  one holder too few means the object gets freed while somebody is still using it")
""")


lesson.md(f"""
The usual fix for this is an atomic instruction, which does the read, the add and the write as one indivisible step that no other core can get inside. That works and it is what the free threaded build uses when it has to. The trouble is the price. An atomic add on a value that several cores are reading forces the cache line holding it to bounce between them, and on a hot object that cost is not small.

So the interpreter does not reach for it first. It has three cheaper answers, and the atomic is what is left over.

{figure("three-answers", "four prices for taking a reference, from free to one atomic instruction")}

The first row is M05, and you have already seen it. The other two are the rest of this lesson.

## Stop counting it at all

The second answer is to pick objects that are read constantly and almost never dropped, and mark them so that nothing bothers counting them. The mark is a number: the object's shared count starts at `PY_SSIZE_T_MAX / 8` {cite("Include/internal/pycore_object.h:24-28@v3.15.0rc1#_Py_REF_DEFERRED")}, which is a bit over a quintillion.

That is not a count of anything. It is a floor, set so far above zero that no realistic number of decrefs will ever reach it, and if the count can never reach zero then nothing will ever free the object by counting. The cycle collector still can, and it becomes the only thing that ever does. This is {term("deferred reference counting")}.

You can work the number out on your own machine, and then check it against the recording below.

{lesson.claim("The deferred marker is PY_SSIZE_T_MAX divided by 8, and on a build with the GIL nothing is parked there because the whole mechanism is compiled out")}
""")


lesson.code(
    """
DEFERRED = sys.maxsize // 8

print(f"  sys.maxsize, which is PY_SSIZE_T_MAX  {sys.maxsize}")
print(f"  divided by eight                      {DEFERRED}")
print(f"  and shifted up by two                 {DEFERRED << 2}")
print()
print("  nothing on this build is anywhere near that:")
for label, thing in [
    ("a function", one_deep),
    ("the sys module", sys),
    ("a list", mine),
]:
    count = sys.getrefcount(thing)
    print(f"    {label:16} {count:>10}  past the marker: {count > DEFERRED}")
""",
    varies="These numbers are much smaller on a 32 bit build, including the one running in "
    "your browser, because PY_SSIZE_T_MAX is a machine word and there the word is four bytes "
    "rather than eight. The recording below came from a 64 bit build, so its marker is the "
    "big one.",
)


lesson.md(f"""
Now the same question, asked on an interpreter built without the GIL. Everything below came out of the image this project publishes, and the program is the whole program.

{lesson.claim("on a free threaded build sys.getrefcount returns the deferred marker plus a handful for a top level function, a class, a module and a built in function, and an ordinary number for a list, an instance and a function defined inside another function", unobservable="deferred reference counting only exists in a build configured with --disable-gil, so what follows is a recording rather than a cell you run")}

{recording(DEFERRED)}
""")


lesson.md(f"""
Two things in there are worth stopping on.

The first is that the list of objects is not arbitrary. Functions, methods, classes and modules are exactly the things every thread reads on every call and nobody ever drops. A list or an instance is the opposite, and it stays counted.

The second is the nested function. A function written at the top level of a module gets the treatment and one written inside another function does not, and the comment in the source says why: a nested function has probably closed over something, and somebody is relying on that something being freed when the function is rather than whenever the collector next runs {cite("Objects/funcobject.c:224-236@v3.15.0rc1#_PyObject_SetDeferredRefcount")}. Deferred counting trades prompt destruction for speed, and that trade is not always worth making.

Modules get it in the same one line way {cite("Objects/moduleobject.c:227-234@v3.15.0rc1#track_module")}. And there is a public function for turning it on yourself from C {cite("Objects/object.c:2814-2848@v3.15.0rc1#PyUnstable_Object_EnableDeferredRefcount")}, which refuses on anything the collector does not track, for the obvious reason: if nothing counts the object and the collector never looks at it, nothing will ever free it.

## Count it locally, or count it shared

Which leaves everything else. Millions of ordinary objects, all of them counted, none of them safe to count carelessly.

The trick is a bet about how programs behave: most objects are made, used and dropped by one thread and no other thread ever sees them. So give the object a memory of which thread made it, and let that thread count in a plain field with no atomic, while everybody else pays for the atomic on a second field. This is {term("biased reference counting")}.

{figure("where-the-reference-goes", "the owning thread adding to the local count against another thread adding to the shared one")}

That needs a bigger header, and the free threaded build has one {cite("Include/object.h:156-167@v3.15.0rc1#ob_ref_shared")}.

{figure("two-headers", "the two word object header next to the seven field free threaded one")}

Reading the count means adding the two halves together, with one shortcut in front for the immortal case {cite("Include/refcount.h:105-117@v3.15.0rc1#_Py_REFCNT")}. And the shared half is not purely a number, because the bottom two bits of it are flags {cite("Include/refcount.h:78-93@v3.15.0rc1#_Py_REF_SHARED")}.

{figure("inside-the-shared-count", "the shared count field with its top bits holding a number and its bottom two holding flags")}

Which means you can decode any shared field you are shown with two operations, and the next cell is a decoder you can point at the numbers in the recording that follows it.

{lesson.claim("Shifting a shared count field right by two gives the reference count and masking the bottom two bits gives the flags, which is enough to read any of these fields by hand")}
""")


lesson.code("""
SHIFT, FLAGS = 2, 0b11
MEANING = {
    0b00: "nothing has happened yet",
    0b01: "something took a weak reference",
    0b10: "a decref is waiting for the owner",
    0b11: "the two counts have been merged",
}

print("  the raw field        the count  what the bottom two bits say")
for raw in [0, 1, 4, 13, 17, sys.maxsize // 8 << 2]:
    print(f"  {raw:>20}  {raw >> SHIFT:>9}  {MEANING[raw & FLAGS]}")

print()
print("  the last row is the deferred marker again, which is why it fits here:")
print("  deferred counting works by writing an enormous number into this same field")
""")


lesson.md(f"""
{lesson.claim("on a free threaded build a reference taken by the thread that made the object goes into the local count, one taken by any other thread goes into the shared count four at a time, and the reference count you get back is the two added together", unobservable="the split only exists in a build configured with --disable-gil, so on any other interpreter these offsets point at other fields entirely and reading them proves nothing")}

{recording(SPLIT)}
""")


lesson.md(f"""
Follow the table in the middle of that. One name, local 1. Three more names from the same thread, local 4, and the shared count has not moved. Then three references from a worker thread and the shared count is 3, while local is still 4, so the total is 7. The worker finishes, its three references go, and the shared count is back to 0.

The `flags` column changed from `init` to `maybe weakref` when the worker touched it and stayed that way afterwards. That bit is a hint for later rather than a lie: it means something might have taken a weak reference to this object, so whatever cleans it up has to check. Turning the bit off would mean proving nothing had, which costs more than checking does.

Three more things in that recording are worth naming.

`None` has an `ob_tid` of zero, which is the value for an object no thread owns {cite("Include/object.h:150-154@v3.15.0rc1#_Py_UNOWNED_TID")}. That covers immortal objects and objects whose two counts have been merged, and it is the state you end up in when nobody can be allowed the cheap path.

Immortality is marked differently here. On the build you are running it is a count above two to the power of 31, which M05 showed you. On the free threaded build there is no room for that trick in a 32 bit local count, so the marker is `UINT32_MAX` instead {cite("Include/refcount.h:71-75@v3.15.0rc1#_Py_IMMORTAL_REFCNT_LOCAL")}, and `_Py_IsImmortal` tests a different thing depending on which build it is compiled into {cite("Include/refcount.h:126-136@v3.15.0rc1#_Py_IsImmortal")}.

And the last two lines of that section are M05's ending, turned inside out. There, `sys.intern` gave you a shared copy and never an immortal one. Here, interning a string makes it immortal every time, because the build cannot afford a shared mutable count on something every thread reads {cite("Objects/unicodeobject.c:14271-14282@v3.15.0rc1#Py_GIL_DISABLED")}.

## What the wider header costs

Seven fields instead of two has to be paid for somewhere, and it is worth being precise about where, because the obvious guess is wrong.

{figure("what-the-header-costs", "object sizes on a build with the GIL against a build without it")}

The header goes from 16 bytes to 32. But a list, a dict and a tuple are all exactly the same size on both builds, and that is not an accident. On an ordinary build the collector keeps its own {term("GC pre header")} of two more words in front of every object whose type it can collect, and the free threaded build does not: those bits live in `ob_gc_bits` inside the object header instead. So `_PyType_PreHeaderSize` adds the collector's header on one build and not the other {cite("Include/internal/pycore_object.h:852-861@v3.15.0rc1#_PyType_PreHeaderSize")}, and the sixteen bytes the header gained are the sixteen bytes the pre header stopped costing.

The thing that decides which side you land on is a flag on the type, `Py_TPFLAGS_HAVE_GC`. It is not whether a particular object is being tracked right now. A tuple of numbers gets untracked as soon as the collector notices it cannot be part of a cycle, but its type still carries the flag, so it still had the pre header and it still gets the refund.

Which means the bill lands entirely on types the collector never deals with. Integers, strings, bytes, plain `object()` instances. Those get 16 bytes bigger and nothing gives it back.

{lesson.claim("Whether an object pays for the wider header depends on a flag on its type rather than on whether the collector is tracking that object right now")}
""")


lesson.code(
    """
import gc

print("  sizes on this build, for comparing against the table in the recording:")
for label, thing in [
    ("object()", object()),
    ("an empty tuple", ()),
    ("a one character string", "x"),
    ("an empty list", []),
    ("an empty dict", {}),
]:
    print(f"    {label:24} {sys.getsizeof(thing):>3} bytes")

print()
print("  and the flag that decides who pays, next to what is tracked right now:")

HAVE_GC = 1 << 14

for label, thing in [
    ("object()", object()),
    ("a one character string", "x"),
    ("a tuple of numbers", (1, 2)),
    ("a list", []),
    ("a dict", {}),
]:
    collectable = bool(type(thing).__flags__ & HAVE_GC)
    print(f"    {label:24} collectable: {collectable!s:5}  tracked now: {gc.is_tracked(thing)}")
""",
    varies="Every size here shrinks on a 32 bit build, including the one in your browser, "
    "because a pointer is four bytes there rather than eight. The collectable column is the "
    "one that decides who pays, and it never changes. The tracked column can, because a tuple "
    "of numbers only gets untracked once the collector has looked at it.",
)


lesson.md("""
## Try it yourself

Three things.

Take the decoder cell and run it over the raw `ob_ref_shared` values in the second recording. The one for the deferred function is `4611686018427387900`, and shifting it right by two should give you back the marker you computed earlier. Getting the same number two different ways is a good way to be sure you have understood the encoding rather than memorised it.

Work out what the split costs when the bet is wrong. If a thread makes a million objects and hands every one of them to a different thread, every single reference after the first goes through the shared field and pays an atomic, and the local count sits there unused. Write down what you would expect that to look like in the header, then read the second recording's table again and see whether your version matches.

If you want to run the recordings yourself rather than read them, `docker run` the image named at the top of each one and pipe the program in. The digest is in the file, so you will be running the same interpreter these numbers came from, not one that happens to have the same version number.

## What you now know

Two threads incrementing the same count can lose an update, and the object gets freed while somebody is still holding it. That is the reason the GIL existed, and removing the GIL means answering it.

An atomic instruction answers it, and costs enough that the interpreter treats it as the last resort rather than the first.

There are three cheaper answers, in order of how much they save. Immortal objects are never counted at all. Deferred objects have an enormous number written into their shared count, so nothing frees them by counting and only the cycle collector ever can. Everything else gets a count split in two.

Deferred counting goes to top level functions, methods, classes, modules and built in functions. It does not go to nested functions, because a closure holds things somebody wants freed on time.

The split count works because most objects never leave the thread that made them. The object remembers its owner in `ob_tid`, the owner counts in a plain 32 bit field, everybody else counts in a shared field with an atomic, and the reference count is the two added together.

The shared field stores its count shifted up by two, because the bottom two bits are flags: whether something might have taken a weak reference, whether a decref is queued for the owner, and whether the two counts have been merged.

The object header goes from 16 bytes to 32, and a list, a dict and a tuple pay none of it, because the collector's own pre header went away at the same time. The bill lands on types the collector never touches, which is integers, strings, bytes and plain instances of `object`.

## What is next

M07 is the cycle collector, and it follows straight on from here. Two of the three answers in this lesson end with the same sentence: the collector is the only thing that can free this object. That is a lot of responsibility to hand to something you have not looked at yet, so the next lesson looks at it, on the ordinary build first, where it is a generational mark and sweep you can watch run.
""")


raise SystemExit(lesson.save())
