"""The command line.

Five subcommands, and they are meant to be run in this order.

    wasmprobe native   --into probes/pyodide
    wasmprobe browser  --into probes/pyodide
    wasmprobe report   probes/pyodide --into probes/pyodide/report.md
    wasmprobe notebook --into probes/pyodide/probe.ipynb
    wasmprobe check    probes/pyodide

The last one is the one CI runs. It reads the two recordings and fails when a check the
lessons depend on works natively and not in the browser, which is the only difference worth
stopping a build over, and when the report or the notebook has fallen behind the checks.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import browser, native, notebook, report
from .checks import CHECKS
from .result import Run

#: The file names inside the results directory.
NATIVE = "native.json"
BROWSER = "pyodide.json"
REPORT = "report.md"
NOTEBOOK = "probe.ipynb"


def _load(room: Path) -> tuple[Run, Run]:
    here, there = room / NATIVE, room / BROWSER
    for path in (here, there):
        if not path.exists():
            raise SystemExit(f"no recording at {path}, run wasmprobe native and browser first")
    return Run.load(here), Run.load(there)


def _native(args: argparse.Namespace) -> int:
    run = native.run()
    path = run.write(Path(args.into) / NATIVE)
    worked = sum(1 for one in run.outcomes.values() if one.worked)
    print(f"{path}: {worked} of {len(run.outcomes)} checks worked on CPython {run.python}")
    return 0


def _browser(args: argparse.Namespace) -> int:
    problem = browser.ready()
    if problem:
        print(f"cannot run the browser probe: {problem}", file=sys.stderr)
        return 1
    run = browser.run()
    path = run.write(Path(args.into) / BROWSER)
    worked = sum(1 for one in run.outcomes.values() if one.worked)
    print(f"{path}: {worked} of {len(run.outcomes)} checks worked on Pyodide {run.python}")
    return 0


def _notebook(args: argparse.Namespace) -> int:
    path = notebook.write(Path(args.into))
    print(f"{path}: the checks as a notebook somebody can run in their own browser")
    return 0


def _report(args: argparse.Namespace) -> int:
    here, there = _load(Path(args.results))
    body = report.markdown(here, there)
    if args.into:
        path = Path(args.into)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        print(f"{path}: {report.summary(here, there)}")
    else:
        print(body, end="")
    return 0


def _stale(room: Path) -> list[str]:
    """Generated files in the results directory that no longer match the checks."""
    here, there = _load(room)
    wanted = {REPORT: report.markdown(here, there), NOTEBOOK: notebook.render()}
    found = []
    for name, body in wanted.items():
        path = room / name
        if not path.exists() or path.read_text(encoding="utf-8") != body:
            found.append(name)
    return found


def _check(args: argparse.Namespace) -> int:
    room = Path(args.results)
    here, there = _load(room)
    print(report.summary(here, there))
    stale = _stale(room)
    if stale:
        print("", file=sys.stderr)
        print(f"out of date: {', '.join(stale)}. Run just build-probe.", file=sys.stderr)
    broken = report.regressions(here, there)
    if not broken:
        return 1 if stale else 0
    print("", file=sys.stderr)
    print("Checks the lessons need that the browser cannot do:", file=sys.stderr)
    for check in broken:
        outcome = there.outcomes[check.key]
        print(f"  {check.key}: {outcome.status}. {check.costs}", file=sys.stderr)
    print("", file=sys.stderr)
    print(
        "Record a fresh pair and update the report, or move those experiments to Tier 1.",
        file=sys.stderr,
    )
    return 1


def _list(args: argparse.Namespace) -> int:
    for check in CHECKS:
        print(f"{check.key:22} {check.weight:6} {check.question}")
    return 0


def build() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wasmprobe", description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)

    here = subs.add_parser("native", help="run the checks on this interpreter")
    here.add_argument("--into", default="probes/pyodide", help="directory to write the run into")
    here.set_defaults(handler=_native)

    there = subs.add_parser("browser", help="run the checks inside Pyodide, through Node")
    there.add_argument("--into", default="probes/pyodide", help="directory to write the run into")
    there.set_defaults(handler=_browser)

    book = subs.add_parser("notebook", help="write the checks out as a runnable notebook")
    book.add_argument("--into", default="probes/pyodide/probe.ipynb", help="file to write")
    book.set_defaults(handler=_notebook)

    shown = subs.add_parser("report", help="render the matrix from two recordings")
    shown.add_argument("results", nargs="?", default="probes/pyodide")
    shown.add_argument("--into", default="", help="file to write, otherwise standard output")
    shown.set_defaults(handler=_report)

    gate = subs.add_parser("check", help="fail when a Tier 0 check stopped working in the browser")
    gate.add_argument("results", nargs="?", default="probes/pyodide")
    gate.set_defaults(handler=_check)

    named = subs.add_parser("list", help="show every check and what it is for")
    named.set_defaults(handler=_list)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
