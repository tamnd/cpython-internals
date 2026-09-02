#!/usr/bin/env python
"""M07. The collector nobody calls.

The seventh lesson of the memory part. T09 showed that a reference cycle needs the collector and
that `gc.collect()` frees one. This lesson is about the collector running when nobody asks: what
counts, what the count has to reach, which of three lists your object is in, and why the most
expensive pass is the one CPython works hardest to avoid.

Everything here runs on any build, in a browser included. The whole point is that this machinery
is visible from Python through the `gc` module, and most people never look.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("m07-the-collector-nobody-calls", "m07")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("m07-the-collector-nobody-calls").figure


lesson.md(f"""
# M07. The collector nobody calls

{badge}

Write a loop that makes a few hundred thousand short lived objects. Do not import `gc`, do not call anything, do not think about memory at all. While that loop runs, the {term("cycle collector")} will start and finish around two thousand times.

{figure("nobody-calls-it", "making a list raising a counter past two thousand, which sets a bit that runs the collector")}

Nothing in your code asked for that. There is a counter you have never seen, a threshold you have never set, and a bit on a flag word that the interpreter checks between instructions. This lesson is about all three, and about the thing they are protecting you from, which is the collector deciding to walk every object in your process at a moment of its own choosing.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/gc.c:1973-1993@v3.15.0rc1`.

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

Every cell runs on the interpreter you already have, including in a browser. There is nothing to build and nothing to install beyond the cell above.

Two cells change the collector's settings while they run and put them back afterwards. If you interrupt one part way through you will be left with unusual thresholds, so run the whole cell rather than half of it.

One warning about the browser. The thresholds and the number of generations are settings rather than facts about the language, and the build Pyodide ships has different ones. Three cells below print noticeably different numbers there, and each of those says so underneath.

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
## The counter you have never seen

`gc.get_count()` returns three numbers. Start with the first one, and find out what it actually counts by moving it.

{lesson.claim("The first number gc.get_count returns goes up when you make an object the collector tracks and comes back down when that object is freed, so it counts what is alive rather than what has been made")}
""")


lesson.code(
    """
import gc

gc.collect()
print(f"  right after a full collection  {gc.get_count()}")

junk = [[] for _ in range(500)]
print(f"  after making 500 lists         {gc.get_count()}")

del junk
print(f"  after dropping all 500         {gc.get_count()}")

for _ in range(500):
    throwaway = []
print(f"  after 500 that died at once    {gc.get_count()}")
""",
    varies="The exact numbers depend on what your session has already done, since a notebook "
    "kernel is doing plenty of its own work. The two lines to read are the last two, which "
    "should be close to each other and far below the 505 above them.",
)


lesson.md(f"""
That last line is the surprising one. Five hundred lists were made and five hundred were freed, one per turn of the loop, and the counter is roughly where it started.

So it is not a count of allocations. It is a count of objects the collector is tracking that are alive right now, and it moves in both directions {cite("Python/gc.c:1973-1993@v3.15.0rc1#_PyObject_GC_Link")} {cite("Python/gc.c:2118-2123@v3.15.0rc1#PyObject_Free")}.

{figure("what-the-counter-counts", "the four moments that change the counter and what each one does")}

Which is a sensible thing to trigger on. A loop that makes and drops one object at a time never builds up anything for a collector to find. A loop that keeps them is the one worth interrupting.

## What happens at two thousand

Making one tracked object too many does not run the collector. It sets a bit {cite("Python/gc.c:1964-1971@v3.15.0rc1#_Py_ScheduleGC")}, and the interpreter notices that bit between two bytecode instructions and runs the collector there {cite("Python/ceval_gil.c:1396-1403@v3.15.0rc1#_Py_RunGC")}.

That is the same flag word signal handling and thread switching use, which is why a collection never lands halfway through an operation that would mind.

You can watch the counter cross the line. It resets to nearly nothing, and the second number goes up by one.

{lesson.claim("When the first count passes the threshold the collector runs, the first count drops back to almost nothing, and the second count goes up by exactly one")}
""")


lesson.code(
    """
gc.collect()
keep = []
before = gc.get_count()

for i in range(4000):
    keep.append([])
    now = gc.get_count()
    if now[0] < before[0]:
        print(f"  after {i + 1} lists the counter went {before} -> {now}")
        break
    before = now

print(f"  the threshold it crossed is    {gc.get_threshold()[0]}")
print(f"  and the three thresholds are   {gc.get_threshold()}")
del keep
""",
    varies="How many lists it takes depends on where the counter started, which depends on "
    "what else is alive. What does not change is the shape of the line: the first number falls "
    "to almost nothing and the second goes up by one. The thresholds themselves are settings "
    "rather than facts about the language, and the browser build ships with the last one set "
    "to 0, which turns automatic full collections off.",
)


lesson.md(f"""
## Three lists, counting three different things

The collector keeps three lists, and an object is in exactly one of them. The names are generation 0, 1 and 2, oldest last.

The confusing part is that the three counts do not all count the same kind of thing {cite("Include/internal/pycore_interp_structs.h:173-178@v3.15.0rc1#gc_generation")}. Only the first counts objects. The second counts collections of the first, and the third counts collections of the second, so the {term("collection threshold")} of 10 means ten passes underneath rather than ten objects {cite("Include/internal/pycore_interp_structs.h:271-278@v3.15.0rc1#GC_GENERATION_INIT")}.

{figure("three-lists", "the three generations, their thresholds, and what each threshold is counting")}

The collector picks the oldest generation whose count is over its threshold, and collects that one and everything younger {cite("Python/gc.c:1315-1321@v3.15.0rc1#gc_select_generation")}.

## Surviving a collection is a promotion

`gc.get_objects` takes a generation, which means you can follow one object as it moves {cite("Modules/gcmodule.c:336-349@v3.15.0rc1#gc_get_objects_impl")}.

{lesson.claim("An object starts in generation 0, moves up every time it survives a collection, never moves back down, and ends up in generation 2 where it stays")}
""")


lesson.code(
    """
gc.disable()
gc.collect()
mine = {"tag": "follow me"}


def which_generation(obj):
    for g in range(3):
        if any(o is obj for o in gc.get_objects(generation=g)):
            return g
    return None


print(f"  as soon as it exists        generation {which_generation(mine)}")
gc.collect(0)
print(f"  after one pass over gen 0   generation {which_generation(mine)}")
gc.collect(0)
print(f"  after another pass over 0   generation {which_generation(mine)}")
gc.collect(1)
print(f"  after a pass over gen 1     generation {which_generation(mine)}")
gc.collect(2)
print(f"  after a full pass           generation {which_generation(mine)}")
gc.enable()
""",
    varies="On the build Pyodide ships the object goes straight to generation 2 on the first "
    "pass and generation 1 stays empty, so the middle lines read 2 rather than 1. The part "
    "that holds everywhere is the direction: up on every pass, never back down, ending at 2.",
)


lesson.md(f"""
{figure("where-your-object-goes", "one object moving from generation 0 to 2 as it survives passes")}

Nothing ever moves an object back down. A promotion is one way, and the merge that does it happens at the end of every collection {cite("Python/gc.c:1486-1497@v3.15.0rc1#gc_list_merge")}.

The consequence is worth stating plainly, because it is the thing that bites people. A cycle that has been alive for a while is not in generation 0 any more, so a pass over generation 0 will not free it, no matter how dead it is.

{lesson.claim("A cycle made a moment ago is freed by a pass over generation 0, and an identical cycle that has already survived a few passes is not freed until a full pass runs")}
""")


lesson.code("""
def make_cycle(tag):
    left = {"tag": tag}
    right = {"tag": tag, "other": left}
    left["other"] = right
    return left


gc.collect()
fresh = make_cycle("fresh")
del fresh
print(f"  a cycle made a moment ago, gc.collect(0) freed  {gc.collect(0)}")

gc.collect()
older = make_cycle("older")
for _ in range(3):
    gc.collect(0)
del older
print(f"  a cycle that survived three passes, collect(0)  {gc.collect(0)}")
print(f"  and then gc.collect(2) freed                    {gc.collect(2)}")
""")


lesson.md(f"""
Both cycles were equally unreachable. The only difference was age, and age decided which list they were sitting in.

## The brake on full passes

A pass over generation 0 walks a couple of thousand objects. A pass over generation 2 walks every tracked object in the process, and there might be millions.

So if a full pass happened every ten passes over generation 1, a program that builds a large structure and keeps it would spend its life walking that structure. Building a list of a million tracked objects would cost time proportional to the square of its length.

CPython refuses. A full pass is skipped unless the number of objects that arrived in the old list since the last full pass is at least a quarter of what is already there {cite("Python/gc.c:1328-1357@v3.15.0rc1#long_lived_pending")}. If a program is not accumulating long lived data, full passes get rare, and then rarer.

The next cell is the only one here that takes a moment. It puts sixty thousand objects in the old generation, lowers the thresholds so the effect shows up quickly, then makes and drops two hundred thousand short lived objects in front of them and counts what actually ran.

{lesson.claim("With sixty thousand long lived objects sitting in the old generation, hundreds of passes over generation 1 produce only a handful of full passes rather than one per two, which is what the threshold on its own would give")}
""")


lesson.code(
    """
gc.collect()
survivors = [[] for _ in range(60000)]
gc.collect()

before = [s["collections"] for s in gc.get_stats()]
original = gc.get_threshold()
gc.set_threshold(100, 2, 2)

for _ in range(400):
    batch = [[] for _ in range(500)]
    del batch

gc.set_threshold(*original)
after = [s["collections"] for s in gc.get_stats()]
ran = [after[i] - before[i] for i in range(3)]

print(f"  passes over generation 0   {ran[0]}")
print(f"  passes over generation 1   {ran[1]}")
print(f"  a threshold of 2 predicts  {ran[1] // 2} full passes")
print(f"  full passes that happened  {ran[2]}")
del survivors
""",
    varies="The exact counts move with what else is alive when the cell starts, and in the "
    "browser they are much smaller because that build collects on a different schedule. The "
    "gap is the point: the last line should be far below the line above it.",
)


lesson.md(f"""
{figure("the-brake-on-full-passes", "the number of full passes the thresholds predict against the number that ran")}

The heuristic is from a 2008 python-dev thread, and the comment in the source names the person who suggested it and links the message. It is worth reading, because it is one of the clearer explanations in the tree of why a garbage collector needs a rule that is not just a counter.

## The collector shrinking its own work

There is a second way to make collections cheap, which is to have fewer objects to walk.

A tuple that cannot reach anything the collector cares about cannot be part of a cycle. `(1, 2, 3)` holds three integers, and an integer holds nothing, so that tuple is dead weight in the young list. Every collection checks for this and drops such tuples out of tracking entirely {cite("Objects/tupleobject.c:138-157@v3.15.0rc1#_PyTuple_MaybeUntrack")}.

The check has to be conservative when the tuple is built, because working it out properly means asking about every element {cite("Objects/tupleobject.c:159-169@v3.15.0rc1#maybe_tracked")}. During a collection there is time to be exact, and the exact version treats an already untracked tuple as harmless {cite("Include/internal/pycore_gc.h:85-93@v3.15.0rc1#_PyObject_GC_MAY_BE_TRACKED")}.

Which produces something you can watch. Nest tuples inside each other, and each collection untracks exactly one more layer, because a layer can only be proved harmless once the layer below it has been.

{lesson.claim("A tuple of integers is never tracked, a tuple nested five deep starts with four of its five layers tracked, and each collection untracks exactly one more layer")}
""")


lesson.code(
    """
gc.collect()
print(f"  a tuple of three integers is tracked: {gc.is_tracked(tuple([1, 2, 3]))}")
print(f"  a tuple holding a list is tracked:    {gc.is_tracked(tuple([[1]]))}")
print()

nest = tuple([1])
for _ in range(4):
    nest = tuple([nest])


def tracked_layers(top):
    layers, at = 0, top
    while isinstance(at, tuple) and at and isinstance(at[0], tuple):
        layers += gc.is_tracked(at)
        at = at[0]
    return layers + gc.is_tracked(at)


print(f"  five nested tuples, tracked layers: {tracked_layers(nest)}")
for pass_number in range(1, 6):
    gc.collect()
    print(f"    after collection {pass_number}: {tracked_layers(nest)}")
""",
    varies="In the browser all four layers go in the first pass rather than one per pass, "
    "because that build lays its generations out differently and every layer ends up in the "
    "same list at the same time. The two lines above the nest behave the same everywhere.",
)


lesson.md(f"""
{figure("one-layer-per-pass", "a five deep nest of tuples losing one tracked layer per collection")}

This runs inside every collection, on the whole young list {cite("Python/gc.c:665-676@v3.15.0rc1#untrack_tuples")}.

Dictionaries used to get the same treatment and no longer do. Up to 3.13 a dictionary holding only untrackable values was untracked too, and 3.14 removed the machinery, because keeping the tracking flag correct meant checking it on every single insertion {cite("Python/gc.c:1519-1529@v3.15.0rc1#long_lived_total")}. Full passes over dictionaries got slightly more expensive and every `d[k] = v` in the language got slightly cheaper.

## Watching a collection happen

`gc.callbacks` is a plain list. Append a function and it gets called before and after every collection, with the generation and the result {cite("Python/gc.c:1258-1265@v3.15.0rc1#invoke_gc_callback")}.

{lesson.claim("Appending a function to gc.callbacks gets it called twice per collection, once with the phase start and once with stop, and the info it is handed says which generation ran")}
""")


lesson.code("""
watched = []


def note_it(phase, info):
    watched.append((phase, info["generation"], info["collected"]))


gc.callbacks.append(note_it)
for _ in range(12):
    gc.collect(0)
gc.collect(2)
gc.callbacks.remove(note_it)

print(f"  calls recorded          {len(watched)}")
print(f"  phases                  {sorted(set(p for p, _, _ in watched))}")
print(f"  generations collected   {[g for p, g, _ in watched if p == 'stop']}")
""")


lesson.md(f"""
`gc.get_stats()` keeps a running total per generation, and 3.15 added two fields to it: how many objects the pass had to consider, and how long it took.

{lesson.claim("gc.get_stats returns one dictionary per generation, and on 3.15 each one carries a candidates count and a duration that 3.14 does not have")}
""")


lesson.code(
    """
for number, generation in enumerate(gc.get_stats()):
    keys = ", ".join(sorted(generation))
    print(f"  generation {number}: {keys}")

print()
newest = gc.get_stats()[0]
print(f"  passes over generation 0 so far  {newest['collections']}")
print(f"  objects freed by them            {newest['collected']}")
if "candidates" in newest:
    print(f"  objects they had to look at      {newest['candidates']}")
    print(f"  seconds spent doing it           {newest['duration']:.4f}")
else:
    print("  this version does not report candidates or duration")
""",
    differs="On 3.14 the dictionaries have three keys rather than five, so the last two lines "
    "are replaced by one saying so. The counts themselves are whatever your session has done, "
    "so they will not match anybody else's.",
)


lesson.md(f"""
## Freezing what you already have

There is a fourth list, and the collector never looks at it. `gc.freeze()` moves everything currently tracked into the {term("permanent generation")}, and nothing comes back until `gc.unfreeze()` {cite("Python/gc.c:1735-1743@v3.15.0rc1#_PyGC_Freeze")}.

This exists for one specific shape of program. A server loads its configuration and its data, then forks worker processes. Fork does not copy memory, it shares it until somebody writes. The collector walking an object writes to that object's header, so a single full pass in a worker can end up copying pages that nothing actually modified.

Freezing before the fork means the parent's data is never walked again, so it is never written to, so it stays shared.

{lesson.claim("gc.freeze moves every tracked object into a generation the collector ignores, gc.get_freeze_count reports how many, and gc.unfreeze puts them all back")}
""")


lesson.code(
    """
gc.collect()
print(f"  frozen objects before      {gc.get_freeze_count()}")
print(f"  tracked in generation 2    {len(gc.get_objects(generation=2))}")

gc.freeze()
print(f"  frozen after gc.freeze()   {gc.get_freeze_count()}")
print(f"  left in generation 2       {len(gc.get_objects(generation=2))}")

gc.unfreeze()
print(f"  frozen after gc.unfreeze() {gc.get_freeze_count()}")
""",
    varies="How many objects your session has is your session's business, so the number will "
    "not match anybody else's. The three things that hold everywhere are that freezing moves "
    "all of them, that generation 2 is empty afterwards, and that unfreezing puts them back.",
)


lesson.md("""
## Try it yourself

Three things.

Put a callback on `gc.callbacks` at the top of a notebook cell that does something ordinary, like building a dictionary of a hundred thousand entries, and print the generations it records. Most people are surprised by how many collections a piece of code they thought was simple sets off.

Take the promotion cell and change `gc.collect(0)` to `gc.collect(1)`. Your object jumps straight to generation 2, because a pass over generation 1 collects generation 0 as well and promotes everything that survives either. Then work out from that what `gc.collect()` with no argument does, and check by trying it.

Set `gc.set_threshold(0)` and run the cycle cell again. Zero turns automatic collection off entirely without disabling the module, so the cycle sits there until you ask for it by hand. Put the threshold back afterwards, or the rest of the notebook will behave oddly.

## What you now know

The collector runs on its own, thousands of times in an ordinary program, and nothing in your code asks for it.

What triggers it is a counter of tracked objects that are alive right now. It goes up when one is made and down when one is freed, so making and dropping a million objects one at a time never triggers anything. Keeping two thousand does.

Crossing the threshold does not run the collector. It sets a bit that the interpreter checks between bytecode instructions, which is the same mechanism signals and thread switches use.

There are three lists. Only the first counts objects, with a threshold of 2000. The other two count collections of the list below them, with a threshold of 10 each.

Surviving a collection promotes an object to the next list, and nothing goes back down. So how old a cycle is decides which pass can free it, and an old cycle is invisible to a pass over generation 0.

Full passes are rarer than the thresholds suggest, because one is skipped unless a quarter of the old generation arrived since the last one. Without that rule, building and keeping a large structure would cost quadratic time.

The collector removes work from its own future by untracking tuples that cannot reach anything trackable, one layer of nesting per pass. Dictionaries got the same treatment until 3.14, which dropped it to make ordinary assignment cheaper.

`gc.callbacks` lets you watch every collection as it happens, `gc.get_stats` keeps the totals, and `gc.freeze` moves everything you already have into a list the collector never walks.

## What is next

M08 asks all of this again on the free threaded build, where the answers are different in ways that follow from M06. There is no single counter to bump when any thread can be allocating, generations mean something else when objects are owned by threads, and a collector that walks the heap has to do something about the other threads still running. The word that turns up is stop the world, and it is more interesting than it sounds.
""")


raise SystemExit(lesson.save())
