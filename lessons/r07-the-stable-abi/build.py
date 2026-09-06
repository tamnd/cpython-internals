#!/usr/bin/env python
"""R07. The stable ABI.

R06 was about which C functions you are allowed to call. This one is about what happens
afterwards, when the thing you compiled turns up on somebody else's machine as a file.

There are two gates. The first is the file name, which the finder reads before it opens
anything. The second is a twelve byte struct the extension carries, which is new in 3.15 and
which the interpreter checks after the extension's own code has already run.

Both gates are runnable from Python, which is the nice surprise here. The first one you can
drive by putting empty files in a temporary directory and asking the finder what it sees. The
second one you can drive by building the struct in ctypes and calling the real check function.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording

lesson = Lesson("r07-the-stable-abi", "r07")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("r07-the-stable-abi").figure

LOADS = "r07-what-a-build-will-load"
NOLOCK = "r07-what-a-build-will-load-without-the-lock"


lesson.md(f"""
# R07. The stable ABI

{badge}

R06 sorted out which C functions you are allowed to call. This one picks up where that leaves off, when the thing you compiled turns up on somebody else's machine as a file with a long name.

There are two gates between that file and a working module. The first is the name itself, which the interpreter reads before it opens anything. The second is a small struct the extension carries, which is new in 3.15 and which gets checked after the extension's own code has already run.

Both of them can be driven from Python, which is the nice part.

{figure("two-gates", "a four stage pipeline, a file turning up, the name being read, the file being opened and run, and the struct being checked")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Include/patchlevel.h:53-62@v3.15.0rc1`.

Read it as three parts: the file, the lines, and the release those line numbers belong to. Sometimes there is a fourth part after a `#`, which is the name of the thing those lines are inside.

Every reference is a link, and every one is checked against the pinned source on each change, so a stale reference fails the build instead of sending you somewhere wrong. You never have to read any of it. The references are there so you can go deeper when you want to, and so you can check that this lesson is not making things up.

## Setup

Colab does not come with the small package these lessons use, so the next cell installs it. If you are running this from a checkout of the repository it is already installed and the cell does nothing.
""")


lesson.code("""
import sys

if sys.version_info < (3, 14):
    print("This lesson needs CPython 3.14 or newer.")
    print(f"This runtime is {sys.version.split()[0]}, and the cells below will not run on it.")
else:
    try:
        import pyxray
    except ImportError:
        %pip install -q "pyxray @ git+https://github.com/tamnd/cpython-internals@main#subdirectory=pyxray"
        import pyxray
""")


lesson.md("""
## Which Python is this

Most of this lesson runs anywhere, because file names and `ctypes` work everywhere. Two things do not. The second gate arrived in 3.15, so on 3.14 those cells say what it would have answered. And two cells read the header files, which a normal install has and a browser tab does not.

## Which interpreter is this
""")


lesson.code(
    """
import pyxray

pyxray.show()
""",
    differs=BANNER,
    quiet=True,
)


lesson.md(f"""
## The name is the first gate

An {term("extension module", "a module that arrives as a compiled shared library rather than as Python")} is a shared library with a long name. The long name is not decoration. It is the only thing the interpreter looks at before deciding whether the file is worth opening.

Start with what this build accepts and what it stamps on its own output.

{lesson.claim("An interpreter will only look at extension files whose names carry a tag it recognises, and it has a short fixed list of those.")}
""")


lesson.code(
    """
import importlib.machinery
import sysconfig

TAGS = importlib.machinery.EXTENSION_SUFFIXES
HERE = sysconfig.get_config_var("EXT_SUFFIX")

print("  file names this build is willing to load an extension from:")
for tag in TAGS:
    print("   ", tag)
print()
print("  and the one it stamps on what it builds:", HERE)
for key in ("SOABI", "ABIFLAGS", "Py_GIL_DISABLED"):
    print(f"    {key:16} {sysconfig.get_config_var(key)!r}")
print(f"    {'sys.abiflags':16} {sys.abiflags!r}")
""",
    differs=(
        "On 3.14 there are three tags rather than six. Both of the abi3t ones are missing "
        "because that tag is new in 3.15, and so is the platform specific abi3 one."
    ),
)


lesson.md(f"""
That list is not built at run time. It is a C array, and you can read the whole thing in {cite("Python/dynload_shlib.c:39-60@v3.15.0rc1#_PyImport_DynLoadFiletab")}. The `#ifndef Py_GIL_DISABLED` in the middle of it is why a free threaded build has fewer entries, and `_imp.extension_suffixes` at {cite("Python/import.c:5175-5204@v3.15.0rc1#_imp_extension_suffixes_impl")} does nothing but copy that array into a list.

The tag is called {term("SOABI", "the tag a build stamps into the file names of the extensions it compiles")}, and it is three facts glued together.

{figure("what-the-name-says", "the file name mymodule.cpython-315t-darwin.so broken into six labelled pieces")}

{lesson.claim("The version in the file name is the Python version, and the 3 in abi3 is not.")}
""")


lesson.code(
    """
import re

VERSIONED = re.compile(r"(cpython-)(\\d+)(t?)")

found = VERSIONED.search(HERE)
if found:
    print("  the tag this build writes:", HERE)
    print("    which Python:  ", found.group(1).rstrip("-"))
    print("    which version: ", found.group(2))
    print("    threading:     ", "no lock" if found.group(3) else "with the lock")
    print("    the rest:      ", HERE[found.end() :])
else:
    print("  this build puts no version in the name at all:", HERE)
print()
print("  the 3 in abi3 is not a Python version, it is PYTHON_ABI_VERSION")
print("  and the other number nobody has touched since 2006:", sys.api_version)
""",
    differs=(
        "On 3.14 the version in the tag reads 314 rather than 315. Everything else here is the "
        "same, including the 1013 that nobody has touched since 2006."
    ),
)


lesson.md(f"""
Those two numbers are worth a look, because they are a small piece of history sitting in a header nobody edits. {cite("Include/patchlevel.h:53-62@v3.15.0rc1#PYTHON_ABI_VERSION")} defines `PYTHON_API_VERSION 1013` and `PYTHON_ABI_VERSION 3` with a comment saying they have not been updated since 2006 and 2010, and that versioning is tied to the CPython version now.

So the `3` in `abi3` is not "Python 3". It is a counter that stopped moving fifteen years ago, and the suffix table builds the string out of it.

## What the finder will even look at

Here is the first gate, run by hand. Put one empty file in a directory, ask for a module by that name, and see whether anything comes back. The file is empty, so nothing gets loaded; the finder only ever stats it.

{lesson.claim("A file with the wrong version in its name is invisible to the finder, not an error.")}
""")


lesson.code(
    """
import pathlib
import tempfile

flipped = VERSIONED.sub(lambda m: m.group(1) + m.group(2) + ("" if m.group(3) else "t"), HERE)
future = VERSIONED.sub(lambda m: m.group(1) + "999" + m.group(3), HERE)
CANDIDATES = ("demo" + HERE, "demo" + flipped, "demo" + future, "demo.abi3.so", "demo.abi3t.so")


def considered(name):
    \"\"\"Put one empty file in a directory of its own and ask the finder whether it sees it.\"\"\"
    room = pathlib.Path(tempfile.mkdtemp())
    (room / name).write_bytes(b"")
    return importlib.machinery.PathFinder.find_spec("demo", [str(room)]) is not None


for name in CANDIDATES:
    print(f"  {name:42} {'considered' if considered(name) else 'invisible, wrong name'}")
""",
    differs=(
        "On 3.14 the abi3t file is invisible too, because that tag did not exist yet. The other "
        "four answers are the same, with 314 in place of 315."
    ),
)


lesson.md(f"""
{figure("which-names-load", "a table of six file names against three builds, saying which are considered and which are invisible")}

Read the two `abi3` rows together and the design shows up. A free threaded build refuses `abi3` and takes `abi3t`. An ordinary 3.15 build takes both. A 3.14 build takes `abi3` and has never heard of `abi3t`. {cite("Doc/c-api/stable.rst:100-105@v3.15.0rc1")} states the rule and draws the conclusion for you: ship `abi3t` if you want one file that reaches both 3.15 builds.

When several of them are sitting in the same directory, the order in that C array decides.

{lesson.claim("When more than one acceptable file is present, the first suffix in the list wins, not the best match.")}
""")


lesson.code(
    """
room = pathlib.Path(tempfile.mkdtemp())
for name in CANDIDATES:
    (room / name).write_bytes(b"")
(room / "demo.py").write_text("")
picked = importlib.machinery.PathFinder.find_spec("demo", [str(room)])
print("  all of them in one directory, and the finder picks:")
print("   ", pathlib.Path(picked.origin).name)
print("    loaded by", type(picked.loader).__name__)
print()
print("  the order is the suffix list, and the first match wins:")
for position, tag in enumerate(TAGS, 1):
    print(f"    {position}. {tag}")
""",
    differs=(
        "On 3.14 the name the finder picks has 314 in it, and the numbered list below has three "
        "entries rather than six, for the same reason as the first cell."
    ),
)


lesson.md(f"""
The exact build wins over the stable one, and both win over the plain `demo.py`. That last part is worth remembering, because it means a compiled file quietly shadows a Python file of the same name.

## The second gate

Everything so far cost one stat call. The second gate is much more expensive, because by the time it runs the file has been opened, the dynamic linker has resolved its symbols, and the extension's own initialisation code has started.

{term("PyABIInfo", "twelve bytes an extension carries saying which ABI it was built against")} is the struct that gets checked. It is declared at {cite("Include/modsupport.h:86-101@v3.15.0rc1#PyABIInfo")}, and an extension that wants the check writes `PyABIInfo_VAR(abi_info)` and lists it as a slot, which {cite("Include/modsupport.h:135-143@v3.15.0rc1#PyABIInfo_VAR")} turns into a static struct filled in from whatever macros were set when it was compiled.

{figure("the-five-fields", "the five fields of PyABIInfo stacked, with the version fields at the bottom")}

`PyABIInfo_Check` is a plain function in the public headers, so `ctypes` can call it, and the struct is five integers, so `ctypes` can build one. That is the whole trick of this lesson.

{lesson.claim("The struct an extension carries is twelve bytes, and Python can build one and hand it to the real check function.")}
""")


lesson.code(
    """
import ctypes

api = ctypes.pythonapi
ABICHECK = hasattr(api, "PyABIInfo_Check")

STABLE = 0x0001
GIL = 0x0002
FREETHREADED = 0x0004
INTERNAL = 0x0008


class PyABIInfo(ctypes.Structure):
    \"\"\"The five fields an extension built against 3.15 or later carries about itself.\"\"\"

    _fields_ = [
        ("abiinfo_major_version", ctypes.c_uint8),
        ("abiinfo_minor_version", ctypes.c_uint8),
        ("flags", ctypes.c_uint16),
        ("build_version", ctypes.c_uint32),
        ("abi_version", ctypes.c_uint32),
    ]


def pack(major, minor):
    \"\"\"The version format the C API uses, two numbers packed into the top two bytes.\"\"\"
    return (major << 24) | (minor << 16)


if not ABICHECK:
    print("  PyABIInfo_Check arrived in 3.15 and this is", sys.version.split()[0])
    print("  so the next cell has nothing to run")
else:
    print("  the struct is", ctypes.sizeof(PyABIInfo), "bytes, laid out as")
    for field, kind in PyABIInfo._fields_:
        print(f"    {field:24} {kind.__name__}")
""",
    differs=(
        "On 3.14 there is no PyABIInfo_Check to find, so this cell says so and the next one "
        "skips itself. The struct did not exist before 3.15."
    ),
)


lesson.md(f"""
## Who gets turned away

Now the interesting part. Build one struct per kind of extension somebody might ship, hand each one to the real check function, and print what comes back. Nothing is being loaded here; the function is only comparing numbers.

{lesson.claim("The check refuses four of these eight, and no two of them for the same reason.")}
""")


lesson.code(
    """
CASES = (
    ("built for this exact version", GIL, pack(*sys.version_info[:2])),
    ("built for 3.13 and nothing else", GIL, pack(3, 13)),
    ("stable abi since 3.2", STABLE | GIL, pack(3, 2)),
    ("stable abi since 3.14", STABLE | GIL, pack(3, 14)),
    ("stable abi from the future", STABLE | GIL, pack(3, 99)),
    ("free threaded only", STABLE | FREETHREADED, pack(3, 14)),
    ("happy either way", STABLE | GIL | FREETHREADED, pack(3, 14)),
    ("claims internal and stable", STABLE | INTERNAL, sys.hexversion),
)

if ABICHECK:
    check = api.PyABIInfo_Check
    check.argtypes = [ctypes.POINTER(PyABIInfo), ctypes.c_char_p]
    check.restype = ctypes.c_int
    for label, flags, version in CASES:
        info = PyABIInfo(1, 0, flags, sys.hexversion, version)
        try:
            check(ctypes.byref(info), label.encode())
        except ImportError as problem:
            print(f"  {label:32} refused: {str(problem).split(': ', 1)[1]}")
        else:
            print(f"  {label:32} loads")
else:
    print("  nothing to run here, this interpreter has no PyABIInfo_Check")
""",
    differs="On 3.14 this prints the one line saying there is nothing to run.",
)


lesson.md(f"""
{figure("who-gets-refused", "a table of eight hypothetical extensions against two builds, with the verdict in each cell")}

Four different refusals from one function. The version comparisons are at {cite("Python/modsupport.c:731-753@v3.15.0rc1#PyABIInfo_STABLE")}, where a stable extension is allowed to be older than the interpreter but not newer, while a version locked one has to match exactly. The threading check is fifteen lines further down at {cite("Python/modsupport.c:768-782@v3.15.0rc1#Py_GIL_DISABLED")}, and it is symmetrical: a GIL only extension is refused on a free threaded build and a free threaded only one is refused here.

The row that loads on both is the one that claims both flags, which is the same conclusion the file name gave. `abi3t`, and no promise about the lock.

Worth being honest about the limits. This check is opt in, an extension that does not carry the struct is not checked at all, and {cite("Doc/c-api/stable.rst:100-105@v3.15.0rc1")} says plainly that Python does not necessarily check that extensions it loads have a compatible ABI. CPython's own bundled modules opt in through a macro at {cite("Include/cpython/modsupport.h:41-45@v3.15.0rc1#_Py_ABI_SLOT")}, and the slot is read at {cite("Objects/moduleobject.c:471-481@v3.15.0rc1#Py_mod_abi")}, one case in the loop that walks a module's slots.

## How the stable ABI grew

The last thing worth measuring is the stable ABI as a list that changes. It is not fixed. Functions get added to it, one release at a time, and the headers record when each one arrived, in the form of the version gate around its declaration.

{lesson.claim("Every function added to the stable ABI since 3.2 is dated by the preprocessor gate around it, and you can read the dates straight out of the headers.")}
""")


lesson.code(
    """
INCLUDE = pathlib.Path(sysconfig.get_paths()["include"])
HEADERS = INCLUDE.is_dir() and any(INCLUDE.glob("*.h"))

DECLARED = re.compile(r"^PyAPI_FUNC\\([^)]*\\)\\s*\\**\\s*(\\w+)", re.M)
OPENS = re.compile(r"^\\s*#\\s*if")
CLOSES = re.compile(r"^\\s*#\\s*endif")
OLD = re.compile(r"Py_LIMITED_API\\+0\\s*>=\\s*0x03([0-9a-fA-F]{2})0000")
NEW = re.compile(r"Py_LIMITED_API\\+0\\s*>=\\s*_Py_PACK_VERSION\\((\\d+),\\s*(\\d+)\\)")


def gate(line):
    \"\"\"The stable ABI version a preprocessor line gates on, when it gates on one at all.\"\"\"
    hit = NEW.search(line)
    if hit:
        return int(hit.group(2))
    hit = OLD.search(line)
    return int(hit.group(1), 16) if hit else None


if not HEADERS:
    print("  no headers next to this interpreter, looked in", INCLUDE)
    print("  so this cell and the next one have nothing to read")
else:
    arrived = {}
    for path in sorted(INCLUDE.glob("*.h")):
        stack = []
        for line in path.read_text(errors="replace").splitlines():
            if OPENS.match(line):
                stack.append(gate(line))
            elif CLOSES.match(line) and stack:
                stack.pop()
            hit = DECLARED.match(line)
            if hit and any(v for v in stack):
                arrived[hit.group(1)] = max(v for v in stack if v)
    counted = {}
    for version in arrived.values():
        counted[version] = counted.get(version, 0) + 1
    print("  public functions the headers put behind a stable abi version gate:", len(arrived))
    for version in sorted(counted):
        print(f"    3.{version:<4} {counted[version]:4}  {'#' * counted[version]}")
""",
    differs=(
        "On 3.14 the total is 140 rather than 173. There is no 3.15 row, and the 3.14 row is 17 "
        "rather than 18, because one more function was added to it after 3.14 shipped."
    ),
)


lesson.md(f"""
{figure("when-it-arrived", "a bar chart of how many gated functions each release from 3.3 to 3.15 added")}

Two hundred and change over thirteen years, and the recent releases are the busy ones. The 528 functions that were already in the stable ABI when it was defined in 3.2 are not on this chart at all; they have no gate, because there is no version to gate on.

You can point the same scan at one name and get its gate and the line it sits on.

{lesson.claim("A function's stable ABI version is readable from the header line it is declared on.")}
""")


lesson.code(
    """
WANTED = ("PyDict_GetItemRef", "PyLong_AsInt64", "PyABIInfo_Check", "PyList_Append")

if HEADERS:
    for path in sorted(INCLUDE.glob("*.h")):
        lines = path.read_text(errors="replace").splitlines()
        stack = []
        for number, line in enumerate(lines, 1):
            if OPENS.match(line):
                stack.append(gate(line))
            elif CLOSES.match(line) and stack:
                stack.pop()
            hit = DECLARED.match(line)
            if hit and hit.group(1) in WANTED:
                live = [v for v in stack if v]
                answer = f"3.{max(live)} and later" if live else "every version since 3.2"
                print(f"  {hit.group(1):20} {path.name}:{number:<5} {answer}")
""",
    differs=(
        "On 3.14 PyABIInfo_Check is missing from the output entirely, because the declaration "
        "is not in those headers yet. The other three are in the same files at the same lines."
    ),
)


lesson.md(f"""
`PyList_Append` has no gate, so it has been callable from a limited build since the beginning. `PyABIInfo_Check` is gated on 3.15, which is a slightly funny situation: the function that checks whether your ABI is old enough is itself too new for most of the ABIs it would check.

## Both gates on two builds

Everything above ran on one interpreter. The claim that the two gates move together deserves two, so here is the same work run in a container against a build made from the pinned source.

{recording(LOADS)}

Six file name tags, four of the eight sample extensions refused. Now the same program on a build made with `--disable-gil`.

{recording(NOLOCK)}

Four tags rather than six, and six refusals rather than four. Both gates tightened, and they tightened in the same direction: the `abi3` name is gone from the list, and every struct that says `PyABIInfo_GIL` without also saying `PyABIInfo_FREETHREADED` is turned away.

That is the whole argument for `abi3t` in two recordings. An extension shipped as `abi3` in 2024 does not reach a free threaded interpreter, by name or by struct, and neither refusal is a bug.

## Try it yourself

**One.** The finder picked the exact version file over `demo.abi3.so`. Delete that one from the directory and run it again, then keep deleting until only `demo.py` is left. The order you see is the C array in `dynload_shlib.c`, read top to bottom.

**Two.** Set `abiinfo_major_version` to 0 in one of the cases and call the check again. Find the line in `Python/modsupport.c` that explains what you see, and work out why that escape hatch exists.

**Three.** The gate scan only looks at `Include/*.h`. Point it at `Include/cpython/*.h` as well and see how many gated functions turn up there. Then work out why any function in that directory would carry a `Py_LIMITED_API` gate at all.

**Four.** `sys.api_version` is 1013 and has not moved since 2006. Find the two places in the source that still read it, and decide for yourself whether the check they do is worth anything.

## What you now know

An extension has to get past two gates. The first is its file name, and it is cheap, mechanical and unforgiving: the tag has to be one of the handful in a C array compiled into the interpreter, and anything else is not rejected but simply never seen.

The tag is the implementation, the version, a `t` when the build has no global interpreter lock, and the platform. The `abi3` and `abi3t` tags say the file was built against the stable ABI instead. A free threaded build takes only `abi3t`, an ordinary 3.15 build takes both and prefers `abi3`, and 3.14 has never heard of `abi3t`.

The second gate is twelve bytes of struct, new in 3.15 and opt in. It compares four things: whether the extension claims the stable ABI, which version it was built against, whether that version is allowed to be older than yours, and which side of the free threading split it is on. Four of the eight sample extensions in this lesson were refused, and no two of them for the same reason.

Neither gate is a real safety net. The name check happens before anything is read, so it catches the common mistake and nothing else. The struct check happens after the extension's code has already run, and only if the extension asked for it.

## What is next

R08 turns the last three lessons around. Instead of asking what an extension may call and whether it will load, it asks what the interpreter is doing while all of this is happening, and what happens when it stops. Shutdown is the part of the runtime with the fewest promises, and it is where every assumption the earlier lessons made about lifetime finally gets tested.
""")


raise SystemExit(lesson.save())
