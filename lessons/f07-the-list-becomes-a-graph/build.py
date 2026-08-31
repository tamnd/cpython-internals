#!/usr/bin/env python
"""F07. The list becomes a graph.

The seventh lesson of the front end part, and the twenty first overall. F06 ended with a flat
list of instructions and a promise that something later would clean it up. This is that
something, and the interesting part is not what it removes but what shape it works in.

The angle is that the fourth pass spends its whole life in a form the finished code object does
not keep. Blocks and edges exist for the length of one function call in the compiler and are
then flattened away, and the only evidence they were ever there is the exception table and a
bytecode order that is nobody's idea of source order.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

#: Three cells disassemble or measure the same try and except function, and 3.15 changed how the
#: constant None is loaded and how many entries the exception table needs. The wording is shared
#: so the notes cannot drift apart.
HANDLER_NOTE = (
    "On 3.14 the `None` in the handler is a `LOAD_CONST` rather than a `LOAD_COMMON_CONSTANT`,"
    " and the exception table has one fewer entry. The order of the blocks is the same."
)

lesson = Lesson("f07-the-list-becomes-a-graph", "f07")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("f07-the-list-becomes-a-graph").figure


lesson.md(f"""
# F07. The list becomes a graph

{badge}

Take a short function with a `try` in it and disassemble it. The line numbers do not count upwards. They go 5, then 8, then back to 6. The last line of the function is compiled before the middle of it.

Nothing has gone wrong. Somewhere between the code generator and the finished code object, the compiler stopped treating your program as a list of instructions and started treating it as a {term("control flow graph", "graph")}. As soon as it did, the order things were emitted in stopped meaning anything at all.

This is the fourth of the five passes. It builds a graph out of the flat list F06 produced, answers two questions that a list simply cannot answer, deletes everything nothing can reach, and then flattens the whole thing back down.

{figure("graph-then-list-again", "a pipeline showing a flat list becoming a graph of blocks and then a flat list again")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/flowgraph.c:41-76@v3.15.0rc1`.

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
## Where a block ends

A {term("basic block")} is a run of instructions you always enter at the top and always leave at the bottom. Nothing jumps into the middle of one, and nothing branches out of the middle. That is the whole definition, and it is useful because anything true at the top of a block is still true at the bottom.

Finding them in a flat list takes three rules. An instruction starts a block if it is the first one, if something jumps to it, or if the instruction before it was a jump or a return. Everything else just continues the block it is in.

{figure("where-a-block-ends", "a table of the three rules that decide where a basic block starts")}

The rules are short enough to write out in Python, and `dis` hands over everything they need. {lesson.claim("the three leader rules are enough to split real bytecode into blocks")}
""")


lesson.code(
    """
import dis


def biggest(items):
    best = items[0]
    for one in items:
        if one > best:
            best = one
    return best


stream = list(dis.get_instructions(biggest))

leaders = {0}
for i, one in enumerate(stream):
    if one.is_jump_target:
        leaders.add(i)
    if one.opcode in dis.hasjump or one.opname.startswith("RETURN"):
        leaders.add(i + 1)
starts = sorted(one for one in leaders if one < len(stream))

print(f"  {len(stream)} instructions fall into {len(starts)} blocks")
for n, start in enumerate(starts, 1):
    end = starts[n] if n < len(starts) else len(stream)
    print(f"    block {n}  {' '.join(one.opname for one in stream[start:end])}")
""",
    differs=(
        "On 3.14 the loop reads `items` with `LOAD_FAST_BORROW` at the end of the first block"
        " rather than `LOAD_FAST`. The blocks fall in exactly the same places."
    ),
)


lesson.md(f"""
Six blocks out of twenty one instructions. Block two is one instruction long, because `FOR_ITER` is jumped back to and also jumps forward, so it is a block all by itself.

CPython does not build blocks by scanning a finished list like this, because it never has one. The code generator emits into blocks from the start, and {cite("Python/flowgraph.c:3993@v3.15.0rc1#_PyCfg_FromInstructionSequence")} is where the sequence F06 produced is turned into the graph. Doing it the other way round, as above, is a good way to convince yourself the rules are the whole story.

Here is what one of those blocks is, in C, {cite("Python/flowgraph.c:41-76@v3.15.0rc1#basicblock")}. It is worth a slow read, because most of the fields are answers that earlier passes wrote down rather than anything to do with instructions.

{figure("what-a-block-carries", "the five fields of a basic block that the later passes actually read")}

The field to be careful about is `b_next`. The comment in the source says it out loud: `b_next` is the next block reached by normal control flow, and it is also the order the blocks sit in memory. The jump targets are somewhere else entirely, on the instructions. Confusing the two is the classic mistake when reading this file.

## The list has an order, the graph has edges

Once there are edges, the order the blocks happen to sit in is free to change, and it does. The clearest place to see it is a `try`.

{lesson.claim("in a function with a try, the compiled instructions are not in source order")}
""")


lesson.code(
    """
import dis


def careful(items):
    try:
        first = items[0]
    except IndexError:
        first = None
    return first


dis.dis(careful)
""",
    differs=HANDLER_NOTE,
)


lesson.md(f"""
Read the line numbers down the left. Line 5 is the body of the `try`. Then line 8, the `return first`, which is the last line of the function. Only after that does line 6 turn up, and the handler runs to the end.

The `--` markers are instructions that belong to no line, the same thing F06 ended on. `PUSH_EXC_INFO` is where the handler starts, and the three instructions at the very bottom are the cleanup that runs when the handler itself raises.

At the very bottom is the {term("exception table")}. It is a list of ranges: if something goes wrong between here and here, jump to there. That table is the closest thing to an edge that survives into the code object, and F11 is the lesson about it.

{figure("two-different-orders", "a comparison of the order blocks sit in memory and the order control flow visits them")}

## Blocks that nothing points at

F06 finished by emitting the dead branch of an `if False` in full and promising that something later would notice. Noticing is easy once there is a graph: walk out from the entry block, count how many ways there are into each block you reach, and anything you never arrive at has no way in.

That is exactly what {cite("Python/flowgraph.c:1008-1043@v3.15.0rc1#remove_unreachable")} does, and then {cite("Python/flowgraph.c:1046-1052@v3.15.0rc1")} empties every block whose count came out at zero.

{lesson.claim("the code generator emits code that can never run, and the graph pass deletes it")}
""")


lesson.code("""
import dis

from pyxray import compiler

PROGRAMS = (
    ("code written after a return", "def f():\\n    return 1\\n    print('never')\\n"),
    ("a loop whose test is always true", "def f():\\n    while True:\\n        pass\\n"),
    (
        "a branch that can never be taken",
        "def f(x):\\n    if False:\\n        return 1\\n    return 2\\n",
    ),
)

for label, source in PROGRAMS:
    emitted = compiler.innermost_codegen(source)
    body = compile(source, "<here>", "exec").co_consts[0]
    finished = list(dis.get_instructions(body))
    print(f"  {label}")
    print(f"      the generator emitted {len(emitted)}, the code object kept {len(finished)}")
    print(f"      what is left  {[one.opname for one in finished]}")
""")


lesson.md(f"""
The middle one is the nicest. `while True:` was emitted with a load of `True`, a `TO_BOOL` and a conditional jump, exactly as written. In the graph, the block that the jump would have skipped to has nothing pointing at it, so it goes, and with it the reason for the test. What is left is a `JUMP_BACKWARD` to itself and nothing else.

Note that none of this is the compiler being clever about your program. It never worked out that `True` is true. It emitted the test, the constant got folded, the jump became unconditional, and then a block ended up with no way in. Reachability did the rest.

## How deep the stack gets is a question about the graph

Every code object carries `co_stacksize`, and the frame it runs in reserves that many slots. Get it wrong and you do not get a slow program, you get a corrupted one, so the compiler has to be exactly right.

Each instruction has a known {term("stack effect")}, so the obvious way to work it out is to walk the list adding them up and remember the highest total. That works right up until the code has more than one path through it.

{lesson.claim("adding stack effects up along the flat list gets the right answer until there is a handler")}
""")


lesson.code("""
import dis


def flat(a, b, c, d):
    return a + b + c + d


def wide(a, b, c, d):
    return [a, b, c, d]


def nested(x):
    return int(str(abs(x)))


def straight_through(code):
    \"\"\"The deepest the stack gets, if you pretend the instructions run one after another.\"\"\"
    depth = high = 0
    for one in dis.get_instructions(code):
        arg = one.arg if one.opcode >= dis.HAVE_ARGUMENT else None
        depth = depth + dis.stack_effect(one.opcode, arg)
        high = max(high, depth)
    return high


for f in (flat, wide, nested, careful):
    real, in_order = f.__code__.co_stacksize, straight_through(f.__code__)
    print(f"  {f.__name__:8} co_stacksize {real}   adding up in order {in_order}")
""")


lesson.md(f"""
Three right and one wrong, and the wrong one is the function with the handler.

The reason is the `--` block from earlier. When an exception is raised, the interpreter pushes the exception onto the stack before jumping to the handler, so the handler block does not begin at whatever depth the instruction above it happened to leave. It begins one deeper, and no amount of reading the list in order will tell you that.

{figure("depth-is-a-path-question", "a comparison of walking the flat list and walking every path through the graph")}

{cite("Python/flowgraph.c:815-824@v3.15.0rc1#calculate_stackdepth")} does it properly. It writes a depth on each block as it arrives there, follows every edge out including the exception edges, and keeps the deepest it ever saw. The comment above the function is honest about the one assumption it makes: cycles in the graph are taken to have no net effect on the depth, which is true because a loop that grew the stack every time round would not be a loop you could run.

That answer is written into the block as `b_startdepth`, and the largest of them all becomes `co_stacksize`.

## Cold blocks go to the end

Now back to why the handler ended up after the return. It is a deliberate pass, {cite("Python/flowgraph.c:3492-3506@v3.15.0rc1#push_cold_blocks_to_end")}, and the reason is the CPU rather than anything about Python.

Instructions that sit next to each other get fetched together. Code that almost never runs, sitting in the middle of code that runs constantly, wastes room in the cache on every trip through. So the compiler marks exception handlers cold, {cite("Python/flowgraph.c:3442-3443@v3.15.0rc1#mark_cold")} spreads that mark to every block only a handler can reach, and everything cold is moved past the end.

{figure("cold-goes-last", "the four steps that move exception handlers to the end of the bytecode")}

Moving a block breaks anything that used to fall off the bottom of it into the block below, so the pass adds a real jump wherever that happened. The comment in the source says exactly that, and you can see the jump it added.

{lesson.claim("moving a cold block to the end leaves a jump behind where control used to fall through")}
""")


lesson.code(
    """
import dis


def two_returns(items):
    try:
        return items[0]
    except IndexError:
        pass
    print("recovering")
    return None


def line_order(code):
    \"\"\"The lines this code object touches, in bytecode order, with runs collapsed.\"\"\"
    out = []
    for one in dis.get_instructions(code):
        where = one.line_number if one.line_number is not None else "--"
        if not out or out[-1] != where:
            out.append(where)
    return out


for f in (careful, two_returns):
    print(f"  {f.__name__:14} lines, in bytecode order  {line_order(f.__code__)}")
print()
dis.dis(two_returns)
""",
    differs=HANDLER_NOTE,
)


lesson.md(f"""
`careful` goes 5, 8, then back to 6. `two_returns` keeps its lines in order, because its `try` block returns, so the two lines after the `except` can only be reached from the handler and are cold as well. Cold blocks stay in their own relative order when they are pushed out, so the tail follows the handler.

The `JUMP_FORWARD` in the disassembly, on the line with the `pass`, is the one the pass had to add. In the source the handler simply runs out and control carries on into the `print`. After the move those two are no longer next to each other, so falling through would land somewhere else entirely.

## And then it is a list again

The graph exists for the length of one call. {cite("Python/flowgraph.c:3759-3763@v3.15.0rc1")} sets it up, the optimizer runs in the middle, {cite("Python/flowgraph.c:3793-3800@v3.15.0rc1")} finishes the housekeeping, and then {cite("Python/flowgraph.c:4058@v3.15.0rc1#_PyCfg_ToInstructionSequence")} walks `b_next` from the entry block and writes every instruction out into one flat sequence again. The header, {cite("Include/internal/pycore_flowgraph.h:27-31@v3.15.0rc1")}, is four function declarations and that is the entire public surface of the pass.

{lesson.claim("nothing in the finished code object is a graph")}
""")


lesson.code(
    """
code = careful.__code__

print(f"  co_code            {len(code.co_code)} bytes, one flat run with no blocks in it")
print(f"  co_stacksize       {code.co_stacksize}, the answer, with none of the working shown")
print(f"  co_exceptiontable  {len(code.co_exceptiontable)} bytes, ranges rather than edges")
print(f"  co_linetable       {len(code.co_linetable)} bytes, and F11 is about that one")
print()
print(f"  co_branches()      {list(code.co_branches())}")
""",
    differs=(
        "The byte counts are a little different on 3.14, because the bytecode for this function"
        " changed, and so did the offsets `co_branches` reports."
    ),
)


lesson.md(f"""
Four sizes and a list of offsets. `co_branches` is the closest the code object comes to admitting there were ever branches, and it is a flat list of byte offsets kept for coverage tools rather than anything you could walk.

Everything else is gone. The blocks, the edges, the predecessor counts, the cold marks, all of it existed only while the pass was running. What is left is the bytes, one number that took a graph walk to work out, and a table of ranges.

That is why disassembling a function with a `try` looks so strange. You are reading the shadow of a graph that no longer exists.

## Try it yourself

1. Run the block splitter over a function with a `while` loop and one with a `try`. Which one produces a block whose first instruction is not a jump target?
2. Add `b_predecessors` to the splitter: for each block, count how many other blocks can reach it. Which block in `biggest` has two?
3. Write a function where `co_stacksize` is larger than the number of local variables, and one where it is smaller.
4. Put a `raise` inside an `if` and check whether the compiler marks that branch cold. Then put it inside an `except` and check again.
5. Take the `while True` example and add a `break`. Does the test come back?

## What just happened

The fourth pass turns the flat list from F06 into a graph of basic blocks. A block is a run of instructions with one way in and one way out, and three rules are enough to find them.

Once there is a graph, two questions get easy that were impossible before. Which code can never run is a reachability walk from the entry block. How deep the stack gets is the deepest path through the graph, which is not the same as adding the effects up in order the moment there is an exception handler.

Exception handlers are marked {term("cold block", "cold")} and pushed past the end of the function, so that the code you actually run stays packed together. Where a cold block used to fall through to a warm one, the pass leaves an explicit jump behind.

Then the graph is flattened back into a list and thrown away. The code object holds bytes, a stack size and an exception table, and none of those is a graph.

## What is next

F08 stays in the same shape and looks at what the optimizer does with it: folding constants on the graph rather than on the tree, straightening out jumps that go to jumps, and turning pairs of common instructions into single ones.
""")


raise SystemExit(lesson.save())
