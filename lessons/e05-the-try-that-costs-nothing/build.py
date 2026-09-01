#!/usr/bin/env python
"""E05. The try that costs nothing.

The fifth lesson of the interpreter part. E04 was about what a frame slot holds. This one is
about something that is not in the bytecode at all.

The hook is that a `try` block disassembles to nothing. Wrap a line in a `try` and the
instructions for that line do not change, and no instruction is added on the way in or on the
way out. The information about which handler covers which range of code went into a table
beside the bytecode, and the interpreter only reads it once something has already raised.

The lesson decodes that table by hand, four bytes at a time, then measures both halves of the
trade: what not raising costs now, and what raising costs instead.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("e05-the-try-that-costs-nothing", "e05")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("e05-the-try-that-costs-nothing").figure


lesson.md(f"""
# E05. The try that costs nothing

{badge}

Take a one line function and wrap that line in a `try`. Then disassemble both versions and compare the instructions for the line itself.

They are identical. Not similar, identical. There is no instruction that starts a `try` and none that ends one. Whatever the interpreter needs to know about the handler, it is not learning it by running anything.

{figure("two-ways-to-mark-a-try", "the same try block marked by instructions before 3.11 and by a table since")}

This is called {term("zero cost exceptions", "zero cost exception handling")}, and the deal is exactly what the name says. Code that never raises pays nothing. Code that does raise pays more than it used to. Since most `try` blocks in most programs never fire, that is a good trade, and this lesson measures both sides of it.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/ceval.h:457-490@v3.15.0rc1#get_exception_handler`.

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

Everything here has worked the same way since 3.11. The instruction names and the exact byte counts move between releases, so a few cells say what changes and where.
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
## The try that disassembles to nothing

Two functions. One adds one to its argument. The other does the same thing inside a `try`.

{lesson.claim("the instructions for the guarded line are the same as the instructions for the unguarded line, so entering a try block executes nothing")}
""")


lesson.code(
    """
import dis


def plain(x):
    return x + 1


def guarded(x):
    try:
        return x + 1
    except ValueError:
        return 0


def body_of(one):
    ops = [step.opname for step in dis.get_instructions(one)]
    return [op for op in ops if op not in ("RESUME", "NOP")]


print(f"  plain    {' '.join(body_of(plain))}")
print(f"  guarded  {' '.join(body_of(guarded)[:4])}   ... and then the handler")
print()
print(f"  same first four instructions  {body_of(plain) == body_of(guarded)[:4]}")
""",
)


lesson.md(f"""
Four instructions on the way in, four on the way out, and nothing between them about the `try`. The only thing the `try` added to the front is a `NOP`, which is there to hold the line number of the `try:` line itself so a debugger can stop on it. The lesson's helper filters those out, and you can put them back to see.

The rest of the guarded function is the handler, sitting after the `return`, on code paths that only run if something raises.

{lesson.claim("a try block adds bytes to the code object, but all of them are the handler and none of them are on the path a successful call takes")}
""")


lesson.code(
    """
def deeply(x):
    try:
        try:
            try:
                return x + 1
            except KeyError:
                pass
        except IndexError:
            pass
    except ValueError:
        return 0


for name, one in [("plain", plain), ("one try", guarded), ("three nested", deeply)]:
    code = one.__code__
    entries = list(dis.Bytecode(one).exception_entries)
    print(
        f"  {name:14} {len(code.co_code):4} bytes of code   "
        f"{len(code.co_exceptiontable):3} bytes of table   {len(entries)} entries"
    )
""",
    differs="On 3.14 the numbers are smaller: 20, 58 and 134 bytes of code, 0, 12 and 46 "
    "bytes of table, and 0, 3 and 11 entries. Both the instruction set and the way the "
    "compiler lays out handlers changed between the two, so the sizes move. The zero on the "
    "first row does not.",
)


lesson.md(f"""
## The table that replaced the instructions

The information has to live somewhere. It lives in `co_exceptiontable`, which is a plain bytes object hanging off the {term("code object")} next to the bytecode and the {term("line table")}.

`dis` will unpack it for you. Each row says: this range of instructions is covered, jump here if something raises inside it.

{figure("what-one-entry-says", "the five fields of one exception table entry and what each one means")}

The last two fields are the part people do not expect. `depth` is how tall the {term("value stack")} should be when the handler starts running, because an exception can go off halfway through building a list and leave junk on the stack that has to go. `lasti` says whether to also push the offset the raise happened at, which matters for re-raising later.

{lesson.claim("every entry in the exception table carries a target, a stack depth and a lasti flag as well as the range it covers")}
""")


lesson.code(
    """
for entry in dis.Bytecode(guarded).exception_entries:
    print(
        f"  covers {entry.start:3} to {entry.end:3}   jump to {entry.target:3}   "
        f"depth {entry.depth}   lasti {entry.lasti}"
    )
""",
    differs="On 3.14 there are three rows rather than four, and all the offsets are "
    "different, because the instructions they point at are laid out differently. The shape "
    "is the same: one row for the body of the try, and the rest covering the handler itself "
    "so that an exception raised while handling one still unwinds properly.",
)


lesson.md(f"""
The first row is the `try` body. The rows after it cover the handler, because an exception raised inside an `except` block also has to go somewhere, and where it goes is the code that cleans up the exception state before passing it on.

## Four bytes, one handler

The table is bytes, not a list of five tuples, and the encoding is worth twenty minutes because the same trick shows up again in the line table.

Every number is a {term("varint")}: six bits per byte, one bit saying another byte follows, and the top bit reserved to mark the first byte of an entry, {cite("InternalDocs/exception_handling.md:140-146@v3.15.0rc1#varint")}. That top bit is what makes the whole thing searchable. The interpreter can jump into the middle of the table, scan backwards to the nearest byte with the top bit set, and know it is at the start of a real entry, {cite("Python/ceval.h:440-452@v3.15.0rc1#scan_back_to_entry_start")}.

Sizes are stored rather than end offsets, because a size is always smaller than the offset it belongs to and so needs fewer bytes, {cite("InternalDocs/exception_handling.md:109-117@v3.15.0rc1")}. Depth and lasti are packed into one number as `depth * 2 + lasti`.

{figure("four-bytes-one-entry", "the four bytes of one exception table entry with the bits labelled")}

{lesson.claim("the exception table can be decoded by hand from the raw bytes, and a hand written decoder gives the same answer as the one in dis")}
""")


lesson.code(
    """
def read_number(table, at):
    value = table[at] & 63
    while table[at] & 64:
        at += 1
        value = (value << 6) | (table[at] & 63)
    return value, at + 1


def read_table(table):
    at = 0
    while at < len(table):
        assert table[at] & 128, "every entry starts with the top bit set"
        start, at = read_number(table, at)
        size, at = read_number(table, at)
        target, at = read_number(table, at)
        packed, at = read_number(table, at)
        yield start * 2, (start + size) * 2, target * 2, packed >> 1, bool(packed & 1)


raw = guarded.__code__.co_exceptiontable
print(f"  the raw bytes  {list(raw)}")
print()

mine = list(read_table(raw))
theirs = [
    (e.start, e.end, e.target, e.depth, e.lasti) for e in dis.Bytecode(guarded).exception_entries
]
for row in mine:
    print(f"  decoded by hand  {row}")
print()
print(f"  matches what dis says  {mine == theirs}")
""",
    varies="The raw bytes are different on 3.14, because the offsets they encode are "
    "different, so the printed list will not match the text. The decoder does not care and "
    "the last line still says True. That is the point of writing one.",
)


lesson.md(f"""
Four bytes for the first entry: `131`, `8`, `12`, `0`. The 131 is 128 plus 3, so the top bit marks the start and the value is 3, which is code unit 3, which is byte 6. Then a size of 8 code units, a target at code unit 12, and a packed zero meaning depth 0 and no lasti.

Everything is in code units rather than bytes, which is why the decoder multiplies by two. The real one, in `dis`, is the same nine lines, {cite("Lib/dis.py:745-759@v3.15.0rc1#_parse_exception_table")}. The one that writes it is `assemble_exception_table`, {cite("Python/assemble.c:157-188@v3.15.0rc1#assemble_exception_table")}, which walks the finished instruction list and starts a new entry every time the covering handler changes.

## What not raising costs

That is the mechanism. Now the trade.

The claim is that a `try` is free when nothing goes wrong. The honest version is that it is nearly free, because of the `NOP`, and that it is cheaper than the thing people write to avoid it.

{lesson.claim("a loop with a try around its body runs at about the same speed as the same loop without one, and faster than the same loop checking a returned value instead")}
""")


lesson.code(
    """
import timeit


def work(x):
    return x + 1


def no_try(n):
    total = 0
    for i in range(n):
        total = work(i)
    return total


def with_try(n):
    total = 0
    for i in range(n):
        try:
            total = work(i)
        except ValueError:
            total = 0
    return total


def checking(n):
    total = 0
    for i in range(n):
        answer = work(i)
        if answer is None:
            continue
        total = answer
    return total


for name, one in [("no_try", no_try), ("with_try", with_try), ("checking", checking)]:
    best = min(timeit.repeat(lambda one=one: one(1000), number=500, repeat=5))
    print(f"  {name:10} {best / 500 / 1000 * 1e9:6.1f} ns per iteration")
""",
    varies="These are timings, so they are different on every machine and every run, and in "
    "a browser they are several times larger across the board. What should hold is the "
    "order: the first two close together, and the third clearly behind.",
)


lesson.md(f"""
{figure("what-not-raising-costs", "three versions of the same loop timed, with the try nearly free and the check not")}

The first two come out the same, near enough that the timer cannot separate them. The third is the pattern the `try` replaced: return a sentinel, check it at every call site. Checking costs a real instruction on every pass, and the `try` does not.

## What raising costs

Now the other half. When something does raise, the interpreter has to go and read that table, {cite("Python/ceval.h:457-490@v3.15.0rc1#get_exception_handler")}. Small tables get a linear scan; anything over forty bytes gets a binary search first, {cite("Python/ceval.h:455@v3.15.0rc1#MAX_LINEAR_SEARCH")}.

If there is no handler in this frame, the frame is added to the {term("traceback")} and dropped, and the same question is asked of the caller, {cite("Python/bytecodes.c:6519-6558@v3.15.0rc1#exception_unwind")}. That is {term("unwinding")}, and it is why the cost depends on distance.

{lesson.claim("raising and catching in the same frame costs a few hundred nanoseconds, and each extra frame the exception has to travel through adds roughly the same amount again")}
""")


lesson.code(
    """
class Sentinel(Exception):
    pass


def deep(n):
    if n:
        return deep(n - 1)
    raise Sentinel


def catch_at(n):
    try:
        deep(n)
    except Sentinel:
        return n


for frames in [1, 5, 20, 50]:
    best = min(timeit.repeat(lambda frames=frames: catch_at(frames), number=20000, repeat=3))
    print(f"  through {frames:3} frames   {best / 20000 * 1e9:8.1f} ns")
""",
    varies="Timings again, so the numbers move. The line to read is the shape: roughly "
    "linear in the number of frames, because each frame is a table lookup plus one more "
    "link on the traceback.",
)


lesson.md(f"""
{figure("what-raising-costs", "the cost of raising and catching plotted against how many frames the exception crosses")}

About fifty nanoseconds per frame on this machine. Most of that is not the table lookup, which is a handful of byte comparisons. It is `PyTraceBack_Here`, which builds a new traceback object for every frame the exception passes through, {cite("Python/bytecodes.c:6507-6514@v3.15.0rc1#PyTraceBack_Here")}. The traceback is assembled on the way out, one link at a time, which is why an exception thrown fifty frames down is fifty times the work of one thrown here.

## Where the traceback thinks it happened

The `lasti` flag from the table is the strangest field, and there is a way to see what it is for.

Put a `finally` around a `raise`. The `finally` block runs, and then the exception carries on. But by the time the exception carries on, the frame's instruction pointer is sitting in the `finally` block, not at the `raise`. Without something remembering, the traceback would point at the cleanup code.

That something is `lasti`. The table says push the raising offset onto the stack before jumping to the handler, {cite("Python/bytecodes.c:6546-6550@v3.15.0rc1#PyStackRef_TagInt")}, and `RERAISE` puts it back afterwards, {cite("Python/bytecodes.c:1920-1931@v3.15.0rc1#RERAISE")}. It is pushed as a {term("tagged integer")}, the E04 trick, so no object is allocated for it.

{lesson.claim("the traceback points at the instruction that raised, not at the finally block that re-raised, because the raising offset was saved on the stack and put back")}
""")


lesson.code(
    """
def cleanup():
    pass


def with_finally():
    try:
        raise ValueError("thrown here")
    finally:
        cleanup()


try:
    with_finally()
except ValueError as caught:
    walk = caught.__traceback__
    while walk is not None:
        print(f"  {walk.tb_frame.f_code.co_name:14} offset {walk.tb_lasti}")
        walk = walk.tb_next

steps = list(dis.get_instructions(with_finally))
raising = [step.offset for step in steps if step.opname == "RAISE_VARARGS"]
inside = [step.offset for step in steps if step.opname == "RERAISE"]
print()
print(f"  the raise is at offset      {raising}")
print(f"  the re-raise is at offset   {inside}")
""",
    varies="The offsets are different on 3.14 and on a browser build, because the "
    "instructions ahead of them are a different size. What holds everywhere is that the "
    "number next to `with_finally` in the traceback is the first number in the second to "
    "last line, and not one of the numbers in the last line.",
)


lesson.md(f"""
The offset in the traceback is the `raise`, not the `RERAISE` that actually sent it on. That is the whole job of `lasti`.

While we are here: a `finally` block is not a jump to shared code. It is copied into the bytecode once for every way out of the `try`, so a `finally` around a block that can return, break, continue and fall through appears several times over.

{lesson.claim("the body of a finally block appears in the bytecode more than once, one copy per way out of the try it guards")}
""")


lesson.code(
    """
def many_exits(n):
    for i in range(n):
        try:
            if i == 1:
                return "returned"
            if i == 2:
                break
            if i == 3:
                continue
        finally:
            cleanup()
    return "fell through"


calls = [step.opname for step in dis.get_instructions(many_exits)].count("LOAD_GLOBAL")
print(f"  copies of the finally body   {calls}")
print(f"  exception table entries      {len(list(dis.Bytecode(many_exits).exception_entries))}")
""",
)


lesson.md(f"""
## The loop that does not raise at all

One more thing worth seeing, because it explains a design decision.

Iteration is supposed to end with `StopIteration`. But a `for` loop does not catch one. `FOR_ITER` asks the iterator for the next value and jumps on exhaustion, without an exception ever existing, so a plain `for` loop over a range has an empty exception table.

{lesson.claim("a for loop has no exception table at all, and the same loop written with next and a try does, and is slower")}
""")


lesson.code(
    """
def with_for(n):
    total = 0
    for i in range(n):
        total += i
    return total


def with_next(n):
    walker = iter(range(n))
    total = 0
    while True:
        try:
            total += next(walker)
        except StopIteration:
            return total


for name, one in [("for loop", with_for), ("while and next", with_next)]:
    guarded_bytes = len(one.__code__.co_exceptiontable)
    best = min(timeit.repeat(lambda one=one: one(1000), number=500, repeat=5))
    print(f"  {name:16} table {guarded_bytes:2} bytes   {best / 500 / 1000 * 1e9:5.1f} ns per item")
""",
    varies="A timing, so the numbers move, and in a browser both are larger. The table "
    "sizes are the stable part: zero for the `for` loop, and not zero for the other one.",
)


lesson.md("""
Zero bytes of table against a handful, and a real speed difference. Iteration is far too common to end every loop with an exception, so it does not.

## How much of this there actually is

A last look at the scale of it. Walk every code object reachable from the modules already imported and see how many of them are guarded, and how much space the tables take next to the bytecode.
""")


lesson.code(
    """
import importlib
import types


def every_code_object():
    seen = set()
    found = []

    def walk(code):
        if id(code) in seen:
            return
        seen.add(id(code))
        found.append(code)
        for one in code.co_consts:
            if isinstance(one, types.CodeType):
                walk(one)

    for module in list(sys.modules.values()):
        for thing in list(vars(module).values()) if hasattr(module, "__dict__") else []:
            if isinstance(thing, types.FunctionType):
                walk(thing.__code__)
            elif isinstance(thing, type):
                for member in list(vars(thing).values()):
                    if isinstance(member, types.FunctionType):
                        walk(member.__code__)
    return found


for name in ["argparse", "http.client", "json", "logging", "unittest"]:
    importlib.import_module(name)

everything = every_code_object()
guarded_ones = [one for one in everything if one.co_exceptiontable]
code_bytes = sum(len(one.co_code) for one in everything)
table_bytes = sum(len(one.co_exceptiontable) for one in everything)
share = len(guarded_ones) * 100 // len(everything)
weight = table_bytes * 100 / code_bytes

print(f"  code objects reachable  {len(everything)}")
print(f"  with a handler          {len(guarded_ones)}, about {share} percent")
print(f"  bytecode                {code_bytes} bytes")
print(f"  exception tables        {table_bytes} bytes, about {weight:.1f} percent")
""",
    varies="Every number here depends on which modules happen to be imported, so a browser "
    "and a bare interpreter and this notebook will all report something different. The "
    "proportions are the interesting part, and they stay in the same neighbourhood: about a "
    "quarter of all code objects guarded, and the tables costing a few percent of the "
    "bytecode.",
)


lesson.md("""
A few percent of the bytecode, for something that used to be instructions on the hot path. That is the trade in one number.

## Try it yourself

Three things to try.

The first is to find a `try` that is not free. The `NOP` at the top is there for the line number, and if the `try:` line and the first statement of the body can share a line number, it may not be needed. Try `try: f()` written on one line and compare.

The second is the stack depth field. Write a `try` around something that raises halfway through building a list, like `[1, 2, 1 / 0, 4]`, and look at what depth the table records for that range. Then work out what would go wrong if the interpreter jumped to the handler without trimming.

The third is nesting. Take a function with two `try` blocks side by side and one with two nested, and compare the tables. Ranges never overlap, so nesting has to be expressed as several rows rather than one row inside another, and it is worth seeing exactly how.

## What just happened

There is no instruction that starts a `try` and none that ends one. The instructions for a guarded line are the same as the instructions for an unguarded one.

What the compiler writes instead is the exception table: a bytes object on the code object, one entry per range of instructions that is covered by a handler.

Each entry is five numbers. Where the range starts, how long it is, where to jump, how tall the value stack should be on arrival, and whether to push the raising offset first.

The encoding is a varint with six data bits per byte, and the top bit of the first byte of each entry is reserved as a marker. That marker is what lets the interpreter binary search a table of variable sized entries.

When something raises, the interpreter looks up the current offset. If it finds a handler it trims the stack to the recorded depth and jumps. If it does not, it adds this frame to the traceback and asks the caller the same question.

So not raising is free, and raising costs about fifty nanoseconds per frame crossed, most of it building the traceback rather than reading the table.

The `lasti` flag exists so that a `finally` that re-raises can point the traceback back at the original `raise` rather than at itself. The offset is pushed as a tagged integer, which is the E04 trick doing real work.

A `for` loop deliberately does not use any of this. Iteration is too common to end with an exception, so `FOR_ITER` jumps instead.

## What is next

E06 is specialization. The same instruction, `BINARY_OP`, does something different depending on what it saw last time it ran. The interpreter watches the types going past, and once it is confident it rewrites the instruction in place into a version that only handles that case and checks it is still right. The bytecode you disassemble on the first call is not the bytecode that is running by the thousandth, and you can watch it change.
""")


raise SystemExit(lesson.save())
