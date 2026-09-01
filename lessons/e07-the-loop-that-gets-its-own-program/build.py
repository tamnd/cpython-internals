#!/usr/bin/env python
"""E07. The loop that gets its own program.

The seventh lesson of the interpreter part. E06 rewrote one instruction at a time. This one
replaces a whole run of them.

The hook is that a hot loop stops being bytecode. After four thousand trips round, the
interpreter records one real trip through as a list of much smaller operations, optimizes that
list, and hands back an object that runs instead of the loop. The object is reachable from
Python and you can print every operation in it.

Everything here needs the JIT switched on, which is an environment variable read at startup,
so the lesson runs its experiments in a fresh interpreter and prints what came back. That is
also honest about the shape of the feature: you have to ask for it.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("e07-the-loop-that-gets-its-own-program", "e07")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("e07-the-loop-that-gets-its-own-program").figure


lesson.md(f"""
# E07. The loop that gets its own program

{badge}

E06 ended with an instruction rewriting itself. That is as far as one instruction can go on its own, and there is a ceiling on it: each instruction is still fetched and dispatched separately, and it still knows nothing about the instruction beside it.

So there is a second thing, for loops that keep going round. After four thousand trips, the interpreter follows one real trip through and writes down everything it did as a list of much smaller operations. Then it optimizes that list, and hands back an object that runs in place of the loop.

{figure("where-a-hot-loop-goes", "a loop running as bytecode, being recorded, and coming back as an optimized executor")}

The object is a real Python object. You can fetch it and print every operation in it, which is what this lesson mostly does.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/bytecodes.c:3556-3583@v3.15.0rc1#_JIT`.

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

This is the least portable lesson in the part. Tier two arrived in 3.13, changed a lot in 3.14 and changed again in 3.15, and whether it exists at all is a build option rather than a version. Every cell below says what it found rather than assuming, so it will tell you honestly if your build cannot do this.
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
## You have to ask for it

The JIT is compiled into most builds and switched off. Turning it on means setting `PYTHON_JIT=1` before the interpreter starts, so there is no way to switch it on from inside a notebook that is already running.

What there is instead is `sys._jit`, which will tell you what your build can do, and the ability to start another interpreter with the variable set. CPython has its own write up of the whole mechanism, and it is short and readable {cite("InternalDocs/jit.md:37-48@v3.15.0rc1")}. Every experiment below runs that way: a small script, a fresh interpreter, and whatever it printed comes back as a string.

{lesson.claim("the JIT is a build option and a startup flag rather than something a running program can turn on")}
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


def with_the_jit(body, **values):
    if jit is None or not jit.is_available():
        return "  this build has no JIT in it, so there is nothing to switch on"
    header = "".join(f"{name} = {value!r}" + chr(10) for name, value in values.items())
    script = header + inspect.getsource(body) + f"{chr(10)}{body.__name__}(){chr(10)}"
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


def report():
    import sys

    print(f"  switched on over there     {sys._jit.is_enabled()}")


print()
print(with_the_jit(report))
""",
    varies="A browser cannot start another process and does not have the JIT anyway, so all "
    "three answers there are the polite version of no. On a desktop build from python.org or "
    "from `uv` the first answer is True and the second is False, which is the interesting "
    "combination: it is there, and it is off until you ask.",
)


lesson.md(f"""
## The instruction that knows

Before anything gets traced, something small and pleasing happens.

`JUMP_BACKWARD` is a specialization family, exactly like the ones in E06. It has two forms, and which one it becomes is decided on its first execution by asking whether the JIT is on {cite("Python/bytecodes.c:3539-3554@v3.15.0rc1#_SPECIALIZE_JUMP_BACKWARD")}.

So the name of the instruction tells you which mode you are in, and the version with the JIT off does not even carry the code that would check the counter {cite("Python/bytecodes.c:3591-3600@v3.15.0rc1#JUMP_BACKWARD_JIT")}.

{lesson.claim("the backward jump in a loop specializes into one of two named forms depending on whether the JIT is switched on")}
""")


lesson.code(
    """
import dis

LOOP = "def f(n):\\n    total = 0\\n    for i in range(n):\\n        total += i\\n    return total\\n"


def show_jump():
    import dis

    space = {}
    exec(compile(LOOP, "<made here>", "exec"), space)
    one = space["f"]
    one(10)
    for step in dis.get_instructions(one, adaptive=True):
        if "JUMP_BACKWARD" in step.opname:
            print(f"  with the jit on   {step.opname}")


space = {}
exec(compile(LOOP, "<made here>", "exec"), space)
here = space["f"]
here(10)
for step in dis.get_instructions(here, adaptive=True):
    if "JUMP_BACKWARD" in step.opname:
        print(f"  in this process   {step.opname}")

print(with_the_jit(show_jump, LOOP=LOOP))
""",
    varies="The first line says `JUMP_BACKWARD_NO_JIT` everywhere, including in a browser "
    "where there is no JIT to switch on, because the family is compiled in either way and the "
    "off form is the one that gets chosen. The second line is the interesting one, and it only "
    "appears where a second interpreter can be started.",
)


lesson.md(f"""
## Four thousand turns

E06's counter was two, and this one is four thousand {cite("Include/internal/pycore_backoff.h:120-136@v3.15.0rc1#JUMP_BACKWARD_INITIAL_VALUE")}.

Rather than take that number on faith, find it. Run the loop with a given number of iterations, ask whether an executor appeared, and binary search on the answer.

{lesson.claim("a loop needs a few thousand iterations before it grows a trace, and the exact number is findable by searching for it")}
""")


lesson.code(
    """
def find_threshold():
    import _opcode
    import dis

    def make():
        space = {}
        exec(compile(LOOP, "<made here>", "exec"), space)
        return space["f"]

    def has_a_trace(one):
        for step in dis.get_instructions(one, adaptive=True):
            try:
                _opcode.get_executor(one.__code__, step.offset)
            except ValueError:
                continue
            return True
        return False

    low, high = 1, 20000
    while low < high:
        middle = (low + high) // 2
        one = make()
        one(middle)
        if has_a_trace(one):
            high = middle
        else:
            low = middle + 1
    print(f"  iterations before a trace appears  {low}")


print(with_the_jit(find_threshold, LOOP=LOOP))
""",
    varies="This machine says 4002 on 3.15 and 4096 on 3.14, and a build with no JIT in it "
    "prints the refusal instead. The number is a build setting rather than a fact about Python. "
    "What it is not is small: this is thousands of trips, not two.",
)


lesson.md(f"""
Four thousand and two on 3.15, and the constant next to it in the header is 4000. On 3.14 the same search says 4096, so this is a number that moves.

The comment above that constant is worth reading, because it is the least tidy thing in this part of CPython and it is honest about why. The number wants to be one less than a prime, so that a loop does not keep landing on the same iteration every time it is considered. The comment records that 4095 did not work for one particular benchmark, because the tracer always ended up recording the iteration where the loop finished, which is the one trip through that is not representative.

Why so much larger than E06's two? Because recording and optimizing a trace is expensive, and unlike rewriting one instruction it can be wasted entirely. A loop that runs three thousand times and stops should not pay for it. The instruction that spends the counter and starts the recording is `_JIT`, and it is a handful of lines {cite("Python/bytecodes.c:3556-3583@v3.15.0rc1#_JIT")}.

## What a trace looks like

Here is the whole thing. A loop with one addition in it, run until it gets a trace, and then every operation in that trace printed. The function that turns a recorded trip into the object you are about to see is `_PyOptimizer_Optimize` {cite("Python/optimizer.c:124-140@v3.15.0rc1#_PyOptimizer_Optimize")}.

{lesson.claim("the trace attached to a hot loop is a readable object, and every micro operation in it can be printed from Python")}
""")


lesson.code(
    """
def dump_trace():
    import _opcode
    import dis

    space = {}
    exec(compile(LOOP, "<made here>", "exec"), space)
    one = space["f"]
    one(20000)
    for step in dis.get_instructions(one, adaptive=True):
        try:
            found = _opcode.get_executor(one.__code__, step.offset)
        except ValueError:
            continue
        print(f"  attached to {step.opname} at offset {step.offset}, {len(found)} operations")
        print()
        for at, item in enumerate(found):
            print(f"   {at:3}  {item[0]}")


print(with_the_jit(dump_trace, LOOP=LOOP))
""",
    varies="Which operations appear and how many there are moves with every release, and a "
    "build without the JIT prints the polite refusal instead. The shape is the part to read.",
)


lesson.md(f"""
On the run above that is five bytecode instructions turned into thirty one operations, which does not sound like a win until you look at where the list stops being straight. The count is different on 3.14 and it will be different again on the next release, so read the shape rather than the number.

`_JUMP_TO_TOP` is the loop closing on itself {cite("Python/bytecodes.c:6161-6167@v3.15.0rc1#_JUMP_TO_TOP")}. Everything above it runs on every trip. Everything below it is cold: those are the {term("side exit")}s, one per guard, and they only run if a guess turns out wrong {cite("Python/bytecodes.c:6183-6196@v3.15.0rc1#_EXIT_TRACE")}.

{figure("the-shape-of-an-executor", "an executor split into a straight line above the jump and cold tails below it")}

So the honest count on that run is twenty three operations on the hot path and eight tails nobody touches. And within those twenty three, look at what they are: `_CHECK_VALIDITY` asks whether anything has invalidated this trace, `_GUARD_NOT_EXHAUSTED_RANGE` is the loop condition turned into a bail out, and `_BINARY_OP_ADD_INT` is the specialized instruction from E06 showing up here with its guards split off into separate operations.

{figure("what-is-in-a-trace", "six of the operations in a small trace and what each one is doing")}

That splitting is the entire point.

## Six guards become one

A {term("trace")} is a straight line, so the optimizer can reason along it {cite("Python/optimizer_analysis.c:800-829@v3.15.0rc1#_Py_uop_analyze_and_optimize")}. Once a guard has checked that something is an int, a later guard asking the same question about the same value cannot fail, and it can go.

Here is a loop body with three additions in it. In tier one that is three specialized instructions, each carrying two type guards, so six guards run on every trip.

{figure("guards-per-iteration", "six type guards per iteration in tier one against one in the trace")}

{lesson.claim("the optimizer deletes guards it can prove cannot fail, so a trace runs far fewer checks than the instructions it came from")}
""")


lesson.code(
    """
THREE_ADDS = (
    "def f(n):\\n    total = 0\\n"
    "    for i in range(n):\\n        total = total + i + i + i\\n    return total\\n"
)


def count_guards():
    import _opcode
    import dis

    space = {}
    exec(compile(THREE_ADDS, "<made here>", "exec"), space)
    one = space["f"]
    one(20000)

    tier1 = [step.opname for step in dis.get_instructions(one, adaptive=True)]
    adds = [name for name in tier1 if name.startswith("BINARY_OP")]
    print(f"  additions in the bytecode    {adds}")

    for step in dis.get_instructions(one, adaptive=True):
        try:
            found = _opcode.get_executor(one.__code__, step.offset)
        except ValueError:
            continue
        names = [item[0] for item in found]
        stop = names.index("_JUMP_TO_TOP") + 1 if "_JUMP_TO_TOP" in names else len(names)
        hot = names[:stop]
        print(f"  type guards on the hot path  {[n for n in hot if n.startswith('_GUARD')]}")
        print(f"  additions on the hot path    {[n for n in hot if 'BINARY_OP' in n]}")


print(with_the_jit(count_guards, THREE_ADDS=THREE_ADDS))
""",
    varies="The exact guard names change between releases, and so does how many the optimizer "
    "manages to remove. What holds is the direction: fewer on the hot path than in the "
    "bytecode it came from.",
)


lesson.md(f"""
Six type guards in the bytecode, and the trace keeps one of them plus one overflow check.

Then look at the additions. The first stays `_BINARY_OP_ADD_INT`. The other two became `_BINARY_OP_ADD_INT_INPLACE`, because the optimizer could see that the intermediate result was not shared with anything and could be written over rather than allocated fresh. That is a saving you cannot get one instruction at a time, because the instruction on its own has no way to know where its input came from.

## The trace goes through the call

The other thing a straight line can do is cross a function call. If a loop calls a small function every time round, the recorder follows it in and the body of that function ends up inside the same trace.

{lesson.claim("a trace recorded from a loop containing a function call includes the body of that function, so the call boundary is gone from the hot path")}
""")


lesson.code(
    """
WITH_CALL = (
    "def helper(x):\\n    return x + 1\\n"
    "def f(n):\\n    total = 0\\n"
    "    for i in range(n):\\n        total += helper(i)\\n    return total\\n"
)


def show_inline():
    import _opcode
    import dis

    space = {}
    exec(compile(WITH_CALL, "<made here>", "exec"), space)
    one = space["f"]
    one(20000)
    for step in dis.get_instructions(one, adaptive=True):
        try:
            found = _opcode.get_executor(one.__code__, step.offset)
        except ValueError:
            continue
        names = [item[0] for item in found]
        print(f"  operations in the trace                  {len(names)}")
        print(f"  pushes a frame                           {'_PUSH_FRAME' in names}")
        print(f"  returns from one                         {'_RETURN_VALUE' in names}")
        print(f"  the addition from inside helper is here  {'_BINARY_OP_ADD_INT' in names}")


print(with_the_jit(show_inline, WITH_CALL=WITH_CALL))
""",
    varies="How much a trace inlines is a heuristic, so a different release may follow the "
    "call less far or not at all. When it does, the operations from the called function are "
    "in the same list as the ones from the loop.",
)


lesson.md(f"""
`helper` has its own code object and its own bytecode, and none of that matters here. Its addition is sitting in the same list as the loop's, with the frame push and the return still there as operations but no dispatch between them.

## What it is worth

Two loops, timed twice each: once in an interpreter with the JIT off and once with it on.

{figure("what-the-jit-is-worth", "two loops timed with the jit off and on")}

{lesson.claim("turning the JIT on changes how long the same loop takes, by enough to measure from Python")}
""")


lesson.code(
    """
def time_it():
    import timeit

    def work(n):
        total = 0
        for i in range(n):
            total += i * 2 - 1
        return total

    def helper(x):
        return x + 1

    def calls(n):
        total = 0
        for i in range(n):
            total += helper(i)
        return total

    work(20000)
    calls(20000)
    for label, one in [("arithmetic loop", work), ("loop with a call", calls)]:
        best = min(timeit.repeat(lambda one=one: one(20000), number=20, repeat=5))
        print(f"  {label:18} {best / 20 / 20000 * 1e9:6.1f} ns per iteration")


print("  with the jit on")
print(with_the_jit(time_it))
print()
print("  with the jit off, for comparison")
time_it()
""",
    varies="A timing, so the numbers move a lot, and where there is no JIT only the second "
    "half prints anything. On 3.15 this machine gets 18.7 down to 12.2 for the arithmetic loop. "
    "On 3.14 the JIT run is the slower of the two, which is the honest state of a young "
    "optimizer. In a browser both loops are two or three times slower than either.",
)


lesson.md(f"""
On 3.15 that is faster, and not by a rounding error. The arithmetic loop gains the most, which fits: it is the one where the guards were the largest share of the work.

Run the same cell on 3.14 and the JIT half comes out slower. That is not a mistake in the measurement. Tier two is young, the tracing and optimizing cost is real, and until recently it did not reliably pay for itself on small loops. This is the most useful thing in the lesson to sit with, because it is why the whole thing is still off by default: an optimizer that helps on your benchmark and hurts on mine is not ready to be on for everyone.

Two more things to keep in perspective. This is a benchmark shaped exactly like the thing tier two is good at, and real programs are mostly not loops that run four thousand times over a single type. And what ran here was still an interpreter over the {term("micro operation")}s rather than compiled machine code, unless your build has the full {term("JIT")}, in which case the trace was turned into machine code by pasting together pre-compiled fragments {cite("InternalDocs/jit.md:111-149@v3.15.0rc1")}.

## Try it yourself

Three things to try.

The first is to break a trace on purpose. Take the arithmetic loop, get it hot, and then have iteration ten thousand pass a float. Print the executor before and after. The guard fails, the side exit is taken, and what happens to the trace after that is worth watching.

The second is to look at a loop with an `if` in it. Record one where the condition is always true, and see what the branch became. There is no branch in the trace, only a guard, and finding it tells you a lot about why a straight line is worth recording.

The third is `sys._jit` itself. It has three questions and they mean three different things: whether the build has it, whether this process has it on, and whether the thread is running compiled code right now. Work out how to get the third one to say True.

## What just happened

Specializing one instruction at a time has a ceiling, because an instruction on its own cannot know anything about its neighbours. Tier two is the answer to that, and it works on runs of instructions rather than single ones.

It is off by default. `PYTHON_JIT=1` at startup turns it on, and there is no way to do it from a running program, so every experiment here ran in a fresh interpreter.

The backward jump at the end of a loop specializes into `JUMP_BACKWARD_JIT` or `JUMP_BACKWARD_NO_JIT` on its first execution, using the same family machinery as everything in E06. The name of the instruction tells you which mode you are in.

After about four thousand trips round, the interpreter records one real trip as a list of micro operations. Branches do not become two paths, they become the path that was taken plus a guard.

The result is an executor, and it is a real Python object. `_opcode.get_executor` hands it to you and iterating it gives one micro operation at a time.

A trace has two halves. Everything above `_JUMP_TO_TOP` runs every trip. Everything below it is a cold tail, one per guard, reached only when a guess turns out wrong.

Because a trace is straight, the optimizer can reason along it. A loop body with three additions runs six type guards in tier one and one on the hot path here, and two of the three additions became an in place form because the optimizer could see the intermediate result was not shared.

A trace can also cross a call. A loop that calls a small function ends up with that function's operations in the same list, with the dispatch between them gone.

Measured on a loop shaped to suit it, that is worth about a third of the running time. Measured on a real program it is worth a lot less, which is why it is still off by default.

## What is next

E08 is `sys.monitoring`. Everything so far has been the interpreter making itself faster. This is the opposite problem: how do you watch a program run without making it slower, when the thing you want to watch is the thing that has been optimized into not happening. The answer is a set of events the interpreter can turn on for one tool at a time, and the mechanism is the same one used everywhere else in this part, which is to rewrite the instruction so it does something different. A debugger that sets one breakpoint should not slow down the rest of the program, and this is how that is arranged.
""")


raise SystemExit(lesson.save())
