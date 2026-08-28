#!/usr/bin/env python
"""T10. The napkin.

The last lesson of the first part. Nothing new is introduced. The reader draws the whole
machine from memory, checks the drawing against a reference diagram, and settles seven
common half truths by running them.

The reference diagram is `the-napkin` in `diagrams.py`. It is the one picture every later
part hangs off, so it is drawn once, here, and pointed at from everywhere else rather than
redrawn slightly differently each time.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of
them. `just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import Lesson
from nbdiagram import Diagrams

lesson = Lesson("t10-the-napkin", "t10")
badge = lesson.badge
cite = lesson.cite
figure = Diagrams("t10-the-napkin").figure

lesson.md(f"""
# T10. The napkin

{badge}

Nine lessons in, you have seen the whole path from a line of text to a result. This lesson has no new material in it. It puts the nine on one page, gives you a way to check what actually stuck, and settles a handful of things you have probably read somewhere that are nearly right.

{figure("where-we-are", "all eight stages of the pipeline, every one of them highlighted")}

Every box is lit this time, because every box has had a lesson. What is left is the arrows between them and one skill that turns out to matter more than any single fact: given a new question about Python, knowing which box to look in.

By the end you will have drawn the machine yourself, compared your drawing against the reference, watched one line of code go through all eight stages in a single cell, and stopped believing four or five things that are not true.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/ceval.c:1212-1218@v3.15.0rc1#_PyEval_EvalFrameDefault`.

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

Everything below was checked against the version this cell prints and against 3.14. Where the two disagree, the lesson says so.
""")


lesson.code("""
import pyxray

pyxray.show()
""")


lesson.md("""
## Draw it first

This is the part that does the work, and it is the part that is easiest to skip. Please do not skip it.

Stop scrolling. Get a piece of paper, or open whatever you draw in. Give yourself ten minutes and draw the machine from memory. Do not look anything up and do not scroll down, because the reference picture is a few paragraphs below and seeing it first turns this from a test into a copying exercise.

Here are the questions to answer with your drawing. No answers underneath them, on purpose.

What happens between you saving a file and the first line of it running? Put the stages in order and give each one a shape.

Which of those stages happen once, and which happen over and over? Draw a line between the two groups.

What is the one thing that gets carried across that line?

Once the second group starts, what does it do, in a loop, forever? Name the steps.

Underneath all of it, what does every single value in the program have in front of it, and what are the two fields you would find there?

When is a value's memory given back, and what is the one shape where that never happens on its own?

Ten minutes. Then come back.
""")


lesson.md(f"""
## The reference

Here is the same machine drawn by someone who has been staring at it for nine lessons.

{figure("the-napkin", "the whole machine on one page, in three bands: compile time, run time, and the object model underneath both")}

Three bands, and it is worth being precise about what each one is.

The top band runs once per source file. Text goes in on the left, a code object comes out on the right, and the six steps between are the six lessons T02 through T07. The tokenizer is at {cite("Parser/lexer/lexer.c:1626-1635@v3.15.0rc1#_PyTokenizer_Get")}, the parser at {cite("Parser/pegen.c:938-941@v3.15.0rc1#_PyPegen_run_parser")}, the symbol table at {cite("Python/symtable.c:415-418@v3.15.0rc1#_PySymtable_Build")}, code generation at {cite("Python/codegen.c:894-897@v3.15.0rc1#_PyCodegen_Expression")}, the optimizer at {cite("Python/flowgraph.c:3753-3757@v3.15.0rc1#_PyCfg_OptimizeCodeUnit")}, and the code object gets built at {cite("Objects/codeobject.c:715-718@v3.15.0rc1#_PyCode_New")}. If you want to see the whole top band as one function, it is {cite("Python/compile.c:1526-1540@v3.15.0rc1#_PyAST_Compile")}, which is about fifteen lines long and calls each stage in turn.

The middle band runs once per instruction, which in a real program means millions of times. It reads two bytes, works out which handler that opcode maps to, runs it, and moves on. That is the whole loop, and it lives in one enormous function at {cite("Python/ceval.c:1212-1218@v3.15.0rc1#_PyEval_EvalFrameDefault")}.

The bottom band is not a stage at all. It is what every value in both other bands is made of: a header with a reference count and a type pointer, at {cite("Include/object.h:127-150@v3.15.0rc1#_object")}. When the count reaches zero the object is freed on the spot, at {cite("Include/refcount.h:417-429@v3.15.0rc1#Py_DECREF")}. When objects hold each other in a loop the count never reaches zero, and the cycle collector deals with that separately, using the subtraction trick at {cite("Python/gc.c:485-501@v3.15.0rc1#subtract_refs")}.

Now compare that against what you drew. The next section is a checklist for exactly that.
""")


lesson.md(f"""
## Checking your drawing

{figure("the-checklist", "nine rows, each naming something the drawing should have and the lesson to reread if it does not")}

Nine rows, one per lesson. Go down them and tick the ones your drawing already had.

A gap is not a failure. It is a pointer. The material is short and rereading one lesson takes twenty minutes, which is a much better use of your time than pushing on and building the next six parts on a foundation with a hole in it.

If you ticked all nine, you are done with the first part.
""")


lesson.md(f"""
## The line that matters most

Of everything on the napkin, one line does more work than the rest: the one between compile time and run time.

{figure("the-boundary", "compile time and run time side by side, with four differences listed under each")}

Almost every confusing thing about Python is a question that got asked on the wrong side of this line. Why can I not use a variable before assigning it, even in a branch that never runs? Compile time. Why is this attribute lookup slow? Run time. Why does the same expression give a different answer in a function than at the module level? Compile time, and specifically the symbol table.

The important part is what crosses. A code object crosses. Nothing else does. The tokens, the tree, the symbol table and the flow graph are all built, used, and thrown away before your program runs a single instruction. Whatever the compiler worked out that did not get written into the code object is simply gone.

You can watch that happen. The next cell compiles a function, throws away the source text entirely, and runs what is left.
""")


lesson.code("""
import marshal


def crossing():
    \"\"\"Compile a function, destroy the source, and see what is still there.\"\"\"
    source = "def area(width, height):\\n    total = width * height\\n    return total\\n"
    module = compile(source, "<gone>", "exec")

    blob = marshal.dumps(module)
    del source, module
    print("the code object as bytes:", len(blob), "and the source text no longer exists")

    space = {}
    exec(marshal.loads(blob), space)
    area = space["area"]
    print("it still runs:", area(6, 7))

    inner = area.__code__
    print()
    print("what the compiler decided, written down and still readable:")
    print("   co_varnames: ", inner.co_varnames)
    print("   co_argcount: ", inner.co_argcount)
    print("   co_stacksize:", inner.co_stacksize)
    print()
    print("what did not cross: the source text, the tokens, the tree, the symbol")
    print("table, and the flow graph. None of them exist any more, anywhere.")


crossing()
""")


lesson.md("""
`co_stacksize` is a good example of the general rule. The compiler walked the flow graph, worked out the deepest the value stack could ever get in this function, wrote the number down, and threw the graph away. At run time nobody recomputes it. The frame is allocated that big and the loop trusts the number.

That is the shape of almost everything the compiler does: work it out once, write down the answer, throw away the working.
""")


lesson.md(f"""
## One line, all the way through

Here is `answer = 6 * 7` at every stage, in a single cell. It is the same eight boxes as the top row of the napkin plus the run, printed one after another.

{figure("one-line-all-the-way", "the eight stages for answer = 6 * 7, with the real artefact and its size at each box")}
""")


lesson.code("""
import ast
import symtable
import tokenize

from pyxray import compiler

SOURCE = "answer = 6 * 7\\n"


def walk_it():
    \"\"\"Every stage of the napkin, for one line, printed one after the other.\"\"\"
    print("1. your file")
    print("   ", SOURCE.strip())

    print("2. tokens")
    print("   ", " ".join(tokenize.tok_name[t.type] for t in compiler.tokens(SOURCE)))

    print("3. syntax tree")
    print("   ", ast.dump(ast.parse(SOURCE)))

    print("4. symbol table")
    for symbol in symtable.symtable(SOURCE, "<napkin>", "exec").get_symbols():
        print("    name:", symbol.get_name(), " global:", symbol.is_global())

    run = compiler.stages(SOURCE)

    print("5. instructions, straight out of codegen")
    for row in run.codegen:
        print("   ", row.opname, "" if row.arg is None else row.arg)

    print("6. the same list, after the optimizer")
    for row in run.optimized:
        print("   ", row.opname, "" if row.arg is None else row.arg)

    print("7. the code object")
    print("    co_consts:", run.code.co_consts)
    print("    co_names: ", run.code.co_names)

    print("8. the answer")
    space = {}
    exec(run.code, space)
    print("    answer =", space["answer"])


walk_it()
""")


lesson.md("""
Two things in that output are worth stopping on.

Step five has a `BINARY_OP` in it and step six does not. The multiplication was done by the compiler, and the running program never multiplies anything. That is the shortest available proof that the compiler is doing real work rather than just translating.

Step seven still has a `6` sitting in `co_consts`, and nothing ever loads it. Codegen put it there when it was still planning to emit `LOAD_CONST 6`, then the optimizer folded the expression into a single `42` and left the constant table alone. Nobody goes back to tidy up. It is a small piece of dead weight in every code object that contains a folded constant, and it is the kind of thing you only ever find by looking.

If you are on 3.14 the last instruction differs slightly, because 3.15 moved `None` out of the constant table and into `LOAD_COMMON_CONSTANT`. Everything else is the same on both.
""")


lesson.md(f"""
## Seven things that are nearly right

{figure("wrong-models", "seven common claims about Python, each with what is actually true beside it")}

Every one of these is a sentence you will have read somewhere, probably more than once. Each is wrong in a way that changes what you would predict. The next two cells settle four of them by running them.
""")


lesson.code("""
import dis
import gc

from pyxray import heap


class Thing:
    \"\"\"Something we can hang a weak reference on, which a list will not allow.\"\"\"


def settle():
    \"\"\"Four of the seven claims, settled by running them.\"\"\"
    print("1. is Python interpreted rather than compiled?")
    code = compile("answer = 6 * 7", "<nothing on disk>", "exec")
    print("   compile() with no file involved gave", len(code.co_code), "bytes of bytecode")

    print()
    print("4. are local names looked up in a dict?")

    def uses_a_local():
        thing = 1
        return thing

    print("   opcodes:", ", ".join(i.opname for i in dis.get_instructions(uses_a_local)))
    print("   co_varnames:", uses_a_local.__code__.co_varnames)

    print()
    print("5. does the garbage collector free your objects?")
    watcher = heap.Deaths()
    plain = watcher.watch("plain", Thing())
    gc.disable()
    del plain
    gc.enable()
    print("   freed with the collector switched off:", watcher.gone)

    print()
    print("6. does del free the object?")
    watcher = heap.Deaths()
    named = watcher.watch("named", Thing())
    second_name = named
    del named
    print("   after del, still alive:", watcher.alive("named"))
    print("   because second_name still holds it:", second_name is not None)


gc.collect()
settle()
""")


lesson.md("""
Read those four in order.

There is no file on disk anywhere in the first one, and bytecode came out of it. The `.pyc` file is a cache of that result so the work can be skipped next time. Deleting your `__pycache__` directory changes nothing except how long the next import takes.

The local in the second one is `STORE_FAST` and `LOAD_FAST_BORROW`, both of which take a slot number, not a name. The name `thing` is in `co_varnames` purely so a debugger and a traceback have something to print. There is no dictionary anywhere near it.

The third one freed an object with the collector switched off, which it can do because the collector had nothing to do with it. The reference count went to zero and the object was freed immediately. That is how almost every object in your program dies.

The fourth one shows `del` doing what it actually does, which is remove one name. The object was still there afterwards, because another name was holding it.
""")


lesson.md("""
The `257 is 257` one deserves its own cell, because the usual explanation of it is wrong in an interesting way.
""")


lesson.code("""
a = 257
b = 257
print("two names, same source file:", a is b)

built = int("257")
again = int("257")
print("built one at a time:      ", built is again)
""")


lesson.md("""
The first line is `True` on every version, and the small integer cache has nothing to do with it. Both `257` literals are in the same code object, and the compiler stores each distinct constant once, so both names point at the same entry in `co_consts`. That would be true for `257000000` as well.

The second line is where the cache actually shows up, and this is the version difference. Building the integers one at a time from a string keeps the compiler out of it. On 3.14 you get `False`, because the cache stops at 256. On 3.15 you get `True`, because it now goes to 1024. Every tutorial that hard coded 256 stopped being correct without its author being told, which is the whole reason this project measures things instead of quoting them.

The last claim on the table, that freeing memory shrinks the process, is T09's territory. Short version: the block goes back to a pool, the pool goes back to an arena, and the arena goes back to the operating system only when every pool inside it is empty. That last condition is rarely met.
""")


lesson.md(f"""
## Everything you can print, with nothing installed

{figure("what-you-can-print", "seven stages and the one call that shows each of them")}

This table is the argument the whole project rests on, so it is worth saying out loud.

Every stage of CPython's front end is inspectable from Python, at run time, with the standard library. No debug build. No C compiler. No patched interpreter. No `gdb`. You can print the tokens, the tree, the scopes, the instructions before optimization, the instructions after, and the finished code object, from a browser tab on a laptop you do not have admin on.

The two rows that use `pyxray` are conveniences, not requirements. `compiler.stages` wraps `_testinternalcapi`, which ships in a normal CPython build and is how the compiler's own test suite drives it. `stepper.run` wraps `sys.monitoring`, which has been public since 3.12.

If you take one thing from this part, take that. The machine is not hidden. Most people just have never been shown where the handles are.
""")


lesson.md(f"""
## Where the rest of this goes

{figure("what-comes-next", "the napkin at the root, with the six later parts hanging off it")}

Six parts left, and every one of them opens a single box on the napkin.

The front end part goes back to T02 and T03 and does them properly: the real PEG parser with its backtracking and its memo table, how the error messages get generated, and what an f-string actually parses into.

The compiler part opens the box between codegen and the code object. The flow graph, what the optimizer will and will not do for you, and why it will fold `6 * 7` but not `x * 1`.

The interpreter part is the biggest, because the middle band of the napkin is where all the performance work of the last five years has gone. Specialization, the tier two optimizer, and the JIT.

The objects part opens the bottom band. Types and slots, how a dict is actually laid out, and what really happens on an attribute lookup.

The runtime part covers the things that happen around your program rather than in it: import, startup, and the C API.

The concurrency part is the GIL, free threading, and subinterpreters.

Nothing after this introduces a stage that the napkin does not already have a box for. That is what makes it useful: a new question is not a new topic, it is a box, and knowing the box is most of the work.
""")


lesson.md("""
## Try it yourself

**One.** Redraw the napkin from memory a week from now, without looking at it, and compare. The gaps after a week are the things you learned rather than the things you read.

**Two.** Take a piece of code you actually wrote recently, pick one line, and run it through `walk_it` above. Most real lines produce output that is more interesting than `answer = 6 * 7`, especially anything with a function call or an attribute access in it.

**Three.** Pick three questions about Python you have never known the answer to, and for each one write down which box on the napkin the answer lives in. You do not have to answer them. Placing them is the exercise, and the ones you cannot place are usually the ones about import or the C API, which is the runtime box.

**Four.** Find a sentence about Python internals on a blog or in an answer somewhere, and decide whether it is on the wrong side of the compile time line. This is the single most common way that otherwise good explanations go wrong.

**Five.** `marshal.dumps` gave a code object as bytes in the crossing cell above. Write those bytes to a file, load them in a fresh interpreter, and run the function. Then explain to somebody why this is exactly what a `.pyc` file is and what the extra header on a real one is for.
""")


lesson.md("""
## What just happened

You drew the machine, and then you checked the drawing. If there were gaps, you now know which lesson each gap points at, which is more useful than the drawing was.

The machine is three bands. The top one runs once per file and turns text into a code object through six stages. The middle one runs once per instruction and reads, dispatches, executes, and repeats. The bottom one is the header in front of every value the other two touch, with a count that frees the object the moment it hits zero and a collector for the one shape where it never does.

One thing crosses from the top band to the middle one, and that is the code object. Everything else the compiler built is thrown away, so anything it worked out that did not get written down is unrecoverable at run time.

Several things you have read about Python are nearly right. Python compiles. Locals are slots, not dictionary keys. Reference counting does almost all the freeing, and the collector handles cycles and nothing else. `del` removes a name.

And all of it is printable from an ordinary Python prompt with the standard library, which is why this material can be a notebook rather than a build environment.

## Where this goes next

That is the first part finished. You have a map, and the rest of the material fills it in.

Part two goes back to the front end and does the parser properly. T02 gave you a token stream and T03 gave you a tree, but the thing in between is a PEG parser with backtracking, a memo table, and a rather clever approach to error messages, and it is the piece of CPython most people have never looked at.
""")


raise SystemExit(lesson.save())
