#!/usr/bin/env python
"""E10. The compiler that finished before you started.

The tenth lesson of the interpreter part, and the last step of the tier two story. E07
recorded a trace, E09 shortened it, and something has still been walking the result one
operation at a time. This lesson is about not walking it.

The technique is copy and patch, and the reason it deserves a lesson of its own is that it
moves almost all of the work to build time. By the time your loop gets hot, the machine code
for every micro operation already exists. What happens at run time is a copy and a handful of
addresses written into blanks, and both halves of that are measurable from Python.

Everything here needs the JIT switched on, so the experiments run in a fresh interpreter the
same way E07 and E09 did, using the same shipping helper.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("e10-the-compiler-that-finished-before-you-started", "e10")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("e10-the-compiler-that-finished-before-you-started").figure


lesson.md(f"""
# E10. The compiler that finished before you started

{badge}

Ask a hot loop for its machine code and you get bytes back. Real ones, the kind the processor runs.

Here are two loops that differ in one name. Each of them compiles to 1637 bytes. Twenty two of those bytes are different.

{figure("where-the-machine-code-comes-from", "the path from bytecodes.c through clang to the machine code in your process")}

The other 1615 were compiled on somebody else's machine, months before you wrote either loop.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/jit.c:644-659@v3.15.0rc1#_PyJIT_Compile`.

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

Same warning as E07 and E09, with one extra condition. Tier two has to be in your build, and this lesson also needs the part of tier two that emits machine code, which is a separate build option again. Plenty of perfectly normal CPython builds have neither. Every cell prints what it found rather than assuming, so it will say so.

The byte counts below also depend on your processor and your operating system. The shapes do not, and the shapes are the lesson.
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
## Getting at the machine code

The JIT is off unless `PYTHON_JIT=1` was set before the interpreter started, and a notebook has already started. So this lesson does what E07 and E09 did: it writes a small function, ships the source of it to a fresh interpreter with the variable set, and reads back what got printed.

An executor has a method nobody talks about much. `get_jit_code` hands you the compiled function as a `bytes` object, so you can measure it, compare it and go looking through it.

{lesson.claim("an executor hands back its compiled machine code as bytes, rounded up to a whole page")}
""")


lesson.code(
    """
import inspect
import os
import subprocess
import sys

jit = getattr(sys, "_jit", None)
print(f"  compiled into this build   {jit.is_available() if jit else False}")
print(f"  switched on right here     {jit.is_enabled() if jit else False}")


def with_the_jit(body, *also, **values):
    if jit is None or not jit.is_available():
        return "  this build has no JIT in it, so there is nothing to switch on"
    header = "".join(f"{name} = {value!r}" + chr(10) for name, value in values.items())
    shipped = "".join(inspect.getsource(one) + chr(10) for one in also)
    script = header + shipped + inspect.getsource(body) + f"{chr(10)}{body.__name__}(){chr(10)}"
    try:
        done = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env=dict(os.environ, PYTHON_JIT="1"),
            timeout=300,
        )
    except OSError:
        return "  this runtime cannot start another interpreter, so try this on a real machine"
    return (done.stdout + done.stderr).rstrip()


def trace_of(one):
    import _opcode

    code = one.__code__
    for offset in range(0, len(code.co_code), 2):
        try:
            found = _opcode.get_executor(code, offset)
        except ValueError:
            continue
        if found is not None:
            return found
    return None


def first_look():
    import mmap

    def loop(n):
        total = 0
        for i in range(n):
            total += i
        return total

    loop(20000)
    found = trace_of(loop)
    raw = found.get_jit_code()
    used = raw.rstrip(b"\\x00")
    print(f"  micro operations in the trace   {len(found)}")
    print(f"  bytes handed back               {len(raw)}")
    print(f"  a whole number of pages         {len(raw) % mmap.PAGESIZE == 0}")
    print(f"  bytes that are not padding      {len(used)}")
    print(f"  the first sixteen of them       {used[:16].hex(' ')}")


print()
print(with_the_jit(first_look, trace_of))
""",
    varies="Whether anything prints at all depends on your build having both tier two and the "
    "machine code half of it, which a browser does not. The byte counts depend on your "
    "processor, and the hex line will be different on every run because it contains addresses.",
)


lesson.md(f"""
Those sixteen bytes are instructions for whatever processor you are sitting in front of. Nothing in this lesson decodes them, and you do not need them decoded. What matters is where they came from.

## The size is settled before a byte is written

Start with the thing that gives the whole design away.

The function that builds an executor's machine code does two loops over the trace. The first one adds up a fixed size per micro operation and writes down where each one will start. Only then does it ask for memory {cite("Python/jit.c:644-659@v3.15.0rc1#_PyJIT_Compile")}.

{figure("size-first-then-bytes", "the two loops of _PyJIT_Compile, sizing then emitting")}

A compiler that decides how big its output is before generating any of it is a strange compiler. It can only work if the size of the output for each micro operation is already known, which means the output for each micro operation already exists.

You can see the consequence without reading any C. Take a loop, add more work to the body, and watch the machine code grow.

{lesson.claim("machine code size grows by a fixed amount for each micro operation added to the trace")}
""")


lesson.code(
    """
def code_size():
    def build(adds):
        body = " + ".join(["total"] + ["n"] * adds)
        head = ["def f(n):", "    total = 0", "    for _ in range(n):"]
        tail = ["        total = " + body, "    return total", ""]
        source = chr(10).join(head + tail)
        space = {}
        exec(compile(source, "<made here>", "exec"), space)
        return space["f"]

    print("  additions   operations   bytes   difference")
    before = None
    for adds in (1, 2, 3, 4, 6, 10):
        one = build(adds)
        one(20000)
        found = trace_of(one)
        size = len(found.get_jit_code().rstrip(b"\\x00"))
        step = "" if before is None else str(size - before)
        print(f"  {adds:9d}   {len(found):10d}   {size:5d}   {step:>10}")
        before = size


print(with_the_jit(code_size, trace_of))
""",
    varies="On this machine 3.15 gives 320 more bytes for every extra addition and 3.14 gives "
    "384, and the numbers themselves will be different on yours. The column to read is the last "
    "one: the same increase, every time, with no rounding and no drift.",
)


lesson.md(f"""
{figure("the-code-grows-in-a-straight-line", "a table of additions against micro operations and bytes of machine code")}

Each extra addition costs the same number of extra bytes. Not roughly the same. Exactly the same, because the size is a sum of fixed numbers looked up per operation.

That also tells you what the JIT cannot do. A real optimizing compiler would notice that the third addition looks like the second and share something between them. This one cannot, because it never looks at two operations at once. Everything clever already happened, back in E09, on the list of micro operations.

## One chunk per micro operation

So where do the fixed size chunks come from?

They are built when CPython is built, and the recipe is short. `Python/bytecodes.c` is the file the interpreter is written in, and a build step turns it into `Python/executor_cases.c.h`, one C case per micro operation. Then, for each of those cases, the build writes out a tiny C file containing one function whose body is that single case {cite("InternalDocs/jit.md:123-138@v3.15.0rc1")}.

The tiny file is made by taking a template and replacing the word `CASE` {cite("Tools/jit/_targets.py:322-330@v3.15.0rc1")}. The template is a real function with a real signature, so what comes out really is one small C function per micro operation {cite("Tools/jit/template.c:123-133@v3.15.0rc1#_JIT_ENTRY")}.

Each of those files is then compiled by clang, once, at build time. The flags are worth a look, because they are chosen for a job no normal build has {cite("Tools/jit/_targets.py:212-229@v3.15.0rc1")}. `-Os` rather than `-O2`, because the passes that make a standalone function fast make a chunk that has to be glued to other chunks worse. No builtins and no stack protector, because those call into things that cannot be found later. The results are read back out of the object files and written into a header that ships inside the interpreter {cite("InternalDocs/jit.md:140-149@v3.15.0rc1")}.

The finished chunks are called {term("stencil")}s, and pasting them together is {term("copy and patch")}.

One consequence you can measure: a micro operation costs about the same wherever it turns up, so the size of a trace's machine code tracks its length across completely different programs.

{lesson.claim("different loop bodies produce a similar number of machine code bytes per micro operation")}
""")


lesson.code(
    """
def per_operation():
    def build(setup, body):
        head = ["def f(n):", "    total = 0"]
        if setup:
            head.append("    " + setup)
        tail = ["    for _ in range(n):", "        " + body, "    return total", ""]
        source = chr(10).join(head + tail)
        space = {}
        exec(compile(source, "<made here>", "exec"), space)
        return space["f"]

    rows = [
        ("", "total += 1"),
        ("", "total = total + n"),
        ("s = 'abc'", "total += len(s)"),
        ("", "total += n * 2 - 1"),
        ("d = {'k': 1}", "total += d['k']"),
    ]
    print("  loop body             operations   bytes   bytes each")
    for setup, body in rows:
        one = build(setup, body)
        one(20000)
        found = trace_of(one)
        size = len(found.get_jit_code().rstrip(b"\\x00"))
        print(f"  {body:20}  {len(found):10d}   {size:5d}   {size / len(found):10.1f}")


print(with_the_jit(per_operation, trace_of))
""",
    varies="On this machine the last column sits between 41 and 48 on 3.15 whatever the loop "
    "does, and between 87 and 100 on 3.14. Your processor will give different numbers again. The "
    "narrow spread within one release is the point, not the value.",
)


lesson.md(f"""
Five loops that have almost nothing to do with each other, and the cost per micro operation barely moves. That is what you get when the output is a lookup rather than a decision.

## The blank that only your program can fill

A chunk compiled months ago cannot contain the address of an object you created this morning. So it does not. It contains a blank where the address goes.

The way the blanks are made is a trick worth knowing about. The template declares a variable whose value is the address of an external symbol that does not exist anywhere {cite("Tools/jit/jit.h:6-8@v3.15.0rc1#PATCH_VALUE")}. clang has no idea what that address is, so it leaves the usual note for the linker: fill in this many bytes at this offset once you know. Nobody ever links it. The note is kept instead, and it becomes the blank.

CPython's own name for one of those notes says exactly this {cite("Tools/jit/_stencils.py:149-172@v3.15.0rc1#Hole")}. Each one carries an offset into the chunk, and what to write there is a short C expression picked from a table {cite("Tools/jit/_stencils.py:106-128@v3.15.0rc1#_HOLE_EXPRS")}.

{figure("what-goes-in-a-hole", "the blanks left in a stencil and what gets written into each one")}

Every entry in that table is an address of some kind, and addresses are the one thing a build cannot know.

Here is the most concrete of them. When E09's optimizer bakes a global into the trace, what it stores is a pointer to the object. That pointer ends up written into the machine code, and you can go and find it.

{lesson.claim("the address of a baked in constant appears literally inside the compiled machine code")}
""")


lesson.code(
    """
def find_the_address():
    import struct

    global TARGET
    TARGET = 10**30

    def loop(n):
        total = 0
        for _ in range(n):
            total += TARGET
        return total

    loop(20000)
    found = trace_of(loop)
    code = found.get_jit_code().rstrip(b"\\x00")
    carrying = [step[0] for step in found if "CONST_INLINE" in step[0]]
    wanted = struct.pack("<Q", id(TARGET))
    spots = [i for i in range(len(code) - 7) if code[i : i + 8] == wanted]
    print(f"  operations carrying a constant   {carrying}")
    print(f"  where the object itself lives    {hex(id(TARGET))}")
    print(f"  that address, inside the code    {[hex(spot) for spot in spots]}")


print(with_the_jit(find_the_address, trace_of))
""",
    varies="The address is different on every run, and the offset it is found at depends on the "
    "release and the processor. What does not change is that it is in there, exactly once.",
)


lesson.md(f"""
The number Python is holding for you, sitting inside the machine code as eight bytes, put there by a copy and a write.

## Two loops, twenty two bytes apart

Now the measurement from the top of the lesson.

Two loops. Same shape, same length, same everything, except that one adds `ONE` and the other adds `TWO`. If the chunks really are copied rather than generated, the two results should be almost the same bytes, and the differences should be addresses.

{lesson.claim("two loops differing only in which constant they use compile to almost identical machine code")}
""")


lesson.code(
    """
def two_loops():
    import struct

    global ONE, TWO
    ONE = 10**30
    TWO = 10**31

    def build(name):
        head = ["def f(n):", "    total = 0", "    for _ in range(n):"]
        tail = ["        total += " + name, "    return total", ""]
        source = chr(10).join(head + tail)
        space = {"ONE": ONE, "TWO": TWO}
        exec(compile(source, "<made here>", "exec"), space)
        return space["f"]

    made = []
    for name in ("ONE", "TWO"):
        one = build(name)
        one(20000)
        made.append(trace_of(one).get_jit_code().rstrip(b"\\x00"))
    first, second = made
    shared = min(len(first), len(second))
    apart = [i for i in range(shared) if first[i] != second[i]]
    print(f"  bytes in each                {len(first)} and {len(second)}")
    print(f"  bytes that are different     {len(apart)}")
    print(f"  bytes that are the same      {shared - len(apart)}")
    for name, value in (("ONE", ONE), ("TWO", TWO)):
        wanted = struct.pack("<Q", id(value))
        here = [i for i in range(shared) if first[i : i + 8] == wanted]
        there = [i for i in range(shared) if second[i : i + 8] == wanted]
        print(f"  address of {name:3} found in the two   {here} {there}")


print(with_the_jit(two_loops, trace_of))
""",
    varies="The exact number of differing bytes moves a little from run to run, because the two "
    "allocations land at different addresses. It has been in the low twenties on 3.15 and in the "
    "forties on 3.14 here, out of one and a half to three thousand.",
)


lesson.md(f"""
{figure("two-loops-one-number-different", "two loops of the same length whose machine code differs in twenty two bytes")}

Ninety nine percent of the bytes are shared, and the address of each constant turns up in exactly one of the two, at the same offset. That is copy and patch in one output.

## The same opening, twice

The last check is the interesting direction. Two loops that are not the same, but that happen to start with the same micro operations.

Every trace of a `for` loop over `range` begins the same way, whatever the body does. If the chunks are copied, the machine code should begin the same way too.

{lesson.claim("two different loops that share a prefix of micro operations share most of their opening bytes")}
""")


lesson.code(
    """
def same_opening():
    def build(body):
        head = ["def f(n):", "    total = 0", "    for _ in range(n):"]
        tail = ["        " + body, "    return total", ""]
        source = chr(10).join(head + tail)
        space = {}
        exec(compile(source, "<made here>", "exec"), space)
        return space["f"]

    made = []
    for body in ("total = total + n", "total = total + n + n"):
        one = build(body)
        one(20000)
        found = trace_of(one)
        made.append(([step[0] for step in found], found.get_jit_code().rstrip(b"\\x00")))
    (names, first), (others, second) = made
    shared = 0
    for left, right in zip(names, others, strict=False):
        if left != right:
            break
        shared += 1
    print(f"  operations in the two traces     {len(names)} and {len(others)}")
    print(f"  operations matching from the top {shared}")
    print(f"  the first four of them           {names[:4]}")
    for window in (200, 400, 600):
        same = sum(1 for i in range(window) if first[i] == second[i])
        print(f"  of the first {window} bytes, the same  {same}")


print(with_the_jit(same_opening, trace_of))
""",
    varies="Here the first two hundred bytes come out 93 percent the same on 3.15 and 99 percent "
    "on 3.14, and the agreement falls away further in, because jump targets and exit stubs move "
    "once the two traces stop matching. The exact counts move between runs.",
)


lesson.md(f"""
Two loops that were never compiled together, that share no code object and no constants, and over ninety percent of the first few hundred bytes of their machine code are the same. They start with the same micro operations, so they start with the same chunks.

## And then it stops being writable

One last thing happens, and it is the reason none of this is a security hole.

The memory the chunks are copied into is asked for as readable and writable, and it is never asked for as executable. Once the copying and patching are done, the permissions are changed to readable and executable, and the ability to write to it is given up in the same call. The comment in the source is blunt about it {cite("Python/jit.c:163-188@v3.15.0rc1#mark_executable")}. The instruction cache gets flushed at the same moment, because the processor is entitled to assume that memory holding instructions does not change under it.

{figure("then-it-stops-being-writable", "one page of JIT memory going from writable to executable")}

That allocation is asked for in whole pages, because that is the unit permissions are set on {cite("Python/jit.c:116-143@v3.15.0rc1#jit_alloc")}. Which is why the first cell of this lesson got a page sized answer for a loop that needed about a thousand bytes.

{lesson.claim("the memory an executor is given is a whole number of pages, most of it unused for a short trace")}
""")


lesson.code(
    """
def pages():
    import mmap

    def build(adds):
        body = " + ".join(["total"] + ["n"] * adds)
        head = ["def f(n):", "    total = 0", "    for _ in range(n):"]
        tail = ["        total = " + body, "    return total", ""]
        source = chr(10).join(head + tail)
        space = {}
        exec(compile(source, "<made here>", "exec"), space)
        return space["f"]

    print(f"  one page on this machine is {mmap.PAGESIZE} bytes")
    print("  additions   bytes used   pages taken   left over")
    for adds in (1, 10, 30, 50):
        one = build(adds)
        one(20000)
        found = trace_of(one)
        raw = found.get_jit_code()
        used = len(raw.rstrip(b"\\x00"))
        print(f"  {adds:9d}   {used:10d}   {len(raw) // mmap.PAGESIZE:11d}   {len(raw) - used:9d}")


print(with_the_jit(pages, trace_of))
""",
    varies="Page size is 16384 on Apple silicon and 4096 on most other machines, so the last two "
    "columns will look quite different on yours. The shape is the same either way: short traces "
    "waste most of a page, and long ones take more than one.",
)


lesson.md("""
Short traces leave most of a page unused. That is the price of being able to set permissions at all, and it is a large part of why the JIT is not switched on by default yet.

## Try it yourself

Three things worth trying, all small edits to the cells above.

The first is to work out the cost of one particular micro operation. Pick two loop bodies that differ by exactly one operation in the trace, take the difference in bytes, and you have measured one stencil. Do it for a few and you will find that the cheap looking ones are not always the small ones.

The second is to go looking for something other than a constant. `find_the_address` searched for the address of an object. Try searching for the address of the code object, or of the executor itself, and see how many times each turns up.

The third is to find the ceiling. Traces have a maximum length, and the machine code has a maximum size that the source complains about by name. Build loops with more and more in the body until you stop getting an executor, and see which limit you hit first.

## What just happened

E07 recorded a trace and E09 shortened it. This lesson was about what happens to the result.

An executor will hand you its machine code as bytes. It is a whole number of pages, most of which is padding for a short trace, and the part that is not padding is real instructions.

The compiler that produced them does two loops. The first adds up a fixed size per micro operation and asks for that much memory. The second copies a chunk per micro operation into it. Deciding the size before generating anything only makes sense if the generating already happened, and it did.

It happened when CPython was built. One small C file per micro operation, made by pasting a single case into a template, compiled by clang with flags chosen for code that will be glued to other code, and the results stored in a header inside the interpreter.

The chunks have blanks in them, made by taking the address of a symbol that does not exist so the compiler leaves a relocation note behind. CPython keeps the notes and calls them holes. Every one of them is filled with an address, and you can find the address of a baked in constant sitting in the bytes.

Two loops that differ in one name give machine code that is ninety nine percent identical. Two loops that share nothing but their opening micro operations share most of their opening bytes.

Then the memory stops being writable and starts being executable, in one call, with the instruction cache flushed.

## What is next

E11 goes back to the interpreter that runs everything else, the one that has been doing the work in every lesson before this one, and asks a question about how it is written. The eval loop is a very large switch statement inside a very large function, and there is a second way to write the same thing: one small function per opcode, each ending by calling the next one, with the compiler asked very firmly not to grow the stack. It sounds slower and it is not, the reason is about registers rather than calls, and the two versions are both in the source right now.
""")


raise SystemExit(lesson.save())
