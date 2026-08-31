"""The glossary, as data, so that one definition serves every lesson.

A course this long has two ways to go wrong with vocabulary. It can define a word once, in
the lesson where it first came up, and then assume it forty lessons later when the reader
has forgotten. Or it can redefine it every time, which trains the reader to skip the first
paragraph of everything. This module is the third option: there is one definition, it lives
here, and lessons link into it.

Everything here is content rather than machinery, which is why it sits in `pyxray` next to
the instrumentation instead of in the build tools. A lesson can import it and print a
definition in a cell, and `GLOSSARY.md` at the root of the repository is generated from it
so that a reader can also just read the thing.

Two rules keep it honest. A term is only in here if a lesson has actually earned it, so
there are no entries for parts that have not been written. And where a definition rests on
something in CPython rather than on the language reference, it carries the citation, which
means `refcheck` resolves it against the pinned tree on every change like every other claim
in the project.
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass, field

from .cite import url

__all__ = ["GROUPS", "TERMS", "Group", "Term", "anchor", "get", "link", "markdown", "names"]

#: Where the generated file lives, relative to the root of the repository. Lessons link to
#: the version on GitHub rather than this path, because a notebook opened in Colab has no
#: idea which repository it came from and a relative link would be broken for every reader
#: who arrived through the badge.
PATH = "GLOSSARY.md"

REPOSITORY = "https://github.com/tamnd/cpython-internals"


@dataclass(frozen=True)
class Term:
    """One entry. The short line is what a lesson quotes, the long one is why it matters."""

    #: Letters, digits, spaces and underscores, which is the subset of characters where
    #: the anchor GitHub makes from a heading is predictable. Backticks and punctuation go
    #: in `also` instead, where they cannot end up in a URL.
    name: str

    #: One sentence, the definition you would give somebody in passing.
    short: str

    #: A paragraph. Where there is a thing people reliably get wrong about the term, this
    #: is where it goes, because a glossary that only says what a word means is a
    #: dictionary and the reader already has one of those.
    long: str

    #: Other names for the same thing, including how it is spelled in the source.
    also: tuple[str, ...] = ()

    #: Where in CPython the definition comes from, when it comes from CPython at all.
    cite: str = ""

    #: Related terms, by name. Checked, so a rename cannot leave a dead link behind.
    see: tuple[str, ...] = ()

    #: The lesson where a reader first meets it.
    met: str = ""

    @property
    def anchor(self) -> str:
        """The fragment GitHub will generate for this term's heading."""
        return anchor(self.name)


@dataclass(frozen=True)
class Group:
    """A run of terms under one heading, in the order a reader meets them."""

    title: str
    blurb: str
    terms: tuple[Term, ...] = field(default_factory=tuple)


def anchor(name: str) -> str:
    """GitHub's heading slug, for the small subset of headings this file produces.

    GitHub lowercases the heading, drops punctuation and turns spaces into hyphens, but it
    keeps underscores, so `EXTENDED_ARG` becomes `extended_arg` and not `extended-arg`.
    Getting that one wrong gives you links that look right and go nowhere.
    """
    return re.sub(r"[^a-z0-9_]+", "-", name.lower()).strip("-")


READING = Group(
    "Reading the source",
    "The words you need before the C stops looking like a foreign language. Z01 and Z02 are the two lessons that cover this ground.",
    (
        Term(
            name="pointer",
            short="A value holding the address of something rather than the something itself.",
            long="Almost every value in CPython's C is a `PyObject *`, which is the address of an object. The `*` in a declaration means address of one of these, and the `->` means follow the address and take that field. A pointer that is `NULL` is how a C function reports that something went wrong, which is why so much of this code is a call followed immediately by a check for `NULL`.",
            also=("`PyObject *`",),
            see=("struct", "object"),
            met="Z01",
        ),
        Term(
            name="struct",
            short="A named group of fields laid out one after another in memory.",
            long="Reading CPython is mostly a matter of finding the struct behind a type and seeing what fields it has. The order matters more than it looks: every object starts with the same header fields, and that is exactly what lets a function accept any object at all and still be able to ask what type it is.",
            cite="Include/cpython/listobject.h:5-22@v3.15.0rc1#PyListObject",
            see=("object header", "pointer"),
            met="Z01",
        ),
        Term(
            name="header file",
            short="A `.h` file holding the declarations that other files include.",
            long="The split is worth remembering because it saves a lot of searching. If you want to know what a thing is made of, look in `Include/`. If you want to know what happens to it, look in `Objects/` or `Python/`. `Include/internal/` is the half that is not part of the public API, and it is where most of the shapes worth reading actually live.",
            see=("struct",),
            met="Z01",
        ),
        Term(
            name="generated file",
            short="A source file a script writes at build time rather than a person typing it.",
            long="About a third of the C in CPython is generated, and every one of those files announces itself in its first three lines. Reading one means reading the output of a program instead of the program, which is why it never quite makes sense. The fix is to find the input: `Python/bytecodes.c` for the interpreter, `Grammar/python.gram` for the parser, `Parser/Python.asdl` for the tree.",
            cite="Python/generated_cases.c.h:1-4@v3.15.0rc1#tier1_generator",
            see=("grammar", "ASDL", "bytecode"),
            met="Z02",
        ),
        Term(
            name="Argument Clinic",
            short="The tool that writes a C function's argument parsing from a comment above it.",
            long="A block beginning `/*[clinic input]` above a C function declares that function's Python signature, and the parsing code generated from it lands in a `clinic/` directory next to the file. This is why the function you find in `Objects/listobject.c` is called `list_append_impl` rather than `list_append`, and why the part that turned Python arguments into C ones is nowhere near it.",
            cite="Objects/listobject.c:1221-1233@v3.15.0rc1#list_append_impl",
            see=("generated file",),
            met="Z02",
        ),
        Term(
            name="new reference",
            short="A reference the caller now owns and is responsible for releasing.",
            long="Functions whose names contain `New` return one, and so does almost anything that builds an object. If you take a new reference and forget to release it the object never dies, which is a leak, and nothing will tell you. The three kinds of reference are the single most important thing to keep straight while reading this code, because the C does not say which kind it is handing you and the docstring often does not either.",
            cite="Include/refcount.h:527-538@v3.15.0rc1#Py_NewRef",
            also=("owned reference",),
            see=("borrowed reference", "stolen reference", "reference count"),
            met="Z01",
        ),
        Term(
            name="borrowed reference",
            short="A reference you may use but do not own, so you must not release it.",
            long="Reading a field out of a struct usually gives you one of these. It is only valid for as long as whatever you borrowed it from stays alive, so borrowing from a list and then modifying the list is the classic way to end up holding an address that no longer means anything.",
            see=("new reference", "stolen reference"),
            met="Z01",
        ),
        Term(
            name="stolen reference",
            short="A reference you hand to a function which then owns it instead of you.",
            long="After the call you must not release it and you should not use it either. There are not many of these and they are all documented, but they are the reason you sometimes see `Py_NewRef` wrapped around an argument at a call site: the caller is manufacturing a reference specifically so the callee can take it away.",
            cite="Include/internal/pycore_list.h:36-54@v3.15.0rc1#_PyList_AppendTakeRef",
            see=("new reference", "borrowed reference"),
            met="Z01",
        ),
    ),
)


FRONT_END = Group(
    "From text to a tree",
    "The first two stages, which between them turn a file into a shape the rest of the compiler can walk. T02 and T03 are the lessons.",
    (
        Term(
            name="token",
            short="One piece of the source text with a name attached to it.",
            long="A token is a span of characters and a label, and that is all. The tokenizer does not know what any of it means, so the word `if` comes out as a NAME just like `answer` does, and the thing that decides `if` is a keyword happens later. Some tokens do not exist in the file at all, which is the next entry.",
            cite="Parser/lexer/lexer.c:1626-1635@v3.15.0rc1#_PyTokenizer_Get",
            see=("tokenizer", "indent and dedent"),
            met="T02",
        ),
        Term(
            name="tokenizer",
            short="The part that turns a stream of characters into a stream of tokens.",
            long="It works one character at a time and keeps very little state, which is why it can tell you about an unterminated string but has never heard of a function definition. The one genuinely clever thing in it is the indentation stack, and it is worth reading for that alone.",
            also=("lexer",),
            cite="Parser/lexer/lexer.c:500-530@v3.15.0rc1#tok_get_normal_mode",
            see=("token", "indent and dedent"),
            met="T02",
        ),
        Term(
            name="indent and dedent",
            short="Two tokens the tokenizer invents to mark a change in indentation.",
            long="The tokenizer keeps a stack of column numbers. A line indented further than the top of the stack pushes a new number and emits an INDENT. A line indented less pops until it matches and emits one DEDENT per pop, which is why a single line can produce three of them. Neither token is anything you can point at in the file, which makes indentation errors much easier to understand once you have seen it.",
            cite="Parser/lexer/lexer.c:520-530@v3.15.0rc1#ALTTABSIZE",
            see=("token", "tokenizer"),
            met="T02",
        ),
        Term(
            name="grammar",
            short="The file describing which arrangements of tokens are legal Python.",
            long="`Grammar/python.gram` is 1,645 lines and it is the actual definition of the language, not a description of it: the parser is generated from this file, so if the two ever disagreed the grammar would win by construction. It is readable, and looking up the rule for the thing you are confused about is often faster than reading anything else.",
            cite="Grammar/python.gram:846-852@v3.15.0rc1#term",
            see=("PEG parser", "generated file"),
            met="T03",
        ),
        Term(
            name="PEG parser",
            short="The parser CPython generates from the grammar file.",
            long="It reads the tokens left to right and tries the alternatives of a rule in the order they are written, taking the first that fits, which is the part that differs from the older parser and the reason rule order in the grammar is meaningful. It remembers what it has already tried at each position so that backtracking does not become expensive.",
            cite="Parser/pegen.c:938-941@v3.15.0rc1#_PyPegen_run_parser",
            see=("grammar", "abstract syntax tree"),
            met="T03",
        ),
        Term(
            name="abstract syntax tree",
            short="The program as nested nodes, with everything that does not affect meaning dropped.",
            long="The tree keeps the structure and the source positions and throws away the whitespace, the comments, the brackets you wrote for readability, and the difference between one way of spelling something and another. That is what abstract means here. It is the last stage where the program still looks like the program, and everything after it looks like a machine.",
            also=("AST",),
            cite="Lib/ast.py:26-30@v3.15.0rc1#parse",
            see=("ASDL", "PEG parser", "code generation"),
            met="T03",
        ),
        Term(
            name="ASDL",
            short="The small language declaring which node types the tree can contain.",
            long="`Parser/Python.asdl` is 154 lines and every node class in both the C and the Python side is generated from it. This is why `ast.BinOp` knows its own field names and why they are the same in both languages: nobody typed them twice.",
            cite="Parser/Python.asdl:104-105@v3.15.0rc1#operator",
            see=("abstract syntax tree", "generated file"),
            met="T03",
        ),
        Term(
            name="coding cookie",
            short="A comment in the first two lines that says what encoding the file is in.",
            long="PEP 263 gave source files a way to declare their own encoding, and the tokenizer looks for it before it looks for anything else. It only means anything when the tokenizer was handed bytes. Hand it a `str` and the encoding question is already settled, so the line is treated as an ordinary comment.",
            also=("encoding declaration",),
            see=("tokenizer",),
            met="F01",
        ),
        Term(
            name="underflow",
            short="The function the tokenizer calls when it has run out of input and wants another line.",
            long="It is a field on `struct tok_state` rather than a fixed call, which is how one lexer reads from a file, a string, a bytes object or a Python callable without knowing which it got. Each of the four constructors sets it to its own version and then never comes up again.",
            cite="Parser/lexer/lexer.c:74-82@v3.15.0rc1",
            see=("tokenizer",),
            met="F01",
        ),
        Term(
            name="f string",
            short="A string literal with a prefix of f, whose braces hold real expressions.",
            long="Since PEP 701 landed in 3.12 the tokenizer reads one directly rather than grabbing it whole and handing it to a separate parser. That is the reason the old restrictions on quotes, backslashes and comments inside the braces all went away at once: there is no longer a second parser to disagree with the first one.",
            also=("formatted string literal",),
            see=("replacement field", "t string", "tokenizer"),
            met="F02",
        ),
        Term(
            name="replacement field",
            short="The part of an f-string between a pair of braces, made of an expression and up to three optional pieces.",
            long="After the expression comes an optional equals sign for debugging, an optional conversion after a bang, and an optional format spec after a colon. The lexer has to recognise all four boundaries while it is still scanning characters, which is most of what makes f-string lexing harder than it looks.",
            cite="Grammar/python.gram:971-973@v3.15.0rc1",
            see=("f string", "t string"),
            met="F02",
        ),
        Term(
            name="t string",
            short="A template string, written with a t prefix, which hands you its pieces instead of formatting them.",
            long="PEP 750 added these in 3.14 and they reuse the f-string lexer completely. The one difference in the tokenizer is a two value enum saying which kind it is. Because a t-string is meant to be inspected rather than printed, it always keeps the source text of each expression, where an f-string only keeps it after an equals sign.",
            also=("template string",),
            see=("f string", "replacement field"),
            met="F02",
        ),
        Term(
            name="parser generator",
            short="The program that reads the grammar file and writes the parser.",
            long="It lives in `Tools/peg_generator` and is a normal Python package, so it is not part of any installed Python and you cannot import it without a source checkout. It has two back ends. The C one writes `Parser/parser.c` and is what a CPython build runs. The Python one writes a parser you can import, which is what the test suite and anyone experimenting with the grammar uses.",
            cite="Makefile.pre.in:2046-2054@v3.15.0rc1",
            also=("pegen",),
            see=("grammar", "PEG parser", "generated file"),
            met="F03",
        ),
        Term(
            name="soft keyword",
            short="A word that counts as a keyword only in the one place the grammar looks for it.",
            long="The grammar marks these with double quotes rather than single ones, and there are five of them: `_`, `case`, `lazy`, `match` and `type`. The tokenizer knows nothing about any of them, which is why you can still have a variable called `match`. Only a parser willing to try an alternative and back out of it can work this way.",
            cite="Grammar/python.gram:32-34@v3.15.0rc1",
            see=("PEG parser", "grammar", "token"),
            met="F03",
        ),
        Term(
            name="left recursion",
            short="A rule that names itself as the first thing it matches.",
            long="Read literally this never terminates, so most parser generators refuse it and ask you to rewrite the rule. Pegen accepts it and generates a loop instead: parse the rule without the recursion, then feed the result back in and try again, keeping the longest parse that got longer. That is why `1 - 2 - 3` groups to the left without anybody writing down a precedence table.",
            cite="Parser/parser.c:14045-14079@v3.15.0rc1#sum_rule",
            see=("grammar", "PEG parser", "parser generator"),
            met="F03",
        ),
        Term(
            name="sum type",
            short="A schema type written as a list of alternatives separated by bars.",
            long="Every one of these becomes an abstract base class plus one concrete class per alternative, which is why `isinstance(node, ast.expr)` is a sensible thing to write. Python's whole syntax is two large sums, 29 kinds of expression and 28 kinds of statement, and a handful of small ones for the operators.",
            cite="Parser/Python.asdl:104-105@v3.15.0rc1",
            see=("ASDL", "product type", "abstract syntax tree"),
            met="F04",
        ),
        Term(
            name="product type",
            short="A schema type written as one bracketed list of fields, with no alternatives.",
            long="There is only ever one shape, so it becomes a single class with no base class of its own. Seven of them exist: `arguments`, `arg`, `keyword`, `alias`, `withitem`, `comprehension` and `match_case`. Telling them apart from the sums in Python is a matter of asking which classes have no subclasses.",
            cite="Parser/Python.asdl:116-117@v3.15.0rc1",
            see=("ASDL", "sum type"),
            met="F04",
        ),
    ),
)


NAMES = Group(
    "Names and where they live",
    "The stage between the tree and the bytecode, which decides what every name in the program is before a single instruction is emitted. T04 is the lesson.",
    (
        Term(
            name="symbol table",
            short="The table saying what every name in a block is, built before any code is generated.",
            long="This is the answer to the question people usually phrase as when does Python decide. It decides here, at compile time, for the whole block at once, by looking at every binding in it. That is why assigning to a name at the bottom of a function changes how a read of it at the top compiles.",
            cite="Python/symtable.c:415-418@v3.15.0rc1#_PySymtable_Build",
            see=("scope", "binding", "cell"),
            met="T04",
        ),
        Term(
            name="scope",
            short="One block with its own set of names: a module, a function, a class body or a lambda.",
            long="Scopes nest, and a name is resolved by looking outward through the enclosing function scopes. Class bodies are the odd one out and do not participate in that outward walk, which is why a method cannot see a class attribute by bare name. Comprehensions used to be scopes of their own and stopped being so in 3.12.",
            cite="Include/internal/pycore_symtable.h:187-192@v3.15.0rc1#GLOBAL_EXPLICIT",
            see=("symbol table", "closure"),
            met="T04",
        ),
        Term(
            name="binding",
            short="Anything in a block that makes a name refer to something.",
            long="An assignment is the obvious one, but so are `def`, `class`, `import`, a `for` target, an `except ... as` name, a `with ... as` name and a function parameter. A name bound anywhere in a function is local to that function everywhere in it, including on the lines above the binding, and that rule alone explains most of the surprising `UnboundLocalError` reports people file.",
            cite="Include/internal/pycore_symtable.h:165-177@v3.15.0rc1#DEF_BOUND",
            see=("symbol table", "scope"),
            met="T04",
        ),
        Term(
            name="cell",
            short="A small box holding a variable that an inner function shares with an outer one.",
            long="When a nested function reads a name from the function around it, the value cannot just live in the outer frame, because the outer call may have finished. So the compiler puts it in a cell, the outer function holds the cell rather than the value, and the inner one holds the same cell. Two functions sharing a variable are sharing one of these, which is why `nonlocal` works at all.",
            see=("closure", "free variable"),
            met="T04",
        ),
        Term(
            name="free variable",
            short="A name a function uses that belongs to a function around it.",
            long="Free here means free of this scope, not free of charge. The compiler lists them in `co_freevars`, and each one is a cell the function was handed when it was created rather than a local it makes for itself.",
            see=("cell", "closure"),
            met="T04",
        ),
        Term(
            name="closure",
            short="A function together with the cells it captured from around it.",
            long="The word gets used for the function, for the cells, and for the general idea, and it is usually clear enough from context. The concrete version is `function.__closure__`, which is a tuple of cells, one per name in `co_freevars`, and you can look inside them from Python.",
            see=("cell", "free variable", "scope"),
            met="T04",
        ),
        Term(
            name="symbol table pass",
            short="The walk over the tree that decides what every name means, before any code is emitted.",
            long="It runs twice over each block. The first walk only collects what was written down, an assignment here, a parameter there, a `global` statement over there. The second walk turns that into one of five scopes per name. The compiler starts it on its first line and never reasons about scope again afterwards, it just reads the answers.",
            cite="Python/symtable.c:415-416@v3.15.0rc1#_PySymtable_Build",
            also=("symtable",),
            see=("symbol table", "scope", "code generation"),
            met="F05",
        ),
        Term(
            name="class cell",
            short="The `__class__` cell a method gets so that a bare `super()` can find its class.",
            long="A method is an ordinary function and has no idea which class it was written in, so the symbol table adds the name for you. Reading the name `super` anywhere in a method body is the whole trigger, which is why a method that reaches the same builtin through the `builtins` module gets no cell and fails at run time.",
            cite="Python/symtable.c:2651-2657@v3.15.0rc1",
            also=("__classcell__",),
            see=("cell", "free variable", "symbol table pass"),
            met="F05",
        ),
    ),
)


COMPILING = Group(
    "Turning a tree into instructions",
    "What the compiler does after it knows what the names are, and the shape of the thing it produces. T05 and T06 are the lessons.",
    (
        Term(
            name="code generation",
            short="Walking the tree and emitting instructions for each node.",
            long="This stage is mechanical on purpose. It does not try to be clever, it emits a straightforward sequence including jumps to labels, and everything that makes the result smaller or faster happens afterwards on the graph. Separating the two is what keeps `Python/codegen.c` readable.",
            cite="Python/codegen.c:894-897@v3.15.0rc1#_PyCodegen_Expression",
            see=("control flow graph", "abstract syntax tree"),
            met="T05",
        ),
        Term(
            name="short circuiting",
            short="Stopping an `and` or an `or` as soon as the answer is known.",
            long="There is no instruction for either operator. The code generator emits a copy of the left hand value, a test, and a jump past everything after it, so the behaviour is decided at compile time and the interpreter never sees a boolean operator at all. The value you get back is one of the operands rather than True or False, which falls out of the same shape.",
            cite="Python/codegen.c:3387-3413@v3.15.0rc1#codegen_boolop",
            see=("code generation", "instruction", "dispatch"),
            met="F06",
        ),
        Term(
            name="evaluation order",
            short="Which part of an expression or statement runs first.",
            long="Not a rule written down anywhere separately. It is whatever order the code generator visits a node's children in, so it is readable off a few lines of C. Left before right for an operator, and for an assignment the value before the target, which is why `box[key] = value` runs the value first.",
            cite="Python/codegen.c:3101-3113@v3.15.0rc1",
            see=("code generation", "abstract syntax tree"),
            met="F06",
        ),
        Term(
            name="control flow graph",
            short="The emitted instructions as blocks, with the jumps between them as edges.",
            long="This is the form the optimizer works on, because questions like is this code reachable and how deep does the stack get are questions about a graph and are awkward to ask about a flat list. It is turned back into a flat list at the end by the assembler.",
            also=("CFG",),
            cite="Python/flowgraph.c:3753-3757@v3.15.0rc1#_PyCfg_OptimizeCodeUnit",
            see=("basic block", "assembler", "constant folding"),
            met="T05",
        ),
        Term(
            name="basic block",
            short="A run of instructions with one way in at the top and one way out at the bottom.",
            long="Nothing jumps into the middle of one and nothing branches out of the middle, which is what makes them useful: anything true at the top of a block stays true all the way down it. A jump target always starts a new block.",
            cite="Python/flowgraph.c:1008-1044@v3.15.0rc1#remove_unreachable",
            see=("control flow graph",),
            met="T05",
        ),
        Term(
            name="cold block",
            short="A block the compiler expects almost never to run, such as an exception handler.",
            long="Marking one costs nothing and buys a tidier layout: every cold block is moved past the end of the function so the code that does run stays packed together, which is why the handler for line 6 turns up after the return on line 8. Where a cold block used to fall off its bottom into a warm one, the pass writes an explicit jump in place of the fallthrough.",
            cite="Python/flowgraph.c:3492-3506@v3.15.0rc1#push_cold_blocks_to_end",
            see=("basic block", "exception table"),
            met="F07",
        ),
        Term(
            name="stack depth",
            short="How many slots a frame has to reserve for the value stack, worked out at compile time.",
            long="It is the deepest path through the graph rather than the running total down the list, and the difference shows up as soon as there is an exception handler, because a handler starts one deeper than empty. The answer ends up in the code object as `co_stacksize` and the interpreter trusts it completely, so being wrong here is a crash rather than a slowdown.",
            cite="Python/flowgraph.c:815-824@v3.15.0rc1#calculate_stackdepth",
            also=("`co_stacksize`",),
            see=("stack effect", "control flow graph", "value stack"),
            met="F07",
        ),
        Term(
            name="constant folding",
            short="Working an expression out while compiling, so it does not have to be worked out later.",
            long="`6 * 7` becomes 42 in the compiled file and the multiply never reaches the interpreter. CPython does this twice, once on the tree and once on the graph, and it stops when the answer would be unreasonably large, so folding a giant power does not make an import take a second and a megabyte. The old operand often stays behind in the constants with nothing loading it, which is a good thing to notice.",
            cite="Python/flowgraph.c:1916-1948@v3.15.0rc1#fold_const_binop",
            see=("control flow graph", "code object"),
            met="T05",
        ),
        Term(
            name="pseudo instruction",
            short="An instruction that exists inside the compiler and never reaches a code object.",
            long="Things like `JUMP` without a resolved target, or the markers used to build the exception table. They are real entries in the opcode table with numbers above the real instructions, and they are all gone by the time the assembler is finished, so seeing one in a disassembly would mean something had gone badly wrong.",
            cite="Include/opcode_ids.h:247-257@v3.15.0rc1#ANNOTATIONS_PLACEHOLDER",
            see=("assembler", "opcode"),
            met="T05",
        ),
        Term(
            name="assembler",
            short="The stage that flattens the finished graph into the bytes of a code object.",
            long="It lays the blocks out in order, turns label references into offsets, works out how deep the value stack gets, builds the line table and the exception table, and hands back the finished object. By the time it runs every decision has been made, so it is the least interesting stage and the one you are most grateful for when reading a disassembly.",
            cite="Python/assemble.c:779-802@v3.15.0rc1#_PyAssemble_MakeCodeObject",
            see=("code object", "control flow graph", "exception table"),
            met="T05",
        ),
        Term(
            name="code object",
            short="The compiled form of one module, function, class body or comprehension.",
            long="It holds the bytecode, the constants, the names, the local variable names, the line table, the exception table and the stack size, and it holds no values: a code object for a function is the same whether the function has been called once or a million times. Nested definitions produce their own code objects which sit in the outer one's constants, so a module's code object contains its functions the way a box contains boxes.",
            cite="Objects/codeobject.c:715-718@v3.15.0rc1#_PyCode_New",
            also=("`co_*`",),
            see=("bytecode", "frame", "assembler"),
            met="T05",
        ),
        Term(
            name="bytecode",
            short="The instruction stream inside a code object.",
            long="It is a sequence of two byte units, one opcode and one argument each, plus the cache slots belonging to the instruction before. It is an implementation detail with no compatibility promise and it changes every release, which is exactly why reading it teaches you about this interpreter rather than about Python.",
            cite="Include/internal/pycore_structs.h:17-32@v3.15.0rc1#_Py_CODEUNIT",
            see=("instruction", "code object", "inline cache"),
            met="T05",
        ),
        Term(
            name="instruction",
            short="One opcode and one argument byte, two bytes together.",
            long="Everything is exactly two bytes, which is why an instruction that needs a bigger argument has to be preceded by extra instructions rather than growing. Any cache slots belonging to an instruction follow it and are skipped over rather than executed.",
            also=("code unit",),
            see=("opcode", "oparg", "inline cache"),
            met="T06",
        ),
        Term(
            name="opcode",
            short="The number in the first byte, saying which instruction this is.",
            long="`dis` prints the name, and the names and numbers both come out of a table generated from `Python/bytecodes.c`, so asking Python for them is asking the same file the interpreter was compiled from. Numbers move between releases and are not worth memorising.",
            see=("instruction", "oparg", "generated file"),
            met="T06",
        ),
        Term(
            name="oparg",
            short="The second byte, whose meaning is different for every instruction.",
            long="This is the single biggest source of confusion when reading a disassembly. In `LOAD_CONST 1` it indexes the constants, in `LOAD_FAST 1` it indexes the locals, in `CALL 1` it counts arguments and in a jump it counts instructions. The number 1 in those four lines has nothing in common beyond being the number 1.",
            also=("argument",),
            see=("instruction", "opcode", "EXTENDED_ARG"),
            met="T06",
        ),
        Term(
            name="EXTENDED_ARG",
            short="An instruction that supplies the high bits of the argument of the next one.",
            long="One byte only reaches 255, so a function with more than 256 constants needs a way to say so. Up to three of these can stack up in front of an instruction, each shifting what came before left by eight. `dis` folds them into the number it prints, so you see the real argument and have to remember that the offsets moved.",
            cite="Python/bytecodes.c:6092-6098@v3.15.0rc1#EXTENDED_ARG",
            see=("oparg", "instruction"),
            met="T06",
        ),
        Term(
            name="inline cache",
            short="Spare slots after an instruction where it writes down what happened last time.",
            long="They sit in the bytecode as if they were instructions and are stepped over rather than run. This is where a specialized instruction keeps the type it saw and whatever it worked out from it, which is why the number of slots is fixed per instruction family and why offsets in a disassembly jump by more than two.",
            see=("specialization", "instruction", "bytecode"),
            met="T06",
        ),
        Term(
            name="exception table",
            short="A side table saying, for each range of instructions, where to jump if something raises.",
            long="There are no instructions marking the start or end of a `try`. The compiler records ranges instead, and entering a `try` costs nothing at all at run time because there is nothing to execute. The number of entries rarely matches the number of keywords you wrote, since a `finally` has to appear once for the normal path and again for the raising one.",
            cite="InternalDocs/exception_handling.md:80-95@v3.15.0rc1#exception",
            see=("code object", "assembler"),
            met="T06",
        ),
        Term(
            name="line table",
            short="A side table mapping instruction offsets back to positions in the source.",
            long="It is compressed rather than being one entry per instruction, and it carries columns as well as lines, which is what lets a traceback underline the exact subexpression that failed. `code.co_positions()` unpacks it for you.",
            also=("`co_linetable`",),
            see=("code object",),
            met="T06",
        ),
    ),
)


RUNNING = Group(
    "Running the instructions",
    "The interpreter itself, and the machinery it uses to go faster than it looks like it should. T07 is the lesson, and parts three and four go further.",
    (
        Term(
            name="frame",
            short="The working space for one call: its locals, its value stack and where it was up to.",
            long="A frame is created per call, not per function, so a function called twice has two of them. Most of the time the interpreter allocates them in a contiguous chunk it manages itself rather than as ordinary objects, and the `frame` object you get from `sys._getframe` is a view onto that rather than the thing itself. A generator is the case where a frame outlives the call that made it.",
            cite="Include/internal/pycore_interpframe_structs.h:29-53@v3.15.0rc1#_PyInterpreterFrame",
            see=("value stack", "code object", "eval loop"),
            met="T07",
        ),
        Term(
            name="value stack",
            short="Where an instruction leaves its results for the next instruction to pick up.",
            long="Nearly every instruction is described entirely by what it takes off the top and what it puts back, and reading a disassembly fluently is mostly a matter of tracking that. It lives inside the frame and its maximum depth is worked out at compile time and stored in the code object, so the space is reserved once when the frame is made.",
            also=("stack",),
            see=("frame", "stack effect"),
            met="T06",
        ),
        Term(
            name="stack effect",
            short="How many values an instruction takes off the stack and how many it leaves.",
            long="The numbers come from a table generated from `Python/bytecodes.c`, so they cannot drift from what the instructions actually do. Walking the graph and adding these up is how the compiler works out the stack size, and doing the same by hand down a listing is how you check that you have read it correctly.",
            cite="Include/internal/pycore_opcode_metadata.h:35-38@v3.15.0rc1#_PyOpcode_num_popped",
            see=("value stack", "instruction"),
            met="T06",
        ),
        Term(
            name="eval loop",
            short="The loop that fetches the next instruction and does it.",
            long="It is one very large function, and most of its body is generated from `Python/bytecodes.c` rather than typed, so the file to read is the input rather than the loop. It is worth knowing that the loop is also where a call to a Python function is handled without recursing into C, which is why deep Python recursion is fine and deep recursion through C is not.",
            cite="Python/ceval.c:1212-1218@v3.15.0rc1#_PyEval_EvalFrameDefault",
            also=("`_PyEval_EvalFrameDefault`", "ceval"),
            see=("dispatch", "frame", "generated file"),
            met="T07",
        ),
        Term(
            name="dispatch",
            short="Getting from the end of one instruction to the start of the right next one.",
            long="This happens more often than anything else in the interpreter, so it gets more attention than its two lines of code would suggest. The plain version is going back to the top of a loop with a switch in it, and the faster version gives each instruction its own jump.",
            cite="Python/ceval_macros.h:198-206@v3.15.0rc1#DISPATCH",
            see=("computed goto", "eval loop"),
            met="T07",
        ),
        Term(
            name="computed goto",
            short="A compiler extension letting each instruction jump straight to the next one.",
            long="Instead of every instruction returning to one shared switch, each ends with a jump through a table of labels. The reason it is faster is not the jump itself but the branch predictor: one shared switch is one branch the processor keeps guessing wrong, while a per instruction jump gives it many branches each with its own pattern to learn.",
            cite="Python/ceval_macros.h:128-141@v3.15.0rc1#DISPATCH_GOTO",
            see=("dispatch",),
            met="T07",
        ),
        Term(
            name="specialization",
            short="Swapping an instruction for a narrower one that assumes what it saw last time.",
            long="`BINARY_OP` on two ints becomes `BINARY_OP_MULTIPLY_INT`, which skips every check about what the operands might have been. It happens while the program runs, per instruction rather than per function, and it needs only a handful of executions, so a single call to a function with a loop in it is usually enough to see it happen.",
            cite="Python/bytecodes.c:657-670@v3.15.0rc1#_BINARY_OP_MULTIPLY_INT",
            see=("adaptive instruction", "deoptimization", "inline cache"),
            met="T07",
        ),
        Term(
            name="adaptive instruction",
            short="The general instruction that watches what happens and then specializes itself.",
            long="It counts down while it watches, and when the counter runs out it writes a narrower instruction over itself. The counter and the notes it takes live in the inline cache slots following it, which is why every instruction that can specialize has some.",
            see=("specialization", "inline cache"),
            met="T07",
        ),
        Term(
            name="deoptimization",
            short="Going back to the general instruction when the assumption stops being true.",
            long="A specialized instruction starts with a guard, and if the guard fails it hands control back to the general form rather than being wrong. This is what makes the whole scheme safe: the fast path never has to be right, it only has to notice when it is not.",
            see=("specialization", "adaptive instruction"),
            met="T07",
        ),
        Term(
            name="tier one",
            short="The ordinary interpreter, the one that runs the bytecode in the code object.",
            long="This is what runs everything, and for most programs it is the only thing that runs. The name only exists because there is now a second tier, and it is worth using because a sentence about the interpreter is ambiguous once there are two of them.",
            see=("tier two", "eval loop"),
            met="T07",
        ),
        Term(
            name="tier two",
            short="A second interpreter that runs traces of smaller operations, feeding the JIT.",
            long="When a loop gets hot enough, the bytecode inside it is projected into a straight line of much smaller operations, with the branches turned into guards that bail out to tier one. That straight line is what the JIT compiles, and it is also runnable on its own, which is what makes it possible to debug.",
            also=("uop", "micro operation"),
            see=("tier one", "JIT", "deoptimization"),
            met="T07",
        ),
        Term(
            name="JIT",
            short="The part that turns a hot trace into machine code at run time.",
            long="It is off unless the interpreter was built with it turned on, so the first thing to do with any claim about it is check whether it is running on your build. It compiles tier two traces rather than bytecode, which is why the tier two operations exist at all.",
            see=("tier two",),
            met="T07",
        ),
    ),
)


OBJECTS = Group(
    "Objects",
    "What every value in Python actually is, and the few fields they all share. T08 is the lesson.",
    (
        Term(
            name="object",
            short="Anything Python can name, which is everything, including types and functions.",
            long="Every value is a block of memory beginning with the same two fields, and every Python level operation on it goes through its type. There is no separate category of primitive values with different rules, which is the fact that makes the rest of the object model simple to describe and expensive to run.",
            cite="Include/object.h:127-150@v3.15.0rc1#_object",
            see=("object header", "type object"),
            met="T08",
        ),
        Term(
            name="object header",
            short="The reference count and the type pointer that every object starts with.",
            long="Two fields, in that order, at the front of every object. It is what lets a function take a `PyObject *` without knowing what it is and still be able to ask. Variable sized objects such as lists and tuples have a third field for the length.",
            cite="Include/object.h:156-170@v3.15.0rc1#_object",
            see=("object", "reference count", "type object"),
            met="T08",
        ),
        Term(
            name="type object",
            short="The object describing what another object is and what can be done to it.",
            long="It is itself an object, with a header and a reference count and a type of its own, and it holds the function pointers for everything from addition to deallocation. When Python needs to add two things, it looks in their type objects for the function to call, and that indirection is the whole of what people mean by dynamic typing here.",
            see=("object", "object header"),
            met="T08",
        ),
        Term(
            name="reference count",
            short="How many references to an object there currently are.",
            long="Every reference taken adds one and every reference released takes one away, and at zero the object is freed immediately. `sys.getrefcount` is the way to look at it from Python and its answer includes the reference created by asking, though as of 3.14 not always, because passing a local now often hands over a borrowed reference and costs nothing.",
            cite="Include/refcount.h:417-429@v3.15.0rc1#Py_DECREF",
            see=("new reference", "immortal object", "deallocation"),
            met="T08",
        ),
        Term(
            name="immortal object",
            short="An object whose count is parked at a value the interpreter never decreases.",
            long="`None`, `True`, `False`, the small integers and every type object are immortal. They are never freed, which saves the cost of counting references to objects that are shared by everything, and it means the number `sys.getrefcount` gives you for them is a marker rather than a count. Printing it next to a paragraph about reference counting teaches the wrong thing.",
            cite="Include/refcount.h:125-136@v3.15.0rc1#_Py_IsImmortal",
            see=("reference count",),
            met="T08",
        ),
        Term(
            name="interning",
            short="Keeping one shared copy of a string so that equal strings are often the same object.",
            long="Names, attribute names and anything that looks like an identifier get interned, because comparing them by address is much faster than comparing them character by character, and the interpreter compares them constantly. This is why `is` sometimes appears to work on strings, and why relying on that is a mistake: the rule is about what the compiler chose to intern, not about equality.",
            cite="Objects/codeobject.c:116-137@v3.15.0rc1#should_intern_string",
            see=("small integer cache",),
            met="T08",
        ),
        Term(
            name="small integer cache",
            short="A block of small integers made once at startup and handed out rather than built.",
            long="The range is a compile time constant and it moved in 3.15, from minus 5 through 256 up to minus 5 through 1024, which quietly broke every tutorial that had hard coded the old bound. Measure it rather than quoting it, which takes about four lines.",
            cite="Include/internal/pycore_runtime_structs.h:96-98@v3.15.0rc1#_PY_NSMALLPOSINTS",
            see=("interning", "immortal object"),
            met="T08",
        ),
        Term(
            name="instance dictionary",
            short="Where an ordinary object keeps its attributes.",
            long="It is a real dict and you can look at it, which is why `self.name = name` works without anything being declared anywhere. Instances of the same class share the layout of their keys rather than each holding a full copy, so the memory cost is much lower than a dict per object would suggest, and `__slots__` removes it entirely at the cost of the flexibility.",
            also=("`__dict__`",),
            see=("object", "type object"),
            met="T08",
        ),
    ),
)


MEMORY = Group(
    "Memory",
    "Where objects come from and what happens to them afterwards. T09 is the lesson.",
    (
        Term(
            name="obmalloc",
            short="CPython's own allocator, which handles every small object rather than passing it on.",
            long="Anything up to 512 bytes is served from memory CPython already holds, because objects that small are created and destroyed far too often for the system allocator to be a reasonable thing to call. Larger requests go straight through to `malloc`.",
            cite="Include/internal/pycore_obmalloc.h:156-164@v3.15.0rc1#SMALL_REQUEST_THRESHOLD",
            see=("block", "pool", "arena"),
            met="T09",
        ),
        Term(
            name="block",
            short="The smallest unit obmalloc hands out, rounded up to a multiple of sixteen bytes.",
            long="An object does not get the number of bytes it asked for, it gets the next size up, and every block in a given pool is the same size. That rounding is why two objects that differ by a few bytes can take exactly the same amount of memory.",
            cite="Include/internal/pycore_obmalloc.h:128-146@v3.15.0rc1#ALIGNMENT",
            see=("pool", "obmalloc"),
            met="T09",
        ),
        Term(
            name="pool",
            short="A page sized run of blocks that are all the same size.",
            long="Keeping one size per pool means allocating is taking the first entry off a free list and freeing is putting it back, with no searching and no merging of neighbours. It also means a pool is only reusable for objects of that size, which is where fragmentation comes from.",
            cite="Include/internal/pycore_obmalloc.h:232-241@v3.15.0rc1#POOL_BITS",
            see=("block", "arena"),
            met="T09",
        ),
        Term(
            name="arena",
            short="A large chunk requested from the operating system and carved up into pools.",
            long="This is the level at which memory is actually given back, and it can only go back when every pool inside it is empty. That is the mechanism behind the common observation that a Python process which allocated a lot of memory does not always return it: one live object in an arena keeps the whole thing.",
            cite="Include/internal/pycore_obmalloc.h:216-226@v3.15.0rc1#ARENA_BITS",
            see=("pool", "obmalloc"),
            met="T09",
        ),
        Term(
            name="deallocation",
            short="What happens the moment an object's reference count reaches zero.",
            long="The type's deallocation function runs, which releases the references the object was holding, so freeing one object often frees a chain of them. This is immediate and it is the main way memory is reclaimed. The cycle collector is the exception rather than the rule.",
            cite="Objects/object.c:3282-3300@v3.15.0rc1#_Py_Dealloc",
            see=("reference count", "finalizer", "reference cycle"),
            met="T09",
        ),
        Term(
            name="reference cycle",
            short="A group of objects that between them hold all the references keeping them alive.",
            long="Two objects pointing at each other is the smallest one. Counting alone can never free them, because each is being held by another member of the group, so both counts stay above zero long after the last name for either has gone. This is the entire reason a second mechanism exists.",
            see=("cycle collector", "reference count"),
            met="T09",
        ),
        Term(
            name="cycle collector",
            short="The part that finds groups of objects keeping each other alive and frees them.",
            long="It works by copying every count, subtracting the references that objects in the group hold to each other, and seeing which objects are left with nothing pointing at them from outside. Anything not reached from those is garbage. It only looks at container types, since an object that cannot refer to anything cannot be part of a cycle.",
            cite="Python/gc.c:485-501@v3.15.0rc1#subtract_refs",
            also=("gc",),
            see=("reference cycle", "generation"),
            met="T09",
        ),
        Term(
            name="generation",
            short="Which of the collector's three lists an object is currently in.",
            long="New objects go in the youngest, which is collected often and is small, and anything surviving a collection moves up to a list that is looked at less often. The bet is that most objects die young, and it is a good bet. Integers, floats and strings are not tracked at all.",
            cite="Include/internal/pycore_interp_structs.h:271-286@v3.15.0rc1#GC_GENERATION_INIT",
            see=("cycle collector",),
            met="T09",
        ),
        Term(
            name="weak reference",
            short="A reference that lets you reach an object without keeping it alive.",
            long="It is the only way to watch an object die from Python, because any ordinary name that could tell you is itself a reason it is still there. When the object goes, the weak reference starts returning `None` and any callback attached to it runs.",
            cite="Objects/weakrefobject.c:1001-1024@v3.15.0rc1#PyObject_ClearWeakRefs",
            see=("reference count", "deallocation"),
            met="T09",
        ),
        Term(
            name="finalizer",
            short="A `__del__` method, run before an object is freed.",
            long="The collector runs finalizers on the objects in a cycle before it frees any of them, and a finalizer that stores a reference to its own object somewhere can bring the whole group back. That case is handled rather than being an error, which is worth knowing before writing one.",
            cite="Python/gc.c:1041-1074@v3.15.0rc1#finalize_garbage",
            also=("`__del__`",),
            see=("deallocation", "cycle collector"),
            met="T09",
        ),
    ),
)


BUILDING = Group(
    "Building the interpreter",
    "The words that turn out to be about the binary rather than about the language. B01 through B04 are the lessons, and several numbers in the earlier lessons move when the build does.",
    (
        Term(
            name="configure",
            short="The script that inspects your machine and writes the Makefile and pyconfig.h.",
            long='Nobody wrote `configure`. It is generated from `configure.ac` by autoconf, and it is the file that turns your flags and your operating system into two files the rest of the build reads. The argument list you gave it survives in the finished interpreter as `sysconfig.get_config_var("CONFIG_ARGS")`, which is how you can find out how a Python you did not build was built.',
            also=("`./configure`", "`configure.ac`"),
            see=("debug build", "generated file"),
            met="B01",
        ),
        Term(
            name="pyconfig",
            short="The header full of #define lines saying what your system has and what you asked for.",
            long="Every C file in CPython includes `pyconfig.h`, and it is how one source tree becomes a different program on Linux, on macOS and in a browser. It is also more complete than `sysconfig`: the parser behind `sysconfig.get_config_vars` only matches macros whose names start with a capital letter, so every `_Py_` macro in the header is invisible from Python. When the two disagree, the header is the one the compiler saw.",
            cite="Lib/sysconfig/__init__.py:438@v3.15.0rc1#define_rx",
            also=("`pyconfig.h`",),
            see=("configure",),
            met="B01",
        ),
        Term(
            name="debug build",
            short="An interpreter built with Py_DEBUG, which checks its own invariants as it runs.",
            long="`--with-pydebug` turns on assertions all through the interpreter, adds `sys.gettotalrefcount`, and makes the allocator fill freed memory with a recognisable byte pattern so a use after free shows up as garbage instead of as the old value still sitting there. It also makes objects bigger and everything two to three times slower, which is why behaviour in this material comes from a debug build and timings never do.",
            cite="configure.ac:1771-1785@v3.15.0rc1#Py_DEBUG",
            also=("`--with-pydebug`", "`Py_DEBUG`"),
            see=("configure", "reference count"),
            met="B01",
        ),
        Term(
            name="free threaded build",
            short="CPython built without the GIL, which is a different interpreter rather than a flag.",
            long="`--disable-gil` sets `Py_GIL_DISABLED`, and what follows is not a switch: the object header gains fields, reference counting splits into a local count and a shared one, the allocator becomes per thread and the cycle collector is a different algorithm. Every reference count and every `sys.getsizeof` in the object lessons comes out differently here, which is why those lessons measure rather than assert.",
            also=("`--disable-gil`", "`Py_GIL_DISABLED`"),
            see=("reference count", "cycle collector", "object header"),
            met="B01",
        ),
        Term(
            name="profile guided optimization",
            short="Build the interpreter, run it to see which branches are hot, then build it again.",
            long="`--enable-optimizations` is worth roughly ten percent and turns a five minute build into twenty minutes or an hour, because the whole thing is compiled twice with a test run in between. It is the right flag for measuring speed and the wrong one for understanding a crash, since everything hot has been inlined into everything else by the time the debugger sees it.",
            cite="configure.ac:1847-1860@v3.15.0rc1#Py_OPT",
            also=("PGO", "`--enable-optimizations`"),
            see=("debug build",),
            met="B01",
        ),
        Term(
            name="WebAssembly",
            short="A portable instruction set that browsers run, and one of the targets CPython builds for.",
            long="CPython compiled to WebAssembly is a real CPython rather than a reimplementation, which is what makes the browser tier of this project possible at all. It is a 32 bit target, so a pointer is 4 bytes instead of 8, and every object size in the lessons shrinks with it. That is the single most common reason a number in a lesson does not match what a reader sees.",
            also=("wasm",),
            see=("Pyodide",),
            met="B01",
        ),
        Term(
            name="Pyodide",
            short="A CPython distribution compiled to WebAssembly, with a package installer attached.",
            long="This is what runs when you open one of these lessons in a browser without a local Python. It is a genuine CPython build, so `dis`, `gc` and `sys.monitoring` all work, but it is not the same build as the one on your laptop and a few things are missing from it. Every lesson opens with a banner that says which of the two you are on, for exactly this reason.",
            see=("WebAssembly",),
            met="B01",
        ),
    ),
)


DEBUGGING = Group(
    "Stopping a running interpreter",
    "The words for looking at a program that is halfway through doing something. Most of them come from B02, and about half are things you already have on your machine without knowing it.",
    (
        Term(
            name="pdb",
            short="The debugger that ships with Python, written in Python.",
            long="It is a subclass of `bdb.Bdb` and `cmd.Cmd`, which is to say a trace hook with a command prompt bolted on. Because the prompt is just a pair of streams, you can hand it a list of commands instead of a keyboard and get the whole session back as text, which is how this project shows one. `breakpoint()` is the short way in.",
            cite="Lib/pdb.py:488@v3.15.0rc1#Pdb",
            also=("`breakpoint()`", "`python -m pdb`"),
            see=("trace function", "gdb"),
            met="B02",
        ),
        Term(
            name="trace function",
            short="A function the interpreter calls back on every call, line and return.",
            long="Install one with `sys.settrace` and the interpreter will tell you about everything your program does, one event at a time. Every Python debugger, coverage tool and line profiler is built on this hook or on the newer `sys.monitoring`. It is also expensive, because it turns every line into a Python call, which is why nothing has it on by default.",
            cite="Lib/bdb.py:232-236@v3.15.0rc1#start_trace",
            also=("`sys.settrace`",),
            see=("pdb", "monitoring events"),
            met="B02",
        ),
        Term(
            name="monitoring events",
            short="The newer, cheaper way to be told what a running program is doing.",
            long="Added in 3.12, and what pdb prefers when it can get it. A trace function is called for every event whether you wanted it or not, while `sys.monitoring` lets a tool register for only the events it cares about, so an unwatched line costs nothing. Several tools can watch at once without fighting over the one hook.",
            also=("`sys.monitoring`", "PEP 669"),
            see=("trace function",),
            met="B02",
        ),
        Term(
            name="gdb",
            short="A debugger that works on a process from outside it, rather than from inside.",
            long="gdb attaches to a running program, or starts one under its control, and can stop it anywhere and read its memory. That is what makes it able to answer questions pdb cannot, because it does not need the program to still be running Python, or running at all. CPython ships a script for it, `Tools/gdb/libpython.py`, which teaches gdb what a Python frame looks like and adds the `py-bt` command.",
            also=("`py-bt`", "lldb"),
            see=("pdb", "backtrace", "debug build"),
            met="B02",
        ),
        Term(
            name="backtrace",
            short="The list of calls that were in progress when a program stopped.",
            long="A Python traceback and a C backtrace are the same idea at two levels, and a stopped interpreter has both at once. They do not have the same length: four nested Python calls can sit inside a single `_PyEval_EvalFrameDefault` frame, because the eval loop reuses one C frame for a whole chain of Python ones. `py-bt` is the command that reads the second out of the first.",
            also=("`bt`", "stack trace"),
            see=("gdb", "frame", "eval loop"),
            met="B02",
        ),
        Term(
            name="segmentation fault",
            short="The kernel taking a process away for touching memory that is not its own.",
            long="Not an exception. There is no interpreter left to build one, nothing is printed, and `try` and `except` never see it. You reach one through `ctypes` or through a C extension with a bug in it. A debugger attached to the corpse is the only thing that will tell you which line of Python was responsible, which is what `py-bt` is for.",
            also=("SIGSEGV", "segfault"),
            see=("gdb", "backtrace"),
            met="B02",
        ),
        Term(
            name="regen",
            short="The make targets that rewrite every generated file from its input.",
            long="`make regen-cases` rebuilds the twelve files that come out of `Python/bytecodes.c`, `make regen-all` does that and the rest, and the reason to know the names is that forgetting them is the classic wasted afternoon. You edit the input, you build, nothing changes, and the build was quietly using the generated files that were already there. The Makefile calls each generator directly, so you can run one on its own with the interpreter you already have.",
            also=("`make regen-all`", "`make regen-cases`"),
            see=("generated file", "Argument Clinic"),
            met="B04",
        ),
        Term(
            name="blurb",
            short="One file per change under Misc/NEWS.d, naming the issue it came from.",
            long="A user visible change ships with a small file whose name carries the issue number, and at release time they are collected into one file per version. It exists so that a release note is written by the person who made the change rather than by somebody guessing afterwards, and it means every entry in a release note is a link back to the argument that produced it.",
            cite="Misc/NEWS.d/next/Core_and_Builtins/README.rst:1-3@v3.15.0rc1",
            see=("devguide",),
            met="B04",
        ),
        Term(
            name="devguide",
            short="The separate repository that documents how to work on CPython.",
            long="Building, testing, the git workflow, what a core developer will ask you for and how long to expect to wait. It is written for a new contributor rather than for a reader, which makes it the wrong place to look for how the interpreter works and the right place to look for anything about the process around it. `InternalDocs/` in the main repository is the other half, and is the one written for somebody trying to understand the code.",
            also=("devguide.python.org",),
            see=("blurb", "generated file"),
            met="B04",
        ),
    ),
)


TESTING = Group(
    "Checking that it still works",
    "The words for CPython's own test suite. It is twice the size of the library it tests, it is ordinary unittest underneath, and the rest is what it takes to run four hundred files in a row without one of them spoiling the next.",
    (
        Term(
            name="regrtest",
            short="The runner CPython uses on its own test suite.",
            long="A layer on top of unittest that knows how to find test files in a directory, run each one in its own process, put a time limit on it, check the environment came back the way it was found, and hunt reference leaks. `python -m test` is how you start it. For one test file none of that matters and plain unittest does the same job.",
            cite="Lib/test/libregrtest/main.py:793-796@v3.15.0rc1#main",
            also=("`python -m test`", "`Lib/test/regrtest.py`"),
            see=("test case", "reference leak"),
            met="B03",
        ),
        Term(
            name="test case",
            short="One method on a unittest.TestCase subclass, whose name starts with test.",
            long="The unit everything else counts. A file holds several classes, a class holds several of these, and the dotted name of one, like `test.test_dis.DisTests.test_widths`, is what `-m` and `--list-cases` work in. Failing one prints FAIL, raising anything else prints ERROR, and the difference is worth knowing when you are reading a wall of them.",
            cite="Lib/unittest/case.py:393@v3.15.0rc1#TestCase",
            also=("`assertEqual`", "test method"),
            see=("regrtest",),
            met="B03",
        ),
        Term(
            name="reference leak",
            short="An object the interpreter can no longer reach and will never free.",
            long="Not a crash and not a failing test. The test passes, the memory stays, and the only sign is that the process holds a few more references after the test than before. Almost always a bug in C code that forgot a decref. Found by running a test several times over on a debug build and watching `sys.gettotalrefcount()`, which is what the `-R` flag does.",
            cite="Lib/test/libregrtest/refleak.py:196-209@v3.15.0rc1#check_rc_deltas",
            also=("`-R 3:3`", "refleak"),
            see=("reference count", "debug build"),
            met="B03",
        ),
        Term(
            name="environment changed",
            short="A test that passed and left something different behind it.",
            long="regrtest takes a copy of 28 things before each test file, from `os.environ` and `sys.path` down to whether your terminal still echoes, and compares afterwards. A mismatch is exit code 3, or a failure with `--fail-env-changed`. It matters because the files run in a random order in one process, so an untidy test breaks a different test on a different machine a week later.",
            cite="Lib/test/libregrtest/save_env.py:62-76@v3.15.0rc1#resources",
            also=("`--fail-env-changed`",),
            see=("regrtest",),
            met="B03",
        ),
        Term(
            name="resource",
            short="Something a test needs that the runner will not use unless told.",
            long="Network access, audio devices, large temporary files, anything slow or intrusive. A test asks for one with `@support.requires_resource('network')` and is skipped unless the run was started with `-u network`, or `-u all`. This is why a clean local run and a buildbot run do not cover the same tests.",
            cite="Lib/test/support/__init__.py:1354-1360@v3.15.0rc1#requires_resource",
            also=("`-u all`", "`requires_resource`"),
            see=("regrtest",),
            met="B03",
        ),
    ),
)


#: The groups, in the order a reader meets them, which is also the order of the lessons.
GROUPS: tuple[Group, ...] = (
    READING,
    FRONT_END,
    NAMES,
    COMPILING,
    RUNNING,
    OBJECTS,
    MEMORY,
    BUILDING,
    DEBUGGING,
    TESTING,
)

#: Every term, flattened.
TERMS: tuple[Term, ...] = tuple(term for group in GROUPS for term in group.terms)

_BY_NAME = {term.name.lower(): term for term in TERMS}


def names() -> list[str]:
    """Every term, alphabetically, which is the order somebody looking one up expects."""
    return sorted(term.name for term in TERMS)


def get(name: str) -> Term:
    """Look a term up. Raises rather than returning nothing, so a bad link fails the build."""
    try:
        return _BY_NAME[name.strip().lower()]
    except KeyError:
        raise KeyError(f"no glossary entry for {name!r}. There are {len(TERMS)} of them.") from None


def link(name: str, text: str = "") -> str:
    """A markdown link into the glossary on GitHub, for a lesson to drop into a sentence.

    The URL is absolute rather than relative because a notebook opened from a Colab badge
    has no idea which repository it came from, and a relative link would be broken for
    every reader who arrived that way.
    """
    term = get(name)
    return f"[{text or term.name}]({REPOSITORY}/blob/main/{PATH}#{term.anchor})"


def _entry(term: Term) -> list[str]:
    lines = [f"### {term.name}", "", f"**{term.short}**", "", term.long]
    notes = []
    if term.also:
        notes.append("Also written " + ", ".join(term.also) + ".")
    if term.met:
        notes.append(f"First met in {term.met}.")
    if term.see:
        related = ", ".join(f"[{other}](#{anchor(other)})" for other in term.see)
        notes.append(f"See also {related}.")
    if term.cite:
        # The full citation stays as the visible label rather than being shortened into the
        # link text. It is what `refcheck` scans for, so a definition whose source moved
        # fails the build here the same way it would in a lesson.
        notes.append(f"In the source: [`{term.cite}`]({url(term.cite)}).")
    if notes:
        lines += ["", " ".join(notes)]
    return lines


def markdown() -> str:
    """The whole of `GLOSSARY.md`, which is generated from this module rather than edited."""
    lines = [
        "# Glossary",
        "",
        "One definition per term, in one place, so that a lesson can use a word without stopping to explain it and without assuming you remember it from forty lessons ago. Lessons link into this file rather than repeating themselves.",
        "",
        "The order below is the order you meet these things, not alphabetical, because reading it straight through is a reasonable thing to do. If you are looking one up, the index is next.",
        "",
        "This file is generated from `pyxray/src/pyxray/glossary.py`. Edit that and run `just build-glossary`.",
        "",
        "## Index",
        "",
        " | ".join(f"[{name}](#{anchor(name)})" for name in names()),
        "",
    ]
    for group in GROUPS:
        lines += [f"## {group.title}", "", group.blurb, ""]
        for term in group.terms:
            lines += _entry(term)
            lines += [""]
    return "\n".join(lines).rstrip("\n") + "\n"


def main() -> int:
    """Write `GLOSSARY.md`, relative to wherever this was run from.

    `just build-glossary` runs it from the root of the repository, which is where the file
    belongs. There is no checker recipe next to it because the test suite already compares
    the committed file against this module, and one check is enough.
    """
    path = pathlib.Path(PATH)
    text = markdown()
    if path.exists() and path.read_text(encoding="utf-8") == text:
        print(f"{PATH} is up to date, {len(TERMS)} terms")
        return 0
    path.write_text(text, encoding="utf-8")
    print(f"wrote {PATH}, {len(TERMS)} terms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
