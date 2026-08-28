#!/usr/bin/env python
"""T05. The tree becomes bytecode.

The lesson T01 promised. T01 disassembled `answer = 6 * 7`, showed the reader that no
multiply instruction is there, and left it at that. This is where the multiplication turns
up, in a function in `Python/flowgraph.c` that runs while the file is being compiled.

The shape of the lesson is that `compile()` looks like one thing and is three, and all three
can be called separately from a stock interpreter through `_testinternalcapi`. So the reader
gets to run the code generator on its own, look at what it produced, run the optimizer on
that, and compare. Watching the list get shorter is worth more than any amount of prose
about optimization.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of
them. `just lessons` checks that the committed notebook still matches this file, so a cell
edited in Jupyter and committed without coming back here fails the build.

The pictures come from `diagrams.py` in this directory. They are looked up on disk rather
than imported, so a diagram that has not been built yet fails here instead of producing a
notebook full of broken images.
"""

from nbbuild import Lesson
from nbdiagram import Diagrams

lesson = Lesson("t05-the-tree-becomes-bytecode", "t05")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("t05-the-tree-becomes-bytecode").figure

lesson.md(f"""
# T05. The tree becomes bytecode

{badge}

T01 disassembled one line of Python and pointed out something odd. Here is that line again:

```
answer = 6 * 7
```

There is no multiply instruction in the result. The number 42 is simply there, and nothing in the finished program ever works it out. T01 said the multiplication had already happened and moved on. This lesson is where it happened.

{figure("where-we-are", "the eight stages of running Python, with the last three of the compiler highlighted")}

Three boxes are lit up because `compile()` is three separate pieces of work behind one name. You can run each piece on its own, from an ordinary Python, and that is what most of the cells below do.

By the end you will have watched the compiler do the multiplication, seen the exact function that did it, found the four numbers that decide when it gives up and leaves the work for later, and watched an entire `if` block disappear from a file.

No C required, and everything here runs on a normal Python.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/flowgraph.c:1916-1948@v3.15.0rc1#fold_const_binop`.

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

More of this lesson is version dependent than usual. The optimizer is where CPython's release notes spend most of their "faster" bullet points, so the exact instruction list below is the one your interpreter produced and not the one somebody wrote down in 2023.
""")


lesson.code("""
import pyxray

pyxray.show()
""")


lesson.md(f"""
## compile() is three things

`compile()` takes source and gives back a {term("code object")}, and it looks like one operation while being three. The comment at the top of CPython's own compiler file lists the passes, and it is worth reading because it is the whole plan of the front end in twelve lines: {cite("Python/compile.c:1-15@v3.15.0rc1#_PyAST_Compile")}.

The first two are behind us. T02 was the tokenizer, T03 was the parser, T04 was the symbol table. This lesson is the last three, and here they are with the file each one lives in.

{figure("three-stages-in-one-call", "the code generator, the optimizer and the assembler, with their source files")}

{term("code generation", "The code generator")} walks the tree and emits {term("instruction", "instructions")}. It does not think about them at all, it just writes down what each node means. The optimizer takes that list, rearranges it into a graph, and improves it. The {term("assembler")} turns the improved graph into the bytes and the tables that make up a code object.

The reason this lesson can exist is that a stock CPython exports the first two as callable functions, in a module called `_testinternalcapi` that ships with the interpreter so CPython can test itself. Almost nobody uses it for teaching, and it is the best teaching hook in the codebase.
""")


lesson.code("""
from pyxray import compiler

print("stage by stage compiling available:", compiler.available())
""")


lesson.md("""
If that said False you are on a build without `_testinternalcapi`, which happens on some slimmed down distributions. Most cells below still work, and the two that run the stages separately will raise a clear error rather than a confusing one.

## The whole trip, counted

The next cell runs every stage on one line of source and counts what came out of each one.
""")


lesson.code("""
result = compiler.stages("answer = 6 * 7")

print(result.summary())
""")


lesson.md("""
Read the last three numbers again. Eight instructions came out of the code generator, five survived the optimizer, and the finished code object is a handful of bytes. Three instructions went missing, and one of them was the multiplication.

## Where the multiplication went

The next cell puts both lists side by side. The left column is what the code generator wrote down, the right column is what was left after the optimizer had a look at it.
""")


lesson.code("""
print(compiler.what_the_optimizer_did(result))
""")


lesson.md(f"""
{figure("before-and-after", "the eight instructions the code generator produced and the five that survived")}

Look at rows three, four and five on the left. Load a constant, load another constant, multiply them. That is the multiplication, written down exactly as you would expect, and it exists for a moment during compilation and then stops existing.

{figure("where-the-multiplication-went", "three instructions collapsing into one that already holds the answer")}

The function that does it is {cite("Python/flowgraph.c:1916-1948@v3.15.0rc1#fold_const_binop")}. Its job is small and worth spelling out. It finds a `BINARY_OP`, looks at the two instructions before it, and checks whether both of them are loading constants. If they are, it fetches the two values, does the arithmetic there and then, replaces the `BINARY_OP` with a load of the answer, and turns the two loads into nothing.

The arithmetic itself is in {cite("Python/flowgraph.c:1860-1880@v3.15.0rc1#eval_const_binop")}, and it is a `switch` over the operators calling the same `PyNumber_Multiply` and `PyNumber_Add` your program would have called. The compiler is not simulating the multiplication. It is doing it, with the same code, on the same objects, just earlier.

This has a name people use without explaining it, {term("constant folding")}, which is accurate and not much help. What is happening is that the compiler notices it already has everything it needs to work out an answer, so it works it out and writes the answer down instead of the recipe.
""")


lesson.md(f"""
## Where 42 actually ended up

The finished instruction is `LOAD_SMALL_INT 42`, and that is worth a moment because the 42 is not stored anywhere. It is the {term("oparg", "argument byte")} of the instruction itself.
""")


lesson.code("""
code = compile("answer = 6 * 7", "lesson.py", "exec")

print("co_consts:", code.co_consts)
""")


lesson.md(f"""
That is not a typo, and it is two surprises at once.

42 is not in there, because an instruction argument is one byte and 42 fits in one byte, so it rides along inside the instruction. {cite("Python/bytecodes.c:317-322@v3.15.0rc1#LOAD_SMALL_INT")} is the whole implementation, which is one index into an array of preallocated small integers, with no lookup and no table.

And 6 is still in there with nothing loading it. The optimizer removed the instruction that used it and left the constant sitting in the table, because the constants are collected while the code is being generated and nobody goes back afterwards to sweep up. It costs eight bytes in the file and nothing at runtime, so it has never been worth fixing.

You can check that claim rather than believing it.
""")


lesson.code("""
import dis

used = [step.arg for step in dis.get_instructions(code) if step.opname == "LOAD_CONST"]
print("constants in the table:", code.co_consts)
print("constants actually loaded:", used)
""")


lesson.md(f"""
## Instructions that cannot run

There is a second thing in the left column worth noticing, `ANNOTATIONS_PLACEHOLDER`, and there is no such instruction. You will never see it in a disassembly and the interpreter has no idea what it means.

The code generator uses a handful of these. They are called {term("pseudo instruction", "pseudo instructions")}, and they carry information between the compiler's own stages. Some mark a spot that a later pass will fill in, and some describe control flow in a form that is easier to rearrange than a jump to a byte offset.
""")


lesson.code("""
for name in compiler.pseudo_instructions():
    print(name)
""")


lesson.md(f"""
Eleven of them, and the list comes from the interpreter's own opcode table rather than from this lesson, because it changes: {cite("Include/opcode_ids.h:247-257@v3.15.0rc1#ANNOTATIONS_PLACEHOLDER")}. Their numbers start at 256, which is the giveaway. An instruction argument is a byte, opcodes go up to 255, and anything numbered higher than that could not be written into a file even if somebody wanted to.

`SETUP_FINALLY` is the interesting one. Look at what happens to a `try` block.
""")


lesson.code('''
guarded = """
try:
    n = 1 / 0
except ZeroDivisionError:
    n = 0
"""

print(compiler.what_the_optimizer_did(compiler.stages(guarded)))
''')


lesson.md(f"""
`SETUP_FINALLY` and `SETUP_CLEANUP` survive the optimizer, so they are still there in the right column, and then they are gone from the finished code object. The assembler reads them, works out which range of bytes each one protects and where the handler is, writes that down as an {term("exception table")}, and drops the instructions.

That table is why `try` is free in Python when nothing goes wrong. There is no instruction at the top of the block doing bookkeeping, there is a lookup table that is only consulted when an exception is actually raised.

Also worth noticing in that output: `1 / 0` was not folded. The optimizer tried, got a `ZeroDivisionError`, and put the instructions back exactly as they were so your program can raise the error itself at the moment it runs.

## The optimizer works on a graph

Calling it a list of instructions has been a simplification for the last few cells. The optimizer's first move is to cut the list into {term("basic block", "basic blocks")}, which are runs of instructions with no jumps in and no jumps out except at the end, and to join those blocks with edges wherever a jump goes. The result is a {term("control flow graph")}.

Doing that makes a question askable that a flat list cannot answer: can this code be reached at all.
""")


lesson.code('''
never = """
if False:
    print("this never runs")
print("this does")
"""

print(compiler.what_the_optimizer_did(compiler.stages(never)))
''')


lesson.md(f"""
Seventeen instructions in and nine out, and the entire body of the `if` is gone.

{figure("the-unreachable-block", "a block with no arrow pointing into it, which is how the compiler finds dead code")}

The steps are small and each one is dull on its own. `False` is a constant so `TO_BOOL` folds. Now `POP_JUMP_IF_FALSE` is jumping on a value that is known, so it becomes an ordinary jump, and the edge into the middle block disappears with it. Then {cite("Python/flowgraph.c:1008-1044@v3.15.0rc1#remove_unreachable")} walks the graph from the entry block counting how many edges arrive at each one, finds a block that nothing points to, and deletes its instructions.

You can check that the string is really gone.
""")


lesson.code("""
print(compile(never, "lesson.py", "exec").co_consts)
""")


lesson.md("""
`'this never runs'` is not in the file. It is not skipped at runtime and not stored and ignored, it was never written down.

`False` is still there, which is the same kind of leftover constant as before. Removing it is nobody's job.

## What else disappears

Two smaller rewrites are visible in almost every disassembly once you know to look for them.
""")


lesson.code('''
looping = """
total = 0
for n in [1, 2, 3]:
    total += n
"""

print(compiler.what_the_optimizer_did(compiler.stages(looping)))
''')


lesson.md(f"""
On the left, four instructions build the list: load 1, load 2, load 3, `BUILD_LIST 3`. On the right there is one `LOAD_CONST`, because the optimizer noticed that the list is never modified and is only being iterated over, so it built the collection once at compile time and stored it as a constant tuple. Every time round the loop, the interpreter would otherwise be rebuilding the same list from scratch.

The other one is `LOAD_COMMON_CONSTANT 7` at the end. That is `None`, and it is not in the constants table either. Twelve values turn up so often that the interpreter keeps them permanently and loads them by number: {cite("Include/internal/pycore_opcode_utils.h:70-83@v3.15.0rc1#CONSTANT_NONE")}. `None`, `True`, `False`, `AssertionError`, the empty string, and a few builtins.

Every function that falls off the end returns `None`, which is most functions, so this saves one constant table entry per function in a program that has thousands of them.
""")


lesson.md(f"""
## When the compiler decides not to

Folding trades file size for speed. The answer to `6 * 7` is smaller than the recipe for it, so writing down the answer wins twice, and that stops being true quickly.

Somewhere there has to be a line, and in CPython it is four numbers: {cite("Python/flowgraph.c:1760-1763@v3.15.0rc1#MAX_INT_SIZE")}.

{figure("four-limits", "the four size limits that stop constant folding, with an example either side of each")}

They are exact rather than rules of thumb, so you can find the boundary yourself.
""")


lesson.code("""
for expression in ["2 ** 64", "2 ** 65", "3 ** 64", "4 ** 64", "'-' * 4096", "'-' * 4097"]:
    verdict = "worked it out now" if compiler.folds(expression) else "left it for later"
    print(f"{expression:14} {verdict}")
""")


lesson.md(f"""
The check is in {cite("Python/flowgraph.c:1810-1829@v3.15.0rc1#const_folding_safe_power")}, and it is arithmetic on the sizes rather than a try and see. A number that takes `v` bits, raised to the power `w`, needs about `v * w` bits, so the question is whether `v * w` goes over 128.

That estimate is deliberately generous, and it is worth knowing because it explains an answer that otherwise looks arbitrary. `2 ** 65` is a 66 bit number, which is nowhere near 128. It does not fold, because 2 takes two bits to write down and the estimate is two times 65. The compiler is guessing high rather than working it out, and guessing high is the safe direction to be wrong in when the thing you are avoiding is a program that takes a minute to compile.

The same reasoning says 3 stops at the same exponent as 2, since both take two bits, and 4 stops earlier because it takes three.

Two of the refusals have nothing to do with size. `1 / 0` is left alone because evaluating it raised, and `'%s' % name` is left alone on purpose, because `%` on a string is formatting rather than arithmetic and the compiler has no business running it early.
""")


lesson.code("""
for expression in ["7 % 3", "'%s' % 'x'", "1 / 0", "0.1 + 0.2"]:
    verdict = "worked it out now" if compiler.folds(expression) else "left it for later"
    print(f"{expression:14} {verdict}")
""")


lesson.md("""
`0.1 + 0.2` folds, and gives exactly the wrong looking answer you would get at runtime, because it is the same addition on the same floats. Folding never changes what your program computes. That is the one rule the whole thing has to obey.

## The one thing it cannot do

Everything above depends on the compiler knowing both values. The moment one of them is a name, all of it stops.
""")


lesson.code("""
for expression in ["6 * 7", "6 * x", "x * 7"]:
    verdict = "worked it out now" if compiler.folds(expression) else "left it for later"
    print(f"{expression:14} {verdict}")
""")


lesson.md("""
This is the honest boundary of a compiler that does not run your program. `x` might be an integer, or a numpy array, or a class with a `__mul__` that sends an email. The compiler has no idea, and cannot have one, because `x` is looked up when the code runs.

There is a real speedup here that people reach for by hand. Pulling a constant expression out of a loop is worth doing yourself, because the compiler will not do it for you as soon as a name is involved. And a name spelled `math.pi` is worse than a name spelled `pi`, because an attribute lookup is a whole extra instruction with its own cache.

## The assembler

The graph now has to become a file. That is the third stage, and it is the one that builds the parts of a code object that are not instructions.
""")


lesson.code("""
print(compile("answer = 6 * 7", "lesson.py", "exec").co_code.hex(" "))
""")


lesson.md(f"""
Twelve bytes in pairs. Every instruction is one byte of {term("opcode")} and one byte of {term("oparg", "argument")}, and if you look at the third pair you can read `2a` on the right hand side, which is 42. That is the answer to the multiplication, sitting in the file in hexadecimal.

Five instructions is ten bytes, so one pair is unaccounted for, and it is the `00 00` in second place.

{figure("one-instruction", "two bytes per instruction, and the blank cache slots between them")}

Some instructions are followed by blank slots that the interpreter writes into while your program runs, remembering what it saw last time so it can guess faster next time. Those are {term("inline cache", "inline caches")}. They are real bytes in `co_code`, and they are why offsets in a disassembly jump by four or by twenty rather than always by two. T06 is about reading that fluently.

{cite("Python/assemble.c:779-802@v3.15.0rc1#_PyAssemble_MakeCodeObject")} is the whole third stage in one function. Apply the label map, turn the jump pseudo instructions into real jumps, work out the byte offsets, emit, and build the code object.

{figure("what-the-assembler-makes", "the fields of a code object, and which ones the assembler builds")}

Two of those fields are built here and nowhere else, and neither of them is in the bytes.
""")


lesson.code("""
from pyxray import bytecode

for start, end, line in bytecode.line_table("answer = 6 * 7"):
    print(f"bytes {start:>3} to {end:<3} came from line {line}")
""")


lesson.md(f"""
That is `co_linetable`, the {term("line table")}. It is how a traceback knows which line to print, and it is a lookup table rather than anything stored with the instructions. Since 3.11 it holds column numbers too, which is where the carets under the failing part of a line come from, and those columns came all the way from the tree in T03.
""")


lesson.code('''
faulty = """
try:
    n = 1 / 0
except ZeroDivisionError:
    n = 0
"""

table = compile(faulty, "lesson.py", "exec").co_exceptiontable
print("exception table, in bytes:", len(table))
print(table.hex(" "))
''')


lesson.md("""
That is the whole cost of the `try` block: a few bytes in a table nobody reads unless something goes wrong.

It is also the reason for a piece of Python advice that otherwise sounds like folklore. Asking forgiveness rather than permission is faster than checking first, because the check costs an instruction every single time while the `try` costs nothing until it fires.

## Try it yourself

**One.** Find your own folding boundary. `MAX_COLLECTION_SIZE` is 256 items. Work out which repeated tuple is the last one the compiler will build for you, and check with `compiler.folds`.

**Two.** Take a `while True:` loop with a `break` in it and run it through `what_the_optimizer_did`. `True` is a constant, so the test at the top of the loop is decided at compile time and the three instructions that did the testing are gone. Look for the `TO_BOOL` that also disappears in front of the `if`, and work out why it was safe to remove that one too.

**Three.** Compare `x = 1; y = 2; z = x + y` with `z = 1 + 2`. Both look like they should give the same code. Predict which one has an addition in it, then check.
""")


lesson.code('''
experiment = """
x = 1
y = 2
z = x + y
"""

print(compiler.what_the_optimizer_did(compiler.stages(experiment)))
''')


lesson.md("""
The addition is still there. The compiler can see what `x` and `y` were assigned two lines earlier and does not use it, because at module level another module could have changed either of them in between. The optimizer only ever looks at instructions sitting next to each other in the same block.

## What just happened

`compile()` is three stages. The code generator writes down what the tree means, one node at a time, with no opinions about it. The optimizer rearranges that into a graph of blocks and improves it. The assembler flattens the graph into bytes and builds the tables.

The multiplication in `6 * 7` happens in the optimizer, in a C function called `fold_const_binop`, while your file is being compiled. It is a real multiplication using the same code your program would have used.

The compiler stops as soon as it does not know a value, which is nearly always the moment a name appears.

Dead code is found by asking a graph question, not by reading the source. A block that nothing points at is deleted, and what was inside it never reaches the file.

Two tables come out of the assembler that are not instructions. One turns a byte offset back into a line and a column, which is what tracebacks are made of. The other turns a byte offset into an exception handler, which is what makes `try` cost nothing until it is needed.
""")


lesson.md("""
## Where this goes next

There is now a code object, and everything about it has been described from the outside. T06 is about reading one fluently: what the argument to each instruction actually indexes, how the stack rises and falls as you read down a listing, and how to look at a disassembly and know what the interpreter is about to do without running it.

After that, T07 is the loop that runs it.
""")


raise SystemExit(lesson.save())
