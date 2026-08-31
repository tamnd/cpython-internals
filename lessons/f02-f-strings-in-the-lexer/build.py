#!/usr/bin/env python
"""F02. f-strings in the lexer.

The second lesson of the front end part, and the sixteenth overall. F01 left one field of
`struct tok_state` alone on purpose: `tok_mode_stack`, the thing that makes f-strings work.
This lesson is that field, and the small language the lexer switches into when it meets one.

The rule this lesson works to is that everything shown has to be visible from Python. The
mode stack cannot be printed, but its depth limit can be found by binary search, its brace
counting can be seen in the token positions, and the copy it keeps of your source text is
sitting in the output of any f-string that ends in an equals sign.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("f02-f-strings-in-the-lexer", "f02")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("f02-f-strings-in-the-lexer").figure

lesson.md(f"""
# F02. f-strings in the lexer

{badge}

An f-string looks like a string. It is quoted like one, it sits in your source like one, and for the first six years of its life it was tokenized like one: the lexer grabbed the whole thing as a single `STRING` and a separate hand written parser picked it apart afterwards.

That is not what happens any more. Since 3.12 the lexer walks into an f-string, tokenizes what it finds in the braces with the same code that tokenizes the rest of your file, and walks back out. Nine tokens for something that used to be one.

{figure("one-string-many-tokens", "an f-string broken into a start token, two middle tokens, the tokens of the expression, and an end token")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Parser/lexer/state.h:8@v3.15.0rc1`.

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
## Nine tokens, not one

Start by putting the two side by side. Same characters, one `f` of difference.

{lesson.claim("a plain string is a single STRING token, and an f-string with the same characters is a start token, some middle tokens, the ordinary tokens of the expression, and an end token")}
""")


lesson.code("""
import io
import token
import tokenize

SKIP = (token.NEWLINE, token.NL, token.ENDMARKER, token.INDENT, token.DEDENT)


def tokens(source):
    \"\"\"Every token in one line of source, without the line and block bookkeeping.\"\"\"
    found = tokenize.generate_tokens(io.StringIO(source).readline)
    return [one for one in found if one.type not in SKIP]


for source in ('x = "a{y+1}b"', 'x = f"a{y+1}b"'):
    print(f"  {source}")
    for one in tokens(source):
        print(f"      {token.tok_name[one.type]:16} {one.string!r}")
    print()
""")


lesson.md(f"""
The `y+1` in the middle came out as three tokens: a `NAME`, an `OP` and a `NUMBER`. Not a name inside a string, the actual tokens you would get from writing `y + 1` on a line by itself. Everything the language allows in an expression is allowed in there, and it works because it is not being treated specially at all.

This is what PEP 701 bought when it made {term("f string", "f-strings")} part of the real grammar, and a pile of old restrictions went away with it. You can reuse the outer quote inside the braces. You can put a backslash in there. You can write a comment inside a multi line one. None of those needed a rule to be removed, because there was no longer a separate mini parser holding its own opinions about quotes.

The three token types are `FSTRING_START`, which is the prefix and the opening quote, `FSTRING_MIDDLE`, which is a run of literal text, and `FSTRING_END`, which is the closing quote. They are lines 67 to 69 of `Grammar/Tokens`, right after the ones F01 counted.

## Two lexers in one, and a stack of them

Here is the problem the lexer has. Inside the braces it should behave normally: `{{` opens a set, a `#` starts a comment, whitespace does not matter. Outside the braces but inside the quotes it should behave completely differently: whitespace is content, `#` is just a hash, and the thing it is looking for is a closing quote.

So it has two modes. {cite("Parser/lexer/state.h:36-46@v3.15.0rc1")} names them `TOK_REGULAR_MODE` and `TOK_FSTRING_MODE`, and {cite("Parser/lexer/state.h:48-70@v3.15.0rc1")} is the struct that goes with a mode: the quote character it is looking for, how many braces are open, whether it is in a format spec, and a few more.

One mode is not enough, though, because an f-string can contain an f-string. So it is a stack, at {cite("Parser/lexer/state.h:132-133@v3.15.0rc1")}, and the stack is a fixed array.

{figure("the-mode-stack", "three entries on the tokenizer mode stack, with regular mode at the bottom")}

That array is `MAXFSTRINGLEVEL` long, which {cite("Parser/lexer/state.h:8@v3.15.0rc1")} sets to 150. There is a second, much smaller limit hiding nearby: `MAX_EXPR_NESTING` is 3, and it counts something different. So {lesson.claim("f-strings have two separate nesting limits, one for f-strings inside f-strings and a far smaller one for fields inside a format spec, and you can find both from Python")}.
""")


lesson.code("""
def deepest(build):
    \"\"\"Grow the source until it stops compiling, and return the last size that worked.\"\"\"
    size = 1
    while True:
        try:
            compile(build(size), "<here>", "eval")
        except SyntaxError as unhappy:
            return size - 1, unhappy.msg
        size += 1


def nested_strings(depth):
    return "f'{" * (depth - 1) + "f'1'" + "}'" * (depth - 1)


def nested_specs(depth):
    return "f'{v" + ":{w" * (depth - 1) + "}" * (depth - 1) + "}'"


for label, build in (("f-strings", nested_strings), ("format specs", nested_specs)):
    reached, said = deepest(build)
    print(f"  {label:13} deepest that compiles: {reached:3}")
    print(f"  {'':13} one deeper:            {said}")
""")


lesson.md(f"""
149 rather than 150, because the check at {cite("Parser/lexer/lexer.c:1085-1087@v3.15.0rc1")} is written `tok_mode_stack_index + 1 >= MAXFSTRINGLEVEL` and runs before the push. Index zero is regular mode, so 149 f-string entries fit above it.

{figure("two-ceilings", "the two nesting limits, the constants behind them and the message each one produces")}

The other one reaches 3 exactly, from the check at {cite("Parser/lexer/lexer.c:1413-1416@v3.15.0rc1")}. Three is a strange looking number until you see what it is protecting. Format specs are the one place where the lexer has to decide between two readings of a brace without much context, and every extra level of that makes the decision harder. Rather than get it subtly wrong, CPython puts a low ceiling on it.

Coming back out is one line. {cite("Parser/lexer/lexer.c:1441-1444@v3.15.0rc1")} decrements the stack index and emits `FSTRING_END`, and the mode underneath takes over again.

## The format spec is another f-string

That second limit only makes sense once you know that the part after the colon is itself tokenized as f-string content.

{figure("the-spec-is-a-string", "a format spec broken into two nested fields and the literal text between them")}

{lesson.claim("the text of a format spec comes out as FSTRING_MIDDLE tokens, the same token type as literal text in the body of the f-string")}
""")


lesson.code("""
for one in tokens('f"{v:{w}.{p}f}"'):
    print(f"  {token.tok_name[one.type]:16} {one.string!r}")
""")


lesson.md(f"""
The `.` between the two fields and the `f` at the end are `FSTRING_MIDDLE`. Not a spec token, not a string, the same token type the `a` and the `b` got in the very first cell. A format spec is an f-string body that happens to live after a colon.

That is also why `{{v:{{w}}}}` works at all. There is nothing special about it. The lexer is already in f-string mode, it sees a brace, and it does what it always does with a brace.

## The middle is raw source

Now for the part that catches people out. `FSTRING_MIDDLE` is not the text of your string. It is the characters of your source, untouched.

{lesson.claim("the lexer does no escape decoding inside an f-string, so the token for a backslash n is two characters long and the parser is what turns it into one")}
""")


lesson.code("""
import ast

for source in ('f"a\\\\nb"', 'rf"a\\\\nb"'):
    middle = next(one for one in tokens(source) if one.type == token.FSTRING_MIDDLE)
    built = ast.parse(source, mode="eval").body.values[0].value
    print(f"  {source:12} token holds {middle.string!r:10} the AST holds {built!r}")
""")


lesson.md(f"""
Four characters in the token, three in the tree. And the raw version, `rf`, produces the exact same token and a different tree, which is the clearest possible statement that the lexer is not the one deciding.

{figure("raw-until-the-parser", "the same token becoming a three character string or a four character string depending on the prefix")}

The decoding happens in the parser. The grammar rule at {cite("Grammar/python.gram:968-983@v3.15.0rc1")} builds a plain `Constant` from the token with {cite("Parser/action_helpers.c:1483-1499@v3.15.0rc1#_PyPegen_constant_from_token")}, and then {cite("Parser/action_helpers.c:1399-1411@v3.15.0rc1")} runs `_PyPegen_decode_fstring_part` over it, which is where `\\n` finally becomes a newline.

There is one exception, and it leaves a mark you can see. Doubled braces are handled by the lexer, because it has to know about them anyway to tell `{{{{` from the start of a field. It deals with them by ending the token one character early and starting the next one after the pair, at {cite("Parser/lexer/lexer.c:1546-1570@v3.15.0rc1")}. So {lesson.claim("a doubled brace produces two separate FSTRING_MIDDLE tokens with a one character gap between them, and that gap is the character the lexer threw away")}.
""")


lesson.code("""
SOURCE = 'f"{{literal}}"'

for one in tokens(SOURCE):
    if one.type != token.FSTRING_MIDDLE:
        continue
    where = f"columns {one.start[1]:2} to {one.end[1]:2}"
    print(f"  {where}   token {one.string!r:12}  source {SOURCE[one.start[1] : one.end[1]]!r}")
""")


lesson.md(f"""
Column 3 belongs to no token. That is the second `{{` of the pair, dropped on the floor.

While we are here, a comment in the source is worth quoting because it explains something odd. {cite("Parser/action_helpers.c:1405-1407@v3.15.0rc1")} says the tokenizer emits string parts even when the underlying string might become an empty value, and gives the example of a `FSTRING_MIDDLE` holding a line continuation. End a line inside an f-string with a backslash and you get exactly that: a `FSTRING_MIDDLE` token covering two characters that decodes to nothing, so the parser drops it and the tree has no constant in it at all.

## The lexer keeps a copy of your source

Last piece, and it is the one that surprised me most.

When you write `f"{{x=}}"` Python prints `x=` and then the value. It has to get the text `x` from somewhere, and the obvious guess is that the compiler reconstructs it from the tree. It does not. The lexer keeps the raw characters as it scans them.

{figure("the-text-is-kept", "your source text being copied into last_expr_buffer and carried through to the printed output")}

{cite("Parser/lexer/lexer.c:227@v3.15.0rc1#_PyLexer_update_ftstring_expr")} is the copying, one character at a time into a buffer called `last_expr_buffer` that lives on the mode. {cite("Parser/lexer/lexer.c:113-120@v3.15.0rc1#set_ftstring_expr")} is what happens at the end of the {term("replacement field")}: on a `:`, a `!` or a `}}`, the buffer gets attached to the token as metadata and travels to the parser.

The check in that function is worth reading. It only does the work when `in_debug` is set, which {cite("Parser/lexer/lexer.c:1380-1384@v3.15.0rc1")} turns on the moment it sees an `=` at the top level of a field, or when the string is a {term("t string")}, which always needs the text. Everything else pays nothing.

If the text really is a copy of your source rather than something rebuilt, then {lesson.claim("the spacing you wrote inside an equals field survives exactly, including spaces a reconstruction would have normalised away")}.
""")


lesson.code("""
value = 1

#: Written as text and evaluated, because a code formatter run over this notebook would
#: tidy the spacing away, and the spacing is the whole point of the cell.
SPACED = 'f"{value  +  1  =  }"'
PLAIN = 'f"{ value }"'
TEMPLATE = 't"{value  +  1}"'

print(f"  {SPACED:24} gives {eval(SPACED)!r}")
print(f"  {PLAIN:24} gives {eval(PLAIN)!r}")

kept = [part.expression for part in eval(TEMPLATE) if not isinstance(part, str)]
print(f"  {TEMPLATE:24} kept  {kept}")
""")


lesson.md(f"""
Two spaces either side of the `+`, two around the `=`, and every one of them comes back. Nothing that walked an `ast.BinOp` would produce that. Compare the second line, an ordinary field with a space on each side of the name, where the spacing is gone because nothing was recording it.

The third line is the same buffer doing a different job. A {term("t string")} does not format anything at the point of writing, so it has to hand you the expression text to use later, and `Interpolation.expression` is exactly the string the lexer copied. That is why t-strings always pay the copying cost and f-strings only pay it after an `=`.

## One lexer, two prefixes

t-strings arrived in 3.14 and reused all of this. {cite("Parser/lexer/state.h:41-44@v3.15.0rc1")} is the whole difference: a two value enum on the mode saying whether this is an f-string or a t-string.

{lesson.claim("a t-string produces the same shape of token stream as an f-string with different token names, because the lexer runs the same code and only changes which name it stamps on the result")}
""")


lesson.code("""
for one in tokens('x = t"a{y}b"'):
    print(f"  {token.tok_name[one.type]:16} {one.string!r}")
""")


lesson.md("""
`TSTRING_START`, `TSTRING_MIDDLE`, `TSTRING_END`, in the same places, with the same contents. In the C the emitting is done through a pair of macros that pick the name from the mode, so there is genuinely one implementation. The parser then builds a `TemplateStr` instead of a `JoinedStr`, and that is where the two stories part company.

## Try it yourself

1. Tokenize an f-string that spans several lines and watch what happens to `FSTRING_MIDDLE` at the line breaks. Does one token cross a newline?
2. Put a `#` inside the braces of a single line f-string and read the error. Now do the same inside a triple quoted one. Explain the difference using the two modes.
3. Take the `deepest` helper and point it at brackets inside an f-string field rather than at f-strings. Which limit do you hit, the f-string one or `MAXLEVEL` from F01?
4. `f"{x!r:>10}"` has both a conversion and a format spec. Tokenize it and work out which of the three characters `!`, `r` and `:` are their own tokens.
5. Find a case where `f"{expr=}"` prints something that is not valid Python to paste back. Comments and line continuations are a good place to start.

## What just happened

An f-string is a stretch of source that the lexer walks into and back out of, not a token it hands over whole. The tokens in the braces are ordinary tokens produced by ordinary code.

The walking in and out is a stack of modes on `struct tok_state`, one entry per open f-string, capped at 150 entries so 149 nested f-strings is the most that compiles. A second and much smaller cap of 3 applies to fields nested inside a format spec.

A format spec is f-string content too. The literal parts of it come out as `FSTRING_MIDDLE`, the same as literal parts of the body.

`FSTRING_MIDDLE` holds raw source. No escape decoding happens in the lexer, so the same token can become three characters or four depending on whether there was an `r` in the prefix. Doubled braces are the one thing the lexer does resolve, and it leaves a visible gap in the token positions where the dropped character was.

The lexer keeps a copy of the characters of your expression, and that copy is what makes `f"{x=}"` print your spacing and what fills in `Interpolation.expression` for t-strings.

## What is next

F03 leaves the tokenizer for good and starts on the parser. The token stream stops being the subject and becomes the input, and the thing reading it is generated from a grammar file that is a great deal bigger than `Grammar/Tokens`.

The two rules you saw quoted here, `fstring_middle` and `fstring_replacement_field`, are a small corner of that grammar. F03 is about where the code that runs them comes from.
""")


raise SystemExit(lesson.save())
