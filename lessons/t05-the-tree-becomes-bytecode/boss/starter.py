"""Start here. Copy this file somewhere, fill in `predict`, and run the grader against it.

    cp lessons/t05-the-tree-becomes-bytecode/boss/starter.py answer.py
    python lessons/t05-the-tree-becomes-bytecode/grade.py answer.py

`source` is a module with exactly one `def` in it. Return that function's `co_varnames`, in
order, without compiling anything.

Two suggestions, from watching people do this.

Work out the rules by experiment rather than by reading. You have a Python in front of you
and `compile(source, "<t>", "exec")` gives you the answer for any source you like, so the
loop is: guess a rule, write a function that would break it, compile it, see who was right.
The grader takes that tool away from your answer, not from you.

Get the parameters right first and run the grader. It will tell you the first function you
disagree with CPython about, which is a better place to start than a blank file.
"""

from __future__ import annotations

import ast


def predict(source: str) -> tuple[str, ...]:
    """The `co_varnames` of the one function in `source`."""
    module = ast.parse(source)
    function = next(
        one for one in module.body if isinstance(one, ast.FunctionDef | ast.AsyncFunctionDef)
    )
    found: list[str] = []
    # Parameters go first, and here are the plain ones to get you started. Four kinds are
    # missing: positional only, keyword only, `*rest` and `**kw`. `function.args` has a field
    # for each, and the order they end up in is not the order they are written in, which is
    # the first thing the grader will disagree with you about.
    for one in function.args.args:
        found.append(one.arg)
    # Then every other name the function binds, in the order the compiler first meets the
    # binding, which is a walk over `function.body` and is the rest of the fight.
    return tuple(found)
