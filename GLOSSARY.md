# Glossary

One definition per term, in one place, so that a lesson can use a word without stopping to explain it and without assuming you remember it from forty lessons ago. Lessons link into this file rather than repeating themselves.

The order below is the order you meet these things, not alphabetical, because reading it straight through is a reasonable thing to do. If you are looking one up, the index is next.

This file is generated from `pyxray/src/pyxray/glossary.py`. Edit that and run `just build-glossary`.

## Index

[ASDL](#asdl) | [Argument Clinic](#argument-clinic) | [C stack](#c-stack) | [C3 linearization](#c3-linearization) | [DISABLE](#disable) | [EXTENDED_ARG](#extended_arg) | [GC pre header](#gc-pre-header) | [JIT](#jit) | [MRO](#mro) | [PEG parser](#peg-parser) | [PyVarObject](#pyvarobject) | [Pyodide](#pyodide) | [WebAssembly](#webassembly) | [abstract interpreter](#abstract-interpreter) | [abstract syntax tree](#abstract-syntax-tree) | [adaptive counter](#adaptive-counter) | [adaptive instruction](#adaptive-instruction) | [arena](#arena) | [assembler](#assembler) | [backtrace](#backtrace) | [basic block](#basic-block) | [binding](#binding) | [block](#block) | [blurb](#blurb) | [borrowed reference](#borrowed-reference) | [bound method](#bound-method) | [bytecode](#bytecode) | [cached hash](#cached-hash) | [cases generator](#cases-generator) | [cell](#cell) | [class cell](#class-cell) | [closure](#closure) | [code generation](#code-generation) | [code object](#code-object) | [code point](#code-point) | [code unit](#code-unit) | [coding cookie](#coding-cookie) | [cold block](#cold-block) | [compact dict](#compact-dict) | [compact int](#compact-int) | [compact string](#compact-string) | [computed goto](#computed-goto) | [configure](#configure) | [constant folding](#constant-folding) | [control flow graph](#control-flow-graph) | [copy and patch](#copy-and-patch) | [cycle collector](#cycle-collector) | [data descriptor](#data-descriptor) | [data stack](#data-stack) | [deallocation](#deallocation) | [debug build](#debug-build) | [deoptimization](#deoptimization) | [descriptor](#descriptor) | [devguide](#devguide) | [digit array](#digit-array) | [dispatch](#dispatch) | [environment changed](#environment-changed) | [eval loop](#eval-loop) | [evaluation order](#evaluation-order) | [exact type check](#exact-type-check) | [exception table](#exception-table) | [executor](#executor) | [f string](#f-string) | [finalized bit](#finalized-bit) | [finalizer](#finalizer) | [frame](#frame) | [frame object](#frame-object) | [free list](#free-list) | [free threaded build](#free-threaded-build) | [free variable](#free-variable) | [gdb](#gdb) | [generated file](#generated-file) | [generation](#generation) | [grammar](#grammar) | [guard](#guard) | [header file](#header-file) | [heap type](#heap-type) | [immortal object](#immortal-object) | [indent and dedent](#indent-and-dedent) | [inline cache](#inline-cache) | [inline values](#inline-values) | [instance dictionary](#instance-dictionary) | [instruction](#instruction) | [instruction DSL](#instruction-dsl) | [instruction pointer](#instruction-pointer) | [instrumented instruction](#instrumented-instruction) | [interning](#interning) | [left recursion](#left-recursion) | [line table](#line-table) | [magic number](#magic-number) | [marshal](#marshal) | [metaclass](#metaclass) | [micro operation](#micro-operation) | [monitoring events](#monitoring-events) | [new reference](#new-reference) | [object](#object) | [object header](#object-header) | [obmalloc](#obmalloc) | [oparg](#oparg) | [opcode](#opcode) | [over allocation](#over-allocation) | [parser generator](#parser-generator) | [pdb](#pdb) | [pointer](#pointer) | [pool](#pool) | [probe sequence](#probe-sequence) | [product type](#product-type) | [profile guided optimization](#profile-guided-optimization) | [pseudo instruction](#pseudo-instruction) | [pyc file](#pyc-file) | [pyconfig](#pyconfig) | [quickening](#quickening) | [reference count](#reference-count) | [reference cycle](#reference-cycle) | [reference leak](#reference-leak) | [regen](#regen) | [regrtest](#regrtest) | [replacement field](#replacement-field) | [resource](#resource) | [resurrection](#resurrection) | [scope](#scope) | [segmentation fault](#segmentation-fault) | [short circuiting](#short-circuiting) | [side exit](#side-exit) | [slot](#slot) | [slot wrapper](#slot-wrapper) | [small int cache](#small-int-cache) | [small integer cache](#small-integer-cache) | [soft keyword](#soft-keyword) | [specialization](#specialization) | [specialization family](#specialization-family) | [split table](#split-table) | [stack depth](#stack-depth) | [stack effect](#stack-effect) | [stack reference](#stack-reference) | [static type](#static-type) | [stencil](#stencil) | [stolen reference](#stolen-reference) | [string kind](#string-kind) | [struct](#struct) | [sum type](#sum-type) | [symbol table](#symbol-table) | [symbol table pass](#symbol-table-pass) | [t string](#t-string) | [tagged integer](#tagged-integer) | [tagged pointer](#tagged-pointer) | [test case](#test-case) | [tier one](#tier-one) | [tier two](#tier-two) | [token](#token) | [tokenizer](#tokenizer) | [tool id](#tool-id) | [trace](#trace) | [trace function](#trace-function) | [traceback](#traceback) | [type object](#type-object) | [underflow](#underflow) | [unwinding](#unwinding) | [value stack](#value-stack) | [varint](#varint) | [watcher](#watcher) | [weak reference](#weak-reference) | [weakref callback](#weakref-callback) | [weakref offset](#weakref-offset) | [zero cost exceptions](#zero-cost-exceptions)

## Reading the source

The words you need before the C stops looking like a foreign language. Z01 and Z02 are the two lessons that cover this ground.

### pointer

**A value holding the address of something rather than the something itself.**

Almost every value in CPython's C is a `PyObject *`, which is the address of an object. The `*` in a declaration means address of one of these, and the `->` means follow the address and take that field. A pointer that is `NULL` is how a C function reports that something went wrong, which is why so much of this code is a call followed immediately by a check for `NULL`.

Also written `PyObject *`. First met in Z01. See also [struct](#struct), [object](#object).

### struct

**A named group of fields laid out one after another in memory.**

Reading CPython is mostly a matter of finding the struct behind a type and seeing what fields it has. The order matters more than it looks: every object starts with the same header fields, and that is exactly what lets a function accept any object at all and still be able to ask what type it is.

First met in Z01. See also [object header](#object-header), [pointer](#pointer). In the source: [`Include/cpython/listobject.h:5-22@v3.15.0rc1#PyListObject`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/cpython/listobject.h#L5-L22).

### header file

**A `.h` file holding the declarations that other files include.**

The split is worth remembering because it saves a lot of searching. If you want to know what a thing is made of, look in `Include/`. If you want to know what happens to it, look in `Objects/` or `Python/`. `Include/internal/` is the half that is not part of the public API, and it is where most of the shapes worth reading actually live.

First met in Z01. See also [struct](#struct).

### generated file

**A source file a script writes at build time rather than a person typing it.**

About a third of the C in CPython is generated, and every one of those files announces itself in its first three lines. Reading one means reading the output of a program instead of the program, which is why it never quite makes sense. The fix is to find the input: `Python/bytecodes.c` for the interpreter, `Grammar/python.gram` for the parser, `Parser/Python.asdl` for the tree.

First met in Z02. See also [grammar](#grammar), [ASDL](#asdl), [bytecode](#bytecode). In the source: [`Python/generated_cases.c.h:1-4@v3.15.0rc1#tier1_generator`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/generated_cases.c.h#L1-L4).

### Argument Clinic

**The tool that writes a C function's argument parsing from a comment above it.**

A block beginning `/*[clinic input]` above a C function declares that function's Python signature, and the parsing code generated from it lands in a `clinic/` directory next to the file. This is why the function you find in `Objects/listobject.c` is called `list_append_impl` rather than `list_append`, and why the part that turned Python arguments into C ones is nowhere near it.

First met in Z02. See also [generated file](#generated-file). In the source: [`Objects/listobject.c:1221-1233@v3.15.0rc1#list_append_impl`](https://github.com/python/cpython/blob/v3.15.0rc1/Objects/listobject.c#L1221-L1233).

### new reference

**A reference the caller now owns and is responsible for releasing.**

Functions whose names contain `New` return one, and so does almost anything that builds an object. If you take a new reference and forget to release it the object never dies, which is a leak, and nothing will tell you. The three kinds of reference are the single most important thing to keep straight while reading this code, because the C does not say which kind it is handing you and the docstring often does not either.

Also written owned reference. First met in Z01. See also [borrowed reference](#borrowed-reference), [stolen reference](#stolen-reference), [reference count](#reference-count). In the source: [`Include/refcount.h:527-538@v3.15.0rc1#Py_NewRef`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/refcount.h#L527-L538).

### borrowed reference

**A reference you may use but do not own, so you must not release it.**

Reading a field out of a struct usually gives you one of these. It is only valid for as long as whatever you borrowed it from stays alive, so borrowing from a list and then modifying the list is the classic way to end up holding an address that no longer means anything.

First met in Z01. See also [new reference](#new-reference), [stolen reference](#stolen-reference).

### stolen reference

**A reference you hand to a function which then owns it instead of you.**

After the call you must not release it and you should not use it either. There are not many of these and they are all documented, but they are the reason you sometimes see `Py_NewRef` wrapped around an argument at a call site: the caller is manufacturing a reference specifically so the callee can take it away.

First met in Z01. See also [new reference](#new-reference), [borrowed reference](#borrowed-reference). In the source: [`Include/internal/pycore_list.h:36-54@v3.15.0rc1#_PyList_AppendTakeRef`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_list.h#L36-L54).

## From text to a tree

The first two stages, which between them turn a file into a shape the rest of the compiler can walk. T02 and T03 are the lessons.

### token

**One piece of the source text with a name attached to it.**

A token is a span of characters and a label, and that is all. The tokenizer does not know what any of it means, so the word `if` comes out as a NAME just like `answer` does, and the thing that decides `if` is a keyword happens later. Some tokens do not exist in the file at all, which is the next entry.

First met in T02. See also [tokenizer](#tokenizer), [indent and dedent](#indent-and-dedent). In the source: [`Parser/lexer/lexer.c:1626-1635@v3.15.0rc1#_PyTokenizer_Get`](https://github.com/python/cpython/blob/v3.15.0rc1/Parser/lexer/lexer.c#L1626-L1635).

### tokenizer

**The part that turns a stream of characters into a stream of tokens.**

It works one character at a time and keeps very little state, which is why it can tell you about an unterminated string but has never heard of a function definition. The one genuinely clever thing in it is the indentation stack, and it is worth reading for that alone.

Also written lexer. First met in T02. See also [token](#token), [indent and dedent](#indent-and-dedent). In the source: [`Parser/lexer/lexer.c:500-530@v3.15.0rc1#tok_get_normal_mode`](https://github.com/python/cpython/blob/v3.15.0rc1/Parser/lexer/lexer.c#L500-L530).

### indent and dedent

**Two tokens the tokenizer invents to mark a change in indentation.**

The tokenizer keeps a stack of column numbers. A line indented further than the top of the stack pushes a new number and emits an INDENT. A line indented less pops until it matches and emits one DEDENT per pop, which is why a single line can produce three of them. Neither token is anything you can point at in the file, which makes indentation errors much easier to understand once you have seen it.

First met in T02. See also [token](#token), [tokenizer](#tokenizer). In the source: [`Parser/lexer/lexer.c:520-530@v3.15.0rc1#ALTTABSIZE`](https://github.com/python/cpython/blob/v3.15.0rc1/Parser/lexer/lexer.c#L520-L530).

### grammar

**The file describing which arrangements of tokens are legal Python.**

`Grammar/python.gram` is 1,645 lines and it is the actual definition of the language, not a description of it: the parser is generated from this file, so if the two ever disagreed the grammar would win by construction. It is readable, and looking up the rule for the thing you are confused about is often faster than reading anything else.

First met in T03. See also [PEG parser](#peg-parser), [generated file](#generated-file). In the source: [`Grammar/python.gram:846-852@v3.15.0rc1#term`](https://github.com/python/cpython/blob/v3.15.0rc1/Grammar/python.gram#L846-L852).

### PEG parser

**The parser CPython generates from the grammar file.**

It reads the tokens left to right and tries the alternatives of a rule in the order they are written, taking the first that fits, which is the part that differs from the older parser and the reason rule order in the grammar is meaningful. It remembers what it has already tried at each position so that backtracking does not become expensive.

First met in T03. See also [grammar](#grammar), [abstract syntax tree](#abstract-syntax-tree). In the source: [`Parser/pegen.c:938-941@v3.15.0rc1#_PyPegen_run_parser`](https://github.com/python/cpython/blob/v3.15.0rc1/Parser/pegen.c#L938-L941).

### abstract syntax tree

**The program as nested nodes, with everything that does not affect meaning dropped.**

The tree keeps the structure and the source positions and throws away the whitespace, the comments, the brackets you wrote for readability, and the difference between one way of spelling something and another. That is what abstract means here. It is the last stage where the program still looks like the program, and everything after it looks like a machine.

Also written AST. First met in T03. See also [ASDL](#asdl), [PEG parser](#peg-parser), [code generation](#code-generation). In the source: [`Lib/ast.py:26-30@v3.15.0rc1#parse`](https://github.com/python/cpython/blob/v3.15.0rc1/Lib/ast.py#L26-L30).

### ASDL

**The small language declaring which node types the tree can contain.**

`Parser/Python.asdl` is 154 lines and every node class in both the C and the Python side is generated from it. This is why `ast.BinOp` knows its own field names and why they are the same in both languages: nobody typed them twice.

First met in T03. See also [abstract syntax tree](#abstract-syntax-tree), [generated file](#generated-file). In the source: [`Parser/Python.asdl:104-105@v3.15.0rc1#operator`](https://github.com/python/cpython/blob/v3.15.0rc1/Parser/Python.asdl#L104-L105).

### coding cookie

**A comment in the first two lines that says what encoding the file is in.**

PEP 263 gave source files a way to declare their own encoding, and the tokenizer looks for it before it looks for anything else. It only means anything when the tokenizer was handed bytes. Hand it a `str` and the encoding question is already settled, so the line is treated as an ordinary comment.

Also written encoding declaration. First met in F01. See also [tokenizer](#tokenizer).

### underflow

**The function the tokenizer calls when it has run out of input and wants another line.**

It is a field on `struct tok_state` rather than a fixed call, which is how one lexer reads from a file, a string, a bytes object or a Python callable without knowing which it got. Each of the four constructors sets it to its own version and then never comes up again.

First met in F01. See also [tokenizer](#tokenizer). In the source: [`Parser/lexer/lexer.c:74-82@v3.15.0rc1`](https://github.com/python/cpython/blob/v3.15.0rc1/Parser/lexer/lexer.c#L74-L82).

### f string

**A string literal with a prefix of f, whose braces hold real expressions.**

Since PEP 701 landed in 3.12 the tokenizer reads one directly rather than grabbing it whole and handing it to a separate parser. That is the reason the old restrictions on quotes, backslashes and comments inside the braces all went away at once: there is no longer a second parser to disagree with the first one.

Also written formatted string literal. First met in F02. See also [replacement field](#replacement-field), [t string](#t-string), [tokenizer](#tokenizer).

### replacement field

**The part of an f-string between a pair of braces, made of an expression and up to three optional pieces.**

After the expression comes an optional equals sign for debugging, an optional conversion after a bang, and an optional format spec after a colon. The lexer has to recognise all four boundaries while it is still scanning characters, which is most of what makes f-string lexing harder than it looks.

First met in F02. See also [f string](#f-string), [t string](#t-string). In the source: [`Grammar/python.gram:971-973@v3.15.0rc1`](https://github.com/python/cpython/blob/v3.15.0rc1/Grammar/python.gram#L971-L973).

### t string

**A template string, written with a t prefix, which hands you its pieces instead of formatting them.**

PEP 750 added these in 3.14 and they reuse the f-string lexer completely. The one difference in the tokenizer is a two value enum saying which kind it is. Because a t-string is meant to be inspected rather than printed, it always keeps the source text of each expression, where an f-string only keeps it after an equals sign.

Also written template string. First met in F02. See also [f string](#f-string), [replacement field](#replacement-field).

### parser generator

**The program that reads the grammar file and writes the parser.**

It lives in `Tools/peg_generator` and is a normal Python package, so it is not part of any installed Python and you cannot import it without a source checkout. It has two back ends. The C one writes `Parser/parser.c` and is what a CPython build runs. The Python one writes a parser you can import, which is what the test suite and anyone experimenting with the grammar uses.

Also written pegen. First met in F03. See also [grammar](#grammar), [PEG parser](#peg-parser), [generated file](#generated-file). In the source: [`Makefile.pre.in:2046-2054@v3.15.0rc1`](https://github.com/python/cpython/blob/v3.15.0rc1/Makefile.pre.in#L2046-L2054).

### soft keyword

**A word that counts as a keyword only in the one place the grammar looks for it.**

The grammar marks these with double quotes rather than single ones, and there are five of them: `_`, `case`, `lazy`, `match` and `type`. The tokenizer knows nothing about any of them, which is why you can still have a variable called `match`. Only a parser willing to try an alternative and back out of it can work this way.

First met in F03. See also [PEG parser](#peg-parser), [grammar](#grammar), [token](#token). In the source: [`Grammar/python.gram:32-34@v3.15.0rc1`](https://github.com/python/cpython/blob/v3.15.0rc1/Grammar/python.gram#L32-L34).

### left recursion

**A rule that names itself as the first thing it matches.**

Read literally this never terminates, so most parser generators refuse it and ask you to rewrite the rule. Pegen accepts it and generates a loop instead: parse the rule without the recursion, then feed the result back in and try again, keeping the longest parse that got longer. That is why `1 - 2 - 3` groups to the left without anybody writing down a precedence table.

First met in F03. See also [grammar](#grammar), [PEG parser](#peg-parser), [parser generator](#parser-generator). In the source: [`Parser/parser.c:14045-14079@v3.15.0rc1#sum_rule`](https://github.com/python/cpython/blob/v3.15.0rc1/Parser/parser.c#L14045-L14079).

### sum type

**A schema type written as a list of alternatives separated by bars.**

Every one of these becomes an abstract base class plus one concrete class per alternative, which is why `isinstance(node, ast.expr)` is a sensible thing to write. Python's whole syntax is two large sums, 29 kinds of expression and 28 kinds of statement, and a handful of small ones for the operators.

First met in F04. See also [ASDL](#asdl), [product type](#product-type), [abstract syntax tree](#abstract-syntax-tree). In the source: [`Parser/Python.asdl:104-105@v3.15.0rc1`](https://github.com/python/cpython/blob/v3.15.0rc1/Parser/Python.asdl#L104-L105).

### product type

**A schema type written as one bracketed list of fields, with no alternatives.**

There is only ever one shape, so it becomes a single class with no base class of its own. Seven of them exist: `arguments`, `arg`, `keyword`, `alias`, `withitem`, `comprehension` and `match_case`. Telling them apart from the sums in Python is a matter of asking which classes have no subclasses.

First met in F04. See also [ASDL](#asdl), [sum type](#sum-type). In the source: [`Parser/Python.asdl:116-117@v3.15.0rc1`](https://github.com/python/cpython/blob/v3.15.0rc1/Parser/Python.asdl#L116-L117).

## Names and where they live

The stage between the tree and the bytecode, which decides what every name in the program is before a single instruction is emitted. T04 is the lesson.

### symbol table

**The table saying what every name in a block is, built before any code is generated.**

This is the answer to the question people usually phrase as when does Python decide. It decides here, at compile time, for the whole block at once, by looking at every binding in it. That is why assigning to a name at the bottom of a function changes how a read of it at the top compiles.

First met in T04. See also [scope](#scope), [binding](#binding), [cell](#cell). In the source: [`Python/symtable.c:415-418@v3.15.0rc1#_PySymtable_Build`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/symtable.c#L415-L418).

### scope

**One block with its own set of names: a module, a function, a class body or a lambda.**

Scopes nest, and a name is resolved by looking outward through the enclosing function scopes. Class bodies are the odd one out and do not participate in that outward walk, which is why a method cannot see a class attribute by bare name. Comprehensions used to be scopes of their own and stopped being so in 3.12.

First met in T04. See also [symbol table](#symbol-table), [closure](#closure). In the source: [`Include/internal/pycore_symtable.h:187-192@v3.15.0rc1#GLOBAL_EXPLICIT`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_symtable.h#L187-L192).

### binding

**Anything in a block that makes a name refer to something.**

An assignment is the obvious one, but so are `def`, `class`, `import`, a `for` target, an `except ... as` name, a `with ... as` name and a function parameter. A name bound anywhere in a function is local to that function everywhere in it, including on the lines above the binding, and that rule alone explains most of the surprising `UnboundLocalError` reports people file.

First met in T04. See also [symbol table](#symbol-table), [scope](#scope). In the source: [`Include/internal/pycore_symtable.h:165-177@v3.15.0rc1#DEF_BOUND`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_symtable.h#L165-L177).

### cell

**A small box holding a variable that an inner function shares with an outer one.**

When a nested function reads a name from the function around it, the value cannot just live in the outer frame, because the outer call may have finished. So the compiler puts it in a cell, the outer function holds the cell rather than the value, and the inner one holds the same cell. Two functions sharing a variable are sharing one of these, which is why `nonlocal` works at all.

First met in T04. See also [closure](#closure), [free variable](#free-variable).

### free variable

**A name a function uses that belongs to a function around it.**

Free here means free of this scope, not free of charge. The compiler lists them in `co_freevars`, and each one is a cell the function was handed when it was created rather than a local it makes for itself.

First met in T04. See also [cell](#cell), [closure](#closure).

### closure

**A function together with the cells it captured from around it.**

The word gets used for the function, for the cells, and for the general idea, and it is usually clear enough from context. The concrete version is `function.__closure__`, which is a tuple of cells, one per name in `co_freevars`, and you can look inside them from Python.

First met in T04. See also [cell](#cell), [free variable](#free-variable), [scope](#scope).

### symbol table pass

**The walk over the tree that decides what every name means, before any code is emitted.**

It runs twice over each block. The first walk only collects what was written down, an assignment here, a parameter there, a `global` statement over there. The second walk turns that into one of five scopes per name. The compiler starts it on its first line and never reasons about scope again afterwards, it just reads the answers.

Also written symtable. First met in F05. See also [symbol table](#symbol-table), [scope](#scope), [code generation](#code-generation). In the source: [`Python/symtable.c:415-416@v3.15.0rc1#_PySymtable_Build`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/symtable.c#L415-L416).

### class cell

**The `__class__` cell a method gets so that a bare `super()` can find its class.**

A method is an ordinary function and has no idea which class it was written in, so the symbol table adds the name for you. Reading the name `super` anywhere in a method body is the whole trigger, which is why a method that reaches the same builtin through the `builtins` module gets no cell and fails at run time.

Also written __classcell__. First met in F05. See also [cell](#cell), [free variable](#free-variable), [symbol table pass](#symbol-table-pass). In the source: [`Python/symtable.c:2651-2657@v3.15.0rc1`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/symtable.c#L2651-L2657).

## Turning a tree into instructions

What the compiler does after it knows what the names are, and the shape of the thing it produces. T05 and T06 are the lessons.

### code generation

**Walking the tree and emitting instructions for each node.**

This stage is mechanical on purpose. It does not try to be clever, it emits a straightforward sequence including jumps to labels, and everything that makes the result smaller or faster happens afterwards on the graph. Separating the two is what keeps `Python/codegen.c` readable.

First met in T05. See also [control flow graph](#control-flow-graph), [abstract syntax tree](#abstract-syntax-tree). In the source: [`Python/codegen.c:894-897@v3.15.0rc1#_PyCodegen_Expression`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/codegen.c#L894-L897).

### short circuiting

**Stopping an `and` or an `or` as soon as the answer is known.**

There is no instruction for either operator. The code generator emits a copy of the left hand value, a test, and a jump past everything after it, so the behaviour is decided at compile time and the interpreter never sees a boolean operator at all. The value you get back is one of the operands rather than True or False, which falls out of the same shape.

First met in F06. See also [code generation](#code-generation), [instruction](#instruction), [dispatch](#dispatch). In the source: [`Python/codegen.c:3387-3413@v3.15.0rc1#codegen_boolop`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/codegen.c#L3387-L3413).

### evaluation order

**Which part of an expression or statement runs first.**

Not a rule written down anywhere separately. It is whatever order the code generator visits a node's children in, so it is readable off a few lines of C. Left before right for an operator, and for an assignment the value before the target, which is why `box[key] = value` runs the value first.

First met in F06. See also [code generation](#code-generation), [abstract syntax tree](#abstract-syntax-tree). In the source: [`Python/codegen.c:3101-3113@v3.15.0rc1`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/codegen.c#L3101-L3113).

### control flow graph

**The emitted instructions as blocks, with the jumps between them as edges.**

This is the form the optimizer works on, because questions like is this code reachable and how deep does the stack get are questions about a graph and are awkward to ask about a flat list. It is turned back into a flat list at the end by the assembler.

Also written CFG. First met in T05. See also [basic block](#basic-block), [assembler](#assembler), [constant folding](#constant-folding). In the source: [`Python/flowgraph.c:3753-3757@v3.15.0rc1#_PyCfg_OptimizeCodeUnit`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/flowgraph.c#L3753-L3757).

### basic block

**A run of instructions with one way in at the top and one way out at the bottom.**

Nothing jumps into the middle of one and nothing branches out of the middle, which is what makes them useful: anything true at the top of a block stays true all the way down it. A jump target always starts a new block.

First met in T05. See also [control flow graph](#control-flow-graph). In the source: [`Python/flowgraph.c:1008-1044@v3.15.0rc1#remove_unreachable`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/flowgraph.c#L1008-L1044).

### cold block

**A block the compiler expects almost never to run, such as an exception handler.**

Marking one costs nothing and buys a tidier layout: every cold block is moved past the end of the function so the code that does run stays packed together, which is why the handler for line 6 turns up after the return on line 8. Where a cold block used to fall off its bottom into a warm one, the pass writes an explicit jump in place of the fallthrough.

First met in F07. See also [basic block](#basic-block), [exception table](#exception-table). In the source: [`Python/flowgraph.c:3492-3506@v3.15.0rc1#push_cold_blocks_to_end`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/flowgraph.c#L3492-L3506).

### stack depth

**How many slots a frame has to reserve for the value stack, worked out at compile time.**

It is the deepest path through the graph rather than the running total down the list, and the difference shows up as soon as there is an exception handler, because a handler starts one deeper than empty. The answer ends up in the code object as `co_stacksize` and the interpreter trusts it completely, so being wrong here is a crash rather than a slowdown.

Also written `co_stacksize`. First met in F07. See also [stack effect](#stack-effect), [control flow graph](#control-flow-graph), [value stack](#value-stack). In the source: [`Python/flowgraph.c:815-824@v3.15.0rc1#calculate_stackdepth`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/flowgraph.c#L815-L824).

### constant folding

**Working an expression out while compiling, so it does not have to be worked out later.**

`6 * 7` becomes 42 in the compiled file and the multiply never reaches the interpreter. It used to happen twice, once on the tree and once on the graph, but the tree pass is gone and all of it now runs on the graph. It stops when the answer would be unreasonably large, so folding a giant power does not make an import take a second and a megabyte. The old operand often stays behind in the constants with nothing loading it, which is a good thing to notice.

First met in T05. See also [control flow graph](#control-flow-graph), [code object](#code-object). In the source: [`Python/flowgraph.c:1916-1948@v3.15.0rc1#fold_const_binop`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/flowgraph.c#L1916-L1948).

### pseudo instruction

**An instruction that exists inside the compiler and never reaches a code object.**

Things like `JUMP` without a resolved target, or the markers used to build the exception table. They are real entries in the opcode table with numbers above the real instructions, and they are all gone by the time the assembler is finished, so seeing one in a disassembly would mean something had gone badly wrong.

First met in T05. See also [assembler](#assembler), [opcode](#opcode). In the source: [`Include/opcode_ids.h:247-257@v3.15.0rc1#ANNOTATIONS_PLACEHOLDER`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/opcode_ids.h#L247-L257).

### assembler

**The stage that flattens the finished graph into the bytes of a code object.**

It lays the blocks out in order, turns label references into offsets, works out how deep the value stack gets, builds the line table and the exception table, and hands back the finished object. By the time it runs every decision has been made, so it is the least interesting stage and the one you are most grateful for when reading a disassembly.

First met in T05. See also [code object](#code-object), [control flow graph](#control-flow-graph), [exception table](#exception-table). In the source: [`Python/assemble.c:779-802@v3.15.0rc1#_PyAssemble_MakeCodeObject`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/assemble.c#L779-L802).

### code object

**The compiled form of one module, function, class body or comprehension.**

It holds the bytecode, the constants, the names, the local variable names, the line table, the exception table and the stack size, and it holds no values: a code object for a function is the same whether the function has been called once or a million times. Nested definitions produce their own code objects which sit in the outer one's constants, so a module's code object contains its functions the way a box contains boxes.

Also written `co_*`. First met in T05. See also [bytecode](#bytecode), [frame](#frame), [assembler](#assembler). In the source: [`Objects/codeobject.c:715-718@v3.15.0rc1#_PyCode_New`](https://github.com/python/cpython/blob/v3.15.0rc1/Objects/codeobject.c#L715-L718).

### bytecode

**The instruction stream inside a code object.**

It is a sequence of two byte units, one opcode and one argument each, plus the cache slots belonging to the instruction before. It is an implementation detail with no compatibility promise and it changes every release, which is exactly why reading it teaches you about this interpreter rather than about Python.

First met in T05. See also [instruction](#instruction), [code object](#code-object), [inline cache](#inline-cache). In the source: [`Include/internal/pycore_structs.h:17-32@v3.15.0rc1#_Py_CODEUNIT`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_structs.h#L17-L32).

### instruction

**One opcode and one argument byte, two bytes together.**

Everything is exactly two bytes, which is why an instruction that needs a bigger argument has to be preceded by extra instructions rather than growing. Any cache slots belonging to an instruction follow it and are skipped over rather than executed.

First met in T06. See also [code unit](#code-unit), [opcode](#opcode), [oparg](#oparg), [inline cache](#inline-cache).

### opcode

**The number in the first byte, saying which instruction this is.**

`dis` prints the name, and the names and numbers both come out of a table generated from `Python/bytecodes.c`, so asking Python for them is asking the same file the interpreter was compiled from. Numbers move between releases and are not worth memorising.

First met in T06. See also [instruction](#instruction), [oparg](#oparg), [generated file](#generated-file).

### oparg

**The second byte, whose meaning is different for every instruction.**

This is the single biggest source of confusion when reading a disassembly. In `LOAD_CONST 1` it indexes the constants, in `LOAD_FAST 1` it indexes the locals, in `CALL 1` it counts arguments and in a jump it counts instructions. The number 1 in those four lines has nothing in common beyond being the number 1.

Also written argument. First met in T06. See also [instruction](#instruction), [opcode](#opcode), [EXTENDED_ARG](#extended_arg).

### EXTENDED_ARG

**An instruction that supplies the high bits of the argument of the next one.**

One byte only reaches 255, so a function with more than 256 constants needs a way to say so. Up to three of these can stack up in front of an instruction, each shifting what came before left by eight. `dis` folds them into the number it prints, so you see the real argument and have to remember that the offsets moved.

First met in T06. See also [oparg](#oparg), [instruction](#instruction). In the source: [`Python/bytecodes.c:6092-6098@v3.15.0rc1#EXTENDED_ARG`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/bytecodes.c#L6092-L6098).

### inline cache

**Spare slots after an instruction where it writes down what happened last time.**

They sit in the bytecode as if they were instructions and are stepped over rather than run. This is where a specialized instruction keeps the type it saw and whatever it worked out from it, which is why the number of slots is fixed per instruction family and why offsets in a disassembly jump by more than two.

First met in T06. See also [specialization](#specialization), [instruction](#instruction), [bytecode](#bytecode).

### exception table

**A side table saying, for each range of instructions, where to jump if something raises.**

There are no instructions marking the start or end of a `try`. The compiler records ranges instead, and entering a `try` costs nothing at all at run time because there is nothing to execute. The number of entries rarely matches the number of keywords you wrote, since a `finally` has to appear once for the normal path and again for the raising one.

First met in T06. See also [code object](#code-object), [assembler](#assembler). In the source: [`InternalDocs/exception_handling.md:80-95@v3.15.0rc1#exception`](https://github.com/python/cpython/blob/v3.15.0rc1/InternalDocs/exception_handling.md#L80-L95).

### line table

**A side table mapping instruction offsets back to positions in the source.**

It is compressed rather than being one entry per instruction, and it carries columns as well as lines, which is what lets a traceback underline the exact subexpression that failed. `code.co_positions()` unpacks it for you.

Also written `co_linetable`. First met in T06. See also [code object](#code-object).

### marshal

**The format a code object is written in when it goes to disk.**

One byte says what an object is, and whatever that kind of object needs follows it. The low seven bits of that byte are an ascii letter, which is why a `.pyc` in a hex dump is half readable, and the top bit means the object is worth numbering so that something later can point at it instead of repeating it. It is not a general purpose serialisation format and is not safe to point at untrusted bytes.

First met in F12. See also [code object](#code-object), [pyc file](#pyc-file). In the source: [`Python/marshal.c:460-495@v3.15.0rc1#w_object`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/marshal.c#L460-L495).

### pyc file

**A sixteen byte header and one marshalled code object.**

The header is a magic number, a flags word, and the source file's modification time and length. The last two are what makes a `.pyc` go stale: if either does not match the source, the file is thrown away and the source is compiled again. Everything after byte sixteen is one code object, with the code objects for every function in the file sitting in its constants.

Also written `__pycache__`. First met in F12. See also [marshal](#marshal), [magic number](#magic-number), [code object](#code-object). In the source: [`Lib/importlib/_bootstrap_external.py:413-444@v3.15.0rc1#_classify_pyc`](https://github.com/python/cpython/blob/v3.15.0rc1/Lib/importlib/_bootstrap_external.py#L413-L444).

### magic number

**The four bytes at the front of a pyc that say which Python wrote it.**

Only the first two are the number, and it goes up whenever the bytecode changes, which is what stops a `.pyc` from one release being loaded by another. The other two bytes are a carriage return and a newline, put there so that anything copying the file in text mode corrupts those two bytes and fails the check loudly rather than loading something strange.

First met in F12. See also [pyc file](#pyc-file). In the source: [`Include/internal/pycore_magic_number.h:313-318@v3.15.0rc1#PYC_MAGIC_NUMBER_TOKEN`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_magic_number.h#L313-L318).

## Running the instructions

The interpreter itself, and the machinery it uses to go faster than it looks like it should. T07 is the lesson, and parts three and four go further.

### frame

**The working space for one call: its locals, its value stack and where it was up to.**

A frame is created per call, not per function, so a function called twice has two of them. Most of the time the interpreter allocates them in a contiguous chunk it manages itself rather than as ordinary objects, and the `frame` object you get from `sys._getframe` is a view onto that rather than the thing itself. A generator is the case where a frame outlives the call that made it.

First met in T07. See also [value stack](#value-stack), [code object](#code-object), [eval loop](#eval-loop). In the source: [`Include/internal/pycore_interpframe_structs.h:29-53@v3.15.0rc1#_PyInterpreterFrame`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_interpframe_structs.h#L29-L53).

### value stack

**Where an instruction leaves its results for the next instruction to pick up.**

Nearly every instruction is described entirely by what it takes off the top and what it puts back, and reading a disassembly fluently is mostly a matter of tracking that. It lives inside the frame and its maximum depth is worked out at compile time and stored in the code object, so the space is reserved once when the frame is made.

Also written stack. First met in T06. See also [frame](#frame), [stack effect](#stack-effect).

### stack effect

**How many values an instruction takes off the stack and how many it leaves.**

The numbers come from a table generated from `Python/bytecodes.c`, so they cannot drift from what the instructions actually do. Walking the graph and adding these up is how the compiler works out the stack size, and doing the same by hand down a listing is how you check that you have read it correctly.

First met in T06. See also [value stack](#value-stack), [instruction](#instruction). In the source: [`Include/internal/pycore_opcode_metadata.h:35-38@v3.15.0rc1#_PyOpcode_num_popped`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_opcode_metadata.h#L35-L38).

### eval loop

**The loop that fetches the next instruction and does it.**

It is one very large function, and most of its body is generated from `Python/bytecodes.c` rather than typed, so the file to read is the input rather than the loop. It is worth knowing that the loop is also where a call to a Python function is handled without recursing into C, which is why deep Python recursion is fine and deep recursion through C is not.

Also written `_PyEval_EvalFrameDefault`, ceval. First met in T07. See also [dispatch](#dispatch), [frame](#frame), [generated file](#generated-file). In the source: [`Python/ceval.c:1212-1218@v3.15.0rc1#_PyEval_EvalFrameDefault`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/ceval.c#L1212-L1218).

### dispatch

**Getting from the end of one instruction to the start of the right next one.**

This happens more often than anything else in the interpreter, so it gets more attention than its two lines of code would suggest. The plain version is going back to the top of a loop with a switch in it, and the faster version gives each instruction its own jump.

First met in T07. See also [computed goto](#computed-goto), [eval loop](#eval-loop). In the source: [`Python/ceval_macros.h:198-206@v3.15.0rc1#DISPATCH`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/ceval_macros.h#L198-L206).

### computed goto

**A compiler extension letting each instruction jump straight to the next one.**

Instead of every instruction returning to one shared switch, each ends with a jump through a table of labels. The reason it is faster is not the jump itself but the branch predictor: one shared switch is one branch the processor keeps guessing wrong, while a per instruction jump gives it many branches each with its own pattern to learn.

First met in T07. See also [dispatch](#dispatch). In the source: [`Python/ceval_macros.h:128-141@v3.15.0rc1#DISPATCH_GOTO`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/ceval_macros.h#L128-L141).

### specialization

**Swapping an instruction for a narrower one that assumes what it saw last time.**

`BINARY_OP` on two ints becomes `BINARY_OP_MULTIPLY_INT`, which skips every check about what the operands might have been. It happens while the program runs, per instruction rather than per function, and it needs only a handful of executions, so a single call to a function with a loop in it is usually enough to see it happen.

First met in T07. See also [adaptive instruction](#adaptive-instruction), [deoptimization](#deoptimization), [inline cache](#inline-cache). In the source: [`Python/bytecodes.c:657-670@v3.15.0rc1#_BINARY_OP_MULTIPLY_INT`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/bytecodes.c#L657-L670).

### adaptive instruction

**The general instruction that watches what happens and then specializes itself.**

It counts down while it watches, and when the counter runs out it writes a narrower instruction over itself. The counter and the notes it takes live in the inline cache slots following it, which is why every instruction that can specialize has some.

First met in T07. See also [specialization](#specialization), [inline cache](#inline-cache).

### deoptimization

**Going back to the general instruction when the assumption stops being true.**

A specialized instruction starts with a guard, and if the guard fails it hands control back to the general form rather than being wrong. This is what makes the whole scheme safe: the fast path never has to be right, it only has to notice when it is not.

First met in T07. See also [specialization](#specialization), [adaptive instruction](#adaptive-instruction).

### tier one

**The ordinary interpreter, the one that runs the bytecode in the code object.**

This is what runs everything, and for most programs it is the only thing that runs. The name only exists because there is now a second tier, and it is worth using because a sentence about the interpreter is ambiguous once there are two of them.

First met in T07. See also [tier two](#tier-two), [eval loop](#eval-loop).

### tier two

**A second interpreter that runs traces of smaller operations, feeding the JIT.**

When a loop gets hot enough, the bytecode inside it is projected into a straight line of much smaller operations, with the branches turned into guards that bail out to tier one. That straight line is what the JIT compiles, and it is also runnable on its own, which is what makes it possible to debug.

Also written uop, micro operation. First met in T07. See also [tier one](#tier-one), [JIT](#jit), [deoptimization](#deoptimization).

### JIT

**The part that turns a hot trace into machine code at run time.**

It is off unless the interpreter was built with it turned on, so the first thing to do with any claim about it is check whether it is running on your build. It compiles tier two traces rather than bytecode, which is why the tier two operations exist at all.

First met in T07. See also [tier two](#tier-two).

### instruction DSL

**The small language that `Python/bytecodes.c` is written in.**

It looks like C and is not. Each definition opens with a line saying what kind of thing it is, what it is called, and what it takes off the stack and leaves behind, and only the body after that is ordinary C. That first line is what lets one file produce the eval loop, the stack effect tables, the cache sizes and the opcode numbers, because all of it is stated once in a form a program can read.

Also written the DSL, `bytecodes.c`. First met in E01. See also [cases generator](#cases-generator), [generated file](#generated-file), [stack effect](#stack-effect), [eval loop](#eval-loop). In the source: [`Python/bytecodes.c:1-7@v3.15.0rc1`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/bytecodes.c#L1-L7).

### cases generator

**The set of scripts under `Tools/cases_generator` that read the DSL and write C.**

There is a shared parser and then one script per output file, so adding an instruction means editing one definition and running `make regen-all`. Every file it writes opens with the same four line banner naming the script and the input and ending in `Do not edit!`, which is the quickest way to tell a generated file from a written one.

First met in E01. See also [instruction DSL](#instruction-dsl), [generated file](#generated-file), [regen](#regen). In the source: [`Tools/cases_generator/generators_common.py:66-75@v3.15.0rc1#write_header`](https://github.com/python/cpython/blob/v3.15.0rc1/Tools/cases_generator/generators_common.py#L66-L75).

### specialization family

**A base opcode and the faster versions it can turn into, declared as a group.**

The declaration is one line in the DSL naming the base instruction, its cache size and its members. Everything downstream comes from that: the table mapping a specialized opcode back to its base, the `_specializations` dict in `_opcode_metadata`, and the checks that every member has the same stack effect and cache layout as the base. There is no separate list to keep in step.

Also written `family`. First met in E01. See also [specialization](#specialization), [adaptive instruction](#adaptive-instruction), [inline cache](#inline-cache), [instruction DSL](#instruction-dsl). In the source: [`Python/bytecodes.c:484-491@v3.15.0rc1#family`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/bytecodes.c#L484-L491).

### code unit

**The sixteen bits an instruction occupies, which are not always an instruction.**

It is a union of three readings of the same word: two bytes for an opcode and its argument, one whole word used as a cache slot, and a counter the specializer counts down. Nothing in the word says which reading applies, so the only way to know is to have walked the stream from the start and kept track of how many cache slots each instruction claims.

Also written `_Py_CODEUNIT`. First met in E02. See also [instruction](#instruction), [inline cache](#inline-cache), [instruction pointer](#instruction-pointer), [bytecode](#bytecode). In the source: [`Include/internal/pycore_structs.h:25-32@v3.15.0rc1`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_structs.h#L25-L32).

### instruction pointer

**The interpreter's place in the instruction stream, kept in a local C variable.**

It is called `next_instr`, and it is already pointing past the current instruction while that instruction runs. Everything moves it: fetching advances it by one word, a cache carrying instruction skips over its own slots, and a jump adds a signed count of words. Because it lives in a register rather than in the frame, anything that needs the real position, like a traceback, has to write it back first.

Also written `next_instr`. First met in E02. See also [code unit](#code-unit), [dispatch](#dispatch), [eval loop](#eval-loop), [frame](#frame). In the source: [`Python/ceval_macros.h:249-254@v3.15.0rc1#next_instr`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/ceval_macros.h#L249-L254).

### data stack

**The memory the interpreter allocates frames from, which is not the C stack.**

It is a linked list of chunks, sixteen kilobytes each by default, owned by the thread state. Calling a Python function takes the next few slots off the top, and returning hands them straight back, so a call is a pointer bump rather than an allocation. This is the reason a hundred thousand deep Python recursion works while the same depth routed through a C function does not.

Also written datastack. First met in E03. See also [frame](#frame), [frame object](#frame-object), [C stack](#c-stack). In the source: [`Python/pystate.c:3133-3143@v3.15.0rc1#_PyThreadState_PushFrame`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/pystate.c#L3133-L3143).

### frame object

**The Python level `frame` you can hold, which is not the frame the interpreter uses.**

The interpreter runs on a bare struct with no reference count and no type. The `frame` object is made only when something asks for one, which `sys._getframe`, a traceback and any debugger all do. Once made it is cached on the interpreter frame, so asking twice gives the same object, and if the call returns while somebody still holds it the object takes ownership of the contents rather than leaving a dangling view.

Also written `PyFrameObject`. First met in E03. See also [frame](#frame), [data stack](#data-stack), [trace function](#trace-function). In the source: [`Include/internal/pycore_interpframe_structs.h:36-36@v3.15.0rc1#frame_obj`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_interpframe_structs.h#L36).

### C stack

**The machine stack the thread actually runs on, with a size fixed when it starts.**

Python calls do not use it, but any call that goes out through C and back into Python does, and each one of those costs somewhere between hundreds of bytes and several kilobytes. CPython checks how much room is left rather than counting calls, which is why the resulting `RecursionError` says how many kilobytes were used instead of what the limit was.

First met in E03. See also [data stack](#data-stack), [frame](#frame), [eval loop](#eval-loop).

### stack reference

**What a frame slot holds, which is a pointer with the bottom bits used for something.**

Every slot in a frame, both the locals and the value stack, holds one of these rather than a plain object pointer. The bottom two bits say whether the slot owns a counted reference, is only borrowing one, or is not holding a pointer at all. Everything that used to be an unconditional increment or decrement is now a test on those two bits first.

Also written `_PyStackRef`. First met in E04. See also [tagged pointer](#tagged-pointer), [borrowed reference](#borrowed-reference), [reference count](#reference-count), [frame](#frame). In the source: [`Include/internal/pycore_stackref.h:533-537@v3.15.0rc1#PyStackRef_Borrow`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_stackref.h#L533-L537).

### tagged pointer

**A pointer with extra information hidden in the bits that are always zero.**

Objects are aligned in memory, so the bottom two bits of any object pointer are zero and can be used to carry a flag. CPython uses one of them to mean this reference was not counted, so releasing it should do nothing. The flag that marks an object immortal is deliberately the same bit value, which is why building the tagged reference is a single AND with no branch.

First met in E04. See also [stack reference](#stack-reference), [immortal object](#immortal-object), [pointer](#pointer). In the source: [`Include/internal/pycore_stackref.h:53-58@v3.15.0rc1#Py_TAG_REFCNT`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_stackref.h#L53-L58).

### tagged integer

**A small number living in a stack slot with no object anywhere.**

The bottom bits can also say that the rest of the word is not a pointer but a number shifted up by two. From 3.15 the interpreter uses this for the position a `for` loop has reached in a list or a tuple, so the counter sits on the value stack with nothing allocated for it. It is why a loop over a list needs one more stack slot in 3.15 than it did in 3.14.

First met in E04. See also [stack reference](#stack-reference), [tagged pointer](#tagged-pointer), [value stack](#value-stack). In the source: [`Include/internal/pycore_stackref.h:432-438@v3.15.0rc1#PyStackRef_TagInt`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_stackref.h#L432-L438).

### zero cost exceptions

**Entering a try block runs no instructions, so it costs nothing until something raises.**

Older CPython pushed a block onto a stack when a try started and popped it when the try ended, which meant every guarded region paid on the way in and on the way out whether or not anything went wrong. Since 3.11 the compiler writes the same information into a table on the side of the code object instead, and the interpreter only reads that table when an exception is already in flight. Raising got a little more expensive and not raising got free.

First met in E05. See also [exception table](#exception-table), [unwinding](#unwinding), [pseudo instruction](#pseudo-instruction). In the source: [`InternalDocs/exception_handling.md:48-53@v3.15.0rc1#metadata`](https://github.com/python/cpython/blob/v3.15.0rc1/InternalDocs/exception_handling.md#L48-L53).

### unwinding

**Walking back out through frames looking for something that will catch the exception.**

When an instruction raises, the interpreter looks the current offset up in the exception table of the code object it is running. If there is a handler it trims the value stack to the depth the table recorded and jumps there. If there is not, it adds the frame to the traceback, drops it, and asks the same question of the caller, all the way up until something catches or the top is reached.

First met in E05. See also [exception table](#exception-table), [traceback](#traceback), [frame](#frame), [zero cost exceptions](#zero-cost-exceptions). In the source: [`Python/bytecodes.c:6519-6558@v3.15.0rc1#exception_unwind`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/bytecodes.c#L6519-L6558).

### traceback

**The chain of frames an exception passed through, built one link at a time as it unwinds.**

It is not captured at the point of the raise. Each frame the exception leaves adds itself to the front of the chain on the way past, which is why the cost of raising grows with how far the exception has to travel and why the printed report reads from the outermost call inwards. Every link records the offset in that frame's bytecode, so the report can point at the exact instruction.

Also written `__traceback__`. First met in E05. See also [unwinding](#unwinding), [frame object](#frame-object), [line table](#line-table). In the source: [`Python/bytecodes.c:6509-6514@v3.15.0rc1#PyTraceBack_Here`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/bytecodes.c#L6509-L6514).

### varint

**A number written in as many bytes as it needs, six bits at a time.**

Both the exception table and the line table use it, because most of the numbers in them are small and a fixed width field would waste space on every entry. Six bits of each byte carry data, one says whether another byte follows, and in the exception table the top bit is reserved to mark the first byte of an entry, which is what makes a binary search over variable sized entries possible.

First met in E05. See also [exception table](#exception-table), [line table](#line-table), [assembler](#assembler). In the source: [`Python/assemble.c:157-188@v3.15.0rc1#assemble_exception_table`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/assemble.c#L157-L188).

### adaptive counter

**Two bytes of cache saying how much longer to wait before rewriting this instruction.**

It sits in the first cache slot after an instruction that can specialize, and it is a number packed together with a backoff exponent. A cold instruction starts at one, so the second execution triggers a specialization attempt. Once specialized it is reset to fifty two, so it takes fifty three failures before the instruction gives up and tries something else. Both numbers are named constants you can read.

First met in E06. See also [adaptive instruction](#adaptive-instruction), [inline cache](#inline-cache), [specialization](#specialization), [deoptimization](#deoptimization). In the source: [`Include/internal/pycore_code.h:450-464@v3.15.0rc1#ADAPTIVE_WARMUP_VALUE`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_code.h#L450-L464).

### guard

**The check at the top of a specialized instruction that says whether it may run.**

`BINARY_OP_ADD_INT` is really two type checks followed by an addition that skips every other question. If a check fails the instruction bails out to the general form instead of being wrong, which is why specializing is safe: the fast path never has to be correct in general, it only has to notice when it does not apply.

First met in E06. See also [specialization](#specialization), [deoptimization](#deoptimization), [adaptive instruction](#adaptive-instruction). In the source: [`Python/bytecodes.c:635-643@v3.15.0rc1#_GUARD_TOS_INT`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/bytecodes.c#L635-L643).

### quickening

**Taking a private copy of the bytecode so it can be rewritten without touching the original.**

`co_code` is what the compiler produced and never changes. The interpreter runs a separate copy, reachable as `_co_code_adaptive`, and that copy is what specialized instructions get written into. It is why disassembling a function gives one answer by default and a different one with `adaptive=True`, and why marshalling a warmed up function to a `.pyc` file still writes the cold version.

First met in E06. See also [specialization](#specialization), [code object](#code-object), [bytecode](#bytecode), [inline cache](#inline-cache). In the source: [`Python/specialize.c:63-70@v3.15.0rc1#_PyCode_Quicken`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/specialize.c#L63-L70).

### micro operation

**One of the small pieces a bytecode instruction is broken into for tier two.**

A single instruction like `BINARY_OP_ADD_INT` is really a guard, another guard and an addition, and in tier two those become three separate operations rather than one. Splitting them up is what lets the optimizer notice that the second copy of a guard cannot fail and delete it, which is not something you can do while the three are welded together.

Also written uop. First met in E07. See also [tier two](#tier-two), [trace](#trace), [executor](#executor), [guard](#guard). In the source: [`Python/bytecodes.c:672-685@v3.15.0rc1#_BINARY_OP_ADD_INT`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/bytecodes.c#L672-L685).

### trace

**A straight line of micro operations recorded from one actual trip through a hot loop.**

The recorder follows what the program really did, so a branch does not become two paths. It becomes whichever path was taken, plus a guard that bails out to the ordinary interpreter if the other one happens next time. That is why a trace can be optimized like straight line code even though the source it came from is full of branching.

First met in E07. See also [micro operation](#micro-operation), [executor](#executor), [side exit](#side-exit), [tier two](#tier-two). In the source: [`InternalDocs/jit.md:37-48@v3.15.0rc1`](https://github.com/python/cpython/blob/v3.15.0rc1/InternalDocs/jit.md#L37-L48).

### executor

**The object holding one optimized trace, attached to the code object it came from.**

It is a real Python object you can fetch with `_opcode.get_executor` and iterate over, which is unusual for something this deep in the machinery. Each item is one micro operation with its argument and its jump target, so an executor is readable in the same way a code object is.

First met in E07. See also [trace](#trace), [micro operation](#micro-operation), [JIT](#jit), [code object](#code-object). In the source: [`Python/optimizer.c:124-140@v3.15.0rc1#_PyOptimizer_Optimize`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/optimizer.c#L124-L140).

### side exit

**The point where a guard in a trace fails and control goes back to the ordinary interpreter.**

Every guard in a trace has one, which is why a trace of twenty three operations can be forty one operations long: the extra ones are the cold tails nobody runs unless a guess turns out wrong. A side exit that keeps getting taken can itself get hot and grow a trace of its own.

First met in E07. See also [trace](#trace), [guard](#guard), [deoptimization](#deoptimization), [executor](#executor). In the source: [`Python/bytecodes.c:6183-6196@v3.15.0rc1#_EXIT_TRACE`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/bytecodes.c#L6183-L6196).

### instrumented instruction

**An opcode swapped into the bytecode so that running it also calls a tool back.**

Every instruction a monitoring tool can be told about has a paired form whose name starts with `INSTRUMENTED_`. Switching an event on writes those paired forms over the ordinary ones, and switching it off writes the ordinary ones back, so a function you are not watching runs exactly the bytecode it always did. It is the same trick as specialization pointed the other way: rewrite the instruction rather than test a flag inside it.

First met in E08. See also [monitoring events](#monitoring-events), [tool id](#tool-id), [specialization](#specialization), [bytecode](#bytecode). In the source: [`Python/instrumentation.c:757-784@v3.15.0rc1#instrument`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/instrumentation.c#L757-L784).

### tool id

**One of the numbered slots a monitoring tool claims before it can ask for events.**

There are eight in the C code and six you can use, because the last two are held for `sys.settrace` and `sys.setprofile`. Claiming one is how a debugger and a coverage tool stay out of each other's way: each registers its own callbacks and asks for its own events, and the interpreter keeps a separate set of them per slot rather than one hook everybody has to share.

Also written `sys.monitoring.use_tool_id`. First met in E08. See also [monitoring events](#monitoring-events), [instrumented instruction](#instrumented-instruction), [trace function](#trace-function). In the source: [`Include/internal/pycore_instruments.h:71-77@v3.15.0rc1#PY_MONITORING_TOOL_IDS`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_instruments.h#L71-L77).

### DISABLE

**What a monitoring callback returns to stop being called at that one place.**

Returning it does not switch the event off everywhere. It removes the instrumentation from the single instruction that fired, so the rest of the program keeps reporting and that one line goes back to full speed. This is what makes a coverage tool cheap: it only ever needs to be told about a line once, so almost every line disables itself on its first execution and the loop around it runs as if nothing were watching.

Also written `sys.monitoring.DISABLE`. First met in E08. See also [monitoring events](#monitoring-events), [instrumented instruction](#instrumented-instruction), [tool id](#tool-id). In the source: [`Python/instrumentation.c:971-994@v3.15.0rc1#call_one_instrument`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/instrumentation.c#L971-L994).

### abstract interpreter

**The pass that walks a trace holding a description of each value instead of the value.**

It steps through the recorded micro operations the way the interpreter would, but its stack holds notes like `this is an int` or `this is exactly that object` rather than real objects. Nothing runs, so nothing can be observed, and the only thing it produces is a shorter list of operations. Every deletion tier two makes comes out of one of those notes being specific enough to answer a question the trace was about to ask.

First met in E09. See also [trace](#trace), [micro operation](#micro-operation), [guard](#guard), [tier two](#tier-two). In the source: [`Python/optimizer_analysis.c:803-829@v3.15.0rc1#_Py_uop_analyze_and_optimize`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/optimizer_analysis.c#L803-L829).

### watcher

**A callback the runtime fires when a dictionary or a type is modified.**

It is how the optimizer is allowed to assume things. A trace that baked in the value of a global asks to be told if that module dictionary ever changes, and a trace that checked a type asks to be told if that type is patched. When the callback fires it throws away every executor that depended on the thing, so monkeypatching still works and simply costs you the optimized code. You can see the result from Python, because the executor's `is_valid` flips to False.

First met in E09. See also [executor](#executor), [abstract interpreter](#abstract-interpreter), [trace](#trace), [deoptimization](#deoptimization). In the source: [`Python/optimizer_analysis.c:140-158@v3.15.0rc1#globals_watcher_callback`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/optimizer_analysis.c#L140-L158).

### stencil

**A chunk of machine code for one micro operation, compiled when CPython was built.**

The build writes a tiny C file for each micro operation, containing that one operation and nothing else, and compiles it. What comes out is a run of finished instructions with a few blanks in it where addresses have to go. Nothing about your program is in there, which is exactly why it could be made months before your program existed.

First met in E10. See also [copy and patch](#copy-and-patch), [micro operation](#micro-operation), [JIT](#jit), [generated file](#generated-file). In the source: [`Tools/jit/template.c:123-133@v3.15.0rc1#_JIT_ENTRY`](https://github.com/python/cpython/blob/v3.15.0rc1/Tools/jit/template.c#L123-L133).

### copy and patch

**Building machine code by pasting prebuilt chunks together and filling in the blanks.**

It is how CPython's JIT works and why it is fast enough to run while your program is waiting. For each micro operation in a trace it copies the chunk that was compiled at build time, then writes the addresses that only exist now into the blanks that chunk was left with. There is no instruction selection and no register allocation, so the size of the output is known before any of it is written.

Also written copy-and-patch. First met in E10. See also [stencil](#stencil), [JIT](#jit), [executor](#executor), [trace](#trace). In the source: [`InternalDocs/jit.md:123-138@v3.15.0rc1`](https://github.com/python/cpython/blob/v3.15.0rc1/InternalDocs/jit.md#L123-L138).

## Objects

What every value in Python actually is, and the few fields they all share. T08 is the lesson.

### object

**Anything Python can name, which is everything, including types and functions.**

Every value is a block of memory beginning with the same two fields, and every Python level operation on it goes through its type. There is no separate category of primitive values with different rules, which is the fact that makes the rest of the object model simple to describe and expensive to run.

First met in T08. See also [object header](#object-header), [type object](#type-object). In the source: [`Include/object.h:127-150@v3.15.0rc1#_object`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/object.h#L127-L150).

### object header

**The reference count and the type pointer that every object starts with.**

Two fields, in that order, at the front of every object. It is what lets a function take a `PyObject *` without knowing what it is and still be able to ask. Variable sized objects such as lists and tuples have a third field for the length.

First met in T08. See also [object](#object), [reference count](#reference-count), [type object](#type-object). In the source: [`Include/object.h:156-170@v3.15.0rc1#_object`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/object.h#L156-L170).

### type object

**The object describing what another object is and what can be done to it.**

It is itself an object, with a header and a reference count and a type of its own, and it holds the function pointers for everything from addition to deallocation. When Python needs to add two things, it looks in their type objects for the function to call, and that indirection is the whole of what people mean by dynamic typing here. It is also the largest struct in the interpreter, and most of it is answers to questions about instances rather than about the type.

Also written `PyTypeObject`. First met in T08. See also [object](#object), [object header](#object-header), [static type](#static-type), [heap type](#heap-type). In the source: [`Include/cpython/object.h:147-151@v3.15.0rc1#_typeobject`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/cpython/object.h#L147-L151).

### reference count

**How many references to an object there currently are.**

Every reference taken adds one and every reference released takes one away, and at zero the object is freed immediately. `sys.getrefcount` is the way to look at it from Python and its answer includes the reference created by asking, though as of 3.14 not always, because passing a local now often hands over a borrowed reference and costs nothing.

First met in T08. See also [new reference](#new-reference), [immortal object](#immortal-object), [deallocation](#deallocation). In the source: [`Include/refcount.h:417-429@v3.15.0rc1#Py_DECREF`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/refcount.h#L417-L429).

### immortal object

**An object whose count is parked at a value the interpreter never decreases.**

`None`, `True`, `False`, the small integers and every type object are immortal. They are never freed, which saves the cost of counting references to objects that are shared by everything, and it means the number `sys.getrefcount` gives you for them is a marker rather than a count. Printing it next to a paragraph about reference counting teaches the wrong thing.

First met in T08. See also [reference count](#reference-count). In the source: [`Include/refcount.h:125-136@v3.15.0rc1#_Py_IsImmortal`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/refcount.h#L125-L136).

### interning

**Keeping one shared copy of a string so that equal strings are often the same object.**

Names, attribute names and anything that looks like an identifier get interned, because comparing them by address is much faster than comparing them character by character, and the interpreter compares them constantly. This is why `is` sometimes appears to work on strings, and why relying on that is a mistake: the rule is about what the compiler chose to intern, not about equality.

First met in T08. See also [small integer cache](#small-integer-cache). In the source: [`Objects/codeobject.c:116-137@v3.15.0rc1#should_intern_string`](https://github.com/python/cpython/blob/v3.15.0rc1/Objects/codeobject.c#L116-L137).

### small integer cache

**A block of small integers made once at startup and handed out rather than built.**

The range is a compile time constant and it moved in 3.15, from minus 5 through 256 up to minus 5 through 1024, which quietly broke every tutorial that had hard coded the old bound. Measure it rather than quoting it, which takes about four lines.

First met in T08. See also [interning](#interning), [immortal object](#immortal-object). In the source: [`Include/internal/pycore_runtime_structs.h:96-98@v3.15.0rc1#_PY_NSMALLPOSINTS`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_runtime_structs.h#L96-L98).

### instance dictionary

**Where an ordinary object keeps its attributes.**

It is a real dict and you can look at it, which is why `self.name = name` works without anything being declared anywhere. Instances of the same class share the layout of their keys rather than each holding a full copy, so the memory cost is much lower than a dict per object would suggest, and `__slots__` removes it entirely at the cost of the flexibility.

Also written `__dict__`. First met in T08. See also [object](#object), [type object](#type-object).

### PyVarObject

**An object header with a length field welded on the end of it.**

Tuples, lists and bytes objects all hold a count of how many items they have, and rather than each of them inventing a field for it the header itself grows by one machine word called `ob_size`. It is the same trick as the header: put the thing everybody needs in a fixed place so that generic code can read it without knowing the type. Strings keep their length in the same place without being one of these, and integers used to and no longer do.

Also written variable sized object, `ob_size`. First met in O01. See also [object header](#object-header), [object](#object). In the source: [`Include/object.h:174-178@v3.15.0rc1#PyVarObject`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/object.h#L174-L178).

### slot

**One of the function pointer fields in a type object.**

`tp_repr`, `tp_hash`, `tp_call` and about seventy others. The interpreter reads them directly, so calling `repr(x)` is a load and an indirect call rather than a dictionary lookup. Python code never assigns to one. It defines a dunder method and a table walk fills the slot in, which is what makes the two spellings feel like the same thing.

Also written type slot. First met in O03. See also [slot wrapper](#slot-wrapper), [type object](#type-object). In the source: [`Objects/typeobject.c:11584-11590@v3.15.0rc1#slotdefs`](https://github.com/python/cpython/blob/v3.15.0rc1/Objects/typeobject.c#L11584-L11590).

### slot wrapper

**A dunder method that is really a C slot with a Python callable wrapped around it.**

When a type written in C is made ready, `add_operators` walks the slot table and puts one of these into the class dict for every slot that has a function in it. That is where `int.__add__` and `object.__repr__` come from: nobody wrote them as methods, they are `nb_add` and `tp_repr` made callable. `type(int.__add__).__name__` is `wrapper_descriptor`, which is how you tell one from an ordinary method.

Also written `wrapper_descriptor`. First met in O03. See also [slot](#slot), [type object](#type-object). In the source: [`Objects/typeobject.c:12456-12470@v3.15.0rc1#add_operators`](https://github.com/python/cpython/blob/v3.15.0rc1/Objects/typeobject.c#L12456-L12470).

### descriptor

**An object in a class dict whose type defines __get__, __set__ or __delete__.**

Reading an attribute that resolves to a descriptor calls `__get__` rather than handing the object back. There is nothing to inherit from and nothing to register, so having the method is the whole qualification. Functions are descriptors, which is where `self` comes from: `func_descr_get` returns the function on a class and a bound method on an instance. `property`, `classmethod`, `staticmethod`, every `__slots__` entry and most attributes defined from C are descriptors too. The protocol only applies to objects found on the type, so a descriptor sitting in an instance dict is an ordinary value.

Also written descriptor protocol. First met in O06. See also [data descriptor](#data-descriptor), [slot](#slot). In the source: [`Objects/funcobject.c:1264-1270@v3.15.0rc1#func_descr_get`](https://github.com/python/cpython/blob/v3.15.0rc1/Objects/funcobject.c#L1264-L1270).

### bound method

**A small object holding a function and the instance it was read from.**

`PyMethod_New` allocates one with two pointers, `im_func` and `im_self`, and calling it inserts the instance as the first argument. That is all `self` is. A fresh one is built on every attribute read, so `obj.method is obj.method` is false, though the two compare equal. The allocation comes off a free list when one is available, and the interpreter specialises the common call shape so that reading and immediately calling a method skips building the object at all.

First met in O06. See also [descriptor](#descriptor), [type object](#type-object). In the source: [`Objects/classobject.c:64-84@v3.15.0rc1#PyMethod_New`](https://github.com/python/cpython/blob/v3.15.0rc1/Objects/classobject.c#L64-L84).

### data descriptor

**An object on a type that has __set__ or __delete__ as well as __get__.**

The test is one line: `PyDescr_IsData` asks whether `tp_descr_set` is filled in. That one bit decides the whole precedence question, because attribute lookup calls a data descriptor before it ever looks in the instance dict and calls anything else after. `property` and the descriptors `__slots__` generates are data descriptors. A plain function is not, which is why you can shadow a method on one instance and cannot shadow a property.

Also written non data descriptor. First met in O05. See also [slot](#slot), [type object](#type-object). In the source: [`Objects/descrobject.c:1028-1032@v3.15.0rc1#PyDescr_IsData`](https://github.com/python/cpython/blob/v3.15.0rc1/Objects/descrobject.c#L1028-L1032).

### MRO

**The flat list of classes, in order, that a name is looked up in.**

Every type carries one as `tp_mro`, computed once when the class is made and recomputed for the whole subtree if `__bases__` is later assigned. It always starts with the type itself and ends with `object`. Attribute lookup, `super`, and the slot table all read this list rather than walking `__bases__`, which is why multiple inheritance has one answer instead of a search.

Also written method resolution order, `__mro__`, `tp_mro`. First met in O04. See also [C3 linearization](#c3-linearization), [type object](#type-object). In the source: [`Objects/typeobject.c:3431-3451@v3.15.0rc1#mro_implementation_unlocked`](https://github.com/python/cpython/blob/v3.15.0rc1/Objects/typeobject.c#L3431-L3451).

### C3 linearization

**The merge rule that turns a class and its bases into one ordered list.**

Take the MRO of each base, add the declared bases tuple, and repeatedly take the first head that does not appear later in any of the lists. If no such head exists the merge fails and you get a TypeError instead of a class. CPython spells this out in `pmerge`, and it is about forty lines. The rule guarantees a class comes before its bases and that the order you declared bases in is preserved.

Also written C3, the merge. First met in O04. See also [MRO](#mro). In the source: [`Objects/typeobject.c:3361-3400@v3.15.0rc1#pmerge`](https://github.com/python/cpython/blob/v3.15.0rc1/Objects/typeobject.c#L3361-L3400).

### static type

**A type object written out as a C literal and compiled into the binary.**

`int`, `str`, `list` and `type` itself are all one of these. There is exactly one of each, it is immortal, and it lives in the binary rather than on the heap, so you cannot assign an attribute to it and there is nothing to collect at shutdown. The flags word is what tells you: a static type does not have `Py_TPFLAGS_HEAPTYPE` set.

Also written builtin type. First met in O02. See also [heap type](#heap-type), [type object](#type-object). In the source: [`Objects/typeobject.c:7290-7295@v3.15.0rc1#PyType_Type`](https://github.com/python/cpython/blob/v3.15.0rc1/Objects/typeobject.c#L7290-L7295).

### heap type

**A type object built while the program is running, which is what a class statement makes.**

What actually gets allocated is a `PyHeapTypeObject`, a type object with all the operator tables attached after it, so a class costs about nine hundred bytes before you put anything in it. Unlike a static type it is reference counted, it can be collected, and you can assign to it, which is the whole difference between `Plain.nope = 1` working and `int.nope = 1` raising.

Also written `PyHeapTypeObject`. First met in O02. See also [static type](#static-type), [type object](#type-object), [metaclass](#metaclass). In the source: [`Include/cpython/object.h:272-296@v3.15.0rc1#PyHeapTypeObject`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/cpython/object.h#L272-L296).

### metaclass

**The type of a type, which is what gets called to build a class.**

A class statement compiles to a call to `__build_class__`, which runs the class body, collects the names it defined, and calls the metaclass with the name, the bases and that namespace. Unless you say otherwise the metaclass is `type`, which is why `type("Greeter", (), {})` and a class statement produce the same thing.

First met in O02. See also [type object](#type-object), [heap type](#heap-type). In the source: [`Python/bltinmodule.c:102-108@v3.15.0rc1#builtin___build_class__`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/bltinmodule.c#L102-L108).

### compact dict

**A dict laid out as a small array of slot numbers in front of an entry array.**

The slot array, `dk_indices`, holds a row number into the entry array, or -1 for a position never used, or -2 for one that used to hold something. The entry array is appended to and never reordered, so iterating it top to bottom gives insertion order with no bookkeeping at all. Only the small array has holes, which is why the layout is called compact: a mostly empty hash table costs one byte per slot rather than a whole row.

Also written compact ordered dict. First met in O07. See also [probe sequence](#probe-sequence), [instance dictionary](#instance-dictionary). In the source: [`Include/internal/pycore_dict.h:196-235@v3.15.0rc1#_dictkeysobject`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_dict.h#L196-L235).

### probe sequence

**The order of slots a dict lookup visits when the first one is a collision.**

The first slot is the hash masked down to the table size. After that the step is `i = mask & (i * 5 + perturb + 1)`, where `perturb` starts as the whole hash and is shifted right by 5 each round. The `i * 5 + 1` part visits every slot exactly once and in an order unrelated to how consecutive keys arrive, and `perturb` brings back the high bits of the hash the mask discarded. For a size 8 table starting at slot 0 the order is 0, 1, 6, 7, 4, 5, 2, 3.

First met in O07. See also [compact dict](#compact-dict). In the source: [`Objects/dictobject.c:1078-1101@v3.15.0rc1#do_lookup`](https://github.com/python/cpython/blob/v3.15.0rc1/Objects/dictobject.c#L1078-L1101).

### split table

**A dict whose keys are owned by a type and shared by every instance of it.**

The keys array is marked `DICT_KEYS_SPLIT` and hangs off the type rather than off any one instance, so the attribute names of a class are stored once instead of once per object. Each instance carries only an array of value pointers. `_PyDict_NewKeysForClass` builds the shared array when the class is created and prefills it from `__static_attributes__`, and `insert_split_key` adds any name discovered later. There is room for 30 names, or 29 if they are not known when the class is made, because creating the first instance reserves a slot.

Also written shared keys. First met in O08. See also [inline values](#inline-values), [compact dict](#compact-dict). In the source: [`Objects/dictobject.c:7210-7238@v3.15.0rc1#_PyDict_NewKeysForClass`](https://github.com/python/cpython/blob/v3.15.0rc1/Objects/dictobject.c#L7210-L7238).

### inline values

**The array of attribute values stored inside an instance, with no dict at all.**

An instance of a class with a split table has its values allocated as part of the object, past whatever fields the type declared. Four bytes of bookkeeping come first, then one pointer per possible attribute, then one byte per attribute actually set recording which slot it went into, which is how per instance insertion order survives a shared keys array. `obj.__dict__` builds a real dict object on demand that points at the same values, and asking for it makes the instance permanently bigger and stops its attribute reads specialising.

Also written managed dict. First met in O08. See also [split table](#split-table), [instance dictionary](#instance-dictionary). In the source: [`Objects/dictobject.c:7241-7274@v3.15.0rc1#_PyObject_InitInlineValues`](https://github.com/python/cpython/blob/v3.15.0rc1/Objects/dictobject.c#L7241-L7274).

### digit array

**The array of base 2**30 digits an int is made of, least significant first.**

A digit is a `uint32_t` carrying 30 bits, so two bits in every four bytes go unused. That is deliberate: the product of two digits fits in 64 bits with enough headroom left to accumulate carries before anything has to be done about overflow. Two rules hold everywhere in the source and every operation is allowed to assume them, that no digit is ever at or above the base, and that the most significant digit is never zero. The second is why almost everything ends by calling `long_normalize`.

Also written ob_digit. First met in O09. See also [compact int](#compact-int). In the source: [`Include/cpython/longintrepr.h:64-91@v3.15.0rc1`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/cpython/longintrepr.h#L64-L91).

### compact int

**An int small enough to be a sign and one digit, with a fast path all its own.**

The sign, the digit count and one flag share a single word called `lv_tag`, packed so that a tag below 16 means the digit count is 0 or 1 and the sign is not negative. `_PyLong_IsCompact` is that one unsigned comparison, and the value comes back out with a multiply and no branches. Anything from 0 up to 2**30 - 1 qualifies on an ordinary build, which is most of the integers a program actually handles, so the fast path is taken constantly.

First met in O09. See also [digit array](#digit-array), [small int cache](#small-int-cache). In the source: [`Include/cpython/longintrepr.h:121-125@v3.15.0rc1#_PyLong_IsCompact`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/cpython/longintrepr.h#L121-L125).

### small int cache

**The fixed array of int objects built at startup and handed out rather than allocated.**

Every operation whose result lands in the range returns the object from the array instead of making a new one, so two separate computations that reach the same small value give you the same object. They are immortal, because an object handed to everybody forever cannot usefully be reference counted. The range runs from -5 up to a ceiling that was 256 through 3.14 and is 1024 from 3.15, which is why using `is` on integers is a bug waiting for a version bump.

Also written small ints. First met in O09. See also [compact int](#compact-int), [immortal object](#immortal-object). In the source: [`Include/internal/pycore_runtime_structs.h:97-98@v3.15.0rc1#_PY_NSMALLPOSINTS`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_runtime_structs.h#L97-L98).

### code point

**The number Unicode assigns to a character, from 0 up to 0x10FFFF.**

A Python string is a sequence of code points, not of bytes, and `len` counts code points. This is the thing that makes strings portable and it is also the thing that makes them expensive, because the largest code point present decides how many bytes every character in the string takes. `ord` gives you the code point of a character and `chr` goes back the other way.

First met in O10. See also [string kind](#string-kind), [compact string](#compact-string). In the source: [`Include/cpython/unicodeobject.h:66-88@v3.15.0rc1`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/cpython/unicodeobject.h#L66-L88).

### string kind

**Whether a string stores each character in 1, 2 or 4 bytes.**

The kind is set once when the string is created, from the largest code point in it, and it never changes afterwards because strings are immutable. One byte if nothing goes above 255, two if nothing goes above 65535, four otherwise. There is a fourth case that is not a kind value but behaves like one: a string where everything is ASCII gets a smaller struct as well as one byte characters. Adding a single wide character to a narrow string rewrites every character in it at the wider size.

Also written kind. First met in O10. See also [code point](#code-point), [compact string](#compact-string). In the source: [`Objects/unicodeobject.c:1272-1311@v3.15.0rc1#PyUnicode_New`](https://github.com/python/cpython/blob/v3.15.0rc1/Objects/unicodeobject.c#L1272-L1311).

### compact string

**A string whose characters sit in the same allocation as its header.**

One `PyObject_Malloc` covers the struct, the characters and a trailing zero byte, so there is no second block and no pointer to follow. That trailing zero is why the buffer can be handed straight to C functions expecting a null terminated string. The alternative, called the legacy form in the source, keeps the characters in a separate block and only shows up for subclasses of `str`, which have their own fields to store.

First met in O10. See also [string kind](#string-kind), [interning](#interning). In the source: [`Objects/unicodeobject.c:1322-1336@v3.15.0rc1`](https://github.com/python/cpython/blob/v3.15.0rc1/Objects/unicodeobject.c#L1322-L1336).

### over allocation

**Asking for more room than is needed right now, so the next few asks are free.**

A list keeps two sizes: `ob_size`, how many items you can see, and `allocated`, how many slots the array behind it has. `list_resize` asks for the new size plus an eighth of it plus six, rounded down to a multiple of four, which gives the sequence 4, 8, 16, 24, 32, 40, 52, 64, 76, 92. Growing by a fraction of the current size is what makes a long run of appends cheap on average: a hundred thousand appends cost about sixty six reallocations rather than a hundred thousand. The same function shrinks the array, but only once the length drops below half of what is allocated.

First met in O11. See also [cached hash](#cached-hash). In the source: [`Objects/listobject.c:119-129@v3.15.0rc1`](https://github.com/python/cpython/blob/v3.15.0rc1/Objects/listobject.c#L119-L129).

### cached hash

**A hash computed on the first ask and kept in the object from then on.**

Strings and tuples both do this, and both can only do it because they cannot change. The field starts at -1 and the hash function returns early if it is anything else. This is the real reason a tuple can be a dict key and a list cannot: a container that can change has no stable hash to offer. It is also why a recycled tuple taken off a free list has to have the field cleared before it is handed out again.

First met in O11. See also [over allocation](#over-allocation), [compact string](#compact-string). In the source: [`Objects/tupleobject.c:371-404@v3.15.0rc1#tuple_hash`](https://github.com/python/cpython/blob/v3.15.0rc1/Objects/tupleobject.c#L371-L404).

## Memory

Where objects come from and what happens to them afterwards. T09 is the lesson.

### obmalloc

**CPython's own allocator, which handles every small object rather than passing it on.**

Anything up to 512 bytes is served from memory CPython already holds, because objects that small are created and destroyed far too often for the system allocator to be a reasonable thing to call. Larger requests go straight through to `malloc`.

First met in T09. See also [block](#block), [pool](#pool), [arena](#arena). In the source: [`Include/internal/pycore_obmalloc.h:156-164@v3.15.0rc1#SMALL_REQUEST_THRESHOLD`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_obmalloc.h#L156-L164).

### block

**The smallest unit obmalloc hands out, rounded up to a multiple of sixteen bytes.**

An object does not get the number of bytes it asked for, it gets the next size up, and every block in a given pool is the same size. That rounding is why two objects that differ by a few bytes can take exactly the same amount of memory.

First met in T09. See also [pool](#pool), [obmalloc](#obmalloc). In the source: [`Include/internal/pycore_obmalloc.h:128-146@v3.15.0rc1#ALIGNMENT`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_obmalloc.h#L128-L146).

### pool

**A page sized run of blocks that are all the same size.**

Keeping one size per pool means allocating is taking the first entry off a free list and freeing is putting it back, with no searching and no merging of neighbours. It also means a pool is only reusable for objects of that size, which is where fragmentation comes from.

First met in T09. See also [block](#block), [arena](#arena). In the source: [`Include/internal/pycore_obmalloc.h:232-241@v3.15.0rc1#POOL_BITS`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_obmalloc.h#L232-L241).

### arena

**A large chunk requested from the operating system and carved up into pools.**

This is the level at which memory is actually given back, and it can only go back when every pool inside it is empty. That is the mechanism behind the common observation that a Python process which allocated a lot of memory does not always return it: one live object in an arena keeps the whole thing.

First met in T09. See also [pool](#pool), [obmalloc](#obmalloc). In the source: [`Include/internal/pycore_obmalloc.h:216-226@v3.15.0rc1#ARENA_BITS`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_obmalloc.h#L216-L226).

### deallocation

**What happens the moment an object's reference count reaches zero.**

The type's deallocation function runs, which releases the references the object was holding, so freeing one object often frees a chain of them. This is immediate and it is the main way memory is reclaimed. The cycle collector is the exception rather than the rule.

First met in T09. See also [reference count](#reference-count), [finalizer](#finalizer), [reference cycle](#reference-cycle). In the source: [`Objects/object.c:3282-3300@v3.15.0rc1#_Py_Dealloc`](https://github.com/python/cpython/blob/v3.15.0rc1/Objects/object.c#L3282-L3300).

### reference cycle

**A group of objects that between them hold all the references keeping them alive.**

Two objects pointing at each other is the smallest one. Counting alone can never free them, because each is being held by another member of the group, so both counts stay above zero long after the last name for either has gone. This is the entire reason a second mechanism exists.

First met in T09. See also [cycle collector](#cycle-collector), [reference count](#reference-count).

### cycle collector

**The part that finds groups of objects keeping each other alive and frees them.**

It works by copying every count, subtracting the references that objects in the group hold to each other, and seeing which objects are left with nothing pointing at them from outside. Anything not reached from those is garbage. It only looks at container types, since an object that cannot refer to anything cannot be part of a cycle.

Also written gc. First met in T09. See also [reference cycle](#reference-cycle), [generation](#generation). In the source: [`Python/gc.c:485-501@v3.15.0rc1#subtract_refs`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/gc.c#L485-L501).

### generation

**Which of the collector's three lists an object is currently in.**

New objects go in the youngest, which is collected often and is small, and anything surviving a collection moves up to a list that is looked at less often. The bet is that most objects die young, and it is a good bet. Integers, floats and strings are not tracked at all.

First met in T09. See also [cycle collector](#cycle-collector). In the source: [`Include/internal/pycore_interp_structs.h:271-286@v3.15.0rc1#GC_GENERATION_INIT`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_interp_structs.h#L271-L286).

### weak reference

**A reference that lets you reach an object without keeping it alive.**

It is the only way to watch an object die from Python, because any ordinary name that could tell you is itself a reason it is still there. When the object goes, the weak reference starts returning `None` and any callback attached to it runs.

First met in T09. See also [reference count](#reference-count), [deallocation](#deallocation). In the source: [`Objects/weakrefobject.c:1001-1024@v3.15.0rc1#PyObject_ClearWeakRefs`](https://github.com/python/cpython/blob/v3.15.0rc1/Objects/weakrefobject.c#L1001-L1024).

### finalizer

**A `__del__` method, run before an object is freed.**

The collector runs finalizers on the objects in a cycle before it frees any of them, and a finalizer that stores a reference to its own object somewhere can bring the whole group back. That case is handled rather than being an error, which is worth knowing before writing one.

Also written `__del__`. First met in T09. See also [deallocation](#deallocation), [cycle collector](#cycle-collector). In the source: [`Python/gc.c:1041-1074@v3.15.0rc1#finalize_garbage`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/gc.c#L1041-L1074).

### GC pre header

**Two words allocated in front of an object, holding its place in the collector's list.**

Only the types the cycle collector tracks get one, and the object's own address points past it, so nothing that reads the header ever sees it. You can still measure it: `sys.getsizeof` adds it and the object's own `__sizeof__` does not, so the gap between those two is exactly this.

Also written `PyGC_Head`. First met in O01. See also [cycle collector](#cycle-collector), [object header](#object-header). In the source: [`Include/internal/pycore_interp_structs.h:158-169@v3.15.0rc1#PyGC_Head`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_interp_structs.h#L158-L169).

### free list

**A small stash of dead objects of one type, kept so the next one can skip the allocator.**

When an object of a type that has one is freed, it is not handed back to the allocator, it is pushed onto a chain of dead objects of exactly that type. The next request pops it off and reuses the memory. The chain is threaded through the objects themselves, using the first word of each dead one to point at the next, so the stash costs nothing beyond a head pointer and a count. There is a cap per type, and the cycle collector empties every one of them, but only when it collects the oldest generation.

First met in O12. See also [obmalloc](#obmalloc), [deallocation](#deallocation), [generation](#generation). In the source: [`Include/internal/pycore_freelist.h:52-63@v3.15.0rc1#_PyFreeList_Push`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_freelist.h#L52-L63).

### exact type check

**A test that a value is that type and not a subclass of it.**

`PyList_Check` says yes to anything that inherits from `list` and `PyList_CheckExact` says yes only to `list` itself. Fast paths and caches use the exact form, because a subclass can have extra fields, a different size and a different deallocation function, so recycling one as if it were the base type would be wrong. This is why a subclass often quietly loses an optimisation the base type gets.

First met in O12. See also [free list](#free-list), [type object](#type-object), [heap type](#heap-type). In the source: [`Include/listobject.h:24-26@v3.15.0rc1#PyList_CheckExact`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/listobject.h#L24-L26).

### weakref offset

**Where in an object the interpreter looks for its list of weak references.**

Every type carries this number and Python shows it as `__weakrefoffset__`. Zero means the type has no room for the pointer, so you cannot take a weak reference to one of its instances, which is why `list` and `int` refuse. Static types put a real field in the struct and get a positive number. A class you write in Python gets minus thirty two instead, because the pointer lives in a pre header allocated in front of the object rather than inside it.

Also written `tp_weaklistoffset`, `__weakrefoffset__`. First met in O13. See also [weak reference](#weak-reference), [GC pre header](#gc-pre-header), [static type](#static-type). In the source: [`Include/internal/pycore_object.h:922-928@v3.15.0rc1#MANAGED_WEAKREF_OFFSET`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_object.h#L922-L928).

### weakref callback

**A function attached to a weak reference, run just after the object dies.**

It is handed the weak reference rather than the object, and by the time it runs every weak reference to that object has already been broken, so calling it gives you `None`. That is deliberate. It means a callback has no way to make the doomed object reachable again. If the callback raises, the exception is reported as unraisable and does not propagate, because there is no caller to propagate it to.

First met in O13. See also [weak reference](#weak-reference), [finalizer](#finalizer), [deallocation](#deallocation). In the source: [`Objects/weakrefobject.c:987-999@v3.15.0rc1#handle_callback`](https://github.com/python/cpython/blob/v3.15.0rc1/Objects/weakrefobject.c#L987-L999).

### resurrection

**A finalizer storing `self`, which cancels the deallocation that called it.**

`__del__` is handed the object as `self`, and `self` is an ordinary reference, so putting it in a list somewhere makes the object reachable again and the interpreter stops freeing it. This is expected rather than an error. Deallocation bumps the count before calling the finalizer and checks afterwards whether anything else took a reference, and if the object came out of a cycle the collector moves it to the old generation instead of freeing it.

First met in O14. See also [finalizer](#finalizer), [finalized bit](#finalized-bit), [cycle collector](#cycle-collector). In the source: [`Objects/object.c:594-630@v3.15.0rc1#PyObject_CallFinalizerFromDealloc`](https://github.com/python/cpython/blob/v3.15.0rc1/Objects/object.c#L594-L630).

### finalized bit

**One bit on an object saying its finalizer has already been called.**

It is set before the finalizer runs rather than after, which is what guarantees a finalizer is called at most once even if it resurrects the object or raises. `gc.is_finalized` reads it. Setting it first is also why a finalizer that fails halfway is not retried: as far as the interpreter is concerned that object has had its turn.

Also written `gc.is_finalized`. First met in O14. See also [finalizer](#finalizer), [resurrection](#resurrection). In the source: [`Include/internal/pycore_gc.h:166-181@v3.15.0rc1#_PyGC_SET_FINALIZED`](https://github.com/python/cpython/blob/v3.15.0rc1/Include/internal/pycore_gc.h#L166-L181).

## Building the interpreter

The words that turn out to be about the binary rather than about the language. B01 through B04 are the lessons, and several numbers in the earlier lessons move when the build does.

### configure

**The script that inspects your machine and writes the Makefile and pyconfig.h.**

Nobody wrote `configure`. It is generated from `configure.ac` by autoconf, and it is the file that turns your flags and your operating system into two files the rest of the build reads. The argument list you gave it survives in the finished interpreter as `sysconfig.get_config_var("CONFIG_ARGS")`, which is how you can find out how a Python you did not build was built.

Also written `./configure`, `configure.ac`. First met in B01. See also [debug build](#debug-build), [generated file](#generated-file).

### pyconfig

**The header full of #define lines saying what your system has and what you asked for.**

Every C file in CPython includes `pyconfig.h`, and it is how one source tree becomes a different program on Linux, on macOS and in a browser. It is also more complete than `sysconfig`: the parser behind `sysconfig.get_config_vars` only matches macros whose names start with a capital letter, so every `_Py_` macro in the header is invisible from Python. When the two disagree, the header is the one the compiler saw.

Also written `pyconfig.h`. First met in B01. See also [configure](#configure). In the source: [`Lib/sysconfig/__init__.py:438@v3.15.0rc1#define_rx`](https://github.com/python/cpython/blob/v3.15.0rc1/Lib/sysconfig/__init__.py#L438).

### debug build

**An interpreter built with Py_DEBUG, which checks its own invariants as it runs.**

`--with-pydebug` turns on assertions all through the interpreter, adds `sys.gettotalrefcount`, and makes the allocator fill freed memory with a recognisable byte pattern so a use after free shows up as garbage instead of as the old value still sitting there. It also makes objects bigger and everything two to three times slower, which is why behaviour in this material comes from a debug build and timings never do.

Also written `--with-pydebug`, `Py_DEBUG`. First met in B01. See also [configure](#configure), [reference count](#reference-count). In the source: [`configure.ac:1771-1785@v3.15.0rc1#Py_DEBUG`](https://github.com/python/cpython/blob/v3.15.0rc1/configure.ac#L1771-L1785).

### free threaded build

**CPython built without the GIL, which is a different interpreter rather than a flag.**

`--disable-gil` sets `Py_GIL_DISABLED`, and what follows is not a switch: the object header gains fields, reference counting splits into a local count and a shared one, the allocator becomes per thread and the cycle collector is a different algorithm. Every reference count and every `sys.getsizeof` in the object lessons comes out differently here, which is why those lessons measure rather than assert.

Also written `--disable-gil`, `Py_GIL_DISABLED`. First met in B01. See also [reference count](#reference-count), [cycle collector](#cycle-collector), [object header](#object-header).

### profile guided optimization

**Build the interpreter, run it to see which branches are hot, then build it again.**

`--enable-optimizations` is worth roughly ten percent and turns a five minute build into twenty minutes or an hour, because the whole thing is compiled twice with a test run in between. It is the right flag for measuring speed and the wrong one for understanding a crash, since everything hot has been inlined into everything else by the time the debugger sees it.

Also written PGO, `--enable-optimizations`. First met in B01. See also [debug build](#debug-build). In the source: [`configure.ac:1847-1860@v3.15.0rc1#Py_OPT`](https://github.com/python/cpython/blob/v3.15.0rc1/configure.ac#L1847-L1860).

### WebAssembly

**A portable instruction set that browsers run, and one of the targets CPython builds for.**

CPython compiled to WebAssembly is a real CPython rather than a reimplementation, which is what makes the browser tier of this project possible at all. It is a 32 bit target, so a pointer is 4 bytes instead of 8, and every object size in the lessons shrinks with it. That is the single most common reason a number in a lesson does not match what a reader sees.

Also written wasm. First met in B01. See also [Pyodide](#pyodide).

### Pyodide

**A CPython distribution compiled to WebAssembly, with a package installer attached.**

This is what runs when you open one of these lessons in a browser without a local Python. It is a genuine CPython build, so `dis`, `gc` and `sys.monitoring` all work, but it is not the same build as the one on your laptop and a few things are missing from it. Every lesson opens with a banner that says which of the two you are on, for exactly this reason.

First met in B01. See also [WebAssembly](#webassembly).

## Stopping a running interpreter

The words for looking at a program that is halfway through doing something. Most of them come from B02, and about half are things you already have on your machine without knowing it.

### pdb

**The debugger that ships with Python, written in Python.**

It is a subclass of `bdb.Bdb` and `cmd.Cmd`, which is to say a trace hook with a command prompt bolted on. Because the prompt is just a pair of streams, you can hand it a list of commands instead of a keyboard and get the whole session back as text, which is how this project shows one. `breakpoint()` is the short way in.

Also written `breakpoint()`, `python -m pdb`. First met in B02. See also [trace function](#trace-function), [gdb](#gdb). In the source: [`Lib/pdb.py:488@v3.15.0rc1#Pdb`](https://github.com/python/cpython/blob/v3.15.0rc1/Lib/pdb.py#L488).

### trace function

**A function the interpreter calls back on every call, line and return.**

Install one with `sys.settrace` and the interpreter will tell you about everything your program does, one event at a time. Every Python debugger, coverage tool and line profiler is built on this hook or on the newer `sys.monitoring`. It is also expensive, because it turns every line into a Python call, which is why nothing has it on by default.

Also written `sys.settrace`. First met in B02. See also [pdb](#pdb), [monitoring events](#monitoring-events). In the source: [`Lib/bdb.py:232-236@v3.15.0rc1#start_trace`](https://github.com/python/cpython/blob/v3.15.0rc1/Lib/bdb.py#L232-L236).

### monitoring events

**The newer, cheaper way to be told what a running program is doing.**

Added in 3.12, and what pdb prefers when it can get it. A trace function is called for every event whether you wanted it or not, while `sys.monitoring` lets a tool register for only the events it cares about, so an unwatched line costs nothing. Several tools can watch at once without fighting over the one hook.

Also written `sys.monitoring`, PEP 669. First met in B02. See also [trace function](#trace-function).

### gdb

**A debugger that works on a process from outside it, rather than from inside.**

gdb attaches to a running program, or starts one under its control, and can stop it anywhere and read its memory. That is what makes it able to answer questions pdb cannot, because it does not need the program to still be running Python, or running at all. CPython ships a script for it, `Tools/gdb/libpython.py`, which teaches gdb what a Python frame looks like and adds the `py-bt` command.

Also written `py-bt`, lldb. First met in B02. See also [pdb](#pdb), [backtrace](#backtrace), [debug build](#debug-build).

### backtrace

**The list of calls that were in progress when a program stopped.**

A Python traceback and a C backtrace are the same idea at two levels, and a stopped interpreter has both at once. They do not have the same length: four nested Python calls can sit inside a single `_PyEval_EvalFrameDefault` frame, because the eval loop reuses one C frame for a whole chain of Python ones. `py-bt` is the command that reads the second out of the first.

Also written `bt`, stack trace. First met in B02. See also [gdb](#gdb), [frame](#frame), [eval loop](#eval-loop).

### segmentation fault

**The kernel taking a process away for touching memory that is not its own.**

Not an exception. There is no interpreter left to build one, nothing is printed, and `try` and `except` never see it. You reach one through `ctypes` or through a C extension with a bug in it. A debugger attached to the corpse is the only thing that will tell you which line of Python was responsible, which is what `py-bt` is for.

Also written SIGSEGV, segfault. First met in B02. See also [gdb](#gdb), [backtrace](#backtrace).

### regen

**The make targets that rewrite every generated file from its input.**

`make regen-cases` rebuilds the twelve files that come out of `Python/bytecodes.c`, `make regen-all` does that and the rest, and the reason to know the names is that forgetting them is the classic wasted afternoon. You edit the input, you build, nothing changes, and the build was quietly using the generated files that were already there. The Makefile calls each generator directly, so you can run one on its own with the interpreter you already have.

Also written `make regen-all`, `make regen-cases`. First met in B04. See also [generated file](#generated-file), [Argument Clinic](#argument-clinic).

### blurb

**One file per change under Misc/NEWS.d, naming the issue it came from.**

A user visible change ships with a small file whose name carries the issue number, and at release time they are collected into one file per version. It exists so that a release note is written by the person who made the change rather than by somebody guessing afterwards, and it means every entry in a release note is a link back to the argument that produced it.

First met in B04. See also [devguide](#devguide). In the source: [`Misc/NEWS.d/next/Core_and_Builtins/README.rst:1-3@v3.15.0rc1`](https://github.com/python/cpython/blob/v3.15.0rc1/Misc/NEWS.d/next/Core_and_Builtins/README.rst#L1-L3).

### devguide

**The separate repository that documents how to work on CPython.**

Building, testing, the git workflow, what a core developer will ask you for and how long to expect to wait. It is written for a new contributor rather than for a reader, which makes it the wrong place to look for how the interpreter works and the right place to look for anything about the process around it. `InternalDocs/` in the main repository is the other half, and is the one written for somebody trying to understand the code.

Also written devguide.python.org. First met in B04. See also [blurb](#blurb), [generated file](#generated-file).

## Checking that it still works

The words for CPython's own test suite. It is twice the size of the library it tests, it is ordinary unittest underneath, and the rest is what it takes to run four hundred files in a row without one of them spoiling the next.

### regrtest

**The runner CPython uses on its own test suite.**

A layer on top of unittest that knows how to find test files in a directory, run each one in its own process, put a time limit on it, check the environment came back the way it was found, and hunt reference leaks. `python -m test` is how you start it. For one test file none of that matters and plain unittest does the same job.

Also written `python -m test`, `Lib/test/regrtest.py`. First met in B03. See also [test case](#test-case), [reference leak](#reference-leak). In the source: [`Lib/test/libregrtest/main.py:793-796@v3.15.0rc1#main`](https://github.com/python/cpython/blob/v3.15.0rc1/Lib/test/libregrtest/main.py#L793-L796).

### test case

**One method on a unittest.TestCase subclass, whose name starts with test.**

The unit everything else counts. A file holds several classes, a class holds several of these, and the dotted name of one, like `test.test_dis.DisTests.test_widths`, is what `-m` and `--list-cases` work in. Failing one prints FAIL, raising anything else prints ERROR, and the difference is worth knowing when you are reading a wall of them.

Also written `assertEqual`, test method. First met in B03. See also [regrtest](#regrtest). In the source: [`Lib/unittest/case.py:393@v3.15.0rc1#TestCase`](https://github.com/python/cpython/blob/v3.15.0rc1/Lib/unittest/case.py#L393).

### reference leak

**An object the interpreter can no longer reach and will never free.**

Not a crash and not a failing test. The test passes, the memory stays, and the only sign is that the process holds a few more references after the test than before. Almost always a bug in C code that forgot a decref. Found by running a test several times over on a debug build and watching `sys.gettotalrefcount()`, which is what the `-R` flag does.

Also written `-R 3:3`, refleak. First met in B03. See also [reference count](#reference-count), [debug build](#debug-build). In the source: [`Lib/test/libregrtest/refleak.py:196-209@v3.15.0rc1#check_rc_deltas`](https://github.com/python/cpython/blob/v3.15.0rc1/Lib/test/libregrtest/refleak.py#L196-L209).

### environment changed

**A test that passed and left something different behind it.**

regrtest takes a copy of 28 things before each test file, from `os.environ` and `sys.path` down to whether your terminal still echoes, and compares afterwards. A mismatch is exit code 3, or a failure with `--fail-env-changed`. It matters because the files run in a random order in one process, so an untidy test breaks a different test on a different machine a week later.

Also written `--fail-env-changed`. First met in B03. See also [regrtest](#regrtest). In the source: [`Lib/test/libregrtest/save_env.py:62-76@v3.15.0rc1#resources`](https://github.com/python/cpython/blob/v3.15.0rc1/Lib/test/libregrtest/save_env.py#L62-L76).

### resource

**Something a test needs that the runner will not use unless told.**

Network access, audio devices, large temporary files, anything slow or intrusive. A test asks for one with `@support.requires_resource('network')` and is skipped unless the run was started with `-u network`, or `-u all`. This is why a clean local run and a buildbot run do not cover the same tests.

Also written `-u all`, `requires_resource`. First met in B03. See also [regrtest](#regrtest). In the source: [`Lib/test/support/__init__.py:1354-1360@v3.15.0rc1#requires_resource`](https://github.com/python/cpython/blob/v3.15.0rc1/Lib/test/support/__init__.py#L1354-L1360).
