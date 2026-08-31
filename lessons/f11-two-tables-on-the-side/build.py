#!/usr/bin/env python
"""F11. Two tables on the side.

The eleventh lesson of the front end part, and the twenty fifth overall. F10 opened the code
object and named its two side tables without saying what is in them. This one decodes both,
byte by byte, and checks the answers against the interpreter's own.

The angle is that the two tables are the same idea twice. A traceback needs to know which line
and which columns an instruction came from. A raise needs to know which handler covers an
offset. Neither is needed while a program is going right, so neither is allowed to cost
anything while it is. Both got moved out of the instruction stream and into a compressed blob
that nothing reads until something has already gone wrong.

The payoff is that both blobs are short enough to decode in about thirty lines of Python, and
the reader can check their decoder against `co_positions()` and `dis._parse_exception_table`
rather than taking anybody's word for it.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("f11-two-tables-on-the-side", "f11")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("f11-two-tables-on-the-side").figure


lesson.md(f"""
# F11. Two tables on the side

{badge}

Write a `try` around a loop and the loop does not get any slower. The instructions inside the `try` are the same ones you get without it, in the same order, at the same offsets.

Nothing in the bytecode says a `try` started or ended. What CPython has instead is a table saying which range of offsets each handler covers, and nothing reads it until something raises. That is zero cost exception handling.

Source locations work the same way. Every instruction knows its line and columns, which is how a traceback underlines the failing part of an expression, and those four numbers per instruction live in a second blob beside the bytecode.

Two tables, same idea. This lesson decodes both.

{figure("nothing-in-the-hot-path", "the loop instructions on one side and the two side tables on the other")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Include/cpython/code.h:314-325@v3.15.0rc1`.

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
## The try that is not there

Start with the claim, because it is easy to check and hard to believe.

Take a loop. Wrap it in a `try` with an `except` after it. Then compare the instructions inside the covered range against the instructions of the same loop with no `try` around it at all.

{lesson.claim("the instructions inside a try block are identical to the same code with no try around it")}
""")


lesson.code(
    """
import dis

PLAIN = "def f(xs):\\n    t = 0\\n    for x in xs:\\n        t += x\\n    return t\\n"
TRIED = (
    "def f(xs):\\n    t = 0\\n    try:\\n        for x in xs:\\n            t += x\\n"
    "    except TypeError:\\n        t = -1\\n    return t\\n"
)

plain = compile(PLAIN, "<here>", "exec").co_consts[0]
tried = compile(TRIED, "<here>", "exec").co_consts[0]

covered = dis._parse_exception_table(tried)[0]
inside = [
    one.opname for one in dis.get_instructions(tried) if covered.start <= one.offset < covered.end
]
loop = [one.opname for one in dis.get_instructions(plain)][3:-2]

print(f"  the try covers bytes {covered.start} to {covered.end}, handler at {covered.target}")
print()
print(f"  inside the try  {len(inside)} instructions")
print(f"  the plain loop  {len(loop)} instructions")
print(f"  the same list   {inside == loop}")
print()
total = len(list(dis.get_instructions(tried)))
print(f"  the try version has {total} instructions in total,")
print(f"  and the {total - len(inside)} outside it are the setup, the return and the handler")
""",
    varies="The offsets are 3.15's. On 3.14 the loop compiles two bytes shorter so every number here shifts down, and the two lists still match, which is the part that matters.",
)


lesson.md("""
Two pseudo instructions used to be there. `SETUP_FINALLY` said "from here on, exceptions go to L1", and `POP_BLOCK` undid it. They still exist in the compiler, because the code generator finds them convenient to think in, and F08 watched the optimizer move them around. The assembler deletes both and writes the exception table instead, which is `Python/assemble.c:158-190@v3.15.0rc1#assemble_exception_table`.

So neither one survives into the bytecode. Worth checking rather than believing.
""")


lesson.code(
    """
names = {one.opname for one in dis.get_instructions(tried)}

for one in ("SETUP_FINALLY", "POP_BLOCK", "SETUP_CLEANUP", "SETUP_WITH"):
    print(f"  {one:16} in the bytecode: {one in names}")

print()
print(f"  and the whole exception table is {len(tried.co_exceptiontable)} bytes:")
print(f"    {' '.join(f'{b:02x}' for b in tried.co_exceptiontable)}")
print(f"  the plain version's table is {len(plain.co_exceptiontable)} bytes")
""",
    varies="The table's bytes are 3.15's. On 3.14 the same function needs twelve bytes rather than sixteen, because it has one fewer handler entry.",
)


lesson.md(f"""
## Four numbers, and one of them is doubled

An exception table entry is conceptually five things: where the covered range starts, where it ends, where the handler is, how deep the stack should be when the handler starts, and whether the offset of the failing instruction has to be pushed too.

The last one is `lasti`, and it is there for re raising. At the end of a `finally` block an in flight exception has to be raised again and has to keep pointing at the instruction that first raised it, but by then the instruction pointer is somewhere inside the `finally`. So the original offset gets pushed on the stack and `RERAISE` puts it back.

Five things get stored as four, because the size is always smaller than the end, so `start, size, target, depth` is cheaper than `start, end, target, depth`, and `depth` and `lasti` share a number as `depth * 2 + lasti`. That is `Python/assemble.c:133-156@v3.15.0rc1#assemble_emit_exception_table_entry`.

{figure("one-entry-decoded", "the four bytes of one exception table entry, labelled")}

Every number in the encoding counts code units rather than bytes, so everything doubles on the way out.

{lesson.claim("an exception table entry decodes to start, size, target and a doubled depth")}
""")


lesson.code(
    """
table = tried.co_exceptiontable

print(f"  {' '.join(f'{b:02x}' for b in table)}")
print()
for i, b in enumerate(table[:4]):
    starts = "yes" if b & 0x80 else "no"
    more = "yes" if b & 0x40 else "no"
    print(f"    byte {i}: {b:3}  {b:08b}   starts: {starts:3}  more: {more:3}  value {b & 0x3F}")

start, size, target, both = (b & 0x3F for b in table[:4])

print()
print(f"  so start {start}, size {size}, target {target}, and depth and lasti packed into {both}")
print(f"  which covers bytes {start * 2} to {(start + size) * 2}, handler at byte {target * 2}")
print(f"  with the stack popped back to {both >> 1} and lasti {bool(both & 1)}")
""",
    varies="These four bytes are 3.15's. On 3.14 they read 84 11 17 00, which is start 4, size 17, target 23, and the walk through them is the same walk.",
)


lesson.md(f"""
That is the whole format. The top bit marks the first byte of an entry, bit 6 says another byte follows, and the low six bits carry the value. Which means the entire table can be decoded in about a dozen lines.

Here is a decoder, and next to it what `dis` says, so there is nothing to take on trust.

{lesson.claim("a dozen lines of Python decode co_exceptiontable exactly as dis does")}
""")


lesson.code(
    """
import dis


def handlers(table):
    \"\"\"Every entry in a co_exceptiontable, as byte offsets rather than code units.\"\"\"

    def number(at):
        byte = table[at]
        value = byte & 0x3F
        while byte & 0x40:
            at += 1
            byte = table[at]
            value = (value << 6) | (byte & 0x3F)
        return value, at + 1

    at = 0
    while at < len(table):
        start, at = number(at)
        size, at = number(at)
        target, at = number(at)
        both, at = number(at)
        yield start * 2, (start + size) * 2, target * 2, both >> 1, bool(both & 1)


def guarded(items):
    total = 0
    try:
        for one in items:
            total = total + one
    except TypeError:
        total = -1
    finally:
        print(total)
    return total


mine = list(handlers(guarded.__code__.co_exceptiontable))
theirs = [tuple(one) for one in dis._parse_exception_table(guarded.__code__)]

print("  start  end  target  depth  lasti")
for one in mine:
    print(f"  {one[0]:5}  {one[1]:3}  {one[2]:6}  {one[3]:5}  {one[4]}")
print()
print(f"  {len(mine)} entries in {len(guarded.__code__.co_exceptiontable)} bytes")
print(f"  and dis agrees on every one of them: {mine == theirs}")
""",
    varies="The offsets are 3.15's and 3.14 puts them a few bytes lower. The line that matters is the last one, and it says True on both.",
)


lesson.md(f"""
## Why the top bit is set

The marker bit looks like a small thing and it is the reason the format was chosen.

When something raises, the interpreter has an offset and needs the entry covering it. Entries vary in size, so you cannot index into the table. But because every entry starts with a byte that has the top bit set, and no other byte in an entry does, you can land anywhere in the middle of the table and walk backwards until you find one. That is `Python/ceval.h:440-444@v3.15.0rc1#scan_back_to_entry_start`, four lines long.

Which means binary search works on a variable length table. Jump to the middle, walk back to the nearest entry boundary, read its start offset, and go left or right. `Python/ceval.h:457-490@v3.15.0rc1#get_exception_handler` does exactly that, and falls back to a straight scan once the range is under forty bytes, which is where a binary search stops being worth the trouble.

{figure("how-a-raise-finds-its-handler", "raise, look up the offset, unwind the stack, jump to the handler")}

The depth in the entry is what the second step needs. When a handler starts, the stack has to look the way it looked when the `try` began, whatever the failing code left on it. Rather than tracking that at run time, the compiler works it out once and writes it down.
""")


lesson.md(f"""
## Every instruction knows where it came from

Now the other table. This one is bigger and the format is more interesting.

`co_positions()` gives four numbers per instruction: start line, end line, start column, end column. That is what lets a traceback underline the failing part of an expression instead of the whole line. Here is that underline, rebuilt from the table by hand rather than printed by `traceback`, so you can see exactly where it comes from.

{lesson.claim("the caret in a traceback is drawn from the column numbers in co_linetable")}
""")


lesson.code(
    """
SOURCE = \"\"\"def totals(first, second):
    return first["count"] + second["count"]

totals({"count": 1}, {"total": 2})
\"\"\"

lines = SOURCE.splitlines()

try:
    exec(compile(SOURCE, "example.py", "exec"), {})
except KeyError as problem:
    deepest = problem.__traceback__
    while deepest.tb_next:
        deepest = deepest.tb_next
    inner = deepest.tb_frame.f_code
    line, end_line, start, end = list(inner.co_positions())[deepest.tb_lasti // 2]
    print(f"  it failed at instruction {deepest.tb_lasti // 2}, which the table puts at")
    print(f"  line {line}, columns {start} to {end}")
    print()
    print("   ", lines[line - 1])
    print("   ", " " * start + "^" * (end - start))
""",
    varies="3.14 reaches the failure one instruction earlier, so the instruction number differs. The line and the columns it reports, and so the caret, are the same on both.",
)


lesson.md(f"""
## Six ways to say where

Storing four numbers for every instruction plainly would cost sixteen bytes each, which for a small function is more than the bytecode. So the format has six shapes and the assembler picks the smallest one that fits.

Every entry begins with one byte carrying three things: a marker bit, which of the six forms this is, and how many code units the entry covers. `Include/internal/pycore_code.h:432-437@v3.15.0rc1#write_location_entry_start` is the one line that builds it.

{figure("the-first-byte-says-what-follows", "the three fields packed into the first byte of a location entry")}

The six forms are `Include/cpython/code.h:314-325@v3.15.0rc1`, and the reason there are six is that almost every instruction is boring. Same line as the one before, columns under eighty, span under sixteen characters. That case is two bytes.

{figure("six-ways-to-say-where", "the six location entry forms and what each one stores")}

Form 15 is the odd one. Some instructions did not come from your source at all, and they get no location. In a function with a `try` in it they are the exception plumbing, the instructions that save the in flight exception and re raise it, which no line you wrote asked for.

{lesson.claim("some instructions in a normal function have no source location at all")}
""")


lesson.code(
    """
import dis

where = list(guarded.__code__.co_positions())
nowhere = [one.opname for one in dis.get_instructions(guarded) if where[one.offset // 2][0] is None]

print(f"  {len(list(dis.get_instructions(guarded)))} instructions in guarded")
print(f"  {len(nowhere)} of them come from nowhere, and they are {sorted(set(nowhere))}")
print()
print(f"  co_code           {len(guarded.__code__.co_code):4} bytes")
print(f"  co_linetable      {len(guarded.__code__.co_linetable):4} bytes")
print(f"  co_exceptiontable {len(guarded.__code__.co_exceptiontable):4} bytes")
""",
    varies="The counts and the byte sizes are 3.15's. 3.14 compiles the same function a little smaller, and the instructions with no location are the same exception plumbing either way.",
)


lesson.md(f"""
## Decoding it

Thirty lines. The only fiddly parts are the two variable length integers and one off by one.

The off by one is that the long form stores each column plus one, so that zero can mean "no column here". `Python/assemble.c:257-267@v3.15.0rc1#write_location_info_long_form` adds the one on the way in and `Objects/codeobject.c:1201-1225@v3.15.0rc1#advance_with_locations` takes it off on the way out. The internal documentation does not mention it, which is a reasonable reminder that the source is the specification.

{lesson.claim("a hand written decoder reproduces co_positions() for every code object in a standard library module")}
""")


lesson.code("""
def positions(code):
    \"\"\"Every instruction's source location, decoded out of co_linetable by hand.\"\"\"
    table = code.co_linetable
    line = code.co_firstlineno
    at = 0

    def varint():
        nonlocal at
        value = shift = 0
        while True:
            chunk = table[at]
            at += 1
            value |= (chunk & 63) << shift
            shift += 6
            if not chunk & 64:
                return value

    def svarint():
        value = varint()
        return -(value >> 1) if value & 1 else value >> 1

    while at < len(table):
        first = table[at]
        at += 1
        kind = (first >> 3) & 15
        length = (first & 7) + 1
        if kind == 15:
            found = (None, None, None, None)
        elif kind == 13:
            line += svarint()
            found = (line, line, None, None)
        elif kind == 14:
            line += svarint()
            end_line = line + varint()
            start, end = varint() - 1, varint() - 1
            found = (line, end_line, start if start >= 0 else None, end if end >= 0 else None)
        elif kind >= 10:
            line += kind - 10
            found = (line, line, table[at], table[at + 1])
            at += 2
        else:
            second = table[at]
            at += 1
            start = kind * 8 + ((second >> 4) & 7)
            found = (line, line, start, start + (second & 15))
        yield from [found] * length
""")


lesson.md("""
Now run it against something. Not one hand picked function, because that proves nothing, but every code object in a handful of standard library modules, nested functions and comprehensions and all.
""")


lesson.code(
    """
import argparse
import dataclasses
import json.decoder
import types


def everything(code):
    \"\"\"This code object and every one nested inside it.\"\"\"
    yield code
    for one in code.co_consts:
        if isinstance(one, types.CodeType):
            yield from everything(one)


def written_in(module):
    \"\"\"Every code object belonging to functions and methods defined in this module.\"\"\"
    for one in vars(module).values():
        if isinstance(one, types.FunctionType) and one.__module__ == module.__name__:
            yield from everything(one.__code__)
        elif isinstance(one, type) and one.__module__ == module.__name__:
            for other in vars(one).values():
                if isinstance(other, types.FunctionType):
                    yield from everything(other.__code__)


checked = wrong = 0
for module in (argparse, dataclasses, dis, json.decoder):
    for one in written_in(module):
        checked += 1
        if list(positions(one)) != list(one.co_positions()):
            wrong += 1
            print(f"    mismatch in {module.__name__}.{one.co_name}")

print(f"  {checked} code objects out of four standard library modules")
print(f"  {wrong} of them decoded differently from co_positions()")
""",
    varies="How many code objects those four modules hold depends on the version, because the modules themselves change. The number that has to be zero is zero on both.",
)


lesson.md(f"""
## Two varints, opposite ways round

One last detail, and it is the kind of thing that looks like sloppiness until you see why.

Both tables encode numbers six bits to a byte with bit 6 meaning "another byte follows". They put the chunks in opposite orders. The line table writes the least significant chunk first, in `Include/internal/pycore_code.h:405-416@v3.15.0rc1#write_varint`. The exception table reads the most significant chunk first, in `Include/internal/pycore_code.h:394-403@v3.15.0rc1#parse_varint`.

{figure("two-varints-in-one-file", "the two variable length integer encodings side by side")}

The reason is the binary search. The exception table gets searched on the start offset of each entry, and reading the leading chunk of a most significant first number gives you the big end straight away. The line table is never searched that way, it is walked from the beginning, so it uses whichever order is easier to write.

{lesson.claim("the two tables encode integers with their chunks in opposite orders")}
""")


lesson.code("""
def as_exception_table(value):
    \"\"\"How the exception table would write this number: biggest chunk first.\"\"\"
    chunks = []
    while value >= 64:
        chunks.append(value & 63)
        value >>= 6
    chunks.append(value)
    chunks.reverse()
    out = [one | 0x40 for one in chunks[:-1]] + [chunks[-1]]
    out[0] |= 0x80
    return out


def as_line_table(value):
    \"\"\"How the line table would write it: smallest chunk first.\"\"\"
    out = []
    while value >= 64:
        out.append(64 | (value & 63))
        value >>= 6
    out.append(value)
    return out


for number in (5, 100, 4000, 100000):
    one = " ".join(f"{b:02x}" for b in as_exception_table(number))
    other = " ".join(f"{b:02x}" for b in as_line_table(number))
    print(f"  {number:6}   exception table {one:14}   line table {other}")

print()
print("  same number, same six bit chunks, read from opposite ends")
""")


lesson.md("""
## Try it yourself

Three things to poke at.

Write a function with a `try` inside a `try` inside a loop, and print its exception table with the decoder above. The nesting shows up as overlapping ranges, and the depth column is what tells the handlers apart.

Take a function with a long expression spread over several lines and print `co_positions()` next to `co_lines()`. The second is smaller and older and only gives you line numbers. Work out from the entry forms why.

Compile the same function twice, once with the body all on one line and once spread over ten, and compare the length of `co_linetable`. The bytecode is identical. The table is not, and the difference is entirely which entry forms the assembler could get away with.

## What just happened

A `try` costs nothing when nothing raises, because nothing about it is in the bytecode. The pseudo instructions the compiler used are deleted by the assembler, and what replaces them is a table of ranges.

That table holds start, size, target and a number that is the stack depth doubled plus a re raise flag, all in code units, all as six bit chunks. The top bit of the first byte of each entry is what makes a variable length table binary searchable, because you can land anywhere and walk backwards to a boundary.

The line table is the same idea for source locations. Four numbers per instruction, six entry forms, and the assembler picks the smallest that fits. It is what draws the caret under the failing half of an expression in a traceback.

Both are decodable in about thirty lines of Python, and both decoders agree with the interpreter, which is the only evidence worth having.

## What is next

F12 is marshal, which is how all of this gets written to a `.pyc` file and read back. It is the last lesson of the front end, and it closes the loop: source text in at F01, bytes on disk at F12, and the same code object at both ends.
""")


raise SystemExit(lesson.save())
