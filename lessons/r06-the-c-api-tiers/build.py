#!/usr/bin/env python
"""R06. The C API tiers.

The sixth runtime lesson, and the first one that is really about C rather than about Python.
CPython's C API lives in three directories, and which one you are allowed to reach into is
decided by two macros you set before you include anything.

The awkward part of writing this lesson is that half of it wants to read the headers, and the
headers are not always there. A normal install ships them, Colab usually does, and a browser
tab never does. So the header cells all sit behind one flag set in the first of them, and they
say so out loud rather than printing nothing.

The two Tier 1 recordings answer the question the notebook cannot answer on its own, which is
whether the sweep is telling the truth about builds other than yours. They run the same
program on the ordinary build and on the free threaded one.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording

lesson = Lesson("r06-the-c-api-tiers", "r06")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("r06-the-c-api-tiers").figure

LEAVES = "r06-what-leaves-the-binary"
FREE = "r06-what-leaves-the-binary-on-a-free-threaded-build"


lesson.md(f"""
# R06. The C API tiers

{badge}

Everything so far has looked at CPython from inside Python. This one looks at it from the other side, the way a C extension does.

An extension gets at the interpreter by including `Python.h` and calling functions. Which functions it is allowed to call is not one list. It is three, they live in three directories, and you pick which ones you get by defining a macro before the include.

{figure("three-doors", "three nested rings, the public headers inside the cpython only headers inside the internal headers")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Include/exports.h:88-93@v3.15.0rc1`.

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

About half the cells here read the header files that sit next to the interpreter. A normal install has them and a browser tab does not, so the first cell below works out whether they are there and the rest check that answer before they do anything. The other half only need `ctypes`, which works everywhere.

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
## Three directories

{term("C API", "the set of C functions and macros an extension may call to talk to the interpreter")} is not one thing. `Include/` holds the headers any extension may use. `Include/cpython/` holds the ones that only make sense if you were compiled against this exact CPython. `Include/internal/` holds the ones CPython uses on itself.

The first cell finds where they live and measures how much is in each. The interesting number is the third one.

{lesson.claim("Most of CPython's header surface is in the directory extensions are not meant to open.")}
""")


lesson.code(
    """
import pathlib
import sysconfig

INCLUDE = pathlib.Path(sysconfig.get_paths()["include"])
TIERS = (("public", "*.h"), ("cpython only", "cpython/*.h"), ("internal", "internal/*.h"))
HEADERS = INCLUDE.is_dir() and any(INCLUDE.glob("*.h"))


def headers(pattern):
    \"\"\"Every header in one tier as text, or nothing when this runtime did not ship them.\"\"\"
    return [path.read_text(errors="replace") for path in sorted(INCLUDE.glob(pattern))]


if not HEADERS:
    print("  no headers next to this interpreter, looked in", INCLUDE)
    print("  the cells that read them say so and skip themselves")
else:
    print("  headers live in", INCLUDE)
    for tier, pattern in TIERS:
        blobs = headers(pattern)
        lines = sum(len(blob.splitlines()) for blob in blobs)
        print(f"  {tier:13} {len(blobs):4} files {lines:7} lines")
""",
    differs=(
        "On 3.14 the internal directory is a good deal smaller, 139 files and about thirty "
        "thousand lines rather than 148 and forty two thousand."
    ),
)


lesson.md(f"""
More than half the lines are in the directory nobody outside CPython is supposed to read. That is not a mistake. The interpreter is written against its own headers, and those headers describe the parts that change from release to release.

{figure("who-can-see-what", "a table of the three tiers, the directory each one lives in, the macro that opens it, how its names look and how long it lasts")}

The right hand column is the whole point. The public tier is covered by CPython's backwards compatibility policy. The middle one may change in any minor release. The internal one may change in a patch release, and the documentation says so plainly in {cite("Doc/c-api/stable.rst:21-35@v3.15.0rc1")}.

## What one macro hides

The gate is `Py_LIMITED_API`. Define it before you include `Python.h` and a large amount of the header tree stops existing for you.

The mechanism is dull and worth seeing once. At the bottom of {cite("Include/object.h:740-744@v3.15.0rc1#Py_CPYTHON_OBJECT_H")} there is an `#ifndef Py_LIMITED_API` around an `#include "cpython/object.h"`. Almost every public header ends the same way. That is the entire second door.

{term("limited API", "the subset of the C API you get when you define Py_LIMITED_API before including Python.h")} is not a separate set of files. It is the same files with a lot of them switched off.

{lesson.claim("Defining Py_LIMITED_API removes about a quarter of the functions declared in the public headers, and all of the other two directories.")}
""")


lesson.code(
    """
import re

DECLARED = re.compile(r"^PyAPI_FUNC\\([^)]*\\)\\s*\\**\\s*(\\w+)", re.M)
OPENS = re.compile(r"^\\s*#\\s*if")
CLOSES = re.compile(r"^\\s*#\\s*endif")
ASKED = ("PyList_Append", "PyErr_SetString", "PyBuffer_FillInfo", "PyThreadState_GetFrame")


def split_by_the_guard(text):
    \"\"\"Split one header's function names into what a limited build sees and what it does not.\"\"\"
    shut = []
    seen, hidden = set(), set()
    for line in text.splitlines():
        if OPENS.match(line):
            shut.append("Py_LIMITED_API" in line and ("ifndef" in line or "!defined" in line))
        elif CLOSES.match(line) and shut:
            shut.pop()
        found = DECLARED.match(line)
        if found:
            (hidden if any(shut) else seen).add(found.group(1))
    return seen, hidden


if HEADERS:
    seen, hidden = set(), set()
    for blob in headers("*.h"):
        one, other = split_by_the_guard(blob)
        seen |= one
        hidden |= other
    away = set()
    for pattern in ("cpython/*.h", "internal/*.h"):
        for blob in headers(pattern):
            away |= set(DECLARED.findall(blob))
    print("  in the public headers")
    print("    functions a limited build may call:", len(seen))
    print("    functions the guard takes away:    ", len(hidden))
    print("  in the other two directories, which it never opens:", len(away))
    print()
    for name in ASKED:
        answer = "yes" if name in seen else "no, the guard hides it"
        print(f"    can a limited build call {name:24} {answer}")
""",
    differs=(
        "On 3.14 the numbers are 575 and 162, and 824 in the other two directories. The four "
        "answers underneath are the same."
    ),
)


lesson.md(f"""
{figure("the-gate", "a four step flow, including Python.h, checking whether Py_LIMITED_API is defined, and either pulling in cpython/object.h or skipping it")}

Losing a quarter of the functions is the part people notice. It is not the part that hurts.

What actually hurts is that the struct definitions go too. With `_Py_OPAQUE_PYOBJECT` set, {cite("Include/object.h:124-126@v3.15.0rc1#_Py_OPAQUE_PYOBJECT")} says only `/* PyObject is opaque */`, so there is no `ob_refcnt` field to read and no `ob_type` field to follow.

{figure("what-limited-costs", "a comparison of an ordinary build against a limited one, showing that the fields disappear and the macros become calls")}

That is the trade. You give up knowing where anything is, and in return one built file keeps working across releases, because the thing that changes between releases is where everything is.

## The lock on the third door

The third door has a different kind of lock, and it is worth seeing because it is so much cruder than you would expect.

{cite("Include/internal/pycore_object.h:7-9@v3.15.0rc1#Py_BUILD_CORE")} is three lines: if `Py_BUILD_CORE` is not defined, stop the compiler with an error message. Nearly every file in that directory starts with the same three lines.

{lesson.claim("The internal headers are protected by a compiler error and nothing else.")}
""")


lesson.code(
    """
if HEADERS:
    blobs = headers("internal/*.h")
    refuse = [blob for blob in blobs if "#ifndef Py_BUILD_CORE" in blob]
    print("  internal headers:                        ", len(blobs))
    print("  that stop the compiler without the macro:", len(refuse))
    print()
    start = refuse[0].index("#ifndef Py_BUILD_CORE")
    for line in refuse[0][start:].splitlines()[:3]:
        print("     ", line)
""",
    differs="On 3.14 it is 139 headers and 132 of them, because the directory grew in 3.15.",
)


lesson.md(f"""
Nothing stops you defining `Py_BUILD_CORE` yourself. People do. It compiles, it links, and it breaks on the next patch release when a struct grows a field.

## The names and the directories

There is a second convention running alongside the directories, and it is the one you meet first, because it is in the names.

A plain `Py` name is public. A `PyUnstable_` name is the middle tier saying so out loud, which {cite("Doc/c-api/stable.rst:44-52@v3.15.0rc1")} describes as intended for debuggers and tools that follow CPython development. A leading underscore means private.

You would expect the three conventions to line up exactly with the three directories. They nearly do.

{lesson.claim("The naming convention and the directory disagree about a few dozen functions, in both directions.")}
""")


lesson.code(
    """
if HEADERS:

    def convention(name):
        \"\"\"Which of the three naming conventions a name follows.\"\"\"
        if name.startswith("PyUnstable"):
            return "PyUnstable"
        return "underscore" if name.startswith("_") else "plain Py"

    print(f"  {'tier':13} {'plain Py':>9} {'PyUnstable':>11} {'underscore':>11}")
    for tier, pattern in TIERS:
        names = set()
        for blob in headers(pattern):
            names |= set(DECLARED.findall(blob))
        counted = {"plain Py": 0, "PyUnstable": 0, "underscore": 0}
        for name in names:
            counted[convention(name)] += 1
        print(
            f"  {tier:13} {counted['plain Py']:>9} "
            f"{counted['PyUnstable']:>11} {counted['underscore']:>11}"
        )
""",
    differs=(
        "The three rows on 3.14 read 716, 1, 20 then 304, 30, 89 then 8, 0, 394. The shape is "
        "the same and the internal row is a lot shorter."
    ),
)


lesson.md(f"""
{figure("names-against-tiers", "a table counting plain Py names, PyUnstable names and underscore names in each of the three directories")}

The seventeen underscore names in the public row are the interesting ones, and they all have the same explanation. `Py_DECREF` is a macro, and at {cite("Include/refcount.h:417-429@v3.15.0rc1#Py_DECREF")} you can see what it expands to: a decrement, and then a call to `_Py_Dealloc` if the count reached zero.

That call happens in your code, after the macro is pasted in. So `_Py_Dealloc` has to be a symbol your extension can link against, private name or not, and it is declared two hundred lines earlier at {cite("Include/refcount.h:238-241@v3.15.0rc1#_Py_Dealloc")}.

A private name has to be public when a public macro expands to it. That is the whole rule, and it accounts for nearly the entire list.

## Ask the linker instead

Everything up to here has been about compiling. Now the interesting bit, which is what happens once the compiling is over.

Python can look up C symbols by name. `ctypes.pythonapi` is a handle on the running interpreter, and asking it for an attribute asks the dynamic linker for a symbol with that name.

{lesson.claim("The tier a function belongs to makes no difference to whether you can find it at run time.")}
""")


lesson.code("""
import ctypes

api = ctypes.pythonapi
SAMPLE = (
    ("public", "PyList_Append"),
    ("public", "PyErr_SetString"),
    ("cpython only", "PyUnstable_Code_New"),
    ("cpython only", "PyFrame_GetLasti"),
    ("internal", "_PyDict_SizeOf"),
    ("internal", "_PyEval_EvalFrameDefault"),
    ("internal", "_PyObject_GC_New"),
    ("no such name", "PyNothingLikeThis"),
)
for tier, name in SAMPLE:
    found = "the linker hands it over" if hasattr(api, name) else "not found"
    print(f"  {tier:13} {name:26} {found}")
""")


lesson.md(f"""
Seven for seven, and the made up name is the only one that fails. The three tiers are a compile time arrangement. By the time there is a binary, they are gone.

Which raises the obvious question: is the internal tier exported by accident, or on purpose? The answer is in the headers, and it is on purpose.

{term("PyAPI_FUNC", "the macro that marks a declaration as a symbol other binaries may link against")} expands, at {cite("Include/exports.h:88-93@v3.15.0rc1#PyAPI_FUNC")}, to `Py_EXPORTED_SYMBOL`, which is the compiler attribute for default visibility. A declaration that does not use it is not exported.

The internal headers use both spellings, often two lines apart. `_PyDict_SizeOf` at {cite("Include/internal/pycore_dict.h:50-54@v3.15.0rc1#_PyDict_SizeOf")} is `PyAPI_FUNC`, with a comment above it saying which shipped extension needs it, and `_PyDict_SizeOf_LockHeld` right underneath is a plain `extern`.

{lesson.claim("Inside the internal headers, the two spellings decide what leaves the binary, and almost nothing crosses over.")}
""")


lesson.code(
    """
EXTERN = re.compile(r"^extern\\s+[\\w *]+?\\**\\s*(\\w+)\\s*\\(", re.M)
WHO = re.compile(r"^//\\s*Export for (.+?)\\.?$", re.M)

if HEADERS:
    loud, quiet, asked = set(), set(), []
    for blob in headers("internal/*.h"):
        loud |= set(DECLARED.findall(blob))
        quiet |= set(EXTERN.findall(blob))
        asked += WHO.findall(blob)
    quiet -= loud
    out = sum(1 for name in loud if hasattr(api, name))
    kept = sum(1 for name in quiet if hasattr(api, name))
    print(f"  spelled PyAPI_FUNC:   {len(loud):4}, and {out} of them resolve")
    print(f"  spelled plain extern: {len(quiet):4}, and {kept} of them resolve")
    print()
    print("  comments naming who needs the export:", len(asked))
    print("  the first three:", ", ".join(asked[:3]))
""",
    differs=(
        "On 3.14 it is 402 exported and 388 resolving, against 783 held back and 2 resolving, "
        "with 161 comments rather than 168. The gap between the two spellings is the same shape."
    ),
)


lesson.md(f"""
So the internal tier is deliberately half exported. The reason is in those comments: CPython's own bundled extensions, `math` and `_asyncio` and `_pickle` and the rest, are compiled as separate shared libraries, and they need to reach back into the interpreter that loaded them.

The handful of exported names that did not resolve are the ones behind `Py_GIL_DISABLED` and the Windows only ones, which is why the free threaded recording at the end finds a few more.

## Calling one of them

Finding a symbol is not the same as calling it. Calling it means telling `ctypes` what the arguments and the return value are, and getting that wrong crashes the process rather than raising.

`_PyDict_SizeOf` is a safe one to try. It takes a dict and returns a count of bytes, and there is a familiar function sitting on top of it.

{lesson.claim("The internal function, the dunder and sys.getsizeof are the same measurement with one thing added.")}
""")


lesson.code("""
size_of = api._PyDict_SizeOf
size_of.argtypes = [ctypes.py_object]
size_of.restype = ctypes.c_ssize_t

small = {"a": 1, "b": 2}
print("  what the internal function says:", size_of(small))
print("  what the dunder says:           ", small.__sizeof__())
print("  what sys.getsizeof says:        ", sys.getsizeof(small))
print("  the difference:                 ", sys.getsizeof(small) - small.__sizeof__())
try:
    import _testinternalcapi

    print("  and the header the collector adds:", _testinternalcapi.SIZEOF_PYGC_HEAD, "bytes")
except ImportError:
    print("  and _testinternalcapi is not here to say what that difference is")
""")


lesson.md(f"""
`dict.__sizeof__` is a thin wrapper around the internal function, so those two agree exactly. `sys.getsizeof` adds the bytes the cycle collector keeps in front of the object, which you can see it doing at {cite("Python/sysmodule.c:1970-1979@v3.15.0rc1#_PyType_PreHeaderSize")}.

We went round the outside and got the same answer the front door gives. That is the honest summary of what the internal tier is: not hidden, just unsupported.

## A macro and a function with the same name

One more thing falls out of all this, and it explains the shape of a lot of the header tree.

If a limited build cannot see the struct, it cannot read `ob_type` to implement `Py_TYPE`. So `Py_TYPE` has to exist twice: as a macro for everybody else, and as a real exported function for the limited build.

{cite("Include/object.h:185-198@v3.15.0rc1#Py_Is")} does this in the open. A `PyAPI_FUNC` declaration, then a `#define` of the same name on the very next line. The macro wins when it is visible, and the function is there when it is not.

{lesson.claim("Some C API names are a macro and an exported function at once, and which one you get depends on your build.")}
""")


lesson.code(
    """
for name in ("Py_TYPE", "Py_REFCNT", "Py_SIZE", "Py_IS_TYPE", "Py_Is", "Py_DECREF", "Py_CLEAR"):
    both = "declared as well, so a limited build can call it"
    print(f"  {name:11} {both if hasattr(api, name) else 'a macro and nothing else'}")
""",
    differs=(
        "On 3.14 Py_SIZE and Py_IS_TYPE are macros and nothing else. They got their function "
        "forms in 3.15, which the comment above them in object.h dates."
    ),
)


lesson.md(f"""
`Py_DECREF` and `Py_CLEAR` never got function forms, which is why a limited build calls `_Py_DecRef` instead, as {cite("Include/refcount.h:327-338@v3.15.0rc1#Py_DECREF")} shows.

That is the cost of the limited API in one line. The single most common operation in the whole C API stops being a decrement and becomes a function call.

## What the file name says

None of the tiers show up in a built extension. One thing does, and it is the file name.

{term("stable ABI", "a build of an extension that keeps working across releases, marked by abi3 in its file name")} extensions are named `something.abi3.so`. Version locked ones carry the exact version, like `something.cpython-315-darwin.so`. The interpreter decides what it is willing to load from that suffix alone.

{lesson.claim("Which tier an installed extension was built against is written on the outside of the file.")}
""")


lesson.code(
    """
import importlib.machinery

print("  suffixes this interpreter will load:")
for one in importlib.machinery.EXTENSION_SUFFIXES:
    print("   ", one)
print()
counted = {"built for one version": 0, "built for the stable abi": 0, "no tag at all": 0}
example = {}
for entry in {p for p in sys.path if p and pathlib.Path(p).is_dir()}:
    for found in pathlib.Path(entry).rglob("*.so"):
        tag = (
            "built for the stable abi"
            if ".abi3" in found.name
            else "built for one version"
            if ".cpython-" in found.name
            else "no tag at all"
        )
        counted[tag] += 1
        example.setdefault(tag, found.name)
for tag, total in counted.items():
    print(f"  {tag:26} {total:4}  {example.get(tag, '')}")
""",
    varies=(
        "The counts underneath are whatever happens to be installed where you are running "
        "this, so they will not match. The suffix list is the part that depends on the "
        "version: 3.14 offers three and 3.15 offers six, because 3.15 added abi3t for free "
        "threaded builds."
    ),
)


lesson.md(f"""
Three suffixes on 3.14 and six on 3.15. The new ones end in `abi3t`, and they belong to PEP 803, which gives free threaded builds their own stable ABI. R07 is about that list.

## How much really leaves the binary

Everything above was measured on whatever machine you are reading this on. The claim that the internal tier is half exported deserves better than that, so here is the same sweep run in a container, on a build made from the pinned source.

{recording(LEAVES)}

Ninety three percent of the private declarations that are spelled `PyAPI_FUNC` can be found by name, and four in a thousand of the ones spelled `extern` can. Two spellings, two completely different outcomes, in the same files.

{figure("what-leaves-the-binary", "a bar chart comparing the share of internal PyAPI_FUNC names that resolve against the share of plain extern names")}

The other run is the same program on a build made with `--disable-gil`, which compiles a different half of the headers.

{recording(FREE)}

Six more names resolve there, and the numbers on the three tiers are otherwise identical. The extra six are the ones guarded by `Py_GIL_DISABLED`, which is the answer to whether the missing names were a mystery or just a build flag.

## Try it yourself

**One.** Take the sweep in the cell above and print the names in the internal headers that are spelled `PyAPI_FUNC` but do not resolve. Then go and look two of them up in the pinned source and work out what they have in common.

**Two.** `PyUnstable_Code_New` resolved in the linker cell. Find its declaration in `Include/cpython/code.h` and work out from the comments around it why a name with `Unstable` in it is declared in a header at all rather than being kept private.

**Three.** The cross tabulation cell counts eight plain `Py` names in the internal directory. Print them. They are all from the same area of the interpreter, and the reason is a piece of history rather than a design decision.

**Four.** `ctypes.pythonapi` also finds data, not just functions. Look up `PyLong_Type` with `ctypes.cast` and confirm the address you get back is the same one `id(int)` reports.

## What you now know

The C API is three directories. `Include/` is for anybody, `Include/cpython/` needs you not to have defined `Py_LIMITED_API`, and `Include/internal/` needs you to define `Py_BUILD_CORE` and stops the compiler with an error if you do not.

The limited API takes away about a quarter of the public functions, and all of the struct layouts. The second half is the expensive one, because it turns field reads into function calls, `Py_DECREF` included.

The naming convention nearly matches the directories, and the exceptions have a reason. A private name has to be exported when a public macro expands to it.

None of this survives the build. The linker exports ninety three percent of the internal declarations that ask for it, on purpose, because CPython's own bundled extensions are separate shared libraries that need to reach back in. What stops you using them is a comment and a compiler error, not the loader.

## What is next

R07 takes the last cell and expands it. The stable ABI is what `abi3` means, `abi3t` is what 3.15 added for free threaded builds, and `PyABIInfo` at {cite("Include/modsupport.h:85-101@v3.15.0rc1#PyABIInfo")} is the struct an extension carries so the interpreter can check, at load time, that the two of you agree about which tier you compiled against.
""")


raise SystemExit(lesson.save())
