#!/usr/bin/env python
"""F10. Inside a code object.

The tenth lesson of the front end part, and the twenty fourth overall. F09 assembled the bytes.
This one opens the box they came out in.

The angle is that a code object is a plain record with nothing surprising in it, except for one
thing that surprises everybody: four of its attributes are not stored. `co_varnames`,
`co_cellvars` and `co_freevars` are computed on demand from one array of names and one string
of tag bytes, and because a tag byte can have two bits set, a name can appear in two of them.
That is why the tuples add up to more entries than there are slots.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("f10-inside-a-code-object", "f10")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("f10-inside-a-code-object").figure


lesson.md(f"""
# F10. Inside a code object

{badge}

Nine lessons to get here, and what comes out the end is one object you can hold in a variable.

A {term("code object")} is the compiled form of exactly one thing: one module, one function body, one class body. It is a plain record. There is no cleverness in it and nothing lazy about it, and the single most useful thing to know is what is missing: it holds no values. Not the arguments, not the locals, not the result. A code object for a function that has been called a million times is the same object it was before the first call.

Most of it reads exactly how you would expect. One part does not, and it is the part everybody trips over, so most of this lesson is about that.

{figure("no-values-in-here", "the fields of a code object, none of which is a value the program computed")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Include/cpython/code.h:82-95@v3.15.0rc1`.

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

Everything below was checked against the version this cell prints and against 3.14. Where the two disagree, the lesson says so.
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
## Boxes inside boxes

Compile a file and you get one code object back. Every `def` and every `class` in that file produced a code object too, and each of those went into the enclosing one's `co_consts`, in with the numbers and the strings.

So a module is a tree, and you can walk it with four lines of Python. There is no separate list of functions to consult and no registry anywhere. A nested definition is a constant.

{lesson.claim("the code objects of a file form a tree, reachable through co_consts alone")}
""")


lesson.code("""
import types

SOURCE = \"\"\"\\\"\\\"\\\"A tiny module.\\\"\\\"\\\"

import math


class Shape:
    def area(self):
        return math.pi


def counter(n):
    while n:
        yield n
        n = n - 1
\"\"\"

module = compile(SOURCE, "tiny.py", "exec")


def walk(code, depth=0):
    \"\"\"Every code object reachable from this one, through the constants.\"\"\"
    print(f"  {'    ' * depth}{code.co_name:10} qualname {code.co_qualname}")
    for one in code.co_consts:
        if isinstance(one, types.CodeType):
            walk(one, depth + 1)


walk(module)
""")


lesson.md(f"""
Four code objects out of one file. `co_name` is the short one and `co_qualname` is the path to it, which is how a traceback can say `Shape.area` when two classes both have a method called `area`.

{figure("boxes-inside-boxes", "the code objects of one small file, nested through the constants")}

Notice what is not in the tree. There is no code object for the class body's `def` line, because a `def` statement is just instructions in the body that made it. And in 3.12 and later a list comprehension is compiled into the function around it rather than into its own object, so writing one adds nothing here.

## Names, in four tuples

Now the confusing part.

A code object has `co_varnames` for locals, `co_cellvars` for locals that a nested function reads, `co_freevars` for names it reads from an enclosing function, and `co_names` for everything looked up by name at run time: globals, attributes, imports.

The first three of those are not stored. There is one array, `co_localsplusnames`, holding every slot a {term("frame")} will need, and one string of bytes next to it with one tag per slot. The header says so out loud, {cite("Include/cpython/code.h:82-95@v3.15.0rc1")}, where the four counts are under a comment reading "redundant values (derived from co_localsplusnames and co_localspluskinds)".

Getting `co_varnames` runs {cite("Objects/codeobject.c:423-443@v3.15.0rc1#get_localsplus_names")}, which walks the array and keeps the slots whose tag matches. The test is `(k & kind) == 0`, a bitwise and, and the tags are single bits, {cite("Include/internal/pycore_code.h:192-199@v3.15.0rc1")}. A slot with two bits set comes back from two different calls.

{lesson.claim("a parameter that a nested function reads is tagged twice, so it appears in two tuples")}
""")


lesson.code("""
def outer(a, b=2, *args, c, **kw):
    n = 0

    def inner():
        return a + n

    return inner


code = outer.__code__

slots = []
while True:
    try:
        slots.append(code._varname_from_oparg(len(slots)))
    except IndexError:
        break

print(f"  {len(slots)} slots in the array")
print(f"  co_varnames has {len(code.co_varnames)}", end="")
print(f", co_cellvars has {len(code.co_cellvars)}", end="")
print(f", co_freevars has {len(code.co_freevars)}")
print()
for i, name in enumerate(slots):
    tags = [
        label
        for label, where in (
            ("local", code.co_varnames),
            ("cell", code.co_cellvars),
            ("free", code.co_freevars),
        )
        if name in where
    ]
    print(f"    slot {i}  {name:8} {', '.join(tags)}")
""")


lesson.md(f"""
Seven slots. Six locals and two cells, which is eight, because `a` is both.

{figure("one-array-four-views", "one array of slots, and the two tuples that overlap on one of them")}

The reason is a single `|=` in the compiler, {cite("Python/assemble.c:516-528@v3.15.0rc1")}: every parameter gets `CO_FAST_LOCAL`, and then if the name is also in the cell variables, `CO_FAST_CELL` goes on top. It has to be a local, because that is where the caller puts the argument. It has to be a cell, because the nested function needs to see later changes to it rather than a copy.

If you have ever added `len(co_varnames)` to `len(co_cellvars)` and got a number one too big, that is why.

## The instructions before line one

There is a visible consequence. A slot cannot be a plain value and a cell at the same time, so something has to convert it, and that something is an instruction at the very top of the function.

{lesson.claim("a function whose parameter is captured starts with instructions that belong to no line of source")}
""")


lesson.code("""
import dis

dis.dis(outer)
""")


lesson.md(f"""
The first two instructions have `--` where a line number should be. `MAKE_CELL 0` takes the value the caller put in slot 0 and wraps it in a cell, in place. `MAKE_CELL 6` makes an empty cell for `n`, which has no value yet.

{figure("a-parameter-becomes-a-cell", "a parameter arriving as a value and being turned into a cell before line one")}

Then look at how the closure gets built. `LOAD_FAST_BORROW 0` and `LOAD_FAST_BORROW 6` load the two cell objects, `BUILD_TUPLE` puts them together, and `SET_FUNCTION_ATTRIBUTE 8` hangs that tuple on the new function. Inside `inner`, `COPY_FREE_VARS 2` pulls them out again. Every one of those is an ordinary instruction. There is no hidden machinery.

## co_flags is one integer

`co_flags` is a bit field decided at compile time. Nothing sets a bit in it later.

The definitions are {cite("Include/cpython/code.h:118-153@v3.15.0rc1")}, and `dis` will give you their names.

{lesson.claim("a module body and a class body have no flags set at all, and a function has several")}
""")


lesson.code("""
import dis


def find(code, name):
    \"\"\"The first code object with this name, anywhere inside this one.\"\"\"
    for one in code.co_consts:
        if isinstance(one, types.CodeType):
            if one.co_name == name:
                return one
            deeper = find(one, name)
            if deeper is not None:
                return deeper
    return None


for name in ("<module>", "Shape", "area", "counter"):
    found = module if name == "<module>" else find(module, name)
    bits = [text for bit, text in sorted(dis.COMPILER_FLAG_NAMES.items()) if found.co_flags & bit]
    print(f"  {name:10} {found.co_flags:>10}  {', '.join(bits) or 'nothing set'}")
""")


lesson.md(f"""
`CO_OPTIMIZED` is the one that matters most. It means the locals of this code object live in numbered slots rather than in a dictionary, which is why `LOAD_FAST` exists and why you cannot add a local to a running function. A module body does not have it. That is the whole reason module level code is slower than the same code in a function.

{figure("some-of-the-flags", "four of the co_flags bits and what each one changes")}

`CO_GENERATOR` on `counter` is set because the body contains a `yield`. The compiler decided that while walking the tree, four lessons ago, and calling `counter` returns a generator instead of running the body because of that one bit.

## Two of them can be equal

Code objects compare by value, and the list of what gets compared is worth reading, because of what is missing from it: {cite("Objects/codeobject.c:2502-2541@v3.15.0rc1#code_richcompare")} checks the name, the argument counts, the flags, the first line number, the bytecode, the constants, the names and both side tables. It never looks at `co_filename`.

The bytecode comparison is the other interesting bit. It reads through `_Py_GetBaseCodeUnit`, which undoes {term("specialization")}, so a function that has been running hot for an hour still compares equal to a freshly compiled copy of itself.

{lesson.claim("the same source compiled from two different filenames gives two equal code objects")}
""")


lesson.code("""
SOURCE = "def h(x):\\n    return x * 2\\n"

here = compile(SOURCE, "/one/place.py", "exec").co_consts[0]
there = compile(SOURCE, "/somewhere/else.py", "exec").co_consts[0]

print(f"  filenames  {here.co_filename}  and  {there.co_filename}")
print(f"  equal      {here == there}")
print(f"  same hash  {hash(here) == hash(there)}")
print(f"  same object {here is there}")
print()

namespace = {}
exec(compile(SOURCE, "/one/place.py", "exec"), namespace)
for _ in range(5000):
    namespace["h"](3)

warm = namespace["h"].__code__
print(f"  after 5000 calls, still equal to a fresh compile   {warm == there}")
print(f"  co_code is byte for byte identical                 {warm.co_code == there.co_code}")
adaptive_differs = warm._co_code_adaptive != there._co_code_adaptive
print(f"  the adaptive copy underneath it is not             {adaptive_differs}")
""")


lesson.md(f"""
The filename is carried so a traceback can tell you where to look. It is not part of what the object is.

{figure("what-equality-looks-at", "the fields equality reads and the ones it ignores")}

The last two lines are a preview of F14. `co_code` gives you the instructions the compiler produced. `_co_code_adaptive` gives you the ones the interpreter is actually running, which change as it learns. Equality uses the first, which is the only sensible choice, since otherwise a function would stop being equal to itself partway through a loop.

## You cannot change one

Code objects are immutable. There is no setter for any of the `co_` attributes. What there is instead is `replace`, which builds a new one with some fields swapped, and it is how tools like `coverage` and `cloudpickle` get their work done.

{lesson.claim("replace gives you a new code object and leaves the original alone")}
""")


lesson.code("""
renamed = here.replace(co_name="something_else", co_filename="/made/up.py")

print(f"  original {here.co_name:16} {here.co_filename}")
print(f"  new      {renamed.co_name:16} {renamed.co_filename}")
print(f"  equal to the original now  {renamed == here}")
print()
try:
    here.co_name = "nope"
except AttributeError as problem:
    print(f"  assigning to co_name says: {problem}")
""")


lesson.md(f"""
Changing the name broke equality, because the name is compared. Changing the filename would not have.

Everything a new code object goes through on the way in is {cite("Objects/codeobject.c:446-485@v3.15.0rc1#_PyCode_Validate")}, which checks the argument counts against each other, checks the bytecode is an even number of bytes, and refuses anything that does not add up. That is the guard between a valid code object and a crash, and it is worth knowing it exists before you go building one by hand.

## Try it yourself

1. Walk the code objects of a real module from the standard library. Which one has the most constants?
2. Find a function where `co_names` and `co_varnames` share a name. What has to be true for that?
3. Compile a lambda. What is its `co_name`, and what is its `co_qualname`?
4. Use `replace` to change `co_consts` of a simple function and build a working function from the result with `types.FunctionType`.
5. Set `CO_OPTIMIZED` on a module body with `replace` and try to run it. What happens, and why is that fair?

## What just happened

A code object is the compiled form of one module, function body or class body, and it holds no values at all. That is what lets one of them serve every call.

Compiling a file gives you one code object with the rest nested inside it, through `co_consts`. There is no other index. A nested `def` is a constant.

Names are the confusing part. `co_varnames`, `co_cellvars` and `co_freevars` are not stored. They are filtered out of one array of slots using one tag byte per slot, and a tag byte can have more than one bit set, so a parameter that a nested function reads appears in two of them and gets counted twice.

That double tagging is visible from the outside as `MAKE_CELL` instructions at the top of a function, which have no line number because they belong to no line you wrote.

`co_flags` is a bit field fixed at compile time. `CO_OPTIMIZED` is the one that decides whether locals are slots or dictionary entries, and a module body does not have it.

Two code objects compiled from different files can be equal and hash the same, because the filename is not part of the comparison. Neither is anything the specializer wrote after compilation.

## What is next

F11 is the two side tables this lesson skipped: the {term("line table")} and the {term("exception table")}. Both are compressed byte formats, both are decodable by hand, and one of them explains why a `try` block costs nothing until something goes wrong.
""")


raise SystemExit(lesson.save())
