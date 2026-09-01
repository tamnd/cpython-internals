#!/usr/bin/env python
"""E01. The interpreter nobody wrote by hand.

The first lesson of the interpreter part, and the one that sets up every lesson after it.

`Python/bytecodes.c` is not C. It is a small language that looks like C, and a set of scripts
under `Tools/cases_generator` compiles it into the tier one eval loop, the tier two
interpreter, the optimizer cases and every metadata table on both sides of the C boundary.
Six thousand seven hundred lines in, just under fifty thousand out.

The reason to teach this first is that it makes the rest tractable. You do not read the eval
loop, you read the definitions it was built from. And you can check the whole claim from a
plain install, because the smallest of the generated files is `Lib/_opcode_metadata.py` and it
is sitting in your standard library with `Do not edit!` on line four.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("e01-the-interpreter-nobody-wrote", "e01")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("e01-the-interpreter-nobody-wrote").figure


lesson.md(f"""
# E01. The interpreter nobody wrote by hand

{badge}

The {term("eval loop", "eval loop")} is the biggest function in CPython. It is a switch with a case for every {term("opcode", "opcode")}, thirteen thousand lines of C, and it is the part of the source people mean when they say the interpreter.

Nobody typed it.

It is generated, every release, from a file of instruction definitions written in a small language of its own. That file is six thousand seven hundred lines long and it produces seven others, one of which is already installed on your machine.

{figure("where-the-interpreter-comes-from", "four steps from an instruction definition to a compiled eval loop")}

This lesson is about that arrangement, because everything in this part of the book depends on it. You do not read the eval loop. You read what it was built from.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/bytecodes.c:477-482@v3.15.0rc1#UNARY_NOT`.

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

Everything below was checked against the version this cell prints and against 3.14. Several cells differ between the two, and each one says so where it appears. That is not an accident in this lesson. The whole point of generating these files is that they are allowed to change, and they do.
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
## The file on your machine that says do not edit

Start with the evidence, because it does not need a CPython checkout. Your standard library contains a module called `_opcode_metadata`. It is where `dis` gets its opcode numbers from, and its first four lines name the script that wrote it and the file it was written from.

Those four lines are not written by hand either. One function in the generator emits them into every file it produces, {cite("Tools/cases_generator/generators_common.py:66-75@v3.15.0rc1#write_header")}, which makes the banner a reliable way to tell a {term("generated file", "generated file")} from a written one anywhere in the tree.

{lesson.claim("Lib/_opcode_metadata.py ships with every CPython install, and its first four lines say which script generated it and from which file")}
""")


lesson.code(
    """
import _opcode_metadata
import inspect
import pathlib

source = inspect.getsource(_opcode_metadata)
lines = source.splitlines()

print(f"  the file    {pathlib.PurePath(_opcode_metadata.__file__).name}")
for line in lines[:4]:
    print(f"  {line}")
print(f"  lines in it {len(lines)}")
""",
    differs="On 3.14 the last line reads 371 rather than 387. The banner is identical, "
    "because it is the same generator writing it, but what comes after it grew.",
)


lesson.md(f"""
That is the whole argument in one cell. A file in your standard library, saying where it came from.

The build rule that makes it is two lines of the makefile, {cite("Makefile.pre.in:2224-2228@v3.15.0rc1#py_metadata_generator")}. The rule that makes the eval loop is the same shape, {cite("Makefile.pre.in:2230-2234@v3.15.0rc1#tier1_generator")}. There are a dozen of these and `make regen-all` runs all of them.

## One instruction, before and after

Here is the source of `UNARY_NOT`, which is the instruction behind `not x`, {cite("Python/bytecodes.c:477-482@v3.15.0rc1#UNARY_NOT")}.

```c
inst(UNARY_NOT, (value -- res)) {{
    assert(PyStackRef_BoolCheck(value));
    res = PyStackRef_IsFalse(value)
        ? PyStackRef_True : PyStackRef_False;
    DEAD(value);
}}
```

The body is ordinary C. The first line is not. `inst` is not a macro and `(value -- res)` is not an expression. It is a declaration in the {term("instruction DSL", "instruction DSL")}, and it says: this instruction is called `UNARY_NOT`, it takes one value off the stack, and it leaves one behind.

{figure("what-one-definition-carries", "the three parts of an instruction definition, the kind, the name and the stack arrow")}

Six lines. Here is what the generator turns them into, {cite("Python/generated_cases.c.h:12726-12742@v3.15.0rc1#UNARY_NOT")}.

```c
TARGET(UNARY_NOT) {{
    #if _Py_TAIL_CALL_INTERP
    int opcode = UNARY_NOT;
    (void)(opcode);
    #endif
    frame->instr_ptr = next_instr;
    next_instr += 1;
    INSTRUCTION_STATS(UNARY_NOT);
    _PyStackRef value;
    _PyStackRef res;
    value = stack_pointer[-1];
    assert(PyStackRef_BoolCheck(value));
    res = PyStackRef_IsFalse(value)
    ? PyStackRef_True : PyStackRef_False;
    stack_pointer[-1] = res;
    DISPATCH();
}}
```

Three of those lines are the ones a person wrote. Everything else is the arrow being cashed in: declaring the local variables, reading `value` off the top of the stack, writing `res` back, moving the instruction pointer, and dispatching to whatever is next.

The same three lines turn up again in four more places, in the {term("tier two", "tier two")} interpreter, {cite("Python/executor_cases.c.h:2729-2744@v3.15.0rc1#_UNARY_NOT_r01")}. Those four are the same instruction written for four different arrangements of values held in registers rather than on the stack, {cite("Include/internal/pycore_uop_ids.h:1430-1433@v3.15.0rc1#_UNARY_NOT_r01")}. The definition says nothing about registers. Nobody typed any of them.

{lesson.claim("the six line definition of UNARY_NOT becomes a seventeen line case in the generated eval loop plus four more in the tier two interpreter, and only three lines were written by a person", unobservable="the generated C is not shipped in an install, so it is quoted from the pinned tree rather than measured here")}

## The arrow is the stack effect

The arrow is worth dwelling on, because it is the piece that earns its keep.

Count the names before the `--`, count the names after it, subtract. That number is the {term("stack effect", "stack effect")}, and it is what the compiler adds up to work out how much stack a function needs. It is not stored anywhere as a number somebody chose. It is read off the arrow.

`_opcode.stack_effect` is that number, reaching the same table the interpreter was built from. The arrows below are copied out of the definitions in the pinned source, and the cell works out what they imply and checks it.

{figure("the-arrow-is-the-stack-effect", "five stack arrows with the number each one implies")}

{lesson.claim("the stack effect of an instruction is the count of names after the arrow minus the count before it, and _opcode.stack_effect agrees")}
""")


lesson.code(
    """
import _opcode
import opcode

ARROWS = {
    "POP_TOP": "value --",
    "PUSH_NULL": "-- res",
    "UNARY_NOT": "value -- res",
    "GET_LEN": "obj -- obj, len",
    "END_SEND": "receiver, index_or_null, value -- val",
}


def names(side):
    return len([piece for piece in side.split(",") if piece.strip()])


for name, arrow in ARROWS.items():
    takes, leaves = arrow.split("--")
    from_arrow = names(leaves) - names(takes)
    number = opcode.opmap[name]
    oparg = 1 if number >= opcode.HAVE_ARGUMENT else None
    measured = _opcode.stack_effect(number, oparg)
    print(f"  {arrow:40} {from_arrow:3} {measured:3}   agrees {from_arrow == measured}")
""",
    differs="On 3.14 the last row disagrees. END_SEND was defined there as "
    "`(receiver, value -- val)`, with no index, so the arrow above is right for 3.15 and "
    "wrong for 3.14. That is the point rather than a problem, and the next paragraph is about it.",
)


lesson.md(f"""
On 3.15 every row agrees. On 3.14 the last one does not, because `END_SEND` gained a value between the two releases and the arrow copied above is the newer one.

That is a small demonstration of the thing this whole project is built around. The arrow is the source of truth. A copy of it in a notebook is right until it is not, and nothing tells you when it stops being right. Asking the interpreter is the only version that keeps working.

Two of the definitions have arrows that cannot be counted this way. `BUILD_TUPLE` is written `(values[oparg] -- tup)`, which means it takes as many values as the argument says, so its effect depends on the argument and `stack_effect` needs to be told what the argument is. That is why the call takes one.

## The families are declared, not tabulated

The next thing the language carries is which instructions are faster versions of which. A {term("specialization family", "family")} is one declaration, {cite("Python/bytecodes.c:484-491@v3.15.0rc1#family")}.

```c
family(TO_BOOL, INLINE_CACHE_ENTRIES_TO_BOOL) = {{
    TO_BOOL_ALWAYS_TRUE,
    TO_BOOL_BOOL,
    TO_BOOL_INT,
    TO_BOOL_LIST,
    TO_BOOL_NONE,
    TO_BOOL_STR,
}};
```

Six lines of names. One generator walks the families and writes them into the Python side as a dict, {cite("Tools/cases_generator/py_metadata_generator.py:32-43@v3.15.0rc1#generate_specializations")}, and that dict is what `opcode._specializations` is.

{lesson.claim("opcode._specializations is the family declarations from Python/bytecodes.c, with one entry per family and one name per member")}
""")


lesson.code("""
print(f"  the TO_BOOL family has {len(opcode._specializations['TO_BOOL'])} members")
for member in opcode._specializations["TO_BOOL"]:
    print(f"    {member}")
""")


lesson.md(f"""
The same six names, in the same order, read out of a file that shipped with your interpreter.

Here is every family, with how many members it has and how much scratch space the base instruction carries. The second number is the next section.

{lesson.claim("the number of families and the number of specialized opcodes are both properties of this build, and both changed between 3.14 and 3.15")}
""")


lesson.code(
    """
import dis

print(f"  families in this build  {len(opcode._specializations)}")
print(f"  specialized opcodes     {len(opcode._specialized_opmap)}")
print()
for name, members in opcode._specializations.items():
    slots = dis._inline_cache_entries.get(name, 0)
    print(f"  {name:18} {len(members):3} members   cache slots {slots}")
""",
    differs="On 3.14 this reads 17 families and 84 specialized opcodes rather than 18 and 91. "
    "LOAD_CONST had a family there and no longer does, GET_ITER and CALL_FUNCTION_EX have one "
    "now and did not, and several families changed size.",
)


lesson.md(f"""
Eighteen families covering ninety one opcodes, none of which anybody listed by hand.

## Where the cache slots come from

The second column is the other thing the language counts for you.

Specialization needs somewhere to keep its notes, and that somewhere is a run of empty instruction slots directly after the instruction, which is what an {term("inline cache", "inline cache")} is. How many slots is written in the definition as well. `TO_BOOL` is assembled from three pieces, {cite("Python/bytecodes.c:493-512@v3.15.0rc1#_SPECIALIZE_TO_BOOL")}:

```c
macro(TO_BOOL) = _SPECIALIZE_TO_BOOL + unused/2 + _TO_BOOL;
```

The first piece declares `counter/1`, meaning one slot called `counter`, and the middle piece reserves two more that nothing uses yet. One plus two is three. The generator adds them up and writes the total into a C table, {cite("Include/internal/pycore_opcode_metadata.h:1822-1845@v3.15.0rc1#_PyOpcode_Caches")}, which is what the compiler reads when it lays out the bytecode.

`dis` has the same numbers, and it uses them to know how many slots to skip when it walks a code object.

{lesson.claim("the cache slots after an instruction are the numbered slots in its definition added up, and dis reports the same totals the C table holds")}
""")


lesson.code(
    """
for name in ["TO_BOOL", "BINARY_OP", "LOAD_GLOBAL", "LOAD_ATTR"]:
    layout = ", ".join(f"{slot}={size}" for slot, size in opcode._cache_format[name].items())
    print(f"  {name:12} {dis._inline_cache_entries[name]} slots   {layout}")
print()
print(f"  instructions with a cache at all  {len(dis._inline_cache_entries)}")
""",
    differs="On 3.14 the last number is 19 rather than 22. The four layouts above are the same "
    "on both.",
)


lesson.md(f"""
`TO_BOOL` reads `counter=1, version=2`, which is the macro line above with the two unused slots given the name they were reserved for.

The good part is that you can check the whole arrangement against a real function, because if these numbers were wrong the disassembler would fall out of step with the bytecode and produce nonsense. Every instruction is two bytes, plus two more for each cache slot, so the totals have to add up to the exact length of the compiled code.

{lesson.claim("every instruction is two bytes plus two per cache slot, so the declared sizes add up to the exact length of a code object")}
""")


lesson.code(
    """
def sample(items, key):
    total = 0
    for item in items:
        total += item.count * 2
    return total > len(key)


code = sample.__code__
declared = 0
for instruction in dis.get_instructions(code):
    declared += 2 + 2 * dis._inline_cache_entries.get(instruction.opname, 0)

print(f"  real instructions in it        {sum(1 for _ in dis.get_instructions(code))}")
print(f"  bytes the declared sizes need  {declared}")
print(f"  bytes the code object has      {len(code.co_code)}")
print(f"  agrees                         {declared == len(code.co_code)}")
""",
    differs="On 3.14 the same function compiles to 102 bytes rather than 106, from the same "
    "22 instructions. The last line reads True on both.",
)


lesson.md(f"""
Exact, with nothing left over. That is a real check of the generated cache table against real compiled bytecode, done from Python, with no build of CPython involved.

## Where the opcode numbers come from

One more piece and the picture is complete. The numbers themselves.

`Lib/opcode.py` is a thin wrapper. It imports two maps from the generated module and builds `opname` by dropping every name into the slot its number points at, {cite("Lib/opcode.py:16-23@v3.15.0rc1#_specialized_opmap")}. Where no name lands, it leaves a placeholder.

That is eight lines of real code, and it means `dis.opname` can be rebuilt from scratch in the notebook. If the rebuild matches, there is nothing else feeding it.

{lesson.claim("dis.opname is built entirely from opmap and _specialized_opmap in the generated module, and rebuilding it the same way gives an identical list")}
""")


lesson.code(
    """
rebuilt = [f"<{number}>" for number in range(max(opcode.opmap.values()) + 1)]
for table in (opcode.opmap, opcode._specialized_opmap):
    for name, number in table.items():
        rebuilt[number] = name

unused = [name for name in rebuilt if name.startswith("<")]

print(f"  base opcodes from the file  {len(opcode.opmap)}")
print(f"  specialized ones from it    {len(opcode._specialized_opmap)}")
print(f"  slots in dis.opname         {len(dis.opname)}")
print(f"  of those, unused numbers    {len(unused)}")
print(f"  the rebuild matches dis     {rebuilt == list(dis.opname)}")
""",
    differs="On 3.14 there are 84 specialized opcodes and 29 unused numbers rather than 91 "
    "and 22. The base count and the total are the same on both, so the seven new "
    "specializations came out of the spare numbers.",
)


lesson.md(f"""
The gaps are numbers nothing is using in this build. They are what the next specialization gets allocated out of, which is exactly what happened between these two releases.

Notice what this means for anything you write against `dis`. A specialized opcode number is not stable across releases and was never promised to be. The name is what you should hold on to.

## The two tables still written by hand

It would be neat to say all of it is generated. It is not, and the exceptions are worth knowing because they are where the mistakes live.

The cache layout you saw above is one of them. `opcode._cache_format` is typed out in `Lib/opcode.py`, {cite("Lib/opcode.py:52-62@v3.15.0rc1#_cache_format")}, and the totals it produces have to match the generated C table or `dis` misreads bytecode. Nothing makes them match. Someone keeps them in step.

The other is the list of constants the compiler is allowed to load by index instead of by name, and it comes with a note, {cite("Lib/opcode.py:42-47@v3.15.0rc1#_common_constants")}: append only, must match a list in a C header. A comment asking a future person to remember something is the exact thing the generators exist to remove.

{figure("generated-against-written-by-hand", "what the generators produce against the two tables still typed by a person")}

{lesson.claim("the list of common constants is written by hand in Lib/opcode.py and grew from five entries to twelve between 3.14 and 3.15")}
""")


lesson.code(
    """
labels = [getattr(item, "__name__", repr(item)) for item in opcode._common_constants]

print(f"  entries in this build  {len(labels)}")
for label in labels:
    print(f"    {label}")
""",
    differs="On 3.14 there are 5 of these rather than 12, ending at any. The seven after it "
    "were added in one release, in two places that have to agree with each other.",
)


lesson.md(f"""
Twelve on 3.15, five on 3.14. Seven added in one release, in two files, by hand, with only a comment holding them together.

{figure("one-file-many-outputs", "seven generated files with what each one holds and how many lines it is")}

That table is what the six thousand seven hundred lines of definitions turn into, {cite("Tools/cases_generator/README.md:14-34@v3.15.0rc1")}. Just under fifty thousand lines out, and the last row is the one you have been reading from all lesson.

## Try it yourself

Three things to poke at.

The first is to read the file. `inspect.getsource(_opcode_metadata)` gives you all of it and it is under four hundred lines. Look at the shape of `_specializations` and then run the same thing on 3.14 if you have it. The contents changed, and so did the container: 3.15 writes tuples inside a `frozendict` where 3.14 wrote lists inside a plain dict. Nothing announced that, because it is a build artefact rather than an interface.

The second is to find the other hand written mirror. Search your standard library for `must match` and see how many comments turn up asking a person to keep two files in step. Each one is a place where a generator could have been.

The third is a counting exercise. There are more instructions carrying a cache than there are families, so some of them have nowhere to specialize into. Find them by comparing the keys of `dis._inline_cache_entries` with the keys of `opcode._specializations`, and then work out what a counter is doing on an instruction with no faster version to become.

## What just happened

The eval loop is generated. `Python/bytecodes.c` is six thousand seven hundred lines of a language that looks like C and is not, and `Tools/cases_generator` compiles it into seven files totalling just under fifty thousand lines.

Each definition opens with a line saying what kind of thing it is, what it is called, and what it takes off the stack and leaves behind. The body under that is ordinary C. The first line is what makes everything downstream possible.

The arrow is the stack effect. Count the names on each side and subtract, and `_opcode.stack_effect` gives the same number, because both come from the same place. When `END_SEND` gained a value between 3.14 and 3.15, the arrow changed and every table changed with it.

Families are declared in one place and expanded into the tables on both sides of the C boundary. Cache sizes are added up from the numbered slots in the definition, and they match the compiled bytecode to the byte.

`dis.opname` is nothing but the two maps from the generated module, dropped into an array by number. Rebuilding it by hand gives an identical list.

And two tables are still typed by a person: the cache layout in `Lib/opcode.py` and the common constants list, which grew from five entries to twelve in one release with a comment as its only safety net.

## What is next

E02 is dispatch: what happens between the end of one instruction and the start of the next, and why that `DISPATCH()` at the bottom of the generated case is not a jump back to the top of a loop.

The generated file you have been reading from is going to keep coming up. Every lesson in this part reads the definitions rather than the loop, because the definitions are shorter, they are the thing that was actually written, and they are the only version that cannot be out of date.
""")


raise SystemExit(lesson.save())
