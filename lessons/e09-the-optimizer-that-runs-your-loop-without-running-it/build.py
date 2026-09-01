#!/usr/bin/env python
"""E09. The optimizer that runs your loop without running it.

The ninth lesson of the interpreter part. E07 got a trace recorded and looked at what came
back. This one is about the pass in the middle, the thing that decides which of the recorded
operations are worth keeping.

The hook is three reads of the same attribute and one type check between them. From there the
lesson builds up what the optimizer is actually doing: walking the trace holding a description
of each value rather than the value, and deleting anything those descriptions make pointless.

Everything here needs the JIT switched on, so the experiments run in a fresh interpreter the
same way E07's did, with one small addition: the helper can ship a second function along.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("e09-the-optimizer-that-runs-your-loop-without-running-it", "e09")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("e09-the-optimizer-that-runs-your-loop-without-running-it").figure


lesson.md(f"""
# E09. The optimizer that runs your loop without running it

{badge}

Here is a loop body: `total += p.x + p.x + p.x`. Three reads of the same attribute, and each read in tier one has to check that `p` is still the type it was last time.

In the recorded trace there is one check. Not three.

{figure("what-the-optimizer-does-to-a-trace", "a trace going through two optimizer passes and coming out shorter")}

Nothing ran to work that out. Something walked down the list of operations holding a note about what it knew, and crossed off the checks the note made pointless. That is this lesson.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/optimizer_analysis.c:803-829@v3.15.0rc1#_Py_uop_analyze_and_optimize`.

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

Same warning as E07. The optimizer is part of tier two, tier two is a build option rather than a version, and what it can prove changes a lot between releases. Every cell prints what it found instead of assuming, so it will tell you honestly if your build cannot do this.
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
## Getting a trace to look at

The JIT is off unless `PYTHON_JIT=1` was set before the interpreter started, and a notebook has already started. So this lesson does what E07 did: it writes a small function, ships the source of it to a fresh interpreter with the variable set, and reads back what got printed.

There is one addition. Every experiment below needs the same little helper for finding an executor, so the shipping function takes extra functions to send along with the body.

{lesson.claim("an executor can be fetched from Python and read as a list of micro operation names")}
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
            return [step[0] for step in found], found
    return [], None


def first_look():
    def loop(n):
        total = 0
        for i in range(n):
            total += i
        return total

    loop(20000)
    names, _ = trace_of(loop)
    print(f"  operations in the trace   {len(names)}")
    print(f"  the first five            {names[:5]}")


print()
print(with_the_jit(first_look, trace_of))
""",
    varies="Whether anything prints at all depends on your build having tier two in it, which "
    "a browser does not. On a desktop build the counts are stable for a given release and move "
    "between releases.",
)


lesson.md(f"""
## Three reads, one check

Now the loop from the top of the lesson.

`p.x` is read three times. In tier one each read is a `LOAD_ATTR_INSTANCE_VALUE`, and each one begins by checking that `p`'s type has not been patched since last time. Three reads, three checks.

{figure("three-reads-one-check", "three attribute reads in a trace with a single type check above them")}

{lesson.claim("a trace with three reads of the same attribute contains one type check, not three")}
""")


lesson.code(
    """
def three_reads():
    class Point:
        def __init__(self, x):
            self.x = x

    def loop(n, p):
        total = 0
        for _ in range(n):
            total += p.x + p.x + p.x
        return total

    loop(20000, Point(1))
    names, _ = trace_of(loop)
    print(f"  micro operations in the trace   {len(names)}")
    print(f"  reads of p.x                    {names.count('_LOAD_ATTR_INSTANCE_VALUE')}")
    print(f"  type checks on p                {names.count('_GUARD_TYPE_VERSION')}")


print(with_the_jit(three_reads, trace_of))
""",
    varies="The total operation count moves between releases. The other two lines are the "
    "point, and they have been three and one since tier two learned to do this.",
)


lesson.md(f"""
Why is one enough? Because the trace is a straight line. Between the first read and the second there is nothing that could run any Python at all, so there is nothing that could patch `Point`. The check at the top still has to happen, because `Point` might have been patched since the trace was recorded. It just does not have to happen again eleven operations later.

That is the whole idea, and everything else in this lesson is the same idea applied to something else.

## Twelve guards in, two out

Attributes make a nice picture. Arithmetic makes a nicer measurement.

A specialized integer addition is not one instruction in tier two, it is a small macro: check the top of the stack is a small int, check the one under it is too, then add {cite("Python/bytecodes.c:705-706@v3.15.0rc1#BINARY_OP_ADD_INT")}. Two {term("guard")}s per addition, every time.

So a loop body with six additions arrives at the optimizer carrying twelve guards. Watch what comes out.

{figure("guards-do-not-grow", "a table of addition counts against micro operation counts and guard counts")}

{lesson.claim("the number of guards in the trace does not grow as more additions are added to the loop body")}
""")


lesson.code(
    """
def count_guards():
    def build(adds):
        body = " + ".join(["total"] + ["i"] * adds)
        head = ["def f(n):", "    total = 0", "    for i in range(n):"]
        tail = ["        total = " + body, "    return total", ""]
        source = chr(10).join(head + tail)
        space = {}
        exec(compile(source, "<made here>", "exec"), space)
        return space["f"]

    print("  additions   micro operations   guards")
    for adds in (1, 2, 4, 6):
        one = build(adds)
        one(20000)
        names, _ = trace_of(one)
        guards = sum(1 for name in names if name.startswith("_GUARD"))
        print(f"  {adds:9d}   {len(names):16d}   {guards:6d}")


print(with_the_jit(count_guards, trace_of))
""",
    varies="On 3.15 this build gives 31, 36, 46 and 56 operations with three guards every "
    "time. On 3.14 the operation counts are different and the guard count sits at two rather "
    "than three. What matters is the shape: the left column grows, the right one does not.",
)


lesson.md(f"""
The middle column climbs by five operations per addition. The right one does not move.

One of those guards is not even arithmetic, it is the range iterator checking it has not run out. So six additions, twelve guards handed in, two guards kept.

## How it knows

Here is the part that makes the deletions possible.

The optimizer walks the trace one operation at a time, exactly like an interpreter, except that where the interpreter would hold a value on its stack this holds a description of a value. CPython calls those descriptions symbols, and the whole pass is an {term("abstract interpreter")}.

A description starts out saying nothing. Every guard the walk goes past adds something, and the descriptions only ever get more specific {cite("Python/optimizer_symbols.c:23-46@v3.15.0rc1")}.

{figure("what-it-can-know", "the levels of what the optimizer can know about a value")}

There are fourteen of these states in the source and they have short names {cite("Include/internal/pycore_optimizer_types.h:33-48@v3.15.0rc1#JitSymType")}. The rule for a guard is then two lines of ordinary thinking: if the description already says the check will pass, do not emit the check. If it says something weaker, emit a cheaper check and write down what it proved {cite("Python/optimizer_bytecodes.c:207-229@v3.15.0rc1#_GUARD_TOS_INT")}.

You can watch that second half happen. The loop variable comes out of `range`, so the optimizer already knows it is an integer, but not that it is small enough to add without overflow. So the full check gets swapped for the cheap one.

{lesson.claim("a guard whose type question is already answered comes out as a narrower check on the remaining question")}
""")


lesson.code(
    """
def which_guards():
    def loop(n):
        total = 0
        for i in range(n):
            total = total + i + i + i
        return total

    loop(20000)
    names, _ = trace_of(loop)
    for name in names:
        if name.startswith(("_GUARD", "_BINARY_OP")):
            print(f"  {name}")


print(with_the_jit(which_guards, trace_of))
""",
    varies="On 3.15 the first addition keeps `_GUARD_TOS_OVERFLOWED` and `_GUARD_NOS_INT`, "
    "and the next two keep nothing. On 3.14 there is one guard and all three additions are the "
    "plain form. Either way the guards stop after the first addition.",
)


lesson.md(f"""
Three additions, one pair of guards, and the pair that survived is the narrow kind. After that the optimizer knows the result of adding two small integers is an integer, so the next addition asks nothing.

On 3.15 two of the three also changed shape. `_BINARY_OP_ADD_INT_INPLACE` is an addition that writes into its left operand instead of allocating a new integer, and it is only safe when nobody else is holding that operand. The descriptions are what say so {cite("Python/bytecodes.c:711-722@v3.15.0rc1#_BINARY_OP_ADD_INT_INPLACE")}.

## The same pop, three ways

There is a smaller version of this that is easier to hold in your head.

Every operation that throws a value off the stack has to decide whether to decrement its reference count. That decision depends on what the value is, so tier one has one instruction that works it out at run time. Tier two has five, and picks between them while optimizing {cite("Python/optimizer_analysis.c:433-454@v3.15.0rc1#optimize_pop_top")}.

{figure("the-same-pop-three-ways", "three pop instructions chosen from what the optimizer knows")}

{lesson.claim("one loop body produces three different pop instructions depending on what is known about each value")}
""")


lesson.code(
    """
def which_pops():
    def loop(n):
        total = 0
        for i in range(n):
            total = total + i + i + i
        return total

    loop(20000)
    names, _ = trace_of(loop)
    for name in sorted(set(names)):
        if name.startswith("_POP_TOP"):
            print(f"  {name:16} {names.count(name)}")


print(with_the_jit(which_pops, trace_of))
""",
    varies="This is a 3.15 result. On 3.14 nothing prints, because the typed pops did not "
    "exist yet and the trace has no `_POP_TOP` in it at all. That is a fair picture of how "
    "quickly this part of the interpreter is still moving.",
)


lesson.md(f"""
Same source line, same effect on the stack, three different instructions. The one that costs nothing is the most common, which is the point of having them.

## Your global stops being a lookup

Now something that feels like it should not be allowed.

A global name lookup is a dictionary read. In a trace, the optimizer checks the module dictionary has not been modified, reads the value out once, and then writes that value straight into the operation as a constant {cite("Python/optimizer_analysis.c:182-209@v3.15.0rc1#convert_global_to_const")}. The name lookup is gone. What is left is the object.

And once a called function is a constant rather than a lookup, the call can be flattened into the trace, which is what E07 saw happening from the outside.

{lesson.claim("a loop that reads a global and calls a global function contains no name lookups in its trace")}
""")


lesson.code(
    """
def baked_in():
    global BUMP
    BUMP = 1

    def helper(x):
        return x + BUMP

    def loop(n):
        total = 0
        for i in range(n):
            total += helper(i)
        return total

    loop(20000)
    names, _ = trace_of(loop)
    print(f"  micro operations in the trace   {len(names)}")
    print(f"  global name lookups left        {sum(1 for n in names if 'LOAD_GLOBAL' in n)}")
    print(f"  constants pasted in             {sum(1 for n in names if 'CONST_INLINE' in n)}")
    print(f"  calls that became a frame push  {names.count('_PUSH_FRAME')}")
    print(f"  checks that a global changed    {names.count('_GUARD_GLOBALS_VERSION')}")


print(with_the_jit(baked_in, trace_of))
""",
    varies="The middle three lines are the ones to read, and they are zero, one and one on "
    "both 3.14 and 3.15. The last line is one on 3.15 and zero on 3.14, which is a difference "
    "in where the version check ends up rather than whether there is one.",
)


lesson.md(f"""
Zero lookups. One value pasted in. One call that stopped being a call.

## And then you rebind it

Which raises the obvious question. If the value of a global is written into an executor, what happens when you assign to that name?

Something has to notice. What notices is a {term("watcher")}: the optimizer asks to be told about changes to the module dictionary, and the callback throws away every executor that depended on it {cite("Python/optimizer_analysis.c:140-158@v3.15.0rc1#globals_watcher_callback")}. There is a matching one for types, which is what makes the type check in the very first experiment safe to do once.

{figure("baked-in-and-thrown-away", "a global baked into a trace and the trace being dropped when the name is rebound")}

{lesson.claim("rebinding a global that a trace depends on marks the executor invalid and detaches it")}
""")


lesson.code(
    """
def thrown_away():
    global BUMP
    BUMP = 1

    def helper(x):
        return x + BUMP

    def loop(n):
        total = 0
        for i in range(n):
            total += helper(i)
        return total

    loop(20000)
    _, found = trace_of(loop)
    print(f"  valid right after warming up    {found.is_valid()}")
    globals()["BUMP"] = 2
    print(f"  valid after BUMP is rebound     {found.is_valid()}")
    print(f"  still attached to the loop      {trace_of(loop)[1] is not None}")

    class Box:
        def __init__(self, v):
            self.v = v

        def get(self):
            return self.v

    def calls(n, box):
        total = 0
        for _ in range(n):
            total += box.get()
        return total

    calls(20000, Box(1))
    _, other = trace_of(calls)
    print(f"  a method loop, valid            {other.is_valid()}")
    Box.get = lambda self: 2
    print(f"  valid after patching Box.get    {other.is_valid()}")


print(with_the_jit(thrown_away, trace_of))
""",
    varies="These five lines are the same on 3.14 and 3.15, and nothing prints where there is "
    "no tier two. This is one of the few cells in the part whose answer has been stable across "
    "releases.",
)


lesson.md(f"""
True, then False, then gone. The loop goes back to running bytecode, and if it stays hot it gets recorded again with the new value baked in.

This is worth stopping on, because it is the deal the whole design rests on. The optimizer is allowed to assume anything it likes about your program as long as it also arranges to be told when the assumption breaks. Monkeypatching a class in a test still works. It just costs you every trace that touched it.

## The pass that deletes the bookkeeping

There is a second pass, and it is much simpler than the first.

Traces carry two kinds of bookkeeping. `_SET_IP` records where in the original bytecode we are, which matters only if the next operation might raise or call into arbitrary code. `_CHECK_VALIDITY` re-checks that the executor is still valid, which matters only if something since the last check could have run Python. The second pass walks the trace once and deletes every copy of both that no following operation needs {cite("Python/optimizer_analysis.c:723-749@v3.15.0rc1#remove_unneeded_uops")}.

It does not really delete them, it turns them into `_NOP`, and the `_NOP`s are dropped later when the trace is laid out {cite("Python/optimizer.c:1641-1664@v3.15.0rc1#stack_allocate")}. Which is why you never see one from Python.

{lesson.claim("the amount of bookkeeping left in a trace tracks how many operations in it could run other code")}
""")


lesson.code(
    """
def bookkeeping():
    def plain(x):
        return x

    def quiet(n):
        total = 0
        for i in range(n):
            total = total + i + i + i
        return total

    def noisy(n, f):
        total = 0
        for i in range(n):
            total = total + f(i) + i
        return total

    quiet(20000)
    noisy(20000, plain)
    for label, one in [("no calls in the loop", quiet), ("one call in the loop", noisy)]:
        names, _ = trace_of(one)
        checks = names.count("_CHECK_VALIDITY")
        marks = names.count("_SET_IP")
        print(f"  {label:22} {len(names):3d} operations, {marks} _SET_IP, {checks} _CHECK_VALIDITY")


print(with_the_jit(bookkeeping, trace_of))
""",
    varies="On 3.15 the quiet loop keeps two of each in forty one operations and the noisy "
    "one keeps four and three. On 3.14 the same two loops keep six and five, and seven and "
    "five. The second pass got better at this between the two releases.",
)


lesson.md("""
On 3.15 that is forty one operations with two place markers between them. Add one call and the numbers go up, because a call can run anything, and after anything has run nothing that was known is still known.

## Try it yourself

Three things to try, all of them small edits to the cells above.

The first is to break the reasoning. Take the three reads of `p.x` and put a function call between the first and the second. Count the type checks again. The call is the thing that could patch `Point`, so the second read has to ask afresh.

The second is to find a contradiction. The optimizer has a state for a value it has proved impossible, and it reaches it when two guards disagree. Write a loop where the same value would have to be an integer and a string, get it hot, and see whether you get an executor at all.

The third is to count what a real function costs. Take something out of the standard library with a loop in it, run it enough to get traced, and print the operation names. Most of what you find will be guards and bookkeeping rather than work, and the ratio between them is the honest answer to how much tier two is doing for you.

## What just happened

E07 recorded a trace and looked at the result. This lesson was about the pass in between, which is where the recorded operations turn into fewer operations.

The pass is an abstract interpreter. It walks the trace the way the interpreter would, except that it holds a description of each value instead of the value. Descriptions start out saying nothing and only ever get more specific, never less.

That is enough to delete checks. Three reads of the same attribute need one type check, because the straight line between them contains nothing that could change the answer. Six additions need one pair of int guards instead of six, because after the first addition the optimizer knows the result is an integer.

The same descriptions choose between instructions that do the same thing at different prices. Throwing a value off the stack has five forms in tier two, from one that does nothing at all to the general one, and the optimizer picks.

A global stops being a dictionary lookup and becomes the object itself, written into the operation. A called function that was a global can then be flattened into the trace.

That is only safe because of watchers. Rebinding the global, or patching a method on a class the trace guarded, invalidates the executor immediately and detaches it. You can watch `is_valid` flip from Python.

A second, simpler pass deletes the position markers and validity checks that no following operation needs. What is left is a trace where most of the remaining operations are work.

## What is next

E10 is the JIT proper. Everything so far has produced a better list of micro operations, and something has still been walking that list one at a time. The last step is to stop walking it: take each micro operation, look up a chunk of machine code that was compiled for it when CPython itself was built, and paste the chunks together into one function. It is called copy and patch, the compiler it needs is not the one you are thinking of, and the reason it works at all is that the hard part was done long before your program started.
""")


raise SystemExit(lesson.save())
