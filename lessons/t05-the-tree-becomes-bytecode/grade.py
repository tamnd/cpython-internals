#!/usr/bin/env python3
"""The T05 boss fight. Work out a function's local slots without compiling it.

The lesson watched the compiler build a code object. `co_varnames` is one of the tables it
builds: the layout of the frame's local slots, decided while your file is being compiled and
fixed for good by the time anything runs. This asks you to produce that layout yourself, from
the source text, for a function nobody has shown you.

Write a file with one function in it:

    def predict(source: str) -> tuple[str, ...]:
        ...

`source` is a module with exactly one `def` in it and nothing else. Return the `co_varnames`
of that function, in order. Start from `boss/starter.py` next to this file.

    python grade.py my_answer.py
    python grade.py my_answer.py --seed 7

You get a fixed set of hand written functions and a pile of randomly generated ones, so
memorising answers does not work. Every answer is checked against what CPython actually
builds, on the interpreter you are running, so the grader cannot be more or less right than
your Python is.

You may use `ast`. You may not use `compile`, `eval`, `exec` or `symtable`, and the grader
says so if you do. That fence is knee high on purpose. Getting round it is easy and the only
person you would be fooling is the one doing the reading.

The functions you get are restricted, so that the rules stay findable in an evening. No
nested `def`, no `lambda`, no `class`, no `nonlocal`, and no `return` inside a `try`. That
last one is not fussiness: a `return` there makes the compiler lay the `finally` block down
early, which moves the slots around for a reason that has nothing to do with the rules this
is asking about. Everything else the language can do is fair game, including the three or
four orderings that are genuinely surprising the first time you meet them.
"""

from __future__ import annotations

import argparse
import ast
import random
import sys
from pathlib import Path

#: Builtins that would answer the question instead of you. `compile` is the obvious one and
#: `eval` and `exec` are the same thing wearing a hat.
BANNED_CALLS = ("compile", "eval", "exec", "__import__")

#: Modules that hold the answer. `symtable` is the compiler's own first pass, `dis` and
#: `marshal` both need a code object, and the rest are doors back to `compile`.
BANNED_IMPORTS = (
    "symtable",
    "dis",
    "marshal",
    "inspect",
    "types",
    "builtins",
    "importlib",
    "ctypes",
    "_testinternalcapi",
)

#: The hand written half of the corpus. Every one of these is here because it catches a rule
#: that is easy to get wrong, and the name is what you see when you get it wrong, so the name
#: is the hint. They are in rough order of how surprising they are.
SNIPPETS: tuple[tuple[str, str], ...] = (
    (
        "parameters-come-first",
        "def f(a, b, c=1):\n    d = 2\n",
    ),
    (
        "star-args-go-after-keyword-only",
        "def f(a, b=1, *rest, c, d=2, **kw):\n    e = 3\n",
    ),
    (
        "positional-only-are-still-parameters",
        "def f(a, /, b, *, c):\n    pass\n",
    ),
    (
        "a-name-only-read-gets-no-slot",
        "def f():\n    total = first + second\n",
    ),
    (
        "the-value-is-looked-at-before-the-target",
        "def f():\n    total = (part := 1) + (piece := 2)\n",
    ),
    (
        "an-augmented-assignment-goes-the-other-way",
        "def f():\n    count += (step := 1)\n",
    ),
    (
        "else-is-looked-at-before-except",
        "def f():\n"
        "    try:\n"
        "        opened = 1\n"
        "    except ValueError as problem:\n"
        "        handled = 2\n"
        "    else:\n"
        "        fine = 3\n"
        "    finally:\n"
        "        closed = 4\n",
    ),
    (
        "a-list-comprehension-is-part-of-the-function",
        "def f():\n    squares = [item for item in rows]\n",
    ),
    (
        "a-generator-expression-is-not",
        "def f():\n    lazy = (item for item in rows)\n",
    ),
    (
        "an-annotation-with-no-value-binds-nothing",
        "def f():\n    counted: int\n    named: str = 'x'\n",
    ),
    (
        "global-means-no-slot-at-all",
        "def f():\n    global shared\n    shared = 1\n    private = 2\n",
    ),
    (
        "deleting-a-name-still-needs-a-slot",
        "def f():\n    del gone\n",
    ),
    (
        "an-import-inside-a-function-is-a-local",
        "def f():\n    import os\n    import sys as system\n    from json import loads as parse\n",
    ),
    (
        "the-loop-target-comes-after-what-it-loops-over",
        "def f():\n    for row in (source := []):\n        seen = row\n",
    ),
    (
        "match-captures-in-the-order-they-are-written",
        "def f():\n"
        "    match (subject := []):\n"
        "        case [head, *tail] if (checked := 1):\n"
        "            pass\n"
        "        case {'k': found}:\n"
        "            pass\n",
    ),
    (
        "a-name-bound-twice-only-gets-one-slot",
        "def f(a):\n    a = 1\n    b = 2\n    b = 3\n",
    ),
)

#: The pool the generator draws names from. Words rather than single letters, because a
#: failure message naming `gamma` and `delta` is easier to read than one naming `g` and `d`.
WORDS = (
    "alpha",
    "beta",
    "gamma",
    "delta",
    "epsilon",
    "zeta",
    "eta",
    "theta",
    "iota",
    "kappa",
    "lam",
    "mu",
    "nu",
    "xi",
    "rho",
    "sigma",
    "tau",
    "phi",
    "chi",
    "psi",
)

#: Expressions the generator drops in where a value is needed. None of them bind anything, so
#: they are noise on purpose: the question is which names get slots, and these get none.
VALUES = ("[]", "0", "rows", "source.field", "gather(1)", "{}", "'text'")


class Refused(Exception):
    """The submission used something that would answer the question for it."""


def indent(body: list[str]) -> list[str]:
    return ["    " + line for line in body] or ["    pass"]


def statement(rng: random.Random, names: list[str], depth: int = 0) -> list[str]:
    """One randomly chosen statement, as a list of lines, unindented.

    Every shape here is one that appears in the fixed corpus above, so a reader who has
    worked out the fixed half is not ambushed by a construct they have never seen. What the
    random half adds is combinations, and ordering between statements, which is where
    a rule that is nearly right stops being right.
    """
    pick = rng.choice(names)
    other = rng.choice(names)
    value = rng.choice(VALUES)
    kinds = [
        [f"{pick} = {value}"],
        [f"{pick} = {other} = {value}"],
        [f"{pick} += 1"],
        [f"{pick} = ({other} := {value})"],
        [f"{pick}: int"],
        [f"{pick}: int = {value}"],
        [f"del {pick}"],
        [f"import os as {pick}"],
        [f"from json import loads as {pick}"],
        [f"{pick} = [{other} for {other} in {value}]"],
        [f"{pick} = ({other} for {other} in {value})"],
        [f"{pick} = {{{other}: {pick}0 for {other}, {pick}0 in {value}}}"],
        [f"assert ({pick} := 1), ({other} := 2)"],
    ]
    if depth < 2:
        kinds += [
            [f"for {pick} in {value}:", *indent(statement(rng, names, depth + 1))],
            [
                f"if ({pick} := {value}):",
                *indent(statement(rng, names, depth + 1)),
                "else:",
                *indent(statement(rng, names, depth + 1)),
            ],
            [
                f"with opened({value}) as {pick}, opened({value}) as {other}:",
                *indent(statement(rng, names, depth + 1)),
            ],
            [
                "try:",
                *indent(statement(rng, names, depth + 1)),
                f"except ValueError as {pick}:",
                *indent(statement(rng, names, depth + 1)),
                "else:",
                *indent(statement(rng, names, depth + 1)),
                "finally:",
                *indent(statement(rng, names, depth + 1)),
            ],
            [
                f"match {value}:",
                f"    case [{pick}, *{other}]:",
                "        pass",
                f"    case {{'k': {pick}1}}:",
                "        pass",
            ],
        ]
    return rng.choice(kinds)


def signature(rng: random.Random, names: list[str]) -> str:
    """A random parameter list, sometimes with the awkward parts in it."""
    taken = rng.sample(names, rng.randint(0, 3))
    parts = list(taken)
    if parts and rng.random() < 0.4:
        parts[-1] += "=1"
    if rng.random() < 0.3:
        parts.append("*" + rng.choice([one for one in names if one not in taken] or ["rest"]))
    elif rng.random() < 0.3 and parts:
        parts.append("*")
        parts.append(rng.choice([one for one in names if one not in taken] or ["only"]))
    if rng.random() < 0.3:
        parts.append("**" + rng.choice([one for one in names if one not in taken] or ["kw"]))
    return ", ".join(parts)


def generated(rng: random.Random) -> str:
    """One random function, valid Python, never run and only ever compiled."""
    names = rng.sample(WORDS, 6)
    lines = [f"def f({signature(rng, names)}):"]
    if rng.random() < 0.25:
        lines.append("    global shared")
    for _ in range(rng.randint(1, 4)):
        lines += indent(statement(rng, names))
    return "\n".join(lines) + "\n"


def corpus(seed: int, count: int) -> list[tuple[str, str]]:
    """The fixed snippets, then `count` generated ones, all with names for the report."""
    rng = random.Random(seed)
    found = list(SNIPPETS)
    while len(found) < len(SNIPPETS) + count:
        source = generated(rng)
        try:
            truth(source)
        except SyntaxError:
            # The generator can put a `global` after the name it names, and a few other
            # shapes the language refuses. Throwing those away is cheaper than teaching the
            # generator every rule about where a statement is allowed to go.
            continue
        found.append((f"generated-{len(found) - len(SNIPPETS) + 1}", source))
    return found


def truth(source: str) -> tuple[str, ...]:
    """What CPython actually lays out, which is the only answer key there is."""
    room: dict[str, object] = {}
    # The grader is allowed to compile. That is the whole asymmetry: it knows the answer
    # because it asked the compiler, and the submission has to work it out instead.
    exec(compile(source, "<boss>", "exec"), room)
    function = next(one for one in room.values() if hasattr(one, "__code__"))
    return function.__code__.co_varnames


def refusals(tree: ast.Module) -> list[str]:
    """Everything in the submission that would answer the question instead of the reader."""
    found = []
    for node in ast.walk(tree):
        call = isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        if call and node.func.id in BANNED_CALLS:
            found.append(f"calls {node.func.id}() on line {node.lineno}")
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in BANNED_IMPORTS:
                    found.append(f"imports {alias.name} on line {node.lineno}")
        brought = isinstance(node, ast.ImportFrom) and node.module
        if brought and node.module.split(".")[0] in BANNED_IMPORTS:
            found.append(f"imports from {node.module} on line {node.lineno}")
    return found


def load(path: Path):
    """The reader's `predict`, after checking they did not import the answer."""
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError as problem:
        raise Refused(f"{path} does not parse: {problem}") from problem
    refused = refusals(tree)
    if refused:
        raise Refused(
            f"{path} " + ", and ".join(refused) + ".\n"
            "The point of the fight is to work the layout out, so those are off the table."
        )
    room: dict[str, object] = {"__name__": "__answer__", "__file__": str(path)}
    # Running the submission is the only way to get at its `predict`, and anything it does
    # on the way is the reader's own business on the reader's own machine.
    exec(compile(text, str(path), "exec"), room)
    predict = room.get("predict")
    if not callable(predict):
        raise Refused(f"{path} does not define a function called predict")
    return predict


def answer(predict, source: str) -> tuple[str, ...]:
    """Call the reader's function and insist on a sequence of strings coming back."""
    given = predict(source)
    if isinstance(given, list):
        given = tuple(given)
    if not isinstance(given, tuple) or any(not isinstance(one, str) for one in given):
        raise Refused(f"predict returned {given!r}, and it has to return a tuple of strings")
    return given


def disagreement(name: str, source: str, wanted: tuple[str, ...], got: tuple[str, ...]) -> str:
    """The failure message. Specific enough to act on without reading the grader."""
    lines = [f"Your predict() disagrees with CPython on '{name}'.", "", source.rstrip(), ""]
    lines.append(f"  CPython lays out {wanted}")
    lines.append(f"  you said         {got}")
    for slot, (here, there) in enumerate(zip(wanted, got, strict=False)):
        if here != there:
            lines.append(
                f"  first difference at slot {slot}: CPython has {here!r}, you have {there!r}"
            )
            return "\n".join(lines)
    shorter, longer = sorted((len(got), len(wanted)))
    rest = wanted[shorter:] if len(wanted) > len(got) else got[shorter:]
    side = "missing" if len(wanted) > len(got) else "extra"
    verb = "is" if longer - shorter == 1 else "are"
    lines.append(
        f"  the first {shorter} agree, and then there {verb} {longer - shorter} {side}: {rest}"
    )
    return "\n".join(lines)


def grade(path: Path, seed: int, count: int) -> tuple[int, str]:
    """Run one submission against the whole corpus and hand back an exit code and a report."""
    try:
        predict = load(path)
    except Refused as problem:
        return 1, str(problem)
    cases = corpus(seed, count)
    for name, source in cases:
        wanted = truth(source)
        try:
            got = answer(predict, source)
        except Refused as problem:
            return 1, f"On '{name}':\n\n{source.rstrip()}\n\n{problem}"
        except Exception as problem:
            # Anything at all, because a submission halfway through being written raises
            # everything, and "AttributeError on generated-12" is the useful thing to say.
            kind = type(problem).__name__
            return 1, (
                f"Your predict() raised {kind} on '{name}':\n\n{source.rstrip()}\n\n  {problem}"
            )
        if got != wanted:
            return 1, disagreement(name, source, wanted, got)
    return 0, (
        f"All {len(cases)} functions agree with CPython, "
        f"{len(SNIPPETS)} written by hand and {count} generated from seed {seed}."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("submission", type=Path, help="your file, the one with predict() in it")
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="the seed for the generated half, random by default so it is different every run",
    )
    parser.add_argument("--count", type=int, default=40, help="how many generated functions")
    args = parser.parse_args(argv)
    seed = random.randrange(1_000_000) if args.seed is None else args.seed
    code, report = grade(args.submission, seed, args.count)
    print(report, file=sys.stderr if code else sys.stdout)
    if code:
        again = f"\nRun it again with --seed {seed} to get the same functions back."
        print(again, file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
