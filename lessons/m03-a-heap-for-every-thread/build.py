#!/usr/bin/env python
"""M03. A heap for every thread.

The third lesson of the memory part. M02 took CPython's own allocator apart and found arenas,
pools, blocks and a 48 byte header. This lesson points out that there is a second allocator
sitting right next to it, already compiled into the interpreter you are running, and that one
environment variable is enough to make every measurement in M02 come out differently.

The spine is a single design choice. obmalloc keeps the record of what a pool holds inside the
pool. mimalloc keeps it in the segment header instead. Everything else follows: whether a block
can start on its own size boundary, how big a page can be, and whether a page can belong to one
thread with nobody else reading it. That last one is why the free threaded build has no choice
about which allocator it uses.

Like M01 this lesson shells out, because the allocator is chosen once at startup and cannot be
changed afterwards. A browser build cannot start a second interpreter, so those cells say so
rather than printing nothing.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("m03-a-heap-for-every-thread", "m03")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("m03-a-heap-for-every-thread").figure


lesson.md(f"""
# M03. A heap for every thread

{badge}

Your Python has two small object allocators compiled into it. You have been using one of them.

M02 measured the first one down to the byte. This lesson sets one environment variable, runs the same measurements again, and gets different answers to every single one.

{figure("two-reports", "the same report printed by obmalloc and by mimalloc, side by side")}

The second allocator is `mimalloc`, and it is not an experiment or a build option somebody forgot to remove. It is what the free threaded build uses for everything, because the design in M02 cannot be made to work well when many threads allocate at once.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Objects/obmalloc.c:781-796@v3.15.0rc1`.

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

The allocator is picked once, before the interpreter finishes starting, and nothing can change it afterwards. So like M01, most cells here start a small child interpreter with a different setting and read what it prints. A browser cannot start a child process at all, so those cells will say so and tell you to try them on a real machine. That is most of this lesson, so it is one to run locally or in Colab rather than in a browser tab.

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
## Both of them are already in there

Two build settings decide what your interpreter contains. `WITH_PYMALLOC` puts in the allocator from M02, and `WITH_MIMALLOC` puts in the other one. On an ordinary build both are on, and `PYTHONMALLOC` picks between them at startup {cite("Objects/obmalloc.c:781-796@v3.15.0rc1#PYMEM_ALLOCATOR_MIMALLOC")}.

Look at the `#if` lines around that code and you can read the whole policy off them. `pymalloc` is only offered when free threading is off. `mimalloc` is offered whenever it was compiled in, with no such condition. That is the free threaded build having no choice, written out in two preprocessor directives.

{lesson.claim("An ordinary CPython build contains both allocators, and the free threaded build contains only mimalloc")}
""")


lesson.code(
    """
import sysconfig


def setting(name):
    value = sysconfig.get_config_var(name)
    return value not in (None, "", 0, "0")


for name in ("WITH_PYMALLOC", "WITH_MIMALLOC", "Py_GIL_DISABLED"):
    print(f"  {name:18} {'yes' if setting(name) else 'no'}")

print()
print("  so on this interpreter you can ask for:")
for name in ("malloc", "pymalloc", "mimalloc"):
    have = name == "malloc" or setting(f"WITH_{name.upper()}")
    print(f"    PYTHONMALLOC={name:10} {'yes' if have else 'no, not compiled in'}")
""",
    varies="A free threaded build says yes to Py_GIL_DISABLED and no to WITH_PYMALLOC, because "
    "obmalloc is compiled out of it entirely. A browser build also says no to WITH_PYMALLOC, for "
    "an unrelated reason: it leaves the small object allocator out and uses the one the runtime "
    "already provides.",
)


lesson.md(f"""
On a normal desktop build, both. You have simply never asked for the second one.

## The same report, a different shape

M02 spent a whole lesson on what `sys._debugmallocstats` prints. Run it under the other allocator and it is a different function printing different lines {cite("Objects/obmalloc.c:3667-3687@v3.15.0rc1#py_mimalloc_print_stats")}.

The two numbers in its first line come straight from mimalloc's own constants {cite("Include/internal/mimalloc/mimalloc/types.h:225-232@v3.15.0rc1#MI_BIN_HUGE")}. Compare them against 512 and 32 from M02.

{lesson.claim("mimalloc serves requests up to 16384 bytes across 73 size classes, against 512 bytes across 32")}
""")


lesson.code(
    """
import inspect
import os
import subprocess

CANNOT = "    this runtime cannot start a second interpreter, so try this on a real machine"


def under(value, body, *also):
    try:
        shipped = "".join(inspect.getsource(one) + chr(10) for one in also)
        script = shipped + inspect.getsource(body) + f"{chr(10)}{body.__name__}(){chr(10)}"
        done = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env=dict(os.environ, PYTHONMALLOC=value),
            timeout=300,
        )
    except OSError:
        return ""
    return (done.stdout + done.stderr).rstrip()


def headlines():
    import os
    import sys
    import tempfile

    worth = ("threshold", "Large object", "Allocated Blocks", "Bytes Reserved", "bytes/arena")
    saved = os.dup(2)
    with tempfile.TemporaryFile() as sink:
        os.dup2(sink.fileno(), 2)
        sys._debugmallocstats()
        os.dup2(saved, 2)
        os.close(saved)
        sink.seek(0)
        report = sink.read().decode()

    for line in report.splitlines():
        if any(one in line for one in worth):
            print("   ", " ".join(line.split()))


for value in ("pymalloc", "mimalloc"):
    print(f"  PYTHONMALLOC={value}")
    print(under(value, headlines) or CANNOT)
""",
    varies="The arena count and the allocated block count depend on what the child interpreter "
    "had imported by the time it printed, so those move. The thresholds and the class counts do "
    "not move at all.",
)


lesson.md(f"""
Thirty two times the threshold and more than twice the classes. The classes are not evenly spaced either: mimalloc grows them by about an eighth at a time rather than sixteen bytes at a time, which is how 73 of them cover a range that would need a thousand under M02's rule.

Underneath, mimalloc's two boxes are much bigger than M02's {cite("Include/internal/mimalloc/mimalloc/types.h:203-211@v3.15.0rc1#MI_SEGMENT_SHIFT")}. A segment is 32 MiB where an arena was 1 MiB, and a small page inside it is 64 KiB where a pool was 16 KiB.

You do not have to take that on trust. Segments are aligned to their own size, so rounding a block address down to a multiple of 32 MiB gives you the segment it is in, and rounding down to 64 KiB gives you the page.

{lesson.claim("Four thousand blocks of any small size land in a single 32 MiB segment, spread over as many 64 KiB pages as they need")}
""")


lesson.code(
    """
def count_the_regions():
    import ctypes

    grab = ctypes.pythonapi.PyObject_Malloc
    grab.restype = ctypes.c_void_p
    grab.argtypes = [ctypes.c_size_t]
    drop = ctypes.pythonapi.PyObject_Free
    drop.restype = None
    drop.argtypes = [ctypes.c_void_p]

    for asked in (16, 64, 256, 512):
        kept = (ctypes.c_void_p * 4000)()
        for i in range(4000):
            kept[i] = grab(asked)
        at = [int(one) for one in kept]
        segments = len({one >> 25 for one in at})
        pages = len({one >> 16 for one in at})
        for one in kept:
            drop(one)
        print(f"     4000 blocks of {asked:4} bytes   {segments} segment   {pages:2} pages")


print("  PYTHONMALLOC=mimalloc")
print(under("mimalloc", count_the_regions) or CANNOT)
""",
    varies="How many pages the blocks spread over depends on which pages were already part "
    "filled, so those counts move a little. One segment for all of them is the part that holds.",
)


lesson.md(f"""
One segment each time. Sixteen byte blocks fit four thousand into a single page, and 512 byte blocks need about thirty three of them.

## The same measurement, the opposite answer

Here is the difference that matters, and it takes one line to test.

M02 established that a block never starts at the top of its pool, because the first 48 bytes are the pool header. So a 256 byte block sits at 48, or 304, or 560, and none of those is a multiple of 256. Under obmalloc a block is never aligned to its own size, and that is not a near miss, it is never.

mimalloc puts the record of what a page holds in the segment header instead, so the page itself is nothing but blocks, and the first one starts at the page boundary.

{figure("where-the-bookkeeping-goes", "where each allocator keeps its per page record and what follows from that")}

{lesson.claim("Under obmalloc no block address is a multiple of its own size, and under mimalloc every one is")}
""")


lesson.code(
    """
def where_the_blocks_land():
    import ctypes

    grab = ctypes.pythonapi.PyObject_Malloc
    grab.restype = ctypes.c_void_p
    grab.argtypes = [ctypes.c_size_t]
    drop = ctypes.pythonapi.PyObject_Free
    drop.restype = None
    drop.argtypes = [ctypes.c_void_p]

    for asked in (64, 128, 256, 512):
        kept = (ctypes.c_void_p * 400)()
        for i in range(400):
            kept[i] = grab(asked)
        at = [int(one) for one in kept]
        lined = sum(1 for one in at if one % asked == 0)
        for one in kept:
            drop(one)
        print(f"     {asked:5} byte blocks   {lined:3} of 400 start on a {asked} byte boundary")


for value in ("pymalloc", "mimalloc"):
    print(f"  PYTHONMALLOC={value}")
    print(under(value, where_the_blocks_land) or CANNOT)
""",
    varies="This one does not move. Zero of four hundred under one allocator and four hundred of "
    "four hundred under the other, on every machine that can run it.",
)


lesson.md("""
Zero and four hundred. Not a tendency, a rule, and it comes from the single sentence about where the record lives.

It is worth sitting with why that matters, because it is not really about alignment. If the record of what a page holds is inside the page, then anything touching a block has a reason to touch that shared record, and shared means locked. If the record is somewhere else, a whole page can be handed to one thread and that thread can allocate and free inside it without any other thread reading a single byte of it. Fast allocation for many threads is the goal, and keeping the bookkeeping out of the page is the move that gets you there.

That is also why obmalloc is not simply patched to work under free threading. The 48 bytes at the front of every pool are the problem, and they are the whole design.

## The fences do not care

One thing does not change, and it is the thing M01 built.
""")


lesson.md(f"""
The debug hooks are a layer above whichever allocator you picked. They add the size and the domain letter in front of your block and the fences behind it, then call down. Swap what is underneath and they carry on exactly as before.

{figure("the-fences-sit-on-top", "the debug hooks, the chosen allocator and the operating system as three layers")}

CPython goes further than just leaving them alone. It compiles mimalloc with mimalloc's own debug byte values redefined to CPython's {cite("Include/internal/pycore_mimalloc.h:22-33@v3.15.0rc1#MI_DEBUG_UNINIT")}, so even the filler bytes underneath match what M01 taught you to read.

{lesson.claim("The block header and fences from M01 read the same under mimalloc_debug as under pymalloc_debug")}
""")


lesson.code(
    """
def read_the_door():
    import ctypes

    def call(name, taking):
        fn = getattr(ctypes.pythonapi, name)
        fn.restype = ctypes.c_void_p if taking else None
        fn.argtypes = [ctypes.c_size_t if taking else ctypes.c_void_p]
        return fn

    def run_at(at, count):
        return bytes(ctypes.c_ubyte.from_address(at + i).value for i in range(count))

    step = ctypes.sizeof(ctypes.c_size_t)
    for name in ("PyMem_RawMalloc", "PyMem_Malloc", "PyObject_Malloc"):
        at = call(name, True)(400)
        asked = int.from_bytes(run_at(at - 2 * step, step), "big")
        door = chr(ctypes.c_ubyte.from_address(at - step).value)
        fence = run_at(at - step + 1, step - 1).hex()
        fresh = run_at(at + 200, 8).hex()
        call(name.replace("Malloc", "Free"), False)(at)
        print(f"     {name:16} door {door!r}  asked {asked}  fence {fence}  fresh {fresh}")


for value in ("pymalloc_debug", "mimalloc_debug"):
    print(f"  PYTHONMALLOC={value}")
    print(under(value, read_the_door) or CANNOT)
""",
    varies="Six identical lines on any machine that can run this. If yours differ, the most "
    "likely reason is a 32 bit build, where the header words are four bytes rather than eight.",
)


lesson.md(f"""
Same three doors, same size, same fence bytes, same filler. The layer you learned to read in M01 sits above the layer this lesson is about, which is exactly why it was worth learning first.

One warning if you go experimenting. Do not run the alignment test under `mimalloc_debug`. The debug hooks shift your pointer sixteen bytes past the start of the real block, so nothing is aligned to anything and the result looks like a contradiction. Alignment is a fact about the allocator underneath, so measure it without the hooks in the way.

## Four heaps, not one

Everything so far runs on an ordinary build. The rest of the lesson is about what the free threaded build does with this allocator, and it cannot be measured here, because the interpreter running this notebook has the lock.

Each thread gets its own set of heaps, and there are four of them rather than one {cite("Include/internal/pycore_mimalloc.h:12-18@v3.15.0rc1#_Py_mimalloc_heap_id")}.

{figure("four-heaps-per-thread", "the four mimalloc heaps each thread gets and what each one holds")}

{lesson.claim("A free threaded build gives every thread four mimalloc heaps, split by what the cycle collector needs to do with the objects in them", unobservable="The struct holding them only exists under Py_GIL_DISABLED, and this notebook is not running such a build. You can read the fields at Include/internal/pycore_mimalloc.h:53-67 and see the array of four heaps and the thread local page list.")}

The split is not about speed. Look at the names: `mem` for plain buffers, `object` for objects the collector never has to visit, and then two for collected objects, separated by whether the object carries a {term("GC pre header")}. The allocator is being asked to keep the collector's work sorted into piles in advance.
""")


lesson.md(f"""
## How the collector finds everything

That last point is the one worth the walk down here, because it changes something you might have assumed was fundamental.

With the lock in place, every object the {term("cycle collector")} watches is on a doubly linked list, and every such object pays two pointers for the privilege. Collecting means walking the list. The free threaded build does not have that list. It asks each thread's heap to walk itself instead {cite("Python/gc_free_threading.c:381-399@v3.15.0rc1#mi_heap_visit_blocks")}.

{figure("how-the-collector-finds-things", "walking a linked list against walking the heap itself")}

{lesson.claim("The free threaded cycle collector finds objects by walking the mimalloc heaps rather than a linked list, which is why its objects do not carry the two list pointers", unobservable="Both halves need a free threaded interpreter to observe. The visiting code is the function cited above, and the two heaps it visits per thread are the gc and gc_pre ones from the enum.")}

Read that function and the whole reason for the four way split falls out. It visits two heaps per thread, the collected ones, and it passes a different offset for each because objects with a pre header start two pointers later. It never has to look at the `mem` or `object` heaps at all. Sorting objects into the right heap when they are created is what makes finding them later a matter of walking a couple of heaps rather than checking every block in the process.

{figure("one-set-each", "one interpreter, two threads with four heaps each, and the shared pool for dead threads")}

The one shared thing in that picture is the pool at the bottom. A thread that exits may still be holding pages with live objects in them, so it leaves them where another thread can claim and reuse them {cite("Include/internal/pycore_mimalloc.h:53-67@v3.15.0rc1#_mimalloc_thread_state")}. Everything else is per thread, which is the entire point.
""")


lesson.md("""
## Try it yourself

Three things, and the first two take about a minute each.

Run your own program under both allocators and compare the memory it uses. `PYTHONMALLOC=pymalloc python yours.py` against `PYTHONMALLOC=mimalloc python yours.py`, with `sys._debugmallocstats()` at the end of each. A program holding a lot of medium sized objects, in the range between 512 and 16384 bytes, is where you should expect the biggest difference, because that whole range goes to the system allocator under one of them and is handled in house by the other.

Take the alignment cell and add 1024, 4096 and 16384 to the list of sizes. Then add 16385. The last one is past mimalloc's threshold and behaves differently from all the others, which tells you where its own line is, the same way M01 found obmalloc's line at 512.

If you have a free threaded build, everything in the last two sections becomes measurable. Check what `sysconfig.get_config_var("WITH_PYMALLOC")` says there, then try `PYTHONMALLOC=pymalloc` and read the error. That is the two preprocessor directives from the first section, talking back to you.
""")


lesson.md("""
## What you now know

Your Python contains two small object allocators, not one. `PYTHONMALLOC` picks between them at startup, and `sysconfig` will tell you which ones your build has.

mimalloc serves requests up to 16384 bytes across 73 size classes, where the allocator in M02 stops at 512 bytes across 32. Its segments are 32 MiB and its small pages are 64 KiB, against 1 MiB arenas and 16 KiB pools.

The one design difference underneath all of that is where the per page record lives. obmalloc puts it at the front of the pool, which is why a block is never aligned to its own size. mimalloc puts it in the segment header, which is why every block is. Zero of four hundred against four hundred of four hundred, with the same measuring code.

That choice is also why one of them can be split per thread and the other cannot. Nothing shared inside a page means a page can belong to one thread with no lock anywhere near it, and that is what the free threaded build needs.

Each thread there gets four heaps rather than one, sorted by what the cycle collector has to do with the objects in them. That sorting is what lets the collector drop the linked list entirely and walk the heaps instead, which takes two pointers off every collected object.

The debug hooks from M01 sit above all of this and read exactly the same either way.

## What is next

M04 goes back to the object itself and the number that decides when any of this memory comes back. Reference counting is three lines of C that the interpreter runs more often than anything else it does, and most of the complexity in the free threaded build is about making those three lines safe.
""")


raise SystemExit(lesson.save())
