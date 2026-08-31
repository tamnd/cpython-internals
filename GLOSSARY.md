# Glossary

One definition per term, in one place, so that a lesson can use a word without stopping to explain it and without assuming you remember it from forty lessons ago. Lessons link into this file rather than repeating themselves.

The order below is the order you meet these things, not alphabetical, because reading it straight through is a reasonable thing to do. If you are looking one up, the index is next.

This file is generated from `pyxray/src/pyxray/glossary.py`. Edit that and run `just build-glossary`.

## Index

[ASDL](#asdl) | [Argument Clinic](#argument-clinic) | [EXTENDED_ARG](#extended_arg) | [JIT](#jit) | [PEG parser](#peg-parser) | [Pyodide](#pyodide) | [WebAssembly](#webassembly) | [abstract syntax tree](#abstract-syntax-tree) | [adaptive instruction](#adaptive-instruction) | [arena](#arena) | [assembler](#assembler) | [backtrace](#backtrace) | [basic block](#basic-block) | [binding](#binding) | [block](#block) | [borrowed reference](#borrowed-reference) | [bytecode](#bytecode) | [cell](#cell) | [closure](#closure) | [code generation](#code-generation) | [code object](#code-object) | [computed goto](#computed-goto) | [configure](#configure) | [constant folding](#constant-folding) | [control flow graph](#control-flow-graph) | [cycle collector](#cycle-collector) | [deallocation](#deallocation) | [debug build](#debug-build) | [deoptimization](#deoptimization) | [dispatch](#dispatch) | [environment changed](#environment-changed) | [eval loop](#eval-loop) | [exception table](#exception-table) | [finalizer](#finalizer) | [frame](#frame) | [free threaded build](#free-threaded-build) | [free variable](#free-variable) | [gdb](#gdb) | [generated file](#generated-file) | [generation](#generation) | [grammar](#grammar) | [header file](#header-file) | [immortal object](#immortal-object) | [indent and dedent](#indent-and-dedent) | [inline cache](#inline-cache) | [instance dictionary](#instance-dictionary) | [instruction](#instruction) | [interning](#interning) | [line table](#line-table) | [monitoring events](#monitoring-events) | [new reference](#new-reference) | [object](#object) | [object header](#object-header) | [obmalloc](#obmalloc) | [oparg](#oparg) | [opcode](#opcode) | [pdb](#pdb) | [pointer](#pointer) | [pool](#pool) | [profile guided optimization](#profile-guided-optimization) | [pseudo instruction](#pseudo-instruction) | [pyconfig](#pyconfig) | [reference count](#reference-count) | [reference cycle](#reference-cycle) | [reference leak](#reference-leak) | [regrtest](#regrtest) | [resource](#resource) | [scope](#scope) | [segmentation fault](#segmentation-fault) | [small integer cache](#small-integer-cache) | [specialization](#specialization) | [stack effect](#stack-effect) | [stolen reference](#stolen-reference) | [struct](#struct) | [symbol table](#symbol-table) | [test case](#test-case) | [tier one](#tier-one) | [tier two](#tier-two) | [token](#token) | [tokenizer](#tokenizer) | [trace function](#trace-function) | [type object](#type-object) | [value stack](#value-stack) | [weak reference](#weak-reference)

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

## Turning a tree into instructions

What the compiler does after it knows what the names are, and the shape of the thing it produces. T05 and T06 are the lessons.

### code generation

**Walking the tree and emitting instructions for each node.**

This stage is mechanical on purpose. It does not try to be clever, it emits a straightforward sequence including jumps to labels, and everything that makes the result smaller or faster happens afterwards on the graph. Separating the two is what keeps `Python/codegen.c` readable.

First met in T05. See also [control flow graph](#control-flow-graph), [abstract syntax tree](#abstract-syntax-tree). In the source: [`Python/codegen.c:894-897@v3.15.0rc1#_PyCodegen_Expression`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/codegen.c#L894-L897).

### control flow graph

**The emitted instructions as blocks, with the jumps between them as edges.**

This is the form the optimizer works on, because questions like is this code reachable and how deep does the stack get are questions about a graph and are awkward to ask about a flat list. It is turned back into a flat list at the end by the assembler.

Also written CFG. First met in T05. See also [basic block](#basic-block), [assembler](#assembler), [constant folding](#constant-folding). In the source: [`Python/flowgraph.c:3753-3757@v3.15.0rc1#_PyCfg_OptimizeCodeUnit`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/flowgraph.c#L3753-L3757).

### basic block

**A run of instructions with one way in at the top and one way out at the bottom.**

Nothing jumps into the middle of one and nothing branches out of the middle, which is what makes them useful: anything true at the top of a block stays true all the way down it. A jump target always starts a new block.

First met in T05. See also [control flow graph](#control-flow-graph). In the source: [`Python/flowgraph.c:1008-1044@v3.15.0rc1#remove_unreachable`](https://github.com/python/cpython/blob/v3.15.0rc1/Python/flowgraph.c#L1008-L1044).

### constant folding

**Working an expression out while compiling, so it does not have to be worked out later.**

`6 * 7` becomes 42 in the compiled file and the multiply never reaches the interpreter. CPython does this twice, once on the tree and once on the graph, and it stops when the answer would be unreasonably large, so folding a giant power does not make an import take a second and a megabyte. The old operand often stays behind in the constants with nothing loading it, which is a good thing to notice.

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

Also written code unit. First met in T06. See also [opcode](#opcode), [oparg](#oparg), [inline cache](#inline-cache).

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

It is itself an object, with a header and a reference count and a type of its own, and it holds the function pointers for everything from addition to deallocation. When Python needs to add two things, it looks in their type objects for the function to call, and that indirection is the whole of what people mean by dynamic typing here.

First met in T08. See also [object](#object), [object header](#object-header).

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
