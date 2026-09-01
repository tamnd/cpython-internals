#!/usr/bin/env python
"""E03. Where a running function lives.

The third lesson of the interpreter part. E02 followed the instruction pointer through the
code. This one is about the thing that pointer is pointing into, and about the space a
running function keeps its locals in.

The argument of the lesson is that there are two stacks. Python calls go on one, C calls go
on the other, and the two have different sizes, different limits and different error
messages. Almost everything people find confusing about recursion in Python comes from
treating them as one thing.

All of it is measurable. A thread with a known stack size, three routes to the same
recursion, and you can read the cost per level straight off the depth each one reached.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("e03-where-a-running-function-lives", "e03")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("e03-where-a-running-function-lives").figure


lesson.md(f"""
# E03. Where a running function lives

{badge}

A function that is running has to keep things somewhere. Its local variables, its place in the code, the half finished values it is working on, and who to go back to when it is done. In most languages all of that sits on the machine's stack, and how deep you can recurse is how much of that stack there is.

Python does it differently, and the difference is bigger than it sounds. A Python function calling another Python function uses no machine stack at all. The same call routed through a C function uses about a kilobyte, and through `sorted` about five.

{figure("two-stacks", "the data stack and the C stack side by side with what limits each one")}

Two stacks, two limits, two different `RecursionError` messages. This lesson measures all of it.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/pystate.c:3133-3143@v3.15.0rc1#_PyThreadState_PushFrame`.

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

Everything below was checked against the version this cell prints and against 3.14. Most of this lesson gives the same answers on both, which is unusual for this part of the book. The frame layout has been stable for a while. The cells that measure the machine stack are the ones that move, and they move per machine rather than per version.
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
## One frame, and everything in it

A {term("frame", "frame")} is the working space for one call. Not one per function, one per call, so a function called twice has two of them.

In C it is a struct of about a dozen fields, {cite("Include/internal/pycore_interpframe_structs.h:29-53@v3.15.0rc1#_PyInterpreterFrame")}. Who called it, which code object it is running, where in that code it is, a pointer to the top of its value stack, and then an array on the end holding the locals and the stack together.

{figure("what-is-in-a-frame", "the five things a frame keeps, with the locals and the value stack as one array")}

`sys._getframe` hands you a Python object that reads out of one of those. Ask twice and you get the same object, because the first ask is what created it and it is kept on the frame from then on, {cite("Include/internal/pycore_interpframe.h:307-320@v3.15.0rc1#_PyFrame_GetFrameObject")}.

{lesson.claim("sys._getframe returns the same object each time it is called in one frame, and the frame it returns keeps working after the function has returned")}
""")


lesson.code(
    """
def outer():
    return inner("made while inner was still running")


def inner(label):
    return sys._getframe()


held = outer()

print(f"  type of it                {type(held).__name__}")
print(f"  its code is inner's       {held.f_code is inner.__code__}")
print(f"  who called it             {held.f_back.f_code.co_name}")
print(f"  and above that            {held.f_back.f_back.f_code.co_name}")
print(f"  where it got to, in bytes {held.f_lasti}")
print(f"  its locals, after return  {dict(held.f_locals)}")


def twice():
    return sys._getframe() is sys._getframe()


print(f"  same object each time     {twice()}")
""",
    varies="Only the byte offset moves. It is a position in the instruction stream, so it "
    "depends on how many cache slots the instructions ahead of it carry, and E02 showed "
    "that changing between releases. It reads 44 on 3.15, 42 on 3.14 and 40 on the browser "
    "build. Every other line is the same everywhere.",
)


lesson.md(f"""
Both `outer` and `inner` have returned by the time that runs, and the chain above the held frame is still intact. That is not the frames surviving. When a call finishes while somebody is still holding its frame object, the object copies the contents into its own storage and then builds the objects for everything below it too, {cite("Python/frame.c:47-68@v3.15.0rc1#take_ownership")}.

{figure("one-object-or-two", "the interpreter frame against the frame object, when each exists and what it costs")}

So there are two things both called a frame. The interpreter runs on a bare struct with no reference count and no type. The `frame` object is a real Python object made only when something asks, and `sys._getframe` is asking. So is raising an exception, and so is any debugger, which is a good part of why tracing is slow.

## The locals are a flat array, not a dictionary

The last field of the struct is one array holding the local variables followed by the value stack, {cite("Include/internal/pycore_interpframe_structs.h:51-53@v3.15.0rc1#localsplus")}. A local variable is a slot in it, and `LOAD_FAST` is a read at an index, {cite("Python/bytecodes.c:283-286@v3.15.0rc1#LOAD_FAST")}, with the macro for the read being a single array subscript, {cite("Python/ceval_macros.h:284@v3.15.0rc1#GETLOCAL")}.

That is why the argument to `LOAD_FAST` is a number rather than a name, and why `co_varnames` exists at all: it is the mapping from that number back to something a person can read.

{lesson.claim("a local variable is a numbered slot in the frame rather than an entry in a dictionary, and the argument to LOAD_FAST is that number")}
""")


lesson.code(
    """
import dis


def demo():
    total = 0
    name = "x"
    return total, name


print(f"  co_varnames  {demo.__code__.co_varnames}")
print()
for one in dis.get_instructions(demo):
    if one.opname.startswith(("LOAD_FAST", "STORE_FAST")):
        print(f"  {one.opname:36} arg {one.arg}   which is {one.argrepr}")
""",
)


lesson.md(f"""
The last line is worth a second look. One instruction, one argument byte, two variables loaded. The compiler packs two four bit indices into the one byte, which is the same trick from E02 applied to the same one byte field.

`frame.f_locals` still gives you something that behaves like a dictionary, but since 3.13 it is a proxy that reads and writes those slots rather than a copy of them. Writing to it changes the variable.

{lesson.claim("frame.f_locals inside a function is a write through proxy over the frame slots, so assigning through it changes the local variable")}
""")


lesson.code(
    """
def writer():
    x = 1
    kind = type(sys._getframe().f_locals).__name__
    sys._getframe().f_locals["x"] = 99
    return kind, x


kind, value = writer()

print(f"  what f_locals is in a function  {kind}")
print(f"  x after writing through it      {value}")
""",
)


lesson.md(f"""
## The frame is inside the generator

Most frames are gone the moment the call returns. A generator is the exception: its frame has to survive between one `yield` and the next `next`, so the generator object has a whole frame embedded in it, {cite("Include/internal/pycore_interpframe_structs.h:56-73@v3.15.0rc1#_PyGenObject_HEAD")}.

That makes the frame's size measurable from Python, because `sys.getsizeof` on a generator includes it. Build generators over functions with more and more locals and the size should climb by exactly one pointer per local.

{lesson.claim("a generator object contains its frame, so its size grows by exactly eight bytes for every extra local variable or value stack slot")}
""")


lesson.code(
    """
def build(count):
    body = "\\n".join(f"    x{n} = {n}" for n in range(count))
    namespace = {}
    exec(f"def gen():\\n{body}\\n    yield 0\\n", namespace)
    return namespace["gen"]


print("  locals  stack  slots   bytes   over the row above")
previous = None
for count in [0, 1, 2, 5, 10, 20, 50]:
    made = build(count)
    running = made()
    next(running)
    shape = made.__code__
    slots = shape.co_nlocals + shape.co_stacksize
    size = sys.getsizeof(running)
    step = "" if previous is None else f"{size - previous}"
    print(f"  {shape.co_nlocals:6} {shape.co_stacksize:6} {slots:6} {size:7}   {step}")
    previous = size
""",
    varies="Both numbers halve on a 32 bit build, so in a browser the header is 92 bytes "
    "and the step is 4. That is the whole explanation: a slot is one pointer, and a "
    "pointer there is four bytes rather than eight.",
)


lesson.md(f"""
A fixed 168 bytes of header and eight bytes a slot, on the nose, on both versions. Eight bytes is the size of a pointer, and a slot holds one. That is the clearest look at the frame you can get without a debugger: the number of locals plus the number of value stack slots, times the size of a pointer.

## Making a frame is moving a pointer

Ordinary frames do not come from `malloc` and they do not go on the machine's stack. The thread keeps its own region, a linked list of chunks, and pushing a frame takes the next few slots off the top, {cite("Python/pystate.c:3133-3143@v3.15.0rc1#_PyThreadState_PushFrame")}. Only when a chunk runs out does anything get allocated, and a chunk is sixteen kilobytes, {cite("Include/cpython/pystate.h:65@v3.15.0rc1#_PY_DATA_STACK_CHUNK_SIZE")}, doubled if a single frame needs more than that, {cite("Python/pystate.c:3097-3131@v3.15.0rc1#push_chunk")}.

{figure("where-a-frame-comes-from", "four steps from a call to a running frame, none of which allocate")}

This {term("data stack", "data stack")} is the first of the two stacks. The second is the {term("C stack", "C stack")}, the real one, whose size is fixed when the thread starts.

A Python function calling a Python function does not touch the second one. The eval loop sets up the new frame and keeps going round its own loop, so no C function is entered and nothing is pushed. A call that leaves for C and comes back, like a `key` function passed to `sorted` or a `__repr__` reached through `repr`, does enter C, and every level of that costs real stack.

You can measure the difference exactly. Run the same recursion three ways in a thread with a known stack size, and see how deep each one gets before it stops.

{lesson.claim("a Python function calling a Python function uses no C stack, while the same recursion routed through a C function costs hundreds or thousands of bytes per level")}
""")


lesson.code(
    """
import threading

MEGABYTE = 1 << 20


def straight(go):
    go()


def through_sorted(go):
    sorted([1], key=lambda item: go())


class Box:
    def __init__(self, go):
        self.go = go

    def __repr__(self):
        self.go()
        return ""


def through_repr(go):
    repr(Box(go))


def deepest(step, limit):
    reached = 0
    answer = []

    def go():
        nonlocal reached
        reached += 1
        step(go)

    def run():
        sys.setrecursionlimit(limit)
        try:
            go()
        except RecursionError as stopped:
            answer.append((reached, str(stopped)))
        else:
            answer.append((reached, "did not stop"))

    threading.stack_size(MEGABYTE)
    worker = threading.Thread(target=run)
    worker.start()
    worker.join()
    return answer[0]


try:
    threading.stack_size(MEGABYTE)
    idle = threading.Thread(target=int)
    idle.start()
    idle.join()
    HAS_THREADS = True
except RuntimeError:
    HAS_THREADS = False


def report(name, step, limit=1000000):
    if not HAS_THREADS:
        print(f"  {name:32} this runtime has no threads, so there is nothing to measure")
        return
    reached, message = deepest(step, limit)
    if "maximum recursion" in message:
        print(f"  {name:32} depth {reached:7}   {message}")
    else:
        each = MEGABYTE // reached
        print(f"  {name:32} depth {reached:7}   {message[:29]}, about {each} bytes")


print(f"  thread stack size: {MEGABYTE // 1024} kB")
print()
for name, step in [
    ("python to python", straight),
    ("through repr", through_repr),
    ("through sorted", through_sorted),
]:
    report(name, step)
""",
    varies="The two depths that end in a stack overflow depend on your machine and your "
    "build, so expect different numbers. On the two builds this was written against they "
    "come out near 1150 levels through repr, at about 914 bytes each, and near 185 through "
    "sorted, at about 5670 bytes each. The first row stops for a completely different "
    "reason on any machine. In a browser runtime there are no threads at all, so the cell "
    "says so and measures nothing.",
)


lesson.md(f"""
Three numbers, and the first one is the point. Half a million levels deep in a one megabyte thread, and it stopped because a counter said so, not because anything ran out. The machine stack never noticed, because it was never used. The other two ran out of the same megabyte in a few hundred levels.

{figure("what-a-level-of-recursion-costs", "bytes of C stack per level for the three routes")}

`sorted` costs six times what `repr` does because `list.sort` keeps a fair sized working structure in its own C frame. Nothing about that is Python's doing. It is just what that C function needs, and it is on the shared stack whether you use it or not.

## Two limits, two messages

That experiment produced two different `RecursionError` messages, and they come from two different checks.

The counter is `sys.setrecursionlimit`. It counts Python calls, has nothing to do with memory, and raises a plain "maximum recursion depth exceeded", {cite("Python/ceval.c:1014-1032@v3.15.0rc1#py_recursion_remaining")}.

The other check does not count anything. It compares the current stack pointer against a limit worked out when the thread started, {cite("Include/internal/pycore_pystate.h:330-341@v3.15.0rc1#_Py_RecursionLimit_GetMargin")}, keeping a margin in reserve so that raising the error does not itself overflow, {cite("Include/internal/pycore_pythonrun.h:55-67@v3.15.0rc1#_PyOS_STACK_MARGIN")}. When it fires it reports kilobytes used rather than a depth, {cite("Python/ceval.c:306-322@v3.15.0rc1#RecursionError")}, which is the tell that you are looking at the real stack.

{figure("two-limits-two-messages", "the two RecursionError messages, what ran out, and what changes each one")}

Which means raising the recursion limit moves one of them and does nothing whatsoever to the other.

{lesson.claim("sys.setrecursionlimit changes only the counter, so raising it lets pure Python recursion go further and leaves recursion through C stopping at the same depth for the same reason")}
""")


lesson.code(
    """
for limit in [5000, 20000, 100000]:
    report(f"limit {limit:6}  python to python", straight, limit)

print()
for limit in [20000, 100000]:
    report(f"limit {limit:6}  through repr", through_repr, limit)

sys.setrecursionlimit(1000)
""",
    varies="The first three rows should come out at about half the limit on any machine, "
    "since each level here is two Python calls. The last two should be the same number "
    "twice, whatever that number is on yours, and nowhere near either limit. Around 1150 "
    "here. The message reports kilobytes used, which is how you tell the two errors apart.",
)


lesson.md("""
The counter did what it was told, three times. The depth comes out at half the limit rather than all of it because each level here is two Python calls, `go` and the step it goes through, and the counter counts both. The other check did not move at all, because the limit was never what stopped it.

There is one more consequence worth having. The stack size is fixed per thread, and `threading.stack_size` sets it for threads you start yourself. If you have code that recurses through C and you cannot flatten it, giving its thread a bigger stack is the lever that actually works. Raising the recursion limit is the lever that looks like it should.

## Try it yourself

Three things to poke at.

The first is to find the cheapest and most expensive routes into C. Take the `report` helper above and pass it steps that go through `map`, through `min` with a key, through `json.dumps` with a `default`, through an operator like `__add__` on a class you wrote. The costs are not close to each other, and the reason is always the same: whatever that particular C function keeps in its own frame.

The second is about generators. The size formula in this lesson was a fixed header plus eight bytes a slot. Check it against a function with a deep expression in it, where `co_stacksize` is large but `co_nlocals` is small. Then check it against a comprehension, which compiles to its own code object with its own frame.

The third is the one that shows what a frame object costs. Install a trace function with `sys.settrace` that does nothing at all, and time a small recursive function with it on and off. Every call now materialises a frame object. The gap between the two timings is the price of the thing this lesson said is created only when somebody asks.

## What just happened

A frame is the working space for one call, and it is a plain C struct: who called it, which code object, where in that code, and one array holding the locals followed by the value stack.

A local variable is a numbered slot in that array. `LOAD_FAST 1` is a subscript, `co_varnames` is the mapping back to names, and `f_locals` is a proxy over the slots rather than a dictionary, so writing through it changes the variable.

The `frame` object you can hold is a different thing from the frame the interpreter runs on. It is made only when something asks, cached from then on, and if the call returns while you are still holding it, it copies the contents into itself and materialises the whole chain below.

Generators keep their frame inside the generator object, which makes the size measurable: a fixed 168 byte header plus eight bytes for every local and every value stack slot.

Frames come off a data stack the thread owns, in chunks of sixteen kilobytes, so a call is a pointer bump rather than an allocation.

That data stack is not the machine's stack, and that is the whole point. Half a million Python calls deep in a one megabyte thread costs nothing on the C stack. The same recursion through `repr` costs about 900 bytes a level and through `sorted` about 5600, and runs out in a few hundred.

So there are two limits. `sys.setrecursionlimit` counts Python calls and says "maximum recursion depth exceeded". The other checks how much real stack is left and says how many kilobytes were used. Raising the first does nothing to the second.

## What is next

E04 is `_PyStackRef`, which is what is actually in those slots. Not a `PyObject *`, and not since 3.14. The bottom bits carry a flag saying whether this reference is owned or borrowed, and the entire reason for that is the free threaded build, where taking a reference count is an atomic operation nobody wants to pay for on every `LOAD_FAST`.
""")


raise SystemExit(lesson.save())
