"""The five ways this project builds CPython, and how to tell which one you are on.

`pyxray.build` answers "what is this interpreter", which is the question every lesson opens
with. This module answers the one behind it: what was it built as, what did that decide, and
what would a different build have shown you instead.

The five configurations are the ones this project publishes images for. They are written out
here rather than imported from `cpybuild`, which is the tool that builds them, because that
tool is a repository check and this package is what a reader installs in Colab. A test
compares the two lists, so a build added to one and not the other fails rather than drifts.

Nothing here needs a compiler, a source tree or a container. Every question is answered by
asking the running interpreter about itself, which is the same way the workflow proves an
image is what its tag says it is.
"""

from __future__ import annotations

import shlex
import sys
import sysconfig
from dataclasses import dataclass

from .build import header

#: The configure flags that produced the interpreter, as `configure` recorded them. This is
#: the one config var worth knowing by name: it is the command line somebody typed, kept.
CONFIG_ARGS = "CONFIG_ARGS"

#: The settings the lessons actually depend on, and what each one decides. Not the whole of
#: `sysconfig.get_config_vars`, which is about six hundred entries and mostly paths.
SETTINGS: tuple[tuple[str, str], ...] = (
    ("Py_DEBUG", "assertions on, and sys.gettotalrefcount exists"),
    ("Py_GIL_DISABLED", "the free threaded build, with a different object header"),
    ("_Py_TAIL_CALL_INTERP", "the eval loop is a chain of tail calls rather than a switch"),
    ("WITH_PYMALLOC", "objects come from CPython's own allocator rather than from malloc"),
    ("Py_STATS", "the interpreter counts what it does, at a cost"),
    ("Py_TRACE_REFS", "every object is on a linked list of every object"),
    ("SIZEOF_VOID_P", "how many bytes an address takes, which is what a list slot costs"),
    ("CC", "the compiler"),
    ("OPT", "the optimization flags it was given"),
)


@dataclass(frozen=True)
class Configuration:
    """One way of building CPython, and what it changes that a lesson can see."""

    #: The image tag, and the name the lessons use for this build.
    key: str

    #: What gets passed to `./configure`. Empty for the release build, which is the point.
    flags: tuple[str, ...]

    #: One line on what this build is for.
    summary: str

    #: A Python expression that is true on this build and false on a plain one. The same
    #: expression the publishing workflow runs inside the image before it tags it, because a
    #: configure flag that was quietly ignored still compiles and still publishes.
    proof: str

    #: What a reader would measure differently here, in the words the lessons use.
    changes: str


CONFIGURATIONS: tuple[Configuration, ...] = (
    Configuration(
        key="release",
        flags=(),
        summary="what you get by typing ./configure && make, and what almost everybody runs",
        proof=(
            'not sysconfig.get_config_var("Py_DEBUG") '
            'and not sysconfig.get_config_var("Py_GIL_DISABLED") '
            "and not sys._jit.is_available()"
        ),
        changes="nothing, because this is the one the others are compared against",
    ),
    Configuration(
        key="debug",
        flags=("--with-pydebug", "--with-assertions"),
        summary="the interpreter checking its own invariants instead of trusting them",
        proof='hasattr(sys, "gettotalrefcount")',
        changes=(
            "objects are bigger, sys.gettotalrefcount appears, freed memory is filled with a "
            "recognisable byte pattern, and everything runs two to three times slower"
        ),
    ),
    Configuration(
        key="freethreaded",
        flags=("--disable-gil",),
        summary="built without the GIL, which is a different interpreter rather than a flag",
        proof='bool(sysconfig.get_config_var("Py_GIL_DISABLED"))',
        changes=(
            "the object header has extra fields, reference counting splits into a local and a "
            "shared count, and the cycle collector is a different algorithm"
        ),
    ),
    Configuration(
        key="jit",
        flags=("--enable-experimental-jit",),
        summary="the copy and patch JIT compiled in, so tier 2 traces really execute",
        proof="sys._jit.is_available()",
        changes="hot loops can leave the bytecode interpreter entirely",
    ),
    Configuration(
        key="tailcall",
        flags=("--with-tail-call-interp",),
        summary="the same bytecode through a chain of tail calls instead of one huge switch",
        proof='"--with-tail-call-interp" in (sysconfig.get_config_var("CONFIG_ARGS") or "")',
        changes="nothing observable from Python, which is the interesting part",
    ),
)

BY_KEY = {one.key: one for one in CONFIGURATIONS}


def _ask(expression: str) -> bool:
    """Run one proof expression, treating any failure as a no.

    These run on stock interpreters, on Pyodide and on Python 3.14, and one of them reaches
    for `sys._jit`, which does not exist before 3.13. A proof that raises is telling us the
    build is not that one, which is the answer we wanted, so it must not take the cell down.
    """
    try:
        return bool(eval(expression, {"sys": sys, "sysconfig": sysconfig}))
    except Exception:
        return False


def matches() -> dict[str, bool]:
    """Every configuration's proof, run against the interpreter executing this."""
    return {one.key: _ask(one.proof) for one in CONFIGURATIONS}


def identify() -> list[str]:
    """Which of the five this interpreter looks like, which is not always exactly one.

    A build can be more than one of these at once, since `--with-pydebug` and `--disable-gil`
    are happily combined, and it can be none of them, which is what a reader on Pyodide or on
    a distribution's packaged Python will see. Both answers are useful and neither is wrong,
    so this returns a list rather than picking a winner.
    """
    return [key for key, yes in matches().items() if yes]


def settings() -> list[tuple[str, str, str]]:
    """The build settings the lessons depend on, read off the running interpreter.

    Missing and zero are reported as the same thing on purpose. `sysconfig` gives back None
    for a setting the build never defined and 0 for one it defined as off, and no lesson
    anywhere cares which of those happened.
    """
    macros = header()
    found = []
    for name, decides in SETTINGS:
        value = sysconfig.get_config_var(name)
        if value is None:
            value = macros.get(name)
        found.append((name, "not set" if value in (None, 0, "") else str(value), decides))
    return found


def configured() -> list[str]:
    """The configure arguments that produced this interpreter, one per entry.

    Most readers get a real answer here and it surprises them, because it is a command
    somebody typed months ago on a build machine and the binary has been carrying it around
    ever since. The exceptions are Windows, which does not use `configure` at all, and any
    build whose packager stripped the variable out.

    Split rather than returned whole, because a stock interpreter's configure line is often
    twenty arguments on one line and nobody reads that.
    """
    args = sysconfig.get_config_var(CONFIG_ARGS)
    if args:
        try:
            return shlex.split(args)
        except ValueError:
            return [args]
    if sys.platform == "win32":
        return ["(no configure on Windows, which is built with MSVC project files instead)"]
    return ["(this build did not keep its configure line)"]


def options() -> tuple[list[str], int]:
    """The `--` arguments from the configure line, and how many other entries there were.

    The rest are environment assignments like `CFLAGS=...`, which are real and are also two
    hundred characters of compiler flags each. The count is kept rather than dropped, so the
    reader can see that something was left out instead of wondering.
    """
    args = configured()
    chosen = [one for one in args if one.startswith("--")]
    return chosen, len(args) - len(chosen)


def report() -> None:
    """Print who you are, what you were built with, and which of the five that makes you."""
    found = identify()
    chosen, rest = options()
    print("the configure options this interpreter was built with:")
    for one in chosen:
        print(f"  {one}")
    if rest:
        print(f"  and {rest} environment settings, mostly compiler flags")
    print()
    print("settings the lessons care about:")
    rows = settings()
    width = max(len(value) for _, value, _ in rows)
    for name, value, decides in rows:
        print(f"  {name:22} {value:{width}}  {decides}")
    print()
    print("which of the five builds this is:")
    for one in CONFIGURATIONS:
        mark = "yes" if one.key in found else " no"
        print(f"  {mark}  {one.key:14} {one.summary}")
    if not found:
        print()
        print("None of them, which is normal. The five are what this project publishes,")
        print("not the only ways to build CPython, and a packaged Python is its own thing.")
