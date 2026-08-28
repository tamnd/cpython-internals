"""The nbdiagram command.

`nbdiagram build` runs every lesson's `diagrams.py` and writes the `.excalidraw` and `.svg`
pair for each scene it defines. `nbdiagram check` runs the same scripts and fails if a
committed file has drifted, which is the step CI cares about.

Same structure as nbbuild, and for the same reason: a generated artifact that is also
committed is a lie waiting to happen unless something compares the two on every change.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .render import to_svg
from .scene import Scene

SCRIPT = "diagrams.py"
DEFAULT_ROOT = "lessons"
DIRECTORY = "diagrams"


def scripts(root: Path) -> list[Path]:
    """Every lesson's diagram script, in lesson order."""
    return sorted(root.glob(f"*/{SCRIPT}"))


def write(scene: Scene, directory: Path, *, check: bool = False) -> list[str]:
    """Write, or compare, the two files for one scene.

    The `.excalidraw` is the editable source and the `.svg` is what the lessons embed. Both
    are committed, because GitHub and Colab will render the second and neither will render
    the first.
    """
    directory.mkdir(parents=True, exist_ok=True)
    wanted = {
        directory / f"{scene.name}.excalidraw": scene.document(),
        directory / f"{scene.name}.svg": to_svg(scene),
    }
    problems = []
    for path, text in wanted.items():
        if not check:
            path.write_text(text)
        elif not path.exists():
            problems.append(f"{path} has not been built")
        elif path.read_text() != text:
            problems.append(f"{path} does not match its script, run `just diagrams`")
    return problems


def _run(path: Path, arguments: list[str]) -> int:
    return subprocess.run([sys.executable, str(path), *arguments], check=False).returncode


def _each(args, arguments: list[str]) -> int:
    root = Path(args.root)
    found = scripts(root)
    if not found:
        print(f"no {SCRIPT} under {root}", file=sys.stderr)
        return 0
    failed = [path for path in found if _run(path, arguments) != 0]
    print(f"{len(found)} lesson(s): {len(failed)} failed")
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nbdiagram",
        description="Build the lesson diagrams from the Python scripts that define them",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="regenerate every diagram")
    build.add_argument("--root", default=DEFAULT_ROOT, help="the lessons directory")
    build.set_defaults(func=lambda args: _each(args, []))

    check = sub.add_parser("check", help="fail if a committed diagram no longer matches its script")
    check.add_argument("--root", default=DEFAULT_ROOT, help="the lessons directory")
    check.set_defaults(func=lambda args: _each(args, ["--check"]))

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
