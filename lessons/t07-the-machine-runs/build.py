#!/usr/bin/env python
"""T07. The machine runs.

T06 taught reading a listing. This lesson is about what happens when one actually runs: the
loop in `Python/ceval.c`, the frame it runs against, and the two stacks that frame lives on.

The runnable spine is `pyxray/src/pyxray/stepper.py`, which uses `sys.monitoring` to record
every instruction a function executes and joins that with the heights `pyxray.stack` worked
out in T06. The join is the honest part and the lesson says so out loud: the order is
observed, the heights are computed, and nothing in the standard library can read the values
sitting on the stack.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of
them. `just lessons` checks that the committed notebook still matches this file.

The pictures come from `diagrams.py` in this directory. They are looked up on disk rather
than imported, so a diagram that has not been built yet fails here instead of producing a
notebook full of broken images.
"""

from nbbuild import BANNER, OFFSETS, Lesson
from nbdiagram import Diagrams

lesson = Lesson("t07-the-machine-runs", "t07")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("t07-the-machine-runs").figure

lesson.md(f"""
# T07. The machine runs

{badge}

Six lessons of building. Text became tokens, tokens became a tree, the tree got scopes, the scopes became bytecode, and T06 taught you to read it. Every one ended with something built and nothing running. This is where it runs.

{figure("where-we-are", "the eight stages of running Python, with the last stage highlighted")}

The part of CPython that runs {term("bytecode")} is smaller than you would expect. It is one loop, the {term("eval loop")}: it reads an instruction, does what it says, and reads the next. There is no scheduler and no lookahead, and everything Python can do is one of about two hundred handlers in that loop.

By the end you will have watched a real function run one instruction at a time, watched frames appear and disappear, and found out why ninety thousand Python calls are fine while two thousand through `sorted` are not.

No C required, and everything here runs on a normal Python.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/ceval.c:1212-1218@v3.15.0rc1#_PyEval_EvalFrameDefault`.

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

Instruction names and monitoring events both change between releases. Everything here was checked against the version this cell prints.

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
## The loop

The whole interpreter fits in one picture.

{figure("the-loop", "the interpreter as a ring: read two bytes, look up the handler, run it, move the pointer on")}

Read two bytes, which gives an opcode and an argument, exactly the encoding T06 pulled apart. Look up the code for that opcode. Run it, which usually means pushing or popping a few things. Move the instruction pointer past the instruction and past any inline cache slots behind it. Then go back to the top.

The C for that ring is two macros. {cite("Python/ceval_macros.h:198-206@v3.15.0rc1#DISPATCH")} is the whole cycle: read the next opcode and argument, then jump to the handler. Every handler ends by calling it.

The function containing all of this is {cite("Python/ceval.c:1212-1218@v3.15.0rc1#_PyEval_EvalFrameDefault")}. It is around six thousand lines, and almost all of that is the handlers rather than the loop. The loop itself is the four boxes above.

One thing worth noticing early: nothing in that ring says "call a function". A Python function calling a Python function does not leave the loop, and the section on two stacks is where that starts to matter.
""")


lesson.md(f"""
## Three ways to get to the handler

"Look up the code for that opcode" hides a choice. That step is called {term("dispatch")}, and CPython does it three different ways depending on how it was built.

{figure("three-ways-to-jump", "three dispatch strategies with their costs and when CPython uses each")}

The plain version is a `switch` on the opcode inside a `while` loop, which every C compiler understands. The faster version is a {term("computed goto")}: an array of label addresses, one per opcode, and `goto *opcode_targets[opcode]`. That gives every instruction its own copy of the jump, which the branch predictor can learn separately, and it is worth real percentage points.

The newest version replaces the jump table with a table of functions, and each handler ends by tail calling the next one, which relies on the compiler turning that tail call into a jump. All three live in the same header: {cite("Python/ceval_macros.h:128-141@v3.15.0rc1#DISPATCH_GOTO")}.

{lesson.claim("a build records which dispatch strategy it was compiled with, so you can ask your own interpreter rather than guess")}, because the choice was made when it was compiled and it left a note.
""")


lesson.code(
    """
import sysconfig

arguments = sysconfig.get_config_var("CONFIG_ARGS") or ""
if "--with-tail-call-interp" in arguments:
    print("this build tail calls between handlers")
else:
    print("this build uses computed gotos or a switch")
print()
print("configured with:")
for argument in arguments.replace("'", "").split():
    if argument.startswith("--with") or argument.startswith("--enable"):
        print("   ", argument)
""",
    varies="This lists the flags your CPython was configured with, which says more about who built it than about the version.",
)


lesson.md("""
Same instruction set and the same results either way. This is one of the places where CPython is really two or three programs built from the same source, and the difference is invisible from Python except through the note above.
""")


lesson.md(f"""
## What one call needs

The loop needs somewhere to keep things. That somewhere is a {term("frame")}, and it is one block of memory laid out in a fixed order.

{figure("a-frame", "a frame as three stacked regions: specials, locals, and the value stack")}

The specials are the fixed size part: which code object is running, the globals, the builtins, the previous frame, and `instr_ptr`, which is where we are in the bytecode. Then one slot per local variable. Then `co_stacksize` slots of working space for the {term("value stack")}, which is the number T06 spent half a lesson computing.

The struct is {cite("Include/internal/pycore_interpframe_structs.h:29-53@v3.15.0rc1#_PyInterpreterFrame")}. The layout is why locals are fast: `LOAD_FAST 3` is an offset from the start of the frame, worked out at compile time, so there is no dictionary and no name lookup.

Frames are not allocated one at a time. They go on a per thread stack, contiguously, so pushing one is usually a pointer bump: {cite("InternalDocs/frames.md:16-25@v3.15.0rc1#Allocation")}.
""")


lesson.md(f"""
## Calling Python from Python

This is the part that surprises people. When your Python function calls another Python function, the interpreter does not call itself.

{figure("a-call-in-four-moves", "CALL pushes a frame, jumps to the callee, runs the same loop, and RETURN_VALUE pops it")}

`CALL` pushes a new frame onto that per thread stack and points `instr_ptr` at the callee's first instruction. Then the loop goes round again. It has no idea anything special happened. When the callee hits `RETURN_VALUE`, the frame is popped and `instr_ptr` goes back to where the caller left off.

CPython's own notes describe it in exactly those terms: {cite("InternalDocs/interpreter.md:209-214@v3.15.0rc1#CALL")}.

This is why `RETURN_VALUE` had a stack effect of zero back in T06. The value is not removed from this frame's stack, because this frame is about to stop existing. It ends up on the caller's stack instead.
""")


lesson.md(f"""
## Two stacks, and only one of them is small

There are two stacks in play and they are easy to confuse, so the picture below puts them side by side.

{figure("two-stacks", "Python calling Python grows only the data stack, while calling through C grows both")}

The data stack is the per thread thing frames live on. It grows as needed and it is cheap. The C stack is the one your operating system handed the thread when it started, usually eight megabytes, and it does not grow.

{lesson.claim("Python calling Python only grows the interpreter's own frame stack, so ninety thousand deep is fine, while going out through a C function and back in runs out of the real C stack after a few thousand")}. The C function has a real C stack frame that has to stay put while the callback runs, and `sorted` with a `key` is the classic example.

The next cell shows the difference. It takes a few seconds and prints a `RecursionError`, which is the point.

If you are reading this in a browser tab the second half of that cell does not run and says so. Running out of C stack has to be survivable for the cell to print anything, and under WebAssembly the runtime overflows its own call stack before CPython notices. Everything else in this lesson runs there.
""")


lesson.code(
    """
import sys

sys.setrecursionlimit(200_000)

# Running out of C stack has to be survivable for the second half of this cell to print
# anything. On a normal build it is: CPython checks the stack pointer and raises. Under
# WebAssembly the runtime overflows its own call stack first, which is not a Python
# exception and cannot be caught, so the tab dies instead of printing.
RECOVERABLE = sys.platform != "emscripten"


def only_python(n):
    if n == 0:
        return 0
    return only_python(n - 1)


def through_c(n):
    if n == 0:
        return 0
    return sorted([1], key=lambda _ignored: through_c(n - 1))[0]


print("pure Python, 90000 deep:", only_python(90_000), "no complaints")

if not RECOVERABLE:
    print("through sorted: not run here, a browser cannot survive running out of C stack")
else:
    depth = 0
    try:
        while True:
            depth += 500
            through_c(depth)
    except RecursionError as problem:
        print(f"through sorted, gave up somewhere under {depth} deep")
        print("   ", problem)
""",
    varies="How deep you get before the C stack runs out depends on the build and on the machine, so this number is different everywhere. That it stops far earlier than the pure Python version is the part to read.",
)


lesson.md(f"""
The message says "Stack overflow" and gives a size in kilobytes, which is CPython telling you it ran out of C stack rather than out of its own recursion budget. The limit you set with `setrecursionlimit` was never reached.

CPython checks this by comparing the current stack pointer against a limit worked out when the thread started, rather than by counting calls: {cite("InternalDocs/stack_protection.md:33-38@v3.15.0rc1#_Py_EnterRecursiveCall")}. Counting calls does not work, because different C functions use wildly different amounts of stack, and the number you got is specific to your machine and your build.
""")


lesson.md(f"""
## Watching it happen

Everything so far has been description, and the rest of the lesson is observation.

Since 3.12 there is a supported way to ask the interpreter what it is doing, and it is a lot better than the old one. You claim a tool id, register callbacks for the events you care about, and turn those events on for a specific code object.

{figure("what-you-can-watch", "nine of the twenty sys.monitoring events, with when each fires")}

The full list is on `sys.monitoring.events`. Two of the twenty names are not really events: `NO_EVENTS` is zero, and `BRANCH` is the old single event that got split into `BRANCH_LEFT` and `BRANCH_RIGHT`.

{lesson.claim("the events a tool can ask for are a fixed published list on sys.monitoring.events, and four of the six tool ids are already spoken for")}. Those four are debuggers, coverage, profilers and the optimizer, and 3 and 4 belong to nobody, which is where anything you write should live.
""")


lesson.code("""
import sys

monitoring = sys.monitoring

for name in ["DEBUGGER_ID", "COVERAGE_ID", "PROFILER_ID", "OPTIMIZER_ID"]:
    print(f"{name:<14} {getattr(monitoring, name)}")
print()
print("free for you:  3, 4")
print()
events = sorted(name for name in dir(monitoring.events) if name.isupper())
print(len(events), "names on sys.monitoring.events:")
print("   ", ", ".join(events))
""")


lesson.md(f"""
## Frames appearing and disappearing

Three events are enough to draw a call tree: a function started, a function returned, a function left because of an exception. Nothing here parses or guesses, and every line is the interpreter reporting a frame being pushed or popped. {lesson.claim("a frame that leaves because of an exception is reported by a different event than one that returns, so an unwinding stack can be watched one frame at a time")}.
""")


lesson.code("""
import sys

monitoring = sys.monitoring
event = monitoring.events


def leaf(n):
    if n == 0:
        raise ValueError("bottom")
    return leaf(n - 1)


def top():
    try:
        return leaf(2)
    except ValueError:
        return "caught"


ours = {top.__code__, leaf.__code__}
depth = 0


def started(code, offset):
    global depth
    if code not in ours:
        return
    print("  " * depth + "-> " + code.co_name)
    depth += 1


def returned(code, offset, value):
    global depth
    if code not in ours:
        return
    depth -= 1
    print("  " * depth + "<- " + code.co_name + " returned " + repr(value))


def unwound(code, offset, exception):
    global depth
    if code not in ours:
        return
    depth -= 1
    print("  " * depth + "<- " + code.co_name + " left with " + type(exception).__name__)


watching = event.PY_START | event.PY_RETURN | event.PY_UNWIND
monitoring.use_tool_id(3, "call tree")
try:
    monitoring.register_callback(3, event.PY_START, started)
    monitoring.register_callback(3, event.PY_RETURN, returned)
    monitoring.register_callback(3, event.PY_UNWIND, unwound)
    monitoring.set_events(3, watching)
    top()
finally:
    monitoring.set_events(3, 0)
    monitoring.free_tool_id(3)
""")


lesson.md(f"""
Three `leaf` frames go on, the innermost one raises, and all three come off through `PY_UNWIND` rather than `PY_RETURN`. Then `top` catches it and returns normally. That is the frame stack unwinding, one frame per line, as it happens.

That cell uses `set_events`, which turns events on for the whole process, and the callbacks throw away anything that is not one of our two functions. The cheaper call is `set_local_events`, which turns events on for one code object and leaves the rest of the process paying nothing.

{lesson.claim("not every monitoring event can be turned on for a single code object, and which ones can changed between 3.14 and 3.15")}. An event has to happen at a known instruction for the interpreter to instrument that one spot, and the exception events did not qualify on 3.14. The next cell asks your own build rather than taking either version's word for it.
""")


lesson.code(
    """
import sys

monitoring = sys.monitoring
event = monitoring.events


def nothing():
    pass


local = []
monitoring.use_tool_id(3, "asking")
try:
    for name in sorted(name for name in dir(event) if name.isupper()):
        value = getattr(event, name)
        if value == 0:
            continue
        try:
            monitoring.set_local_events(3, nothing.__code__, value)
        except ValueError:
            continue
        local.append(name)
finally:
    monitoring.set_local_events(3, nothing.__code__, 0)
    monitoring.free_tool_id(3)

print(f"{len(local)} events can be turned on for a single code object:")
print("   ", ", ".join(local))
""",
    differs="3.14 has 12 of these events rather than 17. EXCEPTION_HANDLED, PY_THROW, PY_UNWIND, RAISE and RERAISE cannot be set on a single code object there.",
    quiet=True,
)


lesson.md("""
## One instruction at a time

`INSTRUCTION` is the event that fires for every single instruction, and it is what a stepper is built on. One thing it will not give you is described below.
""")


lesson.md(f"""
{figure("where-the-numbers-come-from", "static heights and observed order joined into one listing")}

{lesson.claim("nothing in the standard library can read the values sitting on the value stack", unobservable="what would show it is the absence of a door, and the cells below demonstrate the way around it rather than the missing thing")}. Not `sys.monitoring`, not `sys.settrace`, not the frame object. Those values live in the frame's memory and there is no Python level door to them.

What we can do is join two things. The order instructions ran in is a real observation from `sys.monitoring`. The stack height at each offset is what `pyxray.stack` computed in T06 by walking the code object. Join them and you get the height at every step of a real run, as long as nobody pretends it was measured.

`pyxray.stepper` does exactly that and its docstring says so. Here it is on a loop, where {lesson.claim("the deepest the stack gets on a real run is exactly the co_stacksize the compiler wrote down")}.
""")


lesson.code(
    """
from pyxray import stepper


def total_of(items):
    total = 0
    for item in items:
        total = total + item
    return total


recording = stepper.run(total_of, [1, 2, 3])
print("returned:", recording.result)
print("deepest the stack got:", recording.deepest)
print("co_stacksize says:", total_of.__code__.co_stacksize)
print()
print(recording.table())
""",
    differs="On 3.14 the offsets are lower and the deepest the stack gets is 3 rather than 4, because the loop is compiled a little differently. The shape of the recording is the same.",
)


lesson.md("""
Read the offset column rather than the step column. It counts up, then drops back to the offset of the `FOR_ITER`, three times over. That is the loop, and the drop is the back edge T06 taught you to spot in a listing, here being taken. The exact offsets depend on your version, because inline cache sizes change between releases, and the shape stays the same.

The bars on the right are the stack height after each instruction. It peaks inside the loop body, when `LOAD_FAST_BORROW_LOAD_FAST_BORROW` puts both `total` and `item` on top of what was there, then comes back down. That peak is exactly `co_stacksize`, the number T06 spent half a lesson working out, and this run used all of it. The last `FOR_ITER` is the one that finds the list empty, and after it comes `POP_ITER`.
""")


lesson.md(f"""
### The instruction that never shows up

Count rows against a disassembly of `total_of` and one instruction is missing. There is an `END_FOR` between the last `FOR_ITER` and the `POP_ITER`, and it does not appear in the table above at all.

That is deliberate, and written into the instruction's declaration: {cite("Python/bytecodes.c:393-400@v3.15.0rc1#END_FOR")}. The `no_save_ip` marker means it does not update the recorded instruction pointer, so as far as instrumentation is concerned it never becomes the current instruction. `POP_ITER` needs to see the `FOR_ITER` as the instruction before it.

{lesson.claim("END_FOR is compiled into the loop and never reported to instrumentation, so an instruction that certainly ran is missing from the recording")}. That would cost you an afternoon if you hit it without warning, so `pyxray` has a test pinning it.
""")


lesson.code(
    """
import dis

compiled = {item.offset: item.opname for item in dis.get_instructions(total_of)}
executed = {moment.offset for moment in recording.moments}

print("compiled but never reported:")
for offset, opname in compiled.items():
    if offset not in executed:
        print(f"   {offset:>4}  {opname}")
""",
    differs=OFFSETS,
    quiet=True,
)


lesson.md(f"""
## Which way did the branch go

`INSTRUCTION` is the heaviest event there is, and most of the time you want less. {lesson.claim("the branch events report only the places control could have gone two ways, and say which way it went, so a two item loop is five reports rather than twenty seven")}.
""")


lesson.code(
    """
import sys

monitoring = sys.monitoring
event = monitoring.events


def total_of(items):
    total = 0
    for item in items:
        total = total + item
    return total


def note(name):
    def callback(code, offset, destination):
        print(f"{name:<13} at {offset:>3}  went to {destination}")

    return callback


watching = event.JUMP | event.BRANCH_LEFT | event.BRANCH_RIGHT
monitoring.use_tool_id(3, "branches")
try:
    for name in ["JUMP", "BRANCH_LEFT", "BRANCH_RIGHT"]:
        monitoring.register_callback(3, getattr(event, name), note(name))
    monitoring.set_local_events(3, total_of.__code__, watching)
    total_of([1, 2])
finally:
    monitoring.set_local_events(3, total_of.__code__, 0)
    monitoring.free_tool_id(3)
""",
    differs=OFFSETS,
    quiet=True,
)


lesson.md("""
Five lines for a two item loop. Every `BRANCH_LEFT` and `BRANCH_RIGHT` is at the same offset, and that offset is the `FOR_ITER`. Left means there was another item, right means there was not. The `JUMP` is the back edge, taken once per item except the last.

This is what a coverage tool wants. It does not care about every instruction, it cares about which edges of the graph were taken, and there are five of those here against twenty seven instructions.

## Why this is cheap

One design decision makes `sys.monitoring` different from everything before it.
""")


lesson.md(f"""
{figure("turning-an-event-off", "returning None keeps firing, returning DISABLE stops at that location")}

{lesson.claim("returning DISABLE turns an event off at one code location rather than everywhere, so a five pass loop reports each instruction once instead of five times")}. It stays off until somebody calls `restart_events`, which is why a loop that runs a million times fires the callback once per instruction in the body and then goes quiet.

The next cell counts the calls both ways on the same five pass loop.
""")


lesson.code("""
import sys

monitoring = sys.monitoring
event = monitoring.events


def five_times():
    total = 0
    for n in range(5):
        total = total + n
    return total


def count(disable):
    seen = []
    monitoring.use_tool_id(3, "counting")
    try:

        def callback(code, offset):
            seen.append(offset)
            return monitoring.DISABLE if disable else None

        monitoring.register_callback(3, event.INSTRUCTION, callback)
        monitoring.set_local_events(3, five_times.__code__, event.INSTRUCTION)
        five_times()
    finally:
        monitoring.set_local_events(3, five_times.__code__, 0)
        monitoring.free_tool_id(3)
    return seen


for label, disable in [("returning None", False), ("returning DISABLE", True)]:
    seen = count(disable)
    print(f"{label:<18} {len(seen):>3} calls, {len(set(seen)):>3} distinct offsets")
""")


lesson.md(f"""
Forty calls against fifteen: the loop body ran five times and the callback saw it once.

The old way is `sys.settrace`, which is what `pdb` and the original `coverage` are built on. One hook for the whole process, firing on every line of every function, with no way to say stop telling me about this one. Turning it on also switches the interpreter into a slower dispatch mode for everything: {cite("Python/ceval_macros.h:128-141@v3.15.0rc1#DISPATCH_GOTO")} is where the tracing and non tracing tables diverge.

For comparison, here is `settrace` on a three pass loop, where {lesson.claim("sys.settrace has no way to be switched off at one place, so every line of every pass through a loop costs a callback")}.
""")


lesson.code("""
import sys
from collections import Counter


def three_times():
    total = 0
    for n in range(3):
        total = total + n
    return total


seen = Counter()


def trace(frame, kind, argument):
    if frame.f_code is three_times.__code__:
        frame.f_trace_opcodes = True
        seen[kind] += 1
        return trace
    return None


sys.settrace(trace)
three_times()
sys.settrace(None)

print(sum(seen.values()), "callbacks for a three pass loop")
for kind, number in seen.most_common():
    print(f"   {kind:<8} {number}")
""")


lesson.md(f"""
Thirty nine calls, with no way to reduce them except by turning the whole thing off. `sys.monitoring` was added because debuggers and coverage tools were paying that price on every line of every program they touched. `settrace` still works, but reach for the newer one.

## Frames from Python

The frame the interpreter uses is not a Python object, it is the block of memory from the diagram earlier. `PyFrameObject`, the thing `sys._getframe()` gives you, is built on demand and cached in the `frame_obj` field of that block.

The caching is visible from Python: {lesson.claim("asking for the frame twice gives back the same object, and that object is still usable after the call it belonged to has returned")}.
""")


lesson.code("""
import sys


def make_one():
    first = sys._getframe()
    second = sys._getframe()
    return first is second, first


same, escaped = make_one()
print("asked twice, got the same object:", same)
print("and it is still here after the call returned:", escaped)
print("its name:", escaped.f_code.co_name)
""")


lesson.md(f"""
The frame object outliving the call is the whole reason frames are not on the C stack. A traceback holds onto frames, a generator is a frame that got paused, and a closure can keep one alive indefinitely. None of that would work if the frame went away when the C function returned.

Locals are worth one more cell, because {lesson.claim("writing through f_locals changes the actual local variable and writing to the dictionary locals() hands back changes nothing")}, and the two look the same from the outside.
""")


lesson.code("""
import sys


def show():
    x = 1
    proxy = sys._getframe().f_locals
    snapshot = locals()
    print("f_locals is a", type(proxy).__name__)
    print("locals() is a", type(snapshot).__name__)

    proxy["x"] = 99
    print("after writing through f_locals, x is", x)

    snapshot["x"] = 1000
    print("after writing to the locals() dict, x is", x)


show()
""")


lesson.md(f"""
`f_locals` is a live view onto the frame's slots, so writing through it changes the actual local. `locals()` inside a function is a plain dictionary copied out of those slots, so writing to it changes nothing. This used to be much more confusing than it is now, and the current behaviour was pinned down deliberately.

## The frame chain

{lesson.claim("every frame keeps a pointer to the one that called it, and walking that chain from the inside out is all a traceback is")}. The pointer is `previous` in the struct.
""")


lesson.code(
    """
from pyxray import stepper


def third():
    for name, line in stepper.chain():
        print(f"{name:<20} line {line}")


def second():
    third()


def first():
    second()


first()
""",
    varies="The frames above yours belong to whatever is running the notebook, so those names and line numbers come from Jupyter and asyncio rather than from anything the lesson did. The bottom of the list is your three functions, and that is the part to read.",
)


lesson.md("""
Innermost first, out to whatever is running the notebook. `stepper.chain` is nine lines and does nothing clever: take `sys._getframe()` and read `f_back` until it is `None`.

## Try it yourself

**One.** Run the stepper on a function with a `try` and an `except` in it, and raise something. Watch where the offsets jump to when the exception fires, then compare that with what `dis` shows for the exception table.

**Two.** Take the branch counting cell and turn it into a small coverage tool: record every `(offset, destination)` pair once, return `DISABLE`, and afterwards report which branches were never taken.

**Three.** `stepper.run` records the function you pass it and nothing it calls. Change it so it records a whole call tree by setting local events on the callee too when `PY_START` fires, then find out how much slower the recording is.

**Four.** Find the recursion depth your machine allows through `sorted`, then try again with the thread's stack size raised using the `threading.stack_size` function. The number should move.
""")


lesson.md(f"""
## What just happened

The interpreter is one loop: read two bytes, look up the handler, run it, move the pointer on. Everything Python does is a handler inside that loop.

How the loop reaches the handler depends on the build: a `switch`, a computed goto through a jump table, or a tail call through a table of functions. Same results either way.

A frame is one block of memory holding the specials, the locals, and `co_stacksize` slots of working space. Frames go on a per thread stack, not on the C stack, so they can outlive the call.

Python calling Python pushes a frame and jumps rather than recursing in C, which is why ninety thousand deep is fine. Going out through a C function and back in grows the real C stack, which is a few megabytes and runs out at a few thousand.

`sys.monitoring` reports what the interpreter is doing, per code object, with a `DISABLE` return value that switches an event off at one location. That makes it cheap in a way `sys.settrace` never was.

Nothing in the standard library reads the values on the value stack. Joining observed instruction order with statically computed heights gets you most of the way, and it is worth being clear about which half is which.

## Where this goes next

You have now followed one line of Python from text all the way to a running instruction, which was the whole point of the first part.

T08 turns around and looks at what all those instructions have been pushing and popping. Every one of those values is a `PyObject`, every `PyObject` has a {term("type object", "type")}, and the type is where the behaviour lives. That is the start of the second half.
""")


raise SystemExit(lesson.save())
