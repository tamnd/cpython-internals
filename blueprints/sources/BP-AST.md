# BP-AST: the abstract syntax tree

**Covers:** `Parser/Python.asdl`, `Python/Python-ast.c`, `Python/ast.c`, `Include/internal/pycore_ast.h` and `Include/internal/pycore_asdl.h`, at the pinned tag
**Lesson:** T03, tokens become a tree
**Status:** partial
**Compatibility tier:** B

## 1. Purpose and scope

This blueprint specifies the shape of the tree the parser produces and the compiler consumes. It names every node kind, every field of every node kind, the order those fields are in, whether each one is required, optional or a sequence, and which node kinds carry source locations.

In scope: the node vocabulary, the C representation of it, how a node is allocated and how long it lives, what a Python program can see of all this through the `ast` module, and the structural checks CPython applies to a tree that was built by hand rather than parsed.

Out of scope: how the tree gets built. The grammar and the parser that matches it are `BP-PARSER`, and this blueprint says nothing about which source text produces which node. What happens to the tree afterwards is `BP-SYMTABLE` and `BP-CODEGEN`. The order the stages run in is `BP-PIPELINE`.

The table at the end of this section, the whole of section 2, the whole of section 5 and the whole of section 8 are generated from `Parser/Python.asdl` by `bpc`, the same file CPython generates its own node structures, its C constructors and its Python classes from. They are not typed by anybody and they are not proofread by anybody. Everything else in this document is written by hand, including the paragraphs above, because where this subsystem stops and `BP-PARSER` starts is not in the grammar and never will be. A generated table cannot be one field out of date, which is the way a hand written one goes wrong: correct on the day it is written, wrong the first time upstream adds a field, and nobody finds out because a reader who trusted the table has no reason to check it.

The generator is `Parser/asdl_c.py:1-2@v3.15.0rc1`, run from the `regen-ast` rule at `Makefile.pre.in:2056-2072@v3.15.0rc1`, which writes three files: the node structures, the per interpreter state that holds the Python classes, and the C source that builds both. Everything this blueprint describes is downstream of one 154 line grammar file.

<!-- bpc: overview -->

## 2. Data structures

Every node kind in the grammar becomes one C struct, one Python class and one constructor function. This section lists what the grammar says. How that becomes C is here, and the tables below are the specification of what a port has to build.

### 2.0.1 The C shape of a node

A sum type becomes a struct holding a `kind` enum and a union of one anonymous struct per constructor, so `struct _stmt` at `Include/internal/pycore_ast.h:196-207@v3.15.0rc1#_stmt` has a `kind` of `FunctionDef_kind` and a `v.FunctionDef` holding that constructor's seven fields. A product type has no `kind` and no union, because there is nothing to switch on.

The attributes listed for a type sit outside the union, once, rather than being repeated in each arm. That is what makes `node->lineno` readable without knowing which kind of statement it is, and it is the reason attributes and fields are separate concepts rather than a naming convention.

A field whose type is one of the four ASDL built ins becomes a `PyObject *` for `identifier`, `string` and `constant`, and a plain `int` for `int`. A field whose type is another node type becomes a pointer to that node's struct. An optional field is the same pointer and may be `NULL`. There is no separate tag saying whether an optional field is present.

### 2.0.2 Sequences

A sequence field is a pointer to an `asdl_seq`, which is a length and an array of pointers laid out inline after it. The header is two words, at `Include/internal/pycore_asdl.h:24-26@v3.15.0rc1#_ASDL_SEQ_HEAD`, and one typed variant is generated per element type by the macro at `Include/internal/pycore_asdl.h:52-74@v3.15.0rc1#GENERATE_ASDL_SEQ_CONSTRUCTOR`.

The length and the elements are read through macros rather than directly, and `asdl_seq_LEN` at `Include/internal/pycore_asdl.h:83@v3.15.0rc1#asdl_seq_LEN` reports zero for a `NULL` sequence. A port that represents a sequence as a growable array gets this for free. A port that distinguishes an absent list from an empty one has invented a state CPython does not have.

Sequences are allocated at their final length and never grown. The parser knows how many children it matched before it builds the node, so there is no append path and no capacity field.

### 2.0.3 Lifetime

Every node and every sequence is allocated from the compile time arena, through `_PyArena_Malloc` at `Include/internal/pycore_pyarena.h:56@v3.15.0rc1#_PyArena_Malloc`, and nothing is freed individually. The whole tree goes away in one call when the arena is released, which happens once a code object exists.

This is why no node has a destructor and why nothing in the tree is reference counted except the `PyObject *` fields, which the arena holds a reference to on the tree's behalf. A port that allocates nodes individually has to answer a question CPython never asks: who owns a subtree that was built and then discarded when a parser alternative failed. The arena's answer is that nobody does and it does not matter.

<!-- bpc: nodes -->

## 3. Algorithms

There are only three algorithms here, and two of them are generated one per node kind. That is the honest shape of this subsystem: it is a data definition with a small amount of machinery around it.

### 3.1 `make_node`

**CPython:** `Python/Python-ast.c:7057-7089@v3.15.0rc1#_PyAST_FunctionDef`
**Precondition:** `arena` is the arena that will own the whole tree, every required field is non NULL
**Postcondition:** a node in the arena, with `kind` set and every field stored
**Complexity:** O(1)
**Fails:** returns NULL, sets an error

One of these exists per constructor and they are all the same shape. `FunctionDef` is the example because it has all three kinds of field.

```
func make_FunctionDef(name: *PyObject, args: *Arguments,
                      body: *[*Stmt], decorator_list: *[*Expr],
                      returns: *Expr, type_comment: *PyObject,
                      type_params: *[*TypeParam],
                      lineno: int, col_offset: int,
                      end_lineno: int, end_col_offset: int,
                      arena: *Arena) -> *Stmt:
    # Required fields are checked one at a time and named in the message. Optional
    # fields are not checked, because NULL is what absent means for them.
    if name == NULL:
        set_error(ValueError, "field 'name' is required for FunctionDef")
        return NULL
    if args == NULL:
        set_error(ValueError, "field 'args' is required for FunctionDef")
        return NULL
    let p: *Stmt = cast(*Stmt, arena_malloc(arena, sizeof(Stmt)))
    if p == NULL:
        return NULL
    p->kind = FunctionDef_kind
    p->v.FunctionDef.name = name
    p->v.FunctionDef.args = args
    p->v.FunctionDef.body = body
    p->v.FunctionDef.decorator_list = decorator_list
    p->v.FunctionDef.returns = returns
    p->v.FunctionDef.type_comment = type_comment
    p->v.FunctionDef.type_params = type_params
    p->lineno = lineno
    p->col_offset = col_offset
    p->end_lineno = end_lineno
    p->end_col_offset = end_col_offset
    return p
```

Nothing is copied and nothing is incref'd. The caller hands over pointers it got from the arena and the node keeps them. A sequence field is stored as given, including `NULL`, which reads as empty everywhere downstream.

Note what is missing: there is no check that a sequence is non empty, no check that a field holds the right kind of node, and no check that the location makes sense. Those are section 3.3's job and they only run on a tree that came from Python rather than from the parser.

### 3.2 `new_sequence`

**CPython:** `Include/internal/pycore_asdl.h:52-74@v3.15.0rc1#GENERATE_ASDL_SEQ_CONSTRUCTOR`
**Precondition:** `size` is not negative, `arena` is the tree's arena
**Postcondition:** a sequence of exactly `size` slots, in the arena
**Complexity:** O(1), one arena allocation
**Fails:** returns NULL, sets `MemoryError`

```
func new_sequence(size: ssize, arena: *Arena) -> *Seq:
    if size < 0 or (size > 0 and cast(uint, size - 1) > SIZE_MAX / sizeof(*void)):
        set_error(MemoryError)
        return NULL
    let n: uint = 0
    if size > 0:
        n = sizeof(*Elem) * (size - 1)          # one slot is already in the header
    if n > SIZE_MAX - sizeof(Seq):
        set_error(MemoryError)
        return NULL
    n = n + sizeof(Seq)
    let seq: *Seq = cast(*Seq, arena_malloc(arena, n))
    if seq == NULL:
        set_error(MemoryError)
        return NULL
    memset(seq, 0, n)                           # every slot starts NULL
    seq->size = size
    seq->elements = cast(**void, seq->typed_elements)
    return seq
```

The two overflow checks are the whole reason this is a function and not a macro. A port on a 64 bit target where sizes come from a parser will never reach either of them from real source, and should keep them anyway, because the size is attacker controlled the moment a program calls `compile` on something it downloaded.

The `memset` is load bearing. A caller allocates a sequence and then fills it, and anything it has not filled yet has to be `NULL` rather than whatever was in the arena, because a partly filled sequence is what the parser is holding when an alternative fails.

The last line is the one to read twice. The struct has two views of the same memory: `typed_elements`, declared with the element type so `asdl_seq_GET` returns something the compiler knows about, and `elements`, a `void **` for the generic code that walks a sequence without caring what is in it. Setting one to point at the other is what makes both work, and the two are aliases and not copies. In a language with generics, one typed slice replaces both and the line disappears.

### 3.3 `validate_tree`

**CPython:** `Python/ast.c:1049-1076@v3.15.0rc1#_PyAST_Validate`
**Precondition:** `mod` is a tree, from the parser or built by a Python program
**Postcondition:** returns 1 when the tree can be compiled, 0 with an error set when it cannot
**Complexity:** O(nodes)
**Fails:** returns 0, sets `ValueError` or `TypeError`

```
func validate_tree(mod: *Mod) -> int:
    if mod->kind == Module_kind:
        return validate_statements(mod->v.Module.body)
    if mod->kind == Interactive_kind:
        return validate_statements(mod->v.Interactive.body)
    if mod->kind == Expression_kind:
        return validate_expression(mod->v.Expression.body, Load)
    if mod->kind == FunctionType_kind:
        if validate_expressions(mod->v.FunctionType.argtypes, Load, false) == 0:
            return 0
        return validate_expression(mod->v.FunctionType.returns, Load)
    set_error(SystemError, "impossible module node")
    return 0
```

The rules it applies below the top are structural and are not in the grammar. The one that catches most hand built trees is that a body may not be empty, at `Python/ast.c:704-711@v3.15.0rc1#_validate_nonempty_seq` and applied by `Python/ast.c:722-726@v3.15.0rc1#validate_body`. `stmt* body` in the grammar allows zero statements and `FunctionDef` with zero statements is rejected here, which is the clearest case of the grammar being necessary and not sufficient.

Recursion is bounded by the interpreter's recursion limit rather than by a depth counter of its own, through the macro at `Python/ast.c:13-18@v3.15.0rc1#ENTER_RECURSIVE`. A tree deep enough to overflow is refused with `RecursionError` rather than crashing.

## 4. Invariants

**INV-AST-001.** The order of a constructor's fields in section 2 is the order of `_fields` on the corresponding Python class, and the order that class takes positional arguments in. Reordering two fields of the same type is undetectable at the C level and changes the meaning of every positional construction in every program.

**INV-AST-002.** A required field is never `NULL` in a tree that has been validated. The constructor refuses to build the node, so a tree from the parser cannot violate this, and a tree from Python is checked before it is compiled.

**INV-AST-003.** An optional field may be `NULL` and that is the only representation of absence. There is no second flag and no sentinel node.

**INV-AST-004.** A sequence field is either a sequence or `NULL`, and `NULL` reads as length zero everywhere. An empty sequence and an absent one are not distinguishable and no code may try.

**INV-AST-005.** Every node and every sequence in one tree belongs to one arena, and no pointer into that tree outlives it. The `PyObject *` fields are the exception: the arena holds a reference to each of them and releases it when the arena goes.

**INV-AST-006.** Attributes are not fields. They are declared once per type, they appear on every constructor of that type, they are listed in `_attributes` rather than `_fields`, and they are not positional arguments.

**INV-AST-007.** A node kind name is unique across the whole grammar, so a name identifies a constructor without saying which type it belongs to. This is what lets the C code use one flat `Xxx_kind` enum per sum and one flat namespace of Python classes.

**INV-AST-008.** Every node kind of a type that carries the four location attributes has a start line and start column. The two end attributes are optional and may be absent on a tree built by hand.

**INV-AST-009.** Validation is not idempotent with construction. A tree that a constructor accepted may still fail validation, because the constructor checks required fields and validation checks structure.

## 5. Observable behaviour

<!-- bpc: observable -->

## 6. Edge cases and error paths

### 6.1 Building a node with fields missing

Omitting a field is allowed for some fields and not others, and which is which comes from the field's kind in section 2. The defaulting happens in `ast_type_init` at `Python/Python-ast.c:5266@v3.15.0rc1#ast_type_init`, in the block at `Python/Python-ast.c:5417-5446@v3.15.0rc1`.

An omitted optional field is `None`. An omitted sequence field is a new empty list. An omitted `expr_context` field is the `Load` singleton, which is a special case with no equivalent anywhere else in the grammar. An omitted field of any other kind is missing, and the constructor raises `TypeError` naming all of them at once, at `Python/Python-ast.c:5448-5459@v3.15.0rc1`.

So `ast.FunctionDef()` raises `TypeError` for `name` and `args` together, and `ast.FunctionDef(name="f", args=ast.arguments())` succeeds with `body` an empty list and `returns` set to `None`. The second one is a node that exists and cannot be compiled, which is section 6.2.

### 6.2 A tree that is valid by the grammar and rejected anyway

`stmt* body` permits zero statements. Every construct with a body rejects zero statements at validation time with `ValueError: empty body on FunctionDef`. The same applies to `Delete` with no targets, `Assign` with no targets, `With` with no items and `Match` with no cases.

A port that generates its node types from the grammar and stops there will accept trees CPython refuses. The grammar is the vocabulary and validation is the grammar of the vocabulary, and only one of the two is generated.

### 6.3 Depth

There is no limit on tree depth in the grammar or in the node structures. The limits are the parser's, and then the recursion limit during validation, symbol table construction and code generation. A tree deep enough raises `RecursionError` at whichever of those reaches it first, so the same program can fail at different stages depending on the recursion limit in force.

### 6.4 Allocation failure

Every constructor and every sequence allocation can fail and returns `NULL` with `MemoryError` set. There is no cleanup on that path and there does not need to be, because everything allocated so far is in the arena and the arena is freed by whoever created it. This is the single largest simplification the arena buys and it is worth keeping in a port.

### 6.5 A tree that came from Python

`PyAST_obj2mod` at `Python/Python-ast.c:18493-18499@v3.15.0rc1#PyAST_obj2mod` converts Python objects back into C nodes, and it is the only way a tree that the parser did not build gets into the compiler. It raises an audit event before it does anything else, because at that point a program is handing the compiler a structure that no source text produced.

Every type error a hand built tree can contain is caught here or in validation. A field holding the wrong kind of node, a string where an `identifier` belongs, a list where a single node belongs: all of them are conversion failures with a message naming the field.

The attributes are checked here too, and this is where INV-AST-008 is enforced rather than at construction time. `ast.Pass()` builds fine and has no `lineno`, and `compile` on a module containing it raises `TypeError: required field "lineno" missing from stmt`. `end_lineno` and `end_col_offset` are `int?` in the grammar and a node without them compiles, which is the difference between the two pairs and the reason only two of the four are declared optional.

### 6.6 The four builtin types

`identifier` and `string` are both `PyObject *` holding a `str`, and nothing at the C level tells them apart. `identifier` is interned and `string` is not, which matters for the speed of the symbol table lookups downstream rather than for correctness. `constant` is any Python object and is the one field type with no constraint at all, which is why `Constant.value` can hold anything a literal can produce. `int` is a C `int` and not a Python integer, so a field like `AnnAssign.simple` is a flag with a C sized range.

### 6.7 The two sequences whose slots can be empty

Two fields in the grammar are written `expr?*`, with both quantifiers. They are sequences, and the entries in them are allowed to be `None`. Everything else in the grammar is a sequence or optional, never both, so these two are worth naming.

`Dict` declares `expr?* keys` at `Parser/Python.asdl:66@v3.15.0rc1#Dict`. `keys` and `values` run in parallel, one slot per entry in the display, and a `None` key means the entry was a `**` unpacking with the mapping in `values`. So `{1: 2, **d}` parses to `keys=[Constant(1), None]` and `values=[Constant(2), Name('d')]`. There is no separate node for dictionary unpacking. The `None` is the node.

`arguments` declares `expr?* kw_defaults` at `Parser/Python.asdl:117@v3.15.0rc1#kw_defaults`. It runs in parallel with `kwonlyargs` rather than listing only the defaults that exist, so the default for `kwonlyargs[i]` is always `kw_defaults[i]`, and it is `None` when that argument has no default. `def f(*, a, b=1)` gives `kw_defaults=[None, Constant(1)]`. `defaults`, which covers the positional arguments, works the other way: it is right aligned against `args` and holds no gaps, because a positional argument with a default cannot be followed by one without.

This is easy to lose in a port, because `asdl.py` itself nearly loses it. `Field.seq` and `Field.opt` are set from the last quantifier only, so `expr?*` arrives with `seq` true and `opt` false, exactly like `expr*`. The `?` survives in `Field.quantifiers` and nowhere else. A port that reads `seq` and `opt` types both fields as plain lists of expressions, and then crashes on the first `{**d}` and the first keyword only argument without a default.

## 7. Interactions

`BP-PARSER` produces the tree and is the only producer other than a Python program calling `compile` on an `ast` object. It builds nodes bottom up with the constructors in section 3.1, into the arena it was given.

`BP-SYMTABLE` walks the tree once and reads names, and it depends on field order only through the field names, not their positions. It is the first consumer to reject trees that validation accepted, because scoping rules are not structural.

`BP-CODEGEN` walks the tree and reads the location attributes on every node to build the line table. INV-AST-008 is the one this depends on: a node with no start line produces a code object whose line table is wrong, and a wrong line table is only detectable in a traceback, which is the worst place to find out.

The `ast` module is the public face of everything here and is the reason this subsystem is tier B rather than tier D. `ast.parse`, `ast.dump`, `ast.NodeVisitor` and `ast.unparse` are all built on `_fields` and `_attributes` being exactly what section 5 says they are.

`BP-PIPELINE` fixes when the arena is created and freed, which is what makes INV-AST-005 hold in practice rather than by convention.

## 8. Conformance

<!-- bpc: conformance -->

## 9. Port notes

Generate the node types rather than typing them. The grammar file is 154 lines and it is stable across releases in the parts that matter, so a port that reads it produces the same 113 node kinds with the same field names in the same order, and stays right when the pin moves. A port that types them by hand is doing the one job in this subsystem that a machine does better.

In Go the natural shape is one interface per sum type and one struct per constructor, with a marker method. That gives type switches where CPython has a `kind` enum, and it loses nothing, because CPython's union is a closed set and so is the interface. The cost is that a nil interface value and an interface holding a nil pointer are different things, and optional fields are exactly where that bites. Use a pointer field and check for nil, never an interface.

In Rust the natural shape is one enum per sum type with a variant per constructor, which is closer to the C than Go gets and gives exhaustive matching for free. `Option<T>` for optional fields and `Vec<T>` for sequences map exactly, with one caveat: `Vec<T>` cannot be absent, and CPython's `NULL` sequence has to become an empty `Vec` at the boundary rather than an `Option<Vec<T>>`. Making that distinction representable is how INV-AST-004 gets violated by accident.

The arena is worth keeping in both. In Rust an arena crate or a `Vec` of nodes with index handles removes the lifetime problem that a tree of `Box`es creates during parsing, when a failed alternative discards a subtree. In Go the garbage collector already does this, so an arena buys allocation speed rather than correctness, and can be skipped until it is measured.

Validation cannot be generated and has to be written. It is a few hundred lines and it is the difference between a port that compiles the same programs CPython compiles and one that accepts trees CPython refuses. Start with the non empty body rule, which is the one every real program depends on without knowing it.

The location attributes are not optional in practice. A port that leaves them out has a working compiler and unusable tracebacks, and adding them afterwards means touching every constructor call in the parser.
