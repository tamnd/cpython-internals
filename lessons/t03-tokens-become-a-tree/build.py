#!/usr/bin/env python
"""T03. Tokens become a tree.

The second stage in close up. The tokens from T02 go in, a syntax tree comes out, and the
lesson is really about one question: what does the tree keep about your file, and what has
it thrown away for good?

The answer is more interesting than it sounds, because the tree throws away the brackets
and keeps what the brackets did. That is the difference between a syntax tree and a record
of what somebody typed, and it is the reason every later stage can be simple.

The experiment at the end is a property test. `unparse(parse(source))` should parse to the
same tree as `source`, and the lesson checks that on every module in the reader's own
standard library rather than on the four line example above it.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of
them. `just lessons` checks that the committed notebook still matches this file, so a cell
edited in Jupyter and committed without coming back here fails the build.

The pictures come from `diagrams.py` in this directory. They are looked up on disk rather
than imported, so a diagram that has not been built yet fails here instead of producing a
notebook full of broken images.
"""

from nbbuild import BANNER, YOUR_INSTALL, Lesson
from nbdiagram import Diagrams

lesson = Lesson("t03-tokens-become-a-tree", "t03")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("t03-tokens-become-a-tree").figure

lesson.md(f"""
# T03. Tokens become a tree

{badge}

T02 left you with a flat list of {term("token", "tokens")}: a name, an equals sign, a number, a star, another number. That list is in the right order, and it says nothing about what goes with what.

This lesson is about the part that fixes that. The parser reads the tokens and builds an {term("abstract syntax tree")}, and the tree is the first thing in the pipeline that knows `6 * 7` is one thing rather than three.

{figure("where-we-are", "the eight stages of running Python, with the syntax tree highlighted")}

The interesting question about the tree is not how it gets built but what it keeps. Your brackets are gone by the end of this stage, and so are your spacing and your comments, and everything they meant is still there. By the end you will have watched three different files turn into exactly the same tree, and then checked that claim against every module in your own standard library.

No C required and no build of your own, since everything here runs on a normal Python.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Parser/pegen.c:938-941@v3.15.0rc1#_PyPegen_run_parser`.

Read it as four parts: the file, the lines, the release those line numbers belong to, and the name of the function they are inside.

Every reference is a link, and every one is checked against the pinned source on each change, so a stale reference fails the build instead of sending you somewhere wrong. The function name on the end is what makes the check work. Line numbers move whenever somebody adds code above them, and a moved line number points at something that looks plausible and is not.

You never have to read any of it. The references are there so you can go deeper when you want to, and so you can check that this lesson is not making things up.
""")


lesson.md("""
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

Node types get added between releases and the tree for a given piece of code can change shape, so every lesson here starts by saying which build produced the output you are about to read.
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
## One line, one tree

`ast.parse` runs the real parser, the same one that runs when you import a module. It is a {term("PEG parser")}, generated from a {term("grammar")} file into `Parser/parser.c` and driven by {cite("Parser/pegen.c:938-941@v3.15.0rc1#_PyPegen_run_parser")}, and the Python side of it is {cite("Lib/ast.py:26-30@v3.15.0rc1#parse")}, which is a thin wrapper around `compile` with a flag set.

Start with the line from T01.
""")


lesson.code(r"""
from pyxray import trees

SOURCE = "answer = 6 * 7\n"

print(trees.outline(SOURCE))
""")


lesson.md(f"""
Read it from the inside out. Two `Constant` nodes hold 6 and 7. A `BinOp` holds those two with a `Mult` between them. An `Assign` puts the result into a `Name` whose `ctx` is `Store`, meaning this name is being written to rather than read from.

The indented view above is this project's, and it is there because the shape is the point. CPython's own view is {cite("Lib/ast.py:117-121@v3.15.0rc1#dump")}, which prints everything and is what you want when you need to be exact rather than quick.
""")


lesson.code("""
import ast

print(ast.dump(ast.parse(SOURCE), indent=4))
""")


lesson.md(f"""
## Where the node types are written down

Python's syntax tree is not defined inside a compiler somewhere. It is defined in one readable file, {cite("Parser/Python.asdl:62@v3.15.0rc1#BinOp")}, in a small language called {term("ASDL")} that exists to describe tree shapes.

The line for `BinOp` in that file says it has three fields: an expression on the left, an operator, and an expression on the right. The neat part is that the same line ends up as the docstring of the class.

{figure("where-the-node-classes-come-from", "Python.asdl is read by asdl_c.py, which generates the classes and puts the declaration in the docstring")}

{cite("Parser/asdl_c.py:95-109@v3.15.0rc1#asdl_of")} turns each declaration back into text at build time, and {cite("Parser/asdl_c.py:1617-1619@v3.15.0rc1#make_type")} hands it to `type()` as the docstring of the generated class. Everything below `Lib/ast.py` here is a {term("generated file")}, so what comes back is the definition itself rather than somebody's description of it.
""")


lesson.code("""
print(trees.asdl(ast.BinOp))
print(trees.fields(ast.BinOp))
""")


lesson.md("""
`expr left` means the left side is any expression at all, not just a number. That single word is why `1 + 2 * 3` can nest: the left of a `BinOp` is allowed to be another `BinOp`, and so is the right.

Some node types are a closed list of cases rather than a thing with fields. The operators are one of those, and asking for the declaration gives you every operator Python has.
""")


lesson.code("""
print(trees.asdl(ast.operator))
print()
print("Mult has fields:", trees.fields(ast.Mult))
""")


lesson.md(f"""
`Mult` has no fields, because it is a case rather than a container. It is not a node holding a `*` somewhere inside it, it is the name of which operator this is, and the full list is fixed at {cite("Parser/Python.asdl:104-105@v3.15.0rc1#operator")}. An operator that is not on that list cannot reach the compiler, because there is nothing for the parser to build.

The C function that actually assembles one of these is {cite("Python/Python-ast.c:7767-7770@v3.15.0rc1#_PyAST_BinOp")}, and it is generated from the same ASDL file.
""")


lesson.md(f"""
## Three files, one tree

The claim this lesson is really about is that the tree keeps what your code means and throws away how you wrote it.

{figure("three-sources-one-tree", "three differently written files all producing one identical tree")}

Three files, with brackets in one, no spaces in another and a comment on the third. Ask whether any two of them produce the same tree.
""")


lesson.code(r"""
WRITTEN = ["answer = (6 * 7)", "answer=6*7", "answer = 6 * 7  # note"]

for other in WRITTEN[1:]:
    print(f"{other!r:<28} same tree as {WRITTEN[0]!r}? {trees.same_tree(WRITTEN[0], other)}")
""")


lesson.md("""
All three give the same tree, and not just a similar or equivalent one: identical, field for field.

It is worth seeing that the brackets really were there a moment ago. The tokenizer from T02 hands the parser both of them as ordinary tokens, and the parser is where they stop existing.
""")


lesson.code(r"""
from pyxray import compiler

for item in compiler.tokens("answer = (6 * 7)\n"):
    if item.string.strip():
        print(f"{item.string!r}", end="  ")
print()
print()
print(trees.outline("answer = (6 * 7)\n"))
""")


lesson.md(f"""
## What the brackets did is still there

The obvious objection is that brackets change what code means, so they cannot just vanish. They do not vanish, they are turned into shape.

{figure("precedence-is-the-shape", "the trees for 1 + 2 * 3 and (1 + 2) * 3, side by side")}

Same five tokens in the same order, two different trees. On the left the multiply is inside the add, because `2 * 3` has to happen first. On the right it is the other way round.
""")


lesson.code("""
print(trees.outline("x = 1 + 2 * 3"))
print()
print(trees.outline("x = (1 + 2) * 3"))
print()
print("same tree?", trees.same_tree("x = 1 + 2 * 3", "x = (1 + 2) * 3"))
""")


lesson.md(f"""
The precedence is not stored anywhere as a number. It is in the grammar, and it comes out as nesting. {cite("Grammar/python.gram:841-844@v3.15.0rc1#sum")} says a `sum` is a `sum` plus a `term`, and {cite("Grammar/python.gram:846-852@v3.15.0rc1#term")} says a `term` is a `term` times a `factor`. Because a sum is built out of terms and not the other way round, multiplication ends up further down the tree, which is exactly what "binds tighter" means.

Those rules are also where the node gets built. Look at the right hand side of the grammar line for `*` and you will see `_PyAST_BinOp(a, Mult, b, EXTRA)`, which is the C constructor from earlier being called by the parser.
""")


lesson.md(f"""
## Every node remembers where it came from

The tree forgets your formatting, and it does keep track of which characters each node came from. That is how a traceback can point at a column, and how tools like linters can tell you where the problem is.

{cite("Lib/ast.py:385-390@v3.15.0rc1#get_source_segment")} goes the other way, from a node back to the text it covers.
""")


lesson.code("""
for span in trees.spans(SOURCE):
    print(span)
""")


lesson.md("""
`Mult` is missing from that list, and that is not a bug. Nodes with no fields have no position either, because `Mult` is not something written at a place in the file. It is which case this `BinOp` is. If you go looking for the position of an operator you will not find one.
""")


lesson.md(f"""
## Turning a tree back into text

{cite("Lib/ast.py:653-659@v3.15.0rc1#unparse")} takes a tree and gives you source code back. It is not your source code, it is source code that means the same thing.

{figure("what-unparse-rewrites", "a table of five things you might write and what unparse gives back")}

Every row of that table is a different file and the same tree, so `unparse` has nothing to go on when it decides how to write it out. It picks one way and uses it every time.
""")


lesson.code(r"""
for source in ["x = 0x2a", "x = 1_000_000", "x = 'a' 'b'", "x = (1 + 2)", "x = 1  # note"]:
    print(f"{source:<22} {trees.roundtrip(source)}")
""")


lesson.md("""
`0x2a` comes back as `42` because the tree holds the number and not the base you wrote it in. `1_000_000` loses its underscores for the same reason. `'a' 'b'` was already joined into one string by the parser, since adjacent string literals are glued together as part of the grammar rather than at runtime.

Every one of them says "same tree", which is the property worth remembering and worth checking rather than believing.
""")


lesson.md("""
## The round trip, on real code

The property in one sentence: take any source file, parse it, unparse it, and parse the result, and the two trees should be identical.

Four examples do not prove a property, so run it over every module in the standard library that shipped with the interpreter you are using right now.
""")


lesson.code(
    """
report = trees.survey(trees.stdlib())

print("standard library at", trees.stdlib())
print(report)
""",
    differs=YOUR_INSTALL,
)


lesson.md("""
Every module gives the same tree both times. That is a real property test over a few hundred thousand lines of code that nobody wrote for this lesson, and it took about a second.

It is worth being clear about what it does not prove. It says nothing about whether the unparsed text is nice to read, and nothing about the files that were skipped, which are mostly test fixtures that are deliberately not valid on this version. What it does show is that the tree really is the whole meaning of the file, because you can throw the file away and rebuild it.
""")


lesson.md(r"""
## Try it yourself

Change `MINE` below and run the cell. Things worth trying, roughly in order of how surprising the answer is.

Try `x = 1 if a else 2` and look at where the condition ends up in the tree. It is not first, even though you typed it in the middle.

Try `def f(a, b=1, *args, **kw): pass` and look at the `arguments` node. Every kind of parameter Python has is a separate field, which is why the tree is a better thing to write a tool against than the text.

Try `x = -5` and count the nodes. The minus sign is a `UnaryOp` wrapped around a `Constant 5`, so there is no negative number literal in Python at all.

Try `f'{a + b}'` and watch the code inside the braces come out as an ordinary tree of its own, which is the tokenizer behaviour from T02 followed through to this stage.

Try something with a syntax error, like `x = (1 +`, and see what the parser says.
""")


lesson.code(r"""
MINE = "x = 1 if a else 2"

print(trees.outline(MINE))
print()
print(trees.roundtrip(MINE))
""")


lesson.md("""
## What just happened

A flat list of tokens became a tree that knows what goes with what. The tree dropped your brackets, your spacing and your comments, and kept every bit of what they meant by putting it into the shape. Each node type is declared in one file, in a small language for describing tree shapes, and carries that declaration around as its own docstring. Every node that was written somewhere remembers where.

Then you checked the whole thing by turning trees back into text and parsing them again, on real code, and got the same tree every time.
""")


lesson.md(f"""
## Where this goes next

The tree is the last stage that is only about syntax. Everything after it is about meaning.

T04 is the next box along, and it is the first pass that asks a question the tree cannot answer on its own: when this code says `answer`, which `answer` is that? The tree has a `Name` node and nothing else. The {term("symbol table")} decides whether that name is a local, a global, or something borrowed from an enclosing function, and the compiler cannot pick an instruction until it knows.

That pass is also where one of Python's most confusing error messages comes from. A function that assigns to a name anywhere treats it as local everywhere, including on the line before the assignment, which is why you can get an `UnboundLocalError` from a name that clearly has a value.
""")

raise SystemExit(lesson.save())
