#!/usr/bin/env python
"""F03. The parser nobody wrote.

The third lesson of the front end part, and the seventeenth overall. F01 and F02 were about
turning characters into tokens. This one is about what reads the tokens, and the surprise is
that no person wrote it. `Parser/parser.c` is 39486 lines of generated C, produced from a
grammar file of 1645 lines that a person really did write.

The rule this lesson works to is the same as the last two: everything shown has to be visible
from Python. That turns out to be easy, because a generated parser leaves fingerprints. The
shape of the trees you get, the two kinds of keyword, and the quality of the error messages
are all decisions written in the grammar file, and all three can be read back off `ast`.

The one thing that cannot be done from a stock interpreter is running the generator, because
`Tools/peg_generator` ships only in the source tree. That part is a Tier 1 recording.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording

lesson = Lesson("f03-the-parser-nobody-wrote", "f03")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("f03-the-parser-nobody-wrote").figure

#: The recorded run. It needs the CPython source tree, which no installed Python has.
GENERATOR = "f03-a-parser-nobody-wrote"


lesson.md(f"""
# F03. The parser nobody wrote

{badge}

Somebody wrote the tokenizer. F01 and F02 read it: `Parser/lexer/lexer.c` is C that a person typed, and it changes when a person decides it should.

The parser is not like that. `Parser/parser.c` is 39486 lines of C and not one of them was written by hand. It is output. The input is `Grammar/python.gram`, a file of 1645 lines that describes Python's syntax, and a {term("parser generator")} in the source tree reads that file and writes the parser out.

That one fact explains a surprising amount. Why `2 ** 3 ** 4` groups to the right while `1 - 2 - 3` groups to the left, why `match` can be a keyword and a variable name in the same file, and why some syntax errors tell you exactly what you did wrong while others just say `invalid syntax`.

{figure("one-file-in-a-parser-out", "a pipeline from python dot gram through the generator to parser dot c and then the compiler")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Grammar/python.gram:841-844@v3.15.0rc1`.

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
## The parser is output, not source

You do not have to take this on trust, and you do not have to go and look at CPython's source to check it. Your own installed Python ships a small module that was written by the same run of the same program.

{lesson.claim("the keyword module in the standard library is generated from the grammar file, and it says so in its own docstring")}
""")


lesson.code("""
import keyword

for line in keyword.__doc__.strip().splitlines():
    print(f"  {line}")
""")


lesson.md(f"""
That docstring is doing a lot of work for one file. It names the input, `Grammar/python.gram`. It names the program, `pegen`, living under `Tools/peg_generator`. It names the outputs, one of which is the very file you are reading the docstring out of. And it says please don't muck it up, which is the polite version of the fact that any edit you make here is gone the next time somebody runs the command.

The parser goes through the same door. The `regen-pegen` target in {cite("Makefile.pre.in:2046-2054@v3.15.0rc1")} runs `pegen` in C mode over the same grammar file and writes `Parser/parser.c`. Same input, same program, different back end.

So what does the generator actually do? The honest answer is that you cannot run it from an installed Python, because `pegen` is not installed anywhere: it lives in the CPython source tree and nowhere else. That makes it a good candidate for a recording. Below is a real run, in a container built from the pinned source, on a grammar of four rules for arithmetic that fits on a screen.

{lesson.claim("the generator is a real program you can point at any grammar, and on a four rule grammar it writes a working parser in about a hundred lines", unobservable="Tools/peg_generator ships only in the CPython source tree, so no installed Python can import it and the run below is a recording")}

{recording(GENERATOR)}
""")


lesson.md(f"""
Three things worth pulling out of that.

The ratio is the first one. 1645 lines of grammar become 39486 lines of C. Nobody is maintaining those 39486 lines, and nobody has to, which is the entire point of doing it this way.

The second is `@memoize_left_rec` and the comment above `expr`. The generator copied the grammar rule into the output as a comment, then wrote a loop underneath it. That loop is how {term("left recursion", "a rule that mentions itself on the left")} is made to work at all, and the C version of it is right there in {cite("Parser/parser.c:14045-14079@v3.15.0rc1#sum_rule")} if you want to see the same shape with Python's real `sum` rule in it.

The third is that the generated parser parses. `1 + 2 + 3` came back as `('+', ('+', 1, 2), 3)`, grouped to the left, and nobody wrote a line of code to make it group that way. That leaning came out of the grammar, and it is the next thing to look at.

## The shape of the tree is the shape of the rule

Most languages document their operators with a precedence table and a column saying left or right. Python has no such table anywhere in the implementation. What it has instead is rules that mention themselves, and which side they mention themselves on is the whole answer.

Here is `sum`, at {cite("Grammar/python.gram:841-844@v3.15.0rc1")}:

```
sum[expr_ty]:
    | a=sum '+' b=term {{ _PyAST_BinOp(a, Add, b, EXTRA) }}
    | a=sum '-' b=term {{ _PyAST_BinOp(a, Sub, b, EXTRA) }}
    | term
```

`sum` appears on the left of the operator, so a chain of them nests to the left. Now `power`, at {cite("Grammar/python.gram:861-863@v3.15.0rc1")}, where the recursive mention is on the right of the operator, so a chain nests the other way. And `comparison`, at {cite("Grammar/python.gram:784-791@v3.15.0rc1")}, which does not mention itself at all: it uses a `+` to say one or more, so a chain of comparisons comes back flat.

{lesson.claim("associativity is not configured anywhere, it falls out of which side of the rule the rule names itself on")}
""")


lesson.code("""
import ast

SIGNS = {ast.Sub: "-", ast.Pow: "**"}


def shape(node):
    \"\"\"The tree as nested brackets, so which way it leans is easy to see.\"\"\"
    if isinstance(node, ast.BinOp):
        return f"({shape(node.left)} {SIGNS[type(node.op)]} {shape(node.right)})"
    if isinstance(node, ast.Compare):
        legs = [shape(node.left)] + [shape(one) for one in node.comparators]
        return f"one node holding {legs}"
    return ast.unparse(node)


for source in ("1 - 2 - 3", "2 ** 3 ** 4", "a < b < c"):
    tree = ast.parse(source, mode="eval").body
    print(f"  {source:14} {type(tree).__name__:8} {shape(tree)}")
""")


lesson.md(f"""
{figure("shape-follows-rule", "a table of three expressions, the grammar rule that matches each, and the tree shape that comes out")}

The third row is the one people find odd the first time. `a < b < c` is not `(a < b) < c` and it is not `a < (b < c)`. It is a single `Compare` node holding three operands and two operators, because the rule collects a list rather than recursing. That is why chained comparison short circuits and why `a < b < c` evaluates `b` exactly once. None of that is special casing in the evaluator. It is a `+` in a grammar file.

## Keywords the tokenizer knows, and keywords only the parser knows

The grammar tells the generator about keywords using quotes, and which quotes you use changes what happens. {cite("Grammar/python.gram:32-34@v3.15.0rc1")} spells out the convention: single quotes mean a real reserved word, double quotes mean a soft keyword.

A reserved word is easy. `class` is `class` everywhere, the tokenizer has the list, and you cannot use it as a name. A {term("soft keyword")} is a word that is a keyword only where the grammar happens to be looking for one. `match` at {cite("Grammar/python.gram:488@v3.15.0rc1")} is the well known example, and there are four others.

{lesson.claim("a soft keyword can be a keyword and an ordinary variable name in the same file, and a reserved word cannot")}
""")


lesson.code(
    """
import keyword

print(f"  reserved words, the tokenizer knows every one:  {len(keyword.kwlist)}")
print(f"  soft keywords, only the parser knows them:      {keyword.softkwlist}")
print()

SOURCE = \"\"\"
match = "a variable called match"
match match:
    case "a variable called match":
        result = "and a match statement, four lines later"
\"\"\"

names = {}
exec(compile(SOURCE, "<here>", "exec"), names)
print(f"  used as a name:    {names['match']!r}")
print(f"  used as a keyword: {names['result']!r}")
print()

for source in ("class = 1", "match = 1"):
    try:
        compile(source, "<here>", "exec")
        print(f"  {source:12} compiles fine")
    except SyntaxError as unhappy:
        print(f"  {source:12} {unhappy.msg}")
""",
    differs="3.15 added `lazy` to the soft keyword list, so 3.14 prints four names here rather than five.",
)


lesson.md(f"""
{figure("hard-and-soft", "a side by side comparison of a hard keyword and a soft keyword")}

Notice what a soft keyword needs. To know whether `match` is a keyword, you have to look at what comes after it: a subject expression and a colon and a newline and an indent. A parser that made up its mind one token at a time could not do that. A parser that can try an alternative, fail, and back up to where it started can, and backing up is what a {term("PEG parser", "PEG parser")} does for a living.

That is the trade. Backtracking gets you soft keywords and it gets you a grammar with no separate operator precedence machinery, and the bill arrives as repeated work, which the generated parser pays down with the memo table you saw in the recording.

## Nearly a quarter of the grammar is apologies

Here is a number that surprises people. Of the 277 rules in `Grammar/python.gram`, 68 have names beginning with `invalid_`. Those rules do not parse Python. They match things that are almost Python, and their only job is to produce a better message than `invalid syntax`.

They are also switched off most of the time. {cite("Grammar/python.gram:35-43@v3.15.0rc1")} explains the arrangement in the file's own header: the first pass ignores every `invalid_` rule, and only if that pass fails does a second pass run with all of them turned on. You can see both halves in {cite("Parser/pegen.c:939-971@v3.15.0rc1#_PyPegen_run_parser")}, and the flag being flipped between them at {cite("Parser/pegen.c:871-884@v3.15.0rc1#reset_parser_state_for_error_pass")}.

{lesson.claim("the wording of a syntax error is written in the grammar file, and code that no invalid_ rule matches falls back to a generic message")}
""")


lesson.code("""
SOURCES = (
    "print 'hi'",
    "x = 1 if True",
    "try:\\n    pass\\n",
    "from a import b, c,",
    "for x in 1, 2 print(x)",
)

for source in SOURCES:
    try:
        compile(source, "<here>", "exec")
    except SyntaxError as unhappy:
        print(f"  {source.replace(chr(10), ' / '):26} {unhappy.msg}")
""")


lesson.md(f"""
The first four messages are strings you can go and find. `Missing parentheses in call to '%U'` is at {cite("Grammar/python.gram:1248@v3.15.0rc1")}, `expected 'else' after 'if' expression` at {cite("Grammar/python.gram:1270@v3.15.0rc1")}, `expected 'except' or 'finally' block` at {cite("Grammar/python.gram:1471@v3.15.0rc1")}, and `trailing comma not allowed without surrounding parentheses` at {cite("Grammar/python.gram:1451-1453@v3.15.0rc1")}. They are not in a table of error strings somewhere. They sit at the end of the rule that recognises the mistake, next to the pattern that catches it.

The last line is the control. `for x in 1, 2 print(x)` is a real mistake and there is no `invalid_` rule for it, so the second pass finds nothing and you get the generic message. That is what a syntax error looks like when nobody has written the apology yet, and writing one is a very approachable first contribution to CPython.

{figure("two-passes", "a flow from the first parse to a second parse with the invalid rules turned on")}

{figure("a-quarter-is-apologies", "a bar chart comparing 209 rules that parse python with 68 rules that only explain failures")}

Paying for good messages only on failure is the reason this costs nothing in the normal case. A file that parses never runs a single `invalid_` rule.

## What one line of grammar is carrying

Pull one alternative apart and you can see everything the generator needs from it.

```
sum[expr_ty]:
    | a=sum '+' b=term {{ _PyAST_BinOp(a, Add, b, EXTRA) }}
```

The name and the return type in brackets become the signature of a C function. The `|` starts an alternative, and alternatives are tried in order, first match wins. The `a=` and `b=` name the pieces so the last part can reach them. And that last part, the C in braces, is the action: it builds the {term("abstract syntax tree", "AST")} node.

{figure("what-a-rule-carries", "a stack of the four things one line of grammar carries")}

The action is why this is a compiler front end and not a syntax checker. There is no separate pass that walks a parse tree and turns it into an AST. The parser builds the AST as it goes, one action at a time, and the names in those actions are names you already know from the `ast` module.

{lesson.claim("the node types you see from the ast module are named directly in the grammar's actions")}
""")


lesson.code("""
import ast

for source in ("a + b", "-a", "a if b else c", "[x for x in y]", "a < b < c", "f(x)"):
    node = ast.parse(source, mode="eval").body
    print(f"  {source:16} ast.{type(node).__name__}")
""")


lesson.md("""
`_PyAST_BinOp` in the grammar is `ast.BinOp` here. `_PyAST_UnaryOp` is `ast.UnaryOp`. The mapping is that direct, because both come from the same description of the tree in `Parser/Python.asdl`, which is the subject of F04.

## Try it yourself

1. Find the rule for `term` in the grammar and predict the shape of `8 / 4 / 2` before you run it. Then check with the `shape` helper above.
2. `a in b in c` chains too. Which of the three rules you looked at does that go through, and does the answer surprise you?
3. Take one of the five soft keywords and try to break it. Can you write a line where `type` is both a name and a keyword? What about `_`?
4. Write five bad lines of Python and sort them into ones that get a specific message and ones that get `invalid syntax`. Then go and find the specific ones in the grammar file.
5. `2 ** -3` parses, but `2 ** ~3` does too and `-2 ** 3` is `-(2 ** 3)`. Read the `power` and `factor` rules and work out why all three are true.

## What just happened

Nobody writes Python's parser. A program in the source tree reads `Grammar/python.gram` and writes `Parser/parser.c`, and the same program will write a parser in Python instead of C, which is what the recording showed.

Because the parser is generated, the grammar file is where the behaviour lives. Associativity is which side of its own rule a rule names itself on. Soft keywords are a matter of which quotes the grammar used. Error messages are strings written next to the pattern that catches the mistake.

Sixty eight of the 277 rules exist only to explain failures, and they are switched off until the first parse has already failed. A file that parses pays nothing for them.

Every alternative ends in an action that builds an AST node, so parsing and tree building are the same pass. There is no parse tree sitting between the tokens and the AST.

## What is next

F04 is the AST itself. The actions you saw at the end of every rule name node types, and those node types are described in yet another generated file, `Parser/Python.asdl`, which produces the C structs, the Python classes and the visitor scaffolding all at once.

Two generated things in a row is not a coincidence. The front end leans on code generation harder than any other part of CPython, and F04 is where the reason becomes obvious.
""")


raise SystemExit(lesson.save())
