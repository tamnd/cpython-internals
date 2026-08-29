"""Running an experiment inside the image it needs, and writing down what came out.

Needs Docker, so nothing in `checks.py` imports this. The split matters: the cheap checks
run on every pull request and take milliseconds, and this runs in a job of its own that pulls
a two hundred megabyte image, and folding the two together would put that pull in front of
every contributor who changed a paragraph.

The image is named by digest, taken from the same lockfile the devcontainer reads. A tag
would mean the recording says "the debug build" and the reader gets whichever debug build
exists on the day they look, which is the failure this whole arrangement is here to avoid.
"""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

from cpybuild.cli import PROOF
from cpybuild.configs import BY_KEY
from cpybuild.images import LOCKFILE, Lock

from .experiments import Experiment
from .recording import Recording

#: Asked of the interpreter before anything else, so the recording says what it ran on
#: rather than what it was supposed to run on.
VERSION = "import sys; print(sys.version.replace(chr(10), ' '))"

#: How long one experiment gets. Generous, because the first run also pulls the image, and
#: the thing this is protecting against is a program that waits on standard input forever.
SECONDS = 900


class Failed(RuntimeError):
    """The container came back non zero, or did not come back."""


def image_for(build: str, lockfile: Path = LOCKFILE) -> str:
    """The digest reference for one build, from the committed lockfile."""
    return Lock.load(lockfile).reference_index(build)


def _inside(image: str, program: str, docker: str = "docker") -> str:
    """Run a program in the image and hand back what it printed.

    Standard input rather than a file or a `-c`, because the programs here are twenty lines
    with docstrings and quotes in them and every other way of getting them in involves
    escaping. `--network=none` because none of them reach for anything and a run that
    quietly downloaded something would be a run nobody could reproduce later.
    """
    done = subprocess.run(
        [docker, "run", "--rm", "-i", "--network=none", image, "python3", "-"],
        input=program,
        capture_output=True,
        text=True,
        timeout=SECONDS,
        check=False,
    )
    if done.returncode != 0:
        raise Failed(f"{image} exited {done.returncode}\n{done.stderr.strip()}")
    return done.stdout


def prove(build: str, image: str, docker: str = "docker") -> str:
    """Check the image really is the build it claims to be, before trusting a number from it.

    `cpybuild proof` prints a program that exits non zero unless the interpreter has the
    thing that build is for. Running it here costs a second and closes the gap where a
    lockfile entry points at an image that built fine and quietly ignored a configure flag.
    A recording taken from that image would look completely normal and be wrong.
    """
    one = BY_KEY[build]
    return _inside(image, PROOF.format(expression=one.proof, key=one.key), docker).strip()


def record(
    experiment: Experiment,
    lockfile: Path = LOCKFILE,
    docker: str = "docker",
) -> Recording:
    """Run one experiment for real and hand back the recording it produced."""
    image = image_for(experiment.build, lockfile)
    prove(experiment.build, image, docker)
    interpreter = _inside(image, VERSION, docker).strip()
    printed = _inside(image, experiment.program, docker)
    return Recording(
        slug=experiment.slug,
        title=experiment.title,
        asks=experiment.asks,
        needs=experiment.needs,
        lesson=experiment.lesson,
        build=experiment.build,
        image=image,
        interpreter=interpreter,
        recorded=date.today().isoformat(),
        program=experiment.program,
        output=printed.splitlines(),
    )
