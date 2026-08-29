#!/usr/bin/env python
"""T04. Names get scopes.

The third stage in close up, and the first one that does not change the tree at all. The
symbol table pass walks the tree, works out what every name in every block means, and hands
the answer to the code generator. Nothing is written back.

The lesson is built around the `UnboundLocalError` puzzle, because it is the one place most
Python programmers have already met this pass without knowing it. A function reads a name
and then assigns it two lines later, and the read fails. Everybody has hit it, most people
have been told "assignment makes it local", and almost nobody has seen the two different
instructions that come out of the compiler.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of
them. `just lessons` checks that the committed notebook still matches this file, so a cell
edited in Jupyter and committed without coming back here fails the build.

The pictures come from `diagrams.py` in this directory. They are looked up on disk rather
than imported, so a diagram that has not been built yet fails here instead of producing a
notebook full of broken images.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("t04-names-get-scopes", "t04")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("t04-names-get-scopes").figure

lesson.md(f"""
# T04. Names get scopes

{badge}

T03 ended with a tree that knows a line says `answer` but not which `answer` that is, and it cannot work it out on its own, because the answer depends on the whole function the line sits in.

This lesson is about the pass that works it out. It walks the tree, decides what every name in every block means, and hands the answer on. It changes nothing in the tree, it only answers a question. What it produces is the {term("symbol table")}.

{figure("where-we-are", "the eight stages of running Python, with the symbol table highlighted")}

That sounds like bookkeeping, and then you find out it is the reason for the error message you have probably already seen:

```
UnboundLocalError: cannot access local variable 'answer' where it is not associated with a value
```

By the end of this lesson you will know why that happens, you will have seen the two different instructions the compiler produced for one identical line of code, and you will be able to predict which one you get before you run anything.

No C required, and everything here runs on a normal Python.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/symtable.c:669-708@v3.15.0rc1#analyze_name`.

Read it as four parts: the file, the lines, the release those line numbers belong to, and the name of the function they are inside.

Every reference is a link, and every one is checked against the pinned source on each change, so a stale reference fails the build instead of sending you somewhere wrong. The function name on the end is what makes the check work. Line numbers move whenever somebody adds code above them, and a moved line number points at something that looks plausible and is not.

You never have to read any of it. The references are there so you can go deeper when you want to, and so you can check that this lesson is not making things up.
""")


lesson.md("""
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

The instruction names in this lesson are the ones your interpreter actually produces, and a few of them changed recently. `LOAD_FAST_BORROW` arrived in 3.14 and you will not see it on an older build. So, as always, the first cell says which interpreter produced everything below it.
""")


lesson.code(
    """
import pyxray

pyxray.show()
""",
    differs=BANNER,
    quiet=True,
)


lesson.md("""
## The puzzle

Two functions, and it is worth reading them and deciding what you expect before running anything. Both contain the line `print(answer)`, and the only difference is that the second one has an extra line at the bottom.
""")


lesson.code('''
source = """
answer = 42

def show():
    print(answer)

def broken():
    print(answer)
    answer = 1
"""

namespace = {}
exec(source, namespace)

namespace["show"]()
''')


lesson.md("""
`show` printed 42, which is what you would expect. Now the other one.
""")


lesson.code("""
try:
    namespace["broken"]()
except UnboundLocalError as error:
    print("UnboundLocalError:", error)
""")


lesson.md("""
The line that failed is `print(answer)`, the first line of the function. The assignment is on the line after it, and it never ran.

The usual explanation is that assigning to a name anywhere in a function makes it local everywhere in that function. That is true, and it does not say who decided or when, which is what the rest of this lesson is about.
""")


lesson.md("""
## The compiler already knew

The most direct way to see what happened is to look at the instructions. These two functions were compiled from the source above, before either of them ran, so whatever went wrong was already decided at that point.
""")


lesson.code("""
from pyxray import scopes

for name in ["show", "broken"]:
    print(name)
    for opname, argument in scopes.opcodes(source, name):
        if argument == "answer":
            print("   ", opname, argument)
""")


lesson.md(f"""
Two different instructions for the same line of code.

`LOAD_GLOBAL` goes and looks in the module dictionary. `LOAD_FAST_CHECK` reads a numbered slot in the current {term("frame")}, checking first that anything was ever put there. In `broken` nothing had been, so it raised.

{figure("the-same-line-twice", "the same line of source compiling to two different instructions")}

That rules something out. The interpreter did not get to `print(answer)`, fail to find `answer`, and then decide to complain. It was never going to look in the module dictionary at all, and that was settled before the function ran once.
""")


lesson.md("""
## Who decided, and when

Between the tree and the code generator there is a pass that does nothing but answer this question. It builds a table: for every block of code, a list of every name that appears in it and what that name means there.

`symtable` in the standard library is that same pass, exposed to you. It is not a reimplementation or an approximation. `symtable.symtable` calls straight into the C the compiler uses.
""")


lesson.code("""
import symtable

top = symtable.symtable(source, "lesson.py", "exec")

for block in top.get_children():
    print(block.get_name(), "block")
    for symbol in block.get_symbols():
        print("   ", symbol.get_name(), "local" if symbol.is_local() else "not local")
""")


lesson.md(f"""
In `show`, `answer` is not local, and in `broken` it is. Same name, same spelling, two blocks, two answers.

You may also see a block called `__annotate__` that you did not write. Since 3.14 every `def` gets one, whether or not you annotated anything, because annotations are now evaluated lazily and need somewhere to live. It is empty here and you can ignore it.

The unit of the decision is the block, which is what {term("scope")} means here, and not the line and not the file.

{figure("one-decision-per-block", "nested blocks, each with its own answer for the same name")}

A block is a module, a function, a lambda, a class body or a comprehension. Every one gets its own table. That is why the assignment on the last line of `broken` reaches back to the first line: they are in the same block, and the block was looked at all at once.

In CPython this happens in {cite("Python/symtable.c:1139-1150@v3.15.0rc1#analyze_block")}, which is called once per block and works out every name in it before moving on.
""")


lesson.md("""
## The whole table at once

Reading `symtable` directly gets verbose quickly, and it only tells you half the story. `pyxray.scopes` puts the symbol table and the compiled instructions side by side, so you can see the decision and the consequence in one row.
""")


lesson.code("""
print(scopes.show(source))
""")


lesson.md(f"""
Read one row at a time: the name, what was decided about it, why, and the instructions that came out. There are five possible decisions and each one produces a different instruction.

{figure("five-answers", "the five scopes and the instruction each one produces")}

The mapping from one column to the next happens in {cite("Python/compile.c:1009-1048@v3.15.0rc1#_PyCompile_ResolveNameop")}, which takes the scope the symbol table decided on and picks which family of opcode to use. {cite("Python/codegen.c:3281-3300@v3.15.0rc1#codegen_nameop")} is the caller, and it is the only place in the compiler that turns a name into a load or a store.

This part is worth pausing on. The scope of a name is not stored anywhere in the finished {term("code object")}, and there is no table in there saying "answer is a local". The information survives only as the choice of instruction, which is why a disassembly tells you everything about scope and why nothing has to look it up while your program runs.
""")


lesson.md("""
## The order the questions are asked in

Five answers, and something has to choose between them when more than one could apply. The order is fixed, and it explains a couple of things that look arbitrary from the outside.
""")


lesson.code('''
declared = """
answer = 42

def f():
    global answer
    answer = 1
"""

print(scopes.find(declared, "f", "answer"))
''')


lesson.md(f"""
`answer` is assigned inside `f`, which would normally make it local. It is global anyway, because the `global` statement was checked first.

{figure("the-cascade", "the order the questions are asked in, first yes wins")}

That ladder is {cite("Python/symtable.c:669-708@v3.15.0rc1#analyze_name")}, one `if` per rung, in that order. The two declarations come first, then whether the name is assigned in this block, then whether some block around this one assigns it, and if nothing matched, it is a global.

The five names CPython uses internally are in {cite("Include/internal/pycore_symtable.h:187-192@v3.15.0rc1#GLOBAL_EXPLICIT")}, and the flags that feed the ladder are just above them in {cite("Include/internal/pycore_symtable.h:165-177@v3.15.0rc1#DEF_BOUND")}. `DEF_BOUND` is worth a look: it is the union of assigned, parameter and imported, which is exactly the set of things that count as "you bound this name here".
""")


lesson.md("""
## A global statement reaches further than you would think

One consequence of that ladder is easy to miss. A `global` statement inside a function changes the instruction used at module level, outside the function.
""")


lesson.code("""
plain = "answer = 42\\n"
declared = "answer = 42\\ndef f():\\n    global answer\\n"

print("without the function:", scopes.find(plain, "<module>", "answer").writes)
print("with the function:   ", scopes.find(declared, "<module>", "answer").writes)
""")


lesson.md("""
The module's own assignment went from `STORE_NAME` to `STORE_GLOBAL`, and the function that caused it never runs. Adding three lines at the bottom of a file changed how the first line is compiled.

Both instructions do the same thing at module level, so nothing about the behaviour changes. It is a good illustration of how far the symbol table's reach goes: it looks at the entire file before it decides anything about any part of it.
""")


lesson.md(f"""
## Closures need somewhere to put the value

So far every name has been in one place: a frame, or the module dictionary. A {term("closure")} is the case where that is not enough, because two functions have to share one variable and one of them has already returned.
""")


lesson.code('''
closure = """
def outer():
    total = 0
    def inner():
        nonlocal total
        total += 1
        return total
    return inner
"""

print(scopes.show(closure))
''')


lesson.md(f"""
`total` is a {term("cell")} in `outer` and a {term("free variable", "free variable")} in `inner`. Both are read with `LOAD_DEREF`, which is the point: the difference between cell and free is which block owns the box, not how you get at it.

{figure("one-box-two-frames", "two frames sharing one cell")}

`MAKE_CELL` in `outer` is what creates the box. Once `outer` returns its frame is gone and the cell is not, because the function object `inner` is holding on to it. That is all a closure is: a function plus a tuple of cells.

You can see the cells from the outside.
""")


lesson.code("""
namespace = {}
exec(closure, namespace)
counter = namespace["outer"]()

print("free variables:", counter.__code__.co_freevars)
print("the cells:     ", counter.__closure__)
print("first call: ", counter())
print("second call:", counter())
print("the cell now:", counter.__closure__[0].cell_contents)
""")


lesson.md("""
The number is inside the cell, and the cell is attached to the function object. Nothing about that involves a frame, which is why the count survives from one call to the next.

Note that `nonlocal` was needed here for the assignment, and would not have been needed for a read. Reading a name from an enclosing function makes it free on its own. Only assigning to one needs the declaration, for the same reason as `global`: without it, the assignment would have made a fresh local.
""")


lesson.md("""
## A class body is not a function

The last of the five answers is `name`, and it only shows up at module level and inside a class body.
""")


lesson.code('''
in_a_class = """
class Table:
    size = 20
    width = size * 2
"""

in_a_function = """
def build():
    size = 20
    width = size * 2
"""

print("in a class body: ", scopes.find(in_a_class, "Table", "size").reads)
print("in a function:   ", scopes.find(in_a_function, "build", "size").reads)
''')


lesson.md(f"""
Identical lines, one indent level apart, two different instructions again.

A function body gets numbered slots, decided at compile time. A class body gets a dictionary that it fills in as it runs, and `LOAD_NAME` looks in that dictionary first, then the globals, then the builtins, every single time.

That is the branch at {cite("Python/compile.c:1009-1048@v3.15.0rc1#_PyCompile_ResolveNameop")}, which asks whether the block is function-like before deciding that a local means a frame slot.

It also explains something you may have run into. `exec("x = 1")` inside a class body or at module level puts `x` where later code can see it, and the same call inside a function does not. The function's slots were numbered at compile time and nothing added at runtime can join them.
""")


lesson.md("""
## Where the check comes from

One loose end is left. The instruction in `broken` was `LOAD_FAST_CHECK` rather than `LOAD_FAST`, and the difference is that one of them checks whether the slot has anything in it.
""")


lesson.code('''
always_set = """
def fine():
    answer = 1
    return answer
"""

print("assigned before it is read:", scopes.find(always_set, "fine", "answer").reads)
print("read before it is assigned:", scopes.find(source, "broken", "answer").reads)
''')


lesson.md(f"""
The compiler only pays for the check where it might be needed. If every path to a read passes through an assignment first, the read cannot fail, so it uses plain `LOAD_FAST` and does not look.

That decision is made later than everything else in this lesson, after the instructions exist, in {cite("Python/flowgraph.c:3362-3401@v3.15.0rc1#add_checks_for_loads_of_uninitialized_variables")}. It walks the {term("control flow graph")} from the start, tracking which locals could still be empty when control arrives, and upgrades exactly the loads that need it.

The message you get comes from {cite("Python/bytecodes.c:271-280@v3.15.0rc1#LOAD_FAST_CHECK")}, which is the definition of the instruction itself.
""")


lesson.md("""
## Try it yourself

Four things to try, with a prediction written down before each one.

**One.** Add `global answer` to the top of `broken` and work out what changes. Two things do: the instruction, and whether the assignment affects the module.

**Two.** Take the `nonlocal` out of `inner`. The read still works and the assignment stops working, and the reason is one row in the table.

**Three.** Write a function that assigns a name only inside an `if` that is never true, then reads it. Predict whether you get `LOAD_FAST` or `LOAD_FAST_CHECK`, and whether it raises.
""")


lesson.code('''
experiment = """
def maybe(flag):
    if flag:
        answer = 1
    return answer
"""

print(scopes.show(experiment))
''')


lesson.md("""
**Four**, which is a real bug people hit and cannot explain. A comprehension inside a class body can use the class's own attributes in some places and not others, so the code below looks fine and raises `NameError`.
""")


lesson.code('''
in_a_class_body = """
class K:
    rows = [1, 2]
    factor = 3
    doubled = [r * factor for r in rows]
"""

try:
    exec(in_a_class_body, {})
except NameError as error:
    print("NameError:", error)

print()
print(scopes.show(in_a_class_body))
''')


lesson.md("""
`rows` is read with `LOAD_NAME` and `factor` with `LOAD_GLOBAL`, in the same block, three lines apart, and `factor` was assigned two lines above where it is read.

The reason is that the first iterable of a comprehension is evaluated in the enclosing block and everything else in the comprehension is not. The body belongs to the comprehension, and a comprehension cannot see into a class body, so `factor` falls through to the globals and is not there. `rows` never had that problem because it was read before the comprehension started.

That is the sharpest version of the point the whole lesson has been making: the source looks symmetrical, the bug is invisible in it, and the two instructions are different.
""")


lesson.md("""
## What just happened

The pipeline picked up a new kind of stage here. The tokenizer turned text into tokens and the parser turned tokens into a tree, and both of them produced something you can look at. This pass produced nothing you can hold: it walked the tree, answered a question about every name, and the answer left as a choice of instruction.

Four things worth keeping.

The unit is the block, meaning a module, a function, a lambda, a class body or a comprehension, and not a line and not a file.

The whole block is considered at once, which is why an assignment on the last line changes the first line.

There are five possible answers, and the code object does not record which one you got, so the instruction is the only record.

`global` and `nonlocal` are not runtime operations. They are notes to this pass, read before anything else in the ladder, which is why they beat an assignment sitting underneath them.
""")


lesson.md("""
## Where this goes next

Every name in the tree now has an answer attached to it, and the tree is otherwise unchanged. T05 is the pass that finally turns all of it into instructions, and it is the one that consumes what this lesson produced: the code generator walks the tree, and every time it reaches a name it asks the symbol table what to emit.

That is also where the arithmetic goes. T01 showed that `6 * 7` never happens while your program runs, and left the question of who did the multiplication and when. T05 answers it.
""")


raise SystemExit(lesson.save())
