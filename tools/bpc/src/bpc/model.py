"""The grammar, as plain data with line numbers attached.

CPython's own `Parser/asdl.py` does the parsing. Writing a second ASDL parser here would
be writing a second opinion about what `Parser/Python.asdl` means, and the whole point of
generating this material is that there is only one opinion in the repository.

What `asdl.py` does not give back is where anything was written. It parses to a tree of
`Module`, `Type`, `Constructor` and `Field` with no line numbers on any of them, and a
specification that cannot point at the line it came from is a specification a reader has
to take on trust. So this module runs `asdl.py`'s own tokenizer a second time, which does
carry line numbers, and walks the two in step. The walk asserts that the names line up in
order, so a change in upstream that this code cannot follow stops the build rather than
quietly producing citations that point at the wrong lines.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from types import ModuleType

#: Where the two files live inside a CPython checkout.
ASDL_MODULE = Path("Parser") / "asdl.py"
GRAMMAR_FILE = Path("Parser") / "Python.asdl"

#: The four types ASDL has built in, which no definition in the file declares. Everything
#: else named as a field type is a definition in the same file, and `asdl.py` checks that.
BUILTIN_TYPES = frozenset({"identifier", "int", "string", "constant"})


class GrammarError(RuntimeError):
    """The grammar could not be read, or could not be lined up with its own source."""


@dataclass(frozen=True)
class Field:
    """One field of one node, in the order it is written."""

    type: str
    name: str
    optional: bool
    sequence: bool
    marks: str = ""

    @property
    def builtin(self) -> bool:
        """Whether the field's type is one of ASDL's four, rather than a node type."""
        return self.type in BUILTIN_TYPES

    @property
    def elements_optional(self) -> bool:
        """Whether this is a sequence whose slots are allowed to be empty.

        There is exactly one of these in the grammar and it is easy to miss, because
        `asdl.py` keeps only the last quantifier in `seq` and `opt`, so `expr?* kw_defaults`
        arrives looking like an ordinary sequence. The `?` is still in `quantifiers` and it
        is load bearing: `kw_defaults` holds one slot per keyword only argument, and the
        slot is `None` for an argument that has no default.
        """
        return self.sequence and "?" in self.marks

    @property
    def kind(self) -> str:
        """How many values the field holds, in a few words.

        A port needs this and needs it separately from the type. A sequence field is
        always present and may be empty, an optional field may be absent altogether, and
        those two are different in a way that `expr* body` and `expr? returns` hide from
        anybody reading quickly.
        """
        if self.elements_optional:
            return "sequence of optional"
        if self.sequence:
            return "sequence"
        return "optional" if self.optional else "required"

    @property
    def notation(self) -> str:
        """The field as ASDL writes it, `expr? returns` and the like."""
        return f"{self.type}{self.marks} {self.name}"


@dataclass(frozen=True)
class Constructor:
    """One concrete node kind, which is one alternative of a sum."""

    name: str
    fields: tuple[Field, ...]
    line: int

    @property
    def signature(self) -> str:
        """The constructor as ASDL writes it, arguments and all."""
        inner = ", ".join(field.notation for field in self.fields)
        return f"{self.name}({inner})" if self.fields else self.name


@dataclass(frozen=True)
class Definition:
    """One named type in the grammar, either a sum of constructors or a single product."""

    name: str
    constructors: tuple[Constructor, ...]
    fields: tuple[Field, ...]
    attributes: tuple[Field, ...]
    line: int
    end_line: int

    @property
    def sum(self) -> bool:
        """Whether this is a choice between constructors rather than a single shape."""
        return bool(self.constructors)

    @property
    def kind(self) -> str:
        return "sum" if self.sum else "product"


@dataclass(frozen=True)
class Grammar:
    """Everything in `Parser/Python.asdl`, in the order the file writes it."""

    name: str
    definitions: tuple[Definition, ...]
    line: int
    path: str = str(GRAMMAR_FILE)

    def definition(self, name: str) -> Definition:
        for one in self.definitions:
            if one.name == name:
                return one
        raise KeyError(name)

    @property
    def node_count(self) -> int:
        """How many concrete node kinds there are, which is what a port has to build."""
        return sum(max(len(one.constructors), 1) for one in self.definitions)


def load_asdl(tree: Path) -> ModuleType:
    """Import CPython's `Parser/asdl.py` from the pinned checkout.

    By path rather than by adding `Parser` to `sys.path`, because that directory also holds
    `pegen` and a handful of other modules with names general enough to shadow something.
    The module is cached under a name that cannot collide with anything installed.
    """
    path = tree / ASDL_MODULE
    if not path.is_file():
        raise GrammarError(f"no {ASDL_MODULE} in {tree}, so there is nothing to compile from")
    name = "bpc._cpython_asdl"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GrammarError(f"{path} could not be loaded as a module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


#: How `asdl.py` names its two quantifiers, and what the grammar file writes for each.
QUANTIFIERS = {"SEQUENCE": "*", "OPTIONAL": "?"}


def _marks(one: object) -> str:
    """The quantifiers after a field's type, in the order the grammar writes them.

    `seq` and `opt` would nearly do, but they are set from the last quantifier only, so
    they turn `expr?* kw_defaults` into `expr* kw_defaults` and lose the fact that the
    slots of that sequence may be empty. The full list is on the field, so use it.
    """
    quantifiers = getattr(one, "quantifiers", None)
    if not quantifiers:
        return "*" if one.seq else "?" if one.opt else ""
    return "".join(QUANTIFIERS[str(mark.name)] for mark in quantifiers)


def _fields(raw: object) -> tuple[Field, ...]:
    return tuple(
        Field(
            type=one.type,
            name=one.name,
            optional=bool(one.opt),
            sequence=bool(one.seq),
            marks=_marks(one),
        )
        for one in raw
    )


class _Lines:
    """Where each name in the grammar was written, from `asdl.py`'s own tokenizer.

    The tokenizer yields `(kind, value, lineno)` in file order, which is the same order
    the parsed tree is in, so lining them up is a forward scan with no lookahead. Anything
    that does not line up raises, because a citation pointing at the wrong line is worse
    than no citation.
    """

    def __init__(self, asdl: ModuleType, text: str) -> None:
        self._kinds = asdl.TokenKind
        self._tokens = list(asdl.tokenize_asdl(text))
        self._at = 0

    @property
    def last_line(self) -> int:
        return self._tokens[-1].lineno if self._tokens else 0

    def module(self, name: str) -> int:
        """The line the `module NAME {` header is on."""
        return self.constructor(name)

    def definition(self, name: str) -> int:
        """The line a definition's name is on.

        A type name followed by `=` and nothing else. The `=` is what makes this a
        definition rather than a use: `arg` is a definition on one line and the type of
        three fields of `arguments` several lines earlier, and taking the first `arg` in
        the file would put every citation for it on the wrong line.
        """
        index = self._find_definition(name, self._at)
        if index is None:
            raise self._lost(name)
        self._at = index + 1
        return self._tokens[index].lineno

    def constructor(self, name: str) -> int:
        """The line a constructor's name is on.

        No `=` check here, because a constructor name is capitalised and a capitalised
        name in this grammar is only ever a constructor being declared.
        """
        while self._at < len(self._tokens):
            token = self._tokens[self._at]
            self._at += 1
            if token.kind == self._kinds.ConstructorId and token.value == name:
                return token.lineno
        raise self._lost(name)

    def peek_definition(self, name: str) -> int | None:
        """The line the next definition starts on, without consuming anything."""
        index = self._find_definition(name, self._at)
        return None if index is None else self._tokens[index].lineno

    def _find_definition(self, name: str, start: int) -> int | None:
        for index in range(start, len(self._tokens) - 1):
            token = self._tokens[index]
            if token.kind != self._kinds.TypeId or token.value != name:
                continue
            if self._tokens[index + 1].kind == self._kinds.Equals:
                return index
        return None

    def _lost(self, name: str) -> GrammarError:
        return GrammarError(
            f"the tokenizer never reached {name!r}, so the grammar and its own source "
            "have stopped lining up and the line numbers cannot be trusted"
        )


def parse(tree: Path) -> Grammar:
    """Read `Parser/Python.asdl` from the pinned checkout, with line numbers attached."""
    asdl = load_asdl(tree)
    path = tree / GRAMMAR_FILE
    if not path.is_file():
        raise GrammarError(f"no {GRAMMAR_FILE} in {tree}, so there is nothing to compile from")
    text = path.read_text(encoding="utf-8")
    module = asdl.parse(str(path))

    lines = _Lines(asdl, text)
    module_line = lines.module(module.name)

    names = [one.name for one in module.dfns]
    definitions: list[Definition] = []
    for index, dfn in enumerate(module.dfns):
        start = lines.definition(dfn.name)
        value = dfn.value
        constructors = tuple(
            Constructor(
                name=one.name,
                fields=_fields(one.fields),
                line=lines.constructor(one.name),
            )
            for one in getattr(value, "types", [])
        )
        following = names[index + 1] if index + 1 < len(names) else None
        after = lines.peek_definition(following) if following else None
        end = (after - 1) if after else lines.last_line
        definitions.append(
            Definition(
                name=dfn.name,
                constructors=constructors,
                fields=_fields(getattr(value, "fields", [])),
                attributes=_fields(getattr(value, "attributes", [])),
                line=start,
                end_line=max(end, start),
            )
        )

    return Grammar(name=module.name, definitions=tuple(definitions), line=module_line)


@cache
def grammar(tree: Path) -> Grammar:
    """`parse`, remembered, because a build reads the grammar once per section."""
    return parse(tree)
