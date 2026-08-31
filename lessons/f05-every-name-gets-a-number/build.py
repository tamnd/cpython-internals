#!/usr/bin/env python
"""F05. Every name gets a number.

The fifth lesson of the front end part, and the nineteenth overall. F04 finished with a tree.
This one is the first thing the compiler does with that tree, and it produces no code at all:
it walks the whole thing twice looking only at names, sorts every one of them into one of five
scopes, and hands the answer to the code generator.

T04 showed that names have scopes and that the scope is decided ahead of time. This lesson is
the pass itself. The `symtable` module is the real C symbol table with a thin Python wrapper
over it, so the whole thing is observable, right down to the flag names in the repr.

The opening is the best evidence there is that this pass exists at all. Five programs that
`ast.parse` accepts without complaint and `compile` refuses.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("f05-every-name-gets-a-number", "f05")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("f05-every-name-gets-a-number").figure


lesson.md(f"""
# F05. Every name gets a number

{badge}

`nonlocal x` at the top of a file is a syntax error. Except that it is not, quite. The grammar has a rule for `nonlocal`, the parser matches it happily, and `ast.parse` hands you a tree without a word of complaint. It is `compile` that refuses.

So something happens between having a tree and having bytecode, and that something knows about scopes. It is the {term("symbol table pass")}, and it produces no code whatsoever. It walks the tree twice, works out what every name in every block means, and writes the answer down for the code generator to use later.

That answer is small. Every name you write ends up as one of five values, and the rest of the compiler never reasons about scope again. It just looks up the number.

{figure("a-pass-in-between", "a pipeline from tokens through the tree to the symbol table and then bytecode")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/symtable.c:415-416@v3.15.0rc1`.

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
## Programs that parse and still will not compile

The quickest way to prove a pass exists is to find something it rejects that nothing before it rejected. Here are five.

{lesson.claim("there are mistakes the parser accepts and the compiler refuses, and every one of them is about names")}
""")


lesson.code(
    """
import ast

SOURCES = (
    "nonlocal x",
    "def f():\\n    nonlocal y\\n",
    "def f():\\n    z = 1\\n    global z\\n",
    "def f(a, a):\\n    pass\\n",
    "class C:\\n    nonlocal w\\n",
)

for source in SOURCES:
    ast.parse(source)
    try:
        compile(source, "<here>", "exec")
        said = "and it compiled too"
    except SyntaxError as unhappy:
        said = unhappy.msg
    print(f"  {source.replace(chr(10), ' / '):34} parses, {said}")
""",
    differs=(
        "3.15 reworded the fourth message. On 3.14 it says `duplicate argument`"
        " rather than `duplicate parameter`."
    ),
)


lesson.md(f"""
Every one of those went through `ast.parse` without raising, which is the first line of the loop and the reason it is there. The tree exists. The refusal comes later.

The messages are in {cite("Python/symtable.c:688-702@v3.15.0rc1")} for the two `nonlocal` ones, {cite("Python/symtable.c:21-22@v3.15.0rc1")} for the `global` one and {cite("Python/symtable.c:386-387@v3.15.0rc1")} for the duplicate parameter. None of them could have been caught earlier, because none of them is about the shape of your program. They are all about what a name means in a block, and nothing before this pass has any idea what a block is.

{figure("parses-but-refuses", "a side by side comparison of what the parser accepts and what the symbol table refuses")}

The pass is started from one line in the compiler, {cite("Python/compile.c:148@v3.15.0rc1")}, before anything else happens. The building is {cite("Python/symtable.c:415-416@v3.15.0rc1#_PySymtable_Build")} and the second walk that works out the answers is {cite("Python/symtable.c:1376-1380@v3.15.0rc1#symtable_analyze")}.

## Five answers, and no sixth

Here is the whole of it, from {cite("Include/internal/pycore_symtable.h:187-191@v3.15.0rc1")}:

```
#define LOCAL 1
#define GLOBAL_EXPLICIT 2
#define GLOBAL_IMPLICIT 3
#define FREE 4
#define CELL 5
```

Five constants. Every name in every block of your program is one of those numbers by the time this pass is done, and the code generator picks its instruction by looking at which.

The `symtable` module is a thin wrapper over the same C structures, and the repr of a symbol prints both the {term("scope")} name and the raw flags that led to it.

{lesson.claim("the symbol table sorts every name in every block into one of five scopes, and you can read the answers straight out of the symtable module")}
""")


lesson.code("""
import symtable

SOURCE = \"\"\"
count = 0

def outer(start):
    total = start
    def inner(step):
        nonlocal total
        total = total + step + count
        return total
    return inner
\"\"\"


def blocks(table, depth=0):
    \"\"\"Every block in the table, skipping the annotation blocks, with how deep it is.\"\"\"
    if table.get_type() != "annotation":
        yield table, depth
    for child in table.get_children():
        yield from blocks(child, depth + 1)


for table, depth in blocks(symtable.symtable(SOURCE, "<here>", "exec")):
    pad = "    " * depth
    print(f"  {pad}{table.get_type()} {table.get_name()}")
    for symbol in sorted(table.get_symbols(), key=lambda one: one.get_name()):
        print(f"  {pad}    {symbol!r}")
""")


lesson.md(f"""
{figure("five-scopes", "a table of the five scopes, how a name lands in each, and what the compiler emits")}

Read `total` down the two function blocks. In `outer` it is `CELL`, because it is assigned there and something inside also wants it. In `inner` it is `FREE`, because it is used there and lives somewhere outside. Same name, same program, two different numbers, and the difference is entirely about who else is looking at it.

`count` in `inner` is `GLOBAL_IMPLICIT`. Nobody wrote `global count` anywhere. It is global because it is used and never assigned in that block, which is the fallback rather than a decision.

The flags after the comma are the second half of the answer. They are the `DEF_` constants from {cite("Include/internal/pycore_symtable.h:165-175@v3.15.0rc1")}, and they record what the first walk saw: `USE` for a read, `DEF_LOCAL` for an assignment, `DEF_PARAM` for a parameter, `DEF_NONLOCAL` for the declaration. The scope on the left is what the second walk concluded from them.

One thing in that output is nothing to do with scopes. Every block has an `annotation` child called `__annotate__`, even though there is not a single annotation in the source. Since 3.14 annotations are evaluated lazily, in a function built for the purpose, so the symbol table makes a block for it whether or not you needed one. The helper above skips them to keep the output readable.

## The whole block, all at once

The first walk reads an entire block before the second walk decides anything. That is not an implementation detail you can ignore, because it is the reason for the most confusing error a new Python programmer meets.

{lesson.claim("a name is local because of an assignment anywhere in the block, including one that comes after the use")}
""")


lesson.code("""
import dis
import symtable

PROGRAMS = (
    ("x is assigned later in the block", "def f():\\n    print(x)\\n    x = 1\\n"),
    ("x is never assigned in the block", "def f():\\n    print(x)\\n"),
)

for label, source in PROGRAMS:
    children = symtable.symtable(source, "<here>", "exec").get_children()
    inside = next(one for one in children if one.get_name() == "f")
    body = compile(source, "<here>", "exec").co_consts[0]
    touches = [one.opname for one in dis.get_instructions(body) if one.argval == "x"]
    print(f"  {label}")
    print(f"      the symbol table says   {inside.lookup('x')!r}")
    print(f"      so the compiler emits   {touches}")
""")


lesson.md(f"""
{figure("the-whole-block-at-once", "a flow showing why a use before an assignment still makes the name local")}

Two identical uses of `x`, two completely different instructions, and the only difference is a line that comes afterwards. In the first program `x` is local, so the compiler emits `LOAD_FAST_CHECK`, which reads a local slot and raises if nothing has been put in it yet. In the second there is no assignment anywhere, so `x` falls through to `GLOBAL_IMPLICIT` and the compiler emits `LOAD_GLOBAL`.

That is where `UnboundLocalError` comes from. It is not a lookup that failed. It is a lookup that succeeded in finding an empty local slot, in a block where the symbol table had already decided the name was local.

## A cell and a free variable are two ends of one wire

The two interesting scopes are `CELL` and `FREE`, and they always come in pairs. A {term("cell")} is a local that something nested inside also reads, so it cannot live in a plain slot that disappears when the function returns. A {term("free variable")} is the other end: a name used here that is local in some block further out.

The code object carries both, in `co_cellvars` and `co_freevars`. Neither of those is worked out by the code generator. They are copied from what this pass already decided.

{lesson.claim("co_cellvars and co_freevars on the code objects are the symbol table's answers, written down again")}
""")


lesson.code("""
import symtable

SOURCE = \"\"\"
def outer(start):
    total = start
    def inner(step):
        nonlocal total
        total = total + step
        return total
    return inner
\"\"\"

table = symtable.symtable(SOURCE, "<here>", "exec")
outer_block = next(one for one in table.get_children() if one.get_name() == "outer")
inner_block = next(one for one in outer_block.get_children() if one.get_name() == "inner")

print("  what the symbol table decided, with no code anywhere in sight")
print(f"      in outer   {outer_block.lookup('total')!r}")
print(f"      in inner   {inner_block.lookup('total')!r}")
print()

names = {}
exec(compile(SOURCE, "<here>", "exec"), names)
outer_code = names["outer"].__code__
inner_code = next(one for one in outer_code.co_consts if getattr(one, "co_name", "") == "inner")

print("  what the finished code objects carry")
print(f"      outer.co_varnames  {outer_code.co_varnames}")
print(f"      outer.co_cellvars  {outer_code.co_cellvars}")
print(f"      inner.co_freevars  {inner_code.co_freevars}")
""")


lesson.md(f"""
{figure("cell-and-free", "a side by side comparison of the same name as a cell in one block and a free variable in another")}

Notice that `total` is not in `outer.co_varnames` at all. It was going to be an ordinary local right up until the symbol table saw that `inner` reads it, and at that point it moved. This is the pass that decides which of your locals get the slow storage, and it decides it once, statically, before anything runs.

## The name you never wrote

There is exactly one name the symbol table will add to a block on your behalf, and it is there so that `super()` can work with no arguments.

`super()` needs to know which class the method was defined in, and a method is just a function: it has no idea. So when this pass is walking a method body and sees the name `super` being read, it records a use of `__class__` as well, at {cite("Python/symtable.c:2651-2657@v3.15.0rc1")}. That turns `__class__` into a free variable of the method and a {term("class cell")} in the class body, which the class machinery fills in as `__classcell__` when the class is created.

The trigger is the name. Not the call, not the type, just a read of the four letters `super` in a function that lives in a class body.

{lesson.claim("a method gets a __class__ free variable because the symbol table saw the name super, and a method that reaches super some other way does not get one")}
""")


lesson.code("""
import builtins


class Base:
    def hello(self):
        return "hello from Base"


class Child(Base):
    def calls_it(self):
        return super().hello()

    def only_names_it(self):
        return super.__name__

    def never_names_it(self):
        return builtins.super().hello()


for method in (Child.calls_it, Child.only_names_it, Child.never_names_it):
    print(f"  {method.__name__:16} co_freevars {method.__code__.co_freevars}")
print()

child = Child()
print(f"  calls_it       {child.calls_it()!r}")
try:
    child.never_names_it()
except RuntimeError as unhappy:
    print(f"  never_names_it RuntimeError: {unhappy}")
""")


lesson.md(f"""
{figure("the-cell-you-did-not-ask-for", "a flow from writing super to the class cell being filled in")}

`only_names_it` never calls anything and still gets the cell, because all the pass looked for was a read of the name. `never_names_it` does call the very same builtin, reaching it through the `builtins` module, and gets nothing, because the only bare name in that line is `builtins`. The error at run time is `super(): __class__ cell not found`, and now you know exactly which pass failed to put it there.

This is the clearest example in the whole compiler of a decision made statically that looks dynamic. Nothing about `super()` is worked out while your program runs. It was all settled by a walk over the tree.

## Try it yourself

1. Put a `global` statement in a function and look at what the symbol table says about that name, in both the function and the module block. Which of the five is it in each?
2. Take the nested example and delete the `nonlocal` line. Watch `total` change scope in both blocks and explain why the outer one changed as well.
3. A comprehension used to be its own block and since 3.12 it usually is not. Write one that uses a name from the enclosing function and see whether a new block appears in the table.
4. `symtable.symtable` takes the same three arguments as `compile`. Point it at a file you wrote and find the block with the most free variables.
5. Find a program where a name is `CELL` in one block and `FREE` in two different blocks below it. What does the middle block have to look like?

## What just happened

Between the tree and the bytecode there is a pass that emits no code. It walks every block twice, once to collect what was written and once to decide what it means, and everything it produces is a set of answers about names.

There are five possible answers, defined as five constants in a header, and every name in every block gets exactly one of them.

The whole block is read before anything is decided, which is why an assignment on the last line makes a name local on the first line, and why `UnboundLocalError` is a thing at all.

`CELL` and `FREE` are the two halves of a closure, and `co_cellvars` and `co_freevars` on the finished code objects are just this pass's answers written down a second time.

Several errors you think of as syntax errors are raised here rather than by the parser, because spotting them needs to know what a block is.

One name gets added on your behalf. Reading the name `super` inside a method makes `__class__` a free variable of that method, which is how a zero argument `super()` finds its class.

## What is next

F06 is the code generator, which is the first pass that produces instructions. It walks the same tree the symbol table just walked, and every time it meets a name it asks this pass what to do.

The answer it gets back is one of the five numbers you have just been reading, which is why a lesson about names had to come before a lesson about code.
""")


raise SystemExit(lesson.save())
