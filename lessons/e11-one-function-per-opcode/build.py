#!/usr/bin/env python
"""E11. One function per opcode.

The eleventh lesson of the interpreter part, and a step back from tier two to the loop that
runs everything else. E01 to E06 treated the eval loop as one huge function with a switch in
it, which is what it is in most builds. This lesson is about the third way of building the
same source, where each opcode becomes a small C function that ends by calling the next one.

Nothing here needs the JIT, and nothing needs a special build to read. The cells report what
your build actually got rather than assuming, and the timing cells work the same on all three
kinds of interpreter, because the thing being measured is the cost of one instruction.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("e11-one-function-per-opcode", "e11")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("e11-one-function-per-opcode").figure


lesson.md(f"""
# E11. One function per opcode

{badge}

The interpreter is one enormous function with a switch in it. Every lesson so far has said so, and in most builds that is exactly what it is.

There is another way to build the same interpreter out of the same file. Each opcode becomes a small C function of its own, and the last thing each one does is call the next one. No loop, no switch, and no way back.

{figure("one-case-becomes-one-function", "the path from one case in bytecodes.c to one C function in a table of 256")}

It sounds slower. It is not, and your build may already be using it.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/ceval_macros.h:99-127@v3.15.0rc1`.

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

This lesson is easier on your build than E07 to E10 were. There is no JIT here, and every cell runs whichever of the three interpreters you have. The first one tells you which that is.

The timings later on depend on your processor and on how busy it is, so treat every nanosecond figure as a shape rather than a number.
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
## Ask your build which one it got

The choice is made once, when CPython is configured, and never again. Passing `--with-tail-call-interp` sets a macro, and everything else follows from that macro being set {cite("configure.ac:7467-7489@v3.15.0rc1")}.

That macro ends up in {term("pyconfig")}, the header that records every decision the build made, and a copy of that header ships with the interpreter. So you can read the answer off your own installation. It has to be the header itself rather than `sysconfig`, because B01 found that `sysconfig` drops every macro whose name starts with an underscore, and on 3.15 this one does.

{lesson.claim("the dispatch style chosen at configure time is recorded as a macro in the shipped pyconfig.h")}
""")


lesson.code(
    """
import pathlib
import sysconfig

wanted = ("TAIL_CALL_INTERP", "COMPUTED_GOTOS")
found = {}
readable = True
try:
    header = pathlib.Path(sysconfig.get_config_h_filename())
    for line in header.read_text().splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0] == "#define" and any(one in parts[1] for one in wanted):
            found[parts[1]] = parts[2]
except OSError:
    readable = False
    print("  this build did not ship its pyconfig.h, so there is nothing to read there")

for name, value in sorted(found.items()):
    print(f"  {name:26} {value}")
if readable and not found:
    print("  nothing about dispatch was defined, so this is the plain switch")

args = (sysconfig.get_config_var("CONFIG_ARGS") or "").replace("'", "")
asked = [word for word in args.split() if "tail-call" in word or "computed" in word]
print(f"  asked for at configure time  {asked or 'nothing about dispatch'}")
""",
    differs="The macro was renamed between the two releases. 3.14 spells it `Py_TAIL_CALL_INTERP` "
    "and 3.15 spells it `_Py_TAIL_CALL_INTERP`, with the leading underscore that marks a name as "
    "private to CPython. Nothing about the behaviour changed with it.",
)


lesson.md(f"""
A `1` next to `TAIL_CALL_INTERP` means the rest of this lesson is describing the interpreter you are running. A `0`, or nothing at all, means it is describing one you could have had.

Both are worth knowing about, because the C in the middle is identical either way.

## The same file, three endings

Every opcode in the eval loop is written once, in `Python/bytecodes.c`, and a build step copies it into `Python/generated_cases.c.h`. Here is what `LOAD_FAST` looks like when it arrives there {cite("Python/generated_cases.c.h:9369-9384@v3.15.0rc1")}. It opens with `TARGET(LOAD_FAST)` and closes with `DISPATCH()`, and the generator that wrote it emits that same pair for every opcode without knowing anything about how the build will be configured {cite("Tools/cases_generator/tier1_generator.py:221-236@v3.15.0rc1")}.

`TARGET` and `DISPATCH` are macros, and there are three definitions of each. Which pair you get is decided by that one macro from the configure step.

{figure("the-same-file-three-endings", "a table of the three interpreter builds and what one opcode becomes in each")}

In a plain build, `TARGET(LOAD_FAST)` becomes `case LOAD_FAST:` and dispatch goes back to the top of the switch {cite("Python/ceval_macros.h:128-145@v3.15.0rc1")}. With computed gotos it becomes a label and dispatch is a jump through a table of label addresses. In the tail calling build it becomes the opening line of a function called `_TAIL_CALL_LOAD_FAST`, and dispatch is a return {cite("Python/ceval_macros.h:99-127@v3.15.0rc1")}.

That last one is worth reading twice. `DISPATCH_GOTO` expands to `return table[opcode](args)`. The way one opcode reaches the next is by calling it and returning whatever it returns.

{lesson.claim("the same generated C file becomes a switch, a jump table or a set of separate functions depending only on which macros are defined around it", unobservable="the three versions are produced by the C preprocessor at build time, and only one of them exists in the binary you are running")}

## Two hundred and fifty six slots

If dispatch is a call through a table, there has to be a table, and it is called the {term("dispatch table")}.

The generator writes it out with one entry per opcode, and then fills every value between 0 and 255 that no opcode claimed with the same handler for unknown opcodes {cite("Tools/cases_generator/target_generator.py:74-82@v3.15.0rc1")}. There is no gap and no bounds check, because an opcode is one byte and every one byte value leads somewhere.

{figure("two-hundred-and-fifty-six-slots", "the dispatch table with real opcodes, leftover slots and the total")}

You cannot see the table from Python, but you can count what has to go in it, because the same numbering is published in the `opcode` module.

{lesson.claim("the opcode numbering fills most of the 256 available slots, and the leftovers shrink as opcodes are added")}
""")


lesson.code(
    """
import opcode

specialized = getattr(opcode, "_specialized_opmap", {})
every = list(opcode.opmap.values()) + list(specialized.values())
real = {value for value in every if value < 256}
pseudo = {value for value in every if value >= 256}

print(f"  names in the opcode module       {len(every)}")
print(f"  of those, real one byte opcodes  {len(real)}")
print(f"  pseudo instructions, never run   {len(pseudo)}")
print(f"  slots left over out of 256       {256 - len(real)}")
print(f"  the slot LOAD_FAST sits in       {opcode.opmap['LOAD_FAST']}")
print(f"  where instrumented opcodes start {opcode.MIN_INSTRUMENTED_OPCODE}")
""",
    differs="3.15 has seven more real opcodes than 3.14, so seven fewer slots are left over, and "
    "the numbering shifted underneath them. `LOAD_FAST` moved from 84 to 83, which is a good "
    "reminder that opcode numbers are not part of the language.",
)


lesson.md(f"""
Two hundred and thirty odd real opcodes, and the table has room for two hundred and fifty six. The remaining slots are not empty, they point at a handler that reports a corrupt code object, which is the only sensible thing to do with a byte that means nothing.

## What a tail call is

Now the part that sounds impossible.

If every opcode ends by calling the next one, and a program runs a billion instructions, that is a billion nested calls. The C stack would be gone long before the program finished.

It is not, because of one word. The macro is defined as `Py_MUSTTAIL return ...`, where `Py_MUSTTAIL` is `__attribute__((musttail))` {cite("Python/ceval_macros.h:82-97@v3.15.0rc1")}. That attribute is a demand, not a hint. It tells the compiler this is a {term("tail call")}, the last thing this function does, so reuse the current stack frame instead of stacking a new one on top. If the compiler cannot do that, it refuses to compile the file rather than quietly producing something that overflows.

{figure("what-must-tail-means", "an ordinary call next to a call the compiler must turn into a jump")}

So the call is a jump. The stack frame is reused. A billion of them in a row use one frame, the same way a loop does, which is the whole reason this design is allowed to exist.

{lesson.claim("each opcode function ends by calling the next one and the compiler is required to turn that call into a jump", unobservable="whether a call reused the stack frame is a property of the machine code, and Python has no way to look at the C stack")}

The nearest thing you can see from Python is that running an enormous number of instructions inside one Python frame is fine. Here are eighty thousand of them, with nothing recursive and no calls at all.

{lesson.claim("a single function containing eighty thousand bytecode instructions runs in one frame without trouble")}
""")


lesson.code("""
import dis
import time

lines = ["def flat():", "    x = 0"] + ["    x = x + 1"] * 20000 + ["    return x"]
space = {}
exec(compile(chr(10).join(lines), "<made here>", "exec"), space)
flat = space["flat"]

steps = list(dis.get_instructions(flat))
calls = sum(1 for step in steps if step.opname.startswith("CALL"))
started = time.perf_counter()
answer = flat()
took = (time.perf_counter() - started) * 1e9

print(f"  lines of Python in it       {len(lines)}")
print(f"  bytecode instructions       {len(steps)}")
print(f"  calls to anything else      {calls}")
print(f"  what it returned            {answer}")
""")


lesson.md(f"""
Zero calls, so all eighty thousand instructions ran inside one Python frame. In a tail calling build that was also eighty thousand C function calls, and the C stack never grew.

## The bill is per instruction

If dispatch is this cheap, the interesting question is what one instruction actually costs.

The way to find out is to stop measuring whole functions and measure the difference between two of them. Take a loop, add lines to the body, count how many instructions really ran using the monitoring tools from E08, and divide the extra time by the extra instructions.

{lesson.claim("adding one more bytecode instruction to a hot loop costs a roughly fixed amount of time")}
""")


lesson.code(
    """
import sys
import timeit

TOOL = 3


def dispatches(fn, *args):
    seen = 0

    def bump(code, offset):
        nonlocal seen
        seen += 1

    mon = sys.monitoring
    mon.use_tool_id(TOOL, "counter")
    mon.register_callback(TOOL, mon.events.INSTRUCTION, bump)
    mon.set_local_events(TOOL, fn.__code__, mon.events.INSTRUCTION)
    fn(*args)
    mon.set_local_events(TOOL, fn.__code__, 0)
    mon.free_tool_id(TOOL)
    return seen


def build(extra):
    body = ["    x = 0", "    for _ in range(1000):"] + ["        x = x"] * extra
    source = chr(10).join(["def loop():", *body, "        x = x + 1", "    return x", ""])
    space = {}
    exec(compile(source, "<made here>", "exec"), space)
    return space["loop"]


print("  extra lines   instructions run   nanoseconds   cost of one more")
before = None
for extra in (0, 5, 10, 20, 40):
    one = build(extra)
    count = dispatches(one)
    took = min(timeit.repeat(one, number=200, repeat=5)) / 200 * 1e9
    step = "" if before is None else f"{(took - before[1]) / (count - before[0]):.2f}"
    print(f"  {extra:11d}   {count:16d}   {took:11.0f}   {step:>16}")
    before = (count, took)
""",
    varies="The last column lands between 0.8 and 1.0 nanoseconds on this machine on 3.15, and "
    "between 0.7 and 1.3 on 3.14, which is the same answer with more noise in it. In a browser it "
    "is several times slower and jumps around a lot, because a tab is a noisy place to time "
    "anything. On a quiet machine the column should stay flat rather than climbing as the loop "
    "gets longer.",
)


lesson.md(f"""
One more instruction, about one more nanosecond, no matter how many are already there. That is what it looks like when there is no per instruction bookkeeping and no shared state to reload.

The same rate turns up when you compare three ways of writing the same job. These are not micro optimizations of each other, they are three different programs, and the only thing that predicts how long they take is how many instructions they run.

{lesson.claim("the time three different loops take tracks the number of instructions they run, at close to the same rate")}
""")


lesson.code(
    """
def with_while(items):
    out = []
    i = 0
    while i < len(items):
        out.append(items[i] + 1)
        i = i + 1
    return out


def with_for(items):
    out = []
    for x in items:
        out.append(x + 1)
    return out


def with_comp(items):
    return [x + 1 for x in items]


data = list(range(1000))
rows = (("a while loop", with_while), ("a for loop", with_for), ("a comprehension", with_comp))
print("  the same job          instructions   nanoseconds   each")
for name, one in rows:
    count = dispatches(one, data)
    took = min(timeit.repeat(lambda one=one: one(data), number=200, repeat=5)) / 200 * 1e9
    print(f"  {name:20}  {count:12d}   {took:11.0f}   {took / count:4.2f}")
""",
    varies="On this machine the last column reads 1.03, 1.00 and 1.09 on 3.15, and 1.33, 1.25 and "
    "1.74 on 3.14. The comprehension is always the odd one out because it does more per "
    "instruction, not because dispatch got more expensive.",
)


lesson.md(f"""
{figure("the-bill-is-per-instruction", "three ways of building the same list, with instruction counts and times")}

Three times the instructions, three times the time. The advice that falls out of this is duller than most performance advice and more reliable than most of it: if you want a loop to be faster, run fewer instructions in it.

## Why it is not slower

Which leaves the question the whole lesson has been circling. How can replacing a jump with a function call possibly be faster?

The answer is not about the call. The call is a jump, and a jump costs about what a jump costs. It is about what surrounds the call, and CPython's own documentation names the two things it leans on {cite("InternalDocs/interpreter.md:510-528@v3.15.0rc1")}.

The first is `preserve_none`, a second attribute sitting next to `musttail` in the same macro block. It changes the {term("calling convention")}. Normally a function has to leave some registers exactly as it found them, so the caller can rely on them afterwards. `preserve_none` says nobody is coming back, so nothing needs preserving. The six values the interpreter carries between opcodes are passed as ordinary parameters and stay in registers the whole way through {cite("Python/ceval_macros.h:74-80@v3.15.0rc1")}.

The second is what the compiler does with a small function. One function containing every opcode has to be given one register allocation that works for all of them, so values get pushed out to memory to make room for whichever case needs the most. Two hundred small functions are two hundred separate problems, each easy.

{figure("why-it-is-not-slower", "one huge function next to many small ones, from the compiler's point of view")}

{lesson.claim("the speed comes from the compiler handling small functions better, not from calls being cheap", unobservable="register allocation happens inside the C compiler, and nothing about it survives into anything Python can inspect")}

Calls being cheap is still worth checking though, and that one you can measure. Here is what a call to an empty Python function costs, in units of bytecode instructions.
""")


lesson.code(
    """
def nothing():
    pass


def caller():
    nothing()


count = dispatches(with_for, data)
took = min(timeit.repeat(lambda: with_for(data), number=200, repeat=5)) / 200 * 1e9
rate = took / count
per_call = min(timeit.repeat(caller, number=200000, repeat=5)) / 200000 * 1e9
alone = min(timeit.repeat(lambda: None, number=200000, repeat=5)) / 200000 * 1e9

print(f"  one bytecode instruction   {rate:.2f} ns")
print(f"  one call to an empty def   {per_call - alone:.2f} ns beyond the code that calls it")
print(f"  so a call costs about      {(per_call - alone) / rate:.0f} instructions")
""",
    varies="This comes out at about eight instructions per call on this machine, on both releases. "
    "The number is sensitive to how busy the machine is, so run it a few times. The point is the "
    "order of magnitude: a call is a handful of instructions, not hundreds.",
)


lesson.md("""
A Python function call costs about as much as running eight simple instructions. That is a number worth carrying around, and it is the reason the tail calling interpreter is not obviously doomed from the start.

## Try it yourself

Three things worth trying.

The first is to run the last two cells a few times in a row. Timing cells lie more than any other kind, and the way to see how much is to watch the numbers move while nothing else changes.

The second is to look for a place where the per instruction rate breaks down. Every instruction in this lesson was a cheap one. Put a dictionary lookup, a string join or an attribute access in the loop body and the rate will climb, because those instructions do real work on top of being dispatched.

The third is for anyone willing to build CPython. Configure it twice, once with `--with-tail-call-interp` and once without, and run the same loop on both. The gap you find will be smaller than the headlines suggest and it will depend heavily on your compiler, which is the honest version of this story.

## What just happened

The eval loop is generated from one file, and there are three ways to stitch the result together.

Two of them are what you expect: a switch, or a table of labels with a jump per opcode. The third turns every opcode into its own C function and makes dispatch a return statement, calling the function for the next opcode and handing back whatever it hands back.

That works because of `musttail`, which orders the compiler to reuse the stack frame instead of stacking a new one. If it cannot, the build fails. So a billion instructions in a row use one frame.

The table those calls go through has 256 slots, one per possible byte, with every value no opcode claimed pointing at a handler for corrupt bytecode. About 234 of them are real on 3.15 and 227 on 3.14.

Measured from Python, one bytecode instruction costs around a nanosecond, and that number barely moves whether the loop is short or long or written three different ways. A call to an empty function costs about eight of them.

The reason this design wins has nothing to do with calls being fast. It is `preserve_none`, which lets the interpreter's six working values stay in registers across the whole chain, and the fact that a compiler does a better job on two hundred small functions than on one enormous one.

## What is next

E12 is the last lesson of this part, and it does not introduce anything new. It takes a single instruction and follows it the whole way down: the case written by hand in `bytecodes.c`, the generated C it turns into, the specialized version that replaces it while your program runs, the micro operations it becomes in a trace, what the optimizer does to those, and the machine code at the end. One instruction, eleven lessons worth of machinery, on one page.
""")


raise SystemExit(lesson.save())
