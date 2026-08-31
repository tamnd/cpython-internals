#!/usr/bin/env python
"""F06. One node at a time.

The sixth lesson of the front end part, and the twentieth overall. F05 finished with a set of
answers about names and no code. This one is the pass that finally emits instructions, and the
thing worth understanding about it is how little it thinks.

T05 toured the whole compiler in one lesson and showed the three stages side by side. This one
stays inside the third stage and asks what its rules actually are. The angle is that almost
everything you think of as a rule of the Python language, short circuiting, chained comparison,
the order the two halves of an assignment run in, is a decision taken here and nowhere else.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

#: Two cells print the tail of a function, and 3.15 renamed the instruction that loads
#: the None it returns. The wording is shared so the two notes cannot drift apart.
NONE_NOTE = (
    "On 3.14 the implicit `return None` at the end is a `LOAD_CONST` rather than a"
    " `LOAD_COMMON_CONSTANT`. Nothing else in this cell moves."
)

lesson = Lesson("f06-one-node-at-a-time", "f06")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("f06-one-node-at-a-time").figure


lesson.md(f"""
# F06. One node at a time

{badge}

There is no `and` instruction. Search the whole opcode table and you will not find one, and there never was one. What you get instead is: load the left side, keep a copy, ask whether it is true, and jump past the rest if it is not.

{term("short circuiting", "Short circuiting")}, the rule everybody learns in their first week, is a jump that a program wrote for you. That program is the {term("code generation", "code generator")}, and it is the third of CPython's compiler passes. F05 was the second.

It is the least clever pass in the compiler, and that is on purpose. It walks the tree, emits a fixed shape for each node, and moves on. It does not look at what came before, it does not ask whether anything it emits can ever run, and it does not tidy up after itself.

{figure("there-is-no-and", "a side by side comparison of the source of a boolean and and the jump it compiles to")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/codegen.c:5390-5394@v3.15.0rc1`.

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
## The operator that is not an instruction

Start with the claim in the first paragraph, because it is easy to check and it sets up everything else. {lesson.claim("`and` and `or` produce no instruction of their own, only a jump")}
""")


lesson.code(
    """
import dis


def both(left, right):
    return left and right


dis.dis(both)
"""
)


lesson.md(f"""
Read it as a sentence. Load `left`. Copy it, because the value is the answer if we stop here. `TO_BOOL` turns the copy into a real True or False. If it is false, jump to the end and the copy of `left` is the value of the whole expression. Otherwise throw the copy away and load `right`, which then becomes the value.

That is the entire meaning of `and` in Python, and there is no operator anywhere in it. The C that emits it is {cite("Python/codegen.c:3387-3413@v3.15.0rc1#codegen_boolop")}, and it is twenty five lines long. The only difference between `and` and `or` is which of two jumps it picks, which is the `if` on the fourth line of the function.

{term("pseudo instruction", "Pseudo instructions")} came up in T05, and `JUMP_IF_FALSE` in that function is one: it is a jump to a label rather than to a byte offset, because at this point in the compiler there are no byte offsets yet.

## One node, one shape

The code generator is a walk over the tree with a big switch at the centre of it, {cite("Python/codegen.c:5375-5382@v3.15.0rc1#codegen_visit_expr")}. One branch of the switch per node kind, and F04 already told you how many kinds there are.

Most branches are tiny. Here is the one for every arithmetic operator you have ever written, {cite("Python/codegen.c:5390-5394@v3.15.0rc1")}:

```
case BinOp_kind:
    VISIT(c, expr, e->v.BinOp.left);
    VISIT(c, expr, e->v.BinOp.right);
    ADDOP_BINARY(c, loc, e->v.BinOp.op);
    break;
```

Visit the left side, visit the right side, emit the operator. Three lines, and they are the reason `a + b` evaluates `a` first. Nobody wrote that rule down separately.

{figure("one-node-one-shape", "a table of node kinds, what the generator does with each, and how short the rule is")}

{lesson.claim("the shape a node compiles to does not depend on where the node is, only on what kind of node it is")}
""")


lesson.code("""
from pyxray import compiler

SOURCES = {
    "at module level": "answer = base + 1",
    "inside a function": "def f():\\n    base = 0\\n    answer = base + 1\\n",
    "in a nested function": (
        "def f():\\n    base = 0\\n    def g():\\n        answer = base + 1\\n    return g\\n"
    ),
}

for label, source in SOURCES.items():
    stream = compiler.innermost_codegen(source)
    at = next(i for i, one in enumerate(stream) if one.opname.startswith("BINARY"))
    reads, adds = stream[at - 2].opname, stream[at].opname
    print(f"  {label:22} reads base with {reads:11} and adds with {adds}")
""")


lesson.md(f"""
{figure("only-the-name-changes", "a table of the same expression in three places and the one instruction that moves")}

Those come from the compiler's own third stage rather than from `dis`, which matters here. On 3.15 the optimizer rewrites the middle one into `LOAD_FAST_BORROW`, so a disassembly would show you what the fourth pass did and not what this one produced.

The addition is the same instruction in all three. The only thing that changed is how `base` is read, and the generator did not work that out for itself. It asked, on one line: {cite("Python/codegen.c:3293@v3.15.0rc1")} inside {cite("Python/codegen.c:3280-3293@v3.15.0rc1#codegen_nameop")}.

`_PyST_GetScope` is the symbol table lookup from F05. The five numbers that lesson was about are read here, once per name, and turned into the matching instruction. That is the whole conversation between the two passes.

## The order was decided here

Since the generator emits code by visiting children in a fixed order, the {term("evaluation order")} of your program is whatever order that walk happens to use. Most of the time it is left to right and there is nothing to notice. Assignment is where it gets interesting.

{lesson.claim("in `box[key] = value` the value runs before the target and before the key")}
""")


lesson.code("""
STEPS = []


def note(label, value):
    \"\"\"Record that this piece was evaluated, and hand the value straight back.\"\"\"
    STEPS.append(label)
    return value


box = {}

note("the box", box)[note("the key", "k")] = note("the value", 1)
print(f"  box[key] = value   {STEPS}")

STEPS.clear()
_ = note("left", 1) + note("right", 2)
print(f"  left + right       {STEPS}")

STEPS.clear()
first = second = note("only once", 3)
print(f"  first = second = v {STEPS}")
""")


lesson.md(f"""
{figure("value-before-target", "a flow from the source line through the generator to the four instructions it emits")}

The value first, then the target, then the key. That is not a rule somebody chose to document, it is what {cite("Python/codegen.c:3101-3113@v3.15.0rc1")} does: one `VISIT` of the value, and then a loop over the targets underneath it.

The third line is the same C. `first = second = v` has one value and two targets, so the value is visited once and the loop runs twice, with a `COPY` in between. That is why the expression on the right of a chained assignment runs exactly once, and it is a consequence of the loop rather than a promise anybody made.

You can see the same thing in the disassembly.
""")


lesson.code(
    """
import dis

dis.dis(compile("box[key] = value", "<here>", "exec"))
""",
    differs=(
        "On 3.14 the implicit return at the end is `LOAD_CONST None` rather than"
        " `LOAD_COMMON_CONSTANT 7`. The four instructions above it are the same."
    ),
)


lesson.md(f"""
`value`, then `box`, then `key`, then one instruction that consumes all three. Chained comparison is the same story told with jumps, {cite("Python/codegen.c:3650-3687@v3.15.0rc1#codegen_compare")}, which is where `a < b < c` evaluating `b` once comes from.

## Not clever, on purpose

The generator emits what the tree says, and only what the tree says. It does not ask whether the code it is emitting can ever run.

{lesson.claim("the code generator emits the dead branch of `if False` in full, and something later removes it")}
""")


lesson.code(
    """
import dis

from pyxray import compiler

SOURCE = "if False:\\n    answer = 1\\nelse:\\n    answer = 2\\n"

emitted = compiler.stages(SOURCE).codegen
finished = list(dis.get_instructions(compile(SOURCE, "<here>", "exec")))

print(f"  the code generator emitted {len(emitted)}")
for one in emitted:
    print(f"      {one}")
print()
print(f"  the finished code object has {len(finished)}")
for one in finished:
    print(f"      {one.opname}")
""",
    differs=NONE_NOTE,
)


lesson.md(f"""
{figure("not-clever-on-purpose", "a side by side comparison of what the generator emits and what survives")}

Everything is there. The constant `False` is loaded, `TO_BOOL` is emitted to turn it into a boolean, a jump is emitted to skip the first branch, and the body of the first branch is emitted in full even though nothing will ever reach it.

None of it survives. Working out that a branch can never run means looking at more than one instruction at a time, and that is a question about a graph rather than about a node. It is the fourth pass, {cite("Python/compile.c:5-13@v3.15.0rc1")} lists all five in order, and it is F07.

Keeping the two apart is what makes both of them readable. The generator has one job and no memory. The optimizer has the whole graph and no idea what the source looked like.

## Instructions that came from no line

The last thing worth seeing is that some of what the generator emits corresponds to nothing you wrote. `dis` gives it away by printing a dash where the line number goes.

{lesson.claim("some instructions in your function belong to no line of your source, and dis says so")}
""")


lesson.code(
    """
import dis


def outer():
    total = 0

    def inner():
        return total

    return inner


def nothing():
    pass


for code in (outer.__code__, outer().__code__, nothing.__code__):
    stream = list(dis.get_instructions(code))
    nowhere = [one.opname for one in stream if one.line_number is None]
    print(f"  {code.co_name:8} belongs to no line  {nowhere}")
    print(f"  {'':8} last two           {[one.opname for one in stream[-2:]]}")
""",
    differs=NONE_NOTE,
)


lesson.md(f"""
{figure("instructions-with-no-line", "the four instructions in a function that came from no line of source")}

`MAKE_CELL` and `COPY_FREE_VARS` are the two ends of the wire F05 ended on, turned into instructions. Neither of them is on a line because neither of them was written by you: the symbol table decided `total` was a {term("cell")} and the generator emitted the setup for it.

`nothing` has no such instruction, because it has no cells and no free variables. What it has instead is the second line of its output: a function whose entire body is `pass` still ends by loading `None` and returning it, because the generator adds that ending to every function that does not already have one.

`RESUME` is the other invisible one. It is on a line, the first line of the body, and it is the point a generator resumes at and the point a debugger or a profiler is allowed to interrupt. You never wrote it either.

## Try it yourself

1. Disassemble `a or b` and find the one difference from `a and b`. Then look at the fourth line of `codegen_boolop` and check you were right.
2. Write `__hidden` as an attribute inside a class and look at `co_names` on the method. The mangling into `_ClassName__hidden` is done by the code generator, on the line just above the scope lookup.
3. Use the `note` helper to find the evaluation order of a function call with a keyword argument, and of an f string with two replacement fields.
4. Compare `compiler.stages(source).codegen` with the finished disassembly for a `while True` loop. Which of the two ends up with a test in it?
5. Find a statement whose generated code contains a jump you did not write and that is not a loop, a condition or a boolean operator.

## What just happened

The code generator is the third of five passes and the first one that emits anything. It is a walk over the tree with a switch at the middle, one branch per node kind, and each branch is a handful of lines.

There is no instruction for `and`, for `or`, or for a chained comparison. All three are jumps, written out by the generator, which is why short circuiting is a compiler behaviour rather than an interpreter one.

The shape a node turns into does not depend on where the node is. The one thing that varies is how names are read, and that comes from a single call into the symbol table.

Evaluation order is whatever order the walk visits children in. For an assignment that means the value first and the target second, and for a chained assignment it means the value once and a `COPY`.

The generator emits dead code without noticing, because noticing would need a view of more than one node. That is the next pass.

Some of what it emits belongs to no line of your program: the cell setup, the free variable copy, and the `return None` at the end of every function that does not return anything.

## What is next

F07 turns this flat list into a {term("control flow graph")} and starts deleting things. The dead branch goes, the jumps get straightened out, and the whole shape of the code changes without any of it looking at your source again.
""")


raise SystemExit(lesson.save())
