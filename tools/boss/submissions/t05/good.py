"""A submission that passes the T05 fight. Spoilers, obviously.

CI needs one of these. A grader nobody has ever seen pass is a grader that might be
impossible, and one nobody has seen fail is a grader that says yes to anything, so both
exist and both run on every pull request.

If you are here to do the fight, this is the answer. Close the tab. The fight is worth about
an hour and this file takes about a minute to read, and the hour is the part that teaches you
something.

The rule it implements, in one paragraph. A function's local slots start with its parameters:
the positional ones in order, then the keyword only ones, then `*args`, then `**kwargs`. After
that come the other names the function binds, in the order the compiler first meets the
binding while walking the tree. Meeting order is not always source order, and that is the
whole fight: an assignment looks at its value before its target, an augmented assignment does
the opposite, a `try` looks at its `else` before its `except` handlers, a list comprehension
is part of the function while a generator expression is not, and a name declared `global`
never gets a slot at all.
"""

from __future__ import annotations

import ast


class Layout:
    """The names a function binds, in the order the compiler first meets each one."""

    def __init__(self) -> None:
        self.names: list[str] = []
        self.declared: set[str] = set()

    def bind(self, name: str) -> None:
        if name in self.declared or name in self.names:
            return
        self.names.append(name)

    def block(self, body: list[ast.stmt]) -> None:
        for one in body:
            self.statement(one)

    def statement(self, node: ast.stmt) -> None:
        """One statement, visited in the order the compiler visits its parts."""
        if isinstance(node, ast.Global):
            self.declared.update(node.names)
        elif isinstance(node, ast.Assign):
            self.expression(node.value)
            for target in node.targets:
                self.target(target)
        elif isinstance(node, ast.AnnAssign):
            # An annotation with no value is a promise about a name, not a binding of it, so
            # `counted: int` on its own leaves no slot behind.
            if node.value is not None:
                self.expression(node.value)
                self.target(node.target)
        elif isinstance(node, ast.AugAssign):
            # The other way round from a plain assignment, because `count += step` reads the
            # target before it can add anything to it.
            self.target(node.target)
            self.expression(node.value)
        elif isinstance(node, ast.For | ast.AsyncFor):
            self.expression(node.iter)
            self.target(node.target)
            self.block(node.body)
            self.block(node.orelse)
        elif isinstance(node, ast.While | ast.If):
            self.expression(node.test)
            self.block(node.body)
            self.block(node.orelse)
        elif isinstance(node, ast.With | ast.AsyncWith):
            for item in node.items:
                self.expression(item.context_expr)
                if item.optional_vars is not None:
                    self.target(item.optional_vars)
            self.block(node.body)
        elif isinstance(node, ast.Try | ast.TryStar):
            # The surprising one. The `else` block is visited straight after the body, before
            # any handler, so a name bound in `else` gets a lower slot than one bound in
            # `except`, whatever the source order looks like.
            self.block(node.body)
            self.block(node.orelse)
            for handler in node.handlers:
                if handler.type is not None:
                    self.expression(handler.type)
                if handler.name:
                    self.bind(handler.name)
                self.block(handler.body)
            self.block(node.finalbody)
        elif isinstance(node, ast.Import | ast.ImportFrom):
            for alias in node.names:
                self.bind(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.Delete):
            # `del gone` still needs a slot. The name has to exist for the delete to have
            # anything to complain about at runtime.
            for target in node.targets:
                self.target(target)
        elif isinstance(node, ast.Match):
            self.expression(node.subject)
            for case in node.cases:
                self.pattern(case.pattern)
                if case.guard is not None:
                    self.expression(case.guard)
                self.block(case.body)
        else:
            # Return, Expr, Raise, Assert, Pass and the rest bind nothing themselves. All
            # that matters is any walrus hiding inside them, and field order finds those.
            for child in ast.iter_child_nodes(node):
                self.expression(child)

    def target(self, node: ast.AST) -> None:
        """The left hand side of an assignment, which is not always a name."""
        if isinstance(node, ast.Name):
            self.bind(node.id)
        elif isinstance(node, ast.Tuple | ast.List):
            for one in node.elts:
                self.target(one)
        elif isinstance(node, ast.Starred):
            self.target(node.value)
        else:
            # `rows[i] = value` and `thing.field = value` bind nothing. What they do is
            # evaluate the bits in front of the assignment, which can hold a walrus.
            for child in ast.iter_child_nodes(node):
                self.expression(child)

    def pattern(self, node: ast.AST) -> None:
        """A match case, whose captures are bindings in the order they are written."""
        if isinstance(node, ast.MatchAs):
            if node.pattern is not None:
                self.pattern(node.pattern)
            if node.name:
                self.bind(node.name)
        elif isinstance(node, ast.MatchStar):
            if node.name:
                self.bind(node.name)
        elif isinstance(node, ast.MatchMapping):
            for key in node.keys:
                self.expression(key)
            for one in node.patterns:
                self.pattern(one)
            if node.rest:
                self.bind(node.rest)
        elif isinstance(node, ast.MatchClass):
            self.expression(node.cls)
            for one in [*node.patterns, *node.kwd_patterns]:
                self.pattern(one)
        elif isinstance(node, ast.MatchSequence | ast.MatchOr):
            for one in node.patterns:
                self.pattern(one)
        elif isinstance(node, ast.MatchValue):
            self.expression(node.value)

    def comprehensions(self, generators: list[ast.comprehension]) -> None:
        for one in generators:
            self.expression(one.iter)
            self.target(one.target)
            for condition in one.ifs:
                self.expression(condition)

    def expression(self, node: ast.AST) -> None:
        """Anything that produces a value, visited in the order its parts are visited."""
        if isinstance(node, ast.NamedExpr):
            self.expression(node.value)
            self.target(node.target)
        elif isinstance(node, ast.ListComp | ast.SetComp):
            # Inlined since 3.12, so the loop variable is a local of the function it is
            # written in, and it is bound before the element expression is looked at.
            self.comprehensions(node.generators)
            self.expression(node.elt)
        elif isinstance(node, ast.DictComp):
            self.comprehensions(node.generators)
            self.expression(node.key)
            self.expression(node.value)
        elif isinstance(node, ast.GeneratorExp):
            # Not inlined. It is a code object of its own, so nothing inside binds here
            # except the outermost iterable, which is evaluated where it is written.
            self.expression(node.generators[0].iter)
        elif isinstance(node, ast.Lambda):
            pass
        else:
            for child in ast.iter_child_nodes(node):
                self.expression(child)


def predict(source: str) -> tuple[str, ...]:
    """The `co_varnames` of the one function in `source`, worked out rather than compiled."""
    module = ast.parse(source)
    function = next(
        one for one in module.body if isinstance(one, ast.FunctionDef | ast.AsyncFunctionDef)
    )
    layout = Layout()
    arguments = function.args
    # Parameters first, and in this order rather than the order they are written: the
    # positional ones, then the keyword only ones, then `*rest`, then `**kw`.
    for one in [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]:
        layout.bind(one.arg)
    if arguments.vararg is not None:
        layout.bind(arguments.vararg.arg)
    if arguments.kwarg is not None:
        layout.bind(arguments.kwarg.arg)
    # Defaults and annotations are evaluated where the `def` is written, not inside the
    # function, so a walrus in a default binds in the enclosing scope and not here.
    layout.block(function.body)
    return tuple(layout.names)
