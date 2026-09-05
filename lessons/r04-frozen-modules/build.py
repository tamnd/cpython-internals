#!/usr/bin/env python
"""R04. Frozen modules.

The fourth runtime lesson. R03 finished on a loose end: `import os` never opens `os.py`, because
`FrozenImporter` is asked before `PathFinder` and it says yes. This lesson is about what it is
saying yes to, and about the harder problem underneath, which is that the import system is written
in Python and therefore cannot be imported.

The method is to read the frozen table from inside a running interpreter. `_imp` exposes all of it:
the list of names, the code objects, and a switch that turns the whole thing off in process. That
switch is what makes the lesson runnable rather than descriptive, because the same import can be
watched arriving both ways without leaving the notebook.

The two Tier 1 recordings measure what it is worth. The release build and the debug build disagree
about whether to use the frozen copies at all, which is a fact about the build rather than about
Python, and the program reports the default rather than assuming it.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording

lesson = Lesson("r04-frozen-modules", "r04")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("r04-frozen-modules").figure

RELEASE = "r04-what-freezing-saves-at-startup"
DEBUG = "r04-what-freezing-saves-on-a-debug-build"


lesson.md(f"""
# R04. Frozen modules

{badge}

R03 left a loose end. `import os` never opens `os.py`, because `FrozenImporter` is asked before `PathFinder` and it answers first. This lesson is about what it is answering with.

Underneath that there is a harder problem. The import system is written in Python, in `Lib/importlib/_bootstrap.py`, which is a file that would have to be imported. Something has to break that circle, and the thing that breaks it is the same thing that makes `import os` skip the disk.

{figure("from-source-to-binary", "a flow from a source file through a code object and a generated C array into the python3 binary")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/import.c:3389-3428@v3.15.0rc1`.

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

Nearly every cell here runs anywhere Python runs, including in a browser tab, because everything the lesson needs is on the `_imp` module and that is compiled into every build. One cell starts a second interpreter to compare two startups, and it says so and skips itself if it cannot.

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
## You cannot import the import system

`Lib/importlib/_bootstrap.py` is fifteen hundred lines of ordinary Python that implements `__import__`, `sys.meta_path`, module specs and everything else R03 walked through. It is also, obviously, a file. Loading it would need an import, and the thing that performs imports is the file being loaded.

CPython cuts that loop by compiling the file during its own build and storing the resulting bytecode in the binary as a C array. Loading it at startup is then a read out of memory the loader already has, which is a step the C code can take on its own {cite("Python/import.c:3389-3428@v3.15.0rc1#init_importlib")}. That is a {term("frozen module")}, and it is the whole trick.

Two things still have to be arranged. The module needs `sys` and `_imp`, and it cannot import them either, so the C code passes both in as arguments to a function called `_setup`, which assigns them to globals {cite("Lib/importlib/_bootstrap.py:1501-1539@v3.15.0rc1#_setup")}. Then `_install` puts `BuiltinImporter` and `FrozenImporter` on `sys.meta_path` and import starts working {cite("Lib/importlib/_bootstrap.py:1541-1546@v3.15.0rc1#_install")}.

That is the whole {term("import bootstrap")}, and you can check the claim rather than take it: if `_bootstrap.py` really never imports anything at module level, its compiled body has no `IMPORT_NAME` opcodes in it at all.

{lesson.claim("The module body of importlib._bootstrap contains no IMPORT_NAME opcodes, because the two modules it needs are passed in as arguments and assigned to globals rather than imported")}
""")


lesson.code(
    """
import _imp
import dis

for name in ("_frozen_importlib", "_frozen_importlib_external", "os", "site"):
    body = _imp.get_frozen_object(name)
    asked = [step for step in dis.get_instructions(body) if step.opname == "IMPORT_NAME"]
    print(f"  {name:28} {len(asked):2} IMPORT_NAME in the module body")

print()
print("  the first modules any process has:", list(sys.modules)[:6])
""",
    differs=(
        "on 3.14 the two bootstrap counts are the same, but os has 18 rather than 19 and site has "
        "7 rather than 11, because more of what they do became an import between the two releases"
    ),
)


lesson.md(f"""
Zero for the first one, which is the point, and eight for the second one, which is also the point. By the time `_frozen_importlib_external` loads, the module above it has already installed a working import system, so it is allowed to write `import sys` like any other file.

The `sys.modules` line underneath shows the order. `sys` and `builtins` are put there by the C startup code, then `_frozen_importlib` arrives out of the array, then `_imp` is built by hand and handed over. Nothing on that list was found by searching for anything.

The name is worth a second look too. The file is `importlib/_bootstrap.py`, but the frozen entry is called `_frozen_importlib`, because the interpreter needs it long before the `importlib` package exists as something you could reach. A table in `Python/frozen.c` maps one name to the other {cite("Python/frozen.c:127-137@v3.15.0rc1#aliases")}, and that {term("module alias")} is how `importlib._bootstrap` and `_frozen_importlib` end up being the same object in `sys.modules`.

{figure("where-the-loop-is-cut", "a stack of six steps from Py_InitializeFromConfig up to sys.meta_path holding three finders")}

## What else is in there

Once the mechanism exists, it is cheap to use it for more than the bootstrap. The list of what gets frozen is a literal table in the build script {cite("Tools/build/freeze_modules.py:37-76@v3.15.0rc1#FROZEN")}, and it lands in the binary as three separate arrays {cite("Python/frozen.c:74-79@v3.15.0rc1#bootstrap_modules")}.

The three groups are not treated the same way, and `_imp` will show you all of them.

{lesson.claim("A stock 3.15 build has 33 frozen names in three groups, three of which are the import system itself and eleven of which are hello world modules that exist for the test suite")}
""")


lesson.code(
    """
import marshal

names = _imp._frozen_module_names()
hello = [name for name in names if name.startswith(("__hello", "__phello"))]
stdlib = [name for name in names[3:] if name not in hello]

print("  names frozen into this binary:", len(names))
print()
print("  the import system:", ", ".join(names[:3]))
print("  the standard library:", ", ".join(stdlib))
print("  hello world, for the test suite:", len(hello), "names")
print()
total = sum(len(marshal.dumps(_imp.get_frozen_object(name))) for name in names)
print(f"  all of that bytecode, marshalled: {total:,} bytes")
""",
    differs=(
        "3.14 freezes 28 names rather than 33 and the marshalled total is about 439 thousand bytes "
        "rather than 497 thousand, because 3.15 added the encodings package and linecache"
    ),
)


lesson.md(f"""
{figure("three-groups", "a table of the three frozen arrays, what each holds, how many names it has and whether it can be switched off")}

The standard library group is everything a bare `python -c pass` touches, which is why it looks like an odd list. It is not the modules people use most. It is the modules that get imported before your first line runs, and R02 counted them.

The eleven hello world names are `__hello__` and its variations, and they are there so that CPython's own test suite has something to test the machinery on. You can import one right now, and it prints nothing, because the print in it is guarded by `if __name__ == "__main__"`. Try `python -m __hello__` in a terminal to see it speak.

## What a frozen module is made of

A frozen entry is a name, a pointer to some bytes, a length and two flags {cite("Python/import.c:3152-3159@v3.15.0rc1#frozen_info")}. The bytes are a marshalled code object, exactly the payload of a {term("pyc file")} without the header. Loading one is a single call to {term("marshal")} over memory that is already there {cite("Python/import.c:3210-3229@v3.15.0rc1#unmarshal_frozen_code")}, and then `exec_module`, which is four lines long {cite("Lib/importlib/_bootstrap.py:1148-1153@v3.15.0rc1#exec_module")}.

{lesson.claim("A frozen module is a marshalled code object with a co_filename of angle bracket frozen name, and _imp will hand it to you as an ordinary code object you can disassemble")}
""")


lesson.code(
    """
body = _imp.get_frozen_object("os")

print("  what get_frozen_object gives back:", type(body).__name__)
print("  its co_filename:                  ", body.co_filename)
print("  its co_name:                      ", body.co_name)
print(f"  bytes of bytecode in it:           {len(body.co_code):,}")
print()
print("  is_frozen('os'):                  ", _imp.is_frozen("os"))
packages = [name for name in names if _imp.is_frozen_package(name)]
print("  frozen names that are packages:   ", ", ".join(packages))
print()
for name in ("os", "__phello__.ham", "_frozen_importlib"):
    data, is_package, origname = _imp.find_frozen(name)
    print(f"  find_frozen({name!r:20}) -> package {is_package}, frozen from {origname!r}")
""",
    differs=(
        "on 3.14 the frozen body of os is 3,088 bytes rather than 3,360, and encodings is not "
        "frozen there at all, so the only frozen packages that version has are the hello world ones"
    ),
)


lesson.md(f"""
`find_frozen` returns three things and the third is the one to notice. For `os` it is just `os`, and for `_frozen_importlib` it is `importlib._bootstrap`, which is the alias table doing its job. The loader keeps that name so it can fix the module up afterwards {cite("Lib/importlib/_bootstrap.py:1000-1011@v3.15.0rc1#FrozenImporter")}.

`is_package` matters for the same reason it mattered in R03. A frozen package gets an empty `__path__`, which means it is a package with nowhere to look for submodules, so anything underneath one has to be frozen separately under its full dotted name rather than found by searching. `__phello__.ham` is exactly that, and on 3.15 the `encodings` package works the same way, which is why `encodings.utf_8` gets an entry of its own.

## Frozen, but not hidden

Here is where it gets interesting. A frozen module never opens a file, and yet it knows perfectly well which file it would have opened.

`FrozenImporter.find_spec` works out where the source lives, from `sys._stdlib_dir` and the name, and parks it on the spec as {term("loader state")} {cite("Lib/importlib/_bootstrap.py:1106-1133@v3.15.0rc1#find_spec")}. The loader then copies it onto `__file__`. So the spec says `frozen` and `__file__` says `/some/path/os.py`, and both are true.

{lesson.claim("A frozen module reports an origin of frozen and a cached of None while still carrying a real path on __file__, which is what lets a traceback through frozen code show you the source line")}
""")


lesson.code(
    """
import linecache
import os

print("  os.__spec__.origin:      ", os.__spec__.origin)
print("  os.__spec__.cached:      ", os.__spec__.cached)
print("  os.__spec__.has_location:", os.__spec__.has_location)
print("  os.__spec__.loader_state:", os.__spec__.loader_state.filename.rpartition("/")[2])
print("  os.__file__ is a file that exists:", os.path.exists(os.__file__))
print()
where = os.get_exec_path.__code__
print("  the code object for os.get_exec_path says it came from:", where.co_filename)
print("  linecache asked for that line with nothing else:")
print("   ", repr(linecache.getline(where.co_filename, where.co_firstlineno)))
print("  and asked again with the module's globals:")
print("   ", repr(linecache.getline(where.co_filename, where.co_firstlineno, os.__dict__)))
""",
    varies=(
        "the last two lines need the source file to be sitting where the loader state says it is, "
        "so a runtime that ships its standard library as a zip with no os.py next to it, which is "
        "what a browser does, reports that the path does not exist and gives you two empty strings"
    ),
)


lesson.md(f"""
{figure("frozen-but-not-hidden", "a table of five questions about the frozen os module and the answer each one gives")}

That second `linecache` call is the whole trick behind readable tracebacks in frozen code. When the filename starts with `<frozen `, `linecache` ignores it and reads `__file__` out of the globals it was handed instead {cite("Lib/linecache.py:122-140@v3.15.0rc1#module_globals")}. `traceback` passes those globals, which is why an error inside `os` prints `File "<frozen os>", line 710` and then shows you the actual line. `inspect` has its own version of the same fix up {cite("Lib/inspect.py:3386-3400@v3.15.0rc1#source_file")}.

The one thing that genuinely is gone is the loader's own source lookup. `FrozenImporter.get_source` returns `None` and always will {cite("Lib/importlib/_bootstrap.py:1155-1165@v3.15.0rc1#get_code")}, because from the loader's point of view there was no source, only bytes.

## Switching it off

The bootstrap group has to be frozen or nothing starts. Everything after it is a speed decision, so there is a switch: `-X frozen_modules=off`, or `PYTHON_FROZEN_MODULES=off` in the environment {cite("Python/initconfig.c:2849-2866@v3.15.0rc1#frozen_modules")}.

The switch cannot reach the bootstrap group, and the reason is four lines of C. `look_up_frozen` walks the bootstrap array unconditionally, and only the standard library and test arrays sit behind a check of the flag {cite("Python/import.c:3104-3129@v3.15.0rc1#look_up_frozen")} {cite("Python/import.c:3130-3150@v3.15.0rc1#use_frozen")}.

There is also an in process version of the same switch, which the test suite uses and which means you can watch both answers without leaving this notebook.

{lesson.claim("Turning frozen modules off in process removes the standard library and test names from the frozen table and leaves exactly the three bootstrap names, which no setting can remove")}
""")


lesson.code(
    """
from importlib.machinery import FrozenImporter

print("  frozen names on:", len(_imp._frozen_module_names()))
print("  FrozenImporter.find_spec('stat'):", FrozenImporter.find_spec("stat"))

_imp._override_frozen_modules_for_tests(-1)
try:
    print()
    print("  frozen names off:", _imp._frozen_module_names())
    print("  FrozenImporter.find_spec('stat'):", FrozenImporter.find_spec("stat"))
    still = FrozenImporter.find_spec("_frozen_importlib")
    print("  and the bootstrap is still there:", still.origin)
    print("  is_frozen('os') now says:", _imp.is_frozen("os"))
finally:
    _imp._override_frozen_modules_for_tests(0)

print()
print("  back on again, frozen names:", len(_imp._frozen_module_names()))
""",
    differs=(
        "3.14 freezes 28 names rather than 33, so the first and last lines both read 28 there, and "
        "the three names left standing in the middle are the same three on either version"
    ),
)


lesson.md(f"""
With the switch off, `FrozenImporter` declines to answer for `stat`, so the next finder along gets asked and the import lands on the file. The module you end up with is the same module. Only its paperwork changes.

{lesson.claim("The same import statement produces a module with an origin of frozen or an origin of a file path depending only on the switch, and the module works identically either way")}
""")


lesson.code(
    """
def reimport(name):
    \"\"\"Throw a module away and import it again, so a fresh search happens.\"\"\"
    sys.modules.pop(name, None)
    return __import__(name)


_imp._override_frozen_modules_for_tests(-1)
try:
    from_disk = reimport("stat")
    print("  with the switch off, stat came from:", from_disk.__spec__.origin.rpartition("/")[2])
    print("  its loader:                         ", type(from_disk.__spec__.loader).__name__)
finally:
    _imp._override_frozen_modules_for_tests(0)

frozen = reimport("stat")
print("  with the switch on, stat came from: ", frozen.__spec__.origin)
print("  its loader:                         ", frozen.__spec__.loader.__name__)
print()
print("  same constant either way:", from_disk.S_IFREG == frozen.S_IFREG)
""",
    varies=(
        "the loader you get with the switch off depends on where your runtime keeps its standard "
        "library, so a browser, which serves it out of a zip file, reports a zipimporter instead "
        "of a SourceFileLoader and a path inside the zip instead of a path on disk"
    ),
)


lesson.md(f"""
## What one costs to load

It is tempting to guess that a frozen module loads faster because unmarshalling from memory beats unmarshalling from a file. That is not it. Both paths end in the same `marshal.loads` over the same bytes, and that call is the expensive part. What freezing removes is everything in front of it.

{figure("two-ways-in", "a comparison of three steps to load a frozen module against five steps to load the same module from disk")}

{lesson.claim("Loading a module from a file and loading it out of the binary end in the same unmarshal of the same bytes, and what freezing removes is the finder search and the file read in front of that")}
""")


lesson.code(
    """
import pathlib
import time
from importlib.machinery import PathFinder


def per_call(work, rounds=2000):
    \"\"\"Seconds per go, best of three, so one unlucky moment does not decide the answer.\"\"\"
    best = None
    for _ in range(3):
        started = time.perf_counter()
        for _ in range(rounds):
            work()
        taken = (time.perf_counter() - started) / rounds
        best = taken if best is None else min(best, taken)
    return best


asking_frozen = per_call(lambda: FrozenImporter.find_spec("os"))
asking_path = per_call(lambda: PathFinder.find_spec("os", sys.path))
print(f"  asking FrozenImporter for os:        {asking_frozen * 1e6:8.2f} microseconds")
print(f"  asking PathFinder for the same name: {asking_path * 1e6:8.2f} microseconds")

tag = f"cpython-{sys.version_info[0]}{sys.version_info[1]}"
pyc = pathlib.Path(os.__file__).with_name("__pycache__") / f"os.{tag}.pyc"
if pyc.exists():
    raw = pyc.read_bytes()
    reading = per_call(pyc.read_bytes)
    unmarshal = per_call(lambda: marshal.loads(raw[16:]))
    print(f"  reading those {len(raw):,} bytes off disk: {reading * 1e6:8.2f} microseconds")
    print(f"  marshal.loads on what it read:       {unmarshal * 1e6:8.2f} microseconds")
else:
    print("  this runtime keeps no pyc for os, so the last two rows have nothing to measure")
""",
    varies=(
        "these are timings on your machine, so the absolute numbers depend on your processor and "
        "your filesystem, the second row depends on how many entries your sys.path has, and a "
        "runtime that keeps its standard library in a zip file has no pyc for os at all"
    ),
)


lesson.md("""
The last row is the same work either way, and it is most of the bill. The first two rows are the difference, and they are not close: asking `FrozenImporter` is a lookup in a C array, while asking `PathFinder` means walking `sys.path`, consulting the caches R03 took apart, and finding a match. Add the file read on top of it.

Multiply that by the number of modules a startup loads before your first line runs, and you have the whole of what freezing is for.

""")


lesson.md(f"""
## What it saves at startup

Which brings us to the number people actually want. A whole interpreter startup, measured both ways, on a machine that is not otherwise busy.

The list is the part that travels. Timings depend on your disk and your processor, but which files a startup opens does not, and `-v` prints one line for each code object it reads.

{lesson.claim("Every file a bare startup reads only when frozen modules are switched off is a pyc for a module in the frozen standard library group, which means freezing saves file reading rather than compiling")}
""")


lesson.code(
    """
import subprocess

ON = ["-X", "frozen_modules=on"]
OFF = ["-X", "frozen_modules=off"]


def files_read(flags):
    \"\"\"The name of every file a fresh interpreter reads a code object out of, in order.\"\"\"
    started = subprocess.run(
        [sys.executable, *flags, "-v", "-c", "pass"], capture_output=True, text=True, check=True
    )
    lines = started.stderr.splitlines()
    return [line.split("'")[1] for line in lines if line.startswith("# code object from")]


def module_name(path):
    \"\"\"Turn the path of a pyc file back into the name of the module it holds.\"\"\"
    parts = pathlib.Path(path).parts
    stem = parts[-1].split(".")[0]
    return parts[-3] if stem == "__init__" else stem


try:
    on, off = files_read(ON), files_read(OFF)
    print(f"  files a bare startup reads with the flag on: {len(on)}, and with it off: {len(off)}")
    print()
    print("  the ones only the second run needed:")
    tails = {name.rpartition(".")[2] for name in names}
    for path in [one for one in off if one not in on]:
        held = module_name(path)
        print(f"    {held:20} is in the frozen list: {held in tails}")
except OSError:
    print("  this runtime cannot start a second process, so this cell has nothing to show")
""",
    varies=(
        "the totals depend on what your interpreter loads at startup, and a virtual environment "
        "adds a handful of files to both runs, but the list underneath is the frozen standard "
        "library either way, minus whichever of those names your version had not frozen yet"
    ),
)


lesson.md(f"""
Every name on that list is a `.pyc` that had already been compiled, so what freezing saves at startup is not compiling anything. It is a dozen rounds of asking finders, listing directories, opening files and checking timestamps.

Now the clock. Two Tier 1 recordings run the same program in a container, once on a release build and once on a debug build, and the interesting part is that the two builds disagree about the default.

{recording(RELEASE)}

{recording(DEBUG)}

{figure("what-freezing-saves", "bars comparing startup milliseconds with frozen modules on and off, on a release build and a debug build")}

Both builds ship the same 33 frozen names, both read 13 files when told not to use them, and both save around a tenth of a startup by using them. What differs is the line that says whether the build uses them unless told otherwise: `True` on the release build and `False` on the debug one.

That is a deliberate choice in the config defaults {cite("Python/initconfig.c:1193-1201@v3.15.0rc1#use_frozen_modules")}. A debug build is the build you use when you are editing `Lib/os.py`, and it would be miserable if your edits were ignored until you re ran the freeze step. So debug builds read the files, and everybody else gets the speed.

{lesson.claim("A build configured with --with-pydebug leaves frozen modules off by default while a release build leaves them on, so the same interpreter version can disagree with itself about where os came from", unobservable="it needs two builds of the same source in two containers, and one notebook is only ever one of them")}
""")


lesson.md(f"""
## Try it yourself

Four things, in rough order of how much you will learn.

Run `python -X frozen_modules=off -X importtime -c pass` and then the same command without the flag, and compare the two trees. Every line that appears only in the first run is a module the frozen build got for free.

Point the disassembly cell at `_frozen_importlib_external` instead and then open the file at those lines. All eight imports are at the top, written completely normally, because by the time that module loads there is an import system to use.

Read the last few lines of `Python/frozen.c` {cite("Python/frozen.c:140-144@v3.15.0rc1#PyImport_FrozenModules")}. There is a fourth pointer there, it starts as `NULL`, and the comment invites an embedding application to point it at an array of its own. That is the supported way to ship a single file executable with a standard library inside it, and `look_up_frozen` checks it before the standard library group.

Delete `stat` from `sys.modules`, turn the switch off, import it, and look at `stat.__spec__.cached`. A file import can write a `.pyc` and a frozen one has nothing to write, so the two runs leave different things behind on your disk.

## What you now know

The import system is written in Python and cannot be imported, so it is compiled during CPython's build and stored in the binary as a C array. The C startup code loads it directly and hands it `sys` and `_imp` as arguments.

`importlib._bootstrap` has no imports in its module body at all. `importlib._bootstrap_external`, which loads second, has eight, because by then import works.

A frozen module is a marshalled code object and nothing more. Loading one is a read out of memory plus an `exec`.

There are 33 of them in a stock 3.15 build, in three groups. The three bootstrap names are searched no matter what. The nineteen standard library names and the eleven test names sit behind a flag.

A frozen module still knows the path it was compiled from, because the loader parks it on the spec and copies it to `__file__`. That is why tracebacks say `<frozen os>` and still show you real source lines.

`-X frozen_modules=off` is a supported way to see the difference, and `_imp._override_frozen_modules_for_tests` does the same thing without starting a new process.

Freezing is worth about a tenth of a startup and thirteen files that never get opened. Debug builds leave it off by default so that editing the standard library works the way you expect.

## What is next

R05 is about the newest thing in this area. PEP 810 adds lazy imports to 3.15: an import that binds the name now and does the actual loading the first time somebody reads it.

That changes the shape of everything R03 and R04 established. The module is not in `sys.modules` when the statement finishes, the finders have not been asked yet, and the cost has moved from startup to whenever the name is first touched. The disassembly cell in this lesson already hinted at it, because on 3.15 an `IMPORT_NAME` argument prints with an eager or lazy marker attached to it.
""")


raise SystemExit(lesson.save())
