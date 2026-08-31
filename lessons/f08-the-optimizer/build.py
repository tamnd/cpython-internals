#!/usr/bin/env python
"""F08. The optimizer.

The eighth lesson of the front end part, and the twenty second overall. F07 built the graph and
showed the two questions it makes easy. This one is what runs in the middle, between building
the graph and flattening it.

The angle is that there is nothing clever in here. Every rewrite is small, local and cautious,
and most of them have a hard number in them that somebody chose and wrote down: four size
limits on folding, a copy budget of four instructions, and an operand that has to fit in four
bits. All of those numbers are visible from Python if you know where to push.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("f08-the-optimizer", "f08")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("f08-the-optimizer").figure


lesson.md(f"""
# F08. The optimizer

{badge}

Write `2 ** 64` in a Python file and the compiler works it out for you. The multiply never happens at runtime, and the twenty digit answer sits in the file as a constant.

Write `2 ** 65` and it does not. The 2, the 65 and the power all survive into the bytecode, and your program does the arithmetic every time that line runs.

The difference is one number, `128`, written down in a header near the top of the folding code. That is what this pass is like all the way through. It is not a clever compiler working out what your program means. It is a short list of small rewrites, each with a rule you can read, and several of the rules are just a number somebody picked.

{figure("folded-or-not", "a table of four expressions, whether each one is folded, and why")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/flowgraph.c:1760-1763@v3.15.0rc1`.

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

Everything below was checked against the version this cell prints and against 3.14. Where the two disagree, the lesson says so.
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
## Arithmetic the compiler does for you

{term("constant folding", "Constant folding")} is the first thing the optimizer does that you can see from outside. If both sides of an operator are constants, work it out now and put the answer in the file.

It is worth being clear about where this happens, because it moved. There used to be a separate pass over the tree that folded constants before any instruction existed. That file is gone, and all of it happens here, on the graph, after the code generator has already emitted a load, a load and an operator. The optimizer replaces the three with one.

The reason for a limit is easy to see once you think about the file rather than the program. `2 ** 200000` is a number with sixty thousand digits. Folding it would put sixty thousand digits into the compiled file, make it slower to import, and save one multiply. So there are four limits, {cite("Python/flowgraph.c:1760-1763@v3.15.0rc1")}, and they are four `#define` lines with a comment each.

{figure("four-numbers", "the four size limits on constant folding and what each one stops")}

{lesson.claim("whether an expression is folded depends on how big the answer would be, and the boundary is exact")}
""")


lesson.code("""
import dis

ARITHMETIC = {one for one in dis.opmap if one.startswith(("BINARY", "UNARY"))}


def is_folded(expression):
    \"\"\"Did the compiler work this out, or is there arithmetic left in the bytecode?\"\"\"
    code = compile("x = " + expression, "<here>", "exec")
    return not any(one.opname in ARITHMETIC for one in dis.get_instructions(code))


TRIALS = (
    "12345678 * 98765432",
    "2 ** 64",
    "2 ** 65",
    "1 << 127",
    "1 << 128",
    "'ab' * 2048",
    "'ab' * 2049",
    "(1, 2) * 128",
    "(1, 2) * 129",
)

for expression in TRIALS:
    print(f"  {expression:22} folded {is_folded(expression)}")
""")


lesson.md(f"""
Every boundary is exactly on the number. `'ab' * 2048` is four thousand and ninety six characters and it folds. One more repeat and it does not. `(1, 2) * 128` is two hundred and fifty six items and it folds, and one more does not.

The integer ones are a little different, because the compiler does not work the answer out and then measure it. That would mean doing the expensive thing first. Instead it estimates: {cite("Python/flowgraph.c:1810-1828@v3.15.0rc1#const_folding_safe_power")} multiplies the bit length of the base by the exponent and refuses if the estimate is over 128. For `2 ** 64` that is exactly 128, and for `2 ** 65` it is 130.

The comment above the collection check, {cite("Python/flowgraph.c:1740-1745@v3.15.0rc1#const_folding_check_complexity")}, gives the other reason to stop: constants which are slow to hash.

## The constant that never leaves

Fold `1000 * 1000` and the two thousands have nothing loading them any more. There is a pass for exactly that, {cite("Python/flowgraph.c:3261-3293@v3.15.0rc1#remove_unused_consts")}. It walks every instruction, marks the constant slots that are used, and drops the rest.

Except for one. {lesson.claim("a leftover constant survives if it happened to land in the first slot, and is removed otherwise")}
""")


lesson.code(
    """
SOURCES = {
    "no docstring": "x = 1000 * 1000\\n",
    "a docstring first": '\"\"\"A module.\"\"\"\\nx = 1000 * 1000\\n',
    "another constant first": "y = 'hello'\\nx = 1000 * 1000\\n",
}

for label, source in SOURCES.items():
    print(f"  {label:24} co_consts {compile(source, '<here>', 'exec').co_consts}")
""",
    differs=(
        "On 3.14 a module ends with a `LOAD_CONST None`, so `None` sits in the constants of all"
        " three and every tuple has one more entry. Which slot the leftover 1000 is in, and"
        " whether it survives, is the same on both."
    ),
)


lesson.md(f"""
The first line keeps a `1000` that nothing loads. The other two do not, and the only thing that changed is what got into slot zero first.

The reason is two lines of C and a comment: {cite("Python/flowgraph.c:3278-3282@v3.15.0rc1")}. The first constant may be the docstring, so it is always kept. A module or function docstring lives in `co_consts[0]` and is read from there by `__doc__` rather than loaded by any instruction, so a pass that only looks at instructions would throw it away. Keeping slot zero unconditionally is the simplest fix, and the price is an occasional stray number.

{figure("slot-zero-is-special", "why a leftover constant survives without a docstring and disappears with one")}

Add a docstring to a module and one integer disappears from the compiled file. That is a small thing, but it is the kind of small thing that tells you the compiler is made of ordinary decisions rather than magic.

## A jump you can delete by copying

Most of the optimizer is about jumps. Jumps that go to jumps get pointed at the final destination, {cite("Python/flowgraph.c:1276-1298@v3.15.0rc1#jump_thread")}, and blocks that end up empty or unreachable get removed. Those are the ones you would expect.

Here is one you might not. If a block ends in a plain jump to a small block that leaves the function, the jump is deleted and the target is copied in instead. The budget is four instructions, {cite("Python/flowgraph.c:1218-1219@v3.15.0rc1")}, and the conditions are on {cite("Python/flowgraph.c:1226-1240@v3.15.0rc1#basicblock_inline_small_or_no_lineno_blocks")}.

{lesson.claim("a small ending can be copied in place of a jump, so the same two instructions appear twice")}
""")


lesson.code(
    """
import dis

from pyxray import compiler

SOURCE = "def f(items):\\n    for one in items:\\n        if one:\\n            break\\n    return 1\\n"

emitted = compiler.innermost_codegen(SOURCE)
body = compile(SOURCE, "<here>", "exec").co_consts[0]
finished = list(dis.get_instructions(body))

emitted_jumps = sum(1 for one in emitted if "JUMP" in one.opname)
finished_jumps = sum(1 for one in finished if "JUMP" in one.opname)

print(f"  the generator emitted {len(emitted)} instructions, {emitted_jumps} of them jumps")
print(f"  the code object has    {len(finished)} instructions, {finished_jumps} of them jumps")
print()
dis.dis(body)
""",
    differs=(
        "On 3.14 the loop reads `items` with `LOAD_FAST_BORROW` and the `break` needs one fewer"
        " `POP_TOP`, so every count is one lower. The ending still appears twice, which is the"
        " point of the cell."
    ),
)


lesson.md(f"""
Look for `LOAD_SMALL_INT 1` followed by `RETURN_VALUE`. It is in there twice. The `break` used to jump to the end of the function, and the end of the function is two instructions long and leaves the scope, so the optimizer deleted the jump and wrote the ending out a second time.

The code got one instruction longer and one jump shorter, and that is the trade the pass is willing to make. A jump costs a branch the processor has to predict. Two extra instructions cost a few bytes.

{figure("copy-instead-of-jump", "the same ending reached by a jump, and the same ending copied in twice")}

The other change worth spotting is that `POP_JUMP_IF_FALSE` became `POP_JUMP_IF_TRUE` with the two sides swapped. The loop needs a backward jump at the bottom, so a separate pass turns the condition round to get one.

## Two instructions in one

Some pairs of instructions are common enough to be worth a single opcode. `LOAD_FAST` followed by `LOAD_FAST` becomes `LOAD_FAST_LOAD_FAST`, and the pass that does it, {cite("Python/flowgraph.c:2668-2698@v3.15.0rc1#insert_superinstructions")}, handles three pairs and nothing else.

The interesting part is the two conditions in {cite("Python/flowgraph.c:2652-2666@v3.15.0rc1#make_super_instruction")}. Both instructions have to be on the same line, and both operands have to be under 16, because the two slot numbers get packed into one operand byte with four bits each.

{figure("two-into-one", "the two conditions a pair of instructions has to meet to become one")}

{lesson.claim("a line break in the middle of an expression, or a sixteenth local variable, costs you a superinstruction")}
""")


lesson.code("""
import dis

NAMES = ", ".join(f"a{i}" for i in range(20))

SOURCES = {
    "a + b on one line": "def f(a, b):\\n    return a + b\\n",
    "a + b split over two": "def f(a, b):\\n    return (a\\n            + b)\\n",
    "two low slots, 0 and 1": f"def f({NAMES}):\\n    return a0 + a1\\n",
    "two high slots, 18 and 19": f"def f({NAMES}):\\n    return a18 + a19\\n",
}

for label, source in SOURCES.items():
    body = compile(source, "<here>", "exec").co_consts[0]
    loads = [one.opname for one in dis.get_instructions(body) if "LOAD_FAST" in one.opname]
    print(f"  {label:28} {loads}")
""")


lesson.md(f"""
Putting a line break between `a` and `b` costs you an instruction. So does using the nineteenth and twentieth parameters of a function instead of the first and second.

Neither of those is a rule anybody wrote down for you to follow. They fall out of an operand being one byte and of the line table needing one line per instruction. It is worth seeing once, and then worth forgetting, because writing Python around a four bit field is not a good use of anybody's afternoon.

The `_BORROW` in the output is a later pass again, {cite("Python/flowgraph.c:2857@v3.15.0rc1#optimize_load_fast")}, which works out that these values are only being read and do not need their reference counts touched. `STORE_FAST_STORE_FAST` survives under its own name if you unpack two values into two locals.

## Proving a local has a value

The last one is the only piece of real analysis in the pass, and it is the reason `UnboundLocalError` is not checked for on every single local read.

A `LOAD_FAST` does not check whether the slot has anything in it. It cannot, if it is going to be fast. So the compiler proves the slot is full: it walks the graph tracking which locals are definitely assigned on every path that reaches each block, {cite("Python/flowgraph.c:3362-3364@v3.15.0rc1#add_checks_for_loads_of_uninitialized_variables")}. Where the proof works, the plain instruction stays. Where it does not, the load is turned into `LOAD_FAST_CHECK`, which does test and raises if the slot is empty.

{lesson.claim("the same local, read twice in one function, can compile to a checked load and an unchecked one")}
""")


lesson.code("""
import dis

SOURCE = "def f(c):\\n    if c:\\n        x = 1\\n        print(x)\\n    return x\\n"

body = compile(SOURCE, "<here>", "exec").co_consts[0]
for one in dis.get_instructions(body):
    if one.opname.startswith("LOAD_FAST"):
        print(f"  line {one.line_number}  {one.opname:18} {one.argval}")
""")


lesson.md(f"""
Two reads of `x`, four lines apart, compiled differently. The one inside the `if` is on a path where the assignment above it definitely ran, so it needs no check. The `return x` can also be reached by skipping the whole `if`, so it gets one.

This is why F05's version of the story was only half of it. The symbol table decided `x` was a local, which is what makes an `UnboundLocalError` possible at all. The graph decided which reads actually need testing, which is what makes the error rare enough that most locals cost nothing.

{figure("proving-it-is-set", "the same name read twice, once provably assigned and once not")}

## Try it yourself

1. Find the smallest `n` where `10 ** n` is not folded, and check it against the bit length rule.
2. Fold something into a `float`. Does `1 / 3` get worked out at compile time? What about `1 / 0`?
3. Put a docstring on a function whose body starts with a folded expression, and watch the leftover constant disappear.
4. Write a function with three consecutive `LOAD_FAST` instructions. How many superinstructions do you get, and why not more?
5. Find a function where a `LOAD_FAST_CHECK` appears even though you can see by eye that the variable is always set.

## What just happened

The optimizer runs between building the graph and flattening it, and it is a list of small rewrites rather than anything that understands your program.

Constant folding happens on the graph, not on the tree, and it stops at four written down limits: 128 bits for an integer, 256 items for a collection, 4096 characters for a string, and 1024 items counting nested ones.

The pass that removes unused constants always keeps slot zero, because slot zero might be a docstring. That is why a leftover number sometimes stays in the file.

Jumps to jumps are pointed at the destination, and a jump to a short ending is deleted by copying the ending in. Four instructions is the budget.

Three pairs of instructions get merged into one, if they are on the same line and both operands fit in four bits.

Locals get an unchecked load where the compiler can prove the slot is full on every path in, and a checked one where it cannot. That proof is a walk over the graph, and it is the only real analysis in the whole pass.

## What is next

F09 is the {term("assembler")}. The graph gets flattened for the last time, labels turn into byte offsets, the {term("line table")} and the {term("exception table")} get built, and a {term("code object")} comes out the other end.
""")


raise SystemExit(lesson.save())
