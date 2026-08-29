"""Running the checks on the interpreter this process is.

The native run is the control. Without it a browser answer has nothing to be surprising
against, and half the interesting findings are of the form "this works everywhere except
there" rather than "this does not work".

Each check gets its own namespace and is expected to leave its answer in `result`. That is
a small amount of ceremony in exchange for the checks being ordinary Python that somebody
can paste into a prompt to see what it does.
"""

from __future__ import annotations

import platform
import traceback

from .checks import CHECKS, Check
from .result import OK, RAISED, Outcome, Run


def one(check: Check) -> Outcome:
    """Run a single check, catching anything it throws."""
    namespace: dict = {}
    try:
        exec(check.source, namespace)
    except BaseException:
        # BaseException rather than Exception because a check that trips a recursion limit
        # or gets interrupted is a result worth recording, not a crash of the probe.
        line = traceback.format_exc().strip().splitlines()[-1]
        return Outcome(check.key, RAISED, error=line)
    return Outcome(check.key, OK, value=namespace.get("result"))


def run(checks: list[Check] | None = None) -> Run:
    """Every check, in order, on this interpreter."""
    outcomes = {}
    for check in checks if checks is not None else CHECKS:
        outcomes[check.key] = one(check)
    # No boot time to report. This interpreter was already running.
    return Run(runtime="native", python=platform.python_version(), outcomes=outcomes)
