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
notebook full of broken images. The animation is looked up the same way, and its alt text
comes out of the animation catalogue rather than being typed in here, so a lesson cannot
describe an animation differently from the page that also shows it.
"""

from nbbuild import BANNER, TRAILING_NONE, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording
from xraymanim.render import figure as animation

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

Three boxes are lit up because `compile()` is three separate pieces of work behind one name. You can run each on its own from an ordinary Python, which is what most of the cells below do.

By the end you will have watched the compiler do the multiplication, seen the exact function that did it, found the four numbers that decide when it gives up, and watched an entire `if` block disappear from a file.

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

More of this lesson is version dependent than usual. The optimizer is where CPython's release notes spend most of their "faster" bullet points, so the instruction lists below are the ones your interpreter produced rather than ones written down in 2023.

Everything below was checked against the version this cell prints and against 3.14, which is what Colab installs today. Two differences account for nearly all of the disagreements. On 3.15 the implicit `return None` at the end of a module is a `LOAD_COMMON_CONSTANT` and `None` is not in the constant table, where on 3.14 it is an ordinary `LOAD_CONST`. And on 3.15 `RESUME` and `GET_ITER` carry an inline cache, where on 3.14 they do not. So on 3.14 expect one more constant, two fewer bytes of bytecode, and every offset two to four lower. The shape of every listing is the same.
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
## compile() is three things

`compile()` takes source and gives back a {term("code object")}, and looks like one operation while being three. The comment at the top of CPython's compiler file lists the passes, and it is the whole plan of the front end in twelve lines: {cite("Python/compile.c:1-15@v3.15.0rc1#_PyAST_Compile")}.

T02 was the tokenizer, T03 the parser, T04 the symbol table. This lesson is the last three, with the file each one lives in.

{figure("three-stages-in-one-call", "the code generator, the optimizer and the assembler, with their source files")}

{term("code generation", "The code generator")} walks the tree and emits {term("instruction", "instructions")}, writing down what each node means without having an opinion about it. The optimizer rearranges that list into a graph and improves it. The {term("assembler")} turns the improved graph into the bytes and tables that make up a code object.

The reason this lesson can exist is that {lesson.claim("a stock CPython exports the first two compiler stages as callable functions, in a module called _testinternalcapi that ships with the interpreter")} so CPython can test itself. Almost nobody uses it for teaching, and it is the best teaching hook in the codebase.
""")


lesson.code("""
from pyxray import compiler

print("stage by stage compiling available:", compiler.available())
print("the compiler hands back its constants:", compiler.constants_available())
""")


lesson.md("""
If the first line said False you are on a build without `_testinternalcapi`, which happens on some slimmed down distributions. Most cells still work, and the two that run the stages separately raise a clear error.

The second line is the one that catches people out in a browser. The optimizer needs the constants the code generator collected in order to work out that 6 times 7 is 42, and the WebAssembly build does not hand them back. Every cell here still runs, because `pyxray` substitutes placeholders of the right length, but the folding does not happen and the two column output says so. To watch a fold, run this lesson on an ordinary Python.

## The whole trip, counted

The next cell runs every stage on one line of source and counts what came out of each one.
""")


lesson.code(
    """
result = compiler.stages("answer = 6 * 7")

print(result.summary())
""",
    differs=TRAILING_NONE,
    quiet=True,
)


lesson.md(f"""
Read the last three numbers again. Eight instructions came out of the code generator, five survived the optimizer, and the finished code object is a handful of bytes. Three instructions went missing, and one of them was the multiplication.

## Where the multiplication went

The next cell puts both lists side by side: what the code generator wrote down, and what the optimizer left. {lesson.claim("The multiplication in 6 * 7 happens while the file is being compiled, and no multiply instruction survives into the finished program")}.
""")


lesson.code(
    """
print(compiler.what_the_optimizer_did(result))
""",
    differs=TRAILING_NONE,
    quiet=True,
)


lesson.md(f"""
{figure("before-and-after", "the eight instructions the code generator produced and the five that survived")}

Look at rows three, four and five on the left. Load a constant, load another, multiply. That is the multiplication, written down exactly as you would expect, and it exists for a moment during compilation and then stops.

{figure("where-the-multiplication-went", "three instructions collapsing into one that already holds the answer")}

The function that does it is {cite("Python/flowgraph.c:1916-1948@v3.15.0rc1#fold_const_binop")}. It finds a `BINARY_OP` and checks whether the two instructions before it both load constants. If they do, it does the arithmetic there and then, replaces the `BINARY_OP` with a load of the answer, and turns the two loads into nothing.

The arithmetic itself is in {cite("Python/flowgraph.c:1860-1880@v3.15.0rc1#eval_const_binop")}, and it is a `switch` over the operators calling the same `PyNumber_Multiply` and `PyNumber_Add` your program would have called. {lesson.claim("the compiler is not simulating the multiplication, it is doing it with the same C function your program would have called", unobservable="the call happens in C while the file is being compiled, and nothing in the finished code object records that it took place")}, just earlier.

This has a name people use without explaining it, {term("constant folding")}. What is happening is that the compiler already has everything it needs to work out an answer, so it works it out and writes the answer down instead of the recipe.
""")


lesson.md(f"""
## Where 42 actually ended up

The finished instruction is `LOAD_SMALL_INT 42`, and that is worth a moment because {lesson.claim("the 42 is not in the constants table")}. It is the {term("oparg", "argument byte")} of the instruction itself.
""")


lesson.code(
    """
code = compile("answer = 6 * 7", "lesson.py", "exec")

print("co_consts:", code.co_consts)
""",
    differs=TRAILING_NONE,
    quiet=True,
)


lesson.md(f"""
That is not a typo, and it is two surprises at once.

42 is not in there, because an instruction argument is one byte and 42 fits in one byte, so it rides along inside the instruction. {cite("Python/bytecodes.c:317-322@v3.15.0rc1#LOAD_SMALL_INT")} is the whole implementation, which is one index into an array of preallocated small integers, with no lookup and no table.

And {lesson.claim("6 is still in the constants table with nothing loading it")}. The optimizer removed the instruction that used it and left the constant sitting in the table, because constants are collected while the code is being generated and nobody sweeps up afterwards. It costs eight bytes in the file and nothing at runtime, so it has never been worth fixing.

You can check that claim rather than believing it.
""")


lesson.code(
    """
import dis

used = [step.arg for step in dis.get_instructions(code) if step.opname == "LOAD_CONST"]
print("constants in the table:", code.co_consts)
print("constants actually loaded:", used)
""",
    differs=TRAILING_NONE,
    quiet=True,
)


lesson.md(f"""
## Instructions that cannot run

There is a second thing in the left column worth noticing, `ANNOTATIONS_PLACEHOLDER`, and {lesson.claim("there is no such instruction as ANNOTATIONS_PLACEHOLDER outside the compiler")}. You will never see it in a disassembly and the interpreter has no idea what it means.

The code generator uses a handful of these, called {term("pseudo instruction", "pseudo instructions")}, to carry information between the compiler's own stages. Some mark a spot a later pass will fill in, and some describe control flow in a form that is easier to rearrange than a jump to a byte offset.
""")


lesson.code("""
for name in compiler.pseudo_instructions():
    print(name)
""")


lesson.md(f"""
Eleven of them, and the list comes from the interpreter's own opcode table rather than from this lesson, because it changes: {cite("Include/opcode_ids.h:247-257@v3.15.0rc1#ANNOTATIONS_PLACEHOLDER")}. Their numbers start at 256, which is the giveaway: opcodes go up to 255, so anything higher could not be written into a file even if somebody wanted to.

`SETUP_FINALLY` is the interesting one. Look at what happens to a `try` block: {lesson.claim("SETUP_FINALLY and SETUP_CLEANUP are pseudo instructions, and both of them survive the optimizer")}.
""")


lesson.code(
    '''
guarded = """
try:
    n = 1 / 0
except ZeroDivisionError:
    n = 0
"""

print(compiler.what_the_optimizer_did(compiler.stages(guarded)))
''',
    differs=TRAILING_NONE,
    quiet=True,
)


lesson.md(f"""
Both survive the optimizer, so they are still in the right column, and then they are gone from the finished code object. The assembler reads them, works out which range of bytes each protects and where the handler is, writes that down as an {term("exception table")}, and drops the instructions.

## The optimizer works on a graph

Calling it a list of instructions has been a simplification. {lesson.claim("the optimizer's first move is to cut the instruction list into basic blocks and join them with edges wherever a jump goes", unobservable="the graph is built, used and thrown away inside the compiler, and is never handed back to Python in any form")}, where a basic block is a run of instructions with no jumps in and no jumps out except at the end. The result is a {term("control flow graph")}.

Doing that makes a question askable that a flat list cannot answer: can this code be reached at all. {lesson.claim("The entire body of an if False block is removed before the file is written")}.
""")


lesson.code(
    '''
never = """
if False:
    print("this never runs")
print("this does")
"""

print(compiler.what_the_optimizer_did(compiler.stages(never)))
''',
    differs=TRAILING_NONE,
    quiet=True,
)


lesson.md(f"""
Seventeen instructions in and nine out, and the entire body of the `if` is gone.

{figure("the-unreachable-block", "a block with no arrow pointing into it, which is how the compiler finds dead code")}

That picture is the end of the story. Here is the same thing happening on a smaller program:

{animation("a06-the-block-nothing-points-at")}

Watch the arrow into the middle block, and then watch the block.

Each step is dull on its own. `False` is a constant, so `TO_BOOL` folds. `POP_JUMP_IF_FALSE` is now jumping on a known value, so it becomes an ordinary jump and the edge into the middle block goes with it. Then {cite("Python/flowgraph.c:1008-1044@v3.15.0rc1#remove_unreachable")} walks the graph counting how many edges arrive at each block, finds one that nothing points to, and deletes its instructions.

You can check that {lesson.claim("the string inside the if False block is not in the code object's constants table")}.
""")


lesson.code(
    """
print(compile(never, "lesson.py", "exec").co_consts)
""",
    differs=TRAILING_NONE,
    quiet=True,
)


lesson.md(f"""
`'this never runs'` is not in the file. It is not skipped at runtime and not stored and ignored, it was never written down. `False` is still there, the same kind of leftover constant as before.

## What else disappears

Two smaller rewrites are visible in almost every disassembly once you know to look for them. {lesson.claim("A list literal that is only iterated over is built once at compile time and stored as a constant tuple")}, and a handful of very common values are loaded by number rather than out of the table.
""")


lesson.code(
    '''
looping = """
total = 0
for n in [1, 2, 3]:
    total += n
"""

print(compiler.what_the_optimizer_did(compiler.stages(looping)))
''',
    differs="On 3.14 the trailing None is a LOAD_CONST, GET_ITER prints without an argument, and the constant indices shift by one.",
    quiet=True,
)


lesson.md(f"""
On the left, four instructions build the list: load 1, load 2, load 3, `BUILD_LIST 3`. On the right there is one `LOAD_CONST`, because the list is never modified and only iterated over, so the optimizer built it once at compile time and stored it as a constant tuple. Otherwise the interpreter would rebuild the same list every time round the loop.

The other one is `LOAD_COMMON_CONSTANT 7` at the end. That is `None`, and it is not in the constants table either. Twelve values turn up so often that the interpreter keeps them permanently and loads them by number: {cite("Include/internal/pycore_opcode_utils.h:70-83@v3.15.0rc1#CONSTANT_NONE")}. `None`, `True`, `False`, `AssertionError`, the empty string, and a few builtins.

Every function that falls off the end returns `None`, so this saves one constant table entry per function.
""")


lesson.md(f"""
## When the compiler decides not to

Folding trades file size for speed. The answer to `6 * 7` is smaller than the recipe for it, so writing down the answer wins twice, and that stops being true quickly.

Somewhere there has to be a line, and in CPython it is four numbers: {cite("Python/flowgraph.c:1760-1763@v3.15.0rc1#MAX_INT_SIZE")}.

{figure("four-limits", "the four size limits that stop constant folding, with an example either side of each")}

They are exact rather than rules of thumb, so you can find the boundary yourself. {lesson.claim("2 ** 65 is not folded, even though the answer is only a 66 bit number")}.
""")


lesson.code("""
for expression in ["2 ** 64", "2 ** 65", "3 ** 64", "4 ** 64", "'-' * 4096", "'-' * 4097"]:
    verdict = "worked it out now" if compiler.folds(expression) else "left it for later"
    print(f"{expression:14} {verdict}")
""")


lesson.md(f"""
The check is in {cite("Python/flowgraph.c:1810-1829@v3.15.0rc1#const_folding_safe_power")}, and it is arithmetic on the sizes rather than a try and see. A number of `v` bits raised to the power `w` needs about `v * w` bits, so the question is whether that goes over 128.

That estimate is deliberately generous, which explains an answer that otherwise looks arbitrary. `2 ** 65` is a 66 bit number, nowhere near 128, and it does not fold because 2 takes two bits to write down and the estimate is two times 65. Guessing high is the safe direction to be wrong in when what you are avoiding is a program that takes a minute to compile.

The same reasoning says 3 stops at the same exponent as 2, since both take two bits, and 4 stops earlier because it takes three.

Two of the refusals have nothing to do with size. {lesson.claim("1 / 0 is left for runtime because evaluating it raised, and a % on a string is left alone on purpose")}, because `%` on a string is formatting rather than arithmetic and the compiler has no business running it early.
""")


lesson.code("""
for expression in ["7 % 3", "'%s' % 'x'", "1 / 0", "0.1 + 0.2"]:
    verdict = "worked it out now" if compiler.folds(expression) else "left it for later"
    print(f"{expression:14} {verdict}")
""")


lesson.md(f"""
`0.1 + 0.2` folds, and gives the same wrong looking answer you would get at runtime, because it is the same addition on the same floats. Folding never changes what your program computes, which is the one rule the whole thing has to obey.

## The one thing it cannot do

Everything above depends on the compiler knowing both values. {lesson.claim("Folding stops the moment either side of the operator is a name")}.
""")


lesson.code("""
for expression in ["6 * 7", "6 * x", "x * 7"]:
    verdict = "worked it out now" if compiler.folds(expression) else "left it for later"
    print(f"{expression:14} {verdict}")
""")


lesson.md(f"""
This is the honest boundary of a compiler that does not run your program. `x` might be an integer, or a numpy array, or a class with a `__mul__` that sends an email. The compiler has no idea, and cannot have one, because `x` is looked up when the code runs.

That is why pulling a constant expression out of a loop is still worth doing yourself, and why `math.pi` costs more than a local `pi`: an attribute lookup is a whole extra instruction with its own cache.

## The assembler

The graph now has to become a file. That is the third stage, and it builds the parts of a code object that are not instructions. Here are the finished bytes, and {lesson.claim("a code object's bytes come in pairs, one byte of opcode and one byte of argument")}.
""")


lesson.code(
    """
print(compile("answer = 6 * 7", "lesson.py", "exec").co_code.hex(" "))
""",
    differs="On 3.14 this is 10 bytes rather than 12, and the bytes themselves are different, because RESUME has no inline cache and the final None is a LOAD_CONST.",
    quiet=True,
)


lesson.md(f"""
Twelve bytes in pairs. Every instruction is one byte of {term("opcode")} and one byte of {term("oparg", "argument")}, and the third pair reads `2a` on the right, which is 42: the answer to the multiplication, sitting in the file in hexadecimal.

Five instructions is ten bytes, so one pair is unaccounted for, and it is the `00 00` in second place.

{figure("one-instruction", "two bytes per instruction, and the blank cache slots between them")}

Some instructions are followed by blank slots the interpreter writes into while your program runs, remembering what it saw last time so it can guess faster. Those are {term("inline cache", "inline caches")}: real bytes in `co_code`, and the reason offsets in a disassembly jump by four or twenty rather than by two. T06 is about reading that fluently.

{cite("Python/assemble.c:779-802@v3.15.0rc1#_PyAssemble_MakeCodeObject")} is the whole third stage in one function. Apply the label map, turn the jump pseudo instructions into real jumps, work out the byte offsets, emit, and build the code object.

{figure("what-the-assembler-makes", "the fields of a code object, and which ones the assembler builds")}

Two of those fields are built here and nowhere else, and neither of them is in the bytes. The first is the line table: {lesson.claim("a traceback finds its line number by looking a byte offset up in a table that is stored separately from the instructions")}.
""")


lesson.code(
    """
from pyxray import bytecode

for start, end, line in bytecode.line_table("answer = 6 * 7"):
    print(f"bytes {start:>3} to {end:<3} came from line {line}")
""",
    differs="On 3.14 the ranges start two bytes lower, because RESUME has no inline cache there.",
    quiet=True,
)


lesson.md(f"""
That is `co_linetable`, the {term("line table")}: how a traceback knows which line to print, stored separately from the instructions. Since 3.11 it holds column numbers too, which is where the carets under a failing expression come from, and those columns came all the way from the tree in T03.

The second is the exception table, and {lesson.claim("a try block leaves no instruction behind in the bytecode, only an entry in a table")}.
""")


lesson.code(
    '''
faulty = """
try:
    n = 1 / 0
except ZeroDivisionError:
    n = 0
"""

table = compile(faulty, "lesson.py", "exec").co_exceptiontable
print("exception table, in bytes:", len(table))
print(table.hex(" "))
''',
    differs="On 3.14 the table is 12 bytes rather than 16, and the bytes are different. It encodes offsets into the bytecode, and those offsets are different on the two versions.",
    quiet=True,
)


lesson.md("""
That is the whole cost of the `try` block: a few bytes in a table nobody reads unless something goes wrong.

It is also the reason for a piece of advice that otherwise sounds like folklore. Asking forgiveness rather than permission is faster than checking first, because the check costs an instruction every time while the `try` costs nothing until it fires.

## The one part you cannot run here

Everything above runs on the Python you already have. This next bit does not, and it is the only measurement in the lesson that checks what the whole lesson rests on: the compiler throws away everything except the code object.

Checking that means counting every reference in the process, before and after. `sys.getrefcount` needs an object you already have a name for, and the question here is about objects nobody kept a name for. `sys.gettotalrefcount` counts all of them, and it only exists in an interpreter built with `--with-pydebug`, which is a different binary rather than a flag. So the program below was run in the debug build this project publishes, and what it printed is underneath.
""")


lesson.md(recording("t05-compiling-costs-nothing-that-lasts"))


lesson.md("""
The count wobbles by about one when nothing has happened, because taking the measurement is itself Python, so anything in single figures means nothing happened.

The first compile costs three thousand, and that is not a leak. It is interning: the name `answer`, the filename and the constants go into the interpreter's table and are kept on purpose, so the next file that mentions `answer` gets the same string back. It is a one time cost, and the two thousand compiles after it move the total by three.

The last two numbers are the same fact from the other side. A thousand code objects cost about five references each, and dropping them brings all of it back. The code object is what survives, and nothing else the compiler built is still standing.

## Try it yourself

**One.** Find your own folding boundary. `MAX_COLLECTION_SIZE` is 256 items. Work out which repeated tuple is the last one the compiler will build for you, and check with `compiler.folds`.

**Two.** Take a `while True:` loop with a `break` in it and run it through `what_the_optimizer_did`. `True` is a constant, so the test at the top of the loop is decided at compile time and the three instructions that did the testing are gone. Look for the `TO_BOOL` that also disappears in front of the `if`, and work out why it was safe to remove that one too.

**Three.** Compare `x = 1; y = 2; z = x + y` with `z = 1 + 2`. Both look like they should give the same code. Predict which one has an addition in it, then check.
""")


lesson.code(
    '''
experiment = """
x = 1
y = 2
z = x + y
"""

print(compiler.what_the_optimizer_did(compiler.stages(experiment)))
''',
    differs=TRAILING_NONE,
    quiet=True,
)


lesson.md("""
The addition is still there. The compiler can see what `x` and `y` were assigned two lines earlier and does not use it, because at module level another module could have changed either of them in between. The optimizer only ever looks at instructions sitting next to each other in the same block.
""")


lesson.md("""
## Boss fight

Everything above you could follow along with. This part you cannot, and that is the point of it.

`co_varnames` is in the diagram above, described as the frame slots. It is a tuple of names in a fixed order, built by the compiler, and the order is not the order you wrote them in. Here is the fight: work that order out from the source text, for a function you have not seen, without compiling it.

```
cp lessons/t05-the-tree-becomes-bytecode/boss/starter.py answer.py
python lessons/t05-the-tree-becomes-bytecode/grade.py answer.py
```

The starter has a `predict(source)` in it that handles the easy half of the parameters and nothing else. Fill in the rest. The grader hands your function sixteen functions written by hand and forty generated at random, compiles each one itself, and compares. When you are wrong it prints the function, both orderings, and the first slot you disagree about.

You are allowed `ast`. You are not allowed `compile`, `eval`, `exec` or `symtable`, because all four answer the question instead of you. That fence is knee high, and the only person you could fool by stepping over it is you.

The answer is not written down anywhere in this lesson, on purpose. Find the rules by experiment rather than by reading: `compile(source, "<t>", "exec").co_varnames` tells you the truth about any function you can think of, so guess a rule, write the function that would break it, and see who was right. Expect about an hour, expect the try block to surprise you, and expect at least one rule you would never have guessed from the source.

## What just happened

`compile()` is three stages. The code generator writes down what the tree means, one node at a time, with no opinions about it. The optimizer rearranges that into a graph of blocks and improves it. The assembler flattens the graph into bytes and builds the tables.

The multiplication in `6 * 7` happens in the optimizer, in a C function called `fold_const_binop`, while your file is being compiled. It is a real multiplication using the same code your program would have used.

The compiler stops as soon as it does not know a value, which is nearly always the moment a name appears.

Dead code is found by asking a graph question, not by reading the source. A block that nothing points at is deleted, and what was inside it never reaches the file.

Two tables come out of the assembler that are not instructions. One turns a byte offset back into a line and a column, which is what tracebacks are made of. The other turns a byte offset into an exception handler, which is what makes `try` cost nothing until it is needed.

## Where this goes next

There is now a code object, and everything about it has been described from the outside. T06 is about reading one fluently: what the argument to each instruction actually indexes, how the stack rises and falls as you read down a listing, and how to look at a disassembly and know what the interpreter is about to do without running it.

After that, T07 is the loop that runs it.
""")


raise SystemExit(lesson.save())
