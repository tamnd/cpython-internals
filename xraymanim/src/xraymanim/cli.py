"""The xraymanim command.

`check` is cheap and needs nothing installed beyond this package. `render` needs manim and
ffmpeg and takes minutes, which is why they are separate subcommands and why only the first
one is in `just check`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .catalogue import ANIMATIONS, find, seconds
from .checks import check
from .render import RenderError, render


def command_list(args: argparse.Namespace) -> int:
    for storyboard in ANIMATIONS:
        print(
            f"{storyboard.slug:<28} {storyboard.seconds:5.1f}s  "
            f"{storyboard.lesson:<4} {storyboard.title}"
        )
    print(f"{len(ANIMATIONS)} animation(s), {seconds() / 60:.1f} minutes to watch")
    return 0


def command_check(args: argparse.Namespace) -> int:
    problems = check(Path(args.root))
    for problem in problems:
        print(problem, file=sys.stderr)
    print(f"{len(ANIMATIONS)} animation(s): {len(problems)} problem(s)")
    return 1 if problems else 0


def command_render(args: argparse.Namespace) -> int:
    root = Path(args.root)
    wanted = [find(slug) for slug in args.slugs] if args.slugs else list(ANIMATIONS)
    into = Path(args.into) if args.into else None
    failed = []
    for storyboard in wanted:
        print(f"rendering {storyboard.slug}, about {storyboard.seconds:.0f}s of video")
        try:
            written = render(storyboard.slug, root, quality=args.quality, into=into)
        except RenderError as error:
            print(error, file=sys.stderr)
            failed.append(storyboard.slug)
            continue
        print(f"  {written} ({written.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"{len(wanted)} animation(s): {len(failed)} failed")
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xraymanim",
        description="The animation library, its catalogue, and the renderer",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    listing = sub.add_parser("list", help="every animation, in course order, with its length")
    listing.set_defaults(func=command_list)

    checking = sub.add_parser("check", help="the storyboards, the scene files and the GIFs")
    checking.add_argument("--root", default=".", help="the repository root")
    checking.set_defaults(func=command_check)

    rendering = sub.add_parser("render", help="render animations to GIF, slowly")
    rendering.add_argument("slugs", nargs="*", help="which ones, or all of them")
    rendering.add_argument("--root", default=".", help="the repository root")
    rendering.add_argument("--quality", default="medium", help="low, medium or high")
    rendering.add_argument("--into", default="", help="write somewhere other than anim/rendered")
    rendering.set_defaults(func=command_render)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
