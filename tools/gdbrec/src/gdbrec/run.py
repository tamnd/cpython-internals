"""Running a session inside the debug image and writing down what gdb printed.

Needs Docker, so nothing in `checks.py` imports this. The split is the same one `tier1`
makes and for the same reason: the cheap checks run on every pull request and take
milliseconds, and this pulls a three hundred megabyte image.

Two container flags here are unusual enough to explain. `--cap-add=SYS_PTRACE` is what lets
one process in the container stop and inspect another, which is the entire job, and
containers do not get it by default because it is also how one process reads another's
memory. `--security-opt seccomp=unconfined` is needed because the default seccomp profile
blocks the `ptrace` syscall outright, so without it gdb starts, attaches to nothing and
reports that ptrace is not implemented. Neither flag is needed to run Python and neither is
turned on anywhere else in this project.

The commands are separated by markers rather than by guessing. gdb in batch mode prints what
each command produced and nothing about the command itself, so the script has an `echo` of a
unique line before each one and the output is cut on those lines afterwards. Anything gdb
said before the first marker is startup noise and is dropped.
"""

from __future__ import annotations

import platform
import re
import subprocess
from datetime import date
from pathlib import Path

from cpybuild.cli import PROOF
from cpybuild.configs import BY_KEY
from cpybuild.images import LOCKFILE, Lock

from .recording import ARCHES, Printed, Recording
from .sessions import PREAMBLE, PROGRAM, Session

#: Asked of the interpreter before anything else, so the transcript says what it ran on
#: rather than what it was supposed to run on.
VERSION = "import sys; print(sys.version.replace(chr(10), ' '))"

#: How long one session gets. Generous, because the first run also pulls the image, and the
#: thing this is protecting against is a gdb waiting on a prompt that will never be answered.
SECONDS = 900

#: The line printed before each command, and the pattern that finds it again. The word is
#: not one that appears in a backtrace, which is the only requirement.
MARKER = "<<<gdbrec {number}>>>"
FOUND = re.compile(r"^<<<gdbrec (\d+)>>>$")


class Failed(RuntimeError):
    """The container came back non zero, or did not come back."""


def here() -> str:
    """Which of the published architectures this machine is, in Docker's spelling."""
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return "arm64"
    if machine in ("x86_64", "amd64"):
        return "amd64"
    raise Failed(f"{machine} is not one of {', '.join(ARCHES)}, so there is nothing to record")


def image_for(build: str, arch: str, lockfile: Path = LOCKFILE) -> str:
    """The digest reference for one build on one architecture, from the committed lockfile.

    By architecture rather than the joined index, because a transcript belongs to the
    architecture it was taken on and naming the index would let the file claim a digest that
    covers a build it never ran.
    """
    return Lock.load(lockfile).reference(build, arch)


def _inside(
    image: str, script: str, arch: str, docker: str = "docker", ptrace: bool = False
) -> str:
    """Run a shell script in the image and hand back everything it said, errors included.

    Standard input rather than a file, because Docker on macOS does not reliably share a
    path under `/tmp` and a mount that silently arrives empty looks exactly like a script
    that did nothing. Standard error is folded in on purpose: gdb writes some of a session to
    each stream and splitting them would shuffle the transcript out of the order it happened.
    """
    command = [docker, "run", "--rm", "-i", "--network=none", f"--platform=linux/{arch}"]
    if ptrace:
        command += ["--cap-add=SYS_PTRACE", "--security-opt", "seccomp=unconfined"]
    done = subprocess.run(
        [*command, image, "sh", "-s"],
        input=script,
        capture_output=True,
        text=True,
        timeout=SECONDS,
        check=False,
    )
    if done.returncode != 0:
        raise Failed(f"{image} exited {done.returncode}\n{done.stderr.strip()}")
    return done.stdout


def prove(build: str, image: str, arch: str, docker: str = "docker") -> str:
    """Check the image really is the build it claims to be, before trusting a transcript.

    `cpybuild proof` prints a program that exits non zero unless the interpreter has the
    thing that build is for. A configure flag that was quietly ignored still compiles and
    still publishes, and a session recorded in that image would look completely normal.
    """
    one = BY_KEY[build]
    program = PROOF.format(expression=one.proof, key=one.key)
    return _inside(image, f"python3 - <<'PROOF'\n{program}\nPROOF\n", arch, docker).strip()


def script_for(session: Session) -> str:
    """The shell script that writes the program, writes the gdb script, and runs gdb."""
    lines = list(PREAMBLE)
    for number, step in enumerate(session.script, start=1):
        lines.append(f"echo \\n{MARKER.format(number=number)}\\n")
        lines.append(step.command)
    lines.append(f"echo \\n{MARKER.format(number=len(session.script) + 1)}\\n")
    commands = "\n".join(lines)
    return (
        f"cat > {PROGRAM} <<'PROGRAM'\n{session.program.rstrip()}\nPROGRAM\n"
        f"cat > /tmp/session.gdb <<'SESSION'\n{commands}\nSESSION\n"
        f"gdb -q -batch -x /tmp/session.gdb /usr/local/bin/python3 2>&1\n"
    )


def split(printed: str, wanted: int) -> list[list[str]]:
    """Cut a batch run into one block of output per command, using the markers.

    The count is checked rather than assumed. There is one marker before each command and one
    after the last, so a session where gdb died halfway comes back with too few, and that is
    the failure worth catching: the alternative is a transcript that is quietly half a session
    with the missing commands showing as having printed nothing.

    A command that really did print nothing gets an empty block rather than being dropped,
    because a command whose whole point is that it says nothing is still a command somebody
    typed and still needs its heading.
    """
    blocks: list[list[str]] = []
    current: list[str] | None = None
    markers = 0
    for line in printed.splitlines():
        if FOUND.match(line.strip()):
            markers += 1
            if current is not None:
                blocks.append(current)
            current = []
            continue
        if current is not None:
            current.append(line)
    if markers != wanted + 1:
        raise Failed(
            f"expected {wanted} block(s) of output and the markers gave {max(markers - 1, 0)}, "
            f"so gdb stopped before the end of the script"
        )
    return [trimmed(one) for one in blocks]


def trimmed(block: list[str]) -> list[str]:
    """One command's output with the blank lines the markers left at either end removed."""
    while block and not block[0].strip():
        block = block[1:]
    while block and not block[-1].strip():
        block = block[:-1]
    return block


def record(
    session: Session,
    arch: str | None = None,
    lockfile: Path = LOCKFILE,
    docker: str = "docker",
) -> Recording:
    """Run one session for real and hand back the transcript it produced."""
    arch = arch or here()
    image = image_for(session.build, arch, lockfile)
    prove(session.build, image, arch, docker)
    interpreter = _inside(image, f"python3 - <<'ASK'\n{VERSION}\nASK\n", arch, docker).strip()
    debugger = _inside(image, "gdb --version | head -1\n", arch, docker).strip()
    printed = _inside(image, script_for(session), arch, docker, ptrace=True)
    blocks = split(printed, len(session.script))
    return Recording(
        slug=session.slug,
        title=session.title,
        asks=session.asks,
        needs=session.needs,
        lesson=session.lesson,
        build=session.build,
        arch=arch,
        image=image,
        interpreter=interpreter,
        debugger=debugger,
        recorded=date.today().isoformat(),
        program=session.program,
        steps=[
            Printed(command=step.command, note=step.note, output=block)
            for step, block in zip(session.script, blocks, strict=True)
        ],
    )
