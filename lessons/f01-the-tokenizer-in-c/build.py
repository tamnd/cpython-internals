#!/usr/bin/env python
"""F01. The tokenizer, in C.

The first lesson of the front end part, and the fifteenth overall. T02 already showed what
the tokenizer does, from the outside, in Python. This one is the same machine from the inside:
where the token numbers come from, the four ways text gets into it, the eight fields that hold
all of its memory, and why some of its error messages are written in the lexer and others are
written a hundred lines away in the parser.

The rule this lesson works to is that nothing here repeats T02. T02 owns the behaviour. F01
owns the C, and every section has to be something a reader could not have learned by calling
`tokenize` and watching what came out.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording

lesson = Lesson("f01-the-tokenizer-in-c", "f01")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("f01-the-tokenizer-in-c").figure

#: The recorded run. It needs a debug build and the -d flag, and a reader has neither.
BUFFER = "f01-one-line-at-a-time"

lesson.md(f"""
# F01. The tokenizer, in C

{badge}

Your file is on disk. The tokenizer has to turn it into {term("token", "tokens")}, and the honest question is how much of your file it is holding while it does that.

The answer is one line. Not the file, not a window, one line, and the lines before it are already gone. Almost everything else about the C tokenizer follows from that.

{figure("one-line-in-the-buffer", "four pointers into a single line of source, with the rest of the file not read yet")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Parser/lexer/state.h:6-8@v3.15.0rc1`.

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
## The token set is a table

Start with the numbers. `NAME` is 1, `NUMBER` is 2, and something has to decide that.

Nothing in the C decides it. `Grammar/Tokens` is a plain text file of one token per line, and the order of the lines is the numbering. A script reads it and writes four files, one of which is the header the {term("tokenizer")} includes and another of which is `Lib/token.py`, the module you have been importing.

{figure("one-table-five-files", "the four files written from Grammar/Tokens and who reads each one")}

Look at what that buys. The C and the Python cannot drift apart on what `NUMBER` means, because neither of them is where the answer lives. {lesson.claim("the token numbers in Lib/token.py are the line order of Grammar/Tokens, and the file says at the top that it was generated")} and the module admits it in its second line.
""")


lesson.code("""
import inspect
import token

print(inspect.getsource(token).splitlines()[1])
print()
print(f"names in tok_name:          {len(token.tok_name)}")
print(f"tokens with a spelling:     {len(token.EXACT_TOKEN_TYPES)}")
print()
for number in range(7):
    print(f"  {number:2}  {token.tok_name[number]}")
""")


lesson.md(f"""
Those first seven are the ones with no spelling: you cannot write an `INDENT` the way you write a `+`. They are lines 6 to 12 of `Grammar/Tokens`, in that order.

The rest of the file has two columns. `LPAR '('` says the token is called `LPAR` and it is spelled `(`. That second column becomes `EXACT_TOKEN_TYPES`, a dict from the spelling to the number, and it is the reason {lesson.claim("every operator arrives as the single type OP and the exact spelling is recovered afterwards from a table, rather than the tokenizer having a separate type for each one")}.
""")


lesson.code("""
import io
import tokenize

for found in tokenize.generate_tokens(io.StringIO("a += b @ c\\n").readline):
    if found.type == token.OP:
        kind = token.tok_name[found.type]
        exact = token.tok_name[found.exact_type]
        print(f"  {found.string:4}  type={kind:4}  exact_type={exact}")
""")


lesson.md(f"""
`+=` and `@` come back as `OP`, and `exact_type` is a lookup in that generated dict. The C tokenizer does the same thing in the same place, from the same table.

If you ever add an operator to Python, this is the file you edit. The comment on the first four lines of `Grammar/Tokens` is there because one place does not update itself: the PEG generator has its own copy, and it has to be edited by hand.

## Four ways in, and then the same lexer

Text reaches the tokenizer four ways, and the whole interface is a ten line header. {cite("Parser/tokenizer/tokenizer.h:6-10@v3.15.0rc1")} declares four constructors, one per kind of input.

{figure("four-front-ends", "the four tokenizer constructors, where each gets its text and who calls it")}

What is nice about this is how little they differ. Each one fills in a `struct tok_state` and sets one field, its {term("underflow")} function, to its own idea of how to get the next line. After that the lexer never asks where the text came from. When it runs out it calls that function pointer, at {cite("Parser/lexer/lexer.c:74-82@v3.15.0rc1")}, and carries on.

Two of the four are one line apart in the same `if`. {cite("Parser/pegen.c:1055-1060@v3.15.0rc1")} picks `_PyTokenizer_FromUTF8` when the caller set `PyCF_IGNORE_COOKIE` and `_PyTokenizer_FromString` when it did not, and the caller that sets it is `compile` when you hand it a `str`. So {lesson.claim("compiling the same source as bytes and as a str goes through two different tokenizer constructors, and the difference shows up as whether a coding cookie is obeyed or ignored")}.
""")


lesson.code("""
COOKIE = b"# -*- coding: ascii -*-\\nname = 'caf\\xe9'\\n"


def compiles(source):
    try:
        compile(source, "<here>", "exec")
    except SyntaxError as unhappy:
        return f"{type(unhappy).__name__}: {unhappy.msg}"
    return "compiles fine"


print("as bytes: ", compiles(COOKIE))
print("as a str: ", compiles(COOKIE.decode("latin-1")))
""")


lesson.md(f"""
Same characters, same {term("coding cookie", "cookie")}, two answers. As bytes the cookie is a promise about the encoding and the tokenizer holds you to it. As a str the bytes question is already settled, so the cookie is treated as a comment and skipped. One `if` in `pegen.c`, two constructors, and a difference you can see from Python.

The other two are `_PyTokenizer_FromFile`, which {cite("Parser/pegen.c:999@v3.15.0rc1")} uses when you run a script, and `_PyTokenizer_FromReadline`, which {cite("Python/Python-tokenize.c:69@v3.15.0rc1")} uses for the `tokenize` module. Every token you looked at in T02 came through that last one.

## It really is one line

Back to the opening claim. A {term("debug build")} compiled with `-d` prints a line to stderr every time the tokenizer runs dry and calls `underflow`, and what it prints is the entire contents of the buffer at that moment, plus the value of `tok->done`.

{lesson.claim("the tokenizer holds one line of your file at a time, and a file that fails to parse gets read more than once", unobservable="the fprintf that prints this is inside an #ifdef Py_DEBUG, so a stock interpreter has no way to show it and the run below is a recording")}

{recording(BUFFER)}
""")


lesson.md(f"""
Read the top block first. Five lines in, six refills out, and the last one is empty with `tok->done = 11`, which is `E_EOF` in {cite("Include/errcode.h:23-24@v3.15.0rc1")}. `10` is `E_OK`, which is worth noticing on its own: these codes do not start at zero, because zero would be ambiguous with a character value.

Now the second block. Same file, one unclosed bracket, and the lines go past ten. A parse that fails runs again with a heavier set of grammar rules turned on so it can produce a better message, at {cite("Parser/pegen.c:957-962@v3.15.0rc1")}, and there is a third walk in {cite("Parser/pegen_errors.c:117-123@v3.15.0rc1")} that tokenizes the whole input looking for unclosed brackets specifically. F05 is about that machinery. For now the useful part is that a good error message costs a re-read, and CPython has decided that is a fine price for a file that was going to fail anyway.

## The whole memory of it

So if the buffer is one line, what carries across lines?

`struct tok_state` runs from {cite("Parser/lexer/state.h:74-112@v3.15.0rc1")} to line 140. That is about fifty fields, and most of them are plumbing: buffers, the encoding, the readline callable, the f-string mode stack. Eight of them are the actual state machine.

{figure("the-state-that-matters", "the eight fields of struct tok_state that decide the token stream")}

Two of those eight are fixed size arrays, and that is where Python's two least famous limits come from. {cite("Parser/lexer/state.h:6-8@v3.15.0rc1")} sets `MAXINDENT` to 100 and `MAXLEVEL` to 200, so {lesson.claim("the deepest you can indent and the deepest you can nest brackets are both fixed at compile time, and you can find both numbers from Python without reading the header")}.
""")


lesson.code(
    """
def deepest(build):
    \"\"\"Grow the source until it stops compiling, and return the last size that worked.\"\"\"
    size = 1
    while True:
        try:
            compile(build(size), "<here>", "exec")
        except SyntaxError:
            return size - 1
        size += 1


def indented(size):
    return "".join(" " * n + "if True:\\n" for n in range(size)) + " " * size + "pass\\n"


def nested(size):
    return "x = " + "(" * size + ")" * size + "\\n"


print(f"deepest indentation that compiles:  {deepest(indented)}")
print(f"deepest bracket nesting:            {deepest(nested)}")
""",
    varies=(
        "These are the two array sizes in state.h, so an interpreter someone rebuilt with "
        "different limits will print different numbers. Every stock build agrees."
    ),
)


lesson.md(f"""
200 is `MAXLEVEL` exactly. 99 is `MAXINDENT` minus one, and the reason is a `+1` in the comparison at {cite("Parser/lexer/lexer.c:582-586@v3.15.0rc1")}: the check runs before the push, so the hundredth level is refused rather than the hundred and first. Small thing, but this is the kind of off by one that a reimplementation gets wrong and only finds out about when someone's generated code stops compiling.

## The counter that owes you tokens

Here is the part T02 could see the shape of but not the reason for.

When a line is less indented than the last one, several blocks close at once, and several `DEDENT` tokens have to come out. But `tok_get` returns one token per call. So it cannot return three.

What it does instead is keep a counter. {cite("Parser/lexer/lexer.c:571-609@v3.15.0rc1")} is the indentation comparison, and in the dedent branch it pops the stack in a loop and does `tok->pendin--` on each pop. It has now not returned anything. Then on the next call, and the call after that, {cite("Parser/lexer/lexer.c:616-633@v3.15.0rc1")} sees a non zero `pendin`, moves it one step towards zero, and returns a single `DEDENT`.

{figure("pendin-drains", "one line ending becoming two DEDENT tokens through the pendin counter")}

The tell is in the positions. Those tokens are made without reading any characters, so {lesson.claim("every DEDENT from the same line ending reports the same position and an empty string, because they are drained from a counter rather than matched against text")}.
""")


lesson.code("""
SOURCE = "if a:\\n    if b:\\n        if c:\\n            pass\\nx = 1\\n"

for found in tokenize.generate_tokens(io.StringIO(SOURCE).readline):
    if found.type in (token.INDENT, token.DEDENT):
        name = token.tok_name[found.type]
        print(f"  {name:7} start={found.start}  end={found.end}  string={found.string!r}")
""")


lesson.md(f"""
Three `INDENT` tokens that each cover real spaces, and three `DEDENT` tokens that all sit at row 5 column 0 and cover nothing. That is `pendin` draining, seen from Python.

The empty string is worth one more note. In the parser's mode the tokenizer does not even fill in the position for these, and the `if (tok->tok_extra_tokens)` guard you can see in that block is what turns it on for `tokenize`. The parser does not need it. Your editor does.

## Two kinds of error

Last piece, and it is the one that makes the tokenizer's error messages make sense.

The tokenizer reports trouble two different ways. Sometimes it knows exactly what is wrong and calls {cite("Parser/tokenizer/helpers.c:67-76@v3.15.0rc1#_PyTokenizer_syntaxerror")} with the message written right there in the lexer. Sometimes it sets `tok->done` to a number from `errcode.h` and returns, and the words get chosen much later by a `switch` in {cite("Parser/pegen_errors.c:34-73@v3.15.0rc1")}.

{figure("two-kinds-of-error", "messages written in the lexer against error codes translated by the parser")}

{lesson.claim("some tokenizer errors carry their message from the lexer and others carry only a number that the parser turns into words, and which is which explains why a TabError and an unterminated string feel like they come from different places")}
""")


lesson.code("""
DEEP = "".join(" " * n + "if True:\\n" for n in range(120)) + " " * 120 + "pass\\n"

CASES = [
    ("an unclosed quote", "x = 'abc", "lexer.c"),
    ("a bad number", "x = 1_", "lexer.c"),
    ("201 open brackets", "x = " + "(" * 201, "lexer.c"),
    ("a tab after spaces", "if 1:\\n\\tif 1:\\n        pass\\n \\tpass\\n", "pegen_errors.c"),
    ("120 levels of indent", DEEP, "pegen_errors.c"),
    ("a dedent to nowhere", "if 1:\\n    if 1:\\n        pass\\n      pass\\n", "pegen_errors.c"),
    ("junk after a backslash", "x = 1 \\\\ 2\\n", "pegen_errors.c"),
]

for label, source, written_in in CASES:
    try:
        compile(source, "<here>", "exec")
        said = "no error at all"
    except SyntaxError as unhappy:
        said = f"{type(unhappy).__name__}: {unhappy.msg}"
    print(f"  {label:24} {written_in:16} {said}")
""")


lesson.md(f"""
The top three messages are string literals in `lexer.c`. The bottom four are not: the lexer set `E_TABSPACE`, `E_TOODEEP`, `E_DEDENT` and `E_LINECONT`, and every word you see was picked by that `switch`.

You can feel the difference in the wording. The lexer knows it was looking at a number, so it says so. The parser only has a number, so it says the general thing. That is also why `TabError` and `IndentationError` exist as separate exception types at all: the `switch` is the only place that gets to choose an exception class, and it chooses from four.

## Try it yourself

1. Add a line to `Grammar/Tokens` in a checkout, run `python Tools/build/generate_token.py all`, and read the diff. Four files should change and one of them is documentation.
2. Take the `deepest` helper and point it at f-string nesting instead. `MAXFSTRINGLEVEL` is in the same header. Do you get the number the header says, or one less, and why?
3. Find a source file where the tokenizer's own error is wrong about what you meant, then look up which of the two paths produced it.
4. `tokenize.generate_tokens` gives you `NL` where the parser sees nothing. Print both streams for a file with comments and blank lines, and count the difference.
5. Read {cite("Parser/lexer/lexer.c:571-609@v3.15.0rc1")} once, slowly. It is 39 lines and it is the whole of Python's indentation.

## What just happened

The token numbers are not written anywhere in the C. `Grammar/Tokens` is 78 lines of table and four files are generated from it, including the `token` module you import.

Four constructors get text into the tokenizer and they differ in one field, a function pointer called `underflow`. Which one you get depends on whether you passed `str` or `bytes` or a filename or a callable, and the `str` and `bytes` cases disagree about coding cookies.

The buffer holds one line. A file that parses is read once. A file that does not is read again, because a good error message is worth a second pass.

Everything that survives between lines lives in eight fields. Two of them are fixed arrays, which is where the 100 and the 200 come from, and one of them is a counter called `pendin` that explains why three `DEDENT` tokens all claim the same position.

Errors come out two ways: a message written in the lexer, or a number that the parser turns into words. Which one you got tells you where to look.

## Where this goes next

F02 stays in the same files and does f-strings, which since 3.12 are tokenized properly rather than pattern matched, and t-strings, which 3.14 added. That is the `tok_mode_stack` field this lesson skipped over.

After that the token stream stops being the subject and becomes the input. F03 is the PEG grammar, which is CPython's second machine readable table, and it is much bigger than this one.
""")


raise SystemExit(lesson.save())
