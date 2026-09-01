#!/usr/bin/env python
"""E02. Two bytes at a time.

The second lesson of the interpreter part. E01 was about where the code for the eval loop
comes from. This one is about the thing that code spends all its time doing: reading the
next instruction out of a flat array of sixteen bit words and jumping to it.

The reason it deserves a whole lesson is that almost nothing about the array is what a
disassembly suggests. Half the words in a small function are not instructions. The pointer
does not move by two. An argument bigger than 255 arrives in pieces. Some opcode numbers
cannot fit in an opcode field on purpose. And the bytes you get from `co_code` are a
reconstruction rather than the bytes running.

Every one of those can be checked from a plain install, which is what the cells do.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("e02-two-bytes-at-a-time", "e02")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("e02-two-bytes-at-a-time").figure


lesson.md(f"""
# E02. Two bytes at a time

{badge}

The {term("eval loop", "eval loop")} does one thing over and over. Read the next instruction, do it, read the next one. E01 was about where the code for the doing comes from. This lesson is about the reading.

The reading is smaller than you would guess: one sixteen bit load, a shift to split it, and a jump. What is not small is everything the load has to already know. The array it reads is not the list `dis` prints, the pointer does not move by two, several of the words in it are not instructions at all, and running one of those on purpose crashes the process.

{figure("the-same-sixteen-bits", "one sixteen bit word with three different readings stacked above each other")}

All of it follows from that picture. Sixteen bits, three meanings, and nothing in the bits saying which.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/ceval_macros.h:250-254@v3.15.0rc1#NEXTOPARG`.

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

Everything below was checked against the version this cell prints and against 3.14. A lot of the numbers move between the two, more than in most lessons, because one instruction gained a cache slot and that shifts every offset after it. Each cell that moves says so where it appears.
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
## One instruction is one sixteen bit word

A {term("code object", "code object")} holds its {term("bytecode", "bytecode")} as a flat array. Every entry in it is the same size, sixteen bits, and in C that entry is a union of three different ways of reading the same word, {cite("Include/internal/pycore_structs.h:25-32@v3.15.0rc1")}.

The first reading is the obvious one: a low byte holding the {term("opcode", "opcode")} and a high byte holding the {term("oparg", "argument")}. The second is a whole sixteen bit value used as an {term("inline cache", "inline cache")} slot. The third is a countdown counter the specializer decrements. One word, three meanings, and no tag anywhere saying which is in force.

{lesson.claim("the same sixteen bits in a code object are read as an opcode and argument pair, as a cache slot, or as a countdown counter, with nothing in the word saying which", unobservable="the union is a C type, so the three readings are quoted from the pinned tree rather than measured from Python")}

Start with the simplest thing you can measure: how big is a small function, and how much of it is instructions.

{lesson.claim("a code object holds more sixteen bit words than dis reports instructions, because the extra words are cache slots belonging to the instruction in front of them")}
""")


lesson.code(
    """
import dis


def add(a, b):
    total = a + b
    return total


code = add.__code__
stream = code.co_code

print(f"  bytes in the code object   {len(stream)}")
print(f"  words, at two bytes each   {len(stream) // 2}")
print(f"  instructions dis reports   {sum(1 for _ in dis.get_instructions(code))}")
print()
for offset in range(0, len(stream), 2):
    first, second = stream[offset], stream[offset + 1]
    print(f"  {offset:3}  {first:4} {second:4}   {dis.opname[first]}")
""",
    differs="On 3.14 this function is 22 bytes rather than 24, because RESUME does not carry "
    "a cache slot there. Every offset from the second word on shifts down by two. The "
    "opcode numbers are different too, which is E01's point about numbers moving between "
    "releases.",
)


lesson.md(f"""
Six instructions, twelve words. Half of what is in there is `CACHE`, which is not something the interpreter runs. It is scratch space belonging to the instruction in front of it, and the size of that space is fixed per instruction by the definition in `Python/bytecodes.c`, which is where E01 left off.

{figure("what-a-listing-hides", "six instructions laid out at their real offsets with the cache words between them")}

That is the whole difficulty of reading this array. The words are uniform and their meanings are not, so you cannot start in the middle. You have to walk it from the beginning, and at every step you have to know how much room the instruction you just read takes up.

## The fetch half of the eval loop, in twelve lines

Here is the C, which is shorter than the explanation, {cite("Python/ceval_macros.h:250-254@v3.15.0rc1#NEXTOPARG")}. It loads one sixteen bit word into the union, reads `word.op.code` into `opcode` and `word.op.arg` into `oparg`, and that is the entire decode step. No shifting written out, no masking. The union does it.

The full move to the next instruction is three lines, {cite("Python/ceval_macros.h:198-205@v3.15.0rc1#DISPATCH")}: fetch, a hook for tracing, then the jump. Advancing past cache slots is separate and happens inside the instruction body, through a macro that exists mostly so the generators can tell an advance from a jump, {cite("Python/ceval_macros.h:256-261@v3.15.0rc1#SKIP_OVER")}.

{figure("walking-the-stream", "the four steps between the end of one instruction and the start of the next")}

You can write the same walk in Python. Take the low byte as the opcode, fold any `EXTENDED_ARG` into the argument, then step forward by one word plus two bytes per declared cache slot. If that reproduces `dis.get_instructions` exactly, there is nothing else feeding the disassembler either.

{lesson.claim("walking co_code two bytes at a time, folding EXTENDED_ARG and skipping cache slots by their declared count, reproduces dis.get_instructions exactly")}
""")


lesson.code(
    """
def walk(target):
    bytes_of_it = target.co_code
    found = []
    offset = 0
    extended = 0
    while offset < len(bytes_of_it):
        number, argument = bytes_of_it[offset], bytes_of_it[offset + 1]
        name = dis.opname[number]
        if name == "EXTENDED_ARG":
            extended = (extended << 8) | argument
            offset += 2
            continue
        found.append((offset, name, (extended << 8) | argument))
        extended = 0
        offset += 2 + 2 * dis._inline_cache_entries.get(name, 0)
    return found


mine = walk(code)
theirs = [(one.offset, one.opname, one.arg or 0) for one in dis.get_instructions(code)]

for offset, name, argument in mine:
    print(f"  {offset:3}  {name:36} {argument}")
print()
print(f"  matches dis.get_instructions   {mine == theirs}")
""",
    differs="On 3.14 the offsets are 0, 2, 4, 16, 18, 20 rather than 0, 4, 6, 18, 20, 22, "
    "for the same six instructions. The last line reads True on both.",
)


lesson.md(f"""
Twelve lines, and it agrees. `dis` is doing more than this, because it also resolves arguments into names and reads the line table, but the walk itself is exactly what you just wrote.

## Why the pointer jumps over things

The {term("instruction pointer", "instruction pointer")} is a local C variable called `next_instr`, and it is not a byte counter. It moves in whole words, and after an instruction with cache slots it moves further than one.

You can watch this from Python, because opcode level tracing reports the interpreter's real position rather than a normalised one. Turn it on for a single function and record where it stops.

{lesson.claim("the interpreter never stops on a cache slot, so the offsets it visits jump by more than two after an instruction that carries a cache")}
""")


lesson.code(
    """
stepped = []


def watch_opcodes(frame, event, argument):
    if event == "opcode":
        stepped.append(frame.f_lasti)
    return watch_opcodes


def on_call(frame, event, argument):
    if frame.f_code is code:
        frame.f_trace_opcodes = True
        frame.f_trace = watch_opcodes
        return watch_opcodes
    return None


sys.settrace(on_call)
add(2, 3)
sys.settrace(None)

gaps = [stepped[at + 1] - stepped[at] for at in range(len(stepped) - 1)]

print(f"  offsets it stopped at   {stepped}")
print(f"  gaps between them       {gaps}")
""",
    differs="On 3.14 the offsets are 2, 4, 16, 18, 20 rather than 4, 6, 18, 20, 22. The gaps "
    "are the same on both, because the instruction with five cache slots is the same one.",
)


lesson.md(f"""
One gap of twelve, and four gaps of two. The twelve is `BINARY_OP` plus its five cache slots, stepped over in a single move.

The list starts at the second instruction rather than the first. That is not the pointer skipping anything: `RESUME` is the instruction that reports the call, so it has already run by the time opcode events are switched on.

## When one byte is not enough

An argument is one byte, so it reaches 255 and stops. Functions with more than 256 locals or constants are ordinary, so there has to be a way through, and the way is an extra instruction in front carrying the high bits, {cite("Include/internal/pycore_structs.h:17-24@v3.15.0rc1")}.

{term("EXTENDED_ARG", "EXTENDED_ARG")} is six lines, {cite("Python/bytecodes.c:6092-6098@v3.15.0rc1#EXTENDED_ARG")}, and the interesting part is the last two. It shifts its own argument left by eight, reads the next opcode itself, and jumps straight to it. It never goes back round to the top of anything. Up to three can stack up, which gets an argument to thirty two bits.

{figure("when-one-byte-is-not-enough", "an EXTENDED_ARG in front of a STORE_FAST, and the argument the pair produces")}

{lesson.claim("an argument bigger than 255 is carried by an EXTENDED_ARG instruction in front of the real one, and dis folds the pair into a single number")}
""")


lesson.code(
    """
body = "\\n".join(f"    v{n} = {n}" for n in range(300))
namespace = {}
exec(f"def many():\\n{body}\\n", namespace)
wide = namespace["many"].__code__
raw = wide.co_code

count = sum(1 for one in dis.get_instructions(wide) if one.opname == "EXTENDED_ARG")
first = next(at for at in range(0, len(raw), 2) if dis.opname[raw[at]] == "EXTENDED_ARG")

print(f"  locals in the function     {len(wide.co_varnames)}")
print(f"  EXTENDED_ARG instructions  {count}")
print()
print(f"  the first one is at offset {first}")
print(f"    the word there    {raw[first]:4} {raw[first + 1]:4}   {dis.opname[raw[first]]}")
print(f"    the word after it {raw[first + 2]:4} {raw[first + 3]:4}   {dis.opname[raw[first + 2]]}")
print(f"    together they say {(raw[first + 1] << 8) | raw[first + 3]}")

for one in dis.get_instructions(wide):
    if one.arg is not None and one.arg > 255:
        print(f"  and dis prints it as       {one.opname} {one.arg} at offset {one.offset}")
        break
""",
    differs="On 3.14 the first EXTENDED_ARG is at offset 1028 rather than 1030, and the "
    "opcode numbers in the two words are 69 and 112 rather than 67 and 111. The count is 44 "
    "on both, and so is the argument the pair produces.",
)


lesson.md(f"""
Forty four of them in one function, all so that a one byte field can address three hundred locals.

This is also why an offset in a disassembly is not a count of instructions and never was. Adding a local somewhere near the top can push an argument over 255, which inserts a word, which moves everything after it.

## The instructions that can never be fetched

Two kinds of thing in the tables are not instructions the interpreter will ever fetch, and they are excluded in two completely different ways.

The first kind is a real opcode with a body that refuses to run. `CACHE` is opcode zero and its body is two lines, an assertion and `Py_FatalError("Executing a cache.")`, {cite("Python/bytecodes.c:6100-6103@v3.15.0rc1#CACHE")}. `RESERVED` is the same idea, {cite("Python/bytecodes.c:6105-6108@v3.15.0rc1#RESERVED")}. Reaching either means the walk lost its place, and the interpreter would rather stop than carry on wrong.

The second kind is stronger. A {term("pseudo instruction", "pseudo instruction")} is something the compiler uses while it is still working and resolves before it emits anything, like `JUMP` before it knows which direction, or `SETUP_FINALLY` before there is an exception table. These get numbers above 255, {cite("Include/opcode_ids.h:245-261@v3.15.0rc1#MIN_INSTRUMENTED_OPCODE")}, and one byte cannot hold a number above 255. There is a macro listing them, {cite("Include/internal/pycore_opcode_metadata.h:20-32@v3.15.0rc1#IS_PSEUDO_INSTR")}, and a constant for the highest number that can appear in real bytecode, {cite("Include/internal/pycore_opcode_utils.h:11-15@v3.15.0rc1#MAX_REAL_OPCODE")}.

{figure("numbers-that-cannot-fit", "the four ranges of opcode numbers and which of them can appear in a code object")}

That is a nice piece of design. A pseudo instruction leaking into a code object is not caught by a check that somebody has to remember to write. It is caught by arithmetic.

{lesson.claim("pseudo instructions are numbered above 255 so that they cannot fit in the one byte opcode field of a code unit")}
""")


lesson.code(
    """
import opcode

instrumented = [
    (number, name)
    for number, name in enumerate(dis.opname)
    if opcode.MIN_INSTRUMENTED_OPCODE <= number < 256 and not name.startswith("<")
]
pseudo = sorted((number, name) for name, number in opcode.opmap.items() if number > 255)
cache_number = opcode.opmap["CACHE"]

print("  the biggest number one byte holds     255")
print(f"  where the instrumented copies start   {opcode.MIN_INSTRUMENTED_OPCODE}")
print(f"  how many numbers that leaves for them {len(instrumented)}")
print(f"  the last two before the ceiling       {instrumented[-2][1]}, {instrumented[-1][1]}")
print()
print(f"  CACHE is opcode number                {cache_number}, and running one is fatal")
print(f"  numbers handed out above 255          {len(pseudo)}")
for number, name in pseudo:
    print(f"    {number}  {name}")
""",
    differs="On 3.14 the instrumented copies start at 234 rather than 233, there are 22 of "
    "them rather than 23, and the last two are INSTRUMENTED_LINE and ENTER_EXECUTOR. 3.15 "
    "added TRACE_RECORD at 255, which is the tier two trace recorder. The eleven pseudo "
    "instructions and their numbers are identical on both.",
)


lesson.md(f"""
Eleven names that exist for the compiler and stop existing before the bytecode does.

## Three ways to say go to the next instruction

Now the jump. In the definitions it is one word, `DISPATCH()`, and in the generated eval loop it is one word too. What that word becomes depends entirely on how CPython was built, and there are three answers.

The plain one is a switch. `TARGET(op)` becomes `case op:` and the jump goes back to the top of the switch, {cite("Python/ceval_macros.h:138-145@v3.15.0rc1#TARGET")}. Correct everywhere, and every instruction shares one branch, which the processor's branch predictor has no chance of guessing.

The usual one is a {term("computed goto", "computed goto")}, a compiler extension where a label is a value you can store, {cite("Python/ceval_macros.h:128-137@v3.15.0rc1#USE_COMPUTED_GOTOS")}. There is a generated file that is nothing but an array of 256 label addresses, {cite("Python/opcode_targets.h:1-12@v3.15.0rc1")}, and the jump becomes `goto *opcode_targets[opcode]`. Now every instruction ends with its own branch, so the predictor gets one pattern per instruction instead of one hopeless one for all of them.

The newest one gives each instruction its own function and makes the jump a guaranteed tail call, {cite("Python/ceval_macros.h:82-97@v3.15.0rc1#Py_MUSTTAIL")}. `TARGET(op)` becomes a whole function definition and `DISPATCH_GOTO()` becomes a mandatory tail call through a table of function pointers. Same shape, same table, and compilers optimise a page sized function better than a thirteen thousand line one.

{figure("three-ways-to-jump", "the same generated case under the three dispatch strategies")}

Going through a table variable rather than a fixed table buys something else. There is a second table where all 256 entries point at the same handler, and switching to it is a single pointer assignment, {cite("Python/ceval_macros.h:147-157@v3.15.0rc1#ENTER_TRACING")}. One store, and every instruction in the program is now routed to the trace recorder.

The build settings that decide all this are recorded, so you can ask your own install which one it got. The answers here are per install rather than per version, so yours may well differ from both of the ones this lesson was checked on.

{lesson.claim("which of the three dispatch strategies a CPython was built with is recorded in its build configuration and can differ between two installs of the same version")}
""")


lesson.code(
    """
import sysconfig

for name in ["HAVE_COMPUTED_GOTOS", "USE_COMPUTED_GOTOS", "Py_TAIL_CALL_INTERP"]:
    print(f"  {name:22} {sysconfig.get_config_var(name)}")
""",
    varies="These are properties of the build, not of the version, so any of the three can "
    "read differently for you. On the two builds this lesson was checked against, the 3.14 "
    "one has Py_TAIL_CALL_INTERP set to 1 and the 3.15 one leaves it unset. A None means the "
    "setting was not recorded, which is the same as off. In a browser, where this is a "
    "WebAssembly build, all three read 0.",
)


lesson.md(f"""
The lesson to take from that cell is that the choice is invisible from Python. The definitions in `Python/bytecodes.c` say nothing about dispatch, the semantics are identical under all three, and which one you have is decided by a compiler flag you did not choose.

If you are reading this in Colab or anywhere else in a browser, all three read 0, because a WebAssembly build has no computed gotos to have. That interpreter really is the plain switch, and every cell above it gave the same answer as everywhere else.

## The stream you disassemble is not the one that runs

One last thing, and it undoes something the whole lesson has been leaning on.

`code.co_code` is not stored. It is built on demand, and it is built by walking the real instructions, replacing every {term("specialization", "specialized")} opcode with the base one it came from, and zeroing every cache word, {cite("Objects/codeobject.c:2201-2215@v3.15.0rc1#deopt_code")}. What you get back is what the compiler produced, which is useful precisely because it is stable.

The bytes actually being executed are reachable too, under `_co_code_adaptive`, the underscore being a fair warning. Run a function enough times and the two stop matching.

{lesson.claim("co_code is reconstructed from the running bytecode by undoing specialization and zeroing caches, so it differs from _co_code_adaptive once an instruction has specialized")}
""")


lesson.code(
    """
for _ in range(200):
    add(1, 2)

plain = code.co_code
live = code._co_code_adaptive

print(f"  same number of bytes  {len(plain) == len(live)}")
print(f"  identical bytes       {plain == live}")
print()
offset = 0
while offset < len(plain):
    name = dis.opname[plain[offset]]
    running = dis.opname[live[offset]]
    marker = "->" if name != running else "  "
    print(f"  {offset:3} {marker} {name:36} {running}")
    offset += 2 + 2 * dis._inline_cache_entries.get(name, 0)
""",
    differs="On 3.14 the offsets are 0, 2, 4, 16, 18, 20 rather than 0, 4, 6, 18, 20, 22. "
    "The four names and the two substitutions are the same on both.",
)


lesson.md("""
Same length, different bytes. `RESUME` is running as `RESUME_CHECK` and `BINARY_OP` is running as `BINARY_OP_ADD_INT`, because this function has only ever been shown two ints.

The length is the same because a specialized instruction is a swap rather than an insertion. It has the same number, the same size and the same cache layout as the base it replaced, which is what the family declaration in E01 was guaranteeing. That is why the interpreter can rewrite an instruction while a pointer is sitting in the middle of the array.

## Try it yourself

Three things to poke at.

The first is to break the walk on purpose. Take the `walk` function above and delete the line that skips cache slots, then run it on `add`. You will get names like `CACHE` and, on a function with a specialized instruction, whatever opcode number happens to be sitting in a cache word. Nothing raises. That is the failure mode the interpreter's fatal error exists to turn into a crash instead.

The second is to find the biggest gap. Walk `dis.get_instructions` over a function that calls something, subtract each offset from the next, and see which instruction claims the most room. Then look up the same name in `dis._inline_cache_entries` and confirm the gap is two plus twice that.

The third is about `_co_code_adaptive`. Write a function that adds its two arguments, call it two hundred times with ints, and check the adaptive bytes. Then call it once with two strings and check again. Watch what the specialized instruction turns back into, and how many calls with strings it takes.

## What just happened

A code object is a flat array of sixteen bit words, and a word has three possible readings: an opcode with an argument, a cache slot, or a countdown counter. Nothing in the word says which, so the array can only be read from the start.

Fetching is one sixteen bit load and two field reads out of a union. Moving on is one word plus two bytes for every cache slot the instruction declares. Writing that walk in twelve lines of Python reproduces `dis.get_instructions` exactly.

The interpreter never stops on a cache slot, and opcode tracing shows it: a gap of twelve where `BINARY_OP` and its five slots are, and gaps of two everywhere else.

An argument over 255 arrives as an `EXTENDED_ARG` in front, which shifts its own argument left by eight and jumps straight to the next opcode without going back round the loop. Three hundred locals need forty four of them.

Two things in the opcode tables can never be fetched. `CACHE` and `RESERVED` are real opcodes whose bodies call `Py_FatalError`. Pseudo instructions are numbered above 255, so a one byte field physically cannot hold them.

`DISPATCH()` compiles to one of three things depending on a build flag: a switch, a computed goto through a table of labels, or a guaranteed tail call through a table of function pointers. Because it goes through a table variable, swapping that variable reroutes every opcode at once.

And `co_code` is a reconstruction. It undoes specialization and zeroes the caches. The bytes running are in `_co_code_adaptive`, and after two hundred calls they are not the same bytes.

## What is next

E03 is the frame: the thing the pointer in this lesson is pointing into, where the local variables live, and why a Python function calling another Python function costs zero bytes of C stack while the same call going through a C function costs about a kilobyte. That gap is measurable from a notebook, and it explains both why deep Python recursion is fine and why deep recursion through `sorted` is not.

After that comes the tail call interpreter, which is the third answer in the dispatch cell above. It only makes sense once you know what state the interpreter is carrying, because the entire point of it is keeping that state in registers.
""")


raise SystemExit(lesson.save())
