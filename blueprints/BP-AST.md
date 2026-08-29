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

<!-- bpc:begin overview -->
The grammar declares 19 types, 12 of them a choice between constructors and 7 of them a single fixed shape. Between them they describe 113 concrete node kinds with 198 fields, and 8 of the types carry source location attributes on every node.

The module header is at `Parser/Python.asdl:4@v3.15.0rc1#Python`.

| # | Type | Kind | Constructors | Fields | Attributes | Declared at |
|---|---|---|---|---|---|---|
| 1 | `mod` | sum | 4 | 6 | 0 | `Parser/Python.asdl:6@v3.15.0rc1#mod` |
| 2 | `stmt` | sum | 28 | 80 | 4 | `Parser/Python.asdl:11@v3.15.0rc1#stmt` |
| 3 | `expr` | sum | 29 | 63 | 4 | `Parser/Python.asdl:60@v3.15.0rc1#expr` |
| 4 | `expr_context` | sum | 3 | 0 | 0 | `Parser/Python.asdl:100@v3.15.0rc1#expr_context` |
| 5 | `boolop` | sum | 2 | 0 | 0 | `Parser/Python.asdl:102@v3.15.0rc1#boolop` |
| 6 | `operator` | sum | 13 | 0 | 0 | `Parser/Python.asdl:104@v3.15.0rc1#operator` |
| 7 | `unaryop` | sum | 4 | 0 | 0 | `Parser/Python.asdl:107@v3.15.0rc1#unaryop` |
| 8 | `cmpop` | sum | 10 | 0 | 0 | `Parser/Python.asdl:109@v3.15.0rc1#cmpop` |
| 9 | `comprehension` | product |  | 4 | 0 | `Parser/Python.asdl:111@v3.15.0rc1#comprehension` |
| 10 | `excepthandler` | sum | 1 | 3 | 4 | `Parser/Python.asdl:113@v3.15.0rc1#excepthandler` |
| 11 | `arguments` | product |  | 7 | 0 | `Parser/Python.asdl:116@v3.15.0rc1#arguments` |
| 12 | `arg` | product |  | 3 | 4 | `Parser/Python.asdl:119@v3.15.0rc1#arg` |
| 13 | `keyword` | product |  | 2 | 4 | `Parser/Python.asdl:123@v3.15.0rc1#keyword` |
| 14 | `alias` | product |  | 2 | 4 | `Parser/Python.asdl:127@v3.15.0rc1#alias` |
| 15 | `withitem` | product |  | 2 | 0 | `Parser/Python.asdl:130@v3.15.0rc1#withitem` |
| 16 | `match_case` | product |  | 3 | 0 | `Parser/Python.asdl:132@v3.15.0rc1#match_case` |
| 17 | `pattern` | sum | 8 | 14 | 4 | `Parser/Python.asdl:134@v3.15.0rc1#pattern` |
| 18 | `type_ignore` | sum | 1 | 2 | 0 | `Parser/Python.asdl:148@v3.15.0rc1#type_ignore` |
| 19 | `type_param` | sum | 3 | 7 | 4 | `Parser/Python.asdl:150@v3.15.0rc1#type_param` |
<!-- bpc:end overview -->

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

<!-- bpc:begin nodes -->
### 2.1 `mod`

A choice between 4 constructors, declared at `Parser/Python.asdl:6@v3.15.0rc1#mod`.

| Node | Order | Field | Type | Holds | Declared at |
|---|---|---|---|---|---|
| `Module` | 1 | `body` | `stmt` | sequence | `Parser/Python.asdl:6@v3.15.0rc1#Module` |
| `Module` | 2 | `type_ignores` | `type_ignore` | sequence |  |
| `Interactive` | 1 | `body` | `stmt` | sequence | `Parser/Python.asdl:7@v3.15.0rc1#Interactive` |
| `Expression` | 1 | `body` | `expr` | required | `Parser/Python.asdl:8@v3.15.0rc1#Expression` |
| `FunctionType` | 1 | `argtypes` | `expr` | sequence | `Parser/Python.asdl:9@v3.15.0rc1#FunctionType` |
| `FunctionType` | 2 | `returns` | `expr` | required |  |

### 2.2 `stmt`

A choice between 28 constructors, declared at `Parser/Python.asdl:11@v3.15.0rc1#stmt`.

Every `stmt` node also carries 4 attributes, which are not fields and are not part of the constructor's positional arguments.

| Attribute | Type | Holds |
|---|---|---|
| `lineno` | `int` | required |
| `col_offset` | `int` | required |
| `end_lineno` | `int` | optional |
| `end_col_offset` | `int` | optional |

| Node | Order | Field | Type | Holds | Declared at |
|---|---|---|---|---|---|
| `FunctionDef` | 1 | `name` | `identifier` | required | `Parser/Python.asdl:11@v3.15.0rc1#FunctionDef` |
| `FunctionDef` | 2 | `args` | `arguments` | required |  |
| `FunctionDef` | 3 | `body` | `stmt` | sequence |  |
| `FunctionDef` | 4 | `decorator_list` | `expr` | sequence |  |
| `FunctionDef` | 5 | `returns` | `expr` | optional |  |
| `FunctionDef` | 6 | `type_comment` | `string` | optional |  |
| `FunctionDef` | 7 | `type_params` | `type_param` | sequence |  |
| `AsyncFunctionDef` | 1 | `name` | `identifier` | required | `Parser/Python.asdl:14@v3.15.0rc1#AsyncFunctionDef` |
| `AsyncFunctionDef` | 2 | `args` | `arguments` | required |  |
| `AsyncFunctionDef` | 3 | `body` | `stmt` | sequence |  |
| `AsyncFunctionDef` | 4 | `decorator_list` | `expr` | sequence |  |
| `AsyncFunctionDef` | 5 | `returns` | `expr` | optional |  |
| `AsyncFunctionDef` | 6 | `type_comment` | `string` | optional |  |
| `AsyncFunctionDef` | 7 | `type_params` | `type_param` | sequence |  |
| `ClassDef` | 1 | `name` | `identifier` | required | `Parser/Python.asdl:18@v3.15.0rc1#ClassDef` |
| `ClassDef` | 2 | `bases` | `expr` | sequence |  |
| `ClassDef` | 3 | `keywords` | `keyword` | sequence |  |
| `ClassDef` | 4 | `body` | `stmt` | sequence |  |
| `ClassDef` | 5 | `decorator_list` | `expr` | sequence |  |
| `ClassDef` | 6 | `type_params` | `type_param` | sequence |  |
| `Return` | 1 | `value` | `expr` | optional | `Parser/Python.asdl:24@v3.15.0rc1#Return` |
| `Delete` | 1 | `targets` | `expr` | sequence | `Parser/Python.asdl:26@v3.15.0rc1#Delete` |
| `Assign` | 1 | `targets` | `expr` | sequence | `Parser/Python.asdl:27@v3.15.0rc1#Assign` |
| `Assign` | 2 | `value` | `expr` | required |  |
| `Assign` | 3 | `type_comment` | `string` | optional |  |
| `TypeAlias` | 1 | `name` | `expr` | required | `Parser/Python.asdl:28@v3.15.0rc1#TypeAlias` |
| `TypeAlias` | 2 | `type_params` | `type_param` | sequence |  |
| `TypeAlias` | 3 | `value` | `expr` | required |  |
| `AugAssign` | 1 | `target` | `expr` | required | `Parser/Python.asdl:29@v3.15.0rc1#AugAssign` |
| `AugAssign` | 2 | `op` | `operator` | required |  |
| `AugAssign` | 3 | `value` | `expr` | required |  |
| `AnnAssign` | 1 | `target` | `expr` | required | `Parser/Python.asdl:31@v3.15.0rc1#AnnAssign` |
| `AnnAssign` | 2 | `annotation` | `expr` | required |  |
| `AnnAssign` | 3 | `value` | `expr` | optional |  |
| `AnnAssign` | 4 | `simple` | `int` | required |  |
| `For` | 1 | `target` | `expr` | required | `Parser/Python.asdl:34@v3.15.0rc1#For` |
| `For` | 2 | `iter` | `expr` | required |  |
| `For` | 3 | `body` | `stmt` | sequence |  |
| `For` | 4 | `orelse` | `stmt` | sequence |  |
| `For` | 5 | `type_comment` | `string` | optional |  |
| `AsyncFor` | 1 | `target` | `expr` | required | `Parser/Python.asdl:35@v3.15.0rc1#AsyncFor` |
| `AsyncFor` | 2 | `iter` | `expr` | required |  |
| `AsyncFor` | 3 | `body` | `stmt` | sequence |  |
| `AsyncFor` | 4 | `orelse` | `stmt` | sequence |  |
| `AsyncFor` | 5 | `type_comment` | `string` | optional |  |
| `While` | 1 | `test` | `expr` | required | `Parser/Python.asdl:36@v3.15.0rc1#While` |
| `While` | 2 | `body` | `stmt` | sequence |  |
| `While` | 3 | `orelse` | `stmt` | sequence |  |
| `If` | 1 | `test` | `expr` | required | `Parser/Python.asdl:37@v3.15.0rc1#If` |
| `If` | 2 | `body` | `stmt` | sequence |  |
| `If` | 3 | `orelse` | `stmt` | sequence |  |
| `With` | 1 | `items` | `withitem` | sequence | `Parser/Python.asdl:38@v3.15.0rc1#With` |
| `With` | 2 | `body` | `stmt` | sequence |  |
| `With` | 3 | `type_comment` | `string` | optional |  |
| `AsyncWith` | 1 | `items` | `withitem` | sequence | `Parser/Python.asdl:39@v3.15.0rc1#AsyncWith` |
| `AsyncWith` | 2 | `body` | `stmt` | sequence |  |
| `AsyncWith` | 3 | `type_comment` | `string` | optional |  |
| `Match` | 1 | `subject` | `expr` | required | `Parser/Python.asdl:41@v3.15.0rc1#Match` |
| `Match` | 2 | `cases` | `match_case` | sequence |  |
| `Raise` | 1 | `exc` | `expr` | optional | `Parser/Python.asdl:43@v3.15.0rc1#Raise` |
| `Raise` | 2 | `cause` | `expr` | optional |  |
| `Try` | 1 | `body` | `stmt` | sequence | `Parser/Python.asdl:44@v3.15.0rc1#Try` |
| `Try` | 2 | `handlers` | `excepthandler` | sequence |  |
| `Try` | 3 | `orelse` | `stmt` | sequence |  |
| `Try` | 4 | `finalbody` | `stmt` | sequence |  |
| `TryStar` | 1 | `body` | `stmt` | sequence | `Parser/Python.asdl:45@v3.15.0rc1#TryStar` |
| `TryStar` | 2 | `handlers` | `excepthandler` | sequence |  |
| `TryStar` | 3 | `orelse` | `stmt` | sequence |  |
| `TryStar` | 4 | `finalbody` | `stmt` | sequence |  |
| `Assert` | 1 | `test` | `expr` | required | `Parser/Python.asdl:46@v3.15.0rc1#Assert` |
| `Assert` | 2 | `msg` | `expr` | optional |  |
| `Import` | 1 | `names` | `alias` | sequence | `Parser/Python.asdl:48@v3.15.0rc1#Import` |
| `Import` | 2 | `is_lazy` | `int` | optional |  |
| `ImportFrom` | 1 | `module` | `identifier` | optional | `Parser/Python.asdl:49@v3.15.0rc1#ImportFrom` |
| `ImportFrom` | 2 | `names` | `alias` | sequence |  |
| `ImportFrom` | 3 | `level` | `int` | optional |  |
| `ImportFrom` | 4 | `is_lazy` | `int` | optional |  |
| `Global` | 1 | `names` | `identifier` | sequence | `Parser/Python.asdl:51@v3.15.0rc1#Global` |
| `Nonlocal` | 1 | `names` | `identifier` | sequence | `Parser/Python.asdl:52@v3.15.0rc1#Nonlocal` |
| `Expr` | 1 | `value` | `expr` | required | `Parser/Python.asdl:53@v3.15.0rc1#Expr` |
| `Pass` |  | no fields |  |  | `Parser/Python.asdl:54@v3.15.0rc1#Pass` |
| `Break` |  | no fields |  |  | `Parser/Python.asdl:54@v3.15.0rc1#Break` |
| `Continue` |  | no fields |  |  | `Parser/Python.asdl:54@v3.15.0rc1#Continue` |

### 2.3 `expr`

A choice between 29 constructors, declared at `Parser/Python.asdl:60@v3.15.0rc1#expr`.

Every `expr` node also carries 4 attributes, which are not fields and are not part of the constructor's positional arguments.

| Attribute | Type | Holds |
|---|---|---|
| `lineno` | `int` | required |
| `col_offset` | `int` | required |
| `end_lineno` | `int` | optional |
| `end_col_offset` | `int` | optional |

| Node | Order | Field | Type | Holds | Declared at |
|---|---|---|---|---|---|
| `BoolOp` | 1 | `op` | `boolop` | required | `Parser/Python.asdl:60@v3.15.0rc1#BoolOp` |
| `BoolOp` | 2 | `values` | `expr` | sequence |  |
| `NamedExpr` | 1 | `target` | `expr` | required | `Parser/Python.asdl:61@v3.15.0rc1#NamedExpr` |
| `NamedExpr` | 2 | `value` | `expr` | required |  |
| `BinOp` | 1 | `left` | `expr` | required | `Parser/Python.asdl:62@v3.15.0rc1#BinOp` |
| `BinOp` | 2 | `op` | `operator` | required |  |
| `BinOp` | 3 | `right` | `expr` | required |  |
| `UnaryOp` | 1 | `op` | `unaryop` | required | `Parser/Python.asdl:63@v3.15.0rc1#UnaryOp` |
| `UnaryOp` | 2 | `operand` | `expr` | required |  |
| `Lambda` | 1 | `args` | `arguments` | required | `Parser/Python.asdl:64@v3.15.0rc1#Lambda` |
| `Lambda` | 2 | `body` | `expr` | required |  |
| `IfExp` | 1 | `test` | `expr` | required | `Parser/Python.asdl:65@v3.15.0rc1#IfExp` |
| `IfExp` | 2 | `body` | `expr` | required |  |
| `IfExp` | 3 | `orelse` | `expr` | required |  |
| `Dict` | 1 | `keys` | `expr` | sequence of optional | `Parser/Python.asdl:66@v3.15.0rc1#Dict` |
| `Dict` | 2 | `values` | `expr` | sequence |  |
| `Set` | 1 | `elts` | `expr` | sequence | `Parser/Python.asdl:67@v3.15.0rc1#Set` |
| `ListComp` | 1 | `elt` | `expr` | required | `Parser/Python.asdl:68@v3.15.0rc1#ListComp` |
| `ListComp` | 2 | `generators` | `comprehension` | sequence |  |
| `SetComp` | 1 | `elt` | `expr` | required | `Parser/Python.asdl:69@v3.15.0rc1#SetComp` |
| `SetComp` | 2 | `generators` | `comprehension` | sequence |  |
| `DictComp` | 1 | `key` | `expr` | required | `Parser/Python.asdl:70@v3.15.0rc1#DictComp` |
| `DictComp` | 2 | `value` | `expr` | optional |  |
| `DictComp` | 3 | `generators` | `comprehension` | sequence |  |
| `GeneratorExp` | 1 | `elt` | `expr` | required | `Parser/Python.asdl:71@v3.15.0rc1#GeneratorExp` |
| `GeneratorExp` | 2 | `generators` | `comprehension` | sequence |  |
| `Await` | 1 | `value` | `expr` | required | `Parser/Python.asdl:73@v3.15.0rc1#Await` |
| `Yield` | 1 | `value` | `expr` | optional | `Parser/Python.asdl:74@v3.15.0rc1#Yield` |
| `YieldFrom` | 1 | `value` | `expr` | required | `Parser/Python.asdl:75@v3.15.0rc1#YieldFrom` |
| `Compare` | 1 | `left` | `expr` | required | `Parser/Python.asdl:78@v3.15.0rc1#Compare` |
| `Compare` | 2 | `ops` | `cmpop` | sequence |  |
| `Compare` | 3 | `comparators` | `expr` | sequence |  |
| `Call` | 1 | `func` | `expr` | required | `Parser/Python.asdl:79@v3.15.0rc1#Call` |
| `Call` | 2 | `args` | `expr` | sequence |  |
| `Call` | 3 | `keywords` | `keyword` | sequence |  |
| `FormattedValue` | 1 | `value` | `expr` | required | `Parser/Python.asdl:80@v3.15.0rc1#FormattedValue` |
| `FormattedValue` | 2 | `conversion` | `int` | required |  |
| `FormattedValue` | 3 | `format_spec` | `expr` | optional |  |
| `Interpolation` | 1 | `value` | `expr` | required | `Parser/Python.asdl:81@v3.15.0rc1#Interpolation` |
| `Interpolation` | 2 | `str` | `constant` | required |  |
| `Interpolation` | 3 | `conversion` | `int` | required |  |
| `Interpolation` | 4 | `format_spec` | `expr` | optional |  |
| `JoinedStr` | 1 | `values` | `expr` | sequence | `Parser/Python.asdl:82@v3.15.0rc1#JoinedStr` |
| `TemplateStr` | 1 | `values` | `expr` | sequence | `Parser/Python.asdl:83@v3.15.0rc1#TemplateStr` |
| `Constant` | 1 | `value` | `constant` | required | `Parser/Python.asdl:84@v3.15.0rc1#Constant` |
| `Constant` | 2 | `kind` | `string` | optional |  |
| `Attribute` | 1 | `value` | `expr` | required | `Parser/Python.asdl:87@v3.15.0rc1#Attribute` |
| `Attribute` | 2 | `attr` | `identifier` | required |  |
| `Attribute` | 3 | `ctx` | `expr_context` | required |  |
| `Subscript` | 1 | `value` | `expr` | required | `Parser/Python.asdl:88@v3.15.0rc1#Subscript` |
| `Subscript` | 2 | `slice` | `expr` | required |  |
| `Subscript` | 3 | `ctx` | `expr_context` | required |  |
| `Starred` | 1 | `value` | `expr` | required | `Parser/Python.asdl:89@v3.15.0rc1#Starred` |
| `Starred` | 2 | `ctx` | `expr_context` | required |  |
| `Name` | 1 | `id` | `identifier` | required | `Parser/Python.asdl:90@v3.15.0rc1#Name` |
| `Name` | 2 | `ctx` | `expr_context` | required |  |
| `List` | 1 | `elts` | `expr` | sequence | `Parser/Python.asdl:91@v3.15.0rc1#List` |
| `List` | 2 | `ctx` | `expr_context` | required |  |
| `Tuple` | 1 | `elts` | `expr` | sequence | `Parser/Python.asdl:92@v3.15.0rc1#Tuple` |
| `Tuple` | 2 | `ctx` | `expr_context` | required |  |
| `Slice` | 1 | `lower` | `expr` | optional | `Parser/Python.asdl:95@v3.15.0rc1#Slice` |
| `Slice` | 2 | `upper` | `expr` | optional |  |
| `Slice` | 3 | `step` | `expr` | optional |  |

### 2.4 `expr_context`

A choice between 3 constructors, declared at `Parser/Python.asdl:100@v3.15.0rc1#expr_context`.

| Node | Order | Field | Type | Holds | Declared at |
|---|---|---|---|---|---|
| `Load` |  | no fields |  |  | `Parser/Python.asdl:100@v3.15.0rc1#Load` |
| `Store` |  | no fields |  |  | `Parser/Python.asdl:100@v3.15.0rc1#Store` |
| `Del` |  | no fields |  |  | `Parser/Python.asdl:100@v3.15.0rc1#Del` |

### 2.5 `boolop`

A choice between 2 constructors, declared at `Parser/Python.asdl:102@v3.15.0rc1#boolop`.

| Node | Order | Field | Type | Holds | Declared at |
|---|---|---|---|---|---|
| `And` |  | no fields |  |  | `Parser/Python.asdl:102@v3.15.0rc1#And` |
| `Or` |  | no fields |  |  | `Parser/Python.asdl:102@v3.15.0rc1#Or` |

### 2.6 `operator`

A choice between 13 constructors, declared at `Parser/Python.asdl:104@v3.15.0rc1#operator`.

| Node | Order | Field | Type | Holds | Declared at |
|---|---|---|---|---|---|
| `Add` |  | no fields |  |  | `Parser/Python.asdl:104@v3.15.0rc1#Add` |
| `Sub` |  | no fields |  |  | `Parser/Python.asdl:104@v3.15.0rc1#Sub` |
| `Mult` |  | no fields |  |  | `Parser/Python.asdl:104@v3.15.0rc1#Mult` |
| `MatMult` |  | no fields |  |  | `Parser/Python.asdl:104@v3.15.0rc1#MatMult` |
| `Div` |  | no fields |  |  | `Parser/Python.asdl:104@v3.15.0rc1#Div` |
| `Mod` |  | no fields |  |  | `Parser/Python.asdl:104@v3.15.0rc1#Mod` |
| `Pow` |  | no fields |  |  | `Parser/Python.asdl:104@v3.15.0rc1#Pow` |
| `LShift` |  | no fields |  |  | `Parser/Python.asdl:104@v3.15.0rc1#LShift` |
| `RShift` |  | no fields |  |  | `Parser/Python.asdl:105@v3.15.0rc1#RShift` |
| `BitOr` |  | no fields |  |  | `Parser/Python.asdl:105@v3.15.0rc1#BitOr` |
| `BitXor` |  | no fields |  |  | `Parser/Python.asdl:105@v3.15.0rc1#BitXor` |
| `BitAnd` |  | no fields |  |  | `Parser/Python.asdl:105@v3.15.0rc1#BitAnd` |
| `FloorDiv` |  | no fields |  |  | `Parser/Python.asdl:105@v3.15.0rc1#FloorDiv` |

### 2.7 `unaryop`

A choice between 4 constructors, declared at `Parser/Python.asdl:107@v3.15.0rc1#unaryop`.

| Node | Order | Field | Type | Holds | Declared at |
|---|---|---|---|---|---|
| `Invert` |  | no fields |  |  | `Parser/Python.asdl:107@v3.15.0rc1#Invert` |
| `Not` |  | no fields |  |  | `Parser/Python.asdl:107@v3.15.0rc1#Not` |
| `UAdd` |  | no fields |  |  | `Parser/Python.asdl:107@v3.15.0rc1#UAdd` |
| `USub` |  | no fields |  |  | `Parser/Python.asdl:107@v3.15.0rc1#USub` |

### 2.8 `cmpop`

A choice between 10 constructors, declared at `Parser/Python.asdl:109@v3.15.0rc1#cmpop`.

| Node | Order | Field | Type | Holds | Declared at |
|---|---|---|---|---|---|
| `Eq` |  | no fields |  |  | `Parser/Python.asdl:109@v3.15.0rc1#Eq` |
| `NotEq` |  | no fields |  |  | `Parser/Python.asdl:109@v3.15.0rc1#NotEq` |
| `Lt` |  | no fields |  |  | `Parser/Python.asdl:109@v3.15.0rc1#Lt` |
| `LtE` |  | no fields |  |  | `Parser/Python.asdl:109@v3.15.0rc1#LtE` |
| `Gt` |  | no fields |  |  | `Parser/Python.asdl:109@v3.15.0rc1#Gt` |
| `GtE` |  | no fields |  |  | `Parser/Python.asdl:109@v3.15.0rc1#GtE` |
| `Is` |  | no fields |  |  | `Parser/Python.asdl:109@v3.15.0rc1#Is` |
| `IsNot` |  | no fields |  |  | `Parser/Python.asdl:109@v3.15.0rc1#IsNot` |
| `In` |  | no fields |  |  | `Parser/Python.asdl:109@v3.15.0rc1#In` |
| `NotIn` |  | no fields |  |  | `Parser/Python.asdl:109@v3.15.0rc1#NotIn` |

### 2.9 `comprehension`

A single shape with 4 fields, declared at `Parser/Python.asdl:111@v3.15.0rc1#comprehension`. There is nothing to switch on: every value of this type has exactly these fields.

| Order | Field | Type | Holds |
|---|---|---|---|
| 1 | `target` | `expr` | required |
| 2 | `iter` | `expr` | required |
| 3 | `ifs` | `expr` | sequence |
| 4 | `is_async` | `int` | required |

### 2.10 `excepthandler`

A choice between 1 constructors, declared at `Parser/Python.asdl:113@v3.15.0rc1#excepthandler`.

Every `excepthandler` node also carries 4 attributes, which are not fields and are not part of the constructor's positional arguments.

| Attribute | Type | Holds |
|---|---|---|
| `lineno` | `int` | required |
| `col_offset` | `int` | required |
| `end_lineno` | `int` | optional |
| `end_col_offset` | `int` | optional |

| Node | Order | Field | Type | Holds | Declared at |
|---|---|---|---|---|---|
| `ExceptHandler` | 1 | `type` | `expr` | optional | `Parser/Python.asdl:113@v3.15.0rc1#ExceptHandler` |
| `ExceptHandler` | 2 | `name` | `identifier` | optional |  |
| `ExceptHandler` | 3 | `body` | `stmt` | sequence |  |

### 2.11 `arguments`

A single shape with 7 fields, declared at `Parser/Python.asdl:116@v3.15.0rc1#arguments`. There is nothing to switch on: every value of this type has exactly these fields.

| Order | Field | Type | Holds |
|---|---|---|---|
| 1 | `posonlyargs` | `arg` | sequence |
| 2 | `args` | `arg` | sequence |
| 3 | `vararg` | `arg` | optional |
| 4 | `kwonlyargs` | `arg` | sequence |
| 5 | `kw_defaults` | `expr` | sequence of optional |
| 6 | `kwarg` | `arg` | optional |
| 7 | `defaults` | `expr` | sequence |

### 2.12 `arg`

A single shape with 3 fields, declared at `Parser/Python.asdl:119@v3.15.0rc1#arg`. There is nothing to switch on: every value of this type has exactly these fields.

Every `arg` node also carries 4 attributes, which are not fields and are not part of the constructor's positional arguments.

| Attribute | Type | Holds |
|---|---|---|
| `lineno` | `int` | required |
| `col_offset` | `int` | required |
| `end_lineno` | `int` | optional |
| `end_col_offset` | `int` | optional |

| Order | Field | Type | Holds |
|---|---|---|---|
| 1 | `arg` | `identifier` | required |
| 2 | `annotation` | `expr` | optional |
| 3 | `type_comment` | `string` | optional |

### 2.13 `keyword`

A single shape with 2 fields, declared at `Parser/Python.asdl:123@v3.15.0rc1#keyword`. There is nothing to switch on: every value of this type has exactly these fields.

Every `keyword` node also carries 4 attributes, which are not fields and are not part of the constructor's positional arguments.

| Attribute | Type | Holds |
|---|---|---|
| `lineno` | `int` | required |
| `col_offset` | `int` | required |
| `end_lineno` | `int` | optional |
| `end_col_offset` | `int` | optional |

| Order | Field | Type | Holds |
|---|---|---|---|
| 1 | `arg` | `identifier` | optional |
| 2 | `value` | `expr` | required |

### 2.14 `alias`

A single shape with 2 fields, declared at `Parser/Python.asdl:127@v3.15.0rc1#alias`. There is nothing to switch on: every value of this type has exactly these fields.

Every `alias` node also carries 4 attributes, which are not fields and are not part of the constructor's positional arguments.

| Attribute | Type | Holds |
|---|---|---|
| `lineno` | `int` | required |
| `col_offset` | `int` | required |
| `end_lineno` | `int` | optional |
| `end_col_offset` | `int` | optional |

| Order | Field | Type | Holds |
|---|---|---|---|
| 1 | `name` | `identifier` | required |
| 2 | `asname` | `identifier` | optional |

### 2.15 `withitem`

A single shape with 2 fields, declared at `Parser/Python.asdl:130@v3.15.0rc1#withitem`. There is nothing to switch on: every value of this type has exactly these fields.

| Order | Field | Type | Holds |
|---|---|---|---|
| 1 | `context_expr` | `expr` | required |
| 2 | `optional_vars` | `expr` | optional |

### 2.16 `match_case`

A single shape with 3 fields, declared at `Parser/Python.asdl:132@v3.15.0rc1#match_case`. There is nothing to switch on: every value of this type has exactly these fields.

| Order | Field | Type | Holds |
|---|---|---|---|
| 1 | `pattern` | `pattern` | required |
| 2 | `guard` | `expr` | optional |
| 3 | `body` | `stmt` | sequence |

### 2.17 `pattern`

A choice between 8 constructors, declared at `Parser/Python.asdl:134@v3.15.0rc1#pattern`.

Every `pattern` node also carries 4 attributes, which are not fields and are not part of the constructor's positional arguments.

| Attribute | Type | Holds |
|---|---|---|
| `lineno` | `int` | required |
| `col_offset` | `int` | required |
| `end_lineno` | `int` | required |
| `end_col_offset` | `int` | required |

| Node | Order | Field | Type | Holds | Declared at |
|---|---|---|---|---|---|
| `MatchValue` | 1 | `value` | `expr` | required | `Parser/Python.asdl:134@v3.15.0rc1#MatchValue` |
| `MatchSingleton` | 1 | `value` | `constant` | required | `Parser/Python.asdl:135@v3.15.0rc1#MatchSingleton` |
| `MatchSequence` | 1 | `patterns` | `pattern` | sequence | `Parser/Python.asdl:136@v3.15.0rc1#MatchSequence` |
| `MatchMapping` | 1 | `keys` | `expr` | sequence | `Parser/Python.asdl:137@v3.15.0rc1#MatchMapping` |
| `MatchMapping` | 2 | `patterns` | `pattern` | sequence |  |
| `MatchMapping` | 3 | `rest` | `identifier` | optional |  |
| `MatchClass` | 1 | `cls` | `expr` | required | `Parser/Python.asdl:138@v3.15.0rc1#MatchClass` |
| `MatchClass` | 2 | `patterns` | `pattern` | sequence |  |
| `MatchClass` | 3 | `kwd_attrs` | `identifier` | sequence |  |
| `MatchClass` | 4 | `kwd_patterns` | `pattern` | sequence |  |
| `MatchStar` | 1 | `name` | `identifier` | optional | `Parser/Python.asdl:140@v3.15.0rc1#MatchStar` |
| `MatchAs` | 1 | `pattern` | `pattern` | optional | `Parser/Python.asdl:143@v3.15.0rc1#MatchAs` |
| `MatchAs` | 2 | `name` | `identifier` | optional |  |
| `MatchOr` | 1 | `patterns` | `pattern` | sequence | `Parser/Python.asdl:144@v3.15.0rc1#MatchOr` |

### 2.18 `type_ignore`

A choice between 1 constructors, declared at `Parser/Python.asdl:148@v3.15.0rc1#type_ignore`.

| Node | Order | Field | Type | Holds | Declared at |
|---|---|---|---|---|---|
| `TypeIgnore` | 1 | `lineno` | `int` | required | `Parser/Python.asdl:148@v3.15.0rc1#TypeIgnore` |
| `TypeIgnore` | 2 | `tag` | `string` | required |  |

### 2.19 `type_param`

A choice between 3 constructors, declared at `Parser/Python.asdl:150@v3.15.0rc1#type_param`.

Every `type_param` node also carries 4 attributes, which are not fields and are not part of the constructor's positional arguments.

| Attribute | Type | Holds |
|---|---|---|
| `lineno` | `int` | required |
| `col_offset` | `int` | required |
| `end_lineno` | `int` | required |
| `end_col_offset` | `int` | required |

| Node | Order | Field | Type | Holds | Declared at |
|---|---|---|---|---|---|
| `TypeVar` | 1 | `name` | `identifier` | required | `Parser/Python.asdl:150@v3.15.0rc1#TypeVar` |
| `TypeVar` | 2 | `bound` | `expr` | optional |  |
| `TypeVar` | 3 | `default_value` | `expr` | optional |  |
| `ParamSpec` | 1 | `name` | `identifier` | required | `Parser/Python.asdl:151@v3.15.0rc1#ParamSpec` |
| `ParamSpec` | 2 | `default_value` | `expr` | optional |  |
| `TypeVarTuple` | 1 | `name` | `identifier` | required | `Parser/Python.asdl:152@v3.15.0rc1#TypeVarTuple` |
| `TypeVarTuple` | 2 | `default_value` | `expr` | optional |  |
<!-- bpc:end nodes -->

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

<!-- bpc:begin observable -->
The whole grammar is visible from Python. Each of the 113 node kinds below is a class in the `ast` module with the same name, each of the 19 types is a class those inherit from, and the field order in the grammar is the order those classes take positional arguments in. A reimplementation that renames a field or reorders two of them is detectable by any program that builds a tree by hand or reads one back.

The three field kinds are three different things to leave out. A required field has to be passed, and building the node without it raises `TypeError` naming the field. An optional field left out is `None`. A sequence field left out is a new empty list, so `body` is `[]` rather than missing. There is one field type that breaks the pattern: a field of type `expr_context` left out is the `Load` singleton, because nearly every expression in a tree is being read rather than written to.

The 4 location attributes are separate from the fields. They are listed in `_attributes` rather than `_fields`, and none of them is ever required by the constructor, so a node can always be built without them. The two declared optional default to `None` like any other optional. The two declared required have no value at all, and reading one raises `AttributeError` rather than returning `None`. Nothing complains until `compile` sees the tree, which is where a missing line number becomes `TypeError` and where a port has to put the same check.

| Class | Base | `_fields` | `_attributes` |
|---|---|---|---|
| `mod` | abstract | `()` | `()` |
| `Module` | `mod` | `('body', 'type_ignores')` | `()` |
| `Interactive` | `mod` | `('body',)` | `()` |
| `Expression` | `mod` | `('body',)` | `()` |
| `FunctionType` | `mod` | `('argtypes', 'returns')` | `()` |
| `stmt` | abstract | `()` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `FunctionDef` | `stmt` | `('name', 'args', 'body', 'decorator_list', 'returns', 'type_comment', 'type_params')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `AsyncFunctionDef` | `stmt` | `('name', 'args', 'body', 'decorator_list', 'returns', 'type_comment', 'type_params')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `ClassDef` | `stmt` | `('name', 'bases', 'keywords', 'body', 'decorator_list', 'type_params')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Return` | `stmt` | `('value',)` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Delete` | `stmt` | `('targets',)` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Assign` | `stmt` | `('targets', 'value', 'type_comment')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `TypeAlias` | `stmt` | `('name', 'type_params', 'value')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `AugAssign` | `stmt` | `('target', 'op', 'value')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `AnnAssign` | `stmt` | `('target', 'annotation', 'value', 'simple')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `For` | `stmt` | `('target', 'iter', 'body', 'orelse', 'type_comment')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `AsyncFor` | `stmt` | `('target', 'iter', 'body', 'orelse', 'type_comment')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `While` | `stmt` | `('test', 'body', 'orelse')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `If` | `stmt` | `('test', 'body', 'orelse')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `With` | `stmt` | `('items', 'body', 'type_comment')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `AsyncWith` | `stmt` | `('items', 'body', 'type_comment')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Match` | `stmt` | `('subject', 'cases')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Raise` | `stmt` | `('exc', 'cause')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Try` | `stmt` | `('body', 'handlers', 'orelse', 'finalbody')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `TryStar` | `stmt` | `('body', 'handlers', 'orelse', 'finalbody')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Assert` | `stmt` | `('test', 'msg')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Import` | `stmt` | `('names', 'is_lazy')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `ImportFrom` | `stmt` | `('module', 'names', 'level', 'is_lazy')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Global` | `stmt` | `('names',)` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Nonlocal` | `stmt` | `('names',)` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Expr` | `stmt` | `('value',)` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Pass` | `stmt` | `()` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Break` | `stmt` | `()` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Continue` | `stmt` | `()` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `expr` | abstract | `()` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `BoolOp` | `expr` | `('op', 'values')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `NamedExpr` | `expr` | `('target', 'value')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `BinOp` | `expr` | `('left', 'op', 'right')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `UnaryOp` | `expr` | `('op', 'operand')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Lambda` | `expr` | `('args', 'body')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `IfExp` | `expr` | `('test', 'body', 'orelse')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Dict` | `expr` | `('keys', 'values')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Set` | `expr` | `('elts',)` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `ListComp` | `expr` | `('elt', 'generators')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `SetComp` | `expr` | `('elt', 'generators')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `DictComp` | `expr` | `('key', 'value', 'generators')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `GeneratorExp` | `expr` | `('elt', 'generators')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Await` | `expr` | `('value',)` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Yield` | `expr` | `('value',)` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `YieldFrom` | `expr` | `('value',)` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Compare` | `expr` | `('left', 'ops', 'comparators')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Call` | `expr` | `('func', 'args', 'keywords')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `FormattedValue` | `expr` | `('value', 'conversion', 'format_spec')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Interpolation` | `expr` | `('value', 'str', 'conversion', 'format_spec')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `JoinedStr` | `expr` | `('values',)` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `TemplateStr` | `expr` | `('values',)` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Constant` | `expr` | `('value', 'kind')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Attribute` | `expr` | `('value', 'attr', 'ctx')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Subscript` | `expr` | `('value', 'slice', 'ctx')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Starred` | `expr` | `('value', 'ctx')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Name` | `expr` | `('id', 'ctx')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `List` | `expr` | `('elts', 'ctx')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Tuple` | `expr` | `('elts', 'ctx')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `Slice` | `expr` | `('lower', 'upper', 'step')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `expr_context` | abstract | `()` | `()` |
| `Load` | `expr_context` | `()` | `()` |
| `Store` | `expr_context` | `()` | `()` |
| `Del` | `expr_context` | `()` | `()` |
| `boolop` | abstract | `()` | `()` |
| `And` | `boolop` | `()` | `()` |
| `Or` | `boolop` | `()` | `()` |
| `operator` | abstract | `()` | `()` |
| `Add` | `operator` | `()` | `()` |
| `Sub` | `operator` | `()` | `()` |
| `Mult` | `operator` | `()` | `()` |
| `MatMult` | `operator` | `()` | `()` |
| `Div` | `operator` | `()` | `()` |
| `Mod` | `operator` | `()` | `()` |
| `Pow` | `operator` | `()` | `()` |
| `LShift` | `operator` | `()` | `()` |
| `RShift` | `operator` | `()` | `()` |
| `BitOr` | `operator` | `()` | `()` |
| `BitXor` | `operator` | `()` | `()` |
| `BitAnd` | `operator` | `()` | `()` |
| `FloorDiv` | `operator` | `()` | `()` |
| `unaryop` | abstract | `()` | `()` |
| `Invert` | `unaryop` | `()` | `()` |
| `Not` | `unaryop` | `()` | `()` |
| `UAdd` | `unaryop` | `()` | `()` |
| `USub` | `unaryop` | `()` | `()` |
| `cmpop` | abstract | `()` | `()` |
| `Eq` | `cmpop` | `()` | `()` |
| `NotEq` | `cmpop` | `()` | `()` |
| `Lt` | `cmpop` | `()` | `()` |
| `LtE` | `cmpop` | `()` | `()` |
| `Gt` | `cmpop` | `()` | `()` |
| `GtE` | `cmpop` | `()` | `()` |
| `Is` | `cmpop` | `()` | `()` |
| `IsNot` | `cmpop` | `()` | `()` |
| `In` | `cmpop` | `()` | `()` |
| `NotIn` | `cmpop` | `()` | `()` |
| `comprehension` | concrete | `('target', 'iter', 'ifs', 'is_async')` | `()` |
| `excepthandler` | abstract | `()` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `ExceptHandler` | `excepthandler` | `('type', 'name', 'body')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `arguments` | concrete | `('posonlyargs', 'args', 'vararg', 'kwonlyargs', 'kw_defaults', 'kwarg', 'defaults')` | `()` |
| `arg` | concrete | `('arg', 'annotation', 'type_comment')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `keyword` | concrete | `('arg', 'value')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `alias` | concrete | `('name', 'asname')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `withitem` | concrete | `('context_expr', 'optional_vars')` | `()` |
| `match_case` | concrete | `('pattern', 'guard', 'body')` | `()` |
| `pattern` | abstract | `()` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `MatchValue` | `pattern` | `('value',)` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `MatchSingleton` | `pattern` | `('value',)` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `MatchSequence` | `pattern` | `('patterns',)` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `MatchMapping` | `pattern` | `('keys', 'patterns', 'rest')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `MatchClass` | `pattern` | `('cls', 'patterns', 'kwd_attrs', 'kwd_patterns')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `MatchStar` | `pattern` | `('name',)` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `MatchAs` | `pattern` | `('pattern', 'name')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `MatchOr` | `pattern` | `('patterns',)` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `type_ignore` | abstract | `()` | `()` |
| `TypeIgnore` | `type_ignore` | `('lineno', 'tag')` | `()` |
| `type_param` | abstract | `()` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `TypeVar` | `type_param` | `('name', 'bound', 'default_value')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `ParamSpec` | `type_param` | `('name', 'default_value')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
| `TypeVarTuple` | `type_param` | `('name', 'default_value')` | `('lineno', 'col_offset', 'end_lineno', 'end_col_offset')` |
<!-- bpc:end observable -->

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

<!-- bpc:begin conformance -->
Sections 1, 2 and 5 are generated from the grammar file, so the way they go wrong is not a typo. They go wrong when the running interpreter and the pinned grammar have stopped agreeing, which is what the checks below are for. Each one reads the grammar from the pinned tree and compares it against the `ast` module of the interpreter running the test.

| Claim | Held up by | Covers |
|---|---|---|
| Every type in section 1 is a class in `ast` | `test_every_type_in_the_grammar_is_a_class_in_ast` | 19 types |
| Every constructor in section 2 is a class in `ast` | `test_every_constructor_in_the_grammar_is_a_class_in_ast` | 113 node kinds |
| `_fields` is the grammar's field names, in the grammar's order | `test_the_field_order_is_the_order_the_grammar_declares` | 198 fields |
| `_attributes` is the grammar's attributes, in the grammar's order | `test_the_attributes_are_the_ones_the_grammar_declares` | 8 types carry attributes |
| Leaving a field out does what section 5 says it does | `test_the_defaults_are_the_ones_section_5_describes` | the three field kinds |
| Every citation generated into sections 1 and 2 resolves against the pinned tree | `just citations` | 145 citations |

The first five run under `just test` and live in `tools/bpc/tests/test_bpc_conformance.py`. They are skipped on an interpreter whose version does not match the pinned tree, because a difference between v3.15.0rc1 and some other version is a fact about the two versions rather than a failure of this document.
<!-- bpc:end conformance -->

## 9. Port notes

Generate the node types rather than typing them. The grammar file is 154 lines and it is stable across releases in the parts that matter, so a port that reads it produces the same 113 node kinds with the same field names in the same order, and stays right when the pin moves. A port that types them by hand is doing the one job in this subsystem that a machine does better.

In Go the natural shape is one interface per sum type and one struct per constructor, with a marker method. That gives type switches where CPython has a `kind` enum, and it loses nothing, because CPython's union is a closed set and so is the interface. The cost is that a nil interface value and an interface holding a nil pointer are different things, and optional fields are exactly where that bites. Use a pointer field and check for nil, never an interface.

In Rust the natural shape is one enum per sum type with a variant per constructor, which is closer to the C than Go gets and gives exhaustive matching for free. `Option<T>` for optional fields and `Vec<T>` for sequences map exactly, with one caveat: `Vec<T>` cannot be absent, and CPython's `NULL` sequence has to become an empty `Vec` at the boundary rather than an `Option<Vec<T>>`. Making that distinction representable is how INV-AST-004 gets violated by accident.

The arena is worth keeping in both. In Rust an arena crate or a `Vec` of nodes with index handles removes the lifetime problem that a tree of `Box`es creates during parsing, when a failed alternative discards a subtree. In Go the garbage collector already does this, so an arena buys allocation speed rather than correctness, and can be skipped until it is measured.

Validation cannot be generated and has to be written. It is a few hundred lines and it is the difference between a port that compiles the same programs CPython compiles and one that accepts trees CPython refuses. Start with the non empty body rule, which is the one every real program depends on without knowing it.

The location attributes are not optional in practice. A port that leaves them out has a working compiler and unusable tracebacks, and adding them afterwards means touching every constructor call in the parser.
