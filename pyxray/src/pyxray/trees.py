"""The syntax tree, and the things about it that are easier to show than to describe.

`ast` already gives you the tree. What it does not give you is a view of the tree you can
read at a glance, or a convenient way to ask the question this lesson is really about,
which is what the tree remembers about your file and what it has thrown away.

The other thing here is the round trip. `ast.unparse` turns a tree back into text, and the
property worth knowing is that the text it produces parses to the same tree, even though it
is very often not the text you wrote. That is a claim you can check rather than believe, so
`roundtrip` checks it on one string and `survey` checks it on a whole directory of real
code.

The ASDL helpers exist because of a detail that surprises people. Every node class in `ast`
carries its own declaration from Parser/Python.asdl:62@v3.15.0rc1#BinOp as its docstring,
because the class was generated from that file. The definition of Python's syntax tree is
not buried in a compiler. It is one readable file, and you can print any line of it from
the interpreter you already have open.
"""

from __future__ import annotations

import ast
import pathlib
from collections.abc import Iterator
from dataclasses import dataclass

#: Nodes with no fields and no children. The operators, the contexts and the boolean
#: operators are all singletons in CPython, so `Mult` is not a thing with a value in it,
#: it is the name of a case. Showing them as a node with an empty body suggests they hold
#: something, so `outline` prints them inline instead.
_LEAFY = (ast.expr_context, ast.operator, ast.unaryop, ast.cmpop, ast.boolop)


def asdl(node: ast.AST | type[ast.AST]) -> str:
    """The ASDL declaration for a node, or for a node type.

    This is the class docstring, which is not a coincidence and not a convention somebody
    kept up by hand. Parser/asdl_c.py reads Parser/Python.asdl and writes the declaration
    into the generated class, so what comes back here is the definition itself.

    Docstrings can be stripped, by `python -OO` and by some packaging tools, so this says
    what happened rather than returning None into the middle of a lesson.
    """
    kind = node if isinstance(node, type) else type(node)
    return kind.__doc__ or f"{kind.__name__} (this interpreter was built without docstrings)"


def fields(node: ast.AST | type[ast.AST]) -> list[tuple[str, str]]:
    """Each field of a node, with the ASDL type it is declared to hold.

    `_fields` gives the names and the annotations give the types, and neither is much use
    without the other. The types are the interesting half: they are what tells you that
    the left of a `BinOp` is any expression at all, which is the whole reason the tree
    nests.
    """
    kind = node if isinstance(node, type) else type(node)
    annotations = getattr(kind, "__annotations__", {})
    return [(name, getattr(annotations.get(name), "__name__", "?")) for name in kind._fields]


def _label(node: ast.AST) -> str:
    """A node's name, with the small amount of its content that fits on the line."""
    name = type(node).__name__
    if isinstance(node, ast.Constant):
        return f"Constant {node.value!r}"
    if isinstance(node, ast.Name):
        # The context is printed on its own line below, as a field, because that is what
        # it is. Repeating it here would suggest a name and its context are one thing.
        return f"Name {node.id!r}"
    if isinstance(node, ast.arg):
        return f"arg {node.arg!r}"
    if isinstance(node, ast.Attribute):
        return f"Attribute .{node.attr}"
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return f"{name} {node.name!r}"
    return name


def outline(tree: ast.AST | str, *, indent: int = 0) -> str:
    """The shape of a tree, one node per line, with the field name that holds each child.

    `ast.dump` is exact and it is hard to see a shape in. Every field name, every empty
    list and every position argument is in there, and for anything bigger than one line of
    source the reader ends up counting brackets. This keeps the field names, because
    knowing a node is the `right` of a `BinOp` rather than the `left` is often the point,
    and drops everything else.
    """
    if isinstance(tree, str):
        tree = ast.parse(tree)
    return "\n".join(_lines(tree, indent, ""))


def _lines(node: ast.AST, depth: int, prefix: str) -> Iterator[str]:
    yield f"{'    ' * depth}{prefix}{_label(node)}"
    for name, value in ast.iter_fields(node):
        for child in value if isinstance(value, list) else [value]:
            if not isinstance(child, ast.AST):
                continue
            if isinstance(child, _LEAFY):
                yield f"{'    ' * (depth + 1)}{name}: {type(child).__name__}"
            else:
                yield from _lines(child, depth + 1, f"{name}: ")


@dataclass(frozen=True)
class Span:
    """One node and the piece of source it came from."""

    node: str
    text: str
    line: int
    columns: tuple[int, int]

    def __str__(self) -> str:
        start, end = self.columns
        return f"{self.node:<22} line {self.line}, columns {start} to {end}  {self.text!r}"


def spans(source: str) -> list[Span]:
    """Every node that knows where it came from, with the text it covers.

    Not every node has a position. The operators do not, because `Mult` is a case rather
    than something written at a place in the file, and a reader who expects one per node
    will go looking for the bug that is not there.
    """
    tree = ast.parse(source)
    found = []
    for node in ast.walk(tree):
        if not hasattr(node, "lineno"):
            continue
        segment = ast.get_source_segment(source, node)
        found.append(
            Span(
                node=_label(node),
                text=segment if segment is not None else "",
                line=node.lineno,
                columns=(node.col_offset, node.end_col_offset),
            )
        )
    return sorted(found, key=lambda span: (span.line, span.columns[0], -span.columns[1]))


def same_tree(left: str, right: str) -> bool:
    """Do two pieces of source produce the same tree?

    This is the question behind most of the interesting facts in this lesson. Parentheses,
    spacing, comments, the underscores in a number and the base you wrote it in are all
    things the tree does not keep, and the fastest way to show that is to compare two trees
    rather than to explain what a tree is.
    """
    return ast.dump(ast.parse(left)) == ast.dump(ast.parse(right))


@dataclass(frozen=True)
class RoundTrip:
    """What happened when a piece of source was unparsed and parsed again."""

    source: str
    text: str
    same_tree: bool
    error: str = ""

    @property
    def same_text(self) -> bool:
        return self.text == self.source.strip()

    def __str__(self) -> str:
        if self.error:
            return f"could not unparse: {self.error}"
        verdict = "same tree" if self.same_tree else "DIFFERENT TREE"
        rewritten = "unchanged" if self.same_text else "rewritten"
        return f"{verdict}, text {rewritten}: {self.text!r}"


def roundtrip(source: str) -> RoundTrip:
    """Parse, unparse, parse again, and report whether the two trees match.

    The interesting result is the common one, where the tree is identical and the text is
    not. That gap is the clearest statement of what a syntax tree is: everything about your
    file that changes the meaning, and nothing about how you typed it.
    """
    tree = ast.parse(source)
    try:
        text = ast.unparse(tree)
    except Exception as error:
        # Deliberately broad. Unparsing a tree the reader built by hand can fail in a
        # handful of ways, and a lesson that ends in a traceback from inside `ast` has
        # stopped teaching. Naming the ones seen so far would just go stale.
        return RoundTrip(source=source, text="", same_tree=False, error=repr(error))
    try:
        again = ast.parse(text)
    except SyntaxError as error:
        return RoundTrip(source=source, text=text, same_tree=False, error=repr(error))
    return RoundTrip(source=source, text=text, same_tree=ast.dump(again) == ast.dump(tree))


@dataclass(frozen=True)
class Survey:
    """The round trip run over a pile of real files."""

    checked: int
    matched: int
    differed: list[str]
    skipped: list[str]

    def __str__(self) -> str:
        parts = [f"{self.checked} file(s) parsed, {self.matched} round tripped to the same tree"]
        if self.differed:
            parts.append(f"different: {', '.join(self.differed)}")
        if self.skipped:
            parts.append(f"could not be read or parsed: {len(self.skipped)}")
        return "\n".join(parts)


def survey(directory: str | pathlib.Path, *, limit: int | None = None) -> Survey:
    """Run the round trip over every `.py` file directly inside a directory.

    Point it at the standard library and it is a property test over a few hundred thousand
    lines of code somebody else wrote, which is a much stronger statement than the same
    check on the four line example above it. Sorted and limited so a notebook cell takes
    the same time and prints the same thing every run.
    """
    paths = sorted(pathlib.Path(directory).glob("*.py"))
    if limit is not None:
        paths = paths[:limit]

    checked = matched = 0
    differed: list[str] = []
    skipped: list[str] = []
    for path in paths:
        try:
            source = path.read_text(encoding="utf-8")
            ast.parse(source)
        except OSError, SyntaxError, UnicodeDecodeError, ValueError, RecursionError:
            # Some of these are deliberate. The standard library ships files that are only
            # valid on another version and files that are not Python at all, and a lesson
            # that fell over on one of them would be making a point about packaging.
            skipped.append(path.name)
            continue
        checked += 1
        if roundtrip(source).same_tree:
            matched += 1
        else:
            differed.append(path.name)
    return Survey(checked=checked, matched=matched, differed=differed, skipped=skipped)


def stdlib() -> pathlib.Path:
    """Where this interpreter keeps the standard library.

    Worth a function rather than a line in the notebook, because the answer is different in
    Colab, in a virtual environment and in a checkout, and a hard coded path is a lesson
    that only runs on the machine it was written on.
    """
    import sysconfig

    return pathlib.Path(sysconfig.get_paths()["stdlib"])
