#!/usr/bin/env python
"""R03. What import does.

The third runtime lesson. `import` looks like a keyword doing something the language will not
explain, and it is nothing of the sort. It compiles to one call to an ordinary builtin, and that
builtin runs Python code you can read, hook, replace and time.

The method is to watch rather than to describe. Compile the four spellings of the statement and
look at what each one binds. Put a finder on the front of `sys.meta_path` that answers nothing and
writes down every question. Build a circular import in a temporary directory and catch the module
halfway through its own body. Serve a module out of a string with fourteen lines of class.

The two Tier 1 recordings settle the question everybody gets wrong about the import lock: it is
one lock per module name, so what serialises two threads importing two different modules is the
GIL and nothing else.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording

lesson = Lesson("r03-what-import-does", "r03")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("r03-what-import-does").figure

WITH_LOCK = "r03-how-much-of-an-import-is-parallel"
WITHOUT_LOCK = "r03-how-much-of-an-import-is-parallel-without-the-lock"


lesson.md(f"""
# R03. What import does

{badge}

R02 ended by noticing that a brand new interpreter imports dozens of modules of its own before it will run a line of your code. This lesson is about how it does that.

`import` reads like a keyword that does something magic. It is not. It compiles to a call to an ordinary function you can reach as `__import__`, and that function is written in Python, in a file you can open. Everything it does is visible from inside the language: the list of finders it asks, the object they hand back, the moment your module becomes visible to other code, and the three caches that make the second import of anything nearly free.

{figure("the-import-protocol", "a stack of six function calls from the builtin import down to loading the module body, with the deepest at the top")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Lib/importlib/_bootstrap.py:899-932@v3.15.0rc1`.

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

Every cell in this lesson runs anywhere Python runs, including in a browser tab. Nothing here needs threads, a second interpreter or a compiler. It does need to write a few small files to a temporary directory, which every runtime this book targets can do.

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
## What the statement compiles to

Start at the front. `import` is a statement, so the compiler turns it into bytecode, and there are only two opcodes involved. Compile the four spellings and look at what comes out.

{lesson.claim("An import statement compiles to one IMPORT_NAME for the module being imported plus zero or more IMPORT_FROM, and import a.b binds the name a rather than a.b")}
""")


lesson.code("""
import dis

WORTH = {"IMPORT_NAME", "IMPORT_FROM", "STORE_NAME", "LOAD_CONST"}

for line in (
    "import os.path",
    "import os.path as p",
    "from os import sep, getcwd",
    "from . import sibling",
):
    print(line)
    for step in dis.get_instructions(compile(line, "<demo>", "exec")):
        if step.opname == "LOAD_SMALL_INT":
            print(f"    {'level':12} {step.arg}")
        elif step.opname in WORTH and step.argrepr != "None":
            print(f"    {step.opname:12} {step.argrepr or '(the empty string)'}")
""")


lesson.md(f"""
{figure("what-the-statement-compiles-to", "a table of five import statements, the name each one asks for and the name each one leaves behind")}

Four things are worth pulling out of that.

The level is the number of leading dots. Zero means an absolute import. `from . import sibling` is level 1, and notice that its `IMPORT_NAME` argument is the empty string, because the name being imported is entirely made of dots.

`import os.path` asks for `os.path` and then stores `os`. That is not a typo in the compiler. When you import a submodule you get the top of the package bound, and you reach the rest through attributes. If you want `path` on its own you have to say `import os.path as p`, and look at what that compiles to: the same `IMPORT_NAME`, then an `IMPORT_FROM` to dig out the attribute.

`from os import sep, getcwd` is one import and two attribute lookups, not two imports.

The opcode itself does almost nothing {cite("Python/bytecodes.c:3497-3517@v3.15.0rc1#IMPORT_NAME")}. It hands off to a helper which looks up the name `__import__` in the builtins of the current frame and calls it {cite("Python/ceval.c:2993-3010@v3.15.0rc1#_PyEval_ImportNameWithImport")}. That lookup happens on every import, which is exactly why replacing `builtins.__import__` works at all.

## One call, and everything under it

So `import shop.till.drawer` becomes one call to `__import__("shop.till.drawer", globals(), locals(), (), 0)`. One call. But three modules end up loaded, and they have to be loaded in the right order, because `shop.till` cannot be found without first asking `shop` where its submodules live.

All of that happens underneath `__import__`, which is why hooking `__import__` shows you one line and not three. To see the three you have to get in at the level of the search, and there is a supported place to do that: `sys.meta_path`. Anything on that list gets asked for a {term("module spec")}, in order, until one of them answers.

Put a class on the front of it that answers nothing and writes down every question, and the whole search becomes visible.

{lesson.claim("Importing a dotted name searches for each part in turn from the outside in, and each part after the first is searched for in the parent package's __path__ rather than in sys.path")}
""")


lesson.code("""
import tempfile
from pathlib import Path


def workshop(files):
    \"\"\"Write those files into a throwaway directory and put it at the front of sys.path.\"\"\"
    folder = Path(tempfile.mkdtemp())
    for name, body in files.items():
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
    sys.path.insert(0, str(folder))
    return folder


ASKED = []


class Watcher:
    \"\"\"A finder that never answers. It is only here to write down what it was asked.\"\"\"

    @classmethod
    def find_spec(cls, name, path, target=None):
        ASKED.append((name, path))
        return None


workshop(
    {
        "shop/__init__.py": "name = 'shop'\\n",
        "shop/till/__init__.py": "name = 'till'\\n",
        "shop/till/drawer.py": "coins = 12\\n",
    }
)

sys.meta_path.insert(0, Watcher)
try:
    exec("import shop.till.drawer", {})
finally:
    sys.meta_path.remove(Watcher)

for name, where in ASKED:
    looked = "sys.path" if where is None else f"the __path__ of {name.rpartition('.')[0]}"
    print(f"  find_spec({name!r}) looked in {looked}")

print()
print("  one call to __import__ loaded:", [n for n in sys.modules if n.startswith("shop")])
print("  and shop.till is now an attribute of shop:", hasattr(sys.modules["shop"], "till"))
""")


lesson.md(f"""
Three questions from one statement, outermost first. The first one gets `None` for the path, meaning search `sys.path`. The other two get the parent package's `__path__`, which is a list of directories the parent said its submodules live in. That is what makes something a package rather than a module: a spec with `submodule_search_locations` set {cite("Lib/importlib/_bootstrap.py:641-654@v3.15.0rc1#submodule_search_locations")}.

The last line of the cell is the other half of it. Loading `shop.till` also sets `till` as an attribute on `shop`, which is why `import shop.till.drawer` followed by `shop.till.drawer.coins` works even though the only name bound in your file was `shop` {cite("Lib/importlib/_bootstrap.py:1263-1302@v3.15.0rc1#_find_and_load_unlocked")}.

The Python side of all this starts at `__import__`, which is a thin wrapper that splits the name up and hands off {cite("Lib/importlib/_bootstrap.py:1457-1491@v3.15.0rc1#__import__")}. There is a C copy of the same logic in `Python/import.c`, with a comment saying so in as many words, and it is the one that actually runs {cite("Python/import.c:4190-4227@v3.15.0rc1#PyImport_ImportModuleLevelObject")}. The Python version stays because it has to work during startup before the C one can be used, and because it is the readable spelling of the rules.

## Who answers

A fresh interpreter starts with three finders on `sys.meta_path`, and each one covers a different kind of module. Ask all three for the same name and you can see which is which.

{lesson.claim("A module name can be answered by more than one finder, and the earlier finder wins, which is why import os never reads os.py even though os.py is right there on sys.path")}
""")


lesson.code("""
from importlib.machinery import BuiltinImporter, FrozenImporter, PathFinder

THREE = (BuiltinImporter, FrozenImporter, PathFinder)
print(f"  {'name':8} {'BuiltinImporter':16} {'FrozenImporter':16} PathFinder")
for name in ("time", "os", "json"):
    answers = []
    for finder in THREE:
        found = finder.find_spec(name, None)
        if found is None:
            answers.append("no answer")
        elif found.origin in ("built-in", "frozen"):
            answers.append(found.origin)
        else:
            answers.append(Path(found.origin).name)
    print(f"  {name:8} {answers[0]:16} {answers[1]:16} {answers[2]}")

print()
for name in ("time", "os", "json"):
    spec = __import__(name).__spec__
    loader = spec.loader
    kind = getattr(loader, "__name__", None) or type(loader).__name__ + " instance"
    package = "a package" if spec.submodule_search_locations is not None else "a module"
    print(f"  {name:8} loaded by {kind:26} {package}")
""")


lesson.md(f"""
{figure("three-finders", "a table of the three finders on sys.meta.path, what each one answers for, and the origin it reports")}

`os` is the interesting row. It exists as a file, `PathFinder` will happily find that file, and none of that matters, because `FrozenImporter` is asked first and says yes. `os` is compiled at build time and baked into the binary as bytecode, so `import os` never opens `os.py` at all. R04 is about what that buys and what it costs.

`time` is a {term("meta path finder")} question with an even shorter answer: it is C compiled into the executable, so there is no file anywhere {cite("Lib/importlib/_bootstrap.py:950-980@v3.15.0rc1#BuiltinImporter")}.

The object all three of them hand back is a `ModuleSpec` {cite("Lib/importlib/_bootstrap.py:605-640@v3.15.0rc1#ModuleSpec")}. It has four parts worth knowing: the full name, the loader that will run the body, an `origin` string saying where it came from, and `submodule_search_locations`, which is `None` for a plain module and a list of directories for a package. Every module you can reach has one, on `__spec__`, so you can ask anything in a running program which finder claimed it.

The search loop itself is fourteen lines and worth reading once {cite("Lib/importlib/_bootstrap.py:1198-1223@v3.15.0rc1#_find_spec")}. Note that it copies `sys.meta_path` before iterating, so a finder that modifies the list while being asked does not corrupt the walk.

## The module is in sys.modules before its body has run

This is the part that explains more real bugs than anything else in the lesson.

Loading a module happens in a fixed order. A blank module object is created from the spec {cite("Lib/importlib/_bootstrap.py:837-870@v3.15.0rc1#module_from_spec")}. It goes into `sys.modules` under its name. Then, and only then, the loader runs the body {cite("Lib/importlib/_bootstrap.py:899-932@v3.15.0rc1#_load_unlocked")}.

The order is not an accident and it is not fixable. It is what makes circular imports work at all: if the module were only published once its body finished, then two modules that import each other would loop forever. Publishing early means the second one finds a real module object, just an incomplete one.

{lesson.claim("A module is in sys.modules from before its body starts running, so a module it imports can read back the names defined so far and not the ones defined later, and if the body raises the entry is taken back out again")}
""")


lesson.code("""
workshop(
    {
        "pair/__init__.py": "",
        "pair/first.py": (
            "top = 'defined before the import'\\n"
            "import pair.second\\n"
            "bottom = 'defined after the import'\\n"
        ),
        "pair/second.py": (
            "import sys\\n"
            "half = sys.modules['pair.first']\\n"
            "print('  second.py is running, and pair.first is already in sys.modules')\\n"
            "print('    it can see top:      ', getattr(half, 'top', 'not there yet'))\\n"
            "print('    it cannot see bottom:', getattr(half, 'bottom', 'not there yet'))\\n"
        ),
        "explodes.py": "raise ValueError('this body did not finish')\\n",
    }
)

import pair.first  # noqa: E402

print("  and once both bodies finish, bottom is there:", pair.first.bottom)
print()

try:
    import explodes  # noqa: F401
except ValueError as problem:
    print("  importing explodes raised:", problem)
print("  is explodes left behind in sys.modules?", "explodes" in sys.modules)
""")


lesson.md(f"""
{figure("when-the-module-becomes-visible", "a flow showing first.py starting, being published to sys.modules, second.py reading half of it, and first.py finishing")}

So the rule for circular imports is not that they fail. It is that whichever module is second gets whatever the first one had defined by the line that triggered the import. Move the `import` to the bottom of the file and more is available. Move it to the top and less is. That is the whole of it, and it is why the usual advice about importing inside the function that needs it works.

The failure case is in the same handful of lines. If the body raises, the entry is deleted from `sys.modules` before the exception is re allowed to propagate, so a failed import does not leave a broken half module lying around for the next attempt to find.

## Writing a finder of your own

Everything so far has been reading. The protocol is public, so you can also write to it. A finder is any object with a `find_spec` method, and a loader is any object with `exec_module`. There is nothing else to implement, and one class can be both.

{lesson.claim("A class with find_spec and exec_module methods, put on the front of sys.meta_path, is enough to make a normal import statement produce a module built from a string with no file on disk anywhere")}
""")


lesson.code("""
from importlib.machinery import ModuleSpec

SOURCE = \"\"\"
greeting = "built from a string, never touched a disk"


def twice(n):
    return n * 2
\"\"\"


class FromAString:
    \"\"\"A finder and a loader in one class, serving exactly one module out of memory.\"\"\"

    serves = "invented"

    @classmethod
    def find_spec(cls, name, path, target=None):
        if name != cls.serves:
            return None
        return ModuleSpec(name, cls, origin="a string in this notebook")

    @classmethod
    def create_module(cls, spec):
        return None

    @classmethod
    def exec_module(cls, module):
        exec(SOURCE, module.__dict__)


sys.meta_path.insert(0, FromAString)

import invented  # noqa: E402

print("  invented.greeting:", invented.greeting)
print("  invented.twice(21):", invented.twice(21))
print("  its origin:        ", invented.__spec__.origin)
print("  its loader:        ", invented.__spec__.loader.__name__)
print("  does it have a __file__?", hasattr(invented, "__file__"))
""")


lesson.md(f"""
That is the mechanism behind every import hook you have ever used. Loading modules out of a zip file, out of a network, out of an encrypted blob, or rewriting the source on the way past to add coverage counters or type checks, are all the same fourteen lines with a different `exec_module`.

Returning `None` from `create_module` is how you say you have no opinion about what the module object should be, and the machinery makes a plain one for you. Returning something else is how a C extension gets to hand back a module it built itself.

## Three caches, and importing touches all of them

An import that has to do everything above is expensive. Almost none of them do, because there are three caches in the way, and all three are ordinary Python objects you can look at.

The first is `sys.modules`, and it is checked before any lock is taken {cite("Lib/importlib/_bootstrap.py:1333-1371@v3.15.0rc1#_find_and_load")}. The C version does the same thing in a few lines {cite("Python/import.c:258-271@v3.15.0rc1#import_get_module")}. That is the whole of a repeat import: one dict lookup.

The second is `sys.path_importer_cache`, which maps each entry of `sys.path` to the {term("path entry finder")} that owns it {cite("Lib/importlib/_bootstrap_external.py:1211-1231@v3.15.0rc1#_path_importer_cache")}. On a miss, `PathFinder` runs the entry past every hook in `sys.path_hooks` until one accepts it {cite("Lib/importlib/_bootstrap_external.py:1176-1199@v3.15.0rc1#PathFinder")}. If nothing accepts it, `None` is stored, so a directory that does not exist is stat'd once for the life of the process rather than once per import.

The third lives inside each `FileFinder`. Rather than trying six filename suffixes against the filesystem for every name it is asked about, it lists the directory once and answers out of a set {cite("Lib/importlib/_bootstrap_external.py:1403-1432@v3.15.0rc1#_fill_cache")}. It refreshes when the directory's modification time changes.

{lesson.claim("Each sys.path entry gets one finder object, kept in sys.path_importer_cache, and a directory that is not there is remembered as None, while each FileFinder holds a set of the directory listing that it refills when the directory's modification time changes")}
""")


lesson.code(
    """
folder = workshop({"one.py": "value = 1\\n", "two.py": "value = 2\\n"})
nowhere = str(folder / "no-such-directory")
sys.path.insert(0, nowhere)

before = len(sys.path_importer_cache)
import one  # noqa: F401, E402
import two  # noqa: F401, E402

print(f"  finders cached before these imports: {before}, after: {len(sys.path_importer_cache)}")

finder = sys.path_importer_cache[str(folder)]
print(f"  the finder for that directory:       {type(finder).__name__}")
print(f"  the same object served both imports: {finder is sys.path_importer_cache[str(folder)]}")
print(f"  a directory that is not there:       {sys.path_importer_cache[nowhere]}")
print()
print(f"  what it listed:  {sorted(finder._path_cache)}")

remembered = finder._path_mtime
(folder / "three.py").write_text("value = 3\\n")
import three  # noqa: F401, E402

print(f"  after adding a file the mtime moved: {remembered != finder._path_mtime}")
print(f"  and it listed again: {sorted(finder._path_cache)}")
""",
    varies=(
        "the number of finders already cached depends on how many directories your runtime has "
        "imported from, and whether a __pycache__ directory shows up in the listing depends on "
        "whether your runtime is writing bytecode files"
    ),
)


lesson.md(f"""
{figure("three-caches", "a table of the three caches an import passes through, what each is keyed by, what it saves and what clears it")}

Two of those three are yours to break. Writing a file into a directory that is already on `sys.path` usually works, because the modification time moves and the listing refills, and that is what the cell just showed. Creating the directory itself after the fact usually does not, because `None` is already sitting in `sys.path_importer_cache`. `importlib.invalidate_caches()` is the supported way to clear both, and it is exactly what a program that generates code at runtime has to call.

{lesson.claim("A directory created after it was already looked up stays invisible to imports until importlib.invalidate_caches is called, because the failed lookup was cached as None")}
""")


lesson.code("""
import importlib

later = folder / "made-later"
sys.path.insert(0, str(later))
try:
    import arrives_late
except ImportError:
    print("  not found yet, which is expected, the directory does not exist")

later.mkdir()
(later / "arrives_late.py").write_text("value = 'here now'\\n")
try:
    import arrives_late
except ImportError:
    print("  still not found, because None is cached for that path entry")

importlib.invalidate_caches()
import arrives_late  # noqa: E402

print("  after invalidate_caches:", arrives_late.value)
""")


lesson.md(f"""
## What it costs

Two numbers matter and they are three orders of magnitude apart. The first import of a module reads a file, unmarshals or compiles it, and runs the body. Every import after that is a dict lookup.

{lesson.claim("The first import of a module from a source file costs hundreds of times what asking for the same module again costs, and most of that gap survives even once a .pyc file exists")}
""")


lesson.code(
    """
import time

COUNT = 150
folder = workshop({f"tiny{n}.py": "value = 0\\n" for n in range(COUNT)})

import tiny0  # noqa: F401, E402


def per_call(work, rounds):
    \"\"\"Seconds per go, taking the best of three so a busy machine matters a little less.\"\"\"
    best = None
    for _ in range(3):
        started = time.perf_counter()
        work()
        taken = (time.perf_counter() - started) / rounds
        best = taken if best is None else min(best, taken)
    return best


started = time.perf_counter()
for n in range(1, COUNT):
    __import__(f"tiny{n}")
fresh = (time.perf_counter() - started) / (COUNT - 1)


def reimport_them_all():
    for n in range(1, COUNT):
        del sys.modules[f"tiny{n}"]
        __import__(f"tiny{n}")


compiled = per_call(reimport_them_all, COUNT - 1)
again = per_call(lambda: [__import__("tiny0") for _ in range(20_000)], 20_000)

print(f"  first time, source file, no .pyc yet: {fresh * 1e6:8.1f} microseconds")
print(f"  from a file, with a .pyc already there:{compiled * 1e6:8.1f} microseconds")
print(f"  asking again for one already loaded:  {again * 1e9:8.1f} nanoseconds")
print(f"  the second of those is {compiled / again:.0f} times the third")
""",
    varies=(
        "every number here is a timing on your machine, so the absolute values depend on your "
        "processor and your filesystem, and a notebook running on a shared or virtualised disk "
        "will show a much larger gap between the first two rows than a local one will"
    ),
)


lesson.md(f"""
The gap is the point rather than the numbers. Reading and running a module body is work measured in hundreds of microseconds. Finding it already loaded is work measured in hundreds of nanoseconds. That is why `import` statements inside a hot function are not the disaster they look like, and it is also why startup time is dominated by how many modules you import rather than by how big they are.

## What the import lock actually locks

There is one more thing to settle, because almost everybody has it wrong.

Importing takes a lock. It is easy to read that as one import at a time for the whole process, and it has not meant that since Python 3.3. There is a {term("module lock")} per module name {cite("Lib/importlib/_bootstrap.py:226-240@v3.15.0rc1#_ModuleLock")}. Two threads importing two different modules do not wait for each other. Two threads importing the same module do, and only one of them runs the body.

The way to prove it is to import modules whose bodies burn processor time and then measure how many cores the process actually kept busy. That number is processor time divided by wall clock, and it does not care how fast your machine is. One means the work went through a queue. Four means it really did overlap.

{recording(WITH_LOCK)}

{recording(WITHOUT_LOCK)}

{figure("cores-kept-busy", "bars comparing cores kept busy for four different modules and for one module, on a build with the GIL and a build without")}

Read the four numbers in pairs. Four different modules on four threads keep 1.02 cores busy on the build with the GIL and 3.63 on the build without, so the import lock was never what was holding them up. The {term("GIL")} was. The same module asked for by four threads keeps almost exactly one core busy on both builds, and the counter at the end of the program says the body ran once, so that is the per module lock doing precisely what it says on the tin.

The last line of each recording is the same measurement as the notebook cell above: a hit in `sys.modules` costs 282 nanoseconds on the build with the lock and 507 on the {term("free threaded build")}, which is the same tax on uncontended locking that C06 and C07 measured on everything else.

{lesson.claim("What stops two threads importing two different modules at the same time is the GIL and not the import lock, which a build configured with --disable-gil shows by keeping three and a half cores busy on the same program", unobservable="it compares two builds of the same source in two containers, and one notebook cannot be both of them")}
""")


lesson.md("""
## Try it yourself

Four things, in rough order of how much you will learn.

Leave the `Watcher` finder installed instead of removing it, then import something from the standard library that you have not imported yet, such as `statistics` or `zoneinfo`. Count the questions. Some innocent looking imports pull in a dozen modules and this is the cheapest way to find out which.

Change `FromAString.exec_module` to compile the source with a transformation applied first. Replacing every `+` with `*` is a silly example that takes one line and makes the point: you now own what the module means, and the import statement in the calling file looks completely ordinary.

Run `python -X importtime -c "import json"` and read the tree. Every line is one of the module bodies this lesson has been talking about, and the indentation is the parent chain the `Watcher` cell printed.

Take the circular import in `pair` and move `import pair.second` to the bottom of `first.py` instead of the middle. Watch `bottom` become visible. Then make `second.py` do `from pair.first import bottom` rather than reading it off the module and see the error change from a missing attribute to an ImportError with a much better message.

## What you now know

`import` is a call. It compiles to `IMPORT_NAME`, which looks `__import__` up in builtins every single time, which is why replacing that name works.

`import a.b` binds `a`. The submodule is reached through an attribute that the import machinery sets on the parent.

A dotted import is one search per part, outermost first, and every part after the first is looked for in the parent package's `__path__` rather than on `sys.path`.

`sys.meta_path` holds finders, they are asked in order, and the first one to return a spec wins. The three you start with cover modules compiled into the binary, modules frozen in as bytecode, and modules on `sys.path`. `import os` stops at the second of those.

A spec is name, loader, origin and `submodule_search_locations`. The last of those is the only thing that makes a module a package.

The module object goes into `sys.modules` before its body runs. That is what makes circular imports possible and it is what decides exactly how much of a half loaded module another module can see. If the body raises, the entry is removed again.

Three caches sit in the way: `sys.modules` keyed by name, `sys.path_importer_cache` keyed by path entry, and a directory listing inside each `FileFinder`. Generated code needs `importlib.invalidate_caches()` because of the second one.

The import lock is per module name, not per process. On a build with the GIL that distinction is invisible, because the GIL serialises the bodies anyway. Take the GIL away and four threads import four modules at close to four times the speed.

## What is next

R04 goes after the thing this lesson kept walking past. `import os` never opened `os.py`, because `FrozenImporter` answered first with bytecode that was compiled when CPython itself was built and written into the binary as a C array.

That is how the interpreter bootstraps a Python level import system using the import system, which sounds impossible until you see where the loop is cut. It is also most of the reason a modern CPython starts as fast as it does, and it is the mechanism a single file executable depends on.
""")


raise SystemExit(lesson.save())
