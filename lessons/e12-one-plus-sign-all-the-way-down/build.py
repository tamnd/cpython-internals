#!/usr/bin/env python
"""E12. One plus sign, all the way down.

The last lesson of the interpreter part. It introduces nothing new. It takes one character
of Python source, a plus sign in a loop, and follows it through every layer the previous
eleven lessons built up: the line of the instruction DSL it comes from, the instruction the
compiler emits, the cache slots behind it, the specialized instruction that overwrites it,
the micro operations it becomes in a trace, what the optimizer leaves of those, and the
machine code at the end.

The spine of the lesson is one line of `Python/bytecodes.c`. Every measurement here is a
consequence of that line, which is a better argument for the DSL than any amount of prose
about it.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("e12-one-plus-sign-all-the-way-down", "e12")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("e12-one-plus-sign-all-the-way-down").figure


lesson.md(f"""
# E12. One plus sign, all the way down

{badge}

Nothing in this lesson is new. That is the point of it.

Here is a line of Python: `total = total + i`. One of those characters is a plus sign, and by now you have met every layer it passes through. This lesson puts them in a row and follows the plus sign down.

{figure("one-plus-sign-six-layers", "a plus sign turning into an instruction, a specialized instruction, micro operations and machine code")}

Six layers, one character, and every one of them measurable from the notebook you are reading.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/bytecodes.c:705-709@v3.15.0rc1`.

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

The first six cells run anywhere, including a browser. The last three need tier two and the machine code half of it, which is a build option most people do not have switched on. Those cells say so rather than failing, the same way E07 to E10 did.

## Which interpreter is this
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
## Where the plus sign is written down

Start at the bottom, in the file the whole interpreter is generated from.

The general case is one line {cite("Python/bytecodes.c:5948-5978@v3.15.0rc1")}. Reading the last line of that block: a `BINARY_OP` is a piece that may specialize, two pieces that write down what types turned up, four unused cache slots, the addition itself, and two pops. The word `unused` there is not a comment. It reserves space in the code object.

The specialized version for two ints is one line as well {cite("Python/bytecodes.c:702-709@v3.15.0rc1")}. Same shape, with the specializing piece replaced by two guards and the same number of cache slots reserved.

{figure("what-the-macro-line-says", "the pieces of macro(BINARY_OP_ADD_INT) and where each one shows up")}

Those reserved slots are the {term("inline cache")}, and you can count them from Python without any of this. An instruction is two bytes. If the next instruction starts twelve bytes later, ten of those bytes are cache, which is five slots of two bytes each.

{lesson.claim("BINARY_OP occupies twelve bytes in a code object, two for the instruction and ten for five cache slots")}
""")


lesson.code(
    """
import dis


def work(n):
    total = 0
    for i in range(n):
        total = total + i
    return total


steps = list(dis.get_instructions(work))
print("  offset  instruction                          cache slots")
for one, following in zip(steps, [*steps[1:], None], strict=True):
    end = following.offset if following else len(work.__code__.co_code)
    print(f"  {one.offset:6d}  {one.opname:34}   {(end - one.offset - 2) // 2:11d}")
print(f"  {len(steps)} instructions in {len(work.__code__.co_code)} bytes")
""",
    differs="The function is 66 bytes on 3.15 and 62 on 3.14, because 3.15 gave `RESUME` and "
    "`GET_ITER` a cache slot each that they did not have before. `BINARY_OP` has five in both.",
)


lesson.md(f"""
`BINARY_OP` at some offset, and the next instruction ten bytes further on than it needs to be. That gap is the space the macro line reserved.

Notice that most instructions have no cache at all. Cache slots are not free, they make every code object bigger, so they go only where {term("specialization")} can use them.

## What running it changes

Nothing has run yet. The loop above was disassembled without ever being called, which is why every instruction in it is the general one.

Run it a few hundred times and the code object rewrites itself in place. This is E06's story, and it is worth seeing again on the exact instruction this lesson is following.

{lesson.claim("the instructions in a loop are replaced by narrower ones after the loop has run enough times")}
""")


lesson.code("""
def family(fn):
    wanted = ("BINARY_OP", "FOR_ITER", "CALL", "RESUME")
    found = dis.get_instructions(fn, adaptive=True)
    return [one.opname for one in found if one.opname.startswith(wanted)]


print(f"  before it ever ran  {family(work)}")
work(1000)
print(f"  after a thousand    {family(work)}")
""")


lesson.md(f"""
Three of the four changed. `BINARY_OP` became `BINARY_OP_ADD_INT`, the loop's `FOR_ITER` became the version that knows it is walking a range, and `RESUME` became the version that skips a check it has already done.

`CALL` did not change, and the reason is worth a moment. It is the call to `range`, and it happens once, before the loop starts. Specialization needs a few hundred trips to trigger, so an instruction that runs once stays general forever. Nothing is wasted on code that does not repeat.

## The same plus sign, six answers

The decision about what to become is made by one function, looking at the two operands that happened to turn up {cite("Python/specialize.c:2364-2400@v3.15.0rc1#_Py_Specialize_BinaryOp")}.

Read the order of the checks. Both operands have to be the same type, or it gives up immediately. Then strings, then small ints, then floats.

{figure("the-decision-tree", "the same plus sign specializing six different ways")}

Same source, same compiler output, six different instructions depending only on what flowed through.

{lesson.claim("the same expression specializes to different instructions depending on the types that turn up at run time")}
""")


lesson.code(
    """
def made(body):
    lines = ["def f(a, b):"] + ["    " + one for one in body]
    space = {}
    exec(compile(chr(10).join([*lines, ""]), "<made here>", "exec"), space)
    return space["f"]


def which(fn):
    found = dis.get_instructions(fn, adaptive=True)
    named = (one.opname for one in found if one.opname.startswith("BINARY_OP"))
    return next(named, "no BINARY_OP at all")


rows = [
    ("1 + 2", ["return a + b"], (1, 2)),
    ("1.5 + 2.5", ["return a + b"], (1.5, 2.5)),
    ("'x' + 'y'", ["return a + b"], ("x", "y")),
    ("1 + 2.5", ["return a + b"], (1, 2.5)),
    ("[1] + [2]", ["return a + b"], ([1], [2])),
    ("9 * 4", ["return a * b"], (9, 4)),
    ("9 - 4", ["return a - b"], (9, 4)),
    ("9 / 4", ["return a / b"], (9, 4)),
]
for label, body, args in rows:
    one = made(body)
    for _ in range(20):
        one(*args)
    print(f"  {label:12} {which(one)}")
""",
    differs="One row moved between the releases. Adding two lists is `BINARY_OP_EXTEND` on 3.15 "
    "and stays the general `BINARY_OP` on 3.14, because 3.15 added a way to specialize operations "
    "whose fast path lives outside the instruction itself.",
)


lesson.md(f"""
Division has no fast path at all, so it stays general no matter how many times you run it. Mixing an int and a float gives `BINARY_OP_EXTEND`, which is the escape hatch for pairs that have a fast path somewhere else.

## It also looks at what comes next

There is one case in that function that does something stranger. When both operands are strings, it peeks at the instruction after this one, and if that instruction stores the result back into the same local the left operand came from, it picks a different specialization {cite("Python/specialize.c:2383-2392@v3.15.0rc1")}.

The reason is that `s = s + t` is the one shape where the old string is about to be thrown away, so the addition is allowed to extend it in place instead of building a new one. That is why appending to a string in a loop is not the quadratic disaster it is in most languages.

Two functions that differ only in which name the result lands in get two different instructions.

{lesson.claim("adding strings specializes differently depending on whether the result is stored back into the left operand")}
""")


lesson.code("""
back = made(["a = a + b", "return a"])
elsewhere = made(["c = a + b", "return c"])
for _ in range(20):
    back("x", "y")
    elsewhere("x", "y")

print(f"  a = a + b   {which(back)}")
print(f"  c = a + b   {which(elsewhere)}")
""")


lesson.md(f"""
One instruction of lookahead, and a loop that would otherwise copy the whole string every time gets to grow it instead.

## What it becomes in a trace

Now the tier two half, which needs a build with the JIT compiled in. The next three cells say so if yours does not.

The macro line said `BINARY_OP_ADD_INT` is six micro operations: two guards, the addition, and two pops. What ends up in a trace is not six, because the optimizer from E09 gets there first.

{lesson.claim("the micro operations a specialized instruction expands to are visible in the trace an executor holds")}
""")


lesson.code(
    """
import inspect
import os
import subprocess

jit = getattr(sys, "_jit", None)


def with_the_jit(body, *also):
    if jit is None or not jit.is_available():
        return "  this build has no JIT in it, so there is nothing to switch on"
    shipped = "".join(inspect.getsource(one) + chr(10) for one in also)
    script = shipped + inspect.getsource(body) + f"{chr(10)}{body.__name__}(){chr(10)}"
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


def three_additions():
    def work(n):
        total = 0
        for i in range(n):
            total = total + i + i + i
        return total

    work(20000)
    found = trace_of(work)
    for step in found:
        if not any(word in step[0] for word in ("EXIT", "DEOPT", "ERROR")):
            print(f"  {step[0]}")


print(with_the_jit(three_additions, trace_of))
""",
    varies="Nothing prints here unless your build has tier two and the machine code half of it, "
    "which a browser does not. The list is a little different on 3.14, which has one guard here "
    "rather than two and keeps more bookkeeping between the additions.",
)


lesson.md(f"""
{figure("first-time-and-every-time-after", "the first addition with its guards next to the two that follow it")}

Read the three additions in that list. The first one has guards in front of it. The second and third have none, because nothing between them could have changed what the values are, which is exactly the argument E09 made.

The second and third are also a different operation. `_BINARY_OP_ADD_INT_INPLACE` is the version that mutates its left operand instead of allocating a result, and it is allowed because the optimizer knows that intermediate value has nobody else holding it.

So the first plus sign in the line costs three micro operations and each one after it costs one.

## A different type, a different family

Change the values from ints to floats and the whole chain changes with them, from the specialized instruction down to which pop instruction gets used.

{lesson.claim("adding floats produces a different guard, a different addition and a different pop than adding ints")}
""")


lesson.code(
    """
def floats():
    def work(n):
        total = 0.0
        for _ in range(n):
            total = total + 1.5
        return total

    work(20000)
    found = trace_of(work)
    for step in found:
        if any(word in step[0] for word in ("FLOAT", "CONST", "BINARY")):
            print(f"  {step[0]}")


print(with_the_jit(floats, trace_of))
""",
    varies="On a build with the JIT this prints a float guard, a float addition and a float pop. "
    "The exact set moves between releases as the optimizer learns to drop more of them.",
)


lesson.md(f"""
A guard that checks for a float, an addition that adds two floats without checking anything, and a pop that knows it is dropping a float and can skip asking what type it was. The constant `1.5` is not looked up either, it was baked into the trace.

## All of it at once

One last cell, which prints the whole journey for a single plus sign in a single loop.

{lesson.claim("one plus sign in a loop can be followed from its instruction through its cache slots and micro operations to its machine code")}
""")


lesson.code(
    """
def all_layers():
    import dis

    def work(n):
        total = 0
        for i in range(n):
            total = total + i
        return total

    work(20000)
    steps = list(dis.get_instructions(work, adaptive=True))
    plus = next(one for one in steps if one.opname.startswith("BINARY_OP"))
    after = next(one for one in steps if one.offset > plus.offset)
    found = trace_of(work)
    names = [step[0] for step in found]
    where = names.index("_BINARY_OP_ADD_INT")
    code = found.get_jit_code().rstrip(b"\\x00")
    print(f"  the instruction, now         {plus.opname}")
    print(f"  bytes it takes in the code   {after.offset - plus.offset}")
    print(f"  micro operations it becomes  {names[where - 2 : where + 1]}")
    print(f"  micro operations in total    {len(found)}")
    print(f"  machine code for all of them {len(code)} bytes")


print(with_the_jit(all_layers, trace_of))
""",
    varies="The byte count is a property of your processor and the two releases give quite "
    "different numbers, 1253 against 2804 on this machine. The twelve bytes in the code object "
    "are the same everywhere, because that is decided by the macro line rather than by hardware.",
)


lesson.md(f"""
{figure("the-same-plus-in-six-places", "one addition named six different ways at six different layers")}

## Try it yourself

Three things worth trying, all small edits.

The first is to break the specialization. Take the int loop and make one of the values enormous, larger than a machine word, and watch which instruction it settles on. Compact ints and long ones are not the same fast path.

The second is to find another lookahead. The string case is not the only place the specializer peeks at the next instruction, and `Python/specialize.c` is readable enough to go looking. Then build a pair of functions that differ only in what comes next and see if you can make them specialize differently.

The third is to run the trace cell with two additions instead of three, then four, then five, and count how the micro operations grow. The first one costs three and the rest cost one, so the arithmetic is easy to predict and worth predicting before you run it.

## What you now know

Eleven lessons of machinery, followed through one character.

A plus sign compiles to `BINARY_OP`, which occupies two bytes and reserves ten more for five cache slots. Both of those facts come from one line of `Python/bytecodes.c`, and you counted them from Python without reading any C.

A few hundred trips later the instruction rewrites itself in place. Which instruction it becomes is decided by looking at the two operands, and for strings, at what the next instruction is going to do with the result. That last check is why building a string in a loop is fast.

If the loop gets hot enough and the build has tier two, the specialized instruction expands into micro operations: two guards and an addition. The optimizer then deletes the guards for every addition after the first, and swaps the addition for a version that mutates its left operand, because it can prove nobody else is holding it.

Those micro operations are turned into machine code by pasting together chunks that were compiled months earlier, with the addresses filled into blanks.

Six layers, and not one of them invented anything. Each is the layer above it, written out in more detail, with the things that could not be known earlier filled in as soon as they could be.

## What is next

That is the interpreter part finished. Twelve lessons, from the eval loop nobody wrote by hand to the machine code nobody wrote at all.

The next part is memory, starting with the allocator. Every object in every lesson so far arrived from somewhere and went away again, and none of those lessons said where. It turns out to be four layers deep, none of them is `malloc` in the way you would expect, and the first measurement is that asking Python for a small object usually does not ask the operating system for anything at all.
""")


raise SystemExit(lesson.save())
