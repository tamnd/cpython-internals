#!/usr/bin/env python
"""T01. One line, seven stages.

The opening lesson, and the map every later one hangs off. It follows `answer = 6 * 7`
from the characters in a file to the number on the screen, naming the seven stages it goes
through and the CPython source file that does each one. The point it is really making is
the last one: the multiplication has already happened by the time the program runs.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of
them. `just lessons` checks that the committed notebook still matches this file, so a cell
edited in Jupyter and committed without coming back here fails the build.

The pictures come from `diagrams.py` next to this file. `figure` looks each one up on disk,
so asking for one that has not been drawn fails here rather than turning into a broken
image somebody finds later.
"""

from nbbuild import BANNER, TRAILING_NONE, Lesson
from nbdiagram import Diagrams

lesson = Lesson("t01-one-line-seven-stages", "t01")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("t01-one-line-seven-stages").figure

lesson.md(f"""
# T01. One line, seven stages

{badge}

This lesson follows one line of Python, `answer = 6 * 7`, from the bytes in a file to the number 42 sitting in a namespace. Seven things happen in between, and you can watch all of them from inside Python. You do not need a C compiler and you do not need to build CPython yourself.

{figure("seven-stages", "eight boxes from your file to the answer, with the CPython source file under each one")}

No C knowledge is assumed, and you do not need to already know what a compiler is. By the end you will have found the point where CPython does the multiplication in that line, which is earlier than most people expect, and you will know which source file does it.

Everything below runs in continuous integration on CPython 3.15.0rc1 and on 3.14 before it reaches you. Where the two versions disagree the lesson says so and prints what your build actually did, so you are never asked to trust a number that was true on somebody else's machine.

Words that turn up here and get used again later, like {term("code object")} and {term("bytecode")}, have one definition each in the [glossary](https://github.com/tamnd/cpython-internals/blob/main/GLOSSARY.md). Follow a link when a word is new to you, ignore it when it is not.
""")


lesson.md("""
## How to read the source references

References to CPython's own source look like `Python/ceval.c:1213@v3.15.0rc1#_PyEval_EvalFrameDefault`. That is a file, a line or a range of lines, the release tag those line numbers belong to, and the name of the function they are inside. Every one is a link you can click.

Every one is also checked against the pinned source tree whenever anything here changes, so a reference that has drifted fails the build. The function name on the end is what makes that possible. A bare line number goes stale quietly when somebody adds a function above it, and then it points at real code that has nothing to do with what you were reading about.
""")


lesson.md("""
## Setup

Colab does not come with the small package these lessons use for poking at the compiler, so the next cell installs it. If you are running this from a checkout of the repository it is already installed and the cell does nothing.
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
## Which interpreter is this

Nearly every fact in this lesson is a fact about one particular build of CPython. Instruction names change between releases and so do the sizes of things, so every lesson here starts by saying out loud which binary is about to produce the output you are reading.

If the banner says 3.14, which is what Colab installs today, nearly all of this lesson is the same and a handful of cells are not. The differences below all come from one change. On 3.15 the implicit `return None` at the end of a module is a `LOAD_COMMON_CONSTANT`, and `None` is not in the constant table at all. On 3.14 it is an ordinary `LOAD_CONST`, and `None` is in the table. That is one more constant and two fewer bytes of bytecode everywhere those get printed. Stage 6 comes back to it and asks your build directly.
""")


lesson.code(
    """
import pyxray

pyxray.show()
""",
    differs=BANNER,
    quiet=True,
)


lesson.md("""
## The line

One assignment, two numbers, one multiplication.
""")


lesson.code(r"""
SOURCE = "answer = 6 * 7\n"

print(SOURCE)
""")


lesson.md(f"""
## Stage 1. Bytes become tokens

CPython reads your file as bytes and cuts it into {term("token", "tokens")}: a name, an equals sign, a number, an operator, another number, an end of line. The code that does the cutting is {cite("Parser/lexer/lexer.c:1626-1635@v3.15.0rc1#_PyTokenizer_Get")}, and somebody wrote it by hand rather than generating it from a description of the language.

{figure("tokens-of-one-line", "the five tokens in answer = 6 * 7, each joined to the characters it came from")}

The standard library exposes this same tokenizer through the `tokenize` module, so what you are about to see is the real thing and not an imitation of it. {lesson.claim("every token comes back with the line and the column range it was cut from, which is how a syntax error knows which characters to point at")}.
""")


lesson.code("""
import token

from pyxray import compiler

for item in compiler.tokens(SOURCE):
    name = token.tok_name[item.type]
    line, start = item.start[0], item.start[1]
    print(f"{name:<10} {item.string!r:<10} line {line}, columns {start} to {item.end[1]}")
""")


lesson.md(f"""
Two of those tokens are not in your file. `ENCODING` comes first, and it carries the tokenizer's answer to a question it has to settle before it can read a single character of Python: how are these bytes meant to be decoded. `ENDMARKER` comes last and marks the end of the input. You wrote neither one.

Indentation is invented the same way: {lesson.claim("INDENT and DEDENT are tokens the tokenizer works out from column numbers rather than characters it found")}, and that is easier to see with a line that has some.
""")


lesson.code(r"""
for item in compiler.tokens("if answer:\n    print(answer)\n"):
    print(f"{token.tok_name[item.type]:<10} {item.string!r}")
""")


lesson.md("""
`INDENT` and `DEDENT` appear nowhere in that text. The tokenizer works them out from column numbers and hands the parser something that behaves like the braces other languages make you type. That is all Python's significant whitespace is, and it is settled here, in the first stage. Nothing later on knows or cares how your code was laid out.

T02 is entirely about this stage, so there is a lot more there.
""")


lesson.md(f"""
## Stage 2. Tokens become a tree

The parser reads the token stream and builds an {term("abstract syntax tree", "abstract syntax tree")}. CPython has used a {term("PEG parser")} since 3.9, generated from a {term("grammar")} file into `Parser/parser.c`, and the function that drives it is {cite("Parser/pegen.c:938-941@v3.15.0rc1#_PyPegen_run_parser")}.

The tree for a single assignment is small enough to look at whole, and in it {lesson.claim("the multiplication is still a multiplication, with 6 and 7 sitting underneath it as two separate constants")}.

{figure("the-tree", "the syntax tree for answer = 6 * 7, with Assign at the top")}
""")


lesson.code("""
import ast

tree = ast.parse(SOURCE)

print(ast.dump(tree, indent=4))
""")


lesson.md(f"""
Read it from the inside out. Two `Constant` nodes hold 6 and 7. A `BinOp` holds those two with a `Mult` between them. An `Assign` puts the result into a `Name` whose context is `Store`, which means the name is being written to rather than read from.

Nothing has been worked out yet, and `6 * 7` is still a multiplication of two constants sitting in a tree.

{lesson.claim("the tree is an ordinary Python object, so you can change a node and compile the result")}, which is what the next cell does to turn the 7 into an 8.
""")


lesson.code("""
edited = ast.parse(SOURCE)
edited.body[0].value.right = ast.Constant(value=8)

namespace = {}
exec(compile(ast.fix_missing_locations(edited), "<edited>", "exec"), namespace)

print(namespace["answer"])
""")


lesson.md(f"""
## Stage 3. The tree gets a symbol table

Before generating a single {term("instruction")}, CPython walks the tree and works out what every name in it is. Is `answer` a local, a global, or something borrowed from an enclosing function? The compiler cannot pick an instruction until it knows, because a local is a numbered slot in a {term("frame")} and a global is a dictionary lookup by name. Those are different {term("opcode", "opcodes")} with very different costs. The pass that decides builds the {term("symbol table")}, and it is {cite("Python/symtable.c:415-418@v3.15.0rc1#_PySymtable_Build")}. {lesson.claim("the symbol table is not private to the compiler, you can ask a stock interpreter for it and print the whole thing")}.
""")


lesson.code("""
print(compiler.symbols(SOURCE).tree())
""")


lesson.md(f"""
`answer` comes back as both local and global, which looks like a contradiction and is not one. At module level the name really is stored in this module's own namespace, so it is local to this scope. It really is also the thing every function in the file will find when it reads that name, so it is a global. Both are true at the same time.

Inside a function the two roles come apart: {lesson.claim("a parameter is a local and nothing else, and a name that comes from the module is a global the function only ever reads")}.

{figure("one-name-two-answers", "answer is local and global at module level, but the two roles split inside a function")}
""")


lesson.code(r"""
print(compiler.symbols("def f(a):\n    return a + answer\n").tree())
""")


lesson.md("""
Now `a` is a parameter and a local and nothing else, and `answer` is a global that only ever gets read.

There is also a scope called `__annotate__` in there that you did not write. That is PEP 649, which made annotations lazy in 3.14. Every `def` gets a hidden function that would work out its annotations if anything ever asked for them, and it gets one whether or not there are any annotations to work out.
""")


lesson.md(f"""
## Stage 4. The tree becomes instructions

Now the compiler walks the tree a second time and emits instructions, a small pile of them per node. That pass is {term("code generation")}, and the case that handles an expression is {cite("Python/codegen.c:894-897@v3.15.0rc1#_PyCodegen_Expression")}.

This is usually the point where you can no longer see what a stock interpreter is doing. CPython ships a module called `_testinternalcapi` that exposes the compiler's stages one at a time, and that is what lets you read the instruction sequence before the optimizer has touched it. If the next cell raises, read the message: it means your interpreter was built without those hooks, and it will tell you what still works.

What comes back is the list before anything has tidied it up, and {lesson.claim("before the optimizer runs, `6 * 7` is still three instructions: load one constant, load the other, multiply them")}.
""")


lesson.code("""
result = compiler.stages(SOURCE)

for item in result.codegen:
    print(item)
""")


lesson.md(f"""
`LOAD_CONST 0`, `LOAD_CONST 1`, `BINARY_OP 5`. The multiplication is still there, and as far as this stage is concerned it is still going to happen while your program runs. `BINARY_OP 5` is multiply, 5 being the position of `*` in CPython's table of binary operators.

`ANNOTATIONS_PLACEHOLDER` is marked pseudo. A {term("pseudo instruction")} only exists inside the compiler, as a marker for a later pass, and none of them ever reaches a code object. This one holds the spot where the module's annotations would be set up if it had any.
""")


lesson.md(f"""
## Stage 5. The optimizer rewrites the instructions

The instruction sequence is turned into a {term("control flow graph")}, and then the graph is optimized. The entry point is {cite("Python/flowgraph.c:3753-3757@v3.15.0rc1#_PyCfg_OptimizeCodeUnit")}. The next cell prints what it did, with the two sequences side by side, and {lesson.claim("the optimizer replaces those three instructions with a single one that loads 42")}.
""")


lesson.code(
    """
print(compiler.what_the_optimizer_did(result))
""",
    differs=TRAILING_NONE,
    quiet=True,
)


lesson.md(f"""
Look at the right hand column. `LOAD_CONST`, `LOAD_CONST`, `BINARY_OP` has turned into a single `LOAD_SMALL_INT 42`, so the multiplication is gone. It ran once, at compile time, inside {cite("Python/flowgraph.c:1860-1866@v3.15.0rc1#eval_const_binop")}, and the answer went straight into the instruction stream. Your program will never multiply anything.

{figure("the-multiplication-disappears", "three instructions on the left becoming one on the right")}

That is {term("constant folding")}, and {lesson.claim("CPython folds constants twice, in two places, on two different data structures", unobservable="the first pass runs on the tree inside a real compile() call, and the stage hook this lesson uses is handed a tree that has already skipped it, so nothing here can catch that one in the act")}.

{figure("two-constant-folders", "the tree folder and the graph folder, one after the other")}

The one you just watched works on the control flow graph. There is an earlier one that works on the tree, {cite("Python/ast_preprocess.c:370-383@v3.15.0rc1#fold_binop")}, and you cannot see it in this notebook for a reason worth knowing. The stage hook is handed a tree straight from `ast.parse`, which skips the preprocessing pass a real `compile()` call would have run first. So what you are looking at is the second folder catching something the first one never got to look at.
""")


lesson.md("""
Folding only happens when the compiler can see both operands for itself. Replace one of the numbers with a name and the multiplication survives all the way into the finished code, because `six` could be anything at all by the time that line runs.
""")


lesson.code(
    r"""
print(compiler.what_the_optimizer_did(compiler.stages("answer = six * 7\n")))
""",
    differs=TRAILING_NONE,
    quiet=True,
)


lesson.md(f"""
## Stage 6. The instructions become a code object

The {term("assembler")} turns the optimized graph into the {term("code object")}, which is the object CPython actually executes and cannot be changed once built. It is built by {cite("Objects/codeobject.c:715-718@v3.15.0rc1#_PyCode_New")}. The whole front end, every stage above, is driven from {cite("Python/compile.c:1526-1540@v3.15.0rc1#_PyAST_Compile")}.

{lesson.claim("the code object holds everything the compiler worked out: the instructions, the table of constants, and how deep the value stack has to be for them")}, and all of it is readable from Python.
""")


lesson.code(
    """
import dis

print("co_consts    ", result.code.co_consts)
print("co_names     ", result.code.co_names)
print("co_stacksize ", result.code.co_stacksize)
print("co_code      ", len(result.code.co_code), "bytes")
print()
dis.dis(result.code)
""",
    differs="On 3.14 co_consts is (6, None) rather than (6,) and the bytecode is 10 bytes rather than 12, because None still needs a table entry there.",
    quiet=True,
)


lesson.md(f"""
Two details in there are worth a second look, and the next cell makes both of them concrete.

{lesson.claim("the constant table still contains the 6, and no instruction in the finished code ever loads it")}. The table was built while the multiplication still existed, and nobody pruned it afterwards, so a number your program has no use for gets carried around inside the code object for as long as the code object lives.

{lesson.claim("the 42 never reaches the constant table, it rides inside the instruction as its argument")}. That argument belongs to `LOAD_SMALL_INT`, and it is the {term("oparg", "argument")} the interpreter reads straight out of the instruction stream. A small integer does not need a table entry, because CPython keeps a shared copy of it alive permanently, which is the {term("small integer cache")} and gets a lesson of its own later on.

{figure("where-the-42-lives", "6 sitting unused in co_consts, and 42 sitting inside the instruction")}
""")


lesson.code(
    """
loaded = {i.argval for i in dis.get_instructions(result.code) if i.opname == "LOAD_CONST"}
inline = [str(i) for i in result.optimized if "SMALL_INT" in i.opname]

print("constants the code object carries:", result.code.co_consts)
print("constants any instruction loads:  ", loaded or "none")
print("where the 42 actually lives:      ", inline)
""",
    differs="On 3.14 one instruction does load a constant, the None at the end, so the middle line says {None} rather than none. The point of the cell survives: nothing loads the 6.",
    quiet=True,
)


lesson.md(f"""
The last two instructions are the module's implicit `return None`, and they are spelled differently depending on which build you are on. From 3.15 there is a `LOAD_COMMON_CONSTANT`, which pulls `None` out of a fixed table shared by every code object, so `None` no longer needs an entry of its own. On 3.14 it is still an ordinary `LOAD_CONST`. The bytecode is a couple of bytes longer on 3.15 for an unrelated reason: `RESUME` grew an {term("inline cache")} entry.

{lesson.claim("from 3.15 the implicit return None needs no entry in the constant table, because LOAD_COMMON_CONSTANT reads it from a table every code object shares")}, so rather than take either version's word for it, print what your build did.
""")


lesson.code(
    """
print("python            ", sys.version.split()[0])
print("last instructions ", [str(item) for item in result.optimized[-2:]])
print("co_consts         ", result.code.co_consts)
print("bytecode          ", len(result.code.co_code), "bytes")
print("None is a constant", None in result.code.co_consts)
""",
    differs="This cell is here to differ. On 3.14 the last line says True and on 3.15 it says False, which is the whole paragraph above turned into output.",
    quiet=True,
)


lesson.md(f"""
## Stage 7. The code object runs

Finally the {term("eval loop", "evaluation loop")} executes the code object one instruction at a time, in {cite("Python/ceval.c:1213@v3.15.0rc1#_PyEval_EvalFrameDefault")}. It is one very large switch statement, and lessons later in the series take it apart properly. Run it and {lesson.claim("42 lands in the namespace without your program multiplying anything")}.
""")


lesson.code("""
namespace = {}
exec(result.code, namespace)

print(namespace["answer"])
""")


lesson.md("""
42, and your program did not multiply anything to get there.

The whole trip, in one line of counts.
""")


lesson.code(
    """
print(result.summary())
""",
    differs="On 3.14 the last number is 10 bytes rather than 12. Everything to the left of it is the same.",
    quiet=True,
)


lesson.md("""
## What just happened

Source text was decoded and cut into tokens. Tokens were parsed into a tree. The tree was walked once to work out what every name meant, and walked again to emit instructions. The instructions became a graph, the graph was optimized, and the optimizer did your arithmetic for you. What was left was assembled into a code object, and the code object was executed.

Seven stages for one line of Python, and only the last one runs when you run your program.
""")


lesson.md(r"""
## Try it yourself

Change `MINE` below and run the cell. Some things worth trying, roughly in order of how surprising the answer is.

Try `x = 2 ** 10`, which folds, and then `x = 2 ** 10000`, which does not. The optimizer will not fold a result that would be enormous, because the constant would then have to be stored in every copy of the code object forever.

Try `x = "ab" * 3` and then `x = "ab" * 100000`, and watch the same size limit apply to strings.

Try `x = 1 / 0`. The compiler will not fold something that raises, so the division survives to runtime, which is why you get a traceback pointing at your line rather than an error at compile time.

Try `if True:\n    x = 1`, and see how much of the `if` is left by the time the optimizer has finished.
""")


lesson.code(
    r"""
MINE = "x = 2 ** 10\n"

mine = compiler.stages(MINE)
print(mine.summary())
print()
print(compiler.what_the_optimizer_did(mine))
""",
    differs=TRAILING_NONE,
    quiet=True,
)


lesson.md("""
## Where this goes next

The seven stages are the map for the rest of the material. Each one gets a lesson of its own, and each of those lessons is the same shape as this one: a small piece of Python you can run, the exact CPython source that does the work, and an experiment that fails if the explanation is wrong. Every lesson opens with the map from the top of this page, with its own box lit up, so you always know where you are.

The next lesson goes back to the first box and stays there. The tokenizer invents `INDENT` and `DEDENT` out of nothing, has never heard of a single Python keyword, and switches modes partway through an f-string. T02 is about all three.
""")

raise SystemExit(lesson.save())
