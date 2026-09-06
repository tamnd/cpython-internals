#!/usr/bin/env python
"""R05. Lazy imports.

The fifth runtime lesson, and the newest thing in this part of CPython. PEP 810 landed in 3.15 and
adds one word to the import statement. `lazy import json` binds the name straight away and does the
finding, the reading and the running of the module body later, the first time something reads that
name back.

The awkward part of writing this lesson is that CI runs the notebooks on 3.14 as well, and 3.14 has
no such keyword, so a literal `lazy import` line anywhere would be a syntax error at load time. The
way out is in `Python/ceval.c`: the interpreter decides a frame is at module scope by comparing
`f_globals` with `f_locals`, and an `exec` of a compiled string with one namespace dict satisfies
that. So every lazy line in this lesson is compiled at runtime behind a version check, and the
cells run everywhere.

The three Tier 1 recordings measure the two things worth measuring: what deferring saves on a real
startup, and whether two threads waking two different deferred imports can do it at the same time.
The second answer is no, and the free threaded recording is what makes that visible.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording

lesson = Lesson("r05-lazy-imports", "r05")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("r05-lazy-imports").figure

SAVES = "r05-what-deferring-an-import-is-worth"
PARALLEL = "r05-how-much-of-a-wake-up-is-parallel"
UNLOCKED = "r05-how-much-of-a-wake-up-is-parallel-without-the-lock"


lesson.md(f"""
# R05. Lazy imports

{badge}

R03 and R04 both assumed the same thing: when an import statement finishes, the module has been found, read and run. 3.15 adds one word that makes that untrue.

`lazy import json` binds the name and stops. The finding, the reading and the running happen later, the first time something reads the name back, and if nothing ever does then they never happen at all.

{figure("two-spellings", "a comparison of the four steps a plain import takes against the two steps a lazy import takes")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/import.c:3883-3895@v3.15.0rc1`.

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

Lazy imports are new in 3.15, so on 3.14, or in a browser tab, the cells that need the keyword say so and skip themselves. Everything else runs anywhere. Nothing here starts a second process or a second thread, so the threading question at the end is answered by recordings taken in containers instead.

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
## What an unused import costs

Start with the problem rather than the feature. An import line at the top of a file is a promise that the module will be needed. Quite often it is not, and it gets paid for anyway.

{lesson.claim("Importing xml.etree.ElementTree brings in most of a package and a C extension underneath it, and a program that never parses any XML carries every one of those modules for its whole run")}
""")


lesson.code(
    """
import importlib
import time

FAMILY = ("xml", "_elementtree", "pyexpat")

before = set(sys.modules)
started = time.perf_counter()
importlib.import_module("xml.etree.ElementTree")
taken = (time.perf_counter() - started) * 1000
arrived = set(sys.modules) - before
family = sorted(name for name in sys.modules if name.startswith(FAMILY))

print(f"  what that one import line cost here: {taken:.1f} ms")
print(f"  modules it needs, all told: {len(family)}")
print("  which are:", ", ".join(family))
print(f"  how many of those this cell had to load: {len(arrived)}")
print()
print(f"  modules this process is now carrying: {len(sys.modules)}")
""",
    varies=(
        "the milliseconds are a measurement on your machine, the fourth line is zero if the runtime "
        "had already imported all of this for its own reasons, which a notebook kernel usually has, "
        "and 3.14 lists eight of these modules rather than nine because it has no xml.utils"
    ),
)


lesson.md(f"""
That is one line in one file. A tool with twenty subcommands imports the machinery for all twenty every time you run one. The usual fix is to move the import into the function that needs it, which works and costs you the list of what a file depends on.

## What you had to do before

3.15 is not the first attempt. `importlib.util.LazyLoader` has been there since 3.5. It wraps a loader, hands back a module with a stand in class, and runs the real body the first time somebody touches it. That works, but it is five lines per module and more fragile than it looks.

{lesson.claim("A module made by LazyLoader replaces its own __getattribute__, so any attribute access at all wakes it up, including reading __name__ or __dict__ to see whether it is awake yet")}
""")


lesson.code(
    """
from importlib.util import LazyLoader, find_spec, module_from_spec


def the_old_way(name):
    \"\"\"Defer a module the way you had to before 3.15, with a hand made spec and five lines.\"\"\"
    spec = find_spec(name)
    spec.loader = LazyLoader(spec.loader)
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def names_in(module):
    \"\"\"Count what a module holds without going through the machinery that would wake it up.\"\"\"
    return len(object.__getattribute__(module, "__dict__"))


try:
    wave = the_old_way("wave")
    print("  what a lazy loader hands you:", type(wave).__name__)
    print("  in sys.modules already:      ", "wave" in sys.modules)
    print("  names it holds so far:       ", names_in(wave))
    print()
    print("  read one attribute of it, and not an interesting one:", wave.__name__)
    print("  the class it has now:        ", type(wave).__name__)
    print("  names it holds now:          ", names_in(wave))
except Exception as why:
    print("  this runtime cannot build a lazy loader here:", type(why).__name__, why)
""",
    varies=(
        "the two counts are the number of names the wave module holds before and after it runs, "
        "which moves whenever the module itself changes between releases, and a runtime that "
        "cannot find a spec for wave reports that instead"
    ),
)


lesson.md(f"""
Reading `wave.__name__` was enough. `_LazyModule` overrides `__getattribute__` rather than `__getattr__` {cite("Lib/importlib/util.py:167-205@v3.15.0rc1#_LazyModule")}, so there is no harmless look, which is why the cell reaches for `object.__getattribute__` to count names without disturbing anything. The other cost is `sys.modules[name] = module` up front: from then on every other importer gets your half built object. The new mechanism has neither problem, because it is not built out of modules at all.

## One word, and two bits in the opcode

`lazy` is a {term("soft keyword")}, only a keyword directly in front of `import` or `from`, so every variable called `lazy` still works. The grammar arranges that with one lookahead {cite("Grammar/python.gram:121-124@v3.15.0rc1#simple_stmt")} and an optional capture in the rule {cite("Grammar/python.gram:227-236@v3.15.0rc1#import_name")}.

What the compiler does is smaller than you would guess. There is no new opcode. `IMPORT_NAME` already took a name index as its argument, so 3.15 shifts that up by two bits and uses the two underneath to say which kind of import this is {cite("Python/codegen.c:2902-2933@v3.15.0rc1#codegen_import")}.

{lesson.claim("A lazy import compiles to the same IMPORT_NAME opcode as a plain one, with the low two bits of the argument set to 1 for lazy and 2 for forced eager, and dis prints the difference")}
""")


lesson.code(
    """
import dis
import types

IN_A_FUNCTION = \"\"\"
def f():
    import json
\"\"\"

IN_A_TRY = \"\"\"
try:
    import json
except ImportError:
    pass
\"\"\"

FOUR = [
    ("plain, at module scope", "import json"),
    ("with the keyword", "lazy import json"),
    ("plain, inside a function", IN_A_FUNCTION),
    ("plain, inside a try block", IN_A_TRY),
]


def import_steps(code):
    \"\"\"Every IMPORT_NAME in this code object and in the code objects nested inside it.\"\"\"
    found = [step for step in dis.get_instructions(code) if step.opname == "IMPORT_NAME"]
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            found.extend(import_steps(const))
    return found


if not hasattr(sys, "lazy_modules"):
    print("  lazy is a word 3.15 added, so the second of these four does not compile here")
else:
    for label, source in FOUR:
        for step in import_steps(compile(source, "<demo>", "exec")):
            bits = step.arg & 3
            print(f"  {label:26} oparg {step.arg:3}  bits {bits:02b}  dis says {step.argrepr!r}")
""",
    differs=(
        "3.14 has no lazy keyword, so the whole cell prints one line saying so and none of the four "
        "spellings get compiled there at all"
    ),
)


lesson.md(f"""
{figure("the-two-bits", "a table of the three values the low two bits of the IMPORT_NAME argument can take and what dis prints for each")}

Bits `00` is the ordinary import and `01` is the keyword. Bits `10` is the compiler saying this one must happen now whatever anything else thinks, and it picks that for any import inside a function, a class body or a `try` block. The eval loop splits the argument the same way {cite("Python/bytecodes.c:3497-3517@v3.15.0rc1#IMPORT_NAME")}.

## A workshop of our own

Everything below needs modules nothing else here has imported, because a name already in `sys.modules` never gets deferred, so the next cell writes throwaway modules into a temporary directory on `sys.path`.

It also gets around the version problem. `lazy import` is a syntax error on 3.14, so this notebook cannot contain one literally. The sources are compiled at run time and run with a single namespace dict, which is what the interpreter checks for when it asks whether a frame is at module scope {cite("Python/ceval.c:3059-3064@v3.15.0rc1#is_lazy_import_module_level")}.
""")


lesson.code(
    """
import pathlib
import tempfile

LAZY = hasattr(sys, "lazy_modules")
WORKSHOP = pathlib.Path(tempfile.mkdtemp())
sys.path.insert(0, str(WORKSHOP))


def make_module(name, body):
    \"\"\"Write a module of our own, so nothing else in this process has already imported it.\"\"\"
    (WORKSHOP / f"{name}.py").write_text(body)


def module_level(source):
    \"\"\"Run source the way a module body runs, and hand back the namespace it filled in.\"\"\"
    namespace = {"__name__": "demo"}
    exec(compile(source, "<demo>", "exec"), namespace)
    return namespace


print("  a scratch directory to write modules into:", WORKSHOP.is_dir())
print("  this interpreter has lazy imports:        ", LAZY)
""",
    differs="the second line reads False on 3.14, and every cell below it takes its short branch",
)


lesson.md(f"""
## What the statement leaves behind

Now the question the whole feature turns on. If the module body has not run, what is sitting under the name?

Not a module, and not a half built one either. It is a small object of its own kind, five fields long: the builtins it was declared in, the name, the attribute if this was a `from` import, and the code object and instruction offset of the line that declared it {cite("Include/internal/pycore_lazyimportobject.h:17-25@v3.15.0rc1#PyLazyImportObject")}. The last two matter later.

{lesson.claim("A lazy import binds an object of type lazy_import, leaves sys.modules untouched, adds the name to sys.lazy_modules, and offers exactly one public method")}
""")


lesson.code(
    """
PAPERS = \"\"\"
print("      (the papers module body is running now)")
STAMP = "signed"
\"\"\"

make_module("papers", PAPERS)

if LAZY:
    space = module_level("lazy import papers")
    print("  the statement has finished, and nothing printed above this line")
    print("  the name it bound is a:    ", type(space["papers"]).__name__)
    print("  its repr:                  ", repr(space["papers"]))
    print("  papers in sys.modules:     ", "papers" in sys.modules)
    print("  papers in sys.lazy_modules:", "papers" in sys.lazy_modules)
    offers = [one for one in dir(space["papers"]) if not one.startswith("_")]
    print("  everything the placeholder offers:", offers)
else:
    print("  there is nothing to bind here, because the keyword is a 3.15 thing")
""",
    differs="on 3.14 this prints the one line from its else branch and binds nothing",
)


lesson.md(f"""
That is the whole object. It is not in `sys.modules`, so nobody else can trip over it, and unlike `_LazyModule` you can look at it as much as you like without setting it off. `sys.lazy_modules` is the other half of the bookkeeping, a set of every name still waiting. The one public method, `resolve`, forces the import and hands the module back without touching the namespace it came out of.

## What wakes it up

An {term("import placeholder")} is only useful if something turns it into a module at the right moment, and only two opcodes know about placeholders at all. Reading a bare name is one, and `LOAD_NAME` writes the resolved module back into globals so the next read is an ordinary lookup {cite("Python/bytecodes.c:2280-2298@v3.15.0rc1#LOAD_NAME")}. Reading an attribute of a module is the other {cite("Objects/moduleobject.c:1330-1360@v3.15.0rc1#_PyImport_LoadLazyImportTstate")}. Anything that goes around those two sees the placeholder.

{lesson.claim("Dict lookups, membership tests and reprs all leave the placeholder alone, while reading the name resolves it, and a placeholder copied into another variable resolves when that variable is read rather than when it was copied")}
""")


lesson.code(
    """
LEDGER = \"\"\"
print("      (the ledger module body is running now)")
TOTAL = 7
\"\"\"

USE_PAPERS = \"\"\"
lazy import papers
kept = papers.STAMP
\"\"\"

make_module("ledger", LEDGER)

if LAZY:
    print("  looking the name up in the namespace:", type(space["papers"]).__name__)
    print("  asking whether it is in there:       ", "papers" in space)
    print("  printing its repr:                   ", repr(space["papers"]))
    print("  after all three it is still a:       ", type(space["papers"]).__name__)
    print()
    print("  now read the name the way a module body would:")
    used = module_level(USE_PAPERS)
    print("  what came back:           ", used["kept"])
    print("  papers in sys.modules now:", "papers" in sys.modules)
    print()
    books = module_level("lazy import ledger")
    escaped = books["ledger"]
    print("  that assignment was a dict lookup, so ledger has run:", "ledger" in sys.modules)
    print("  now read the name we assigned to:", type(escaped).__name__)
    print("  ledger has run now:              ", "ledger" in sys.modules)
    print("  the entry it was copied out of:  ", type(books["ledger"]).__name__)
else:
    print("  no placeholder here to poke at")
""",
    differs="on 3.14 the else branch runs and neither of the two workshop modules is ever imported",
)


lesson.md(f"""
{figure("what-wakes-it", "a table of five things you can do with a lazy name and whether each of them wakes the placeholder up")}

The last two lines are worth staring at. `escaped` came out by a dict lookup, which did nothing, and reading `escaped` resolved it. But the entry it was copied out of is still a placeholder, because nothing knew where the copy came from.

One more thing happens under the covers, and it is the one part of this lesson you cannot see from Python. The specialising interpreter refuses to specialise a global or a module attribute whose value is a placeholder {cite("Python/specialize.c:1364-1374@v3.15.0rc1#SPEC_FAIL_ATTR_MODULE_LAZY_VALUE")}.

{lesson.claim("An unresolved placeholder blocks LOAD_GLOBAL_MODULE and LOAD_ATTR_MODULE from specialising", unobservable="the bail out is recorded in specialisation statistics that only a build configured with --enable-pystats collects, and this notebook is not one")}

## Where the rules live

You can only write `lazy import` at module scope, and not inside a `try` block. The refusal is not where you would look first. It comes from the {term("symbol table")}, not the code generator {cite("Python/symtable.c:1846-1876@v3.15.0rc1#check_lazy_import_context")}, because that pass already knows whether it is inside a function, a class or a `try`. Star imports are refused a few hundred lines further down {cite("Python/symtable.c:2185-2196@v3.15.0rc1#ImportFrom")}, the code generator keeps its own copy of the check as a backstop {cite("Python/codegen.c:2891-2900@v3.15.0rc1#codegen_validate_lazy_import")}, and writing the words the wrong way round gets its own grammar rule {cite("Grammar/python.gram:1446-1449@v3.15.0rc1#invalid_import_from")}.

{lesson.claim("Each of the four ways of misusing the keyword produces a different message naming the specific thing that is wrong, rather than one generic syntax error")}
""")


lesson.code(
    """
LAZY_IN_A_FUNCTION = \"\"\"
def f():
    lazy import json
\"\"\"

LAZY_IN_A_CLASS = \"\"\"
class C:
    lazy import json
\"\"\"

LAZY_IN_A_TRY = \"\"\"
try:
    lazy import json
except ImportError:
    pass
\"\"\"

ATTEMPTS = [
    ("inside a function", LAZY_IN_A_FUNCTION),
    ("inside a class body", LAZY_IN_A_CLASS),
    ("inside a try block", LAZY_IN_A_TRY),
    ("asking for everything", "lazy from json import *"),
    ("the words the wrong way round", "from json lazy import dumps"),
    ("at module scope, which is fine", "lazy import json"),
]

for label, source in ATTEMPTS:
    try:
        compile(source, "<demo>", "exec")
    except SyntaxError as complaint:
        print(f"  {label:31} {complaint.msg}")
    else:
        print(f"  {label:31} compiles")
""",
    differs=(
        "3.14 does not know the word at all, so all six lines there read invalid syntax, including "
        "the last one, which is the only one that is meant to work"
    ),
)


lesson.md(f"""
The `try` block rule is the one to remember. A deferred import can fail at any point later, so an `except ImportError` around the statement would be a promise the interpreter cannot keep. Functions and classes are refused because placeholders live in a globals dict and a function's locals are not one, so there would be nowhere to put it. The runtime checks that a second time {cite("Python/import.c:4538-4545@v3.15.0rc1#f_globals")}.

## Turning it on without the keyword

Rewriting every import in a codebase is not much of a migration path, so there are two other ways in. The first is a list: give a module a `__lazy_modules__` at the top, and plain imports of the names on it are deferred {cite("Python/ceval.c:3021-3057@v3.15.0rc1#check_lazy_import_compatibility")}. The second is a filter, a callable of your own that the runtime asks about every candidate {cite("Python/import.c:4547-4571@v3.15.0rc1#filter")}. It gets the importing module, the absolute name and the fromlist, and a false answer means an ordinary import.

Behind both is a mode, set with `-X lazy_imports=all` {cite("Python/initconfig.c:2456-2487@v3.15.0rc1#config_init_lazy_imports")} and readable at run time {cite("Python/sysmodule.c:2841-2855@v3.15.0rc1#set_lazy_imports")}. A stock interpreter starts in `normal`, where the keyword and the list work and nothing else changes.

{figure("who-decides", "three boxes in a row naming the three source files that each get a say in whether an import is deferred")}

{lesson.claim("A filter installed with sys.set_lazy_imports_filter is asked about every lazy import with three arguments, and returning false for one name makes that one import eagerly while the other stays deferred")}
""")


lesson.code(
    """
TWO_NAMES = \"\"\"
lazy import cutlery
lazy import napkins
\"\"\"

BY_LIST = \"\"\"
__lazy_modules__ = ["candles"]
import candles
import binascii
\"\"\"

make_module("cutlery", "SPOONS = 4")
make_module("napkins", "COUNT = 12")
make_module("candles", "LIT = True")

if LAZY:
    print("  the mode this interpreter started in:", sys.get_lazy_imports())
    asked = []

    def only_cutlery(importer, imported, fromlist):
        \"\"\"Keep the deferral for one name and hand the other one back to the ordinary loader.\"\"\"
        asked.append((importer, imported, fromlist))
        return imported == "cutlery"

    sys.set_lazy_imports_filter(only_cutlery)
    try:
        table = module_level(TWO_NAMES)
    finally:
        sys.set_lazy_imports_filter(None)

    for call in asked:
        print("  the filter was asked about:", call)
    print("  cutlery came out as:", type(table["cutlery"]).__name__)
    print("  napkins came out as:", type(table["napkins"]).__name__)
    print()
    older = module_level(BY_LIST)
    print("  with __lazy_modules__ and no keyword, candles is:", type(older["candles"]).__name__)
    print("  and binascii, which is not on that list, is:     ", type(older["binascii"]).__name__)
else:
    print("  no modes and no filter on this interpreter")
""",
    differs=(
        "3.14 has no sys.get_lazy_imports and no filter to install, so the else branch runs there "
        "and the three workshop modules are written out and left alone"
    ),
)


lesson.md(f"""
## When the module raises

Deferring the work moves the failure with it. If the module body raises, it raises wherever the name was read, which might be a long way from the import line.

CPython gives you both places. It builds a second exception, an `ImportError` naming the lazy import, reconstructs a traceback frame from the code object and offset the placeholder has carried since it was created, and hangs the whole thing on the real exception as its cause {cite("Python/import.c:4055-4086@v3.15.0rc1#PyException_SetCause")}.

{lesson.claim("A failure inside a deferred module arrives as the exception the module raised, with an ImportError attached as its __cause__ whose traceback points at the lazy import line rather than at the use site")}
""")


lesson.code(
    """
import traceback

BAD = \"\"\"
lazy import takings
kept = takings.TOTAL
\"\"\"

make_module("takings", "TOTAL = 1 / 0")


def where(error):
    \"\"\"The file and line of the last frame in an exception's traceback.\"\"\"
    last = traceback.extract_tb(error.__traceback__)[-1]
    return f"{pathlib.Path(last.filename).name} line {last.lineno}"


if LAZY:
    try:
        module_level(BAD)
    except ZeroDivisionError as went_wrong:
        cause = went_wrong.__cause__
        print("  what reached us:       ", type(went_wrong).__name__, went_wrong)
        print("  raised at:             ", where(went_wrong))
        print("  what it names as cause:", type(cause).__name__)
        print("                         ", cause)
        print("  and that points at:    ", where(cause))
else:
    print("  no two part traceback here, because there is nothing deferred to fail")
""",
    differs="on 3.14 the takings module is written out and never imported, so nothing fails",
)


lesson.md(f"""
Two files and two line numbers, which between them tell the whole story: the division happened in `takings.py`, and the reason anybody ran it then is the `lazy import` at the top of the other file.

The resolution path guards against one more thing. If waking a placeholder leads back to waking the same one you get an `ImportCycleError` rather than a hang, because the set of names being resolved is kept on the interpreter and checked on the way in {cite("Python/import.c:3897-3925@v3.15.0rc1#lazy_importing_modules")}.

## What the standard library already defers

This is not a feature waiting for users. 3.15 ships with it on in about thirty files, including `collections`, `typing`, `inspect`, `dataclasses`, `argparse` and `contextlib`. Four are in `site.py`, and they are why a stock interpreter has anything in `sys.lazy_modules` before you write a line {cite("Lib/site.py:46-54@v3.15.0rc1#lazy")}. `collections` defers two functions it needs for one method each {cite("Lib/collections/__init__.py:35-36@v3.15.0rc1#nlargest")}.

That has a knock on effect. Resolving one deferred import runs a module body, and that body can declare deferred imports of its own, so the set grows while you drain it.

{lesson.claim("Resolving one placeholder runs a module body that can declare placeholders of its own, so a name can appear in sys.lazy_modules as a result of resolving a different one")}
""")


lesson.code(
    """
OUTER = \"\"\"
lazy import inner
DEPTH = 1
\"\"\"

USE_OUTER = \"\"\"
lazy import outer
kept = outer.DEPTH
\"\"\"

make_module("inner", "DEPTH = 2")
make_module("outer", OUTER)

if LAZY:
    waiting = sorted(sys.lazy_modules)
    print("  names this process has waiting right now:", len(waiting))
    print("  four of them:", ", ".join(waiting[:4]))
    print()
    module_level("lazy import outer")
    print("  inner is waiting before we touch outer:", "inner" in sys.lazy_modules)
    used = module_level(USE_OUTER)
    print("  outer has now run and gave us:         ", used["kept"])
    print("  and inner is waiting now:              ", "inner" in sys.lazy_modules)
    print("  while inner itself is in sys.modules:  ", "inner" in sys.modules)
else:
    print("  sys.lazy_modules does not exist on this interpreter")
""",
    varies=(
        "the count of waiting names and the four shown depend entirely on what the runtime has "
        "imported for its own reasons before the cell runs, so a notebook kernel reports a longer "
        "list than a bare interpreter does, and the four lines underneath are the same everywhere"
    ),
)


lesson.md(f"""
The last two lines are the point. `inner` is waiting, which means `outer` ran, and `inner` is not in `sys.modules`, which means it did not. Deferral survives one level down.

## What it saves

The same measurement twice, once in this process and once as a real startup in a container.

{lesson.claim("A file with twelve imports at the top that uses one runs several times faster with them deferred, and eleven of the twelve module bodies never run")}
""")


lesson.code(
    r"""
BODY = "total = 0\nfor i in range(200000):\n    total += i\nTOTAL = total\n"

if LAZY:
    heavy = [f"weight_{index}" for index in range(12)]
    light = [f"feather_{index}" for index in range(12)]
    for name in heavy + light:
        make_module(name, BODY)

    plain = "\n".join(f"import {name}" for name in heavy) + "\nkept = weight_3.TOTAL\n"
    deferred = "\n".join(f"lazy import {name}" for name in light) + "\nkept = feather_3.TOTAL\n"

    started = time.perf_counter()
    first = module_level(plain)
    plain_ms = (time.perf_counter() - started) * 1000

    started = time.perf_counter()
    second = module_level(deferred)
    lazy_ms = (time.perf_counter() - started) * 1000

    print(f"  twelve imports and one use, as written: {plain_ms:8.2f} ms")
    print(f"  the same twelve, deferred:              {lazy_ms:8.2f} ms")
    print("  both files ended up with the same answer:", first["kept"] == second["kept"])
    print("  modules of the first set that ran:      ", sum(n in sys.modules for n in heavy))
    print("  modules of the second set that ran:     ", sum(n in sys.modules for n in light))
else:
    print("  nothing to defer here, so there is nothing to time")
""",
    varies=(
        "the two timings are measurements on your machine and the ratio between them depends on "
        "how slow your filesystem is, since most of what the first number pays for is opening and "
        "compiling twelve files that nothing needed"
    ),
)


lesson.md(f"""
Twelve is small for a real program. Here is the same shape as a whole process startup.

{recording(SAVES)}

{figure("what-deferring-saves", "two bars comparing the milliseconds a startup takes with twelve plain imports against the same file with them deferred")}

Three quarters of the run went with the eleven imports nothing needed. The counts underneath are the honest part: fifty four modules in `sys.modules` rather than a hundred and eighty nine, and fifteen code objects read off disk rather than a hundred and ten.

## The lock nobody mentions

This part is not in the release notes, and it only shows up on a free threaded build.

An ordinary import takes a {term("module lock")}, one per module name, so two threads importing two different modules do not wait for each other. Waking a placeholder does not use that lock. It takes the interpreter wide import lock and holds it for the whole resolution, module body included {cite("Python/import.c:3883-3895@v3.15.0rc1#_PyImport_LoadLazyImportTstate")}, a recursive mutex on the interpreter {cite("Python/import.c:150-158@v3.15.0rc1#_PyImport_AcquireLock")}. The comment says why: to serialise reification. Two threads waking two different placeholders take turns.

{figure("which-lock", "a comparison of the per name lock an ordinary import takes against the interpreter wide lock a lazy import takes")}

On a normal build none of this shows, because the global interpreter lock serialises the module bodies anyway.

{recording(PARALLEL)}

{recording(UNLOCKED)}

Read the middle two numbers of each. On the ordinary build both cases keep about one core busy. On the free threaded build the plain imports keep 3.60 cores busy and the deferred ones keep 0.98, the same single core the one thread control measured.

{lesson.claim("On a free threaded build, four threads importing four different modules run about three and a half times over, while four threads waking four different deferred imports run one at a time, because reification takes the interpreter wide import lock", unobservable="it needs a build configured with --disable-gil and several processors, and one notebook is only ever one build")}

Worth knowing before turning `lazy_imports=all` on in a threaded program. Deferring moves import work off the startup path, but on a free threaded build it moves that work onto a lock the ordinary path does not use.

## Try it yourself

Four things, in rough order of how much you will learn.

Run `python -X lazy_imports=all -c "import sys; print(len(sys.modules), len(sys.lazy_modules))"` and compare it with the same command without the flag. That is the whole feature in one line.

Take the escaped placeholder cell and put the copy somewhere a bit further away, such as a list or an attribute of an object, and check what it takes to wake it up. The rule is only about the two opcodes, so a placeholder inside a list stays a placeholder no matter how many times you index it.

Write a filter that prints every candidate rather than deciding anything, install it, and import something big. It is the cheapest way to see what a real program actually asks for.

Read `Python/import.c:3897-3925` and work out what happens if a deferred module's body reads the very name that is being resolved. Then write it and check.

## What you now know

`lazy import json` binds a name and does nothing else. The finding, reading and running happen the first time something reads that name back, and never if nothing does.

It compiles to the same `IMPORT_NAME` opcode as a plain import, with two spare bits in the argument saying lazy, eager or ordinary. There is no new opcode.

What gets bound is not a module. It is a five field placeholder that is not in `sys.modules`, that you can look at without setting it off, and whose name is in `sys.lazy_modules` until it resolves.

Only two opcodes resolve one: reading it as a bare name and reading it as an attribute of a module. Dict lookups, membership tests and reprs all leave it alone, and a placeholder copied into another variable resolves when that variable is read.

The scope rules are enforced by the symbol table, which is why `try` blocks are refused with a specific message rather than a generic syntax error.

Two other ways in exist for code you do not want to edit: a `__lazy_modules__` list at the top of a module, and a filter installed with `sys.set_lazy_imports_filter`.

A failure inside a deferred module arrives with a second exception attached as its cause, pointing at the `lazy import` line, reconstructed from information the placeholder was carrying all along.

It is worth about three quarters of a startup on a file that imports twelve modules and uses one, and about a hundred and thirty fewer modules loaded.

Resolution takes the interpreter wide import lock rather than a per name one, so on a free threaded build deferred imports do not scale across threads and ordinary ones do.

## What is next

R06 turns from the Python side of the runtime to the C side. Everything in these five lessons has an equivalent in the C API, and that API has tiers: a limited subset with a promise attached, a general one with no promise, and an internal one that is not for you at all.

Knowing which tier a function is in decides whether an extension you build against 3.15 still loads on 3.16, which is the same kind of question this lesson asked about when a module body runs, moved from time to versions.
""")


raise SystemExit(lesson.save())
