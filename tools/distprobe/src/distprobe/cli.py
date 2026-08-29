"""The command line.

Four subcommands, in the order they are meant to be run.

    distprobe survey  --into probes/distributions
    distprobe report  probes/distributions --into probes/distributions/report.md
    distprobe check   probes/distributions
    distprobe question

`survey` is the slow one. It pulls container images and runs a package manager in each, so
it takes half an hour on a cold cache and it needs Docker. `survey --only fedora_test` asks
one channel and merges the answer into the recording, which is for when a single slow row
needs redoing. `check` is the one in `just check`: it reads the committed recording, so it
is instant and needs nothing.

`question` prints the source of the question. That is for the two channels this machine
cannot reach, so somebody on a Windows box can paste it into their own Python and send back
the line it prints.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import borrowed, report, run
from .channels import BY_KEY, CHANNELS, RUNNABLE
from .question import SOURCE, Survey

#: The file names inside the results directory.
ANSWERS = "answers.json"
REPORT = "report.md"


def _load(room: Path) -> Survey:
    path = room / ANSWERS
    if not path.exists():
        raise SystemExit(f"no recording at {path}, run distprobe survey first")
    return Survey.from_json(path.read_text(encoding="utf-8"))


def _survey(args: argparse.Namespace) -> int:
    room = Path(args.into)
    room.mkdir(parents=True, exist_ok=True)
    path = room / ANSWERS
    if args.only:
        # One channel, merged into what is already there. The reason this exists is that
        # installing two packages on Fedora took over fifteen minutes on a cold cache and got
        # recorded as a timeout, and redoing the other eleven to fix one row is half an hour
        # of pulling images that already answered.
        wanted = [BY_KEY[one] for one in args.only]
        made = Survey.from_json(path.read_text(encoding="utf-8")) if path.exists() else None
        fresh = run.survey(wanted)
        if made is None:
            made = fresh
        else:
            made.answers.update(fresh.answers)
    else:
        made = run.survey()
        # The browser row comes from the other probe's recording rather than from a second
        # Node driver, so the two cannot disagree about what Pyodide said.
        made.answers["pyodide"] = borrowed.from_wasmprobe()
    path.write_text(made.as_json(), encoding="utf-8")
    print(f"{path}: {report.summary(made)}")
    return 0


def _report(args: argparse.Namespace) -> int:
    made = _load(Path(args.results))
    body = report.markdown(made)
    if args.into:
        path = Path(args.into)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        print(f"{path}: {report.summary(made)}")
    else:
        print(body, end="")
    return 0


def _check(args: argparse.Namespace) -> int:
    """Read the committed recording and say what it means, without measuring anything.

    This does not fail when a channel is missing the module. That is a fact about the world
    and a build going red every time somebody runs it would not change Fedora's packaging.
    It fails when the report has fallen behind the recording, which is a fact about this
    repository and is fixable by running one command.
    """
    room = Path(args.results)
    made = _load(room)
    print(report.summary(made))
    for one in report.problems(made):
        print(f"  {one.name}: {report.cell(made.answers[one.key])}")
    path = room / REPORT
    fresh = report.markdown(made)
    if not path.exists() or path.read_text(encoding="utf-8") != fresh:
        print("", file=sys.stderr)
        print(f"out of date: {REPORT}. Run just build-dist.", file=sys.stderr)
        return 1
    return 0


def _question(args: argparse.Namespace) -> int:
    print(SOURCE.strip())
    return 0


def _list(args: argparse.Namespace) -> int:
    for one in CHANNELS:
        runs = "here" if one in RUNNABLE else "elsewhere"
        print(f"{one.key:20} {runs:10} {one.name}")
    return 0


def build() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="distprobe", description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)

    asked = subs.add_parser("survey", help="ask every channel this machine can reach")
    asked.add_argument("--into", default="probes/distributions", help="directory to write into")
    asked.add_argument(
        "--only",
        nargs="+",
        choices=[one.key for one in RUNNABLE],
        default=[],
        help="ask these channels and merge them into the recording, rather than all of them",
    )
    asked.set_defaults(handler=_survey)

    shown = subs.add_parser("report", help="render the table from the recording")
    shown.add_argument("results", nargs="?", default="probes/distributions")
    shown.add_argument("--into", default="", help="file to write, otherwise standard output")
    shown.set_defaults(handler=_report)

    gate = subs.add_parser("check", help="read the committed recording and check the report")
    gate.add_argument("results", nargs="?", default="probes/distributions")
    gate.set_defaults(handler=_check)

    asking = subs.add_parser("question", help="print the question, to run somewhere else")
    asking.set_defaults(handler=_question)

    named = subs.add_parser("list", help="show every channel and whether it runs here")
    named.set_defaults(handler=_list)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
