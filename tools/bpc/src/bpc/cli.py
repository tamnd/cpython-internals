"""The bpc command.

`bpc build` expands every source document and writes the blueprint next to it. `bpc check`
expands the same documents and fails if what is committed has drifted, which is the half CI
runs.

Two commands rather than one that repairs itself, for the same reason the notebooks and the
diagrams work this way: a checker that silently fixes what it finds checks nothing, and the
diff is the thing a person is supposed to read before the pin moves.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from refcheck.tree import TreeNotFound, find_tree

from .model import GrammarError, grammar
from .template import OUTPUT, SOURCES, Source, TemplateError, expand, find


def _expanded(sources: list[Source], tree: Path) -> list[tuple[Source, str]]:
    parsed = grammar(tree)
    return [(source, expand(source, parsed)) for source in sources]


def command_build(args: argparse.Namespace) -> int:
    sources, tree = _inputs(args)
    if sources is None:
        return 0
    for source, text in _expanded(sources, tree):
        source.output.write_text(text, encoding="utf-8")
        print(f"wrote {source.output}")
    print(f"{len(sources)} blueprint(s) generated")
    return 0


def command_check(args: argparse.Namespace) -> int:
    sources, tree = _inputs(args)
    if sources is None:
        return 0
    problems = []
    for source, text in _expanded(sources, tree):
        if not source.output.exists():
            problems.append(f"{source.output} has not been built, run `just build-blueprints`")
        elif source.output.read_text(encoding="utf-8") != text:
            problems.append(
                f"{source.output} no longer matches {source.path}, "
                "run `just build-blueprints` and read the diff"
            )
    for problem in problems:
        print(problem, file=sys.stderr)
    print(f"{len(sources)} blueprint(s): {len(problems)} out of date")
    return 1 if problems else 0


def command_list(args: argparse.Namespace) -> int:
    sources, _ = _inputs(args, need_tree=False)
    if sources is None:
        return 0
    for source in sources:
        print(f"{source.path} -> {source.output}: {', '.join(source.blocks())}")
    return 0


def _inputs(
    args: argparse.Namespace, *, need_tree: bool = True
) -> tuple[list[Source] | None, Path]:
    sources = find(Path(args.sources))
    if not sources:
        print(f"no source documents under {args.sources}", file=sys.stderr)
        return None, Path()
    if not need_tree:
        return sources, Path()
    return sources, find_tree(getattr(args, "tree", None))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bpc",
        description="Generate the mechanical sections of a blueprint from CPython's own inputs",
    )
    parser.add_argument("--sources", default=str(SOURCES), help=f"defaults to {SOURCES}")
    parser.add_argument("--tree", default=None, help="a CPython checkout at the pinned tag")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help=f"expand every source document into {OUTPUT}")
    build.set_defaults(func=command_build)

    check = sub.add_parser("check", help="fail if a committed blueprint has drifted")
    check.set_defaults(func=command_check)

    listing = sub.add_parser("list", help="show the source documents and the blocks they use")
    listing.set_defaults(func=command_list)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except TreeNotFound as error:
        print(error, file=sys.stderr)
        return 2
    except (GrammarError, TemplateError) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
