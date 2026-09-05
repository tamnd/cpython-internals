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
            long="`6 * 7` becomes 42 in the compiled file and the multiply never reaches the interpreter. It used to happen twice, once on the tree and once on the graph, but the tree pass is gone and all of it now runs on the graph. It stops when the answer would be unreasonably large, so folding a giant power does not make an import take a second and a megabyte. The old operand often stays behind in the constants with nothing loading it, which is a good thing to notice.",
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
            see=("code unit", "opcode", "oparg", "inline cache"),
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
        Term(
            name="marshal",
            short="The format a code object is written in when it goes to disk.",
            long="One byte says what an object is, and whatever that kind of object needs follows it. The low seven bits of that byte are an ascii letter, which is why a `.pyc` in a hex dump is half readable, and the top bit means the object is worth numbering so that something later can point at it instead of repeating it. It is not a general purpose serialisation format and is not safe to point at untrusted bytes.",
            cite="Python/marshal.c:460-495@v3.15.0rc1#w_object",
            see=("code object", "pyc file"),
            met="F12",
        ),
        Term(
            name="pyc file",
            short="A sixteen byte header and one marshalled code object.",
            long="The header is a magic number, a flags word, and the source file's modification time and length. The last two are what makes a `.pyc` go stale: if either does not match the source, the file is thrown away and the source is compiled again. Everything after byte sixteen is one code object, with the code objects for every function in the file sitting in its constants.",
            also=("`__pycache__`",),
            cite="Lib/importlib/_bootstrap_external.py:413-444@v3.15.0rc1#_classify_pyc",
            see=("marshal", "magic number", "code object"),
            met="F12",
        ),
        Term(
            name="magic number",
            short="The four bytes at the front of a pyc that say which Python wrote it.",
            long="Only the first two are the number, and it goes up whenever the bytecode changes, which is what stops a `.pyc` from one release being loaded by another. The other two bytes are a carriage return and a newline, put there so that anything copying the file in text mode corrupts those two bytes and fails the check loudly rather than loading something strange.",
            cite="Include/internal/pycore_magic_number.h:313-318@v3.15.0rc1#PYC_MAGIC_NUMBER_TOKEN",
            see=("pyc file",),
            met="F12",
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
            name="tail call",
            short="A call that is the last thing a function does, so it can reuse the stack frame.",
            long="Nothing happens after the call returns, so there is nothing left to come back for, and the compiler can jump to the callee rather than stack a new frame on top. CPython asks for this with `musttail`, which is a demand rather than a hint: if the compiler cannot manage it, the build fails instead of producing an interpreter that overflows the stack.",
            cite="Python/ceval_macros.h:82-97@v3.15.0rc1",
            also=("musttail",),
            see=("dispatch table", "calling convention", "dispatch", "C stack"),
            met="E11",
        ),
        Term(
            name="dispatch table",
            short="An array of 256 entries, one per possible opcode byte, holding where to go next.",
            long="In a computed goto build the entries are label addresses and in a tail calling build they are function pointers, but either way there is one entry for every value a byte can hold. Values that no opcode claimed point at a handler that reports a corrupt code object, which is why dispatch needs no bounds check.",
            cite="Tools/cases_generator/target_generator.py:74-82@v3.15.0rc1",
            see=("dispatch", "computed goto", "tail call", "opcode"),
            met="E11",
        ),
        Term(
            name="calling convention",
            short="The agreement about which registers a call may use and which it must hand back.",
            long="It is normally invisible, because both sides of every call agree on it. The tail calling interpreter changes it on purpose with `preserve_none`, which says no register has to be handed back untouched, because the caller is finished and nobody is coming back to look. That is what lets the values being carried between opcodes stay in registers.",
            cite="Python/ceval_macros.h:74-80@v3.15.0rc1",
            also=("preserve_none",),
            see=("tail call", "C stack"),
            met="E11",
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
        Term(
            name="instruction DSL",
            short="The small language that `Python/bytecodes.c` is written in.",
            long="It looks like C and is not. Each definition opens with a line saying what kind of thing it is, what it is called, and what it takes off the stack and leaves behind, and only the body after that is ordinary C. That first line is what lets one file produce the eval loop, the stack effect tables, the cache sizes and the opcode numbers, because all of it is stated once in a form a program can read.",
            cite="Python/bytecodes.c:1-7@v3.15.0rc1",
            also=("the DSL", "`bytecodes.c`"),
            see=("cases generator", "generated file", "stack effect", "eval loop"),
            met="E01",
        ),
        Term(
            name="cases generator",
            short="The set of scripts under `Tools/cases_generator` that read the DSL and write C.",
            long="There is a shared parser and then one script per output file, so adding an instruction means editing one definition and running `make regen-all`. Every file it writes opens with the same four line banner naming the script and the input and ending in `Do not edit!`, which is the quickest way to tell a generated file from a written one.",
            cite="Tools/cases_generator/generators_common.py:66-75@v3.15.0rc1#write_header",
            see=("instruction DSL", "generated file", "regen"),
            met="E01",
        ),
        Term(
            name="specialization family",
            short="A base opcode and the faster versions it can turn into, declared as a group.",
            long="The declaration is one line in the DSL naming the base instruction, its cache size and its members. Everything downstream comes from that: the table mapping a specialized opcode back to its base, the `_specializations` dict in `_opcode_metadata`, and the checks that every member has the same stack effect and cache layout as the base. There is no separate list to keep in step.",
            cite="Python/bytecodes.c:484-491@v3.15.0rc1#family",
            also=("`family`",),
            see=("specialization", "adaptive instruction", "inline cache", "instruction DSL"),
            met="E01",
        ),
        Term(
            name="code unit",
            short="The sixteen bits an instruction occupies, which are not always an instruction.",
            long="It is a union of three readings of the same word: two bytes for an opcode and its argument, one whole word used as a cache slot, and a counter the specializer counts down. Nothing in the word says which reading applies, so the only way to know is to have walked the stream from the start and kept track of how many cache slots each instruction claims.",
            cite="Include/internal/pycore_structs.h:25-32@v3.15.0rc1",
            also=("`_Py_CODEUNIT`",),
            see=("instruction", "inline cache", "instruction pointer", "bytecode"),
            met="E02",
        ),
        Term(
            name="instruction pointer",
            short="The interpreter's place in the instruction stream, kept in a local C variable.",
            long="It is called `next_instr`, and it is already pointing past the current instruction while that instruction runs. Everything moves it: fetching advances it by one word, a cache carrying instruction skips over its own slots, and a jump adds a signed count of words. Because it lives in a register rather than in the frame, anything that needs the real position, like a traceback, has to write it back first.",
            cite="Python/ceval_macros.h:249-254@v3.15.0rc1#next_instr",
            also=("`next_instr`",),
            see=("code unit", "dispatch", "eval loop", "frame"),
            met="E02",
        ),
        Term(
            name="data stack",
            short="The memory the interpreter allocates frames from, which is not the C stack.",
            long="It is a linked list of chunks, sixteen kilobytes each by default, owned by the thread state. Calling a Python function takes the next few slots off the top, and returning hands them straight back, so a call is a pointer bump rather than an allocation. This is the reason a hundred thousand deep Python recursion works while the same depth routed through a C function does not.",
            cite="Python/pystate.c:3133-3143@v3.15.0rc1#_PyThreadState_PushFrame",
            also=("datastack",),
            see=("frame", "frame object", "C stack"),
            met="E03",
        ),
        Term(
            name="frame object",
            short="The Python level `frame` you can hold, which is not the frame the interpreter uses.",
            long="The interpreter runs on a bare struct with no reference count and no type. The `frame` object is made only when something asks for one, which `sys._getframe`, a traceback and any debugger all do. Once made it is cached on the interpreter frame, so asking twice gives the same object, and if the call returns while somebody still holds it the object takes ownership of the contents rather than leaving a dangling view.",
            cite="Include/internal/pycore_interpframe_structs.h:36-36@v3.15.0rc1#frame_obj",
            also=("`PyFrameObject`",),
            see=("frame", "data stack", "trace function"),
            met="E03",
        ),
        Term(
            name="C stack",
            short="The machine stack the thread actually runs on, with a size fixed when it starts.",
            long="Python calls do not use it, but any call that goes out through C and back into Python does, and each one of those costs somewhere between hundreds of bytes and several kilobytes. CPython checks how much room is left rather than counting calls, which is why the resulting `RecursionError` says how many kilobytes were used instead of what the limit was.",
            see=("data stack", "frame", "eval loop"),
            met="E03",
        ),
        Term(
            name="stack reference",
            short="What a frame slot holds, which is a pointer with the bottom bits used for something.",
            long="Every slot in a frame, both the locals and the value stack, holds one of these rather than a plain object pointer. The bottom two bits say whether the slot owns a counted reference, is only borrowing one, or is not holding a pointer at all. Everything that used to be an unconditional increment or decrement is now a test on those two bits first.",
            cite="Include/internal/pycore_stackref.h:533-537@v3.15.0rc1#PyStackRef_Borrow",
            also=("`_PyStackRef`",),
            see=("tagged pointer", "borrowed reference", "reference count", "frame"),
            met="E04",
        ),
        Term(
            name="tagged pointer",
            short="A pointer with extra information hidden in the bits that are always zero.",
            long="Objects are aligned in memory, so the bottom two bits of any object pointer are zero and can be used to carry a flag. CPython uses one of them to mean this reference was not counted, so releasing it should do nothing. The flag that marks an object immortal is deliberately the same bit value, which is why building the tagged reference is a single AND with no branch.",
            cite="Include/internal/pycore_stackref.h:53-58@v3.15.0rc1#Py_TAG_REFCNT",
            see=("stack reference", "immortal object", "pointer"),
            met="E04",
        ),
        Term(
            name="tagged integer",
            short="A small number living in a stack slot with no object anywhere.",
            long="The bottom bits can also say that the rest of the word is not a pointer but a number shifted up by two. From 3.15 the interpreter uses this for the position a `for` loop has reached in a list or a tuple, so the counter sits on the value stack with nothing allocated for it. It is why a loop over a list needs one more stack slot in 3.15 than it did in 3.14.",
            cite="Include/internal/pycore_stackref.h:432-438@v3.15.0rc1#PyStackRef_TagInt",
            see=("stack reference", "tagged pointer", "value stack"),
            met="E04",
        ),
        Term(
            name="zero cost exceptions",
            short="Entering a try block runs no instructions, so it costs nothing until something raises.",
            long="Older CPython pushed a block onto a stack when a try started and popped it when the try ended, which meant every guarded region paid on the way in and on the way out whether or not anything went wrong. Since 3.11 the compiler writes the same information into a table on the side of the code object instead, and the interpreter only reads that table when an exception is already in flight. Raising got a little more expensive and not raising got free.",
            cite="InternalDocs/exception_handling.md:48-53@v3.15.0rc1#metadata",
            see=("exception table", "unwinding", "pseudo instruction"),
            met="E05",
        ),
        Term(
            name="unwinding",
            short="Walking back out through frames looking for something that will catch the exception.",
            long="When an instruction raises, the interpreter looks the current offset up in the exception table of the code object it is running. If there is a handler it trims the value stack to the depth the table recorded and jumps there. If there is not, it adds the frame to the traceback, drops it, and asks the same question of the caller, all the way up until something catches or the top is reached.",
            cite="Python/bytecodes.c:6519-6558@v3.15.0rc1#exception_unwind",
            see=("exception table", "traceback", "frame", "zero cost exceptions"),
            met="E05",
        ),
        Term(
            name="traceback",
            short="The chain of frames an exception passed through, built one link at a time as it unwinds.",
            long="It is not captured at the point of the raise. Each frame the exception leaves adds itself to the front of the chain on the way past, which is why the cost of raising grows with how far the exception has to travel and why the printed report reads from the outermost call inwards. Every link records the offset in that frame's bytecode, so the report can point at the exact instruction.",
            also=("`__traceback__`",),
            cite="Python/bytecodes.c:6509-6514@v3.15.0rc1#PyTraceBack_Here",
            see=("unwinding", "frame object", "line table"),
            met="E05",
        ),
        Term(
            name="varint",
            short="A number written in as many bytes as it needs, six bits at a time.",
            long="Both the exception table and the line table use it, because most of the numbers in them are small and a fixed width field would waste space on every entry. Six bits of each byte carry data, one says whether another byte follows, and in the exception table the top bit is reserved to mark the first byte of an entry, which is what makes a binary search over variable sized entries possible.",
            cite="Python/assemble.c:157-188@v3.15.0rc1#assemble_exception_table",
            see=("exception table", "line table", "assembler"),
            met="E05",
        ),
        Term(
            name="adaptive counter",
            short="Two bytes of cache saying how much longer to wait before rewriting this instruction.",
            long="It sits in the first cache slot after an instruction that can specialize, and it is a number packed together with a backoff exponent. A cold instruction starts at one, so the second execution triggers a specialization attempt. Once specialized it is reset to fifty two, so it takes fifty three failures before the instruction gives up and tries something else. Both numbers are named constants you can read.",
            cite="Include/internal/pycore_code.h:450-464@v3.15.0rc1#ADAPTIVE_WARMUP_VALUE",
            see=("adaptive instruction", "inline cache", "specialization", "deoptimization"),
            met="E06",
        ),
        Term(
            name="guard",
            short="The check at the top of a specialized instruction that says whether it may run.",
            long="`BINARY_OP_ADD_INT` is really two type checks followed by an addition that skips every other question. If a check fails the instruction bails out to the general form instead of being wrong, which is why specializing is safe: the fast path never has to be correct in general, it only has to notice when it does not apply.",
            cite="Python/bytecodes.c:635-643@v3.15.0rc1#_GUARD_TOS_INT",
            see=("specialization", "deoptimization", "adaptive instruction"),
            met="E06",
        ),
        Term(
            name="quickening",
            short="Taking a private copy of the bytecode so it can be rewritten without touching the original.",
            long="`co_code` is what the compiler produced and never changes. The interpreter runs a separate copy, reachable as `_co_code_adaptive`, and that copy is what specialized instructions get written into. It is why disassembling a function gives one answer by default and a different one with `adaptive=True`, and why marshalling a warmed up function to a `.pyc` file still writes the cold version.",
            cite="Python/specialize.c:63-70@v3.15.0rc1#_PyCode_Quicken",
            see=("specialization", "code object", "bytecode", "inline cache"),
            met="E06",
        ),
        Term(
            name="micro operation",
            short="One of the small pieces a bytecode instruction is broken into for tier two.",
            long="A single instruction like `BINARY_OP_ADD_INT` is really a guard, another guard and an addition, and in tier two those become three separate operations rather than one. Splitting them up is what lets the optimizer notice that the second copy of a guard cannot fail and delete it, which is not something you can do while the three are welded together.",
            also=("uop",),
            cite="Python/bytecodes.c:672-685@v3.15.0rc1#_BINARY_OP_ADD_INT",
            see=("tier two", "trace", "executor", "guard"),
            met="E07",
        ),
        Term(
            name="trace",
            short="A straight line of micro operations recorded from one actual trip through a hot loop.",
            long="The recorder follows what the program really did, so a branch does not become two paths. It becomes whichever path was taken, plus a guard that bails out to the ordinary interpreter if the other one happens next time. That is why a trace can be optimized like straight line code even though the source it came from is full of branching.",
            cite="InternalDocs/jit.md:37-48@v3.15.0rc1",
            see=("micro operation", "executor", "side exit", "tier two"),
            met="E07",
        ),
        Term(
            name="executor",
            short="The object holding one optimized trace, attached to the code object it came from.",
            long="It is a real Python object you can fetch with `_opcode.get_executor` and iterate over, which is unusual for something this deep in the machinery. Each item is one micro operation with its argument and its jump target, so an executor is readable in the same way a code object is.",
            cite="Python/optimizer.c:124-140@v3.15.0rc1#_PyOptimizer_Optimize",
            see=("trace", "micro operation", "JIT", "code object"),
            met="E07",
        ),
        Term(
            name="side exit",
            short="The point where a guard in a trace fails and control goes back to the ordinary interpreter.",
            long="Every guard in a trace has one, which is why a trace of twenty three operations can be forty one operations long: the extra ones are the cold tails nobody runs unless a guess turns out wrong. A side exit that keeps getting taken can itself get hot and grow a trace of its own.",
            cite="Python/bytecodes.c:6183-6196@v3.15.0rc1#_EXIT_TRACE",
            see=("trace", "guard", "deoptimization", "executor"),
            met="E07",
        ),
        Term(
            name="instrumented instruction",
            short="An opcode swapped into the bytecode so that running it also calls a tool back.",
            long="Every instruction a monitoring tool can be told about has a paired form whose name starts with `INSTRUMENTED_`. Switching an event on writes those paired forms over the ordinary ones, and switching it off writes the ordinary ones back, so a function you are not watching runs exactly the bytecode it always did. It is the same trick as specialization pointed the other way: rewrite the instruction rather than test a flag inside it.",
            cite="Python/instrumentation.c:757-784@v3.15.0rc1#instrument",
            see=("monitoring events", "tool id", "specialization", "bytecode"),
            met="E08",
        ),
        Term(
            name="tool id",
            short="One of the numbered slots a monitoring tool claims before it can ask for events.",
            long="There are eight in the C code and six you can use, because the last two are held for `sys.settrace` and `sys.setprofile`. Claiming one is how a debugger and a coverage tool stay out of each other's way: each registers its own callbacks and asks for its own events, and the interpreter keeps a separate set of them per slot rather than one hook everybody has to share.",
            also=("`sys.monitoring.use_tool_id`",),
            cite="Include/internal/pycore_instruments.h:71-77@v3.15.0rc1#PY_MONITORING_TOOL_IDS",
            see=("monitoring events", "instrumented instruction", "trace function"),
            met="E08",
        ),
        Term(
            name="DISABLE",
            short="What a monitoring callback returns to stop being called at that one place.",
            long="Returning it does not switch the event off everywhere. It removes the instrumentation from the single instruction that fired, so the rest of the program keeps reporting and that one line goes back to full speed. This is what makes a coverage tool cheap: it only ever needs to be told about a line once, so almost every line disables itself on its first execution and the loop around it runs as if nothing were watching.",
            also=("`sys.monitoring.DISABLE`",),
            cite="Python/instrumentation.c:971-994@v3.15.0rc1#call_one_instrument",
            see=("monitoring events", "instrumented instruction", "tool id"),
            met="E08",
        ),
        Term(
            name="abstract interpreter",
            short="The pass that walks a trace holding a description of each value instead of the value.",
            long="It steps through the recorded micro operations the way the interpreter would, but its stack holds notes like `this is an int` or `this is exactly that object` rather than real objects. Nothing runs, so nothing can be observed, and the only thing it produces is a shorter list of operations. Every deletion tier two makes comes out of one of those notes being specific enough to answer a question the trace was about to ask.",
            cite="Python/optimizer_analysis.c:803-829@v3.15.0rc1#_Py_uop_analyze_and_optimize",
            see=("trace", "micro operation", "guard", "tier two"),
            met="E09",
        ),
        Term(
            name="watcher",
            short="A callback the runtime fires when a dictionary or a type is modified.",
            long="It is how the optimizer is allowed to assume things. A trace that baked in the value of a global asks to be told if that module dictionary ever changes, and a trace that checked a type asks to be told if that type is patched. When the callback fires it throws away every executor that depended on the thing, so monkeypatching still works and simply costs you the optimized code. You can see the result from Python, because the executor's `is_valid` flips to False.",
            cite="Python/optimizer_analysis.c:140-158@v3.15.0rc1#globals_watcher_callback",
            see=("executor", "abstract interpreter", "trace", "deoptimization"),
            met="E09",
        ),
        Term(
            name="stencil",
            short="A chunk of machine code for one micro operation, compiled when CPython was built.",
            long="The build writes a tiny C file for each micro operation, containing that one operation and nothing else, and compiles it. What comes out is a run of finished instructions with a few blanks in it where addresses have to go. Nothing about your program is in there, which is exactly why it could be made months before your program existed.",
            cite="Tools/jit/template.c:123-133@v3.15.0rc1#_JIT_ENTRY",
            see=("copy and patch", "micro operation", "JIT", "generated file"),
            met="E10",
        ),
        Term(
            name="copy and patch",
            short="Building machine code by pasting prebuilt chunks together and filling in the blanks.",
            long="It is how CPython's JIT works and why it is fast enough to run while your program is waiting. For each micro operation in a trace it copies the chunk that was compiled at build time, then writes the addresses that only exist now into the blanks that chunk was left with. There is no instruction selection and no register allocation, so the size of the output is known before any of it is written.",
            also=("copy-and-patch",),
            cite="InternalDocs/jit.md:123-138@v3.15.0rc1",
            see=("stencil", "JIT", "executor", "trace"),
            met="E10",
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
            long="It is itself an object, with a header and a reference count and a type of its own, and it holds the function pointers for everything from addition to deallocation. When Python needs to add two things, it looks in their type objects for the function to call, and that indirection is the whole of what people mean by dynamic typing here. It is also the largest struct in the interpreter, and most of it is answers to questions about instances rather than about the type.",
            cite="Include/cpython/object.h:147-151@v3.15.0rc1#_typeobject",
            also=("`PyTypeObject`",),
            see=("object", "object header", "static type", "heap type"),
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
        Term(
            name="PyVarObject",
            short="An object header with a length field welded on the end of it.",
            long="Tuples, lists and bytes objects all hold a count of how many items they have, and rather than each of them inventing a field for it the header itself grows by one machine word called `ob_size`. It is the same trick as the header: put the thing everybody needs in a fixed place so that generic code can read it without knowing the type. Strings keep their length in the same place without being one of these, and integers used to and no longer do.",
            cite="Include/object.h:174-178@v3.15.0rc1#PyVarObject",
            also=("variable sized object", "`ob_size`"),
            see=("object header", "object"),
            met="O01",
        ),
        Term(
            name="slot",
            short="One of the function pointer fields in a type object.",
            long="`tp_repr`, `tp_hash`, `tp_call` and about seventy others. The interpreter reads them directly, so calling `repr(x)` is a load and an indirect call rather than a dictionary lookup. Python code never assigns to one. It defines a dunder method and a table walk fills the slot in, which is what makes the two spellings feel like the same thing.",
            cite="Objects/typeobject.c:11584-11590@v3.15.0rc1#slotdefs",
            also=("type slot",),
            see=("slot wrapper", "type object"),
            met="O03",
        ),
        Term(
            name="slot wrapper",
            short="A dunder method that is really a C slot with a Python callable wrapped around it.",
            long="When a type written in C is made ready, `add_operators` walks the slot table and puts one of these into the class dict for every slot that has a function in it. That is where `int.__add__` and `object.__repr__` come from: nobody wrote them as methods, they are `nb_add` and `tp_repr` made callable. `type(int.__add__).__name__` is `wrapper_descriptor`, which is how you tell one from an ordinary method.",
            cite="Objects/typeobject.c:12456-12470@v3.15.0rc1#add_operators",
            also=("`wrapper_descriptor`",),
            see=("slot", "type object"),
            met="O03",
        ),
        Term(
            name="descriptor",
            short="An object in a class dict whose type defines __get__, __set__ or __delete__.",
            long="Reading an attribute that resolves to a descriptor calls `__get__` rather than handing the object back. There is nothing to inherit from and nothing to register, so having the method is the whole qualification. Functions are descriptors, which is where `self` comes from: `func_descr_get` returns the function on a class and a bound method on an instance. `property`, `classmethod`, `staticmethod`, every `__slots__` entry and most attributes defined from C are descriptors too. The protocol only applies to objects found on the type, so a descriptor sitting in an instance dict is an ordinary value.",
            cite="Objects/funcobject.c:1264-1270@v3.15.0rc1#func_descr_get",
            also=("descriptor protocol",),
            see=("data descriptor", "slot"),
            met="O06",
        ),
        Term(
            name="bound method",
            short="A small object holding a function and the instance it was read from.",
            long="`PyMethod_New` allocates one with two pointers, `im_func` and `im_self`, and calling it inserts the instance as the first argument. That is all `self` is. A fresh one is built on every attribute read, so `obj.method is obj.method` is false, though the two compare equal. The allocation comes off a free list when one is available, and the interpreter specialises the common call shape so that reading and immediately calling a method skips building the object at all.",
            cite="Objects/classobject.c:64-84@v3.15.0rc1#PyMethod_New",
            see=("descriptor", "type object"),
            met="O06",
        ),
        Term(
            name="data descriptor",
            short="An object on a type that has __set__ or __delete__ as well as __get__.",
            long="The test is one line: `PyDescr_IsData` asks whether `tp_descr_set` is filled in. That one bit decides the whole precedence question, because attribute lookup calls a data descriptor before it ever looks in the instance dict and calls anything else after. `property` and the descriptors `__slots__` generates are data descriptors. A plain function is not, which is why you can shadow a method on one instance and cannot shadow a property.",
            cite="Objects/descrobject.c:1028-1032@v3.15.0rc1#PyDescr_IsData",
            also=("non data descriptor",),
            see=("slot", "type object"),
            met="O05",
        ),
        Term(
            name="MRO",
            short="The flat list of classes, in order, that a name is looked up in.",
            long="Every type carries one as `tp_mro`, computed once when the class is made and recomputed for the whole subtree if `__bases__` is later assigned. It always starts with the type itself and ends with `object`. Attribute lookup, `super`, and the slot table all read this list rather than walking `__bases__`, which is why multiple inheritance has one answer instead of a search.",
            cite="Objects/typeobject.c:3431-3451@v3.15.0rc1#mro_implementation_unlocked",
            also=("method resolution order", "`__mro__`", "`tp_mro`"),
            see=("C3 linearization", "type object"),
            met="O04",
        ),
        Term(
            name="C3 linearization",
            short="The merge rule that turns a class and its bases into one ordered list.",
            long="Take the MRO of each base, add the declared bases tuple, and repeatedly take the first head that does not appear later in any of the lists. If no such head exists the merge fails and you get a TypeError instead of a class. CPython spells this out in `pmerge`, and it is about forty lines. The rule guarantees a class comes before its bases and that the order you declared bases in is preserved.",
            cite="Objects/typeobject.c:3361-3400@v3.15.0rc1#pmerge",
            also=("C3", "the merge"),
            see=("MRO",),
            met="O04",
        ),
        Term(
            name="static type",
            short="A type object written out as a C literal and compiled into the binary.",
            long="`int`, `str`, `list` and `type` itself are all one of these. There is exactly one of each, it is immortal, and it lives in the binary rather than on the heap, so you cannot assign an attribute to it and there is nothing to collect at shutdown. The flags word is what tells you: a static type does not have `Py_TPFLAGS_HEAPTYPE` set.",
            cite="Objects/typeobject.c:7290-7295@v3.15.0rc1#PyType_Type",
            also=("builtin type",),
            see=("heap type", "type object"),
            met="O02",
        ),
        Term(
            name="heap type",
            short="A type object built while the program is running, which is what a class statement makes.",
            long="What actually gets allocated is a `PyHeapTypeObject`, a type object with all the operator tables attached after it, so a class costs about nine hundred bytes before you put anything in it. Unlike a static type it is reference counted, it can be collected, and you can assign to it, which is the whole difference between `Plain.nope = 1` working and `int.nope = 1` raising.",
            cite="Include/cpython/object.h:272-296@v3.15.0rc1#PyHeapTypeObject",
            also=("`PyHeapTypeObject`",),
            see=("static type", "type object", "metaclass"),
            met="O02",
        ),
        Term(
            name="metaclass",
            short="The type of a type, which is what gets called to build a class.",
            long='A class statement compiles to a call to `__build_class__`, which runs the class body, collects the names it defined, and calls the metaclass with the name, the bases and that namespace. Unless you say otherwise the metaclass is `type`, which is why `type("Greeter", (), {})` and a class statement produce the same thing.',
            cite="Python/bltinmodule.c:102-108@v3.15.0rc1#builtin___build_class__",
            see=("type object", "heap type"),
            met="O02",
        ),
        Term(
            name="compact dict",
            short="A dict laid out as a small array of slot numbers in front of an entry array.",
            long="The slot array, `dk_indices`, holds a row number into the entry array, or -1 for a position never used, or -2 for one that used to hold something. The entry array is appended to and never reordered, so iterating it top to bottom gives insertion order with no bookkeeping at all. Only the small array has holes, which is why the layout is called compact: a mostly empty hash table costs one byte per slot rather than a whole row.",
            cite="Include/internal/pycore_dict.h:196-235@v3.15.0rc1#_dictkeysobject",
            also=("compact ordered dict",),
            see=("probe sequence", "instance dictionary"),
            met="O07",
        ),
        Term(
            name="probe sequence",
            short="The order of slots a dict lookup visits when the first one is a collision.",
            long="The first slot is the hash masked down to the table size. After that the step is `i = mask & (i * 5 + perturb + 1)`, where `perturb` starts as the whole hash and is shifted right by 5 each round. The `i * 5 + 1` part visits every slot exactly once and in an order unrelated to how consecutive keys arrive, and `perturb` brings back the high bits of the hash the mask discarded. For a size 8 table starting at slot 0 the order is 0, 1, 6, 7, 4, 5, 2, 3.",
            cite="Objects/dictobject.c:1078-1101@v3.15.0rc1#do_lookup",
            see=("compact dict",),
            met="O07",
        ),
        Term(
            name="split table",
            short="A dict whose keys are owned by a type and shared by every instance of it.",
            long="The keys array is marked `DICT_KEYS_SPLIT` and hangs off the type rather than off any one instance, so the attribute names of a class are stored once instead of once per object. Each instance carries only an array of value pointers. `_PyDict_NewKeysForClass` builds the shared array when the class is created and prefills it from `__static_attributes__`, and `insert_split_key` adds any name discovered later. There is room for 30 names, or 29 if they are not known when the class is made, because creating the first instance reserves a slot.",
            cite="Objects/dictobject.c:7210-7238@v3.15.0rc1#_PyDict_NewKeysForClass",
            also=("shared keys",),
            see=("inline values", "compact dict"),
            met="O08",
        ),
        Term(
            name="inline values",
            short="The array of attribute values stored inside an instance, with no dict at all.",
            long="An instance of a class with a split table has its values allocated as part of the object, past whatever fields the type declared. Four bytes of bookkeeping come first, then one pointer per possible attribute, then one byte per attribute actually set recording which slot it went into, which is how per instance insertion order survives a shared keys array. `obj.__dict__` builds a real dict object on demand that points at the same values, and asking for it makes the instance permanently bigger and stops its attribute reads specialising.",
            cite="Objects/dictobject.c:7241-7274@v3.15.0rc1#_PyObject_InitInlineValues",
            also=("managed dict",),
            see=("split table", "instance dictionary"),
            met="O08",
        ),
        Term(
            name="digit array",
            short="The array of base 2**30 digits an int is made of, least significant first.",
            long="A digit is a `uint32_t` carrying 30 bits, so two bits in every four bytes go unused. That is deliberate: the product of two digits fits in 64 bits with enough headroom left to accumulate carries before anything has to be done about overflow. Two rules hold everywhere in the source and every operation is allowed to assume them, that no digit is ever at or above the base, and that the most significant digit is never zero. The second is why almost everything ends by calling `long_normalize`.",
            cite="Include/cpython/longintrepr.h:64-91@v3.15.0rc1",
            also=("ob_digit",),
            see=("compact int",),
            met="O09",
        ),
        Term(
            name="compact int",
            short="An int small enough to be a sign and one digit, with a fast path all its own.",
            long="The sign, the digit count and one flag share a single word called `lv_tag`, packed so that a tag below 16 means the digit count is 0 or 1 and the sign is not negative. `_PyLong_IsCompact` is that one unsigned comparison, and the value comes back out with a multiply and no branches. Anything from 0 up to 2**30 - 1 qualifies on an ordinary build, which is most of the integers a program actually handles, so the fast path is taken constantly.",
            cite="Include/cpython/longintrepr.h:121-125@v3.15.0rc1#_PyLong_IsCompact",
            see=("digit array", "small int cache"),
            met="O09",
        ),
        Term(
            name="small int cache",
            short="The fixed array of int objects built at startup and handed out rather than allocated.",
            long="Every operation whose result lands in the range returns the object from the array instead of making a new one, so two separate computations that reach the same small value give you the same object. They are immortal, because an object handed to everybody forever cannot usefully be reference counted. The range runs from -5 up to a ceiling that was 256 through 3.14 and is 1024 from 3.15, which is why using `is` on integers is a bug waiting for a version bump.",
            cite="Include/internal/pycore_runtime_structs.h:97-98@v3.15.0rc1#_PY_NSMALLPOSINTS",
            also=("small ints",),
            see=("compact int", "immortal object"),
            met="O09",
        ),
        Term(
            name="code point",
            short="The number Unicode assigns to a character, from 0 up to 0x10FFFF.",
            long="A Python string is a sequence of code points, not of bytes, and `len` counts code points. This is the thing that makes strings portable and it is also the thing that makes them expensive, because the largest code point present decides how many bytes every character in the string takes. `ord` gives you the code point of a character and `chr` goes back the other way.",
            cite="Include/cpython/unicodeobject.h:66-88@v3.15.0rc1",
            see=("string kind", "compact string"),
            met="O10",
        ),
        Term(
            name="string kind",
            short="Whether a string stores each character in 1, 2 or 4 bytes.",
            long="The kind is set once when the string is created, from the largest code point in it, and it never changes afterwards because strings are immutable. One byte if nothing goes above 255, two if nothing goes above 65535, four otherwise. There is a fourth case that is not a kind value but behaves like one: a string where everything is ASCII gets a smaller struct as well as one byte characters. Adding a single wide character to a narrow string rewrites every character in it at the wider size.",
            cite="Objects/unicodeobject.c:1272-1311@v3.15.0rc1#PyUnicode_New",
            also=("kind",),
            see=("code point", "compact string"),
            met="O10",
        ),
        Term(
            name="compact string",
            short="A string whose characters sit in the same allocation as its header.",
            long="One `PyObject_Malloc` covers the struct, the characters and a trailing zero byte, so there is no second block and no pointer to follow. That trailing zero is why the buffer can be handed straight to C functions expecting a null terminated string. The alternative, called the legacy form in the source, keeps the characters in a separate block and only shows up for subclasses of `str`, which have their own fields to store.",
            cite="Objects/unicodeobject.c:1322-1336@v3.15.0rc1",
            see=("string kind", "interning"),
            met="O10",
        ),
        Term(
            name="over allocation",
            short="Asking for more room than is needed right now, so the next few asks are free.",
            long="A list keeps two sizes: `ob_size`, how many items you can see, and `allocated`, how many slots the array behind it has. `list_resize` asks for the new size plus an eighth of it plus six, rounded down to a multiple of four, which gives the sequence 4, 8, 16, 24, 32, 40, 52, 64, 76, 92. Growing by a fraction of the current size is what makes a long run of appends cheap on average: a hundred thousand appends cost about sixty six reallocations rather than a hundred thousand. The same function shrinks the array, but only once the length drops below half of what is allocated.",
            cite="Objects/listobject.c:119-129@v3.15.0rc1",
            see=("cached hash",),
            met="O11",
        ),
        Term(
            name="cached hash",
            short="A hash computed on the first ask and kept in the object from then on.",
            long="Strings and tuples both do this, and both can only do it because they cannot change. The field starts at -1 and the hash function returns early if it is anything else. This is the real reason a tuple can be a dict key and a list cannot: a container that can change has no stable hash to offer. It is also why a recycled tuple taken off a free list has to have the field cleared before it is handed out again.",
            cite="Objects/tupleobject.c:371-404@v3.15.0rc1#tuple_hash",
            see=("over allocation", "compact string"),
            met="O11",
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
            name="size class",
            short="One of the 32 block sizes obmalloc serves, sixteen bytes apart.",
            long="A request is rounded up to the next multiple of sixteen and served from a pool holding only that size, so 16, 32, 48 and so on up to 512. Nothing in between exists. Asking for 17 bytes gets you 32 and the other fifteen are not given back to anyone until you free the block.",
            cite="Include/internal/pycore_obmalloc.h:137-146@v3.15.0rc1#INDEX2SIZE",
            see=("block", "pool", "obmalloc"),
            met="M02",
        ),
        Term(
            name="pool header",
            short="The 48 bytes at the front of every pool that say what the pool is holding.",
            long="It records how many blocks are in use, where the free list starts, which size class the pool serves, which arena it belongs to, and the two pointers linking it to the other pools of the same class. Those 48 bytes are why a pool holds 1021 sixteen byte blocks rather than 1024.",
            cite="Include/internal/pycore_obmalloc.h:263-274@v3.15.0rc1#pool_header",
            see=("pool", "block", "arena"),
            met="M02",
        ),
        Term(
            name="mimalloc",
            short="The second small object allocator, already compiled into your Python and picked with one variable.",
            long="It came from Microsoft Research and CPython vendors a modified copy of it. Setting `PYTHONMALLOC=mimalloc` swaps it in for obmalloc on any ordinary build, and the free threaded build has no choice about it because obmalloc is compiled out there entirely. It serves requests up to 16384 bytes across 73 size classes rather than 512 bytes across 32.",
            cite="Objects/obmalloc.c:781-796@v3.15.0rc1#PYMEM_ALLOCATOR_MIMALLOC",
            see=("obmalloc", "segment", "mimalloc heap", "PYTHONMALLOC"),
            met="M03",
        ),
        Term(
            name="segment",
            short="mimalloc's version of an arena, 32 MiB asked from the system and split into 64 KiB pages.",
            long="The record describing each page lives in the segment header rather than in the page itself, which is the one design decision the rest of mimalloc follows from. Because nothing is stored in front of the blocks, a block can start exactly at the page boundary, and a page can be handed to a single thread without anybody else needing to read it.",
            cite="Include/internal/mimalloc/mimalloc/types.h:203-211@v3.15.0rc1#MI_SEGMENT_SHIFT",
            see=("mimalloc", "arena", "pool"),
            met="M03",
        ),
        Term(
            name="mimalloc heap",
            short="One thread's private set of pages, of which each thread gets four rather than one.",
            long="The four are mem for plain buffers, object for objects the cycle collector never has to look at, and two more for collected objects, split by whether the object carries a pre header. Keeping collected objects in their own heaps is what lets the free threaded collector find every object by walking the heap instead of by following a linked list.",
            cite="Include/internal/pycore_mimalloc.h:12-18@v3.15.0rc1#_Py_mimalloc_heap_id",
            see=("mimalloc", "segment", "GC pre header", "cycle collector"),
            met="M03",
        ),
        Term(
            name="allocator domain",
            short="One of the three entrances to CPython's heap, each with its own set of functions.",
            long="Raw is for work that happens outside an interpreter and has to be safe to call with no lock held, mem is for buffers that belong to an object, and obj is for the objects themselves. They are not interchangeable. Each domain is four function pointers a program embedding Python may replace, and under the debug hooks each one writes a different letter in front of every block it hands out.",
            cite="Include/cpython/pymem.h:5-14@v3.15.0rc1#PyMemAllocatorDomain",
            also=("`PYMEM_DOMAIN_RAW`", "`PYMEM_DOMAIN_MEM`", "`PYMEM_DOMAIN_OBJ`"),
            see=("debug hooks", "obmalloc", "PYTHONMALLOC"),
            met="M01",
        ),
        Term(
            name="debug hooks",
            short="A wrapper around whatever allocator is underneath, adding a header and fences to every block.",
            long="Sixteen extra bytes go in front of your pointer, holding the size you asked for and one letter naming the domain, and eight more go behind it. The fences are filled with a byte that is not a plausible number or address, fresh memory is filled with another and freed memory with a third. Every free reads them all back and stops the process rather than continuing on a corrupted heap.",
            cite="Objects/obmalloc.c:3088-3097@v3.15.0rc1",
            see=("allocator domain", "PYTHONMALLOC"),
            met="M01",
        ),
        Term(
            name="PYTHONMALLOC",
            short="The environment variable that picks what sits underneath the three domains.",
            long="It is read once at startup and nothing above the domains can tell the difference afterwards. Setting it to `malloc` takes CPython's own small object allocator out entirely, which is what a tool like Valgrind wants because it needs to see each allocation rather than one large chunk being carved up out of sight. Adding `debug` to any of the names switches the fences on as well.",
            cite="Include/cpython/pymem.h:16-30@v3.15.0rc1#PyMemAllocatorName",
            see=("allocator domain", "debug hooks", "obmalloc"),
            met="M01",
        ),
        Term(
            name="ownership",
            short="The rule about who is responsible for putting a reference back down.",
            long="Every function that hands you a pointer to an object either gives you a reference of your own, which you owe back, or lets you look at one somebody else is holding, which you do not. There is no third option and no way to tell from the pointer, so the answer has to be part of what the function promises. Getting it wrong one way leaks and the other way crashes.",
            cite="Include/refcount.h:285-292@v3.15.0rc1#ob_refcnt",
            see=("reference count", "new reference", "borrowed reference", "stolen reference"),
            met="M04",
        ),
        Term(
            name="reentrancy",
            short="Code being entered again while an earlier call to it is still part way through.",
            long="Dropping the last reference to an object runs that object's destructor, and a destructor can be arbitrary Python, so any C code that drops a reference has to be finished making sense of itself first. This is why a container empties itself before it releases what it held, rather than the other way round.",
            cite="Objects/dictobject.c:3073-3098@v3.15.0rc1#clear_lock_held",
            see=("deallocation", "finalizer", "reference count"),
            met="M04",
        ),
        Term(
            name="deferred reference counting",
            short="Marking an object so that nothing counts references to it at all.",
            long="The free threaded build sets an object's shared count to `PY_SSIZE_T_MAX / 8`, which is so far from zero that no amount of dropping references will ever get there. Nothing frees the object by counting, so only the cycle collector can, and it is the only thing that looks. Top level functions, classes, modules and methods get this, because they are read constantly from every thread and almost never dropped.",
            also=("`_Py_REF_DEFERRED`",),
            cite="Objects/object.c:2802-2812@v3.15.0rc1#_PyObject_SetDeferredRefcount",
            see=("free threaded build", "immortal object", "reference count"),
            met="M06",
        ),
        Term(
            name="biased reference counting",
            short="Splitting one count into a fast half for the owning thread and a shared half for everybody else.",
            long="The object records which thread created it. That thread adds and subtracts in a plain 32 bit field with no atomic instruction, and any other thread has to use an atomic on a second field. The real count is the two added together. It works because most objects are made, used and dropped on one thread, so the cheap path is the one almost every reference takes.",
            also=("`ob_ref_local`", "`ob_ref_shared`", "`ob_tid`"),
            cite="Include/refcount.h:105-117@v3.15.0rc1#_Py_REFCNT",
            see=("free threaded build", "reference count", "object header"),
            met="M06",
        ),
        Term(
            name="stop the world",
            short="Parking every other thread so the collector can look at a heap that holds still.",
            long="Removing the GIL did not remove the collector's need for a moment when nothing is changing. A thread running Python gets a bit set on its eval breaker and parks itself between two bytecode instructions. A thread already blocked in C is marked parked where it stands and never woken. The collector waits in one millisecond steps until the last one has stopped.",
            also=("`_PyEval_StopTheWorld`", "`_PY_EVAL_PLEASE_STOP_BIT`"),
            cite="Python/pystate.c:2408-2443@v3.15.0rc1#stop_the_world",
            see=("free threaded build", "cycle collector"),
            met="M08",
        ),
        Term(
            name="mark alive pass",
            short="A first sweep that finds what is obviously reachable so the real pass can skip it.",
            long="It starts from a known root, follows every reference it can reach with tp_traverse, and sets a bit on each object it lands on. The collection proper then ignores anything wearing that bit. This is how a build that walks the whole heap on every pass stays affordable, and it is skipped entirely when gc.freeze has been used because most objects would be skipped anyway.",
            also=("`gc_mark_alive_from_roots`", "`_PyGC_BITS_ALIVE`"),
            cite="Python/gc_free_threading.c:1376-1401@v3.15.0rc1#gc_mark_alive_from_roots",
            see=("cycle collector", "free threaded build"),
            met="M08",
        ),
        Term(
            name="referrer",
            short="An object that points at the one you asked about, as far as tp_traverse can tell.",
            long="`gc.get_referrers` finds them by walking every tracked object in every generation and calling its tp_traverse to see whether your object comes up. That makes it cost a walk of the whole heap, and it makes it blind to anything untracked, so a tuple of plain integers can be holding your object and never appear in the answer.",
            also=("`gc.get_referrers`", "`gc_referrers_for`"),
            cite="Python/gc.c:1665-1684@v3.15.0rc1#gc_referrers_for",
            see=("cycle collector", "reference cycle"),
            met="M09",
        ),
        Term(
            name="DEBUG_SAVEALL",
            short="A debug flag that puts everything a pass would have freed into gc.garbage instead.",
            long="Without it a collection calls tp_clear on each unreachable object and the objects go away, which is what you want and also means you never get to look at them. With it set, delete_garbage appends each one to the garbage list and clears nothing, so after a pass you have the exact set of objects that were only kept alive by each other.",
            also=("`gc.set_debug`", "`gc.garbage`"),
            cite="Python/gc.c:1082-1110@v3.15.0rc1#delete_garbage",
            see=("cycle collector", "reference cycle"),
            met="M09",
        ),
        Term(
            name="permanent generation",
            short="A fourth list the collector keeps and never looks at.",
            long="`gc.freeze()` moves everything currently tracked into it, and nothing comes back out until `gc.unfreeze()`. It exists for servers that load their data and then fork worker processes: the collector writing to an object's header is enough to make the operating system copy that page into every child, so a process that stops walking its old data stops copying it.",
            also=("`gc.freeze`", "`gc.get_freeze_count`"),
            cite="Python/gc.c:1735-1743@v3.15.0rc1#_PyGC_Freeze",
            see=("generation", "cycle collector"),
            met="M07",
        ),
        Term(
            name="collection threshold",
            short="How high a generation's counter has to get before the collector runs.",
            long="The default is 2000 for the youngest and 10 for the two above it. The youngest counts tracked objects that are alive right now, so it goes up when you make one and down when one is freed. The other two count collections of the generation below, so ten passes over the young list is what earns one pass over the middle.",
            also=("`gc.get_threshold`", "`gc.get_count`"),
            cite="Include/internal/pycore_interp_structs.h:271-278@v3.15.0rc1#GC_GENERATION_INIT",
            see=("generation", "cycle collector"),
            met="M07",
        ),
        Term(
            name="immortalization",
            short="Switching an object that is already alive over to the immortal count.",
            long="The runtime does this to the strings it interns for names while a module is being compiled, and to the objects it sets up at startup. There is no way to ask for it from Python, which is deliberate, because there is no way to undo it either. An object that gets the treatment is never freed again for the life of the process.",
            cite="Objects/unicodeobject.c:14196-14214@v3.15.0rc1#immortalize_interned",
            see=("immortal object", "interning", "reference count"),
            met="M05",
        ),
        Term(
            name="single character cache",
            short="The 256 one character strings the runtime builds once before your code runs.",
            long="Every string of one byte comes out of this table rather than being built, which is why slicing or indexing a string of ASCII never allocates. They are immortal, so nothing ever counts references to them, and the table is one of the reasons a program that shuffles short strings around does far less allocation than it looks like it should.",
            also=("`_Py_LATIN1_CHR`",),
            cite="Objects/unicodeobject.c:1809-1814@v3.15.0rc1#get_latin1_char",
            see=("small integer cache", "immortal object", "interning"),
            met="M05",
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
        Term(
            name="GC pre header",
            short="Two words allocated in front of an object, holding its place in the collector's list.",
            long="Only the types the cycle collector tracks get one, and the object's own address points past it, so nothing that reads the header ever sees it. You can still measure it: `sys.getsizeof` adds it and the object's own `__sizeof__` does not, so the gap between those two is exactly this.",
            cite="Include/internal/pycore_interp_structs.h:158-169@v3.15.0rc1#PyGC_Head",
            also=("`PyGC_Head`",),
            see=("cycle collector", "object header"),
            met="O01",
        ),
        Term(
            name="free list",
            short="A small stash of dead objects of one type, kept so the next one can skip the allocator.",
            long="When an object of a type that has one is freed, it is not handed back to the allocator, it is pushed onto a chain of dead objects of exactly that type. The next request pops it off and reuses the memory. The chain is threaded through the objects themselves, using the first word of each dead one to point at the next, so the stash costs nothing beyond a head pointer and a count. There is a cap per type, and the cycle collector empties every one of them, but only when it collects the oldest generation.",
            cite="Include/internal/pycore_freelist.h:52-63@v3.15.0rc1#_PyFreeList_Push",
            see=("obmalloc", "deallocation", "generation"),
            met="O12",
        ),
        Term(
            name="exact type check",
            short="A test that a value is that type and not a subclass of it.",
            long="`PyList_Check` says yes to anything that inherits from `list` and `PyList_CheckExact` says yes only to `list` itself. Fast paths and caches use the exact form, because a subclass can have extra fields, a different size and a different deallocation function, so recycling one as if it were the base type would be wrong. This is why a subclass often quietly loses an optimisation the base type gets.",
            cite="Include/listobject.h:24-26@v3.15.0rc1#PyList_CheckExact",
            see=("free list", "type object", "heap type"),
            met="O12",
        ),
        Term(
            name="weakref offset",
            short="Where in an object the interpreter looks for its list of weak references.",
            long="Every type carries this number and Python shows it as `__weakrefoffset__`. Zero means the type has no room for the pointer, so you cannot take a weak reference to one of its instances, which is why `list` and `int` refuse. Static types put a real field in the struct and get a positive number. A class you write in Python gets minus thirty two instead, because the pointer lives in a pre header allocated in front of the object rather than inside it.",
            cite="Include/internal/pycore_object.h:922-928@v3.15.0rc1#MANAGED_WEAKREF_OFFSET",
            also=("`tp_weaklistoffset`", "`__weakrefoffset__`"),
            see=("weak reference", "GC pre header", "static type"),
            met="O13",
        ),
        Term(
            name="weakref callback",
            short="A function attached to a weak reference, run just after the object dies.",
            long="It is handed the weak reference rather than the object, and by the time it runs every weak reference to that object has already been broken, so calling it gives you `None`. That is deliberate. It means a callback has no way to make the doomed object reachable again. If the callback raises, the exception is reported as unraisable and does not propagate, because there is no caller to propagate it to.",
            cite="Objects/weakrefobject.c:987-999@v3.15.0rc1#handle_callback",
            see=("weak reference", "finalizer", "deallocation"),
            met="O13",
        ),
        Term(
            name="resurrection",
            short="A finalizer storing `self`, which cancels the deallocation that called it.",
            long="`__del__` is handed the object as `self`, and `self` is an ordinary reference, so putting it in a list somewhere makes the object reachable again and the interpreter stops freeing it. This is expected rather than an error. Deallocation bumps the count before calling the finalizer and checks afterwards whether anything else took a reference, and if the object came out of a cycle the collector moves it to the old generation instead of freeing it.",
            cite="Objects/object.c:594-630@v3.15.0rc1#PyObject_CallFinalizerFromDealloc",
            see=("finalizer", "finalized bit", "cycle collector"),
            met="O14",
        ),
        Term(
            name="finalized bit",
            short="One bit on an object saying its finalizer has already been called.",
            long="It is set before the finalizer runs rather than after, which is what guarantees a finalizer is called at most once even if it resurrects the object or raises. `gc.is_finalized` reads it. Setting it first is also why a finalizer that fails halfway is not retried: as far as the interpreter is concerned that object has had its turn.",
            cite="Include/internal/pycore_gc.h:166-181@v3.15.0rc1#_PyGC_SET_FINALIZED",
            also=("`gc.is_finalized`",),
            see=("finalizer", "resurrection"),
            met="O14",
        ),
    ),
)


CONCURRENCY = Group(
    "Threads",
    "The words for what happens when more than one thread wants to run Python at the same time. C01 is about the one big lock, and C02 is about the many small ones that took its place.",
    (
        Term(
            name="GIL",
            short="One lock per interpreter, and you have to be holding it to run Python.",
            long="The struct behind the name is six fields: a boolean saying whether anybody holds it, a mutex and a condition variable to wait on, the number of microseconds a waiting thread stays patient, which thread had it last, and a count of how many times it has changed hands. Everything surprising about threads in CPython comes out of when a running thread is willing to let go of it.",
            cite="Include/internal/pycore_gil.h:22-61@v3.15.0rc1#_gil_runtime_state",
            also=("global interpreter lock",),
            see=("switch interval", "eval breaker", "free threaded build"),
            met="C01",
        ),
        Term(
            name="switch interval",
            short="How long a thread waiting for the GIL waits before it asks for it.",
            long="Five milliseconds by default, readable and writable from Python as `sys.getswitchinterval` and `sys.setswitchinterval`. It is not how often threads take turns and it is not a fairness dial. It is how long a waiter sits on the condition variable before it decides nobody is going to hand the lock over voluntarily and sets the drop request bit.",
            cite="Python/ceval_gil.c:147-153@v3.15.0rc1#DEFAULT_INTERVAL",
            also=("`sys.setswitchinterval`",),
            see=("GIL", "eval breaker"),
            met="C01",
        ),
        Term(
            name="eval breaker",
            short="A word of bits on the thread state that the eval loop checks between instructions.",
            long="Several unrelated things need to interrupt a running thread: a signal arrived, a callback is pending, an async exception is waiting, the collector wants to run, another thread wants the lock. Rather than check five conditions, the eval loop checks one word and only looks at the individual bits when it is not zero. `_PY_GIL_DROP_REQUEST_BIT` is bit zero of it.",
            cite="Include/internal/pycore_ceval.h:345-352@v3.15.0rc1#_PY_GIL_DROP_REQUEST_BIT",
            also=("`tstate->eval_breaker`",),
            see=("GIL", "periodic check"),
            met="C01",
        ),
        Term(
            name="periodic check",
            short="The one place in the eval loop where a thread can be made to give up the GIL.",
            long="Backward jumps and function resumes run a `_CHECK_PERIODIC` instruction, which reads the eval breaker and calls `_Py_HandlePending` if any bit is set. That is the only route from running code to releasing the lock, which is why a single long call into C cannot be interrupted no matter what the switch interval says.",
            cite="Python/ceval_macros.h:520-528@v3.15.0rc1#check_periodics",
            also=("`_CHECK_PERIODIC`",),
            see=("eval breaker", "GIL"),
            met="C01",
        ),
        Term(
            name="race condition",
            short="Two threads touching the same thing, where the answer depends on which got there first.",
            long="The usual shape is a read, a change and a write back, with another thread reading the old value in between. Nothing about it is specific to Python, but on a build with the GIL a great many of them never happen, because the interpreter only hands the lock over at a periodic check and most short sequences do not contain one.",
            cite="Python/ceval_macros.h:520-528@v3.15.0rc1#check_periodics",
            see=("periodic check", "critical section", "per object lock"),
            met="C02",
        ),
        Term(
            name="per object lock",
            short="A one byte mutex sitting in every object header on the free threaded build.",
            long="`PyMutex` uses two bits of one byte: whether it is held, and whether anybody is parked waiting for it. Taking a free one is a single compare and exchange with no system call, which is why it is cheap enough to put one in every object rather than in a table on the side.",
            cite="Include/cpython/pylock.h:12-35@v3.15.0rc1#PyMutex",
            also=("`ob_mutex`", "`PyMutex`"),
            see=("critical section", "free threaded build", "object header"),
            met="C02",
        ),
        Term(
            name="critical section",
            short="A block of C that holds an object's lock, and is allowed to let go of it partway.",
            long="Written as `Py_BEGIN_CRITICAL_SECTION(op)` and `Py_END_CRITICAL_SECTION()`, and compiled to a bare pair of braces on any build that has the GIL. The letting go is the interesting part: an inner section suspends the outer ones rather than nesting inside them, which is what makes deadlock impossible without anybody having to order the locks.",
            cite="Include/critical_section.h:74-90@v3.15.0rc1#Py_BEGIN_CRITICAL_SECTION",
            also=("`Py_BEGIN_CRITICAL_SECTION`",),
            see=("per object lock", "free threaded build"),
            met="C02",
        ),
        Term(
            name="thread state",
            short="The struct the interpreter keeps for one thread, holding everything only that thread has.",
            long="A `PyThreadState` carries the frame the thread is running, the exception it is handling, how much recursion it has left, a scratch dict, the key its `threading.local` values hang off, and its place in the interpreter's list of threads. The operating system thread underneath it knows none of this.",
            cite="Include/cpython/pystate.h:66-101@v3.15.0rc1#_ts",
            also=("`PyThreadState`", "`tstate`"),
            see=("attach and detach", "frame", "daemon thread"),
            met="C03",
        ),
        Term(
            name="attach and detach",
            short="A thread taking hold of its thread state before running Python, and letting go after.",
            long="Attaching sets one int on the thread state and, on a build with the GIL, takes the lock on the way in. Detaching does the reverse and is what `Py_BEGIN_ALLOW_THREADS` expands to, which is why a C function that releases the GIL and a C function that detaches its thread state are the same thing said two ways.",
            cite="Python/pystate.c:2225-2251@v3.15.0rc1#_PyThreadState_Attach",
            also=("`PyEval_SaveThread`", "`PyEval_RestoreThread`"),
            see=("thread state", "GIL", "stop the world"),
            met="C03",
        ),
        Term(
            name="daemon thread",
            short="A thread the interpreter will not wait for, and will hang wherever it stands at exit.",
            long="Shutdown does not ask a daemon thread to stop. It writes one value into that thread's thread state, and the thread carries on until its next periodic check, tries to attach, reads the value and is parked forever. No `finally` block runs and no `with` block exits, which is why a daemon thread should never be the only thing holding a file open.",
            cite="Python/pystate.c:3199-3212@v3.15.0rc1#_PyThreadState_HangThread",
            also=("`daemon=True`",),
            see=("thread state", "attach and detach", "periodic check"),
            met="C03",
        ),
        Term(
            name="interpreter state",
            short="The struct holding one interpreter's modules, its heap, its threads and its lock.",
            long="A `PyInterpreterState` is one level up from a thread state. It owns the list of threads belonging to it, its own `sys.modules`, its own allocator arenas and, since PEP 684, its own GIL. One process can hold several of them, chained newest first off a list hanging on the runtime.",
            cite="Include/internal/pycore_runtime_structs.h:184-201@v3.15.0rc1#pyinterpreters",
            also=("`PyInterpreterState`", "`interp`"),
            see=("subinterpreter", "thread state", "GIL"),
            met="C04",
        ),
        Term(
            name="subinterpreter",
            short="A second interpreter inside the same process, with its own modules and its own lock.",
            long="Made from Python with `concurrent.interpreters.create()` and from C with `Py_NewInterpreterFromConfig`. It shares the process, the address space and the immortal objects, and almost nothing else. Because it has a lock of its own, work running in one is not held up by work running in another.",
            cite="Include/cpython/pylifecycle.h:40-64@v3.15.0rc1#_PyInterpreterConfig_INIT",
            also=("`concurrent.interpreters`", "PEP 734"),
            see=("interpreter state", "GIL", "shareable object"),
            met="C04",
        ),
        Term(
            name="shareable object",
            short="An object the runtime knows how to hand from one interpreter to another.",
            long="Seven types are registered for it: `None`, `int`, `bytes`, `str`, `bool`, `float` and `tuple`. Anything else has to be turned into bytes on the way in and built again on the way out, which means what arrives is a copy, so changing it on one side is invisible on the other.",
            cite="Python/crossinterp_data_lookup.h:790-829@v3.15.0rc1#_register_builtins_for_crossinterpreter_data",
            also=("`is_shareable`", "`concurrent.interpreters.Queue`"),
            see=("subinterpreter", "immortal object"),
            met="C04",
        ),
        Term(
            name="pending call",
            short="A C function left for a thread to run the next time it reaches a periodic check.",
            long="The caller does not run anything. It puts a function pointer on a small ring buffer, sets a bit on the eval breaker, and returns. `Py_AddPendingCall` always leaves the work for the main thread of the main interpreter, which is how a signal arriving on any thread ends up being handled on the one thread that is allowed to handle it.",
            cite="Python/ceval_gil.c:810-825@v3.15.0rc1#Py_AddPendingCall",
            also=("`_PY_CALLS_TO_DO_BIT`", "`_PyEval_AddPendingCall`"),
            see=("eval breaker", "periodic check"),
            met="C05",
        ),
        Term(
            name="asynchronous exception",
            short="An exception set on one thread by another, raised when the target next looks.",
            long="`PyThreadState_SetAsyncExc` finds the thread state with a matching id, stores the exception class on it and sets a bit. The target raises it at its next periodic check, so a thread spinning in Python stops almost at once and a thread inside one long C call carries on until that call returns.",
            cite="Python/pystate.c:2544-2580@v3.15.0rc1#PyThreadState_SetAsyncExc",
            also=("`tstate->async_exc`", "`_PY_ASYNC_EXCEPTION_BIT`"),
            see=("thread state", "periodic check"),
            met="C05",
        ),
        Term(
            name="signal handler",
            short="A Python function the operating system cannot call, so the runtime calls it later.",
            long="The C handler the kernel actually runs does almost nothing: it records which signal arrived and sets a bit on the main thread's eval breaker. The Python function registered with `signal.signal` runs from the periodic check afterwards, always on the main thread of the main interpreter, no matter which thread the operating system delivered the signal to.",
            cite="Modules/signalmodule.c:80-101@v3.15.0rc1#signal",
            also=("`signal.signal`", "`_PyEval_SignalReceived`"),
            see=("eval breaker", "pending call"),
            met="C05",
        ),
        Term(
            name="optimistic read",
            short="Take a reference first, then check that what you took it on has not moved.",
            long="`_Py_TryIncrefCompare` reads a pointer, tries to bump the count on whatever it found, and then reads the pointer a second time. If the two reads disagree the object was replaced underneath it, so it drops the reference and the caller starts again. No lock is taken on the way in, which is why four threads can read the same list at once.",
            cite="Include/internal/pycore_object.h:571-586@v3.15.0rc1#_Py_TryIncrefCompare",
            also=("`_Py_TryIncrefCompare`", "`_Py_TryXGetRef`"),
            see=("critical section", "free threaded build", "reference count"),
            met="C06",
        ),
        Term(
            name="safe memory reclamation",
            short="Freeing memory only once every thread has been seen to move on past it.",
            long="Also written QSBR. A thread that replaces a container's storage cannot free the old block straight away, because another thread may still be reading it. So the block goes on a queue with a sequence number, and the memory is handed back later, once every thread has reached a point where it is certainly no longer looking. The draining happens at the periodic check, which is the same eval breaker C05 was about.",
            cite="Include/internal/pycore_qsbr.h:1-30@v3.15.0rc1#QSBR",
            also=("QSBR", "`_PyMem_FreeDelayed`"),
            see=("optimistic read", "periodic check", "free threaded build"),
            met="C06",
        ),
        Term(
            name="reference count contention",
            short="Several threads writing the same count, which is the slowest thing a CPU does.",
            long="A reference count lives in one cache line, and a core has to own that line exclusively to write to it. Four threads reading the same object therefore take turns on the hardware even though nothing in Python is locked, and the result can be slower than one thread on its own. It is the reason immortal objects exist, and the reason the free threaded build immortalizes every constant it compiles.",
            also=("cache line ping pong",),
            see=("immortal object", "biased reference counting", "free threaded build"),
            met="C06",
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
    CONCURRENCY,
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
