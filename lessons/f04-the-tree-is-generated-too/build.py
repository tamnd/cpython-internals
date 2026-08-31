#!/usr/bin/env python
"""F04. The tree is generated too.

The fourth lesson of the front end part, and the eighteenth overall. F03 was about the parser
being generated from `Grammar/python.gram`. This one is about the thing the parser builds
being generated too, from a second and much smaller file: `Parser/Python.asdl`, 154 lines
that declare every node type in the tree once, for both C and Python at the same time.

T03 met the AST from the outside and used it. This lesson is about where `ast.BinOp` comes
from, why `_fields` exists at all, and why a tree you build by hand gets checked in C before
the compiler will look at it.

Everything here is observable from a stock interpreter, because the `ast` module is one of
the generator's outputs. Reading `_fields` is reading the schema.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("f04-the-tree-is-generated-too", "f04")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("f04-the-tree-is-generated-too").figure


lesson.md(f"""
# F04. The tree is generated too

{badge}

F03 ended on a generated file. This one starts on another, and it is a much easier read.

`Parser/Python.asdl` is 154 lines. It does not contain any code. It is a list of the kinds of node a Python program can be made of, and what each kind holds. `BinOp` holds a left, an operator and a right. `Return` holds a value, or nothing. That is the whole file.

A program called `Parser/asdl_c.py` reads it at build time and writes three more files, one of which is the 18524 lines of `Python/Python-ast.c` that hold the Python classes you import from `ast`.

So when you type `ast.BinOp._fields` you are reading that schema back. Not a copy of it. The tuple you get is the line from the file.

{figure("one-file-three-outputs", "a pipeline from the asdl schema through the generator to the generated C and then the ast module")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Parser/Python.asdl:62@v3.15.0rc1`.

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
## One line of schema, one class

Here is the line that describes a binary operation, at {cite("Parser/Python.asdl:62@v3.15.0rc1")}:

```
| BinOp(expr left, operator op, expr right)
```

Four things in it. The name of the node type, and then three fields, each written as a type followed by a name. The `{term("ASDL")}` file is nothing but forty or so lines like this one.

{figure("a-line-becomes-a-class", "the BinOp line marked up into a class name and three fields")}

The generator turns that into a C struct, a Python class, and a `_fields` tuple on the class holding the names in order. The three files it writes and the command that writes them are spelled out in the `regen-ast` target at {cite("Makefile.pre.in:2057-2068@v3.15.0rc1")}, and the first line of {cite("Python/Python-ast.c:1@v3.15.0rc1")} says so as well. You can read the tuple straight back.

{lesson.claim("the _fields tuple on a node class is the field list from the schema, in the order the schema wrote it")}
""")


lesson.code("""
import ast

for cls in (ast.BinOp, ast.Return, ast.Call, ast.FunctionDef):
    print(f"  ast.{cls.__name__:12} _fields {cls._fields}")
""")


lesson.md(f"""
`Return` holds one field. `Call` holds three. `FunctionDef` holds seven, and if you go and look at {cite("Parser/Python.asdl:11-14@v3.15.0rc1")} you will find those seven names in that order.

There is a second tuple, and it is a different kind of thing. `_attributes` holds the source position fields, and they are declared once for a whole family of node types rather than per node. One line at {cite("Parser/Python.asdl:98@v3.15.0rc1")} gives every expression a `lineno`, a `col_offset`, an `end_lineno` and an `end_col_offset`, and that is why every expression has them and why `ast.Add` has none.

{lesson.claim("position information is declared once per family in the schema, so a node either has all four position attributes or none of them")}
""")


lesson.code("""
import ast

for cls in (ast.BinOp, ast.Add, ast.arguments, ast.arg):
    kind = "yes" if cls._attributes else "no"
    print(f"  ast.{cls.__name__:12} carries a position: {kind:3}  {cls._attributes}")
print()

SOURCE = "total = price * 2"

for node in ast.walk(ast.parse(SOURCE)):
    if not isinstance(node, ast.expr | ast.stmt):
        continue
    where = f"columns {node.col_offset:2} to {node.end_col_offset:2}"
    print(f"  {type(node).__name__:10} {where}   {ast.get_source_segment(SOURCE, node)!r}")
""")


lesson.md(f"""
That second block is the whole reason the attributes are there. Every error message that underlines part of your line, every coverage tool, every linter that can point at a column, is reading four integers that exist because of one line in a schema file.

## Sums and products

The schema has exactly two ways to declare a type, and you can tell them apart from Python without opening the file.

A {term("sum type", "sum")} is written with bars, like `operator = Add | Sub | Mult | ...` at {cite("Parser/Python.asdl:104-105@v3.15.0rc1")}. It becomes an abstract base class plus one concrete class per alternative. That is why `isinstance(node, ast.expr)` works and why there are 29 different things it can be.

A {term("product type", "product")} is written as a single bracketed list, like `arguments` at {cite("Parser/Python.asdl:116-117@v3.15.0rc1")}. There is only ever one shape, so it becomes one class and no base class. There are seven of those in the whole language.

{lesson.claim("the abstract base classes in the ast module are exactly the sum types in the schema, and the classes with no subclasses are the products")}
""")


lesson.code("""
import ast

#: Six classes in the ast module are not in the schema at all. They are kept so that code
#: written for Python 3.8 and earlier still imports, and nothing the parser builds uses them.
FOSSILS = ("Suite", "AugLoad", "AugStore", "Param", "Index", "ExtSlice")

products = []

for cls in sorted(ast.AST.__subclasses__(), key=lambda one: one.__name__):
    kinds = [one for one in cls.__subclasses__() if one.__name__ not in FOSSILS]
    if kinds:
        print(f"  sum      {cls.__name__:14} {len(kinds):3} alternatives")
    else:
        products.append(cls.__name__)

print()
print(f"  products {', '.join(products)}")
""")


lesson.md(f"""
{figure("sums-and-products", "a side by side comparison of a sum type and a product type")}

Two of those numbers are worth a second look. `expr` has 29 alternatives and `stmt` has 28, so the entire syntax of Python fits in 57 kinds of node. Everything else in that list is small: 13 binary operators, 10 comparison operators, 4 unary ones.

The six names in `FOSSILS` are the only untidy part. They are classes the generator still emits for code written before 3.9, and nothing the parser produces is ever one of them. Filtering them out is the difference between the schema and the module as shipped.

## Three markers, and that is all the optionality there is

Every field in the schema is written one of three ways, and the difference is a single character.

A plain field is required and always there. A field with a `?` after its type is optional. A field with a `*` is a sequence of any length, including empty. There is no fourth case anywhere in the file.

{lesson.claim("an optional field arrives as None and a sequence field arrives as an empty list, whether or not you wrote anything for it")}
""")


lesson.code("""
import ast

node = ast.parse("def greet():\\n    pass\\n").body[0]

for name in node._fields:
    value = getattr(node, name)
    print(f"  {name:16} {value!r}")
""")


lesson.md(f"""
{figure("three-markers", "a table of the three field markers and what each one gives you")}

`greet` has no decorators, no return annotation, no type parameters and no type comment. Three of those come back as empty lists because the schema wrote them with a `*`, and two come back as `None` because the schema wrote them with a `?`. Nothing is missing and nothing raises an `AttributeError`. That predictability is the whole benefit of having a schema.

## Abstract means something was thrown away

The A in AST is doing real work. The tree keeps what your program means and drops how you spelled it, and the fastest way to see the line between the two is to parse something and print it back out.

{lesson.claim("the tree keeps meaning and drops spelling, so parsing and unparsing is not a round trip")}
""")


lesson.code("""
import ast

SOURCES = (
    "x = 1 + (2 * 3)",
    "x = (1 + 2) * 3",
    "x = 1_000",
    "x = 0x10",
    "x = 'a' 'b'",
    "x = 5  # a note to yourself",
)

for source in SOURCES:
    print(f"  {source:30} {ast.unparse(ast.parse(source))}")
""")


lesson.md(f"""
{figure("what-abstract-drops", "a table of four sources, what the tree holds, and what went missing")}

Read the second line against the first. The brackets in `1 + (2 * 3)` did not change the meaning, so there is no node for them and they are gone. The brackets in `(1 + 2) * 3` did change it, so the shape of the tree changed, and `ast.unparse` puts brackets back when it needs them to print that shape correctly. Nothing remembered your brackets. They were reconstructed.

The comment is the one that catches people out. There is no comment node in the schema, so a tool that needs comments cannot use the AST for them and has to go back to the token stream from F01. That is exactly why formatters and linters are harder to write than they look.

## What happens if you hand over a broken tree

`compile` accepts a tree as well as a string, which means you can build one by hand and run it. It also means the compiler has to defend itself, because a hand built tree can be nonsense in ways a parsed one never is.

The defending happens in two places. First the generated code in `Python-ast.c` converts your Python objects into C structs and complains about anything missing. That message was written by the generator, at {cite("Parser/asdl_c.py:652-657@v3.15.0rc1")}, which is why it reads like a template. Then {cite("Python/ast.c:1048-1058@v3.15.0rc1#_PyAST_Validate")} walks the whole tree checking the things a schema cannot express, like a body needing at least one statement at {cite("Python/ast.c:703-710@v3.15.0rc1#_validate_nonempty_seq")}, or a name on the left of an assignment needing a `Store` context at {cite("Python/ast.c:252-256@v3.15.0rc1")}.

{lesson.claim("a hand built tree is checked in C before the compiler sees it, and the two kinds of complaint come from two different places")}
""")


lesson.code("""
import ast


def broken(make):
    \"\"\"Run a function that builds a bad tree, and print the complaint instead of raising.\"\"\"
    try:
        compile(make(), "<here>", "exec")
    except (TypeError, ValueError) as unhappy:
        print(f"  {type(unhappy).__name__:10} {unhappy}")


def no_position():
    return ast.Module(body=[ast.Pass()], type_ignores=[])


def empty_assignment():
    tree = ast.parse("x = 1")
    tree.body[0].targets = []
    return tree


def wrong_context():
    tree = ast.parse("x")
    tree.body[0].value.ctx = ast.Store()
    return tree


for make in (no_position, empty_assignment, wrong_context):
    broken(make)
""")


lesson.md("""
Three different failures, and the first one is a different species from the other two.

`required field "lineno" missing from stmt` comes out of the conversion step, before any validating happens, and it is the schema talking: the field is not optional, so there is nothing to convert. `empty targets on Assign` and the context complaint come from the validator, and neither of those rules is written in the schema anywhere. A schema can say that `Assign` has a list of targets. It cannot say the list must not be empty.

If you do build trees by hand, `ast.fix_missing_locations` copies positions down from the parent and makes the first problem go away. The other two you have to get right yourself.

## Try it yourself

1. Print `ast.Constant._fields` and then find the `Constant` line in the schema. What is the second field for, and when is it not `None`?
2. `ast.dump(tree, include_attributes=True)` shows the position attributes. Run it on a two line function and find the node whose range covers both lines.
3. Build a tree for `print("hi")` entirely by hand, with no `ast.parse` anywhere, and run it. `ast.fix_missing_locations` will save you a lot of typing.
4. Parse a file you wrote and count the node types it actually uses. How many of the 57 does ordinary code touch?
5. `ast.unparse(ast.parse(source))` and then parse the result again. Compare the two trees with `ast.dump`. Should they ever differ, and can you find a case where they do?

## What just happened

Every node type in the tree is declared once, in `Parser/Python.asdl`, and a generator turns that one file into the C structs the parser fills in and the Python classes you inspect. `_fields` is the schema read back.

Position attributes are declared per family rather than per node, which is why every expression and every statement has exactly four of them and the operators have none.

There are two ways to declare a type. Sums become an abstract base plus one class per alternative, which is what makes `isinstance(node, ast.expr)` work. Products become a single class. The whole syntax of Python is 29 kinds of expression and 28 kinds of statement.

Fields are required, optional or repeated, and that is the entire vocabulary. Optional arrives as `None`, repeated arrives as a list, and nothing is ever absent.

The tree keeps meaning and drops spelling. Redundant brackets, the way you wrote a number, adjacent string literals and every comment are gone by the time you have a tree.

A tree you build by hand is checked twice in C, once by generated conversion code and once by a validator, and the second one enforces rules the schema has no way to state.

## What is next

F05 is the symbol table, which is the first thing the compiler does with the tree once it has one. It walks the whole thing looking only at names, works out which scope each one belongs to, and hands the answer to the code generator.

That pass is where `global`, `nonlocal` and closures are decided, and it happens before a single byte of bytecode exists.
""")


raise SystemExit(lesson.save())
