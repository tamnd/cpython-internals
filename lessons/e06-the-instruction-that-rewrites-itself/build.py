#!/usr/bin/env python
"""E06. The instruction that rewrites itself.

The sixth lesson of the interpreter part. E05 was about information that lives beside the
bytecode. This one is about the bytecode changing while the program runs.

The hook is that disassembling the same function twice can give two different answers. Call
it once and `BINARY_OP` is still `BINARY_OP`. Call it again and it has become
`BINARY_OP_ADD_INT`, because the interpreter watched the operands go past and decided it
could skip most of the work.

The lesson watches the rewrite happen, reads the countdown that decides when it happens out
of the bytecode itself, and measures what the whole thing is worth.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("e06-the-instruction-that-rewrites-itself", "e06")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("e06-the-instruction-that-rewrites-itself").figure


lesson.md(f"""
# E06. The instruction that rewrites itself

{badge}

Disassemble a function. Call it twice. Disassemble it again.

You get a different answer. Same function, same source, same code object, and one of the instructions has a different name than it had a moment ago. Nothing recompiled and nothing was patched by you. The interpreter watched what went past and rewrote the instruction in place.

{figure("the-life-of-one-instruction", "an instruction going from cold to specialized and back to general")}

This is {term("specialization")}, and it is the single largest source of speed in modern CPython. This lesson watches it happen, reads the countdown that decides when it happens, and measures what it buys.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/specialize.c:362-374@v3.15.0rc1#specialize`.

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

Specialization arrived in 3.11 and has been growing ever since. Which instructions exist, how many of them there are, and the exact numbers in the counter all move between releases, so several cells below say what changes and where.
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
## The same function, disassembled twice

Here is the whole thing in one cell. A function that adds two numbers, disassembled cold, then called twice, then disassembled again.

The second disassembly passes `adaptive=True`. That is the flag that says show me what is actually there rather than what the compiler wrote.

{lesson.claim("disassembling the same unmodified function before and after calling it twice gives two different instruction names")}
""")


lesson.code(
    """
import dis


def add(left, right):
    return left + right


def arithmetic_in(one):
    steps = dis.get_instructions(one, adaptive=True)
    return [step.opname for step in steps if step.opname.startswith("BINARY_OP")]


print(f"  before any call    {arithmetic_in(add)}")
add(1, 2)
print(f"  after one call     {arithmetic_in(add)}")
add(3, 4)
print(f"  after two calls    {arithmetic_in(add)}")
""",
)


lesson.md(f"""
Two calls, and `BINARY_OP` is now `BINARY_OP_ADD_INT`.

That name is not a label or an annotation. It is a real, separate instruction with its own body in `Python/bytecodes.c`, and the byte in the bytecode array changed to point at it. The old instruction is gone from that slot.

What replaced it is a much smaller piece of work. The general `BINARY_OP` has to look up the type of each operand, find the right slot on it, deal with the reflected operand rules, and handle the case where either side says it does not know. The specialized form does two type checks and an addition {cite("Python/bytecodes.c:672-685@v3.15.0rc1#_BINARY_OP_ADD_INT")}.

Those two type checks are worth a name. They are the {term("guard")}s, and they are the reason this is safe {cite("Python/bytecodes.c:635-643@v3.15.0rc1#_GUARD_TOS_INT")}.

{lesson.claim("BINARY_OP is not one instruction but a family, and the whole set of families is listed in a module you can import")}
""")


lesson.code(
    """
from _opcode_metadata import _specializations

family = _specializations["BINARY_OP"]
print(f"  BINARY_OP has {len(family)} specialized forms, including:")
for name in ["BINARY_OP_ADD_INT", "BINARY_OP_ADD_FLOAT", "BINARY_OP_ADD_UNICODE"]:
    print(f"    {name:24} {'yes' if name in family else 'no'}")
print()
print(f"  families in this build   {len(_specializations)}")
print(f"  specialized forms total  {sum(len(one) for one in _specializations.values())}")
""",
    differs="On 3.14 there are 15 forms of `BINARY_OP` rather than 16, 17 families rather "
    "than 18, and 84 specialized forms in total rather than 91. The set grows with almost "
    "every release, which is a decent measure of how much work goes into this.",
)


lesson.md(f"""
## What it turns into depends on what it saw

The interesting part is that the same line of source becomes a different instruction depending on nothing but the values that flowed through it.

Five copies of the identical function, fed five different pairs of operands.

{figure("what-it-turns-into", "the same add function becoming five different instructions depending on operand types")}

{lesson.claim("five copies of the same source compile to the same bytecode and then specialize into different instructions based only on the values passed in")}
""")


lesson.code(
    """
def fresh(source, name="f"):
    space = {}
    exec(compile(source, "<made here>", "exec"), space)
    return space[name]


def fresh_add():
    return fresh("def f(left, right):\\n    return left + right\\n")


pairs = [
    ("two small ints", 1, 2),
    ("two floats", 1.5, 2.5),
    ("two strings", "a", "b"),
    ("two lists", [1], [2]),
    ("an int and a float", 1, 2.5),
]

for label, left, right in pairs:
    one = fresh_add()
    one(left, right)
    one(left, right)
    print(f"  {label:20} {arithmetic_in(one)[0]}")
""",
    differs="On 3.14 the two lists row stays at plain `BINARY_OP`, because `BINARY_OP_EXTEND` "
    "did not cover list concatenation yet. The first three rows are the same on both, from "
    "source that is character for character identical.",
)


lesson.md(f"""
Character for character the same source, and several different instructions.

Notice the last row. An int plus a float does not get a fast path of its own, so it lands on something general. Mixing types is not an error and nothing goes wrong, you just do not get the prize.

That is the whole shape of the idea. The interpreter is betting that what it saw last time is what it will see next time, and it only takes the bet after seeing the same thing twice.

## The counter in the instruction

So where does "twice" live?

In the bytecode. Right after the instruction, in a slot that is not an instruction at all.

Instructions that can specialize are followed by empty two byte slots called {term("inline cache")} entries, and `dis` will tell you how many each one has. The first slot after a specializing instruction holds the {term("adaptive counter")}: a countdown that says how many more times to run this before trying to rewrite it {cite("Include/internal/pycore_code.h:479-489@v3.15.0rc1#adaptive_counter_cooldown")}.

{lesson.claim("the number of cache slots after each instruction is a fixed property of that instruction and can be read out of dis")}
""")


lesson.code(
    """
sizes = dis._inline_cache_entries
for name in ["LOAD_ATTR", "BINARY_OP", "LOAD_GLOBAL", "STORE_ATTR", "CALL", "TO_BOOL"]:
    slots = sizes[name]
    print(f"  {name:12} {slots} cache slot(s), {slots * 2} bytes after the instruction")
print()
print(f"  instructions with a cache at all  {len(sizes)}")
""",
    differs="The six named here reserve the same number of slots on 3.14, but the last "
    "number is 19 there rather than 22. Three more instructions grew a cache in 3.15.",
)


lesson.md(f"""
Now read the counter out. It sits two bytes past the instruction, in the private copy of the bytecode that the interpreter actually runs.

That private copy is worth its own name. `co_code` is what the compiler produced and it never changes. `_co_code_adaptive` is the copy that gets rewritten, and making it is called {term("quickening")} {cite("Python/specialize.c:63-70@v3.15.0rc1#_PyCode_Quicken")}.

{figure("two-copies-of-the-bytecode", "co_code stays as compiled while the adaptive copy is rewritten as the program runs")}

The counter is a sixteen bit word holding two things. The low three bits are a backoff exponent, and the rest is the countdown {cite("Include/internal/pycore_backoff.h:37-57@v3.15.0rc1#MAX_BACKOFF")}.

{figure("reading-the-counter", "the raw counter word decoding into a countdown value and a backoff exponent")}

{lesson.claim("the countdown that controls specialization can be read directly out of the running bytecode and watched change")}
""")


lesson.code(
    """
def counter_of(one, opname="BINARY_OP"):
    raw = one.__code__._co_code_adaptive
    for step in dis.get_instructions(one, adaptive=True):
        if step.opname.startswith(opname):
            at = step.offset + 2
            word = raw[at] | (raw[at + 1] << 8)
            return word, word >> 3, word & 7
    return None


watched = fresh_add()
print(f"  cold                {counter_of(watched)}")
watched(1, 2)
print(f"  after one call      {counter_of(watched)}")
watched(3, 4)
print(f"  after two calls     {counter_of(watched)}   {arithmetic_in(watched)[0]}")
""",
    differs="On 3.14 every number is doubled: 17 cold rather than 9, and 832 rather than "
    "416, because the countdown is stored one bit further up and drains two at a time. The "
    "two calls to warm up and the fifty three misses to give up come out the same either way.",
)


lesson.md(f"""
Cold, the word is 9: a countdown of 1 and a backoff of 1. One call takes it to 0, and the call after that finds it at zero and tries to specialize.

Once it has specialized, the counter is reset to something much larger. That is not a warmup any more, that is slack: how many times the guards may fail before the interpreter gives up on this guess {cite("Python/specialize.c:362-374@v3.15.0rc1#specialize")}.

## Two calls to warm up, fifty three misses to give up

Both of those numbers are named constants with comments explaining them {cite("Include/internal/pycore_code.h:450-464@v3.15.0rc1#ADAPTIVE_WARMUP_VALUE")}.

Rather than take the header's word for it, count them.

{lesson.claim("an instruction specializes on exactly the second execution, and a specialized instruction survives exactly fifty two failures and gives up on the fifty third")}
""")


lesson.code(
    """
warming = fresh_add()
calls = 0
while arithmetic_in(warming)[0] == "BINARY_OP":
    warming(1, 2)
    calls += 1
print(f"  calls before it specialized   {calls}   now {arithmetic_in(warming)[0]}")

misses = 0
while arithmetic_in(warming)[0] == "BINARY_OP_ADD_INT":
    warming(1.5, 2.5)
    misses += 1
print(f"  misses before it gave up      {misses}   now {arithmetic_in(warming)[0]}")
""",
)


lesson.md(f"""
Two and fifty three, and both numbers are in the header with a comment next to them. The second one is fifty three because it is a prime, so a program that misses on a regular cycle will not sit in step with the counter forever.

Notice what it turned into on the way out. It did not go back to plain `BINARY_OP` and sit there. It re-specialized, this time for floats, because floats are what it kept seeing {cite("Python/specialize.c:376-390@v3.15.0rc1#unspecialize")}.

That is {term("deoptimization")} doing its job. A guess that stops being right is replaced rather than abandoned.

{lesson.claim("an instruction that keeps missing does not return to the general form permanently, it re-specializes for whatever it is now seeing")}
""")


lesson.code(
    """
flipping = fresh_add()
seen = []
for round_number in range(4):
    left, right = (1, 2) if round_number % 2 == 0 else ("a", "b")
    for _ in range(200):
        flipping(left, right)
    seen.append(arithmetic_in(flipping)[0])

for round_number, name in enumerate(seen):
    fed = "ints" if round_number % 2 == 0 else "strings"
    print(f"  after 200 calls with {fed:8} {name}")
""",
    varies="Which form it lands on after a switch can depend on where in the countdown the "
    "switch happened, so another build may show one extra round in the general form. The "
    "pattern is the same: it follows the data.",
)


lesson.md(f"""
## It is not just arithmetic

Arithmetic is the easy example, but it is a small part of what this does. Attribute lookup is where it earns most of its keep, because `something.name` is one of the most common things a Python program does and the general version of it is genuinely slow.

The rules for finding an attribute are the same for every object. But the shape of the object decides which of those rules will matter, and there is a specialized instruction for each common shape.

{figure("where-an-attribute-lookup-goes", "the same attribute lookup becoming five different instructions depending on object shape")}

{lesson.claim("the same attribute lookup specializes into different instructions depending only on the shape of the object it is reading from")}
""")


lesson.code(
    """
import types


class Normal:
    def __init__(self):
        self.x = 1

    def method(self):
        return 1


class Slotted:
    __slots__ = ("x",)

    def __init__(self):
        self.x = 1


class WithProperty:
    @property
    def x(self):
        return 1


module = types.ModuleType("made_here")
module.x = 1

read_attribute = "def f(thing):\\n    return thing.x\\n"
call_method = "def f(thing):\\n    return thing.method()\\n"


def attribute_in(one):
    steps = dis.get_instructions(one, adaptive=True)
    return next(step.opname for step in steps if step.opname.startswith("LOAD_ATTR"))


cases = [
    ("a normal object", read_attribute, Normal()),
    ("a __slots__ object", read_attribute, Slotted()),
    ("a property", read_attribute, WithProperty()),
    ("a module", read_attribute, module),
    ("a method call", call_method, Normal()),
]

for label, source, thing in cases:
    one = fresh(source)
    one(thing)
    one(thing)
    print(f"  {label:20} {attribute_in(one)}")
""",
)


lesson.md(f"""
Five different instructions from two identical words of source, and the family is larger than that again.

The one worth looking at twice is the method call. `thing.method()` does not build a bound method object and then call it. When the interpreter can see that the attribute is a function on the type and the instance has nothing shadowing it, it loads the function and the instance separately and skips the intermediate object entirely.

Calls specialize too, on the same principle and by the same mechanism.

{lesson.claim("calls specialize into different instructions depending on what is being called, not just on the arguments")}
""")


lesson.code(
    """
shapes = [
    ("len of a list", "def f(x):\\n    return len(x)\\n", [1, 2, 3]),
    ("a python function", "def g(y):\\n    return y\\ndef f(x):\\n    return g(x)\\n", 1),
    ("building a list", "def f(x):\\n    return list(x)\\n", [1, 2, 3]),
]

for label, source, argument in shapes:
    one = fresh(source)
    one(argument)
    one(argument)
    steps = dis.get_instructions(one, adaptive=True)
    print(f"  {label:20} {next(s.opname for s in steps if s.opname.startswith('CALL'))}")
""",
    varies="Call specializations move around more than most between releases, so another "
    "Python may name these differently or leave one of them general.",
)


lesson.md(f"""
## What a miss actually costs

Time it. Three lists, all the same length, all summed by the same function. One holds ints, one holds floats, and one alternates.

The alternating one is the interesting case. Every value is a perfectly ordinary number and every addition is valid. The only thing wrong with it is that the instruction never gets to be right twice in a row.

{figure("what-a-miss-costs", "three timings showing the alternating list slower than either uniform list")}

{lesson.claim("a loop over mixed types is slower than the same loop over either type alone, purely because the instruction cannot stay specialized")}
""")


lesson.code(
    """
import timeit


def total_of(values):
    running = 0
    for value in values:
        running = running + value
    return running


ints = [1] * 1000
floats = [1.5] * 1000
mixed = [1 if index % 2 else 1.5 for index in range(1000)]

lists = [
    ("every value an int", ints),
    ("every value a float", floats),
    ("alternating between the two", mixed),
]

for label, values in lists:
    best = min(timeit.repeat(lambda values=values: total_of(values), number=200, repeat=5))
    print(f"  {label:28} {best / 200 / 1000 * 1e9:5.1f} ns per addition")
""",
    varies="A timing, so the numbers move, and a browser build is several times slower across "
    "the board. The ordering is the stable part: the mixed list is the slowest of the three "
    "even though every value in it is an ordinary number.",
)


lesson.md(f"""
The mixed list is slower than either pure one, and the work is identical. That gap is the value of specializing, measured from the wrong side.

This is also the most useful practical lesson in the whole topic. Code that keeps the types going through a hot loop consistent runs faster than code that does not, and it is not because of anything you would see in the source.

## Most instructions never get hot

Last thing, and it is a useful corrective. Reading about all of this makes it sound like the whole program gets rewritten. It does not.

Take a real module out of the standard library, exercise it a little, and count how many of its specializable instructions actually specialized.

{lesson.claim("in a real module only a small fraction of specializable instructions ever specialize, because most code does not run often enough")}
""")


lesson.code(
    """
import random

for _ in range(500):
    random.random()
    random.choice([1, 2, 3])
    random.sample(range(20), 3)
    random.shuffle([1, 2, 3, 4])

bases = set(_specializations)
forms = {name for one in _specializations.values() for name in one}


def every_code_in(module):
    found = []
    for thing in vars(module).values():
        code = getattr(thing, "__code__", None)
        if code is not None:
            found.append(code)
        elif isinstance(thing, type):
            for member in vars(thing).values():
                code = getattr(member, "__code__", None)
                if code is not None:
                    found.append(code)
    return found


warm = cold = 0
for code in every_code_in(random):
    for step in dis.get_instructions(code, adaptive=True):
        if step.opname in bases:
            cold += 1
        elif step.opname in forms:
            warm += 1

print(f"  specializable instructions  {warm + cold}")
print(f"  actually specialized        {warm}")
print(f"  still cold                  {cold}")
""",
    varies="The `random` module changes between releases, so the totals move. The shape does "
    "not: a handful of functions ran, and everything else in the module is still sitting at "
    "the instructions the compiler wrote.",
)


lesson.md("""
Most of them never warmed up, and that is normal. Specializing is not free, so an instruction has to earn it by running twice, and most instructions in most modules never run at all in a given program.

## Try it yourself

Three things to try.

The first is to find the boundary of "small int". `BINARY_OP_ADD_INT` does not work on every integer, only on ones that fit in a single internal digit. Feed the add function two enormous integers and see what it specializes into, then work backwards to find roughly where the cutoff is.

The second is to break a specialization from the outside. Specialize an attribute load on a normal object, then assign to the class after the fact, and watch what happens on the next call. The guards have to notice, and the mechanism they use is worth finding.

The third is to build the worst case on purpose. Write a loop where the operand types change on a cycle of exactly fifty three, and compare it to one that changes on a cycle of fifty two. The prime was chosen for a reason and you can watch the reason.

## What just happened

Disassembling the same function before and after calling it can give two different answers, because the interpreter rewrites instructions in place based on what it sees.

The bytecode you compiled and the bytecode that runs are two different arrays. `co_code` never changes. `_co_code_adaptive` is the copy that gets rewritten, and it is thrown away with the process.

A specialized instruction is a small sequence: one or two guards that check the operand types, then a body that does the work with none of the general lookup. If a guard fails the instruction bails out to the general form rather than being wrong.

The decision is driven by a two byte counter stored in the bytecode itself, right after the instruction. It holds a countdown and a backoff exponent packed into one word, and you can read it out and watch it move.

An instruction specializes on its second execution, and a specialized instruction gives up after fifty three consecutive misses. Both numbers are named constants in the headers, with comments saying why.

Giving up does not mean going back to general forever. It means re-specializing for whatever the code is now doing, which is why a program that changes shape halfway through still gets fast again afterwards.

Arithmetic is the small case. Attribute lookup and calls are where most of the benefit is, and both have large families of specialized forms chosen by the shape of the thing involved.

A loop over mixed types is slower than the same loop over one type, and nothing in the source explains why. That gap is specialization measured from the wrong side.

## What is next

E07 is tier two. Everything in this lesson happens one instruction at a time, and there is a ceiling on how much that can win: each instruction still has to be fetched and dispatched separately, and it still cannot know anything about its neighbours. So once a loop has been running long enough, CPython starts recording the instructions it executes into a straight line trace, translates each one into smaller pieces called micro operations, and optimizes across the boundaries that used to separate them. There is a way to ask for that trace and print it, and reading one next to the bytecode it came from is the clearest picture of what the interpreter is really doing.
""")


raise SystemExit(lesson.save())
