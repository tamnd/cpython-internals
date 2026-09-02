#!/usr/bin/env python
"""M01. Three doors into the same heap.

The first lesson of the memory part. CPython does not have one allocator, it has three
entrances to one, and which entrance a block came through is recorded in the block itself.
Switch the debug hooks on and that record is a single byte you can read with `ctypes`.

Everything here hangs off that one byte. The three doors, the fences either side of your
data, the fillers that say fresh and dead, the fatal error you get for mixing doors up, the
second block hiding behind a list, and the point where the object door stops serving
requests itself and passes them down.

The cells that need the debug hooks ship their function to a fresh interpreter started with
`PYTHONMALLOC=debug`, the same trick E10 and E12 use for the JIT, because the hooks have to
be in place before the interpreter starts.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("m01-three-doors-into-the-same-heap", "m01")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("m01-three-doors-into-the-same-heap").figure


lesson.md(f"""
# M01. Three doors into the same heap

{badge}

Every object you have made in these lessons had to come from somewhere. That somewhere is a heap CPython manages itself, and there are three separate front doors into it.

They are not aliases for each other. Take a block through one door and hand it back through another and the interpreter stops the process on the spot.

{figure("three-doors", "the raw, mem and obj doors with the C function and marker byte for each")}

The last column is the good part. Under one environment variable, every block carries a byte saying which door it came from, and you can read that byte from Python.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Objects/obmalloc.c:3088-3097@v3.15.0rc1`.

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

The first measuring cell runs anywhere, including a browser. Every cell after it needs a second interpreter started with an environment variable set, which a browser cannot do, so this is one of the few lessons that really does want a machine with Python on it. Those cells say so rather than failing.

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
## The obj door keeps count

Before any of the byte reading, here is the one thing about all this you can see from an ordinary interpreter with nothing switched on.

The obj door keeps a running total of how many blocks it has handed out and not got back, and `sys.getallocatedblocks` reports it. Every object is one block, so the number should move by one per object.

{lesson.claim("Making a hundred thousand objects moves sys.getallocatedblocks by a hundred thousand and one, and dropping them moves it back")}
""")


lesson.code(
    """
import sys

start = sys.getallocatedblocks()
kept = [object() for _ in range(100000)]
made = sys.getallocatedblocks()
del kept
gone = sys.getallocatedblocks()

if made == 0:
    print("  this build has no small object allocator, so there is nothing for it to count")
else:
    print(f"  blocks the allocator was holding   {start}")
    print(f"  after a hundred thousand objects   {made}, {made - start} more")
    print(f"  after dropping every one of them   {gone}, {made - gone} fewer")
""",
    varies="The first number is how much of the standard library your interpreter imported at "
    "startup, so it is different on every machine and in a browser. The two differences are "
    "the part to read, and they should be a hundred thousand and one either way.",
)


lesson.md("""
A hundred thousand and one. The one extra is the list holding them, and it went through the obj door too.

Then all of it comes back. That is the whole of the bookkeeping the obj door does, and it is the only one of the three doors that does any.

If you are reading this in a browser you got zero instead, three times. That is not a failure. A browser build has CPython's own allocator compiled out and uses the one the runtime provides, so there is nothing keeping the count. The last section of this lesson does the same thing on purpose with an environment variable.

Everything after this needs the fences, so it needs a second interpreter.
""")


lesson.md(f"""
## Turning the fences on

CPython ships a set of {term("debug hooks")} that wrap whatever allocator is underneath. They are off in a normal build and on in a debug build, and you can switch them on anywhere by starting Python with `PYTHONMALLOC=debug`.

With them on, every allocation is quietly made bigger and the extra space is filled in {cite("Objects/obmalloc.c:3088-3097@v3.15.0rc1")}. Your pointer still points at the part you asked for. Everything else is behind your back.

{figure("what-the-fences-look-like", "the debug block layout with the size, the door byte, the fences and your data")}

The writing of it is nine lines {cite("Objects/obmalloc.c:3114-3128@v3.15.0rc1")}: the size goes in first, then one byte naming the door, then fence bytes, then your data, then more fence bytes.

Since the hooks have to be in place before the interpreter starts, the cells below ship a function to a fresh interpreter that has them. Here is the helper, and it is the same shape as the one E10 used for the JIT.
""")


lesson.code("""
import inspect
import os
import subprocess
import sys


def with_the_fences(body, *also):
    try:
        shipped = "".join(inspect.getsource(one) + chr(10) for one in also)
        script = shipped + inspect.getsource(body) + f"{chr(10)}{body.__name__}(){chr(10)}"
        done = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env=dict(os.environ, PYTHONMALLOC="debug"),
            timeout=300,
        )
    except OSError:
        return "  this runtime cannot start a second interpreter, so try this on a real machine"
    return (done.stdout + done.stderr).rstrip()


def run_at(at, count):
    import ctypes

    return bytes(ctypes.c_ubyte.from_address(at + i).value for i in range(count))


def block_at(at):
    import ctypes

    step = ctypes.sizeof(ctypes.c_size_t)
    asked = int.from_bytes(run_at(at - 2 * step, step), "big")
    which = chr(ctypes.c_ubyte.from_address(at - step).value)
    return asked, which, run_at(at - step + 1, step - 1).hex()


def fence_behind(at):
    import ctypes

    step = ctypes.sizeof(ctypes.c_size_t)
    return run_at(at + block_at(at)[0], step).hex()


def allocator(name):
    import ctypes

    fn = getattr(ctypes.pythonapi, name)
    taking = "Malloc" in name
    fn.restype = ctypes.c_void_p if taking else None
    fn.argtypes = [ctypes.c_size_t if taking else ctypes.c_void_p]
    return fn


print("ready")
""")


lesson.md(f"""
## One byte says which door

The three doors are one {term("allocator domain")} each, listed as an enum in the public header {cite("Include/cpython/pymem.h:5-14@v3.15.0rc1#PyMemAllocatorDomain")}, and each one has its own set of four function pointers that a program embedding Python is allowed to replace.

`ctypes` can call all three directly, so we can ask each of them for four hundred bytes and then read the byte the hooks wrote in front of the block.

{lesson.claim("A block allocated through PyMem_RawMalloc, PyMem_Malloc or PyObject_Malloc carries the byte r, m or o in front of it")}
""")


lesson.code("""
def three_doors():
    rows = []
    for name in ("PyMem_RawMalloc", "PyMem_Malloc", "PyObject_Malloc"):
        at = allocator(name)(400)
        asked, which, front = block_at(at)
        back = fence_behind(at)
        fresh = run_at(at + 200, 8).hex()
        allocator(name.replace("Malloc", "Free"))(at)
        rows.append((name, which, asked, front, back, fresh, run_at(at + 200, 8).hex()))

    for name, which, asked, front, back, fresh, after in rows:
        print(f"  {name:16} door {which!r}  you asked for {asked}")
        print(f"  {'':16} fences   {front} in front, {back} behind")
        print(f"  {'':16} the data {fresh} while yours, {after} once handed back")


print(with_the_fences(three_doors, run_at, block_at, fence_behind, allocator))
""")


lesson.md(f"""
Three doors, three letters, and the fences are the same on both sides of every block.

Look at the last line of each row as well. The bytes are not random. There are three of them and they were picked to be obvious when they turn up somewhere they should not {cite("Include/internal/pycore_pymem.h:33-42@v3.15.0rc1#PYMEM_CLEANBYTE")}.

{figure("three-bytes-worth-knowing", "0xCD for fresh memory, 0xDD for freed memory and 0xFD for the fences")}

`0xCD` is what you get in a fresh block, so reading a variable you never wrote gives you a number full of `cd`. `0xDD` is what a block is filled with when you hand it back, so a pointer you kept after freeing it points at `dd`. Neither is a plausible small number, a plausible address or a letter, which is the whole idea.

The raw door is the odd one out on that last line. It fills the block with `0xDD` too and then gives the memory back to the system, and after that what is in there is the system's business rather than CPython's.
""")


lesson.md(f"""
## What a real object came through

Now the same reading, but on objects you did not allocate by hand.

There is one wrinkle. Objects the cycle collector tracks are allocated with two extra words in front of them for the collector's own list, and `id()` gives you the address after those words. So the block starts either right in front of the object or two words further back, and the cell below finds out which by looking for the fences.

{lesson.claim("A Python object's memory comes through the obj door, and the size stored in front of it is the size of that one block rather than everything sys.getsizeof counts")}
""")


lesson.code(
    """
def real_objects():
    import ctypes
    import sys

    step = ctypes.sizeof(ctypes.c_size_t)
    fence = bytes([0xFD]) * (step - 1)

    def start_of(obj):
        for back in (0, 2 * step):
            asked, which, front = block_at(id(obj) - back)
            if which in "rmo" and bytes.fromhex(front) == fence:
                return back, asked, which
        return None, None, None

    print("  object      bytes in front   block   door   getsizeof")
    for obj in ["hello world", 12345678901234567890, 1.5, object(), (1, 2, 3), [1, 2, 3]]:
        back, asked, which = start_of(obj)
        print(
            f"  {type(obj).__name__:10}  {back:14}  {asked:6}  {which!r:5}  {sys.getsizeof(obj):10}"
        )


print(with_the_fences(real_objects, run_at, block_at))
""",
    varies="The exact sizes depend on the build. A 32 bit build, which is what a browser gives "
    "you, halves the word size and every number in the table with it.",
)


lesson.md(f"""
Read the first two rows against the last two.

A string, an int, a float and a plain `object` have nothing in front of them, because the collector does not track them. A tuple and a list have sixteen bytes in front, which is the {term("GC pre header")}, and it is inside the block rather than an extra allocation.

The `block` column and the `getsizeof` column agree for everything except the list. That is not an error in either of them. They are counting different things.

{lesson.claim("A list is two blocks, and the second one came through the mem door rather than the obj door")}
""")


lesson.code("""
def two_blocks():
    import ctypes
    import sys

    step = ctypes.sizeof(ctypes.c_size_t)
    numbers = list(range(20))
    at = id(numbers)
    items = ctypes.c_void_p.from_address(at + 3 * step).value
    object_block, object_door, _ = block_at(at - 2 * step)
    item_block, item_door, _ = block_at(items)
    print(f"  the list object itself   {object_block:4} bytes through the {object_door!r} door")
    print(f"  the array of its items   {item_block:4} bytes through the {item_door!r} door")
    print(f"  the two added together   {object_block + item_block:4}")
    print(f"  sys.getsizeof says       {sys.getsizeof(numbers):4}")


print(with_the_fences(two_blocks, run_at, block_at))
""")


lesson.md(f"""
{figure("one-object-two-blocks", "a list block through the obj door pointing at an item array block through the mem door")}

The list object is a fixed size no matter how long the list is. It holds a pointer to a separate array, and that array is the thing that grows. The object went through the obj door and the array went through the mem door, which is the rule: objects use obj, the buffers inside them use mem.

The two block sizes add up to exactly what `sys.getsizeof` reports, which is the whole of what that function does for a list. It asks the object how big it is and the object counts both of its blocks. The allocator's own record only ever knows about one block at a time, which is why the two numbers disagreed in the table above.
""")


lesson.md(f"""
## Getting it wrong on purpose

The door byte is not decoration. Every free checks it, and if it does not match the door being used it stops the process rather than carrying on {cite("Objects/obmalloc.c:3343-3351@v3.15.0rc1")}.

This is worth seeing once, because the error message is unusually helpful for a crash.

{lesson.claim("Freeing a block through a different door than it was allocated from is a fatal error naming both doors")}
""")


lesson.code("""
def wrong_door():
    at = allocator("PyObject_Malloc")(400)
    print("  got a block from the obj door, handing it back through the mem door")
    allocator("PyMem_Free")(at)
    print("  nobody minded")


print(with_the_fences(wrong_door, allocator))
""")


lesson.md(f"""
Read the last line: allocated using API `o`, verified using API `m`. It even dumps the block first, so you can see the size, the fences and the first bytes of whatever was in there.

The fences get checked at the same moment {cite("Objects/obmalloc.c:3364-3371@v3.15.0rc1")}, which catches the more common mistake of writing one byte too many.

{lesson.claim("Writing one byte past the end of a block is caught, and the report says which byte and how far past")}
""")


lesson.code("""
def one_byte_too_many():
    import ctypes

    at = allocator("PyObject_Malloc")(8)
    print("  asked for 8 bytes, about to write 9")
    for i in range(9):
        ctypes.c_ubyte.from_address(at + i).value = 65
    allocator("PyObject_Free")(at)
    print("  nobody minded")


print(with_the_fences(one_byte_too_many, allocator))
""")


lesson.md("""
`at tail+0: 0x41 *** OUCH`. The first fence byte behind the block is now the letter A, and the check that reads it says so by name.

Nothing here needed a C compiler, a debugger or a sanitizer. It is one environment variable and sixteen extra bytes per allocation.
""")


lesson.md(f"""
## Where the object door stops

The obj door does not serve every request itself. There is a cut off, and it is 512 bytes {cite("Include/internal/pycore_obmalloc.h:153-164@v3.15.0rc1#SMALL_REQUEST_THRESHOLD")}. The comment above the number explains the choice: 512 is the smallest value that keeps a newly created dictionary on the fast side.

Above the cut off, the function tries its own allocator, gets nothing back, and passes the request to the raw door {cite("Objects/obmalloc.c:2540-2554@v3.15.0rc1#_PyObject_Malloc")}.

{figure("where-the-object-door-stops", "under 512 bytes served from a pool, over 512 passed to the system")}

You can see the line from Python without reading any of that. Small requests are served out of large chunks CPython buys from the operating system, and `sys._debugmallocstats` counts those chunks. Ask for twenty thousand blocks just under the line and the count climbs. Ask for twenty thousand just over it and the count does not move at all.

{lesson.claim("Twenty thousand blocks of 496 bytes costs several new arenas and twenty thousand of 528 bytes costs none")}
""")


lesson.code(
    """
import ctypes
import tempfile

HOW_MANY = 20000


def call(name, taking):
    fn = getattr(ctypes.pythonapi, name)
    fn.restype = ctypes.c_void_p if taking else None
    fn.argtypes = [ctypes.c_size_t if taking else ctypes.c_void_p]
    return fn


def arenas():
    saved = os.dup(2)
    with tempfile.TemporaryFile() as sink:
        os.dup2(sink.fileno(), 2)
        sys._debugmallocstats()
        os.dup2(saved, 2)
        os.close(saved)
        sink.seek(0)
        for line in sink.read().decode().splitlines():
            if "arenas allocated current" in line:
                return int(line.split()[-1])
    return -1


kept = (ctypes.c_void_p * (2 * HOW_MANY))()
grab = call("PyObject_Malloc", True)
drop = call("PyObject_Free", False)

start = arenas()
if start < 0:
    print("  this build does not report arena counts, so there is nothing to compare here")
else:
    for i in range(HOW_MANY):
        kept[i] = grab(496)
    small = arenas()
    for i in range(HOW_MANY):
        kept[HOW_MANY + i] = grab(528)
    large = arenas()
    for at in kept:
        drop(at)
    print(f"  arenas before anything            {start}")
    print(f"  after {HOW_MANY} blocks of 496 bytes  {small:5}, {small - start} more")
    print(f"  after {HOW_MANY} more of 528 bytes   {large:5}, {large - small} more")
""",
    varies="How many arenas the 496 byte blocks cost depends on how full the arenas already "
    "were when you ran the cell, so nine and ten are both normal. The second number is the one "
    "to read, and it should be zero.",
)


lesson.md(f"""
Nine or ten new chunks for the small blocks. None at all for the large ones, because those never touched CPython's allocator on the way through.

## The bottom layer comes out

The three doors are an interface, and what sits underneath them is a choice made at startup. `PYTHONMALLOC` names the choice, and the names come from a second enum next to the first one {cite("Include/cpython/pymem.h:16-30@v3.15.0rc1#PyMemAllocatorName")}.

The next cell starts a fresh interpreter for four of them and asks two questions: how many blocks CPython's own allocator is holding, and how many chunks it has taken from the operating system.

{lesson.claim("Starting Python with PYTHONMALLOC=malloc removes CPython's small object allocator entirely, and sys.getallocatedblocks then reports zero")}
""")


lesson.code(
    """
LOOK = chr(10).join(
    [
        "import os, sys, tempfile",
        "saved = os.dup(2)",
        "sink = tempfile.TemporaryFile()",
        "os.dup2(sink.fileno(), 2)",
        "sys._debugmallocstats()",
        "os.dup2(saved, 2)",
        "sink.seek(0)",
        "said = sink.read().decode().splitlines()",
        "found = [one for one in said if 'arenas allocated current' in one]",
        "print(sys.getallocatedblocks(), found[0].split()[-1] if found else 'none at all')",
    ]
)


def under(value):
    try:
        done = subprocess.run(
            [sys.executable, "-c", LOOK],
            capture_output=True,
            text=True,
            env=dict(os.environ, PYTHONMALLOC=value),
            timeout=300,
        )
    except OSError:
        return ""
    said = (done.stdout or done.stderr).strip().splitlines()
    return said[-1] if said else "it would not start"


rows = [(value, under(value)) for value in ("default", "pymalloc", "malloc", "mimalloc")]
if not any(said for _, said in rows):
    print("  this runtime cannot start a second interpreter, so try this on a real machine")
else:
    print("  PYTHONMALLOC   blocks held   arenas")
    for value, said in rows:
        blocks, _, chunks = said.partition(" ")
        print(f"  {value:12}   {blocks:>11}   {chunks}")
""",
    varies="The block counts are how much of the standard library your interpreter happened to "
    "import at startup, so they move between machines and between versions. The rows that "
    "matter are malloc, which is zero, and the arenas column.",
)


lesson.md(f"""
{figure("the-bottom-layer-comes-out", "the same three doors over four different allocators underneath")}

Under `malloc` the count is zero and there are no chunks, because there is nothing left to count: every request goes straight to the system allocator. Under `mimalloc` there are blocks but no chunks, because that is a different allocator with a different idea of how to group things.

Nothing above the doors changed in any of those runs. Your objects are in the same places, `id()` still works, and `sys.getsizeof` gives the same answers. That is what having the layer buys.

{term("PYTHONMALLOC")} is also how the two sanitizer builds are usually run, since a tool like Valgrind wants to see every `malloc` rather than one big chunk being carved up out of sight.
""")


lesson.md("""
## Try it yourself

Three things worth ten minutes each.

Change the sizes in the arena cell. The line is at 512 and both sides of it are visible: try 504 and 520, and then try 8 and 4096. The interesting question is whether the number of chunks tracks the number of bytes or the number of blocks.

Read the bytes of a string you have already thrown away. Make a string, note its `id()`, delete it, then read that address with `run_at`. Under the debug hooks you should find `dd`. Do it without the hooks and you will find whatever moved in afterwards, which is the reason the hooks exist.

Break the front fence rather than the back one. The `one_byte_too_many` cell writes past the end. Write before the start instead, at `at - 1`, and see which of the two checks catches it and what it says. The order the two checks run in is deliberate and the comment above them says why.
""")


lesson.md("""
## What you now know

Memory in CPython has three entrances and they are not interchangeable. Raw is for work happening outside an interpreter and it has to be safe to call without any lock held. Mem is for buffers that belong to an object. Obj is for the objects themselves.

Which entrance a block came through is written in the block, one byte in front of your pointer, whenever the debug hooks are on. Every free reads that byte back and stops the process if it disagrees, which is how a bug that would otherwise corrupt the heap quietly becomes a message naming both doors.

The same hooks put fence bytes at both ends and fill fresh and dead memory with values chosen to be conspicuous. `cd` means nobody has written here. `dd` means this was handed back. `fd` means you have gone past the end.

A list is two blocks and not one. The object went through the obj door, its array of items went through the mem door, and `sys.getsizeof` adds them up while the allocator's own record does not.

Requests over 512 bytes are not served by CPython's allocator at all. They are handed to the layer below, which is why they never cost a chunk of address space and why the cut off is worth knowing before you tune anything.

And the whole bottom layer is swappable at startup with one environment variable, without a single thing above it noticing.

## What is next

M02 goes down one level, into the part this lesson kept calling a chunk. Arenas, pools and blocks, the size classes that 512 divides into, and why a process that allocated a lot of memory does not always give it back.
""")


raise SystemExit(lesson.save())
