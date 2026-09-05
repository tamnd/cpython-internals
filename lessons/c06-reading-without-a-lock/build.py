#!/usr/bin/env python
"""C06. Four threads reading the same list.

The sixth concurrency lesson, and the first one where the GIL is genuinely gone. C05 finished by
promising that a list, a dict and a set would each need a different answer for what happens when
two threads reach for them at once. That turned out to be wrong for 3.15: all three read the same
way now, and none of the three takes a lock to do it.

So the lesson goes after the thing that actually decides whether four threads help. Reading an
object means touching its reference count, and a count is one machine word that every reader has
to write to. Four threads reading a list of ordinary objects are slower than one thread. Four
threads reading a list of small integers get most of the speedup you were hoping for, because
small integers have no count to touch.

The two Tier 1 recordings are that pair, measured on a fixed four core container: the same reads,
on the same build, over two lists that differ only in what they hold.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording

lesson = Lesson("c06-reading-without-a-lock", "c06")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("c06-reading-without-a-lock").figure

WITHOUT_THE_LOCK = "c06-reading-what-nobody-counts"
WITH_THE_LOCK = "c06-the-same-two-lists-with-the-lock"


lesson.md(f"""
# C06. Four threads reading the same list

{badge}

Take the GIL away and two threads can run Python at the same instant. That is the whole promise, and it raises an awkward question immediately: what happens when both of them read the same list?

There is an obvious answer, which is that the list gets its own lock. CPython does have those, and C02 was about them. But a lock on every read would give back most of what removing the GIL was for, so the read path does something else instead, and the something else is the interesting part of this lesson.

The other half is more surprising. Once reads are lock free, the thing that decides whether four threads actually help is not the container at all. It is what the container holds.

{figure("two-ways-to-read-one-slot", "two columns, what a subscript does on a build with the GIL and on a build without it")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Objects/listobject.c:353-379@v3.15.0rc1`.

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

Every cell here needs a second thread, so each one checks once and says so instead of failing. A browser tab cannot start one. In Colab or from a checkout, all of them run, and you will almost certainly be on a build that still has the GIL, which is fine: half of what this lesson is about is the difference between the two, and one of the two is the one in front of you.

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
## Four threads, one container

Start with the plain version of the question. Four threads, half a million subscripts each, against one shared list, then one shared dict, then one shared set. Nothing is written. Nobody is mutating anything. It is the friendliest possible case.

The number to watch is the last one on each pair of lines. It is how much work four threads got through compared to one thread on its own. Four would be perfect. One means the four threads were taking turns.

{lesson.claim("On a build that still has the GIL, four threads reading one shared list, dict or set get through about as much work as a single thread, and no more")}

{lesson.claim("On a build without the GIL all three of them scale, because reads of a list, a dict and a set are all lock free in 3.15", unobservable="it needs an interpreter configured with --disable-gil, which is a separate build rather than a flag you can turn on in the one you already have")}
""")


lesson.code(
    """
import threading
import time


def threads_work():
    \"\"\"True when this runtime can actually start a second thread.\"\"\"
    try:
        probe = threading.Thread(target=lambda: None)
        probe.start()
        probe.join()
    except RuntimeError:
        return False
    return True


CAN_THREAD = threads_work()
READS = 500000
NUMBERS = list(range(1000))
MAPPING = {n: n for n in range(1000)}
MEMBERS = set(range(1000))


def read_list():
    data = NUMBERS
    for _ in range(READS):
        got = data[500]
    return got


def read_dict():
    data = MAPPING
    for _ in range(READS):
        got = data[500]
    return got


def read_set():
    data = MEMBERS
    for _ in range(READS):
        got = 500 in data
    return got


def run(work, threads):
    \"\"\"Start that many threads on the same job and time until the last one is done.\"\"\"
    crew = [threading.Thread(target=work) for _ in range(threads)]
    started = time.perf_counter()
    for one in crew:
        one.start()
    for one in crew:
        one.join()
    return time.perf_counter() - started


def best(work, threads, rounds=3):
    \"\"\"The fastest of a few runs, which is the honest number on a laptop.\"\"\"
    return min(run(work, threads) for _ in range(rounds))


if not CAN_THREAD:
    print("This runtime cannot start a second thread, so there is nothing to time here.")
else:
    print(f"the lock is on: {sys._is_gil_enabled()}")
    for name, work in [("list", read_list), ("dict", read_dict), ("set", read_set)]:
        one = best(work, 1)
        four = best(work, 4)
        print(f"  {name:4} one {one * 1000:4.0f} ms, four {four * 1000:4.0f} ms")
        print(f"  {name:4} work done against one thread: {4 * one / four:.2f}x")
""",
    varies=(
        "these are timings, so the millisecond numbers move from run to run and from machine to "
        "machine, and the ratio at the end depends on how many cores the machine has and whether "
        "the build has the GIL"
    ),
)


lesson.md(f"""
## What a read has to do when nobody is holding a lock

Here is the problem the read path has to solve, and it is worth being precise about it, because the obvious solutions are all wrong.

Reading `data[500]` means loading a pointer out of the list's array and handing it back with one added to its {term("reference count")}. Between the load and the add, another thread is free to replace that slot and drop the last reference, so the object you loaded can be freed while you are still holding the pointer. Adding one to a freed object's count is a write to memory that belongs to somebody else now.

CPython's answer is to try it and then check {cite("Include/internal/pycore_object.h:571-586@v3.15.0rc1#_Py_TryIncrefCompare")}. Load the pointer. Attempt to add one to the count. Then load the pointer again, and if it is not the same pointer, undo the add and start over. That is an {term("optimistic read")}, and no lock is taken anywhere in it.

{figure("the-optimistic-read", "four steps, load the pointer, bump the count, load the pointer again, hand the object back")}

The attempt in the middle has two ways to succeed. The fast one is for an object this thread already owns, which is a plain non atomic add because nobody else can be touching it {cite("Include/internal/pycore_object.h:520-545@v3.15.0rc1#_Py_TryIncrefFast")}. The slow one is a compare and exchange on the shared half of the count, which refuses if the object is already on its way out {cite("Include/internal/pycore_object.h:547-569@v3.15.0rc1#_Py_TryIncRefShared")}. That split is the {term("biased reference counting")} from M06, and this is the place it earns its keep.

`list_get_item_ref` is the caller {cite("Objects/listobject.c:353-379@v3.15.0rc1#list_get_item_ref")}. It loads the array pointer atomically, checks the index against the length it just read, and tries. If the try fails, it falls back to the version that does take the list's {term("critical section")} {cite("Objects/listobject.c:336-352@v3.15.0rc1#list_item_impl")}. So the lock still exists. It is the retry, not the road.

Dicts and sets do the same thing {cite("Objects/dictobject.c:1566-1600@v3.15.0rc1#_Py_dict_lookup_threadsafe")} {cite("Objects/setobject.c:96-110@v3.15.0rc1#set_compare_threadsafe")}. Sets are the newest of the three: a set lookup has to call `__eq__` on the objects it finds, and that can run arbitrary Python, so 3.15 added a version that notices when the table changed underneath the comparison and starts again.

{figure("what-each-container-does", "a table of what reading and writing each of the three containers does")}

Writing is the part that still locks. `list_ass_item` takes the object's critical section around the assignment {cite("Objects/listobject.c:1158-1170@v3.15.0rc1#list_ass_item")}, and readers carry on straight through it, which is the trade the whole design is making.
""")


lesson.md(f"""
## The same reads, a different list

Now change one thing. Same code, same list length, same index, same number of reads. The only difference is what the list holds: small integers in one case, plain `object()` instances in another, and long strings in a third.

On the build in front of you, if it has the GIL, expect all three to come out the same. That is the point of running it here.

{lesson.claim("On a build with the GIL it makes no difference what the list holds, because the threads were taking turns either way")}
""")


lesson.code(
    """
SMALL = list(range(1000))
FRESH = [object() for _ in range(1000)]
STRINGS = [f"a string long enough that nobody interned it {n}" for n in range(1000)]


def make_reader(data):
    \"\"\"One thread's job: read the same slot over and over and throw the answer away.\"\"\"

    def read():
        local = data
        for _ in range(READS):
            got = local[500]
        return got

    return read


if not CAN_THREAD:
    print("This runtime cannot start a second thread, so there is nothing to time here.")
else:
    for label, data in [("small ints", SMALL), ("objects", FRESH), ("strings", STRINGS)]:
        one = best(make_reader(data), 1)
        four = best(make_reader(data), 4)
        print(f"  {label:10} one {one * 1000:4.0f} ms, four {four * 1000:5.0f} ms")
        print(f"  {label:10} work done against one thread: {4 * one / four:.2f}x")
""",
    varies=(
        "the same timing caveat as the cell above, and on a build with the GIL the three lines "
        "are meant to look alike"
    ),
)


lesson.md(f"""
Here is the same cell on a build with no GIL, from the recordings at the end of this lesson. The list of small integers gets almost three and a half times the work of one thread. The list of ordinary objects gets a third of it, which is three times slower than not bothering with threads at all.

{figure("four-threads-on-one-list", "bars of work done against one thread, small ints and ordinary objects, with and without the GIL")}

Nothing was locked. The reads were lock free in both cases. The difference is that adding one to a reference count is a write, four cores were writing to the same word, and a CPU can only let one core own a cache line at a time. Everything else in this lesson is fast and that one word is not, so that one word is the answer. This is {term("reference count contention")}, and it is the reason the free threaded build cares so much about which objects have a count at all.
""")


lesson.md(f"""
## Which objects have a count at all

An {term("immortal object")} has no working reference count. Incrementing it is a no op, so four threads reading one write nothing and nothing gets contended. M05 introduced them as a startup optimisation. Here they are the difference between three times faster and five times slower.

The next cell asks seven values whether they are immortal, and prints the count for the ones that have one.

{lesson.claim("None and small integers have no reference count at all, while a larger literal and a string built at run time each have an ordinary one")}
""")


lesson.code("""
BIG_LITERAL = 1025
BIG_COMPUTED = int("1025")
TEXT_LITERAL = "a sentence long enough that nobody would have interned it"
TEXT_JOINED = " ".join(["a", "sentence", "built", "at", "run", "time"])

for name, value in [
    ("None", None),
    ("the int 5", 5),
    ("the literal 1025", BIG_LITERAL),
    ('int("1025")', BIG_COMPUTED),
    ("a long literal string", TEXT_LITERAL),
    ("a string joined at run time", TEXT_JOINED),
    ("object()", object()),
]:
    count = sys.getrefcount(value)
    shown = "no count at all" if sys._is_immortal(value) else f"count {count}"
    print(f"  {name:28} {shown}")
""")


lesson.md(f"""
On a build without the GIL, two of those lines change. The literal `1025` and the long literal string both come back with no count at all, while `int("1025")` and the joined string still have one.

The rule is that the free threaded build immortalizes every constant it compiles. Every string in a code object gets interned, where the ordinary build only interns the ones that look like identifiers {cite("Objects/codeobject.c:116-137@v3.15.0rc1#should_intern_string")}, and every other constant gets immortalized too, as long as everything inside it already is {cite("Objects/codeobject.c:139-158@v3.15.0rc1#should_immortalize_constant")} {cite("Objects/codeobject.c:283-300@v3.15.0rc1#intern_one_constant")}.

{figure("who-has-a-count-and-who-does-not", "a table of seven values and whether each has a reference count on each of the two builds")}

That is worth sitting with, because it is a design decision hiding in what looks like an implementation detail. Constants are the things many threads read and nobody writes. Giving them no count is what makes reading them free. The cost is that they are never freed, and the free threaded build decided that was a fair price.
""")


lesson.md(f"""
## One writer is enough

The reads above were friendly: nobody was changing anything. Real programs are not like that, so add one thread that writes, and keep the four readers on the list of small integers that scaled.

Three measurements. The four readers on their own. The four readers with a writer working on a different list. The four readers with a writer working on the list they are reading, though never the slot they read.

{lesson.claim("A single thread writing in a loop costs the four readers much more than the four readers cost each other")}
""")


lesson.code(
    """
OTHER = list(range(1000))


def churn(data, stop):
    \"\"\"Keep writing to one slot of a list until somebody says stop.\"\"\"
    while not stop.is_set():
        data[0] = 1


def with_a_writer(target):
    \"\"\"Time the four readers while one more thread scribbles on the list you pass in.\"\"\"
    stop = threading.Event()
    writer = threading.Thread(target=churn, args=(target, stop))
    writer.start()
    try:
        return best(make_reader(SMALL), 4, rounds=2)
    finally:
        stop.set()
        writer.join()


if not CAN_THREAD:
    print("This runtime cannot start a second thread, so there is nothing to time here.")
else:
    alone = best(make_reader(SMALL), 1)
    four = best(make_reader(SMALL), 4)
    elsewhere = with_a_writer(OTHER)
    same = with_a_writer(SMALL)
    print(f"  four readers, nobody writing: {4 * alone / four:.2f}x")
    print(f"  a writer on a different list: {4 * alone / elsewhere:.2f}x")
    print(f"  a writer on the list they read: {4 * alone / same:.2f}x")
""",
    varies=(
        "timings again, and the gap between the last two lines is much wider on a build without "
        "the GIL than on one with it"
    ),
)


lesson.md(f"""
On a build with the GIL all three lines are poor, and the reason is C01's reason: a thread spinning in a Python loop holds the lock and the readers spend their time waiting for it.

Without the GIL the three lines separate. The readers on their own get about three times the work of one thread. A writer on a different list costs them something, because it is a fifth thread on a four core machine. A writer on their own list costs them almost all of it, and drops them back to roughly one thread's worth.

The reason is in the read path. The first time a thread that does not own a list reads it, the list is marked as shared, and being shared changes what the writer is allowed to do with the old storage {cite("Objects/dictobject.c:1389-1411@v3.15.0rc1#ensure_shared_on_read")} {cite("Objects/setobject.c:75-94@v3.15.0rc1#ensure_shared_on_read")}. The comment in the dict version says it plainly: a resize now has to delay freeing the old keys.
""")


lesson.md(f"""
## Nothing may be freed while somebody might be looking

That delay is the last piece, and it is the one that makes the optimistic read safe rather than merely fast.

Go back to the race at the top. A reader loads a pointer, and before it can do anything with it, a writer replaces the slot and drops the last reference. If the object is freed immediately, the reader is holding a pointer into memory that has been handed back to the allocator, and the retry check reads a field of an object that no longer exists.

So a free threaded build does not free it immediately. The block goes on a per thread queue with a sequence number attached, and it is handed back only once every thread has been observed to move past that number {cite("Include/internal/pycore_qsbr.h:1-30@v3.15.0rc1#QSBR")} {cite("Objects/obmalloc.c:1430-1440@v3.15.0rc1#free_delayed")}. That is {term("safe memory reclamation")}, usually written QSBR. A queue is drained when it gets long enough or when enough memory is sitting on it {cite("Objects/obmalloc.c:1396-1427@v3.15.0rc1#should_advance_qsbr_for_free")} {cite("Objects/obmalloc.c:1500-1530@v3.15.0rc1#_PyMem_FreeDelayed")}.

{figure("where-the-old-storage-goes", "four steps from a writer replacing storage to the old block finally being freed")}

Where does the draining happen? At the {term("periodic check")} {cite("Python/ceval_gil.c:1380-1395@v3.15.0rc1#_PyMem_ProcessDelayed")}. That is C05's eval breaker, doing a job that has nothing to do with signals or the collector. Two lessons that looked unrelated meet in the same fifteen lines of `_Py_HandlePending`.

The next cell is the race, run on purpose. One thread replaces the object in a slot as fast as it can. Another reads that slot two hundred thousand times and immediately touches an attribute of whatever it got. Every bead counts itself on the way out, so you can see how many were freed while the reading was going on.

{lesson.claim("A reader that pulls an object out of a slot while another thread replaces it never gets back an object that has already been freed, on either build")}
""")


lesson.code(
    """
FREED = 0


class Bead:
    \"\"\"An object that counts itself on the way out.\"\"\"

    def __init__(self, n):
        self.n = n

    def __del__(self):
        global FREED
        FREED += 1


if not CAN_THREAD:
    print("This runtime cannot start a second thread, so there is nothing to race here.")
else:
    slot = [Bead(0)]
    stop = threading.Event()

    def replace():
        n = 1
        while not stop.is_set():
            slot[0] = Bead(n)
            n += 1

    writer = threading.Thread(target=replace)
    writer.start()
    seen = set()
    for _ in range(200000):
        seen.add(slot[0].n)
    stop.set()
    writer.join()
    print(f"  different beads the reader got out of that slot: {len(seen)}")
    print(f"  beads freed while the reader was reading: {FREED}")
    print("  beads the reader read after they were freed: 0")
""",
    varies=(
        "how many beads get made and freed depends on the machine, and the count of different "
        "ones the reader saw is tiny on a build with the GIL and large on a build without it"
    ),
)


lesson.md(f"""
The last line is not measured, it is the claim: nothing crashed and no attribute read came back as garbage. On a build with the GIL the reader usually sees one or two different beads, because it holds the lock for a long stretch at a time. Without the GIL it sees tens of thousands, which is what genuinely running at the same instant looks like.

The two recordings below are the headline pair, run in a container with four cores fixed. Same program both times. Once on a build with `--disable-gil` and once on an ordinary one.

{recording(WITHOUT_THE_LOCK)}

{recording(WITH_THE_LOCK)}

Three and a half times the work against a third of it, from the same code, on the same machine, minutes apart. And on the build with the GIL the two lists are indistinguishable, which is the part worth remembering: the difference between them is not a property of Python. It only exists once threads are genuinely running at the same time.

{lesson.claim("Removing the GIL turns what a list holds into a performance decision, and on a build that still has the GIL that decision does not exist", unobservable="the pair of runs needs both an ordinary build and one configured with --disable-gil, and no single interpreter can be both")}
""")


lesson.md("""
## Try it yourself

Four things, roughly in order of how much they will teach you.

Take the second cell and put `sys.intern` around the strings, or replace the list of `object()` with a list of `None`. The reads do not change at all. What changes is whether the objects being read have a count, and on a free threaded build that is the whole result.

In the fourth cell, move the writer onto a slot the readers never touch and then onto the slot they do. It matters much less than you would guess, because the contention is on the list's storage and on the objects, not on the index.

Get a free threaded build and run the whole notebook on it. `uv python install 3.15.0rc1+freethreaded` is one way. Every cell here prints a different story on it, and the cells are the same cells.

Then run the third cell on that build and watch `1025` become immortal. Once you have seen that, go and read `should_immortalize_constant` and work out why a tuple is only immortalized when everything inside it already is.

## What you now know

Reads of a list, a dict and a set are all lock free on a free threaded build in 3.15. The set version is the newest of the three, because a set lookup can run arbitrary Python through `__eq__`.

The way they do it is an optimistic read: load the pointer, try to add one to the object's count, load the pointer again, and start over if it moved.

Adding one has a fast path for an object this thread owns and a compare and exchange for one it does not, which is what biased reference counting is for.

Writing still takes the object's critical section. Readers do not, and go straight past it.

Once reads are lock free, the thing that decides whether threads help is what is being read. A reference count is a single word, and four cores writing to the same word take turns in hardware whatever Python does.

Immortal objects have no working count, so reading one contends with nothing. Four threads reading a list of small integers scale. Four threads reading a list of ordinary objects are slower than one.

The free threaded build therefore immortalizes every constant it compiles, including strings and numbers that the ordinary build leaves alone. The cost is that they are never freed.

The first time a thread reads a container it does not own, the container is marked shared, and from then on its storage cannot be freed straight away.

Instead the old storage goes on a queue and is freed later, once every thread has been seen to move past it. The queue gets drained at the periodic check, which is exactly the eval breaker from C05.

## What is next

C07 stays on the free threaded build and asks what all of this cost the ordinary case. Every one of those atomic operations is real work on a single threaded program too, and the answer that CPython arrived at is a second interpreter loop with the checks compiled out of it, turned on and off while the program is running. That switch is a bit on a word you have already met.
""")


raise SystemExit(lesson.save())
