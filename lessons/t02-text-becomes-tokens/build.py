#!/usr/bin/env python
"""T02. Text becomes tokens.

The first stage in close up. It covers the three things about the tokenizer that catch
people out: indentation is a pair of invented tokens, the tokenizer has never heard of a
keyword, and an f-string is a small language with its own tokens. The indentation section
is backed by a hand transcription of CPython's algorithm in `pyxray.tokens`, which is
differentially tested against the real tokenizer so the lesson cannot start lying.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of
them. `just lessons` checks that the committed notebook still matches this file, so a cell
edited in Jupyter and committed without coming back here fails the build.

The pictures come from `diagrams.py` in this directory. They are looked up on disk rather
than imported, so a diagram that has not been built yet fails here instead of producing a
notebook full of broken images.
"""

from nbbuild import Lesson
from nbdiagram import Diagrams

lesson = Lesson("t02-text-becomes-tokens", "t02")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("t02-text-becomes-tokens").figure

lesson.md(f"""
# T02. Text becomes tokens

{badge}

A Python file is just characters. The {term("tokenizer")} is the part of CPython that cuts those characters into pieces and gives each piece a name: this is a number, that is a name, this one is a plus sign. Each piece is a {term("token")}.

Two of the things people find confusing about Python are decided here and nowhere else.

The first is indentation. Python has no braces, and the reason that works is that the tokenizer adds a token when a block opens and another when it closes. You never type them and you never see them, but the parser does, and to the parser they do the job braces do in C. They are called {term("indent and dedent")}.

The second is f-strings. An f-string is not one string with special handling bolted on. The tokenizer takes it apart, and the code between the braces comes out as ordinary Python tokens.

Here is where this lesson sits. T01 walked past all seven stages. This one stops at the first.

{figure("where-we-are", "the seven stages of running Python, with the tokenizer highlighted")}

By the end you will have run the real tokenizer on your own input, seen it produce tokens that are not in your file, read the indentation algorithm in full, and broken it three different ways on purpose.

No C required, and everything here runs on a normal Python.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Parser/lexer/lexer.c:1626-1635@v3.15.0rc1#_PyTokenizer_Get`.

Read it as four parts: the file, the lines, the release those line numbers belong to, and the name of the function they are inside.

Every reference is a link, and every one is checked against the pinned source on each change, so a stale reference fails the build instead of sending you somewhere wrong. The function name on the end is what makes the check work. Line numbers move whenever somebody adds code above them, and a moved line number points at something that looks plausible and is not.

You never have to read any of it. The references are there so you can go deeper when you want to, and so you can check that this lesson is not making things up.
""")


lesson.md("""
## Setup

Colab does not come with the small toolkit these lessons use, so the next cell installs it. If you are running this from a checkout of the repository it is already there and the cell does nothing.
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

Almost nothing in this lesson changed between 3.14 and 3.15. The tokenizer is old code and it does not move much.

Every lesson still starts by naming the exact build that is about to produce your output. If something does change one day, you want to know which side of it you were on.
""")


lesson.code("""
import pyxray

pyxray.show()
""")


lesson.md(f"""
## It is a real program, and you are about to run it

CPython's tokenizer is hand written C rather than a generated table or a pile of regular expressions. It lives in `Parser/lexer/lexer.c`, and the way in is {cite("Parser/lexer/lexer.c:1626-1635@v3.15.0rc1#_PyTokenizer_Get")}. Call it and you get one token. Call it again and you get the next one.

The standard library has a `tokenize` module, and for most of Python's life that module was a separate reimplementation written in Python. It drifted away from the C over the years, and it disagreed with it in small ways, which made it a poor thing to learn from.

That changed in 3.12, and `tokenize` now calls into the C tokenizer through a small module called `_tokenize`. So when you tokenize something in a moment, the code doing the work is the code cited above rather than a copy of it.
""")


lesson.code("""
import _tokenize

print(_tokenize)
print("has TokenizerIter:", "TokenizerIter" in dir(_tokenize))
""")


lesson.md("""
## First look

Two lines of Python, and every token the tokenizer produces for them.

`pyxray.tokens.table` is a thin wrapper. It runs `tokenize` and lines the output up so it is easy to read. The columns are where the token starts, what it is called, and the exact text it covers.
""")


lesson.code(r"""
from pyxray import tokens

SOURCE = "if answer:\n    print(answer)\n"

print(tokens.table(SOURCE))
""")


lesson.md("""
That is a lot of rows for two short lines. The next cell draws the first line against the text it came from, so you can see which characters became which token.
""")


lesson.code("""
print(tokens.ribbon(SOURCE))
""")


lesson.md(f"""
The same idea on a different line, as a picture. Notice that `INDENT` covers the four spaces at the front and carries them as its text.

{figure("one-line-many-tokens", "one line of source with each token named underneath it")}
""")


lesson.md("""
## Four of those tokens are not in your file

Go back and compare the tokens against what you typed. `ENCODING`, `INDENT`, `DEDENT` and `ENDMARKER` were all added by the tokenizer.

`ENCODING` comes first. It is the tokenizer reporting what it decided your bytes meant. That is a real decision rather than a formality, because a Python file is allowed to declare its own encoding in a comment on line 1 or line 2, and until that is settled the tokenizer cannot read a single character.

`ENDMARKER` comes last. A grammar cannot match on "and then the file ran out", so running out has to arrive as a token like everything else.

`INDENT` and `DEDENT` are the pair most of this lesson is about.
""")


lesson.code("""
for item in tokens.stream(SOURCE):
    if item.synthesized:
        print(f"{item.kind:<12} text {item.text!r:<10} start {item.start}  end {item.end}")
""")


lesson.md("""
## The tokenizer has never heard of keywords

This one explains several later things, so it is worth a minute.

Look at the table again. `if` came back as a `NAME`, not as a keyword and not as an `IF` token. To the tokenizer it is a run of letters, the same kind of thing as `answer` or `print` or `banana`.
""")


lesson.code(r"""
for item in tokens.stream("if x:\n    pass\n"):
    if item.text in {"if", "x", "pass"}:
        print(f"{item.text!r:<8} is a {item.kind}")
""")


lesson.md(f"""
So where do keywords come from? From the parser, one step later.

{figure("who-knows-about-keywords", "the tokenizer handing a NAME token to the parser")}

When the parser pulls a token off the tokenizer, it checks whether a `NAME` happens to spell a keyword, and changes the token's type if it does. That is {cite("Parser/pegen.c:162-179@v3.15.0rc1#_get_keyword_or_name_type")}. It looks the name up by length first, which tells you something about how often it runs: once for every identifier in your program.

{figure("name-or-keyword", "two words that both start as NAME and end up as different token types")}

This split is why Python can have soft keywords. `match` and `case` are keywords in one place in the grammar and ordinary variable names everywhere else. The tokenizer never committed to either, so the parser gets to decide from context. That is how code using `match` as a variable name in 3.9 kept working in 3.10.
""")


lesson.code(r"""
print(tokens.table("match = 1\n"))
""")


lesson.md("""
## Operators are all one token type

Every operator and every piece of punctuation comes back as `OP`. Which operator it was is recorded separately, as the exact type.

`pyxray.tokens` keeps both and prints them as `OP/PLUSEQUAL` when they differ.
""")


lesson.code(r"""
print(tokens.table("a += b[0]\n"))
""")


lesson.md("""
## Indentation, one piece at a time

Now the part most people come here for.

`INDENT` and `DEDENT` are the tokens that stand in for the braces other languages make you type. The thing to hang on to is that they are not symmetric.
""")


lesson.code("""
pair = {item.kind: item for item in tokens.stream(SOURCE)}

for name in ("INDENT", "DEDENT"):
    item = pair[name]
    print(f"{name:<8} text {item.text!r:<8} start {item.start}  end {item.end}")
""")


lesson.md(f"""
`INDENT` has text in it. There really are four spaces at the start of that line, and the tokenizer hands them over.

`DEDENT` has nothing in it. It is zero characters wide, sitting at the first column of the line that ended the block, and no part of your file corresponds to it. If you have ever gone looking for the dedent in the source text, that is why you did not find it: it is a message rather than a substring.

{figure("indent-is-not-symmetric", "INDENT four columns wide and DEDENT with no width at all")}

The second half of the asymmetry is arithmetic, and it catches people out.

Going right produces exactly one `INDENT`, however far right you went. Going left produces one `DEDENT` for every level you closed, so a single line can produce three of them.
""")


lesson.code(r"""
DEEP = "if a:\n    if b:\n        if c:\n            d = 1\ne = 2\n"

for item in tokens.stream(DEEP):
    if item.kind in ("INDENT", "DEDENT"):
        print(f"{item.kind:<8} at line {item.start[0]}, column {item.start[1]}")
""")


lesson.md("""
Three indents going in, and three dedents coming out. All three dedents are reported at the same spot, the start of line 5, back to back, before the tokenizer even looks at `e`.
""")


lesson.md(f"""
## The whole algorithm

The algorithm is smaller than you would expect.

There is a stack of column numbers. It starts with one entry, zero. For every line that has real code on it:

- Column equals the top of the stack: emit nothing.
- Column is bigger: push it and emit one `INDENT`.
- Column is smaller: pop until the top matches, emitting one `DEDENT` per pop. If the stack runs out without a match, that is the "unindent does not match any outer indentation level" error.

That is the whole feature, and here it is running:

{figure("how-the-stack-moves", "four lines of source with the indent stack after each one")}

It comes to about thirty lines of C in {cite("Parser/lexer/lexer.c:500-530@v3.15.0rc1#tok_get_normal_mode")}. The stack is a plain array declared in {cite("Parser/lexer/state.h:88-107@v3.15.0rc1#altindstack")}, one hundred entries long, which is where the limit on how deeply you can nest comes from.

One detail matters if you ever write one of these yourself. The dedents are not handed out immediately. The tokenizer counts them into a field called `pendin` and then returns them one per call until the count reaches zero, at {cite("Parser/lexer/lexer.c:616-634@v3.15.0rc1#pendin")}. The function can only return one token, so a line that closes three blocks has to be remembered across three calls.

`pyxray.tokens.indent_trace` is that algorithm transcribed into Python, rather than a summary of it or pseudocode for it. The test suite runs it and the real CPython tokenizer over the same set of programs and requires the same answer from both, so if the C ever changes, this lesson fails its tests instead of quietly going wrong.
""")


lesson.code("""
print(tokens.indent_report(DEEP))
""")


lesson.md("""
The `stack` column is the whole story, and everything else in that table is bookkeeping.

Ignore the `alt` column for one more minute. It gets its own section, because it answers a question nobody has asked you yet.

Same thing again as a shape, which is easier to take in at a glance. The bars step right as blocks open and drop back as they close.
""")


lesson.code("""
print(tokens.staircase(DEEP))
""")


lesson.md("""
Notice that blank lines and comment only lines never show up in that trace. They are thrown out before any comparison happens, which is why you can indent a comment to a ridiculous column and nothing breaks.
""")


lesson.code(r"""
print(tokens.indent_report("x = 1\n            # what am I even doing here\n\ny = 2\n"))
""")


lesson.md(f"""
## A tab is not worth a fixed number of spaces

Ask around and people will tell you a tab is four columns, or eight, or that it depends on your editor. For the tokenizer it is none of those. A tab moves to the next multiple of eight, so what a tab is worth depends on what came before it.

{figure("where-a-tab-lands", "the same tab character landing on a tab stop from three different starting columns")}

Eight is neither configurable nor a convention. It is a constant in {cite("Parser/lexer/state.c:5-33@v3.15.0rc1#TABSIZE")} with `/* Never change this */` written above it, and that comment is not about style. The number decides whether two lines count as equally indented, so it is part of the language.
""")


lesson.code(r"""
for text in ["\tx", "       \tx", "        \tx", "    x"]:
    col, altcol = tokens.measure(text)
    print(f"{text!r:<16} lands at column {col:>3}")
""")


lesson.md("""
Seven spaces then a tab puts you at column 8. Eight spaces then a tab puts you at column 16. Same tab character, worth one column in the first case and eight in the second.
""")


lesson.md(f"""
## What "mixed tabs and spaces" actually means

Now the `alt` column.

The tokenizer measures every line twice. Once with a tab stop of 8, which is the real answer, and once with a tab stop of 1, which is used for nothing except comparison. That second constant is `ALTTABSIZE`, and you can watch both counts being kept in step at {cite("Parser/lexer/lexer.c:520-530@v3.15.0rc1#ALTTABSIZE")}.

Why bother? Because two lines can be indented the same under a tab stop of 8 and differently under any other. A file like that looks right to you, looks wrong to a colleague whose editor is set to 4, and neither of you will work out why by reading it.

Measuring twice catches that case. If two lines agree on the real count but disagree on the alternate count, their agreement was luck rather than intent, and the tokenizer refuses the file.

{figure("two-counts-of-one-line", "one line measured with a tab stop of 8 and again with a tab stop of 1")}

Lines indented only with spaces produce the same number twice, so a file that never uses a tab cannot trip this.
""")


lesson.code(r"""
for text in ["    x", "\tx", "\t\tx"]:
    col, altcol = tokens.measure(text)
    verdict = "agree" if col == altcol else "DISAGREE"
    print(f"{text!r:<10} tab stop 8 -> {col:>3}   tab stop 1 -> {altcol:>3}   {verdict}")
""")


lesson.md(f"""
## Breaking it on purpose, three ways

`pyxray.tokens.failure` runs the tokenizer and hands the error back as an object instead of raising it, so you can read the message without a traceback in the way.

First, the case from the last section. Line 2 is indented with one tab and line 3 with eight spaces. Under a tab stop of 8 those are the same column, so it looks fine. Under a tab stop of 1 they are not, so the tokenizer knows the match was an accident. The check is {cite("Parser/tokenizer/helpers.c:90-97@v3.15.0rc1#_PyTokenizer_indenterror")}, which does nothing except record the error code and give up.
""")


lesson.code(r"""
TABS = "if x:\n\ty = 1\n        z = 2\n"

print(repr(TABS))
print(tokens.failure(TABS))
""")


lesson.md(f"""
Second, a dedent to a column nobody ever indented to.

The stack holds 0 and 2. Line 3 arrives at column 1, which is smaller than 2, so the tokenizer pops. Now the top is 0, and 1 is not 0. There is nothing left to pop and still no match, so it stops.

{figure("a-dedent-with-no-home", "an indent stack that runs out before it finds a matching column")}
""")


lesson.code(r"""
STRAY = "if x:\n  y = 1\n z = 2\n"

print(repr(STRAY))
print(tokens.failure(STRAY))
""")


lesson.md("""
Third, a bracket that never closes. This one raises a different exception type, `TokenError` rather than a `SyntaxError`, and it carries its position in its arguments rather than as attributes. The inconsistency is historical rather than deliberate.
""")


lesson.code(r"""
print(tokens.failure("x = (1,\n"))
""")


lesson.md("""
The Python transcription raises the same errors for the same reasons. That is part of how it is tested.
""")


lesson.code("""
for source, name in [(TABS, "tabs and spaces"), (STRAY, "stray dedent")]:
    try:
        tokens.indent_trace(source)
    except (TabError, IndentationError) as error:
        print(f"{name:<18} {type(error).__name__}: {error}")
""")


lesson.md(f"""
## A newline that is not a newline

There are two tokens for the end of a line, and the difference matters.

`NEWLINE` ends a logical line, which is the unit the grammar cares about. `NL` is a line ending that did not end anything, because a bracket was open.

The tokenizer picks between them in {cite("Parser/lexer/lexer.c:804-827@v3.15.0rc1#tok_extra_tokens")}, and the test is one field counting how many brackets are open. That single counter is all of implicit line joining.

It is also why indentation is not measured inside brackets. The indentation code only runs when that counter is zero, so you can lay out a function call however you like and nothing complains.
""")


lesson.code(r"""
print(tokens.table("x = (1,\n     2)\n"))
""")


lesson.md(f"""
One `NL` where line 1 ended, one `NEWLINE` where the statement ended, and no `INDENT` for the five spaces in front of the 2.

There is a second thing worth noticing, which is that the parser never sees that `NL`. The tokenizer has a flag for returning extra tokens, and the `tokenize` module switches it on, because a code formatter needs to see comments and blank lines. When the compiler runs the tokenizer that flag is off, and those tokens are dropped inside the loop instead of being returned.

{figure("two-token-streams", "the token stream tokenize returns above the shorter one the compiler receives")}

So the token stream you have been reading all lesson is bigger than the one the compiler works from. Most people assume it is the other way around.
""")


lesson.code(r"""
for source in ["x = 1  # a comment\n", "x = (1,\n     2)\n"]:
    extra = [item.kind for item in tokens.stream(source) if item.kind in ("COMMENT", "NL")]
    print(f"{source!r:<28} tokenize adds {extra}")
""")


lesson.md(f"""
## A backslash leaves nothing at all

The other way to join two lines is a trailing backslash, and it works differently again. It produces no token at all, not even a marker. The two physical lines become one, and the only trace left is in the position numbers, where the tokens jump from line 1 to line 2 in the middle of an expression.

The function is {cite("Parser/lexer/lexer.c:434-443@v3.15.0rc1#tok_continuation_line")}, and the one thing it insists on is that the backslash is the very last character on the line. A single space after it is an error, which is worth knowing the next time you spend five minutes staring at one.
""")


lesson.code(r"""
print(tokens.table("x = 1 + \\\n    2\n"))
""")


lesson.md(f"""
## An f-string is not one token

Until 3.12, an f-string arrived as a single `STRING` token holding the whole thing, braces and all. The compiler pulled it apart later using a second parser written for the job. That is where the odd restrictions came from: you could not reuse the same quote inside, you could not put a backslash in, and error messages pointed at the wrong place.

PEP 701 removed all that, and the tokenizer now handles f-strings directly with the pieces coming out separately.

The trick is a mode switch. The tokenizer has two modes, and {cite("Parser/lexer/lexer.c:1615-1624@v3.15.0rc1#tok_get")} is the two line function that picks one on every call.

{figure("the-mode-switch", "the tokenizer moving between normal mode and f-string mode")}

As soon as it hits an opening brace it goes back to normal mode, which is why the expression inside is tokenized as ordinary Python by the ordinary code.
""")


lesson.code(r"""
print(tokens.table('f"total {count + 1} items"\n'))
""")


lesson.md("""
`FSTRING_START` holds the prefix and the opening quote. `FSTRING_MIDDLE` holds the literal text between braces. The expression is a `NAME`, an `OP` and a `NUMBER`, the same as it would be anywhere else in your program.

That is why everything PEP 701 allowed arrived at once. Same quotes nested inside, backslashes, f-strings inside f-strings. None of it needed a special case, because there was no second parser left to teach.
""")


lesson.code(r"""
print(tokens.table("f\"{f'{1 + 1}'}\"\n"))
""")


lesson.md(f"""
## Template strings get their own tokens

Template strings are new in 3.14. They are lexed the same way, but with their own token kinds rather than borrowing the f-string ones.

The tokenizer works out which family it is in from the prefix letter, at {cite("Parser/lexer/lexer.c:1103-1128@v3.15.0rc1#string_kind")}, and it has to cope with `rt` and `tr` as well as plain `t`.

Keeping the kinds separate is what lets the grammar build a different type of object for each, and it means any tool reading the token stream can tell them apart without inspecting the text.
""")


lesson.code(r"""
print(tokens.table('t"total {count} items"\n'))
""")


lesson.md("""
## Exercises

Each one is a prediction followed by a check. Write your answer down before running the cell. Getting it wrong is the useful outcome, because it shows you where your idea of the tokenizer differs from the real one.

**One.** How many `DEDENT` tokens does this produce, and where?
""")


lesson.code(r"""
print(tokens.table("if a:\n    if b:\n        c = 1\nd = 2\n"))
""")


lesson.md("""
**Two.** This indents by three, then by two more, then drops back five. Does it tokenize? What does the stack do on the way?
""")


lesson.code(r"""
print(tokens.indent_report("if a:\n   b = 1\n   if c:\n     d = 2\ne = 3\n"))
""")


lesson.md("""
**Three.** One of these tokenizes and one does not. Which, and why? The answer is about how a tab measures against the line above it, not about how many characters each line has.
""")


lesson.code(r"""
for source in ["if x:\n\ty = 1\n\tz = 2\n", "if x:\n\ty = 1\n        z = 2\n"]:
    problem = tokens.failure(source)
    print(f"{source!r}\n    {problem or 'tokenizes cleanly'}\n")
""")


lesson.md("""
**Four.** Does an empty file produce any tokens at all? How many?
""")


lesson.code("""
print(tokens.table(""))
""")


lesson.md("""
**Five.** This one is worth getting wrong. Is the word `if` inside a string tokenized as a `NAME`? Write your answer down before you run it.
""")


lesson.code(r"""
print(tokens.table('x = "if"\n'))
""")


lesson.md("""
**Six.** Take a source file and count how many of its tokens the compiler never sees. Point it at something of your own, or leave it as it is to run against `pyxray` itself.
""")


lesson.code("""
import inspect
from collections import Counter

text = inspect.getsource(tokens)
counts = Counter(item.kind for item in tokens.stream(text))
invisible = counts["COMMENT"] + counts["NL"]

print(f"{sum(counts.values())} tokens, of which {invisible} are thrown away before the parser")
print(counts.most_common(8))
""")


lesson.md("""
## What you now know

The tokenizer is hand written C that returns one token at a time, and the `tokenize` module you just used calls it rather than imitating it.

It adds tokens of its own. `ENCODING` and `ENDMARKER` bracket the stream. `INDENT` and `DEDENT` carry the block structure that other languages spell with braces.

Indentation is a stack of column numbers and three comparisons. Bigger than the top means push and emit one `INDENT`, smaller means pop and emit one `DEDENT` per level, and equal means emit nothing.

A tab moves to the next multiple of eight, and every line is measured a second time with a tab stop of one, so lining up by accident can be told apart from lining up on purpose. That is the mixed tabs and spaces check.

The tokenizer has never heard of keywords. The parser turns a `NAME` into a keyword afterwards, which is what makes soft keywords possible.

A newline inside brackets is a different token from one that ends a statement, and a backslash continuation is not a token at all.

An f-string is a run of tokens with real Python in the middle, because the tokenizer switches modes instead of handing the problem to a second parser.

## What is next

T03 takes this token stream and builds a tree from it. The question worth asking there is why the tree is so much smaller than the stream, and where all the punctuation went.
""")

raise SystemExit(lesson.save())
