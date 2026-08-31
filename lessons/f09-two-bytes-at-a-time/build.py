#!/usr/bin/env python
"""F09. Two bytes at a time.

The ninth lesson of the front end part, and the twenty third overall. F08 finished with the
optimizer, which is the last stage that changes what the code does. This one is the assembler,
which changes only how it is written down.

The angle is that the assembler has exactly one hard problem and it is a circular one. How far
a jump has to reach depends on the size of everything in between, and the size of a jump
depends on how far it reaches. The fix is a loop, and there is a comment in the source calling
it an awful hack. Everything else in here is bookkeeping you can check by hand.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

#: Two cells print byte offsets for a function with a for loop in it, and 3.15 added a cache slot
#: to RESUME and another to GET_ITER. That moves every offset in both cells by the same four. The
#: wording is shared so the two notes cannot drift apart.
OFFSET_NOTE = (
    "On 3.14 `RESUME` and `GET_ITER` have no cache slot after them, so every offset here is four"
    " lower. The arguments are identical on both, which is what a relative jump buys you."
)

lesson = Lesson("f09-two-bytes-at-a-time", "f09")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("f09-two-bytes-at-a-time").figure


lesson.md(f"""
# F09. Two bytes at a time

{badge}

Eight lessons of compiler, and nothing has been written down yet. There has been a stream of tokens, a tree, a table of names, a list of instructions and a graph of blocks, and every one of those only ever existed in memory while the compiler was running.

The assembler is where it turns into bytes. It is the least clever stage in the whole front end: nothing here changes what your program does, and by the time it runs every decision has already been made somewhere else.

It does have one genuinely hard problem though, and it is circular. Read on.

{figure("sizes-and-offsets", "the four steps from a list with labels to the bytes of a code object")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/assemble.c:38-48@v3.15.0rc1`.

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
## Every byte of it

A {term("code object")} keeps its {term("bytecode")} in `co_code`, and `co_code` is a plain `bytes` object. You can print it. There is no header on it, no magic number, no table of contents, just instructions.

The layout is as simple as it gets: {cite("Include/internal/pycore_structs.h:17-32@v3.15.0rc1#_Py_CODEUNIT")} says one {term("opcode")} byte and one {term("oparg")} byte, and that is the whole unit. Everything in `co_code` is one of those pairs. Nothing is three bytes and nothing is one.

{lesson.claim("the bytes of a small function are short enough to read one by one and match against the disassembly")}
""")


lesson.code(
    """
import dis


def g(x):
    return x + 1


code = g.__code__

print(f"  {len(code.co_code)} bytes, which is {len(code.co_code) // 2} pairs")
print(f"  {' '.join(f'{b:02x}' for b in code.co_code)}")
print()
dis.dis(g)
""",
    differs=(
        "On 3.14 `RESUME` has no cache slot after it, so the function is 20 bytes rather than 22"
        " and every offset after the first is two lower. The instructions themselves are the same."
    ),
)


lesson.md(f"""
Read the pairs left to right. `80 00` is `RESUME 0`. Then `00 00`, which is opcode zero, and opcode zero is `CACHE`. Then `55 00` is `LOAD_FAST_BORROW 0`, `5d 01` is `LOAD_SMALL_INT 1`, `2a 00` is `BINARY_OP 0`, then five more `00 00` pairs, then `21 00` is `RETURN_VALUE`.

{figure("every-byte-of-it", "the twenty two bytes of a two line function, labelled pair by pair")}

Five instructions and six pairs that are not instructions. That is the next thing to explain.

## The gaps are not empty

Look at the offsets `dis` printed. They are 0, 4, 6, 8 and 20. Not 0, 2, 4, 6, 8. Something is taking up room between them.

Those are {term("inline cache")} slots. They sit in the instruction stream, they are two bytes each like everything else, and they are never executed. They are scratch space for the instruction above them to write down what it saw last time it ran, which is what F14 is about. For now the only thing that matters is that they are there and they take up space.

The assembler is where they get put in. {cite("Python/assemble.c:38-48@v3.15.0rc1#instr_size")} is the whole size calculation, three lines long: how many extra units for a big argument, plus one for the instruction, plus however many cache slots this opcode wants. {cite("Python/assemble.c:368-406@v3.15.0rc1#write_instr")} writes them out as `CACHE` with a zero argument, which is why they read as `00 00` in the bytes above.

{lesson.claim("the gap between one instruction's offset and the next tells you how many cache slots it carries")}
""")


lesson.code(
    """
import dis
from itertools import pairwise


def f(a, b):
    total = 0
    for one in a:
        if one > b:
            total = total + one
    return total


listed = list(dis.get_instructions(f))
units = len(f.__code__.co_code) // 2

print(f"  {units} pairs in co_code")
print(f"  {len(listed)} of them are instructions dis prints")
print(f"  {units - len(listed)} of them are cache slots")
print()
for one, following in pairwise(listed):
    slots = (following.offset - one.offset) // 2 - 1
    if slots:
        print(f"    {one.opname:20} and then {slots} cache slot(s)")
""",
    differs=(
        "On 3.14 `RESUME` and `GET_ITER` have no cache slot after them, so there are two fewer"
        " pairs, two fewer cache slots, and those two lines are missing from the list. How many"
        " instructions there are does not change."
    ),
)


lesson.md(f"""
`BINARY_OP` gets five. That is the biggest in the language, and it is why the offsets in the first cell jumped from 8 straight to 20.

{figure("why-the-offsets-jump", "an offset column with the cache slots that make it skip")}

You never have to think about this while reading a disassembly, but you do have to stop expecting the offsets to be consecutive. They are byte positions, not instruction numbers.

## A jump does not know where it is

Here is the interesting part. Every jump in CPython is relative, and you can prove that in one line: `dis.hasjabs` is empty. There are no absolute jumps left at all.

So a jump instruction holds a distance. The obvious question is a distance from what, and the obvious guess is wrong. The answer is in a four line comment, {cite("Python/assemble.c:705-708@v3.15.0rc1")}: offsets are relative to the instruction pointer after fetching the jump instruction. That means after its own two bytes and after its cache slots.

{lesson.claim("you can rebuild every jump target by hand from the argument and the size of the jump itself")}
""")


lesson.code(
    """
from itertools import pairwise

listed = list(dis.get_instructions(f))
ends = {one.offset: following.offset for one, following in pairwise(listed)}

for one in listed:
    if one.opcode not in dis.hasjrel:
        continue
    after = ends[one.offset]
    backwards = one.argval < after
    landed = after - 2 * one.arg if backwards else after + 2 * one.arg
    print(f"  {one.opname:18} at {one.offset:3}, fetch ends at {after:3},", end="")
    print(f" arg {one.arg:3} -> {landed:3}   dis agrees: {one.argval == landed}")
""",
    differs=OFFSET_NOTE,
)


lesson.md(f"""
The arithmetic is in {cite("Python/assemble.c:710-725@v3.15.0rc1")}, and the direction is decided by comparing the target's position with the current one. Backwards jumps store the distance as a positive number and the opcode says which way to apply it.

{figure("counting-from-where", "the same jump argument counted from two places, one of which lands nowhere")}

This is the single most common mistake in a hand written disassembler, and it is worth doing once by hand so it sticks.

## One byte only reaches 255

An {term("oparg")} is one byte. A jump over more than 255 code units does not fit, so an {term("EXTENDED_ARG")} goes in front carrying the high bits.

Now think about what that costs. The `EXTENDED_ARG` is itself a code unit, so putting one in makes the function one unit longer, which pushes the jump's target one unit further away, which makes the distance bigger. If the distance was near a boundary it can now need another `EXTENDED_ARG`, and so on.

{lesson.claim("the step that first needs an EXTENDED_ARG is one pair bigger than every other step")}
""")


lesson.code(
    """
import dis


def measure(n):
    \"\"\"Compile an if with n statements inside it, and look at the jump over them.\"\"\"
    body = "\\n".join(f"    x = x + {i}" for i in range(n))
    code = compile(f"def f(c, x):\\n  if c:\\n{body}\\n  return x\\n", "<here>", "exec")
    listed = list(dis.get_instructions(code.co_consts[0]))
    jump = next(one for one in listed if one.opcode in dis.hasjrel)
    widened = sum(1 for one in listed if one.opname == "EXTENDED_ARG")
    return len(code.co_consts[0].co_code) // 2, jump.arg, widened


print("  statements   pairs   jump argument   EXTENDED_ARG")
for n in (26, 27, 28, 29, 30):
    pairs, argument, widened = measure(n)
    print(f"  {n:^10}   {pairs:^5}   {argument:^13}   {widened:^12}")
""",
    differs=(
        "On 3.14 `RESUME` has no cache slot after it, so every number in the pairs column is one"
        " lower. The jump arguments and the `EXTENDED_ARG` column are identical, and the boundary"
        " falls between the same two rows."
    ),
)


lesson.md(f"""
Every step down that table adds nine pairs, except the step from 28 to 29, which adds ten. The extra one is the `EXTENDED_ARG`. The jump argument goes 253, then 262, skipping over 254 to 261 entirely, because the instruction that had to widen also pushed its own target further away.

{figure("one-byte-only-reaches-255", "the circular problem: widening a jump moves the thing it jumps to")}

CPython solves this the honest way, by doing it again until nothing changes. {cite("Python/assemble.c:726-728@v3.15.0rc1")} sets a flag whenever an instruction changed size, and the loop runs another round if it did. The comment above the loop, {cite("Python/assemble.c:731-745@v3.15.0rc1")}, opens with "this is an awful hack that could hurt performance" and then explains why it converges quickly anyway. It is a good comment. Somebody knew exactly what they were leaving behind.

## Which way is it going

One more thing happens before any of that, and it explains a name you have seen in earlier lessons.

The code generator does not emit `JUMP_FORWARD` or `JUMP_BACKWARD`. It emits `JUMP`, which is a {term("pseudo instruction")}: real enough to appear in the list, but with no opcode number the interpreter would recognise. Its argument is a label, not a distance, because at that point nobody knows where anything is going to end up.

{cite("Python/assemble.c:749-777@v3.15.0rc1#resolve_unconditional_jumps")} is where that gets settled. By then the labels have become positions in the list, so comparing the target's position with the jump's own is enough to say forward or backward, and the pseudo instruction is replaced with the real one.

{lesson.claim("the same jump is a label before the assembler and a signed distance after it")}
""")


lesson.code(
    """
import dis

from pyxray import compiler

SOURCE = \"\"\"def f(items):
    for one in items:
        if one:
            continue
        print(one)
\"\"\"

print("  what the code generator emitted")
for one in compiler.innermost_codegen(SOURCE):
    if "JUMP" in one.opname:
        print(f"    {one}")

print()
print("  what ended up in the code object")
body = compile(SOURCE, "<here>", "exec").co_consts[0]
for one in dis.get_instructions(body):
    if one.opcode in dis.hasjrel:
        print(f"    at {one.offset:3}  {one.opname:20} {one.arg:3}  lands on {one.argval}")
""",
    differs=OFFSET_NOTE,
)


lesson.md(f"""
`JUMP 3 (pseudo)` on the way in, `JUMP_BACKWARD 11` on the way out. The 3 was a label number. The 11 is a count of code units to subtract.

{figure("three-things-first", "the four steps the assembler runs, in order")}

The whole stage is twenty lines of driver, {cite("Python/assemble.c:779-802@v3.15.0rc1#_PyAssemble_MakeCodeObject")}: apply the label map, resolve the directions, resolve the distances, emit, build the code object. {cite("Python/assemble.c:432-457@v3.15.0rc1#assemble_emit")} is the emit step, and it does the bytecode, the {term("line table")} and the {term("exception table")} in that order.

## Try it yourself

1. Print `co_code` for a function with a `try` in it. Can you find the handler by eye?
2. Write a function whose jump needs two `EXTENDED_ARG` instructions. How many statements does that take?
3. `dis.hasjrel` has sixteen members. Print their names. Which ones surprised you?
4. Take the jump arithmetic cell and make it print the wrong answer on purpose, by counting from the jump's own offset instead of the end of its fetch. How far off is it?
5. Find an instruction other than `BINARY_OP` with more than one cache slot, using only the gaps between offsets.

## What just happened

The assembler is the stage that writes things down. Nothing it does changes what your program computes.

Everything in `co_code` is exactly two bytes: one opcode, one argument. Instructions that want scratch space get cache slots after them, which are also two bytes each, are written out as `CACHE 0`, and are stepped over rather than run. That is why the offsets in a disassembly skip.

Every jump is relative, and the distance is measured from the point after the whole instruction has been fetched, cache slots included. There are no absolute jumps left in the language.

One argument byte only reaches 255, so a long jump gets an `EXTENDED_ARG` in front of it, and that extra unit moves the target it was trying to reach. The assembler works out sizes and distances over and over until a round goes by with nothing changing.

Before any of that, labels turn into positions and the pseudo instruction `JUMP` turns into `JUMP_FORWARD` or `JUMP_BACKWARD`, because only now is there enough information to know which.

## What is next

F10 is the {term("code object")} itself. There is a lot more in one than `co_code`: the constants, the names, the flags, and the odd rules about which names live in which of four different arrays.
""")


raise SystemExit(lesson.save())
