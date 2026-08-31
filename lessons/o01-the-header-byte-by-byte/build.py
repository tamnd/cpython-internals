#!/usr/bin/env python
"""O01. The header, byte by byte.

The first lesson of the object model part, and the twenty seventh overall. T08 said that every
object starts with a reference count and a pointer to its type, which is true and is what
almost every article about CPython says. This lesson reads the actual bytes, and finds that
the first of those two fields is really three.

The count is thirty two bits, not sixty four. Above it sit sixteen bits with a name and no
users, and above those sixteen bits of flags, two of which decide whether an object is
immortal and whether shutting down is allowed to free it.

Everything here is read with ctypes out of the reader's own interpreter, so none of it is
taken on trust. The offsets are computed from the pointer size rather than hardcoded, which is
what lets the same cells run in a browser, where Python is a thirty two bit build and the
header is half the size.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("o01-the-header-byte-by-byte", "o01")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("o01-the-header-byte-by-byte").figure


lesson.md(f"""
# O01. The header, byte by byte

{badge}

Every article about CPython tells you the same thing about the {term("object header")}: two fields, a {term("reference count")} and a pointer to the type. It is a good summary and it is what T08 said.

It is also missing something. On an ordinary sixty four bit build the count is thirty two bits wide, not sixty four, and the other half of that word is two more fields nobody mentions. One of them decides whether the object can ever be freed.

This lesson reads the bytes out of your own interpreter with `ctypes` and checks each field against something Python will tell you another way. Nothing below is taken on trust.

{figure("the-first-sixteen-bytes", "the header as five stacked fields, the first word split into three")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Include/object.h:127-149@v3.15.0rc1#_object`.

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

Everything below was checked against the version this cell prints and against 3.14. The two agree on every number in this lesson, which is unusual and worth saying.
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
## Where an object actually is

`id()` is documented as a number that is unique for the lifetime of an object. In CPython it is the address, and `ctypes` will read memory at an address, so the two together are enough to look at any object's header from Python.

Everything below computes its offsets from the size of a {term("pointer")} rather than writing 8 and 16 into the code. That is not fussiness. In a browser this notebook is running a thirty two bit build and every offset halves.

{lesson.claim("id() is the address an object lives at, and the two machine words there are its reference count and a pointer to its type")}
""")


lesson.code(
    """
import ctypes

WORD = ctypes.sizeof(ctypes.c_void_p)


class Thing:
    pass


it = Thing()

print(f"  a pointer here is {WORD} bytes, so the header is {2 * WORD}")
print(f"  it lives at {id(it)}")
print()
raw = ctypes.c_uint32.from_address(id(it)).value
counted = sys.getrefcount(it) - 1

print(f"  first word, read as a count             {raw}")
print(f"  sys.getrefcount, less its own argument  {counted}")
print(f"  the same number: {raw == counted}")
print()
second = ctypes.c_size_t.from_address(id(it) + WORD).value
print(f"  second word                   {second}")
print(f"  id(Thing) is                  {id(Thing)}")
print(f"  so the second word is the type pointer: {second == id(Thing)}")
print()

also = it
print(f"  after a second name, the count reads  {ctypes.c_uint32.from_address(id(it)).value}")
del also
print(f"  after deleting that name, it reads    {ctypes.c_uint32.from_address(id(it)).value}")
""",
    varies="The address is wherever your interpreter happened to put the object, and a pointer is four bytes in a browser rather than eight.",
)


lesson.md(f"""
## The count is not a whole word

That first read used `c_uint32`, four bytes, and got the right answer. Try `c_uint64` on an ordinary object and you get the same answer, because the top half is zero. Try it on `None` and you do not.

The C is {cite("Include/object.h:127-149@v3.15.0rc1#_object")}, and on a machine where a pointer is more than four bytes the first word is a union of three fields: `ob_refcnt` at thirty two bits, `ob_overflow` at sixteen, and `ob_flags` at sixteen.

{figure("three-fields-in-one-word", "the first word of None split into flags, overflow and count")}

`ob_overflow` is worth a moment. It is declared in that struct and it appears nowhere else in the entire source tree. Sixteen bits with a name, reserved and not yet used.

{lesson.claim("the reference count is thirty two bits wide, and the other half of that word holds two more fields")}
""")


lesson.code(
    """
def header(value):
    \"\"\"The first machine word of an object, split the way the C struct splits it.\"\"\"
    word = ctypes.c_size_t.from_address(id(value)).value
    return word & 0xFFFFFFFF, (word >> 32) & 0xFFFF, (word >> 48) & 0xFFFF


for label, value in [("a Thing", it), ("the float 1.5", 1.5), ("None", None), ("str", str)]:
    count, overflow, flags = header(value)
    print(f"  {label:14}  count {count:>12}   overflow {overflow}   flags {flags}")
""",
    varies="The two ordinary counts depend on what else in your session is holding those objects. And in a browser Python is a thirty two bit build, where the whole word is the count and the other two fields are not in the struct at all, so those columns read zero.",
)


lesson.md(f"""
## A billion either way

`None` came back with a count of 3221225472, which is `3 << 30`. Nothing is holding `None` three billion times. It is an {term("immortal object")}: the count is parked at a value the interpreter never decrements, so `None` is never freed and, more to the point, nothing ever writes to that cache line.

The test is a comparison, {cite("Include/refcount.h:126-136@v3.15.0rc1#_Py_IsImmortal")}, and the interesting part is which two numbers it uses. The line is at `2 ** 31`, and the starting value is `3 << 30`, which is not the top of the field and not the line either.

{figure("how-far-off-you-can-be", "the four numbers that matter in a thirty two bit reference count")}

The comment at {cite("Include/refcount.h:23-50@v3.15.0rc1#_Py_IMMORTAL_INITIAL_REFCNT")} says why. An extension compiled against Python 3.11 has an old `Py_INCREF` in it that knows nothing about immortality, so it increments and decrements `None` like anything else. Parking the count in the middle of the immortal range means that extension can be off by about a billion in either direction and `None` stays immortal.

{lesson.claim("an immortal object's count starts halfway between the immortality line and the top of the field, leaving about a billion of slack in each direction")}
""")


lesson.code(
    """
INITIAL = 3 << 30
MINIMUM = 1 << 31
TOP = 2**32

print(f"  the count parked in None      {sys.getrefcount(None):>12}")
print(f"  3 << 30                       {INITIAL:>12}")
print(f"  the immortality line, 1 << 31 {MINIMUM:>12}")
print(f"  the top of the field, 2 ** 32 {TOP:>12}")
print()
print(f"  slack below the start   {INITIAL - MINIMUM:>13,}")
print(f"  slack above the start   {TOP - INITIAL:>13,}")
""",
    varies="A thirty two bit build draws the line at 1 << 30 and parks a static immortal at 7 << 28, so in a browser the first number and the two amounts of slack are different. The shape of the argument is the same.",
)


lesson.md(f"""
## Two ways to never be freed

`None` also came back with `ob_flags` of 5. Three of those sixteen bits have meanings, {cite("Include/object.h:580-583@v3.15.0rc1#_Py_STATICALLY_ALLOCATED_FLAG")}, and 5 is bit 0 and bit 2: immortal, and statically allocated.

Statically allocated means the object is a `PyObject` written out in the C source and compiled into the binary. {cite("Include/internal/pycore_object.h:83-89@v3.15.0rc1#_PyObject_HEAD_INIT")} is the initialiser that sets both bits at once.

There is another way to become immortal. {cite("Objects/object.c:2773-2791@v3.15.0rc1#_Py_SetImmortalUntracked")} parks the count on an object that was allocated normally, and it sets bit 0 only. That distinction is not cosmetic: when the interpreter shuts down it has to free the promoted ones and must leave the static ones alone, because the static ones are not on the heap.

{figure("two-ways-to-become-immortal", "static immortals with both bits against promoted immortals with one")}

The surprise is in the strings. CPython ships a table of the identifier strings it uses itself, {cite("Include/internal/pycore_global_strings.h:30-38@v3.15.0rc1#_Py_global_strings")}, generated by a script and compiled into the binary. Write `"self"` in your own code and the compiler {term("interning", "interns")} it to that table entry, so your string is a static immortal. Write something CPython has never heard of and you get an ordinary heap string with an ordinary count.

{lesson.claim("a string literal that happens to be one of CPython's own identifiers is immortal, and the same characters CPython does not use are not")}
""")


lesson.code(
    """
for text in ["self", "append", "flags", "zzz nobody uses this one"]:
    count, _, flags = header(text)
    print(f"  {text!r:28}  count {count:>12}   flags {flags}")

print()
print(f"  sys.intern on a fresh string leaves flags at {header(sys.intern('q w e r t y'))[2]}")
print("  so interning and immortalising are two different things")
""",
    varies="The counts depend on what else in your session is holding these strings. Which of them are immortal does not.",
)


lesson.md(f"""
## The third word, when there is one

After the two header words, some types put a length. Those are the variable sized ones, {cite("Include/object.h:174-178@v3.15.0rc1#PyVarObject")}, and the field is `ob_size`. A tuple of three, a list of seven and a `bytes` of four all put their length right there.

{figure("where-a-length-lives", "which types keep a length in the third word and which do not")}

Two things on that picture are worth pointing at. A `str` is not a {term("PyVarObject")} at all, and it still keeps its length in the same place, because `PyASCIIObject` puts a plain `length` field immediately after the header. And an `int` does not, which is why the accessor asserts about it: {cite("Include/object.h:237-244@v3.15.0rc1#_Py_SIZE_impl")} refuses to run on a `PyLong` or a `PyBool`, because since 3.12 an integer packs its sign and its digit count into one field with a different meaning.

{lesson.claim("for a tuple, a list, a bytes and a str, the machine word after the header is the length")}
""")


lesson.code("""
def third_word(value):
    \"\"\"Whatever is in the word after the header, read as a signed count.\"\"\"
    return ctypes.c_ssize_t.from_address(id(value) + 2 * WORD).value


for value in [(1, 2, 3), [0] * 7, b"abcd", bytearray(3), "hello"]:
    kind = type(value).__name__
    print(f"  {kind:10} {value!r:26}  len {len(value)}   third word {third_word(value)}")
""")


lesson.md(f"""
## What sits in front of the header

There is one more thing in the sixteen bytes story, and it is not in the sixteen bytes. It is in front of them.

Types the {term("cycle collector")} tracks get a {term("GC pre header")} allocated immediately before the object, {cite("Include/internal/pycore_interp_structs.h:158-169@v3.15.0rc1#PyGC_Head")}, two words holding the links that thread every tracked object into a list. The object's own address points past it, so nothing that reads the header ever sees it.

You can see it as a gap. `value.__sizeof__()` is what the type says about itself. `sys.getsizeof(value)` calls that and then adds the pre header if the type has one.

{lesson.claim("sys.getsizeof reports two machine words more than an object's own __sizeof__ for the types the cycle collector tracks, and nothing extra for the types it does not")}
""")


lesson.code(
    """
everything = [
    ("object()", object()),
    ("1.5", 1.5),
    ("'hello'", "hello"),
    ("()", ()),
    ("(1, 2, 3)", (1, 2, 3)),
    ("[1, 2, 3]", [1, 2, 3]),
    ("{'a': 1}", {"a": 1}),
]

for label, value in everything:
    own = value.__sizeof__()
    both = sys.getsizeof(value)
    print(f"  {label:10}  __sizeof__ {own:>3}   getsizeof {both:>3}   gap {both - own}")
""",
    varies="Every number here is counted in pointers, so they roughly halve in a browser. The gap is two pointers wherever it is not zero.",
)


lesson.md(f"""
## The same header, wider

Everything above is the ordinary build. The {term("free threaded build")} has a different header, {cite("Include/object.h:156-167@v3.15.0rc1#_object")}, and it is twice the size.

{figure("the-same-header-wider", "the sixteen byte header against the thirty two byte free threaded one")}

The reason is the count. Incrementing a shared counter means writing to a cache line, and if two threads hold the same object then every increment on one core invalidates the other's copy. So the free threaded header splits the count in two: `ob_ref_local`, which only the owning thread touches and therefore needs no atomic instruction, and `ob_ref_shared`, which everybody else uses. `ob_tid` says which thread owns it, and there is a one byte mutex in there as well for the per object lock.

{lesson.claim("the free threaded build gives every object a thirty two byte header, split so the owning thread can increment without an atomic instruction", unobservable="the fields only exist in a build configured with --disable-gil, and this notebook is not running one")}

That is the whole design of free threaded CPython in one struct, and the concurrency lessons come back to it.

## Try it yourself

Three things to poke at.

Walk `gc.get_objects()` and read the flags word on every one of them. Nothing tracked by the cycle collector is immortal, because `_Py_SetImmortal` untracks first. Seeing that come out as a clean result rather than a claim is worth the six lines.

Find the highest reference count in your session. Sort by the count field, look at the top ten, and see whether you can explain each one. The empty tuple and the interpreter's own small integers will be near the top and they will be parked rather than counted, so filter those out first.

Take a class with `__slots__` and one without, and compare `sys.getsizeof` on an instance of each. The gap tells you what an {term("instance dictionary")} costs, and the header is the same either way.

## What just happened

Two fields is a good summary of the header and it is not what is in memory. On an ordinary sixty four bit build the first word is a thirty two bit count, sixteen bits reserved under the name `ob_overflow` and used nowhere, and sixteen bits of flags. The second word is the type pointer.

Immortality is a comparison against `2 ** 31`, and the value it parks at is `3 << 30`, deliberately in the middle so that an old extension incrementing and decrementing without checking can be a billion out either way and the object stays immortal.

Two of the flag bits say how the object became immortal, because shutting down has to free the promoted ones and must not touch the ones compiled into the binary. Every identifier string CPython uses itself is in that second category, which is why `"self"` in your code is immortal and a string CPython has never seen is not.

After the header, variable sized types put their length. Strings are not variable sized types and put it in the same place anyway. Integers used to and no longer do, and the accessor asserts about it.

And in front of the header, for the types the cycle collector tracks, there are two more words that the object's own address points past.

## What is next

The type pointer is the field everything else in this part hangs off. O02 follows it, into the type object: what a `PyTypeObject` holds, which of its hundred or so fields are slots and which are bookkeeping, and how a type written in Python and a type written in C end up being the same kind of thing.
""")


raise SystemExit(lesson.save())
