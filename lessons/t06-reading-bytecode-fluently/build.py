#!/usr/bin/env python
"""T06. Reading bytecode fluently.

T05 finished with a code object and described it from the outside. This lesson is about
reading one. Nothing new gets built here, which makes it the odd lesson out in the first
part, and it is the one that everything after it depends on.

The spine of the lesson is a Python reimplementation of `calculate_stackdepth` from
`Python/flowgraph.c`, in `pyxray/src/pyxray/stack.py`. It agrees with `co_stacksize` on
every code object in the standard library, and the reader gets to run that sweep. That is
the strongest evidence in the repository so far that these lessons describe the rules
accurately rather than approximately, and it is worth more than another paragraph claiming
the same thing.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of
them. `just lessons` checks that the committed notebook still matches this file.

The pictures come from `diagrams.py` in this directory. They are looked up on disk rather
than imported, so a diagram that has not been built yet fails here instead of producing a
notebook full of broken images.
"""

from nbbuild import BANNER, OFFSETS, YOUR_INSTALL, Lesson
from nbdiagram import Diagrams

lesson = Lesson("t06-reading-bytecode-fluently", "t06")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("t06-reading-bytecode-fluently").figure

lesson.md(f"""
# T06. Reading bytecode fluently

{badge}

Five lessons in, you have seen a lot of disassembly listings. Most people read them the way they read a foreign language they half know, picking out the words they recognise and guessing the rest. This lesson is about not having to guess.

{figure("where-we-are", "the eight stages of running Python, with the code object highlighted")}

Nothing new gets built here. T05 handed us a {term("code object")} and described it from the outside, and this is where you learn to read what is inside one, so that from T07 onwards you can look at a listing and know what the interpreter is about to do without running it.

There are four things to learn and they are all small: what the argument byte means, which is a different answer for every instruction, how the stack rises and falls as you read down the page, how jumps count, and which bytes `dis` does not show you.

No C required, and everything here runs on a normal Python.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/flowgraph.c:815-852@v3.15.0rc1#calculate_stackdepth`.

Read it as four parts: the file, the lines, the release those line numbers belong to, and the name of the function they are inside.

Every reference is a link, and every one is checked against the pinned source on each change, so a stale reference fails the build instead of sending you somewhere wrong. The function name on the end is what makes the check work. Line numbers move whenever somebody adds code above them, and a moved line number points at something that looks plausible and is not.

You never have to read any of it. The references are there so you can go deeper when you want to, and so you can check that this lesson is not making things up.

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

Instruction names change between releases more than almost anything else in CPython. Half the opcodes in the listings below did not exist three releases ago. Everything here was checked against the version this cell prints, and if yours is different the shapes will still be right even where the names are not.

It was also checked against 3.14, which is what Colab installs today, and one difference shows up in almost every listing. On 3.15 `RESUME` and `GET_ITER` carry an inline cache slot and on 3.14 they do not, so on 3.14 every offset below is two to four lower than the number in the text. Nothing else about the listing changes. Where a cell differs for some other reason, it says so underneath.
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
## One place to put things

The interpreter is a stack machine. There is no `add r1, r2, r3` anywhere in it, there is a {term("value stack")}, and instructions push values onto it and pop values off it. That is the whole model.

It sounds limiting until you see how little you need. Below is `total = total + n`, one instruction at a time, with the stack drawn next to each one.

{figure("the-stack-rising", "the stack after each instruction of total = total + n")}

Two loads push, the addition pops two and pushes one, and the store pops the last one. {lesson.claim("a line like total = total + 1 pushes two values, replaces them with one, and leaves the stack as empty as it found it")}, and the highest point in the middle is `co_stacksize`, which the interpreter uses to work out how much room to reserve for the {term("frame")} before it starts.

Every listing you read from here on is that shape. The trick to reading one fluently is to stop reading the instruction names and start reading what happens to the stack.
""")


lesson.code(
    """
from pyxray import stack

print(stack.table("total = 0\\ntotal = total + 1"))
""",
    differs=OFFSETS,
    quiet=True,
)


lesson.md("""
The two numbers are the height before the instruction and after it. The dots on the right are the same thing as a picture, one mark per value sitting on the stack.

`RESUME` at the top does nothing to the stack. It is a marker the interpreter uses for tracing and for restarting generators, and it is the first instruction of every code object CPython compiles.

## Two bytes, and no more
""")


lesson.md(f"""
An {term("instruction")} is two bytes. One byte is the {term("opcode")}, which says what to do, and one byte is the {term("oparg", "argument")}, which says what to do it to.

{figure("two-bytes", "one instruction: an opcode byte and an argument byte")}

That is the whole encoding, and CPython says so in a comment on the type: {cite("Include/internal/pycore_structs.h:17-32@v3.15.0rc1#_Py_CODEUNIT")}.

`_Py_CODEUNIT` is a union, so reading it one way gives a 16 bit number and reading it another way gives the two fields. Fixed width instructions are why the interpreter can step forward without decoding anything first, and why {lesson.claim("every offset in a listing is even: the bytes of a code object come in pairs and there is nothing else in there")}.

The next cell pulls the real bytes out of a code object so you can see there is nothing else in there.
""")


lesson.code(
    """
import opcode

code = compile("print(total)", "lesson.py", "exec")

print("the whole thing, in hex:")
print(code.co_code.hex(" "))
print()
for offset in range(0, 8, 2):
    opcode_byte, argument_byte = code.co_code[offset], code.co_code[offset + 1]
    print(f"{offset:>3}  {opcode_byte:>3} {argument_byte:>3}   {opcode.opname[opcode_byte]}")
""",
    differs="On 3.14 RESUME has no cache entry, so the second row is LOAD_NAME rather than CACHE and every offset after it is two lower.",
    quiet=True,
)


lesson.md(f"""
## The same number, six meanings

The thing that stops most people the first time is that `LOAD_CONST 1` and `LOAD_NAME 1` and `CALL 1` all print the same way, and the 1 means three unrelated things.

{figure("one-argument-six-meanings", "the argument 1, and the six different things it can mean")}

There is no rule you can apply from the outside. {lesson.claim("the same argument byte means a different thing for every instruction, and which thing is published by the opcode module rather than worked out from the number")}. The lists are `hasconst`, `hasname`, `haslocal`, `hasfree`, `hasjrel`, `hascompare` and `hasexc`, and everything else with an argument treats it as a plain number that instruction knows what to do with.
""")


lesson.code("""
from pyxray import bytecode

for name in ["LOAD_CONST", "LOAD_NAME", "LOAD_FAST", "LOAD_SMALL_INT", "CALL", "JUMP_FORWARD"]:
    print(f"{name:<16} {bytecode.argument_meaning(name)}")
""")


lesson.md("""
`LOAD_SMALL_INT` is the odd one and worth knowing about, because it turns up constantly. Its argument is not an index into anything, it is the number itself. Small integers are so common that CPython gave them an instruction that carries the value in the argument byte rather than spending a slot in `co_consts` on every 0 and 1 in your program.

That is also why the folded `6 * 7` from T05 came out as a `LOAD_CONST` rather than a `LOAD_SMALL_INT`. 42 fits in a byte, but the instruction is chosen while the tree is being walked, before the folding happens.

Now run it over a real listing and read the meanings down the right hand side.
""")


lesson.code(
    """
def greet(name):
    return "hello " + name


for item in bytecode.disassemble(greet):
    meaning = "" if item.arg is None else bytecode.argument_meaning(item.opname)
    argument = "" if item.arg is None else str(item.arg)
    print(f"{item.offset:>4}  {item.opname:<20} {argument:>4}  {meaning}")
""",
    differs=OFFSETS,
    quiet=True,
)


lesson.md(f"""
## One byte, split in half

A few instructions do two things at once, and they fit two arguments into the one byte by using four bits each. It looks like a mistake in the listing the first time you see it, because `LOAD_FAST_LOAD_FAST 18` loads slot 1 and slot 2 and 18 is neither of those.

18 in binary is `0001 0010`. The top half is 1, the bottom half is 2. The C is exactly that: {cite("Python/bytecodes.c:305-310@v3.15.0rc1#LOAD_FAST_BORROW_LOAD_FAST_BORROW")}, which shifts right by four for the first slot and masks with 15 for the second.

Four bits holds 0 to 15, so this only works for the first sixteen locals. A function with more than sixteen locals gets ordinary separate loads for anything past the sixteenth. {lesson.claim("a packed load carries two slot numbers in one byte, four bits each, so the argument 18 means slots 1 and 2")}.
""")


lesson.code("""
def two_at_once(first, second, third, fourth):
    return first + second, third + fourth


names = two_at_once.__code__.co_varnames

for item in bytecode.disassemble(two_at_once):
    if item.opname.count("LOAD_FAST") == 2:
        first_slot, second_slot = item.arg >> 4, item.arg & 15
        print(f"argument {item.arg:>3} is slots {first_slot} and {second_slot}", end=", ")
        print(f"which are {names[first_slot]} and {names[second_slot]}")
""")


lesson.md(f"""
## When one byte is not enough

One byte holds 0 to 255. Plenty of files have more than 256 names in them, and plenty of jumps are longer than 255 instructions. The way out is {term("EXTENDED_ARG")}, an instruction whose only job is to carry the bits that did not fit.

{figure("extended-arg", "four real bytes from a file with 300 names in it")}

{lesson.claim("an argument bigger than 255 is carried by an EXTENDED_ARG in front of the instruction, which shifts what it holds left by eight and adds the next argument on")}: {cite("Python/bytecodes.c:6092-6098@v3.15.0rc1#EXTENDED_ARG")}. Up to three of them can stack in front of one instruction, which gets you a 32 bit argument, and that limit is stated in the comment on `_Py_CODEUNIT` above.

The next cell builds a file with 300 names in it and finds the four bytes from the picture.
""")


lesson.code(
    """
import dis

crowded = "\\n".join(f"a{i} = {i}" for i in range(300)) + "\\nprint(a256)\\n"
code = compile(crowded, "lesson.py", "exec")

items = list(dis.get_instructions(code))
for index, item in enumerate(items):
    if item.opname == "EXTENDED_ARG" and items[index + 1].opname == "LOAD_NAME":
        following = items[index + 1]
        print("bytes at", item.offset, ":", code.co_code[item.offset : item.offset + 4].hex(" "))
        print(f"{item.arg} * 256 + {following.arg % 256} = {following.arg}")
        print("co_names[" + str(following.arg) + "] is", code.co_names[following.arg])
        break
""",
    differs=OFFSETS,
    quiet=True,
)


lesson.md("""
`print` ended up as name number 300 because 300 other names were written down first. It is the same `print` you use every day, and reaching it takes an extra instruction in this file and not in any of your other files.

That also answers a question people hit when they first meet `dis`. Offsets in a listing are the offsets of the real instruction, and an `EXTENDED_ARG` in front of it occupies two of them, so the instruction you are looking at does not start where you expected. `dis` prints the `EXTENDED_ARG` rows, so you can always account for the difference.

## The offsets skip numbers
""")


lesson.md(f"""
The other reason offsets do not go 0, 2, 4, 6 is that some instructions are followed by blank slots.

{figure("what-dis-does-not-show", "what dis prints, next to what is actually in co_code")}

Those slots are {term("inline cache", "inline caches")}. The interpreter writes into them while your program runs, remembering what it saw last time so it can take a faster path next time. {lesson.claim("inline caches are real bytes in co_code that the offsets step over, and dis leaves them out of a listing unless you ask for them")}.

They stop being noise as soon as you count jumps by hand, which is the next section, so the cell below prints them.
""")


lesson.code(
    '''
loop = """
total = 0
for n in [1, 2, 3]:
    total = total + n
print(total)
"""

print(bytecode.table(loop, show_caches=True))
''',
    differs=OFFSETS,
    quiet=True,
)


lesson.md(f"""
`BINARY_OP` carries five cache slots, so the next instruction is twelve bytes further on rather than two. `CALL` carries three. `FOR_ITER`, `GET_ITER`, `RESUME` and `JUMP_BACKWARD` carry one each.

## Jumps count instructions, not bytes

This is the part that catches everybody out. A jump argument is not a byte offset and it is not an absolute address, it is a count of instructions, forwards or backwards, from where the interpreter would have gone next.

{figure("counting-a-jump", "the JUMP_BACKWARD at the end of a loop, and where the 14 comes from")}

Two separate adjustments are hiding in that. {lesson.claim("a jump argument counts instructions rather than bytes, and it counts from after the jump including the jump's own cache slot")}, so getting from the argument to an offset means multiplying by two and starting from a place that is further on than the jump.

The macro that does it is one line: {cite("Python/ceval_macros.h:256-261@v3.15.0rc1#JUMPBY")}. It adds to `next_instr`, and {lesson.claim("the interpreter never multiplies a jump by two, because next_instr points at a two byte unit and C's pointer arithmetic does the doubling", unobservable="the doubling is in the type of a C pointer, and the only thing that reaches Python is the finished offset")}.
""")


lesson.code(
    """
print(bytecode.jump_table(loop))
""",
    differs=OFFSETS,
    quiet=True,
)


lesson.md(f"""
The `JUMP_BACKWARD` sits at byte 38 with a cache slot at 40, so the interpreter is at 42 when the jump happens, and 42 minus 28 is 14, which is the `FOR_ITER` at the top of the loop.

`FOR_ITER` jumps forward to 42, which is the instruction right after the `JUMP_BACKWARD`. That is what makes a loop a loop: the exit and the back edge point at each other.

One thing worth knowing if you learned this on an older Python: absolute jumps are gone. {lesson.claim("there are no absolute jumps left at all, and every jump instruction is relative")}, and the next cell checks that rather than asking you to believe it.
""")


lesson.code("""
print("absolute jumps:", len(opcode.hasjabs))
print("relative jumps:", len(opcode.hasjrel))
print(sorted(opcode.opname[number] for number in opcode.hasjrel))
""")


lesson.md(f"""
## How tall does the stack get

`co_stacksize` is the number the interpreter uses to reserve room for the frame. Getting it wrong in either direction hurts: too small and the interpreter writes past the end of the frame, too large and every call wastes memory.

The compiler works it out by walking the instructions and following every path.

{figure("how-tall-does-it-get", "walking both sides of a branch and keeping the taller one")}

The rule is in the comment at the top of the function: {cite("Python/flowgraph.c:815-852@v3.15.0rc1#calculate_stackdepth")}. Start at the entry with an empty stack, follow every edge, and when two paths reach the same instruction keep the deeper one. The answer is the deepest the walk ever got.

The comment also says the assumption that makes it terminate: cycles in the flow graph have no net effect on the stack depth. A loop that pushed one value per pass and never popped it would have no answer, and the compiler rejects such code long before this point.

Each instruction's {term("stack effect")} comes from two generated tables, `_PyOpcode_num_popped` and `_PyOpcode_num_pushed`, declared at {cite("Include/internal/pycore_opcode_metadata.h:35-38@v3.15.0rc1#_PyOpcode_num_popped")} and filled in from the stack signatures written on each instruction in `Python/bytecodes.c`. The compiler reads them through {cite("Python/flowgraph.c:772-798@v3.15.0rc1#get_stack_effects")}, and {lesson.claim("how many values an instruction pops and pushes is written down for every one of them, and dis.stack_effect hands back the net of the two")}.
""")


lesson.code(
    """
for name in ["GET_ITER", "BINARY_OP", "END_FOR", "POP_ITER"]:
    number = opcode.opmap[name]
    argument = 0 if number >= opcode.HAVE_ARGUMENT else None
    print(f"{name:<12} {dis.stack_effect(number, argument):>3}")
""",
    differs="On 3.14 GET_ITER is 0 and POP_ITER is -1. In 3.15 GET_ITER leaves one more item on the stack than it takes, and POP_ITER takes that extra item away again.",
)


lesson.md(f"""
`POP_ITER` takes two off. That is the iterator and the value under it, which is how a `for` loop tidies up after itself.

## The same walk, in Python

`pyxray.stack` is that walk, reimplemented in Python in about forty lines. It is short enough to read in one sitting, and reading it is the surest way to know you have understood the rule.

One thing in it is not obvious from the description above. A `try` block has entry points that no instruction jumps to. The interpreter reaches them by looking up the {term("exception table")}, so the walk has to seed them separately and at the right height. The table is a list of five tuples: {cite("InternalDocs/exception_handling.md:108-118@v3.15.0rc1#exception")}. The height we want is the recorded depth, plus one if the handler asked for the instruction pointer to be pushed, plus one for the exception itself. That last plus one is easy to miss, and missing it is how the first version of this came out one short on 847 code objects.

The pseudocode the interpreter follows when something is raised is at {cite("InternalDocs/exception_handling.md:80-95@v3.15.0rc1#exception")}, and it is the clearest paragraph in CPython's internal docs. {lesson.claim("a handler starts at a stack height the instruction above it did not leave behind, because nothing falls into a handler from the line above")}.
""")


lesson.code(
    '''
guarded = """
try:
    value = int("x")
except ValueError:
    value = 0
"""

print(stack.table(guarded))
''',
    differs=OFFSETS,
    quiet=True,
)


lesson.md(f"""
Look at the row where the handler starts. The instruction above it ended at one height and this one begins at a different one, which looks like a mistake until you remember the listing is in address order. The only way to reach a handler is to raise.

## Checking the claim

A lesson can tell you a rule is right, and checking is better.

The next cell compiles a chunk of the standard library, walks every code object in it with the Python version of the rule, and compares against the `co_stacksize` that CPython itself worked out in C. {lesson.claim("the Python version of the stack depth rule in this lesson agrees with CPython's own co_stacksize on every code object it is run over")}, so every disagreement is a bug in this lesson.
""")


lesson.code(
    """
import sysconfig
import types
from pathlib import Path

root = Path(sysconfig.get_paths()["stdlib"])
files = [path for path in sorted(root.rglob("*.py")) if "test" not in path.parts][:150]


def every_code_object(code):
    pending = [code]
    while pending:
        current = pending.pop()
        yield current
        pending.extend(k for k in current.co_consts if isinstance(k, types.CodeType))


checked = disagreed = 0
for path in files:
    try:
        top = compile(path.read_text(encoding="utf-8"), str(path), "exec")
    except SyntaxError, UnicodeDecodeError, ValueError:
        continue
    for code_object in every_code_object(top):
        checked += 1
        disagreed += stack.high_water(code_object) != code_object.co_stacksize

print(f"{len(files)} files, {checked} code objects, {disagreed} disagreements")
""",
    varies=YOUR_INSTALL,
)


lesson.md(f"""
It found no disagreements. Run it over the whole standard library rather than the first 150 files and it still finds none, across thirty three thousand code objects.

That is what this project means when it says you could reimplement CPython from these lessons. The rule has been written down twice, once in C by the people who maintain the compiler and once in Python here, and the two agree everywhere anybody has looked.

## The floor of one

There is one special case worth knowing about, because you will hit it and wonder what went wrong: {lesson.claim("a function that never pushes anything still reports a stack size of one, because a computed zero is bumped up to one")}.
""")


lesson.code("""
def only_raises():
    raise


print("stack size:", only_raises.__code__.co_stacksize)
print("highest the walk ever got:", stack.high_water(only_raises))
""")


lesson.md(f"""
Nothing is ever pushed in that function, so the honest answer is zero, and CPython says one.

The reason is three lines in the constructor: {cite("Objects/codeobject.c:510-519@v3.15.0rc1#init_code")}. If the computed size is zero it is bumped to one. Frames with no room at all are a special case that other code would have to keep checking for, and buying that away for one pointer per frame is cheap.

It is a small thing, and the kind of small thing that matters if you ever write a Python implementation of your own. The rule is not "the highest the stack gets", it is "the highest the stack gets, or one, whichever is more".

## Reading a listing cold

Time to put it together. Below is a function you have not seen, disassembled, with the source in a cell after it. Try to work out what it does first.

{figure("reading-a-listing-cold", "the four questions, in the order that works")}

The order matters, because nobody reads a disassembly top to bottom. Look at what gets loaded, then what happens to it, then where it ends up, and only then sort out the jumps.
""")


lesson.code('''
listing = """
  0  RESUME                              0
  4  LOAD_SMALL_INT                      0
  6  STORE_FAST                          1  total
  8  LOAD_FAST                           0  items
 10  GET_ITER
 14  FOR_ITER                           20  to 58
 18  STORE_FAST                          2  item
 20  LOAD_FAST_BORROW                    2  item
 22  LOAD_SMALL_INT                      0
 24  COMPARE_OP                        148  bool(>)
 28  POP_JUMP_IF_TRUE                    3  to 38
 32  NOT_TAKEN
 34  JUMP_BACKWARD                      12  to 14
 38  LOAD_FAST_BORROW_LOAD_FAST_BORROW   18  total, item
 40  BINARY_OP                           0  +
 52  STORE_FAST                          1  total
 54  JUMP_BACKWARD                      22  to 14
 58  END_FOR
 60  POP_ITER
 62  LOAD_FAST_BORROW                    1  total
 64  RETURN_VALUE
"""

print(listing)
''')


lesson.md(f"""
Work through it with the four questions.

Loaded: one argument called `items`, two locals called `total` and `item`, and the number 0 twice.

Done to it: a comparison against 0, and an addition.

Where it goes: `total` is stored at the start and stored again after the addition, and it is what comes back at the end.

What happens next: `FOR_ITER` at 14 exits to 58, so 14 to 58 is a loop. `POP_JUMP_IF_TRUE` at 28 skips over the `JUMP_BACKWARD` at 34, so failing the test goes back to the top of the loop and passing it falls through to the addition.

That is a loop over `items` that adds up the ones greater than zero. The `18` on the packed load is slots 1 and 2, which are `total` and `item`, exactly as the two halves of the byte say.

Run the next cell for the source and check. {lesson.claim("a listing on its own is enough to work out what a function does, and the source it was compiled from agrees")}.
""")


lesson.code(
    """
def add_up_the_positive_ones(items):
    total = 0
    for item in items:
        if item > 0:
            total = total + item
    return total


print(bytecode.table(add_up_the_positive_ones))
""",
    differs=OFFSETS,
    quiet=True,
)


lesson.md("""
One row in there is worth a second look. `RETURN_VALUE` has a stack effect of zero, which cannot be right for an instruction whose whole job is to hand a value back. It is right because the frame goes away at the same moment, and the value is pushed onto the caller's stack rather than removed from this one. The tables describe the frame you are looking at.

## Try it yourself

**One.** Run the standard library sweep over all of it rather than the first 150 files. It takes about a minute. If you find a disagreement, that is a bug in this lesson and worth an issue.

**Two.** Write a function with seventeen local variables and find the point where the compiler stops packing two loads into one instruction, then work out why sixteen is the limit without looking it up again.

**Three.** Take `while True:` with a `break` in it and read the jumps. There is no test at the top, because T05's optimizer decided the answer at compile time, so the loop is a back edge and nothing else.

**Four.** `stack.walk` returns the height either side of every instruction. Find a function where two different paths reach the same instruction at different heights, and check which one the compiler kept.
""")


lesson.md("""
## What just happened

An instruction is two bytes, an opcode and an argument, and every offset in a listing is even because of that.

The argument means a different thing for every instruction, and the `opcode` module publishes which list each instruction is in. `LOAD_SMALL_INT` carries the value itself rather than an index, and a few instructions split the byte into two four bit slot numbers.

Arguments bigger than 255 are carried by `EXTENDED_ARG` instructions in front, up to three of them.

Offsets skip numbers for two reasons, `EXTENDED_ARG` rows in front and inline cache slots behind, and both are real bytes in `co_code`.

Jumps count instructions rather than bytes, and they count from after the jump including its cache slot. Every jump in 3.15 is relative.

`co_stacksize` is the deepest the stack gets on any path, worked out by walking the graph from the entry and from every exception handler, with a floor of one. The Python version of that walk in this lesson agrees with CPython on every code object in the standard library.

## Where this goes next

You can now read a listing. T07 is the loop that runs one: a single enormous `switch` in C, what the interpreter does between instructions, and why the shape of that loop is most of the reason CPython is as fast or as slow as it is.
""")


raise SystemExit(lesson.save())
