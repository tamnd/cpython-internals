# BP-PIPELINE: source text to a running frame

**Covers:** `Python/pythonrun.c`, `Parser/peg_api.c`, `Python/compile.c`, and the contract at each of the seven stage boundaries
**Lesson:** T01, one line, seven stages
**Status:** complete
**Compatibility tier:** A

## 1. Purpose and scope

This blueprint specifies the sequence of transformations that turns a buffer of source bytes into a value, and it fixes what crosses each boundary between them. There are eight artifacts and therefore seven transitions.

| # | Artifact | Produced by |
|---|---|---|
| 0 | source bytes | the caller |
| 1 | a token stream | `Parser/lexer/lexer.c` |
| 2 | an abstract syntax tree | `Parser/parser.c` |
| 3 | a symbol table | `Python/symtable.c` |
| 4 | an instruction sequence | `Python/codegen.c` |
| 5 | an optimized control flow graph | `Python/flowgraph.c` |
| 6 | a code object | `Objects/codeobject.c` |
| 7 | a value | `Python/ceval.c` |

In scope: the order of the stages, the type and ownership of the artifact at each boundary, which stage may fail and how, the arena that holds stages 2 and 3, and the exact point at which compile time ends and run time begins.

Out of scope: how any one stage does its work. The tokenizer's state machine is `BP-TOKENIZER`, the grammar and its backtracking are `BP-PARSER`, the scope rules are `BP-SYMTABLE`, the instruction selection is `BP-CODEGEN`, the optimizer passes are `BP-CFG`, the encoding of a code object is `BP-CODEOBJECT`, and the eval loop is `BP-EVAL`. This blueprint says a symbol table exists before code generation starts and that code generation reads it. It does not say what is in it.

The boundary with `BP-MAP` is that everything here assumes an initialized runtime, an interpreter and a bound thread state.

The pipeline is not a fixed line. Stages 1 and 2 are interleaved: the parser pulls tokens on demand rather than receiving a finished list, and section 4 states what that does and does not allow. Stages 4, 5 and 6 run once per code unit, and a module containing a function runs them twice, innermost first.

## 2. Data structures

### 2.1 The compile time arena

Stages 2 and 3 allocate into an arena rather than onto the heap individually, and the whole arena is released in one call once a code object exists. Nothing produced by those stages may outlive the arena.

An arena is created before parsing and freed on every exit path, including the failing ones. `Python/pythonrun.c:1556-1590@v3.15.0rc1#_Py_CompileString` shows all four exits freeing it.

### 2.2 `mod_ty`, the tree

The tree is a tagged union generated from `Parser/Python.asdl:4-9@v3.15.0rc1#mod`. Its four top level kinds decide what the rest of the pipeline does.

| Kind | Source of it | Effect downstream |
|---|---|---|
| `Module` | `compile(src, f, "exec")` | A sequence of statements. The code object returns `None`. |
| `Interactive` | `compile(src, f, "single")` | Like `Module`, but each top level expression statement also prints. |
| `Expression` | `compile(src, f, "eval")` | A single expression. The code object returns its value rather than `None`. |
| `FunctionType` | the `func_type` mode | A signature only, used by type checkers. |

The `Expression` case is the one that changes generated code rather than just parsing, and section 3.5 is where that happens.

Tree nodes carry a source location of four integers: start line, start column, end line, end column. Every later stage that reports an error to the user reads them, and a code object's line table is derived from them, so a reimplementation that keeps only a line number loses tier A behaviour.

### 2.3 `PyCompilerFlags`

One `int` of flags plus a feature version, carried through every stage. Two bits change the shape of the pipeline rather than the code.

`PyCF_ONLY_AST` stops the pipeline after stage 2 and returns the tree as Python objects. `PyCF_OPTIMIZED_AST` combined with it decides whether the tree that comes back has been through constant folding first. The `__future__` bits are merged in from the tree itself, since a `from __future__ import` statement is discovered by parsing and then changes how the rest of the same file compiles.

### 2.4 `optimize`

An `int` with three meaningful values and one sentinel. `0` keeps assertions and docstrings, `1` drops assertions, `2` drops assertions and docstrings, and `-1` means take the value from the interpreter configuration rather than the caller. It is a parameter rather than a global because `compile()` exposes it, so two code objects in one process can disagree about it.

### 2.5 `struct symtable`

Built from the tree in one pass over the whole module, before any code is generated for any part of it. It is not incremental, and the reason is INV-PIPELINE-004 below.

### 2.6 `PyCodeObject`

The one artifact that crosses out of compile time. It is a Python object with a refcount, unlike everything in stages 1 to 5, and it is immutable. `BP-CODEOBJECT` specifies its fields; what matters here is that once it exists, no token, tree node, symbol table or graph is reachable from it.

## 3. Algorithms

### 3.1 `compile_source`

**CPython:** `Python/pythonrun.c:1556-1590@v3.15.0rc1#_Py_CompileString`
**Precondition:** a bound thread state, `str` is NUL terminated source, `start` is one of the four start rules
**Postcondition:** a new reference to a code object, or to an AST object when `PyCF_ONLY_AST` is set
**Complexity:** roughly linear in source length, with the exceptions in section 6
**Fails:** returns NULL, sets an error

```
func compile_source(str: *char, filename: *PyObject, start: int,
                    flags: *CompilerFlags, optimize: int) -> *PyObject:
    if not is_valid_start_rule(start):
        return NULL
    let arena: *Arena = arena_new()
    if arena == NULL:
        return NULL
    let mod: *Mod = parse_string(str, filename, start, flags, arena)   # stages 1 and 2
    if mod == NULL:
        arena_free(arena)
        return NULL
    if flags != NULL and (flags->cf_flags & ONLY_AST) != 0:
        let syntax_check_only: bool = (flags->cf_flags & OPTIMIZED_AST) == 0
        if ast_preprocess(mod, filename, flags, optimize, arena, syntax_check_only) < 0:
            arena_free(arena)
            return NULL
        let result: *PyObject = ast_to_python_objects(mod)
        arena_free(arena)
        return result
    let co: *PyCodeObject = compile_tree(mod, filename, flags, optimize, arena)  # stages 3 to 6
    arena_free(arena)
    return cast(*PyObject, co)
```

The arena is freed on all four paths and never conditionally. That is the whole memory story for stages 1 to 5, and it is why none of those stages needs its own cleanup on error.

### 3.2 `next_token`

**CPython:** `Parser/lexer/lexer.c:1626-1635@v3.15.0rc1#_PyTokenizer_Get`
**Precondition:** `tok` is an initialized tokenizer state
**Postcondition:** `token` is filled in, the return value is the token type
**Complexity:** O(length of the token), amortized O(1) per source byte
**Fails:** returns `ERRORTOKEN`, with the reason in `tok->done`

```
func next_token(tok: *TokState, token: *Token) -> int:
    let result: int = tok_get(tok, token)
    if tok->decoding_erred:
        result = ERRORTOKEN
        tok->done = E_DECODE
    return result
```

A decoding failure is turned into a token type rather than reported separately, so the parser only ever has one kind of failure to handle. This is a contract the pipeline depends on and not an implementation detail.

### 3.3 `run_parser`

**CPython:** `Parser/pegen.c:938-971@v3.15.0rc1#_PyPegen_run_parser`
**Precondition:** `p` is a parser holding a tokenizer, at level 0
**Postcondition:** a tree allocated in the arena, or NULL with a `SyntaxError` set
**Complexity:** linear in practice, but see section 6.3
**Fails:** returns NULL, sets an error

```
func run_parser(p: *Parser) -> *Mod:
    let res: *Mod = parse(p)
    if res != NULL and an_error_is_set():
        return NULL              # a result plus a pending error is a failure
    if res == NULL:
        if p->flags has ALLOW_INCOMPLETE_INPUT and at_end_of_source(p):
            clear_error()
            return raise_error(p, IncompleteInputError, "incomplete input")
        if an_error_is_set() and the_error_is_not(SyntaxError):
            return NULL          # a MemoryError, say, is not the parser's to improve on
        let last_token: *Token = p->tokens[p->fill - 1]
        reset_parser_state_for_error_pass(p)
        parse(p)                 # second pass, invalid_* rules now active
        set_syntax_error(p, last_token)
        return NULL
    return res
```

The two pass structure is the important part. The first pass is fast and reports nothing useful, and the second pass reparses the same input with slower rules whose only job is to produce a better message. A reimplementation is free to do it differently, but the messages are tier A, so whatever it does has to end up at the same text and the same location.

`IncompleteInputError` rather than `SyntaxError` is what lets a REPL know to ask for another line instead of complaining.

### 3.4 `build_symtable`

**CPython:** `Python/symtable.c:415-445@v3.15.0rc1#_PySymtable_Build`
**Precondition:** `mod` is a complete tree, `filename` is not NULL, a thread state exists
**Postcondition:** a symbol table with one entry per scope in the module
**Complexity:** O(nodes in the tree)
**Fails:** returns NULL, sets an error

```
func build_symtable(mod: *Mod, filename: *PyObject, future: *FutureFeatures) -> *Symtable:
    let st: *Symtable = symtable_new()
    if st == NULL or filename == NULL:
        free_symtable(st)
        return NULL
    st->st_filename = filename
    incref filename
    st->st_future = future
    if current_thread_state() == NULL:
        free_symtable(st)
        return NULL
    enter_block(st, "top", ModuleBlock, mod)
    for each stmt in mod->body:
        visit_stmt(st, stmt)          # first pass, records every binding and every use
    exit_block(st)
    analyze_blocks(st)                # second pass, resolves each name to a scope
    return st
```

Two passes, and they cannot be merged. The first records what happens; the second decides what each name means. A `global` statement at the bottom of a function changes the meaning of an assignment at the top of it, so no single forward pass can be correct.

### 3.5 `compile_tree`

**CPython:** `Python/compile.c:1526-1540@v3.15.0rc1#_PyAST_Compile` and `Python/compile.c:892-907@v3.15.0rc1#compiler_mod`
**Precondition:** no exception is set, `mod` is in `arena`
**Postcondition:** a new reference to a code object
**Complexity:** O(nodes) for generation, see 3.6 for the rest
**Fails:** returns NULL, sets an error

```
func compile_tree(mod: *Mod, filename: *PyObject, flags: *CompilerFlags,
                  optimize: int, arena: *Arena) -> *PyCodeObject:
    let c: *Compiler = new_compiler(mod, filename, flags, optimize, arena)
    # new_compiler merges __future__ flags out of the tree, resolves optimize == -1
    # against the configuration, folds constants, and calls build_symtable
    if c == NULL:
        return NULL
    let add_none: bool = mod->kind != Expression_kind
    let co: *PyCodeObject = NULL
    if codegen(c, mod) >= 0:
        co = optimize_and_assemble(c, add_none)
    if c->u != NULL:
        exit_scope(c)
    free_compiler(c)
    return co
```

`add_none` is the whole difference between `eval` and `exec` at the code generation level. An `Expression` leaves its value on the stack and returns it; everything else has a `return None` appended, which is why a module's code object evaluates to `None` and why a function with no `return` does too.

### 3.6 `optimize_and_assemble_unit`

**CPython:** `Python/compile.c:1460-1498@v3.15.0rc1#optimize_and_assemble_code_unit`
**Precondition:** `u` is a finished code unit holding an instruction sequence and its metadata
**Postcondition:** a new reference to a code object for this one unit
**Complexity:** O(instructions), with the graph passes each linear in blocks
**Fails:** returns NULL, sets an error

```
func optimize_and_assemble_unit(u: *CompilerUnit, const_cache: *PyObject,
                                code_flags: int, filename: *PyObject) -> *PyCodeObject:
    let consts: *PyObject = consts_dict_keys_inorder(u->u_metadata.u_consts)
    if consts == NULL:
        return NULL
    let g: *CfgBuilder = cfg_from_instruction_sequence(u->u_instr_sequence)
    if g == NULL:
        decref consts
        return NULL
    let nlocals: int = size_of(u->u_metadata.u_varnames)
    let nparams: int = size_of(u->u_ste->ste_varnames)
    if optimize_cfg(g, consts, const_cache, nlocals, nparams,
                    u->u_metadata.u_firstlineno) < 0:
        decref consts
        free_cfg(g)
        return NULL
    let stackdepth: int = 0
    let nlocalsplus: int = 0
    let optimized: InstrSequence = empty_instr_sequence()
    if cfg_to_instruction_sequence(g, &u->u_metadata, &stackdepth,
                                   &nlocalsplus, &optimized) < 0:
        decref consts
        free_cfg(g)
        return NULL
    let co: *PyCodeObject = assemble(&u->u_metadata, const_cache, consts,
                                     stackdepth, &optimized, nlocalsplus,
                                     code_flags, filename)
    decref consts
    free_cfg(g)
    return co
```

The round trip is deliberate: a linear instruction sequence becomes a graph, the graph is optimized, and it is flattened back to a linear sequence before assembly. The stack depth and the count of locals plus cells plus free variables are computed during the flattening, which is why they are outputs of that step rather than inputs to it.

This is the last function in which anything is mutable. `assemble` (`Python/assemble.c:779-802@v3.15.0rc1#_PyAssemble_MakeCodeObject`, then `Objects/codeobject.c:715-718@v3.15.0rc1#_PyCode_New`) produces the immutable object, and stage 6 is over.

### 3.7 `eval_code`

**CPython:** `Python/ceval.c:661-690@v3.15.0rc1#PyEval_EvalCode`
**Precondition:** `co` is a code object, `globals` is a dict
**Postcondition:** a new reference to the value the code produced
**Complexity:** unbounded
**Fails:** returns NULL, sets an error

```
func eval_code(co: *PyObject, globals: *PyObject, locals: *PyObject) -> *PyObject:
    let tstate: *PyThreadState = current_thread_state()
    if locals == NULL:
        locals = globals
    let builtins: *PyObject = load_builtins_from_globals(globals)
    if builtins == NULL:
        return NULL
    let desc: FrameConstructor = {
        globals: globals, builtins: builtins,
        name: co->co_name, qualname: co->co_name, code: co,
        defaults: NULL, kwdefaults: NULL, closure: NULL
    }
    let func: *PyFunctionObject = function_from_constructor(&desc)
    decref builtins
    if func == NULL:
        return NULL
    let res: *PyObject = eval_vector(tstate, func, locals, NULL, 0, NULL)
    decref func
    return res
```

A code object is not callable on its own. Running one means building a function around it first, because the frame needs globals, builtins and a closure, and a code object holds none of those. This is the stage 6 to stage 7 contract, and getting it wrong is the most common way a reimplementation ends up unable to support closures later.

## 4. Invariants

**INV-PIPELINE-001.** The stages run in the order 1 to 7 for any one code unit. No stage reads an artifact from a later stage.

**INV-PIPELINE-002.** Stages 1 and 2 are interleaved rather than sequential. The parser requests tokens as it needs them, and a token is produced at most once and is then owned by the parser. No stage may assume a complete token list exists.

**INV-PIPELINE-003.** Everything produced by stages 1 through 5 lives in the arena or in structures freed with the compiler, and none of it is reachable from the code object. After `arena_free` returns, the code object is fully self contained.

**INV-PIPELINE-004.** The symbol table for a scope is complete before any instruction is generated for that scope. Code generation only reads it.

**INV-PIPELINE-005.** Stages 4, 5 and 6 run once per code unit, and a nested unit completes all three before its enclosing unit reaches stage 6. A nested code object is therefore a constant in its parent's `co_consts`.

**INV-PIPELINE-006.** A failing stage sets exactly one exception and returns the failure sentinel. It does not run the next stage, and it does not leave a half built artifact reachable.

**INV-PIPELINE-007.** A code object is immutable once created. No stage 7 operation writes to the fields produced by stage 6, and the adaptive bytecode that specialization writes to is not one of them.

**INV-PIPELINE-008.** Every stage past 2 that reports an error to the user reports a location taken from a tree node, and that location is the one the tokenizer recorded.

**INV-PIPELINE-009.** `optimize` and the `__future__` flags are fixed before stage 3 begins and do not change for the rest of the compilation of that module.

**INV-PIPELINE-010.** Compile time ends when the code object is returned. Nothing after that point can observe the source text except through what stage 6 wrote down, which is `co_filename`, `co_linetable` and the constants.

## 5. Observable behaviour

This is a tier A blueprint because ordinary Python code depends on almost all of it.

`compile(source, filename, mode)` exposes stages 1 to 6 directly, with `mode` selecting the start rule from 2.2 and therefore the tree kind. Its return value is a code object, and `exec` and `eval` on that value are stage 7.

`compile(source, filename, mode, flags=ast.PyCF_ONLY_AST)` stops after stage 2 and is what the `ast` module is built on. That the tree comes back before any symbol table exists is observable, and it is why `ast` can parse code with names that would never resolve.

`SyntaxError` carries `filename`, `lineno`, `offset`, `end_lineno`, `end_offset` and `text`. All five come from the four integers in 2.2, and programs format them. The message text is also depended on by test suites and by teaching material, which is why the second parser pass in 3.3 exists.

`_IncompleteInputError` is how the REPL tells "not finished" from "wrong". It is only raised when the caller passes `PyCF_ALLOW_INCOMPLETE_INPUT`, which is `0x4000`, and `codeop` sets it together with `PyCF_DONT_IMPLY_DEDENT` and catches the result. Without the flag the same input is an ordinary `SyntaxError` or `IndentationError`. A reimplementation that offers no way to ask for the distinction cannot host an interactive prompt.

The `symtable` module exposes stage 3 as Python objects, so the scope decision for every name is readable without running anything.

`dis` exposes stage 6, and the fact that the code object for a nested function is in the enclosing one's `co_consts` is exactly INV-PIPELINE-005 being observable.

`-O` and `-OO` change `optimize` per 2.4, and their effect on `assert` statements and on `__doc__` is observable and is depended on.

A module's code object evaluating to `None` and an `eval` compiled code object evaluating to a value is the `add_none` decision in 3.5, and it is tier A.

Warnings raised during compilation, such as `SyntaxWarning` for a comparison to a literal, happen at compile time rather than run time. A program can see this by compiling a string and catching the warning without ever running the result.

What is not observable: the instruction sequence before optimization, the control flow graph, the arena, the number of parser passes, and every intermediate in stages 4 and 5. A reimplementation may replace all of it.

## 6. Edge cases and error paths

### 6.1 Empty and near empty input

Empty source compiles to a code object that returns `None`. A source that is only a comment does the same. A source that is only whitespace does the same. None of these is a `SyntaxError`, and a tokenizer that emits nothing at all rather than a `NEWLINE` and an `ENDMARKER` will make the parser disagree.

### 6.2 A NUL byte in the source

`compile("x = 1\0", "<s>", "exec")` raises `SyntaxError` with the message "source code string cannot contain null bytes", because the buffer is handled as a NUL terminated string and the check is done before the tokenizer starts. It is an implementation artifact that became documented behaviour, and it is tier A now regardless of how it got there.

### 6.3 Deeply nested source

There are three separate depth guards, they fire at different stages, and none of them raises the exception a reader would guess.

The tokenizer counts open brackets against `MAXLEVEL`, which is 200 (`Parser/lexer/state.h:6-8@v3.15.0rc1#MAXLEVEL`), and raises `SyntaxError` with "too many nested parentheses" at the 201st (`Parser/lexer/lexer.c:1300-1310@v3.15.0rc1#MAXLEVEL`). Confirmed by compiling 500 nested parentheses.

The tokenizer counts indentation levels against `MAXINDENT`, which is 100, and raises `IndentationError` with "too many levels of indentation" (`Parser/lexer/lexer.c:578-590@v3.15.0rc1#MAXINDENT`). Confirmed by compiling 120 nested `if` statements, which reports at line 101. There is a third limit of 150 on f-string nesting in the same header.

The parser has its own stack depth guard, and exceeding it raises `MemoryError` with "Parser stack overflowed" rather than `RecursionError` (`Parser/pegen_errors.c:410-416@v3.15.0rc1#_Pypegen_stack_overflow`). Confirmed by compiling 20000 stacked unary minus operators, which is deep nesting that uses no brackets and so gets past the first guard.

Compilation does not consume the `sys.setrecursionlimit` budget. Setting the limit to 200 and then compiling an expression 300 levels deep succeeds, so a port must not implement these guards by reusing the run time recursion counter.

The stated linear complexity in 3.3 assumes the grammar's memoization is working. A PEG parser without it is exponential on some inputs, so the memo table is a correctness requirement here rather than an optimization.

### 6.4 A result with a pending exception

3.3 discards a successful parse when an exception is already set. This case is real: an allocation failure deep in a rule can be recovered from locally and leave a `MemoryError` set while the rule above still returns a node. Treating that as success produces a tree built from partly failed allocations. Any stage that can recover internally needs the same check.

### 6.5 The second parser pass failing to produce an error

If the error pass in 3.3 somehow succeeds where the first pass failed, the code still returns NULL and still sets a syntax error from the recorded last token. The pipeline never returns "no tree and no exception", per INV-PIPELINE-006.

### 6.6 `__future__` discovered late

A `from __future__ import annotations` is found by parsing, which is after the tokenizer has already run, and it changes how the rest of the file compiles. This is why 2.3 has the flags merged in `new_compiler` rather than passed in from the caller. A `__future__` import that is not at the top of the file is a `SyntaxError`, which is what keeps this from needing a second compilation pass.

### 6.7 An argument too large for one instruction

An instruction's argument is one byte, and a larger value is encoded as a chain of `EXTENDED_ARG` instructions before it. Stage 5 has to reach a fixed point, because inserting an `EXTENDED_ARG` moves every jump target after it, which can make another jump need an `EXTENDED_ARG` of its own. A single pass is not correct.

### 6.8 Allocation failure mid pipeline

Every stage's failure path is the arena free in 3.1. There is no partial cleanup anywhere in stages 1 to 5, and adding some would be a bug rather than an improvement, since it would free arena memory twice.

### 6.9 Accidental behaviour

`fc_qualname` is set from `co_name` in 3.7 rather than from a qualified name, because `PyEval_EvalCode` has no enclosing scope to build one from. Anything reading `__qualname__` off a function built this way gets the plain name. That is a consequence of the entry point rather than a decision.

The exact set of constants in `co_consts` and their order is not specified anywhere, and it changes between versions. `dis` output is stable enough to teach from and is not stable enough to assert on across versions.

## 7. Interactions

`BP-MAP` provides the thread state that 3.4 and 3.7 both require, and the recursion limit that 6.3 depends on.

`BP-TOKENIZER` must satisfy INV-PIPELINE-002, which means it has to be a pull interface and not a batch one. A tokenizer written to produce a list first will work for `tokenize` and will not work for the parser's error recovery, which needs to reset and pull again.

`BP-SYMTABLE` must satisfy INV-PIPELINE-004, meaning it may not be computed lazily per name.

`BP-CODEGEN` and `BP-CFG` are separated by the instruction sequence in 3.6, and that boundary exists so the optimizer never sees a tree. Anything the optimizer needs must be in the sequence or in the metadata.

`BP-CODEOBJECT` owns everything after the assemble call in 3.6, and INV-PIPELINE-003 is the contract it relies on to be able to say a code object is self contained.

`BP-EVAL` starts at 3.7 and depends on INV-PIPELINE-007, since the eval loop treats the non adaptive parts of a code object as constant and caches derived values off it.

`BP-GC` interacts only through the code object, since nothing in stages 1 to 5 is a Python object with a refcount.

## 8. Conformance

| Claim | Held up by |
|---|---|
| The eight artifacts and seven transitions, INV-PIPELINE-001 | `lessons/t01-one-line-seven-stages`, which produces all eight for `answer = 6 * 7` |
| All eight stages reachable from Python alone | `lessons/t10-the-napkin`, the single cell that runs the whole pipeline |
| Tokens are pulled, not batched, INV-PIPELINE-002 | `lessons/t02-text-becomes-tokens` |
| Tree kind decides the return value, 3.5 | `lessons/t05-the-tree-becomes-bytecode`, `eval` against `exec` |
| The symbol table is complete before codegen, INV-PIPELINE-004 | `lessons/t04-names-get-scopes`, two identical lines compiling differently |
| A nested code object is a constant of its parent, INV-PIPELINE-005 | `lessons/t05-the-tree-becomes-bytecode` |
| Stack depth is computed at stage 5, 3.6 | `lessons/t06-reading-bytecode-fluently`, a Python reimplementation of the rule agreeing with `co_stacksize` on every code object in the standard library |
| The citations in sections 2 and 3 still point at the code they claim | `just citations`, on every change |

The conformance gaps, stated rather than hidden. The three depth limits in 6.3 and the null byte in 6.2 were each checked by hand against 3.15.0rc1 while this was written, and neither is covered by a test in this repository yet. 6.7 is not covered either, and 6.4 cannot be reached from Python at all without injecting an allocation failure. The `EXTENDED_ARG` fixed point in 6.7 is the one worth writing first, because it is reachable by generating a function with enough constants and it is a plausible thing for a port to get wrong.

## 9. Port notes

The arena in 2.1 is the single best thing to copy. Rust will want an arena crate or a `Vec` of nodes with indices instead of pointers, and Go can lean on the garbage collector, but in both cases keeping the "one lifetime for stages 1 to 5" rule is what makes INV-PIPELINE-003 easy to hold rather than something to keep checking.

Node indices beat pointers in both target languages. A tree of `Box<Node>` in Rust fights the borrow checker in every visitor, and a `Vec<Node>` plus `u32` indices does not. The same representation makes the ASDL generated code in 2.2 easier to generate, since the generator is emitting struct definitions and a tag enum either way.

The tree, the token type list, the opcode list and the grammar can all be generated from the upstream sources rather than typed. `Parser/Python.asdl` and `Grammar/python.gram:841-844@v3.15.0rc1` are the two inputs, and writing a generator for them early is much cheaper than transcribing them once and then chasing every upstream change by hand.

The two pass parser error strategy in 3.3 is worth deferring. A port can start with one pass and poor messages, get the whole pipeline working, and add the error pass later. It is the only part of this blueprint that can be left as a stub without anything downstream noticing, because nothing but the message text depends on it.

The three depth guards in 6.3 have to be counted deliberately rather than inherited from the host. Go's growable stacks mean a natural recursive descent implementation will not fall over anywhere near where CPython does, and Rust's will fall over by aborting rather than by raising. Two of the three limits are plain integers in a header and cost nothing to copy. The parser's own guard is the one that needs designing, and starting with a counter in place is much cheaper than adding one to every rule later.

Interleaving stages 1 and 2 per INV-PIPELINE-002 means the tokenizer cannot be an iterator that owns the loop. In Rust that is a pull based struct with a `next` method and a lookahead buffer, and in Go it is the same rather than a channel, because the parser needs to reset the tokenizer's position for the error pass and a channel cannot be rewound.
