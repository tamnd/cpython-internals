"""The five CPython builds this project teaches from, and what each one is for.

A lot of what the lessons observe is a property of the binary rather than of the language.
The reference count of a small integer, whether an object is immortal, what `dis` prints,
whether the JIT is running, how big a dict is: change the build and some of those change with
it. So the material needs more than one interpreter to point at, and it needs them to be the
same interpreter built five ways rather than five interpreters that happen to be lying about.

The list lives here rather than in the workflow because two copies of a matrix drift, and the
one in YAML is the copy nobody runs locally. `cpybuild matrix` prints this list as JSON and
the workflow reads it, so adding a build is a change to this file and nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: The architectures every configuration is built for. Two, because a surprising number of
#: interpreter details are word size or calling convention dependent, and because half the
#: readers are on an Apple laptop and half are on an x86 box, and a recording made on one of
#: those is not automatically true on the other.
ARCHITECTURES = ("amd64", "arm64")

#: The LLVM the JIT build needs, which is not the LLVM Debian has. CPython names an exact
#: major version and refuses anything else, because the JIT cuts its templates out of object
#: files that LLVM produced and a mismatch there is not a warning, it is wrong code.
#:
#: `Tools/jit/_llvm.py:13@v3.15.0rc1#_LLVM_VERSION`. Debian trixie ships 17, 18 and 19, so a
#: build that installs the `llvm` package gets 19 and fails. A test reads this number back out
#: of the pinned checkout, so when the pin moves and CPython wants a different LLVM, the test
#: says so rather than a twenty minute job failing in CI.
LLVM_VERSION = "21"

#: What GitHub calls the runners for those. Native runners rather than emulation: qemu builds
#: CPython perhaps ten times slower, which turns a fifteen minute job into an afternoon.
RUNNERS = {"amd64": "ubuntu-24.04", "arm64": "ubuntu-24.04-arm"}


@dataclass(frozen=True)
class Configuration:
    """One way of building CPython, and the reason the project needs it."""

    key: str

    #: One line, for the table in the README and for the image label.
    summary: str

    #: What gets passed to `./configure`, in the order it is passed.
    flags: tuple[str, ...] = ()

    #: Environment for the configure and make steps. `CC` for the builds that need a specific
    #: compiler, and nothing else so far.
    environment: dict[str, str] = field(default_factory=dict)

    #: Extra Debian packages this build needs on top of the common set.
    packages: tuple[str, ...] = ()

    #: Whether the image carries the source tree and a debugger. Stepping through C with no
    #: source is not an experiment, it is a wall of addresses.
    debugger: bool = False

    #: The LLVM major version this build needs from apt.llvm.org, if it needs one at all.
    #: Only the JIT does, and only because Debian is two releases behind what CPython asks for.
    llvm: str = ""

    #: A Python expression that is true in this build and false in a plain one, run inside the
    #: published image. Without it the only thing the workflow proves is that something
    #: compiled, and a configure flag that was quietly ignored still compiles. That is the
    #: failure worth catching, because the image would then be published, tagged, written into
    #: the lockfile and pulled by a lesson that goes on to draw a conclusion from it.
    proof: str = ""

    #: Why this configuration is on the list, and what a reader would get wrong without it.
    note: str = ""

    @property
    def image(self) -> str:
        """The tag under the package name, which is the key and nothing clever."""
        return self.key


CONFIGURATIONS: list[Configuration] = [
    Configuration(
        key="debug",
        summary="assertions on, refcount totals available, the interpreter checking itself",
        flags=("--with-pydebug", "--with-assertions"),
        debugger=True,
        proof='hasattr(sys, "gettotalrefcount")',
        note=(
            "The one the Tier 1 experiments run on. `sys.gettotalrefcount` exists here and "
            "nowhere else, the allocator fills freed memory with a recognisable byte "
            "pattern, and the interpreter checks its own invariants instead of trusting "
            "them. It is also two to three times slower and has different object sizes, "
            "which is why no timing in this material is ever taken on it."
        ),
    ),
    Configuration(
        key="release",
        summary="CPython's own defaults, which is what almost every reader is running",
        flags=(),
        # The one build whose proof is that nothing is switched on. Asserting the absence of
        # the other four is what makes this the control rather than a build nobody looked at.
        proof=(
            'not sysconfig.get_config_var("Py_DEBUG") '
            'and not sysconfig.get_config_var("Py_GIL_DISABLED") '
            "and not sys._jit.is_available()"
        ),
        note=(
            "The control. Whenever a debug build would mislead, the number comes from here. "
            "No flags at all, because the point is to be what you get by typing "
            "`./configure && make`. Worth knowing that CPython's default is `-O3` and not "
            "`-O2`: the issue that asked for this build said `-O2`, and rather than pass a "
            "flag to make the sentence true, the build is left alone and the sentence is "
            "corrected here."
        ),
    ),
    Configuration(
        key="freethreaded",
        summary="built without the GIL, so the object header and the collector both change",
        flags=("--disable-gil",),
        # What CPython's own test suite uses to answer the same question, at
        # `Lib/test/support/__init__.py:1014@v3.15.0rc1`.
        proof='bool(sysconfig.get_config_var("Py_GIL_DISABLED"))',
        note=(
            "Not a flag on a normal interpreter, a different interpreter. The object header "
            "has extra fields, reference counting is split into a local and a shared count, "
            "the allocator is per thread and the collector is a different algorithm. Every "
            "refcount and every `getsizeof` in the object lessons comes out differently, "
            "which is exactly why the lessons measure rather than assert."
        ),
    ),
    Configuration(
        key="jit",
        summary="the experimental copy and patch JIT compiled in",
        flags=("--enable-experimental-jit",),
        # A host Python, to run `Tools/jit/build.py` during `make`. The JIT generates its
        # templates with a Python script before it can compile them, so this build needs an
        # interpreter to build an interpreter. It is the only one that does, which is why it
        # is here rather than in the common list.
        packages=("python3",),
        llvm=LLVM_VERSION,
        # `Python/sysmodule.c:4291@v3.15.0rc1#_jit_is_available_impl`. It returns true only
        # when `_Py_TIER2` was defined at compile time, and `sys._jit` itself is there in every
        # build, so asking whether the module exists answers nothing. This is the proof that
        # mattered most: the first two attempts at this build failed, and a third that fell
        # back to no JIT and published anyway would have been worse than either of them.
        proof="sys._jit.is_available()",
        note=(
            "Needs LLVM at build time because the JIT is copy and patch: the build compiles "
            "each micro operation into an object file and the templates are cut out of it. "
            "The interpreter lessons need this to show tier 2 traces actually being "
            f"executed rather than described. The LLVM has to be exactly {LLVM_VERSION}, "
            "which Debian does not have, so this is the one build that adds a package "
            "repository. That was found the way these things usually are: the first run of "
            "the workflow built the other four and failed this one on both architectures."
        ),
    ),
    Configuration(
        key="tailcall",
        summary="the tail calling interpreter, a different shape of eval loop",
        flags=("--with-tail-call-interp",),
        environment={"CC": "clang"},
        packages=("clang",),
        # The weak one, and worth being straight about it. The other four ask the interpreter
        # about itself. This reads back the flag configure was given, because a tail calling
        # build is not visible from Python at all: `_Py_TAIL_CALL_INTERP` is a C macro and
        # nothing exposes it. It is still worth having, because configure refuses the flag
        # outright when the compiler has no `musttail`, so the flag surviving into the
        # installed interpreter means it was accepted rather than warned about and dropped.
        proof=('"--with-tail-call-interp" in sysconfig.get_config_var("CONFIG_ARGS")'),
        note=(
            "Needs Clang 19 or newer, because it leans on `musttail`, which GCC does not "
            "have. The same bytecode runs through a chain of tail calls instead of a switch "
            "in one enormous function, so it is the build that makes the point that the "
            "eval loop's shape is an implementation choice and not part of the language."
        ),
    ),
]

BY_KEY = {one.key: one for one in CONFIGURATIONS}

#: The Debian packages every build needs. Kept in one list rather than in the Dockerfile so
#: the tests can say something about it and so a reader can see the whole answer in one place.
COMMON_PACKAGES = (
    "build-essential",
    "ca-certificates",
    "git",
    "libbz2-dev",
    "libffi-dev",
    "libgdbm-compat-dev",
    "libgdbm-dev",
    "liblzma-dev",
    "libncursesw5-dev",
    "libreadline-dev",
    "libsqlite3-dev",
    "libssl-dev",
    "libzstd-dev",
    "pkg-config",
    "tk-dev",
    "uuid-dev",
    "zlib1g-dev",
)


def packages(configuration: Configuration) -> tuple[str, ...]:
    """Everything to install for this build, sorted, with no duplicates.

    The LLVM packages are spelled out from the version rather than listed, so there is one
    place to change when CPython wants a different one.
    """
    extra = set(configuration.packages)
    if configuration.llvm:
        extra |= {f"clang-{configuration.llvm}", f"llvm-{configuration.llvm}"}
    return tuple(sorted(set(COMMON_PACKAGES) | extra))


def matrix() -> list[dict[str, str]]:
    """Every build the workflow runs, one entry per configuration per architecture."""
    return [
        {
            "config": one.key,
            "arch": arch,
            "runner": RUNNERS[arch],
            "flags": " ".join(one.flags),
        }
        for one in CONFIGURATIONS
        for arch in ARCHITECTURES
    ]
