#!/usr/bin/env python
"""E08. Watching without slowing it down.

The eighth lesson of the interpreter part, and the last one about rewriting instructions.
E06 and E07 rewrote them to go faster. This one rewrites them to go slower, on purpose, in
exactly the places somebody asked about and nowhere else.

The hook is that you can watch it happen. Switch on line events for one function, disassemble
it, and the instructions are different. Switch them off, run it once, and they are back.

The measurement that carries the lesson is three numbers: the same loop with nobody watching,
with a callback that counts, and with a callback that returns DISABLE. The third is as fast
as the first, and that is the entire design of `sys.monitoring` in one line.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("e08-watching-without-slowing-it-down", "e08")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("e08-watching-without-slowing-it-down").figure


lesson.md(f"""
# E08. Watching without slowing it down

{badge}

E06 rewrote an instruction so it would run faster. E07 replaced a whole loop for the same reason. This lesson is the same trick pointed the other way.

A debugger needs to be told when a line runs. A coverage tool needs to know which lines ran at all. Both of those used to mean a callback on every line of every function, whether anybody cared about that line or not, which is why nothing had them on by default.

{figure("switching-one-event-on", "four calls that end with the bytecode of one function rewritten in place")}

The answer is to rewrite the instructions that somebody asked about, and leave the rest alone. You can watch it happen from Python.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/instrumentation.c:757-784@v3.15.0rc1#instrument`.

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

`sys.monitoring` arrived in 3.12 and has gained events since, so the list below is longer on newer versions. Everything the lesson does works on 3.14 and 3.15, including in a browser, because none of it needs a special build.
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
## Six slots and nineteen events

Two things have to be true before the interpreter will tell you anything: you have to hold a {term("tool id")}, and you have to say which events you want.

The ids are just numbers. There are eight of them in the C code and six you can use, because the last two are held for `sys.settrace` and `sys.setprofile` {cite("Include/internal/pycore_instruments.h:20-27@v3.15.0rc1#PY_MONITORING_SYS_TRACE_ID")}. Four of the six have names attached by convention, and the interpreter does not check that you are using the one your name suggests.

{figure("eight-slots-six-yours", "the eight tool ids, which four have conventional names, and which two are reserved")}

The events are a set of bit flags, and you ask for them by adding them together.

{lesson.claim("the interpreter offers a fixed set of numbered monitoring events and a fixed number of tool slots, and both are readable from Python")}
""")


lesson.code(
    """
import sys

mon = sys.monitoring
names = sorted(
    (n for n in dir(mon.events) if n.isupper()),
    key=lambda n: getattr(mon.events, n),
)
print(f"  events on this version    {len(names) - 1}")
print(f"  tool ids you can use      {[n for n in dir(mon) if n.endswith('_ID')]}")
print()
for name in names:
    print(f"   {getattr(mon.events, name):>6}  {name}")
"""
)


lesson.md(f"""
## Switching it on rewrites the function

Here is the whole idea in one cell.

Disassemble a function. Ask to be told about its lines. Disassemble it again. The instructions are different, and nothing was recompiled: the bytes in the code object were written over where they sat {cite("Python/instrumentation.c:757-784@v3.15.0rc1#instrument")}.

{figure("the-same-function-before-and-after", "the same function disassembled with line events off and on")}

Then switch the event off and look a third time. The originals come back {cite("Python/instrumentation.c:676-705@v3.15.0rc1#de_instrument")}.

{lesson.claim("switching a monitoring event on for one function replaces instructions in its bytecode, and switching the event off puts the original instructions back")}
""")


lesson.code(
    """
import dis
import sys

mon = sys.monitoring
SOURCE = (
    "def f(a, b):\\n    total = 0\\n"
    "    for i in range(3):\\n        total += a + b\\n    return total\\n"
)


def build(source, name="f"):
    space = {}
    exec(compile(source, "<made here>", "exec"), space)
    return space[name]


def opnames(one, upto=8):
    return [step.opname for step in dis.get_instructions(one, adaptive=True)][:upto]


watched = build(SOURCE)
print(f"  before   {opnames(watched)}")

mon.free_tool_id(mon.DEBUGGER_ID)
mon.use_tool_id(mon.DEBUGGER_ID, "e08")
lines = []
mon.register_callback(mon.DEBUGGER_ID, mon.events.LINE, lambda code, line: lines.append(line))
mon.set_local_events(mon.DEBUGGER_ID, watched.__code__, mon.events.LINE)
print(f"  after    {opnames(watched)}")

watched(1, 2)
print(f"  lines it reported   {lines}")

mon.set_local_events(mon.DEBUGGER_ID, watched.__code__, 0)
mon.free_tool_id(mon.DEBUGGER_ID)
print(f"  off again {opnames(watched)}")
"""
)


lesson.md(f"""
Three things worth noticing in that output.

The instrumented instruction is not an extra one squeezed in beside the original. It is written over the top of it, and the original is kept in a side table so the interpreter can carry on with it afterwards {cite("Python/bytecodes.c:5987-6015@v3.15.0rc1#INSTRUMENTED_LINE")}. That is why the offsets did not move: there is exactly as much bytecode as there was before.

The list of lines is a real trace of what ran, including the line numbers repeating as the loop went round.

And the third disassembly is not quite identical to the first. `RESUME` has become `RESUME_CHECK`, because running the function once warmed it up, which is E06 happening in the background while this lesson was busy.

## What watching costs

Now the number that explains the whole design.

Take a loop, time it with nobody watching, then time it with line events on and a callback that just counts. Then change one thing: have the callback return `sys.monitoring.DISABLE` instead of `None`.

{figure("what-watching-costs", "the same loop timed with nobody watching, with a counting callback, and with a callback that returns DISABLE")}

{lesson.claim("a monitoring callback that returns DISABLE leaves the watched loop running at close to full speed, while the same callback returning None makes it several times slower")}
""")


lesson.code(
    """
import sys
import time

mon = sys.monitoring
LOOP = "def hot(n):\\n    total = 0\\n    for i in range(n):\\n        total += i\\n    return total\\n"
hot = build(LOOP, "hot")
turns = 200000


def per_turn(one, repeat=5):
    best = min(_once(one) for _ in range(repeat))
    return best / turns * 1e9


def _once(one):
    started = time.perf_counter()
    one(turns)
    return time.perf_counter() - started


print(f"  nobody watching             {per_turn(hot):6.1f} ns per turn")

mon.free_tool_id(mon.DEBUGGER_ID)
mon.use_tool_id(mon.DEBUGGER_ID, "e08")
count = 0


def counting(code, line):
    global count
    count += 1


mon.register_callback(mon.DEBUGGER_ID, mon.events.LINE, counting)
mon.set_local_events(mon.DEBUGGER_ID, hot.__code__, mon.events.LINE)
print(f"  callback counts the line    {per_turn(hot):6.1f} ns per turn, {count} calls")

mon.set_local_events(mon.DEBUGGER_ID, hot.__code__, 0)
mon.register_callback(mon.DEBUGGER_ID, mon.events.LINE, lambda code, line: sys.monitoring.DISABLE)
mon.set_local_events(mon.DEBUGGER_ID, hot.__code__, mon.events.LINE)
print(f"  callback returns DISABLE    {per_turn(hot):6.1f} ns per turn")

mon.set_local_events(mon.DEBUGGER_ID, hot.__code__, 0)
mon.free_tool_id(mon.DEBUGGER_ID)
""",
    varies="A timing, so the absolute numbers depend on your machine and are about twice as "
    "large in a browser. The shape is the same everywhere: the middle line is several times "
    "the first. On a desktop build the third line lands within a fraction of a nanosecond of "
    "the first, and in a browser it stays a little above it without ever getting near the "
    "middle one.",
)


lesson.md(f"""
## The word that makes it free

`DISABLE` is not "stop watching". It is "stop telling me about this one instruction" {cite("Python/instrumentation.c:971-994@v3.15.0rc1#call_one_instrument")}.

When a callback returns it, the interpreter takes the instrumentation back out of the single instruction that fired and leaves everything else alone {cite("Python/instrumentation.c:1190-1216@v3.15.0rc1#remove_tools")}. The event is still on for the function. That one place has just gone quiet.

{figure("a-callback-that-stays-or-goes", "the same callback returning None and returning DISABLE, and how many times each is called")}

Count the calls and the difference is not subtle.

{lesson.claim("a callback returning DISABLE is called once per instruction rather than once per execution, so a loop of a thousand turns produces a handful of calls")}
""")


lesson.code(
    """
import sys

mon = sys.monitoring
counted = build(LOOP, "hot")

mon.free_tool_id(mon.DEBUGGER_ID)
mon.use_tool_id(mon.DEBUGGER_ID, "e08")
every = []
mon.register_callback(mon.DEBUGGER_ID, mon.events.LINE, lambda code, line: every.append(line))
mon.set_local_events(mon.DEBUGGER_ID, counted.__code__, mon.events.LINE)
counted(1000)
print(f"  callback returning None      {len(every)} calls for 1000 turns")

mon.set_local_events(mon.DEBUGGER_ID, counted.__code__, 0)
once = []


def first_time(code, line):
    once.append(line)
    return sys.monitoring.DISABLE


mon.register_callback(mon.DEBUGGER_ID, mon.events.LINE, first_time)
mon.set_local_events(mon.DEBUGGER_ID, counted.__code__, mon.events.LINE)
counted(1000)
print(f"  callback returning DISABLE   {len(once)} calls, lines {once}")

mon.restart_events()
counted(1000)
print(f"  after restart_events         {len(once)} calls in total")

mon.set_local_events(mon.DEBUGGER_ID, counted.__code__, 0)
mon.free_tool_id(mon.DEBUGGER_ID)
"""
)


lesson.md(f"""
That is a coverage tool. Five calls to find out which lines of a function ran, no matter how many times the loop went round, and `restart_events` to start again if you want a second measurement.

## Two tools at once

The old `sys.settrace` is one hook per interpreter, so two tools that both wanted it had to fight, and mostly the answer was that you could not run a debugger and a coverage tool at the same time.

Six slots fixes that. Each tool registers its own callbacks and asks for its own events, and the interpreter keeps them apart.

{figure("two-tools-one-function", "a debugger and a coverage tool watching the same function and each hearing only its own events")}

{lesson.claim("two monitoring tools can watch the same function at the same time, each receiving only the events it registered for")}
""")


lesson.code(
    """
mon = sys.monitoring
BRANCHING = (
    "def pick(n):\\n    if n > 0:\\n        out = 'up'\\n"
    "    else:\\n        out = 'down'\\n    return out\\n"
)
pick = build(BRANCHING, "pick")
heard = []


def saw_line(code, line):
    heard.append(("debugger", f"line {line}"))


def saw_left(code, offset, destination):
    heard.append(("coverage", f"left at {offset}"))


def saw_right(code, offset, destination):
    heard.append(("coverage", f"right at {offset}"))


for tool, label in [(mon.DEBUGGER_ID, "debugger"), (mon.COVERAGE_ID, "coverage")]:
    mon.free_tool_id(tool)
    mon.use_tool_id(tool, label)

mon.register_callback(mon.DEBUGGER_ID, mon.events.LINE, saw_line)
mon.register_callback(mon.COVERAGE_ID, mon.events.BRANCH_LEFT, saw_left)
mon.register_callback(mon.COVERAGE_ID, mon.events.BRANCH_RIGHT, saw_right)
mon.set_local_events(mon.DEBUGGER_ID, pick.__code__, mon.events.LINE)
branches = mon.events.BRANCH_LEFT | mon.events.BRANCH_RIGHT
mon.set_local_events(mon.COVERAGE_ID, pick.__code__, branches)

print("  what the bytecode looks like with both on")
for step in dis.get_instructions(pick, adaptive=True):
    print(f"   {step.offset:3}  {step.opname}")
print()

pick(1)
pick(-1)
for who, what in heard:
    print(f"   {who:9} {what}")

for tool in [mon.DEBUGGER_ID, mon.COVERAGE_ID]:
    mon.set_local_events(tool, pick.__code__, 0)
    mon.free_tool_id(tool)
""",
    differs="On 3.14 every offset from the second instruction onwards is two lower, and the "
    "branch is reported at 10 rather than 12. `RESUME` grew a cache slot in 3.15, so it takes "
    "four bytes there and two here, and everything after it moves along.",
)


lesson.md(f"""
`INSTRUMENTED_NOT_TAKEN` is the one to look at {cite("Python/bytecodes.c:6038-6041@v3.15.0rc1#INSTRUMENTED_NOT_TAKEN")}. A branch that is not taken normally costs nothing at all, because not jumping is what the instruction pointer does by itself. To report it, there has to be something there to report it, so the compiler leaves a `NOT_TAKEN` placeholder in the bytecode that does nothing until somebody instruments it.

## It undoes what E06 did

There is a cost the timings above did not show, and it is the interesting one.

An instrumented instruction cannot also be a specialized instruction. There is one byte for the opcode and it cannot say two things. So instrumenting a warm instruction throws its specialization away, and the comment in the interpreter about this is blunt {cite("Python/bytecodes.c:6017-6028@v3.15.0rc1#INSTRUMENTED_INSTRUCTION")}.

{lesson.claim("instrumenting a warm function un-specializes its instructions, and they specialize again once the instrumentation is removed and the function runs")}
""")


lesson.code(
    """
mon = sys.monitoring
adding = build("def add(a, b):\\n    return a + b\\n", "add")


def arithmetic(one):
    return [
        step.opname
        for step in dis.get_instructions(one, adaptive=True)
        if "BINARY_OP" in step.opname or step.opname.startswith("INSTRUMENTED")
    ]


for _ in range(10):
    adding(1, 2)
print(f"  warm, nobody watching      {arithmetic(adding)}")

mon.free_tool_id(mon.DEBUGGER_ID)
mon.use_tool_id(mon.DEBUGGER_ID, "e08")
mon.register_callback(mon.DEBUGGER_ID, mon.events.INSTRUCTION, lambda code, offset: None)
mon.set_local_events(mon.DEBUGGER_ID, adding.__code__, mon.events.INSTRUCTION)
print(f"  every instruction watched  {arithmetic(adding)}")

mon.set_local_events(mon.DEBUGGER_ID, adding.__code__, 0)
mon.free_tool_id(mon.DEBUGGER_ID)
print(f"  watching switched off      {arithmetic(adding)}")

for _ in range(10):
    adding(1, 2)
print(f"  and warmed up again        {arithmetic(adding)}")
"""
)


lesson.md(f"""
So the specialization is not paused, it is thrown away, and the counter is reset to the beginning {cite("Python/instrumentation.c:757-784@v3.15.0rc1#adaptive_counter_warmup")}. A function you have been stepping through in a debugger is a cold function again when you stop, and it has to earn its specializations back.

This is the honest cost of watching, and it does not show up in a timing of the watched function. It shows up in the function you were watching a minute ago.

## The old way is now the new way

`sys.settrace` did not go away when this arrived. It got reimplemented on top of it.

Two of the eight tool ids are reserved for exactly that, and the code that uses them is a small file that turns old style trace events into monitoring events {cite("Python/legacy_tracing.c:129-149@v3.15.0rc1#_PyMonitoring_SetLocalEvents")}. So the thirty year old debugger hook and the new one are now the same machinery underneath, and you can see it from outside.

{lesson.claim("sys.settrace is implemented on top of monitoring, so installing a trace function puts instrumented instructions into the functions it runs")}
""")


lesson.code(
    """
def tracer(frame, event, arg):
    return tracer


traced = build("def small(a, b):\\n    total = a + b\\n    return total\\n", "small")
print(f"  plain              {opnames(traced, 6)}")

sys.settrace(tracer)
traced(1, 2)
print(f"  under settrace     {opnames(traced, 6)}")

sys.settrace(None)
print(f"  settrace(None)     {opnames(traced, 6)}")

traced(1, 2)
print(f"  after one more run {opnames(traced, 6)}")
"""
)


lesson.md("""
The last two lines are the part to read. Turning the trace function off did not clean the instructions up. They stayed instrumented until the function ran once more, and then the interpreter caught the code object up.

That is not laziness for its own sake. Walking every code object in the program every time somebody changes a setting would be slow and would need to happen while nothing else is running. Instead each code object carries a version number, and it checks whether it is out of date the next time it is entered.

## Try it yourself

Three things to try.

The first is to write a coverage tool. It is about fifteen lines: claim `COVERAGE_ID`, register a `LINE` callback that records `(code.co_filename, line)` and returns `DISABLE`, turn the event on globally with `set_events` rather than per function, import a module, and print what you collected. Compare it against what you thought that module did.

The second is to find an event this lesson did not use and work out what it is for. `PY_UNWIND`, `STOP_ITERATION` and `EXCEPTION_HANDLED` are all about the machinery from E05, and watching them fire during a `for` loop that ends normally is a good way to see where exceptions really live in Python.

The third is to break something on purpose. Register a `LINE` callback that raises. Work out where the exception surfaces, and whether the function you were watching finished.

## What just happened

Two things have to be true before the interpreter tells you anything: a tool holds one of the numbered slots, and it has asked for specific events. There are eight slots, six of them yours, and the last two are held for `sys.settrace` and `sys.setprofile`.

Asking for an event on a function rewrites that function's bytecode where it sits. The instrumented instruction goes over the top of the original, which is kept in a side table, so offsets do not move and nothing is recompiled.

Switching the event off writes the originals back. It happens the next time the function runs rather than immediately, because each code object checks whether it is out of date on entry rather than everybody being walked at once.

`DISABLE` is the load bearing part. Returning it from a callback removes the instrumentation from the one instruction that fired, so a coverage tool learns which lines ran with a handful of calls and the loop around them runs at full speed. Returning `None` instead means being called every single time, which is what a debugger actually wants.

Several tools can watch the same function at once and each hears only what it asked for. That is the thing the single `sys.settrace` hook could never do.

The cost that does not show up in a timing is specialization. An instrumented instruction cannot also be a specialized one, so instrumenting throws the specialization away and resets the counter. A function you have finished debugging is cold again.

And `sys.settrace` is not a separate mechanism any more. It is a thin layer over this one, using two reserved slots, which is why installing a trace function puts `INSTRUMENTED_` instructions into your bytecode.

## What is next

E09 is the optimizer that E07 kept mentioning without opening. A recorded trace goes in as a straight list of micro operations and comes out shorter, with guards deleted and constants folded and some operations replaced by cheaper ones. The interesting part is how it knows it is allowed to do that, which comes down to a small abstract interpreter that runs over the trace tracking what it can prove about each value: this is definitely an int, this one cannot be null, this one is a known constant. Those facts are a type system nobody wrote down, inferred at runtime from what actually happened, and you can print the before and after and count what went missing.
""")


raise SystemExit(lesson.save())
