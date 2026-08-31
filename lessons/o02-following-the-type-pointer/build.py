#!/usr/bin/env python
"""O02. Following the type pointer.

The second lesson of the object model part. O01 read the sixteen bytes at the front of every
object and stopped at the second word, which is a pointer to the type. This lesson follows it.

What is on the other end is the largest struct in the interpreter and almost all of it is
answers to questions about instances: how big one is, whether it can be subclassed, where it
keeps its attributes, what to call when somebody adds two of them. The two most surprising
answers are kept in front of the instance rather than inside it, at negative offsets, which is
why one of the fields here holds a negative number that is not an offset at all.

The lesson also takes the mystery out of the `class` statement, which compiles to a function
call and nothing else.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("o02-following-the-type-pointer", "o02")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("o02-following-the-type-pointer").figure


lesson.md(f"""
# O02. Following the type pointer

{badge}

O01 read the front of an object and found four fields in two words. Three of them turned out to be about the object itself. The fourth, the second word, points somewhere else.

This lesson goes there. On the other end is a {term("type object")}, and it is the biggest struct in CPython by a wide margin. Almost everything in it is an answer to a question the interpreter will ask about instances, and you can read most of those answers from Python without any C at all.

{figure("follow-the-second-word", "the type pointer followed from an int to int to type, where it loops")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Include/cpython/object.h:147-151@v3.15.0rc1#_typeobject`.

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

Everything below was checked against the version this cell prints and against 3.14. Two things moved between the two, one number and one opcode name, and the cells that print them say so.
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
## A type is an object too

The second word of an object is a `PyTypeObject *`, {cite("Include/cpython/object.h:147-151@v3.15.0rc1#_typeobject")}. That struct starts with `PyObject_VAR_HEAD`, which means a type object has the same header everything else has, so it has a count and a type pointer of its own.

Follow those and you get a short walk. The int 3 points at `int`. `int` points at `type`. And `type` points at `type`, which is where it stops.

That last one is not a trick. `type` is its own type because the chain has to end somewhere, and ending it in a loop is cheaper than inventing a special case that every lookup would have to check for.

{lesson.claim("the second word of an object is the address of its type object, and following it from any object reaches type in at most two steps, where it loops")}
""")


lesson.code(
    """
import ctypes

WORD = ctypes.sizeof(ctypes.c_void_p)


def type_pointer(value):
    \"\"\"The second machine word of an object, which is the address of its type.\"\"\"
    return ctypes.c_size_t.from_address(id(value) + WORD).value


names = {id(int): "int", id(str): "str", id(type): "type", id(object): "object"}

for label, value in [("the int 3", 3), ("the str 'hi'", "hi"), ("int", int), ("type", type)]:
    print(f"  {label:14}  second word points at  {names[type_pointer(value)]}")

print()
print(f"  type(type) is type:  {type(type) is type}")
print("  so following the pointer never reaches anything new after that")
"""
)


lesson.md(f"""
## The numbers a type keeps about its instances

Two fields decide how much memory one instance takes: `tp_basicsize` and `tp_itemsize`, {cite("Include/cpython/object.h:147-151@v3.15.0rc1#_typeobject")}. Python exposes both as `__basicsize__` and `__itemsize__`.

`tp_basicsize` is the fixed part, the same for every instance. `tp_itemsize` is charged per element, and it is zero for every type whose instances are all the same size.

{figure("two-numbers-per-instance", "a table of basicsize and itemsize for the common builtin types")}

The bottom row explains itself once you know where it comes from. `PyType_Type` sets its own `tp_basicsize` to `sizeof(PyHeapTypeObject)` and its `tp_itemsize` to `sizeof(PyMemberDef)`, {cite("Objects/typeobject.c:7290-7295@v3.15.0rc1#PyType_Type")}, because an instance of `type` is a class, and a class allocated at runtime is a heap type with a member table after it.

The interesting row is `list`. A list has a length and its length varies, so you would expect an itemsize, and it is zero. That is because a list does not store its items inside itself. It stores a pointer to a separate array, which is what lets `append` grow a list without moving the list object, and what lets everything holding a reference to that list keep working.

{lesson.claim("basicsize is the fixed part of an instance and itemsize is charged per element, and list has an itemsize of zero because its items live in a separate allocation")}
""")


lesson.code(
    """
for t in [object, float, int, tuple, bytes, str, list, dict, type]:
    print(f"  {t.__name__:8}  basicsize {t.__basicsize__:>4}   itemsize {t.__itemsize__:>3}")
""",
    differs="type.__basicsize__ is 936 on 3.14 and 944 on 3.15, because the type struct gained one more machine word. Every other number here is the same on both. In a browser almost all of them roughly halve, because they are counted in pointers and a pointer is four bytes there.",
)


lesson.md(f"""
Put the two together and you can predict the size of an instance yourself. Take `tp_basicsize`, add `tp_itemsize` times the length, and compare against what `__sizeof__` reports. The length is the third word from O01, `ob_size`, {cite("Include/object.h:174-178@v3.15.0rc1#PyVarObject")}.

It works for a tuple, for bytes, and trivially for the types with no third word at all. It does not work for a list, and the cell shows exactly how far off it is.

{lesson.claim("basicsize plus itemsize times ob_size matches __sizeof__ for the variable sized types, and misses for list, whose reported size includes an array the type object knows nothing about")}
""")


lesson.code(
    """
def third_word(value):
    \"\"\"The word after the header, which is ob_size for the types that have one.\"\"\"
    return ctypes.c_ssize_t.from_address(id(value) + 2 * WORD).value


samples = [("()", ()), ("(1, 2, 3)", (1, 2, 3)), ("b'abcd'", b"abcd"), ("1.5", 1.5)]
samples.append(("[1, 2, 3]", [1, 2, 3]))

for label, value in samples:
    t = type(value)
    count = third_word(value) if t.__itemsize__ else 0
    predicted = t.__basicsize__ + t.__itemsize__ * count
    actual = value.__sizeof__()
    mark = "" if predicted == actual else "   <- and the items are elsewhere"
    print(
        f"  {label:11} {t.__basicsize__:>3} + {t.__itemsize__} * {count:<2} = {predicted:>3}"
        f"   __sizeof__ {actual:>3}{mark}"
    )
""",
    varies="Every number roughly halves in a browser, and the last row is still the one that does not add up.",
)


lesson.md(f"""
## Two kinds of type

There are two ways a type object comes into existence and the difference shows up everywhere.

A {term("static type")} is a `PyTypeObject` written out as a C literal in the source and compiled into the binary. `int`, `str`, `list` and `type` itself are all like this, {cite("Objects/typeobject.c:7290-7295@v3.15.0rc1#PyType_Type")}. There is exactly one of each, it is immortal in the O01 sense, and it lives in the binary's read only data rather than on the heap.

A {term("heap type")} is built while the program runs, and what gets allocated is not a `PyTypeObject` but a `PyHeapTypeObject`, {cite("Include/cpython/object.h:272-296@v3.15.0rc1#PyHeapTypeObject")}, which is a type object with all the operator tables welded on after it. Every class statement makes one.

{figure("static-and-heap", "static types against heap types, four differences each")}

One bit says which you have got: `Py_TPFLAGS_HEAPTYPE`, {cite("Include/object.h:501-506@v3.15.0rc1#Py_TPFLAGS_HEAPTYPE")}. Python hands you the whole flags word as `__flags__`, so you can decode it.

The practical difference most people meet is that you cannot add an attribute to a builtin type. That is not a rule about builtins, it is `Py_TPFLAGS_IMMUTABLETYPE` being set on them, and the error message names the flag's intent directly.

{lesson.claim("the flags word distinguishes static types from heap types, and the same word is what makes int reject attribute assignment while a class you wrote accepts it")}
""")


lesson.code(
    """
FLAGS = [
    (1 << 1, "STATIC_BUILTIN"),
    (1 << 2, "INLINE_VALUES"),
    (1 << 3, "MANAGED_WEAKREF"),
    (1 << 4, "MANAGED_DICT"),
    (1 << 8, "IMMUTABLETYPE"),
    (1 << 9, "HEAPTYPE"),
    (1 << 10, "BASETYPE"),
    (1 << 12, "READY"),
    (1 << 14, "HAVE_GC"),
    (1 << 24, "LONG_SUBCLASS"),
    (1 << 31, "TYPE_SUBCLASS"),
]


class Plain:
    pass


for t in [int, bool, type, Plain]:
    on = " ".join(name for bit, name in FLAGS if t.__flags__ & bit)
    print(f"  {t.__name__:6} 0x{t.__flags__:08x}  {on}")

print()
try:
    int.nope = 1
except TypeError as error:
    print(f"  int.nope = 1     TypeError: {error}")

Plain.nope = 1
print(f"  Plain.nope = 1   fine, and it reads back as {Plain.nope}")
"""
)


lesson.md(f"""
## Where an instance keeps its attributes

Two more fields, and these are the ones worth slowing down for: `tp_weaklistoffset`, {cite("Include/cpython/object.h:195-198@v3.15.0rc1#tp_weaklistoffset")}, and `tp_dictoffset`, {cite("Include/cpython/object.h:210-213@v3.15.0rc1#tp_dictoffset")}.

Both are byte offsets from the start of the object to a pointer. Zero means there is none, so instances of that type cannot have a `__dict__`, or cannot be weak referenced, and that is why you cannot set an arbitrary attribute on an int.

For a class you write yourself, both come out negative, and they are negative for two completely different reasons.

{figure("reading-an-offset", "the four meanings of tp_dictoffset, ending in the sentinel")}

A negative offset has meant "count back from the end" since long before this, for variable sized objects where the fixed part is followed by items. But `-1` is not that. It is a sentinel, and the code that resolves ordinary offsets asserts it never sees one, {cite("Objects/object.c:1573-1595@v3.15.0rc1#_PyObject_ComputedDictPointer")}. It means the interpreter is managing the dict itself and the offset field is not to be read as an offset at all.

Where the pointer actually goes is in front of the object, {cite("Include/internal/pycore_object.h:922-928@v3.15.0rc1#MANAGED_DICT_OFFSET")}. The weakref list is four pointers back, the dict is three pointers back, and the two words in between are the GC pre header from O01.

{figure("where-the-attributes-live", "one instance drawn with two negative offsets, the GC pre header, and the inline values after")}

So the space is reserved by the allocator ahead of the address you get from `id`, {cite("Include/internal/pycore_object.h:852-861@v3.15.0rc1#_PyType_PreHeaderSize")}, and `sys.getsizeof` charges you for it. That makes the gap between `__sizeof__` and `getsizeof` readable: thirty two bytes for a class that can have attributes and weak references, sixteen for one with `__slots__` that only needs the pre header for the cycle collector.

{lesson.claim("a class statement sets tp_dictoffset to -1 and tp_weaklistoffset to minus four pointers, and the space those refer to sits in front of the object, which is why getsizeof reports more than __sizeof__")}
""")


lesson.code(
    """
class Slotted:
    __slots__ = ("a", "b")


for t in [object, int, Plain, Slotted]:
    print(
        f"  {t.__name__:8}  basicsize {t.__basicsize__:>3}"
        f"   dictoffset {t.__dictoffset__:>3}   weakrefoffset {t.__weakrefoffset__:>4}"
    )

print()
for label, value in [("Plain()", Plain()), ("Slotted()", Slotted())]:
    own = value.__sizeof__()
    both = sys.getsizeof(value)
    print(
        f"  {label:11}  __sizeof__ {own:>3}   getsizeof {both:>3}   reserved in front {both - own}"
    )
""",
    varies="Everything here is counted in pointers, so the numbers halve in a browser and weakrefoffset reads minus sixteen instead of minus thirty two.",
)


lesson.md(f"""
One thing `getsizeof` does not tell you. A class whose instances get a managed dict also gets `Py_TPFLAGS_INLINE_VALUES`, and the allocator reserves room for those values after the object, {cite("Objects/typeobject.c:2512-2531@v3.15.0rc1#_PyType_AllocNoTrack")}. That array is neither in `tp_basicsize` nor in the pre header, so nothing you can call from Python counts it. An instance of a plain class costs more than the number above.

{lesson.claim("an instance of a class with a managed dict is allocated with room for its attribute values after the object, and that room is in neither of the numbers getsizeof adds together", unobservable="the inline values array is sized from a table on the type and no Python level call reports it")}

That array is the whole subject of O08, so it can wait.

## The class statement is a function call

The last thing worth clearing up here is where a type object comes from when you write a class.

There is no class opcode. The compiler turns the body of a class into an ordinary function, then emits a call to a builtin named `__build_class__` with that function and the class name, {cite("Python/bltinmodule.c:102-108@v3.15.0rc1#builtin___build_class__")}. That builtin runs the function, catches the names it defined in a namespace dict, and calls the {term("metaclass")}, which is `type` unless you said otherwise.

{figure("what-a-class-statement-does", "the five steps a class statement compiles to")}

You can check both halves. Disassemble a class statement and the opcodes are there. Then build the same type by calling `type` with three arguments and compare the results.

{lesson.claim("a class statement compiles to a call to __build_class__, and calling type with a name, bases and a namespace produces a type with the same flags, size and mro")}
""")


lesson.code(
    """
import dis

source = "class Greeter:\\n    def hi(self):\\n        return 'hi'\\n"

for instruction in dis.get_instructions(compile(source, "<demo>", "exec")):
    argument = instruction.argrepr
    if argument.startswith("<code object"):
        argument = "the class body, compiled"
    print(f"  {instruction.opname:22} {argument}")
""",
    differs="The last instruction is LOAD_CONST on 3.14 and LOAD_COMMON_CONSTANT on 3.15, which is a change to how a module returns None and has nothing to do with classes. Everything above it is the same on both.",
)


lesson.code(
    """
def hi(self):
    return "hi"


Made = type("Greeter", (), {"hi": hi})


class Greeter:
    def hi(self):
        return "hi"


print(f"  same flags:       {Made.__flags__ == Greeter.__flags__}")
print(f"  same basicsize:   {Made.__basicsize__ == Greeter.__basicsize__}")
print(f"  same mro:         {Made.__mro__[1:] == Greeter.__mro__[1:]}")
print(f"  both work:        {Made().hi()!r} {Greeter().hi()!r}")

print()
extra = sorted(set(Greeter.__dict__) - set(Made.__dict__))
print(f"  only the class statement's version has  {extra}")
print("  which is where a traceback finds the line the class was written on")
"""
)


lesson.md("""
## Try it yourself

Three things to poke at.

Find every static type your interpreter has loaded. Walk `object.__subclasses__()` recursively and keep the ones without `Py_TPFLAGS_HEAPTYPE` set. There are more than you would guess, and the ones defined in extension modules are the interesting half.

Compare `__basicsize__` for a class with no slots, one slot, and five slots. The steps are one pointer each, and the class with no slots is the smallest of the three even though it can hold the most, because its attributes are not in the object.

Subclass `tuple` and add `__slots__ = ()`, then check `__itemsize__` and `__basicsize__` on your subclass. Both are inherited, which is what makes a tuple subclass still store its items inline, and it is also why adding a non empty `__slots__` to a tuple subclass is an error.

## What just happened

The second word of an object points at its type, a type is an object with the same header, and `type` is its own type so the chain terminates in a loop rather than a special case.

A type object is mostly answers about instances. `tp_basicsize` and `tp_itemsize` say how big one is, and multiplying them out matches `__sizeof__` for the variable sized types. It misses for `list`, which keeps its items in a separate array so that appending does not move the object.

The flags word says whether a type was compiled into the binary or built while running, and whether you are allowed to assign to it. That one bit is the whole reason `int.nope = 1` fails and `Plain.nope = 1` does not.

`tp_dictoffset` and `tp_weaklistoffset` are byte offsets, except when they are not. A class statement leaves `-1` in the first one, which is a sentinel meaning the interpreter manages the dict, and the pointer it manages lives three pointers in front of the object, next to the weakref list and the GC pre header. That whole region is why `sys.getsizeof` reports thirty two bytes more than the object claims for itself.

And a class statement is a function call. The body compiles to a function, `__build_class__` runs it, and the metaclass turns the resulting namespace into a type.

## What is next

O03 opens the operator tables. A type object has more than seventy function pointer fields, `tp_repr` and `tp_hash` and `tp_call` and the rest, and Python code never sets any of them directly. It defines `__repr__` and something fills in `tp_repr`. That something is a generated table, it runs in both directions, and it is the reason `__eq__` and `__hash__` are linked in a way that catches people out.
""")


raise SystemExit(lesson.save())
