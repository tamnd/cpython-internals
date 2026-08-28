"""The token stream, and the one algorithm inside it that is worth writing out by hand.

Most of this module is presentation: `tokenize` already gives you the tokens, and what a
lesson needs is a table you can read and an error you can look at without a traceback
burying it.

`indent_trace` is the exception and it is the reason the module exists. Significant
whitespace is the first thing in Python that looks like magic, and it stops looking like
magic the moment you see that the tokenizer keeps a stack of column numbers and compares
against the top of it. That algorithm is thirty lines of C in
Parser/lexer/lexer.c:500-530@v3.15.0rc1#tok_get_normal_mode, it is transcribed here, and
the test suite runs both against the same sources and requires the same answer. A
reimplementation that is checked against the original is worth reading. One that is not
is a guess with syntax highlighting.
"""

from __future__ import annotations

import io
import token as token_module
import tokenize as tokenize_module
from dataclasses import dataclass

from . import draw

#: The tab stop the tokenizer measures a line against. `Parser/lexer/state.c` sets it once
#: and the comment above it reads "Never change this", which is not a style note: the
#: number is part of the language, because it decides whether two lines are indented the
#: same amount.
TABSIZE = 8

#: The second tab stop, used only to detect that a file would be indented differently
#: under a different tab width. Nothing is measured in these units except the disagreement.
ALTTABSIZE = 1


@dataclass(frozen=True)
class Token:
    """One token, with the two type names kept apart because they answer different questions.

    `kind` is what the tokenizer calls it and is what the grammar matches on. `exact` is
    finer and only differs for operators: every one of them is an OP, and the exact type is
    which operator it was. Confusing the two is how people conclude the tokenizer knows
    more than it does.
    """

    kind: str
    exact: str
    text: str
    start: tuple[int, int]
    end: tuple[int, int]

    @property
    def synthesized(self) -> bool:
        """Is this token invented by the tokenizer rather than read out of the file?

        INDENT is a run of real characters given a name, but DEDENT, NEWLINE at end of
        input, ENCODING and ENDMARKER are all zero width or otherwise not in the text, and
        a reader who does not know which is which will try to find them in the source.
        """
        return self.start == self.end or self.kind in {"ENCODING", "INDENT", "DEDENT"}

    def __str__(self) -> str:
        where = f"{self.start[0]}:{self.start[1]}"
        name = self.kind if self.exact == self.kind else f"{self.kind}/{self.exact}"
        return f"{where:>7}  {name:<22} {self.text!r}"


def stream(source: str) -> list[Token]:
    """Every token in this source, including the ones the parser never sees.

    The extras are COMMENT and NL, and they exist because the `tokenize` module asks for
    them. The tokenizer has a flag for it, and when it is off a comment and a newline
    inside brackets are thrown away rather than returned. So this list is a superset of
    what the compiler works from, which is the opposite of what most people assume.
    """
    reader = io.BytesIO(source.encode("utf-8")).readline
    rows = []
    for item in tokenize_module.tokenize(reader):
        rows.append(
            Token(
                kind=token_module.tok_name[item.type],
                exact=token_module.tok_name[item.exact_type],
                text=item.string,
                start=item.start,
                end=item.end,
            )
        )
    return rows


def table(source: str) -> str:
    """The token stream as a table, one token per line, positions included."""
    return "\n".join(str(item) for item in stream(source))


def kinds(source: str) -> list[str]:
    """Just the token names, which is what most comparisons actually want."""
    return [item.kind for item in stream(source)]


@dataclass(frozen=True)
class Failure:
    """A tokenizer error, as data rather than as a traceback.

    A lesson that shows a failure wants the reader looking at the message and the position,
    not at eight frames of `tokenize` internals above it.
    """

    error: str
    message: str
    line: int | None
    column: int | None

    def __str__(self) -> str:
        where = "" if self.line is None else f" at line {self.line}"
        if self.line is not None and self.column is not None:
            where = f" at line {self.line}, column {self.column}"
        return f"{self.error}{where}: {self.message}"


def failure(source: str) -> Failure | None:
    """Tokenize this source and report the error, or None if there was not one.

    Both exceptions that come out of here are worth telling apart. SyntaxError and its
    subclasses, which is what a bad indent raises, carry a position. TokenError, which is
    what an unclosed bracket raises, carries a position in its arguments instead, because
    it predates the rest and nobody has unified them.
    """
    try:
        stream(source)
    except tokenize_module.TokenError as error:
        message = str(error.args[0]) if error.args else str(error)
        position = error.args[1] if len(error.args) > 1 else None
        line, column = position if isinstance(position, tuple) else (None, None)
        return Failure("TokenError", message, line, column)
    except SyntaxError as error:
        return Failure(type(error).__name__, error.msg or "", error.lineno, error.offset)
    return None


def measure(text: str, *, tabsize: int = TABSIZE) -> tuple[int, int]:
    """The two column counts for the leading whitespace of one physical line.

    This is the loop at Parser/lexer/lexer.c:520-530@v3.15.0rc1#ALTTABSIZE, and the only
    thing worth staring at is that a tab is not worth a fixed number of columns. It
    advances to the next multiple of the tab size, so how much a tab is worth depends on
    what came before it.

    The second count does the same arithmetic with a tab size of one. Nothing is ever
    indented in those units. It exists so that the tokenizer can notice that two lines
    which agree under a tab width of eight would disagree under any other, which is the
    only definition of "mixed tabs and spaces" that can actually be checked.
    """
    col = altcol = 0
    for character in text:
        if character == " ":
            col += 1
            altcol += 1
        elif character == "\t":
            col = (col // tabsize + 1) * tabsize
            altcol = (altcol // ALTTABSIZE + 1) * ALTTABSIZE
        elif character == "\014":
            col = altcol = 0
        else:
            break
    return col, altcol


@dataclass(frozen=True)
class IndentStep:
    """What the tokenizer decided about one physical line, and what it did about it."""

    line: int
    text: str
    col: int
    altcol: int
    emitted: tuple[str, ...]
    stack: tuple[int, ...]

    def __str__(self) -> str:
        emitted = " ".join(self.emitted) if self.emitted else "."
        stack = " ".join(str(number) for number in self.stack)
        return f"{self.line:>3}  col {self.col:>3}  alt {self.altcol:>3}  {emitted:<16} [{stack}]"


class OutOfScope(ValueError):
    """Raised for source this transcription deliberately does not handle.

    Saying so is better than getting it quietly wrong. The C tokenizer skips the
    indentation code entirely while a bracket is open, at
    Parser/lexer/lexer.c:586-608@v3.15.0rc1#pendin, and it also lets a backslash join two
    physical lines before the indentation is measured. Both are real and neither is what
    this function is for, so it refuses rather than pretending.
    """


def _spans_lines(source: str) -> bool:
    """Does any logical line in this source occupy more than one physical line?

    Asked by running the real tokenizer, which is the point: the algorithm below is a
    transcription and has to stand on its own, but deciding whether an input is in scope
    is not part of the algorithm, so there is no reason to reimplement it badly.
    """
    first: int | None = None
    for item in stream(source):
        if item.kind in {"ENCODING", "NL", "COMMENT", "INDENT", "DEDENT", "ENDMARKER"}:
            continue
        if item.kind == "NEWLINE":
            if first is not None and item.start[0] != first:
                return True
            first = None
        elif first is None:
            first = item.start[0]
    return False


def indent_trace(source: str, *, tabsize: int = TABSIZE) -> list[IndentStep]:
    """Run the tokenizer's indentation algorithm by hand and show the stack after each line.

    The whole of significant whitespace is here. There is a stack of column numbers whose
    bottom entry is zero. A line whose column matches the top of the stack changes nothing.
    A line further right pushes and produces one INDENT, always exactly one no matter how
    far right it went. A line further left pops until the top matches and produces one
    DEDENT per pop, which is why a single line can produce three of them, and if nothing on
    the stack matches then that is the error about not matching any outer indentation level.

    Blank lines and comment only lines are skipped before any of this, so indenting a
    comment cannot break a block. The C does that at
    Parser/lexer/lexer.c:500-530@v3.15.0rc1#tok_get_normal_mode by setting `blankline` and
    jumping over the whole comparison.
    """
    if _spans_lines(source):
        raise OutOfScope(
            "this source has a logical line spanning several physical lines, using "
            "brackets or a backslash. The tokenizer does not measure indentation at all "
            "while one of those is open, and this transcription does not model it."
        )

    steps: list[IndentStep] = []
    stack = [0]
    altstack = [0]
    for number, text in enumerate(source.splitlines(), start=1):
        stripped = text.lstrip(" \t\014")
        if not stripped or stripped.startswith("#"):
            continue
        col, altcol = measure(text, tabsize=tabsize)
        emitted: list[str] = []
        if col == stack[-1]:
            if altcol != altstack[-1]:
                raise TabError("inconsistent use of tabs and spaces in indentation")
        elif col > stack[-1]:
            if altcol <= altstack[-1]:
                raise TabError("inconsistent use of tabs and spaces in indentation")
            stack.append(col)
            altstack.append(altcol)
            emitted.append("INDENT")
        else:
            while len(stack) > 1 and col < stack[-1]:
                stack.pop()
                altstack.pop()
                emitted.append("DEDENT")
            if col != stack[-1]:
                raise IndentationError("unindent does not match any outer indentation level")
            if altcol != altstack[-1]:
                raise TabError("inconsistent use of tabs and spaces in indentation")
        steps.append(
            IndentStep(
                line=number,
                text=text,
                col=col,
                altcol=altcol,
                emitted=tuple(emitted),
                stack=tuple(stack),
            )
        )

    # End of input closes whatever is still open. It is easy to forget that this happens,
    # because there is no line to attribute it to, and forgetting it is why a hand written
    # tokenizer produces a stream the parser rejects at the very last token.
    if len(stack) > 1:
        steps.append(
            IndentStep(
                line=len(source.splitlines()) + 1,
                text="",
                col=0,
                altcol=0,
                emitted=("DEDENT",) * (len(stack) - 1),
                stack=(0,),
            )
        )
    return steps


def indent_report(source: str, *, tabsize: int = TABSIZE) -> str:
    """`indent_trace` as a table, with a header saying what the columns are."""
    header = f"{'ln':>3}  {'col':>7}  {'alt':>7}  {'emitted':<16} [stack]"
    rows = [str(step) for step in indent_trace(source, tabsize=tabsize)]
    return "\n".join([header, "-" * len(header), *rows])


def ribbon(source: str) -> str:
    """One line of source with every token marked underneath it.

    This is the picture that makes the word "token" concrete. Until you have seen which
    characters became which token, and that some tokens are no characters at all, the word
    is just a word.
    """
    line = source.splitlines()[0] if source.splitlines() else ""
    spans = [
        (item.start[1], item.end[1], item.kind, item.text)
        for item in stream(source)
        if item.start[0] == 1 and item.end[0] == 1 and item.end[1] > item.start[1]
    ]
    return draw.ribbon(line, spans)


def staircase(source: str, *, tabsize: int = TABSIZE) -> str:
    """The indentation of a file drawn as a bar chart, one bar per line of code.

    The shape of the bars is the shape of the blocks. Every step to the right is one
    INDENT, and every step back to the left is one DEDENT for each level it passed.
    """
    steps = indent_trace(source, tabsize=tabsize)
    rows = [(f"line {step.line}" if step.text else "end", step.col) for step in steps]
    notes = [" ".join(step.emitted) for step in steps]
    return draw.bars(rows, note=notes)
