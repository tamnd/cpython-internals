"""A submission that fails the T05 fight, and fails it the way a first attempt does.

CI runs this one too. A grader that has never said no is a grader that says yes to anything,
and the cheapest way to keep it honest is to hand it something wrong on every pull request
and insist it notices, with a message that names what is wrong rather than "incorrect".

What this gets wrong is the thing almost everybody gets wrong first. It walks the tree and
writes down every name it sees bound, in the order the tree hands them over, which for an
assignment means the target before the value. CPython does it the other way round, because
the value has to be worked out before there is anything to store. So `total = (part := 1)`
lays out `part` first and this says `total` first.

Everything else in here is right, which is the point: it is a near miss rather than a
scarecrow, so the grader has to be precise to catch it.
"""

from __future__ import annotations

import ast


def bindings(node: ast.AST, found: list[str]) -> None:
    """Every name bound underneath `node`, in the order the tree hands them over."""
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store | ast.Del):
        if node.id not in found:
            found.append(node.id)
    elif isinstance(node, ast.Import | ast.ImportFrom):
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            if name not in found:
                found.append(name)
    elif isinstance(node, ast.ExceptHandler) and node.name and node.name not in found:
        found.append(node.name)
    for child in ast.iter_child_nodes(node):
        bindings(child, found)


def predict(source: str) -> tuple[str, ...]:
    """The `co_varnames` of the one function in `source`, near enough. Near enough is wrong."""
    module = ast.parse(source)
    function = next(
        one for one in module.body if isinstance(one, ast.FunctionDef | ast.AsyncFunctionDef)
    )
    found: list[str] = []
    arguments = function.args
    for one in [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]:
        found.append(one.arg)
    if arguments.vararg is not None:
        found.append(arguments.vararg.arg)
    if arguments.kwarg is not None:
        found.append(arguments.kwarg.arg)
    for statement in function.body:
        bindings(statement, found)
    return tuple(found)
