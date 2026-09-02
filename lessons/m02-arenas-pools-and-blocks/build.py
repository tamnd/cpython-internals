#!/usr/bin/env python
"""M02. Arenas, pools and blocks.

The second lesson of the memory part, and it goes one level down into the thing M01 kept
calling a chunk. An arena is a megabyte bought from the operating system, a pool is sixteen
kilobytes carved out of an arena, and a block is one of the identically sized slots a pool
is divided into.

The whole lesson comes out of one function nobody reads the output of. `sys._debugmallocstats`
prints a table of the 32 size classes and a summary underneath it, and every number in that
summary can be recomputed from the table plus two constants. Both constants can be worked out
from Python, one by arithmetic and one by looking at where addresses land, and the two routes
agree.

Unlike M01 there are no subprocesses here. Every cell runs in place. A browser build has the
small object allocator compiled out, so the table comes back empty there and the cells say so
rather than printing nonsense.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("m02-arenas-pools-and-blocks", "m02")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("m02-arenas-pools-and-blocks").figure


lesson.md(f"""
# M02. Arenas, pools and blocks

{badge}

M01 kept saying chunk. This lesson opens the chunk.

CPython buys memory from the operating system a megabyte at a time and then hands it out sixteen bytes at a time, and there are two layers of structure in between. Three boxes inside each other, and that is the whole design.

{figure("three-boxes", "an arena containing pools containing blocks, drawn as nested boxes")}

None of that is hidden. There is a function in `sys` that prints the current state of all three, and once you know how to read it you can derive every number in this picture without opening a single C file.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Objects/obmalloc.c:3781-3796@v3.15.0rc1`.

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

Every cell here runs in place, with no second interpreter and no environment variable, which makes this a friendlier lesson than M01 was. A browser is the one exception, and not because of anything the cells do. A browser build of Python has this allocator compiled out entirely and uses the one the runtime provides, so there is no table for it to print. The cells check for that and say so.

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
## The table nobody reads

`sys._debugmallocstats` writes a report about {term("obmalloc")} straight to standard error. Not to `sys.stderr`, which Python can redirect, but to the operating system's error stream, so capturing it takes a moment of setup and then it is an ordinary string.

The report opens with one row per {term("size class")} that currently has memory in it, and it is printed by a loop of about fifteen lines {cite("Objects/obmalloc.c:3781-3796@v3.15.0rc1#INDEX2SIZE")}.

{lesson.claim("sys._debugmallocstats prints one row per size class in use, and there are never more than 32 of them")}
""")


lesson.code(
    """
import os
import tempfile


def stats():
    saved = os.dup(2)
    with tempfile.TemporaryFile() as sink:
        os.dup2(sink.fileno(), 2)
        sys._debugmallocstats()
        os.dup2(saved, 2)
        os.close(saved)
        sink.seek(0)
        return sink.read().decode()


def classes(text):
    rows = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 5 and all(one.isdigit() for one in parts):
            rows.append(tuple(int(one) for one in parts))
    return rows


def total(text, label):
    for line in text.splitlines():
        if label in line:
            return int(line.split()[-1].replace(",", ""))
    return -1


def after_the_star(text, label):
    for line in text.splitlines():
        if label in line:
            return int(line.split("*")[1].split()[0])
    return 0


report = stats()
rows = classes(report)
HAS_POOLS = len(rows) > 0

if not HAS_POOLS:
    print("  this build has no small object allocator, so it has no table to print")
else:
    print(f"  {len(rows)} size classes have memory in them right now")
    print("  class  size   pools   in use   free")
    for index, size, pools, inuse, free in rows[:8]:
        print(f"  {index:5}  {size:4}  {pools:6}  {inuse:7}  {free:5}")
    print("  ... and so on to class 31")
""",
    varies="How many classes are in use and how full each one is depends on what your "
    "interpreter has imported, so the numbers move between machines and between runs. The "
    "shape is the part to read: 32 classes at most, sixteen bytes apart.",
)


lesson.md(f"""
Five columns. The class number, the size of a block in that class, how many {term("pool")}s are holding blocks of that size, how many of those blocks are in use, and how many are sitting free.

The sizes go 16, 32, 48 and so on. That is not a coincidence and it is not tuning: every request is rounded up to the next multiple of sixteen, and the class number is that multiple minus one {cite("Include/internal/pycore_obmalloc.h:137-146@v3.15.0rc1#INDEX2SIZE")}. Thirty two classes covers 16 through 512, and 512 is where this allocator stops, which is the line M01 found by counting.

{figure("rounded-up-to-a-class", "requests of 1, 17, 100, 512 and 513 bytes and the class each lands in")}

That is easy to state and easy to check. Ask for a couple of thousand blocks of some size, watch which row of the table moves, and you have the answer.

{lesson.claim("A request is served from the class holding the next multiple of sixteen up, and a request over 512 bytes moves no row of the table at all")}
""")


lesson.code(
    """
import ctypes


def call(name, taking):
    fn = getattr(ctypes.pythonapi, name)
    fn.restype = ctypes.c_void_p if taking else None
    fn.argtypes = [ctypes.c_size_t if taking else ctypes.c_void_p]
    return fn


grab = call("PyObject_Malloc", True)
drop = call("PyObject_Free", False)
HOW_MANY = 2000

if not HAS_POOLS:
    print("  this build has no small object allocator, so nothing here has a row to move")
else:
    print("  you asked for   you got   which is class")
    for asked in (1, 8, 17, 100, 255, 512, 513):
        kept = (ctypes.c_void_p * HOW_MANY)()
        before = {size: inuse for _, size, _, inuse, _ in classes(stats())}
        for i in range(HOW_MANY):
            kept[i] = grab(asked)
        moved = [
            size
            for _, size, _, inuse, _ in classes(stats())
            if inuse - before.get(size, 0) >= HOW_MANY // 2
        ]
        for at in kept:
            drop(at)
        if moved:
            print(f"  {asked:13}  {moved[0]:7}  {moved[0] // 16 - 1:14}")
        else:
            print(f"  {asked:13}  {'the system':>7}  {'no class at all':>14}")
""",
    varies="This is one of the cells that is the same everywhere it can run at all. If a row "
    "comes out differently on your machine it means something else was allocating at the same "
    "moment, so run it again.",
)


lesson.md(f"""
Ask for one byte, get sixteen. Ask for seventeen, get thirty two. The fifteen bytes you did not ask for are not given to anyone else and are not tracked; they are just part of your block until you free it.

Ask for 513 and nothing moves, because that request never reached this allocator. It went to the layer below, exactly as M01 showed.

## One pool, and how much fits in it

Now the second layer. A {term("pool")} is a fixed size run of blocks that are all in the same class, and it starts with a header describing itself.

{figure("inside-one-pool", "a pool with its 48 byte header, its blocks and the unusable space at the end")}

Here is the nice part. You do not have to be told how big a pool is or how big its header is. The table already tells you, twice over, if you do a little arithmetic.

The pool size is printed further down the report. The header size is not printed anywhere, but the blocks in each class have to fit in whole pools, so `pools * ((pool size - header) // block size)` has to equal the blocks in that row. Guess the header wrong and that fails on most rows. Guess it right and it holds for every row at once.

{lesson.claim("One header size explains the block count of every size class in the table, and no other candidate explains more than a few")}
""")


lesson.code(
    """
POOL = after_the_star(report, "unused pools *")
ARENA = after_the_star(report, "bytes/arena")

if not HAS_POOLS:
    print("  this build has no small object allocator, so there is no table to check")
else:
    print(f"  a pool is {POOL} bytes and an arena is {ARENA}, so an arena holds {ARENA // POOL}")
    print()
    print("  if the header were   rows of the table it would explain")
    scores = []
    for guess in (0, 8, 16, 32, 48, 64, 128):
        fits = sum(
            1
            for _, size, pools, inuse, free in rows
            if pools * ((POOL - guess) // size) == inuse + free
        )
        scores.append((fits, guess))
        mark = "   <- every one of them" if fits == len(rows) else ""
        print(f"  {guess:18}   {fits} of {len(rows)}{mark}")
    HEADER = max(scores)[1]
""",
    varies="The pool and arena sizes come from your build. A 32 bit build uses smaller ones, "
    "and so does a build without the radix tree. Whatever they are, exactly one header size "
    "should explain every row.",
)


lesson.md(f"""
Forty eight bytes, and nothing else comes close.

That number is not arbitrary either. The {term("pool header")} is a struct with eight fields in it {cite("Include/internal/pycore_obmalloc.h:263-274@v3.15.0rc1#pool_header")}: how many blocks are in use, where the free list starts, the two pointers linking this pool to the others in its class, which arena it belongs to, which class it serves, and two offsets tracking how much of the pool has been carved up so far. Four pointers and four small integers is forty eight bytes on a 64 bit machine, and the header size is that rounded up to the alignment {cite("Include/internal/pycore_obmalloc.h:319-327@v3.15.0rc1#NUMBLOCKS")}.

The consequence is the bar chart.

{figure("how-many-fit-in-a-pool", "blocks per pool for six size classes, from 1021 down to 31")}

A pool of sixteen byte blocks holds 1021 of them, not 1024. The header ate three.

## The same number, from the addresses

That was arithmetic. Here is the same answer from a completely different direction, and it is worth doing because two independent routes agreeing is what makes a fact rather than a story.

Every block lives inside a pool, and pools are aligned, which means you can find the start of a block's pool by rounding its address down. Take the address of a block, subtract the start of its pool, and you have the offset of that block inside its pool. If the header really is 48 bytes and the blocks really are packed end to end, every one of those offsets has to be 48 plus a multiple of the block size.

{lesson.claim("Every block address is 48 bytes plus a whole number of blocks from the start of its pool, and the highest one is exactly where the arithmetic says the last block goes")}
""")


lesson.code(
    """
SIZE = 64
HOW_MANY = 4000

if not HAS_POOLS:
    print("  this build has no small object allocator, so its blocks are not in pools at all")
else:
    kept = (ctypes.c_void_p * HOW_MANY)()
    for i in range(HOW_MANY):
        kept[i] = grab(SIZE)
    at = [int(one) for one in kept]
    for one in kept:
        drop(one)

    inside = sorted(one % POOL for one in at)
    pools = len({one - one % POOL for one in at})
    lined = sum(1 for one in inside if (one - HEADER) % SIZE == 0)
    room = (POOL - HEADER) // SIZE
    last = HEADER + (room - 1) * SIZE

    print(f"  {HOW_MANY} blocks of {SIZE} bytes landed in {pools} pools")
    print(f"  offsets that are {HEADER} plus a multiple of {SIZE}   {lined} of {HOW_MANY}")
    print(f"  the lowest offset seen                    {inside[0]}")
    print(f"  the highest offset seen                   {inside[-1]}")
    print(f"  room for {room} blocks, so the last starts at {last}")
""",
    varies="How many pools the blocks spread over depends on how many part filled pools of this "
    "class were already lying around, so that number moves. The three lines under it do not.",
)


lesson.md("""
Four thousand out of four thousand, the lowest offset is 48, and the highest is exactly where the last block of a full pool would start. The arithmetic and the addresses tell the same story.

## Every total adds up

Under the table the report prints a summary, and every line of it is one sum over the table you have already read.

Bytes in allocated blocks is blocks in use times the block size. Bytes in available blocks is the same for the free ones. Bytes lost to pool headers is pools times forty eight. Bytes lost to quantization is the bit at the end of each pool too small for one more block, which is `(pool size - header) % block size`, once per pool.
""")


lesson.md(f"""
That last one is the only line here that needs explaining. A pool of 240 byte blocks fits 68 of them into its 16336 usable bytes and has 16 bytes left over, and those 16 bytes can never hold anything, because a pool only ever serves one size. The report adds up all of that dead space and calls it quantization {cite("Objects/obmalloc.c:3816-3827@v3.15.0rc1#quantization")}.

{lesson.claim("Every byte total in the summary can be recomputed from the table above it using nothing but the pool size and the header size")}
""")


lesson.code(
    """
if not HAS_POOLS:
    print("  this build has no small object allocator, so it prints no totals to check")
else:
    report = stats()
    rows = classes(report)
    mine = [
        ("bytes in allocated blocks", sum(inuse * size for _, size, _, inuse, _ in rows)),
        ("bytes in available blocks", sum(free * size for _, size, _, _, free in rows)),
        ("bytes lost to pool headers", sum(pools * HEADER for _, _, pools, _, _ in rows)),
        (
            "bytes lost to quantization",
            sum(pools * ((POOL - HEADER) % size) for _, size, pools, _, _ in rows),
        ),
    ]
    print("  the line it prints            it printed    we computed   same")
    for label, ours in mine:
        theirs = total(report, label)
        print(f"  {label:26}  {theirs:11}  {ours:13}   {'yes' if ours == theirs else 'no'}")

    busy = sum(pools for _, _, pools, _, _ in rows)
    idle = total(report, "unused pools *") // POOL
    have = total(report, "arenas allocated current")
    print()
    print(f"  {busy} pools in use plus {idle} unused makes {busy + idle}")
    print(f"  {have} arenas times {ARENA // POOL} pools each makes {have * (ARENA // POOL)}")
""",
    varies="Every number here depends on what your interpreter has allocated, and it will "
    "change if you run the cell twice. The two columns agreeing is the point, not the values.",
)


lesson.md(f"""
{figure("every-total-adds-up", "each printed total and the sum over the table that produces it")}

Four sums and two constants, and the last two lines close the loop: the pools in use plus the pools sitting idle is exactly the arenas times sixty four {cite("Include/internal/pycore_obmalloc.h:249-252@v3.15.0rc1#MAX_POOLS_IN_ARENA")}. Nothing is unaccounted for. There is no slack anywhere in this design, which is why the report can assert its own total and mean it.

## Why the memory does not come back

Now the part people actually run into.

An {term("arena")} is the level at which memory is given back to the operating system, and there is exactly one condition for giving one back: every pool in it has to be free {cite("Objects/obmalloc.c:2626-2643@v3.15.0rc1#ntotalpools")}. Not most of them. All of them.

Since your objects do not get to choose which arena they land in, a program that allocates a lot and then frees most of it can easily end up with one live block in every arena and nothing to give back.

{lesson.claim("Freeing all but one block in every two hundred returns no arenas at all, and freeing that last one per two hundred returns nearly all of them")}
""")


lesson.code(
    """
HOW_MANY = 200000
EVERY = 200

if not HAS_POOLS:
    print("  this build has no small object allocator, so it has no arenas to give back")
else:
    kept = (ctypes.c_void_p * HOW_MANY)()
    start = total(stats(), "arenas allocated current")
    for i in range(HOW_MANY):
        kept[i] = grab(64)
    peak = total(stats(), "arenas allocated current")

    for i in range(HOW_MANY):
        if i % EVERY:
            drop(kept[i])
            kept[i] = None
    alive = sum(1 for one in kept if one)
    thin = total(stats(), "arenas allocated current")

    for one in kept:
        if one:
            drop(one)
    done = stats()
    end = total(done, "arenas allocated current")

    lines = [
        ("arenas to start with", start),
        (f"after {HOW_MANY} blocks of 64 bytes", peak),
        (f"after freeing all but {alive} of those", thin),
        (f"after freeing that last {alive} as well", end),
        ("arenas handed back over the whole run", total(done, "arenas reclaimed")),
    ]
    for label, value in lines:
        print(f"  {label:40}  {value:4}")
""",
    varies="The starting count is whatever your interpreter had already taken, so every number "
    "shifts with it. The shape is what matters: the third line equals the second one, and the "
    "fourth is close to the first.",
)


lesson.md(f"""
Read the third line against the second. Nearly two hundred thousand blocks were freed, one in every two hundred was kept, and not one arena came back. Roughly twelve megabytes of address space is being held by roughly sixty kilobytes of live data.

Then the last thousand blocks go and almost all of it comes back at once.

{figure("why-it-does-not-come-back", "an arena with every pool free against an arena with one live block")}

This is the mechanism behind an observation people make about long running Python processes: memory use goes up and stays up even after the objects are gone. Nothing is leaking. The blocks really are free and they really will be reused by the next objects of the same size. They are just spread thinly enough that no arena is empty.

The comment above the check adds one more wrinkle worth knowing: the last arena on the list is kept even when it is completely free, deliberately, so that a loop which allocates and frees the same thing does not buy and return an arena on every trip.
""")


lesson.md("""
## Try it yourself

Three things worth ten minutes each.

Change `EVERY` in the fragmentation cell. At 200 nothing comes back. Somewhere on the way down to 1 everything does. Finding roughly where the change happens tells you how many pools the surviving blocks were spread across, which is a more useful number than it sounds.

Run the size class cell with a size that is already an exact multiple of sixteen, then one byte more. 256 and 257, or 64 and 65. Watch the second one jump a whole class. This is why a struct that grew by one field can cost sixteen more bytes per instance, or nothing at all.

Print the whole report once and read the part below the arena counts. There is a section on the arena map, which is how the allocator answers the question of whether some arbitrary address belongs to it, and a list of the free lists that individual types keep for themselves. Neither is covered here. The free lists are the subject of a later lesson.
""")


lesson.md("""
## What you now know

CPython's own allocator has three levels. Arenas are bought from the operating system a megabyte at a time. Each arena is sixty four pools of sixteen kilobytes. Each pool serves exactly one block size and is divided into blocks of that size end to end.

There are 32 block sizes and they are sixteen bytes apart, from 16 up to 512. Every request is rounded up to one of them. The rounding is not refunded, and it is why two objects a few bytes apart in size can take exactly the same amount of memory.

A pool starts with a 48 byte header describing itself, which is why 1021 sixteen byte blocks fit in a 16384 byte pool rather than 1024. You can find that 48 two ways from Python: by testing candidate header sizes against every row of the size class table, and by looking at where block addresses land inside their pools. They agree.

Every byte total the allocator reports about itself is a sum over that same table, and the pools in use plus the pools idle is exactly the arena count times sixty four. Nothing is hidden and nothing is unaccounted for.

An arena goes back to the operating system only when every pool in it is free, so one surviving block can hold a megabyte. That is the whole explanation for a Python process whose memory use never comes down.

## What is next

M03 is about the other allocator. The free threaded build does not use any of this, because a design built around one shared set of pools is a poor fit for many threads allocating at once. It uses `mimalloc` instead, with per thread heaps, and the cycle collector has to be able to walk it.
""")


raise SystemExit(lesson.save())
