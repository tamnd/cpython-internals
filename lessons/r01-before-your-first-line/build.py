#!/usr/bin/env python
"""R01. Before your first line.

The first of the runtime lessons. Everything up to here has been about what happens when your
code runs. This one is about everything that has already happened by the time it starts: the
configuration, the two halves of startup, the modules that are in the binary rather than on the
disk, the Python program that works out where the standard library is, and the one entry that
gets pushed onto the front of the search path after all of that is finished.

Every measurement comes from a child interpreter, because a notebook is far too late to the
party to be a fair witness about its own startup.

The two Tier 1 recordings are the first release against debug pair in the book, and they turn up
something better than an assertion tax: a debug build imports fourteen modules off the disk that
a release build never touches, because it turns frozen modules off.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording

lesson = Lesson("r01-before-your-first-line", "r01")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("r01-before-your-first-line").figure

ON_RELEASE = "r01-what-startup-costs"
ON_DEBUG = "r01-what-startup-costs-on-a-debug-build"


lesson.md(f"""
# R01. Before your first line

{badge}

By the time your first statement runs, a lot has already happened. The interpreter has read a configuration out of three different places, built a runtime, made an interpreter, imported a few dozen modules without touching the disk once, worked out where the standard library lives by running a Python program that is not on `sys.path`, and then decided what to put at the front of `sys.path` afterwards.

None of that is your code, and all of it is on your clock. This lesson goes through it in the order it happens.

{figure("before-your-first-line", "a flow from the shell running python through configuration, runtime, core startup and main startup to your first line")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Modules/getpath.c:855-894@v3.15.0rc1`.

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

Almost every cell here starts a fresh child interpreter and asks it a question, because the only honest way to look at startup is to watch somebody else do it. Your notebook finished starting up long ago, and it has since imported hundreds of modules that have nothing to do with the subject.

Some runtimes cannot start a process at all. A browser tab is the usual example. Each cell checks first and says so rather than failing, so the notebook still reads through on a runtime that cannot run it.

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
## What is already there

Start with the inventory. A brand new interpreter that has been asked to run nothing at all still has a populated `sys.modules`, and the interesting question is not how many but where they came from.

Every module carries a `__spec__` with an `origin` on it. Three answers matter. `built-in` means the module is C code compiled straight into the `python` binary. `frozen` means it is Python source that was compiled to bytecode when CPython was built, and that bytecode is also inside the binary. Anything else is a path, which means somebody opened a file.

{lesson.claim("A fresh interpreter has a few dozen modules in sys.modules before it runs any of your code, and with site turned off not one of them was read from a file on disk")}
""")


lesson.code(
    """
import subprocess

COUNT = \"\"\"
import sys
kinds = {"built-in": 0, "frozen": 0, "from a file": 0}
named = []
for name, module in sys.modules.items():
    origin = getattr(getattr(module, "__spec__", None), "origin", None)
    if origin in ("built-in", "frozen"):
        kinds[origin] += 1
    elif origin is not None:
        kinds["from a file"] += 1
        named.append(name)
print(len(sys.modules), kinds["built-in"], kinds["frozen"], kinds["from a file"])
print(" ".join(named) or "none at all")
\"\"\"


def child(flags, code):
    \"\"\"Start a brand new interpreter with those flags and hand back what it printed.\"\"\"
    done = subprocess.run(
        [sys.executable, *flags, "-c", code], capture_output=True, text=True, check=True
    )
    return done.stdout.rstrip()


def children_work():
    \"\"\"Some runtimes cannot start a process at all. A browser tab is one of them.\"\"\"
    try:
        child([], "pass")
    except Exception:
        return False
    return True


CHILDREN = children_work()
NO_CHILDREN = "  this runtime cannot start another interpreter, so there is nothing to look at"

if not CHILDREN:
    print(NO_CHILDREN)
else:
    for what, flags in [("a normal start", []), ("started with -S", ["-S"])]:
        counts, names = child(flags, COUNT).splitlines()
        total, builtin, frozen, files = counts.split()
        print(f"  {what:18} {total:>3} modules in sys.modules", end="")
        print(f": {builtin} built in, {frozen} frozen, {files} from a file")
        print(f"  {'':18} the ones from a file: {names}")
""",
    varies=(
        "the counts move a little between releases and between builds, and a debug build reports "
        "far fewer frozen modules for a reason the last section of this lesson gets to"
    ),
)


lesson.md(f"""
{figure("what-is-already-imported", "a table of how each startup module got there, counted for a normal start and for a start with -S")}

Look at the `-S` row first, because that is the interpreter on its own. Nothing came off the disk. That is the whole point of freezing: the interpreter cannot import `os` from a file until it knows where files are, and it cannot know where files are until it has imported `os`. Putting the bytecode in the binary breaks the circle.

The difference between the two rows is `site`, the module that adds `site-packages` to your path and runs any `.pth` files it finds. If your first row listed some modules as coming from a file, those are the ones `site` brought in for you: a virtual environment hook, a `sitecustomize`, whatever your installation puts there. They are yours, not the interpreter's. `site` is not free either, and it is the first thing to turn off if you are starting a lot of short lived interpreters.

## Two halves, and why there are two

The `python` binary lands in `pymain_main`, which does two things and no more: get ready, then run {cite("Modules/main.c:855-868@v3.15.0rc1#pymain_main")}. Getting ready means turning your command line and your environment into a `PyConfig` and handing it over {cite("Modules/main.c:37-76@v3.15.0rc1#pymain_init")}. Running means `Py_RunMain`, which works out whether you gave it a script, a module, a string or nothing at all, does that, and then shuts the interpreter down again {cite("Modules/main.c:831-852@v3.15.0rc1#Py_RunMain")}.

The getting ready part is where the work is, and it comes in two halves {cite("Python/pylifecycle.c:1609-1639@v3.15.0rc1#Py_InitializeFromConfig")}. This is the {term("two phase initialisation")} that the C API documentation keeps mentioning. Core startup builds the runtime, the main interpreter and the built in types, and it has to manage all of that with no import system, no `sys.path` and no codecs {cite("Python/pylifecycle.c:1150-1172@v3.15.0rc1#pyinit_core")}. Main startup is everything that needs those, which includes working out `sys.path` in the first place {cite("Python/pylifecycle.c:1589-1606@v3.15.0rc1#pyinit_main")}.

That split explains something you have probably seen. A bad configuration comes out as a fatal error with a plain C string rather than as a Python traceback, because at the moment the problem is noticed there is nothing to raise and nothing to print it with.

You can watch the second half happen. `-X importtime` prints one line per import with the time it took, and for an interpreter running no code at all, every line it prints is startup.

{lesson.claim("The imports that happen before your first line add up to a few milliseconds, and the ones that show up include the import machinery, the codecs, os and site")}
""")


lesson.code(
    """
if not CHILDREN:
    print(NO_CHILDREN)
else:
    done = subprocess.run(
        [sys.executable, "-X", "importtime", "-c", "pass"], capture_output=True, text=True
    )
    total = 0
    for line in done.stderr.splitlines():
        parts = line.split("|")
        if len(parts) != 3:
            continue
        head = parts[0].removeprefix("import time:").strip()
        if not head.isdigit():
            continue
        total += int(head)
        if int(head) > 300:
            print(f"  {parts[2].strip():30} {int(head) / 1000:5.1f} ms on its own")
    print(f"  {'all of them, added up':30} {total / 1000:5.1f} ms")
""",
    varies=(
        "which imports clear the threshold depends on your disk and your machine, and an install "
        "with a sitecustomize module of its own will show that too"
    ),
)


lesson.md(f"""
The third column is the module, and the number is its own time rather than its children's. `site` looks cheap on that line and is not cheap overall, because most of what it costs is the imports it triggers underneath.

## The configuration comes from three places

A setting can be asked for on the command line, in the environment, or by whoever embedded the interpreter and filled in the `PyConfig` struct directly. When two of them disagree, the natural guess is that the nearest one wins. The guess is wrong.

The helper that reads a flag out of the environment is a few lines long, and the line that matters is `if (*flag < value) *flag = value;` {cite("Python/preconfig.c:560-578@v3.15.0rc1#_Py_get_env_flag")}. It raises a floor. It never lowers anything. `PYTHONOPTIMIZE` goes through the same shape of code {cite("Python/initconfig.c:1995-2020@v3.15.0rc1#PYTHONOPTIMIZE")}, and on the command line `-O` increments the level rather than assigning it, which is what makes `-OO` mean two {cite("Python/initconfig.c:3210-3222@v3.15.0rc1#optimization_level")}.

Put those together and the rule is simple to say and easy to forget. The highest number anybody asked for is the one you get. There is one way out, which is `-E`: it throws the environment away before any of this happens, so it does not beat the environment, it deletes it.

{lesson.claim("When the command line and the environment disagree about the optimization level, neither wins by being nearer, the higher of the two is what you get, and -E removes the environment from the argument entirely")}
""")


lesson.code("""
import os

ASK = "import sys; print(sys.flags.optimize)"
BASE = {k: v for k, v in os.environ.items() if k != "PYTHONOPTIMIZE"}

if not CHILDREN:
    print(NO_CHILDREN)
else:
    for what, flags, extra in [
        ("nothing at all", [], {}),
        ("-O", ["-O"], {}),
        ("-OO", ["-OO"], {}),
        ("PYTHONOPTIMIZE=2", [], {"PYTHONOPTIMIZE": "2"}),
        ("PYTHONOPTIMIZE=2 and -O", ["-O"], {"PYTHONOPTIMIZE": "2"}),
        ("PYTHONOPTIMIZE=1 and -OO", ["-OO"], {"PYTHONOPTIMIZE": "1"}),
        ("PYTHONOPTIMIZE=2 and -E", ["-E"], {"PYTHONOPTIMIZE": "2"}),
    ]:
        done = subprocess.run(
            [sys.executable, *flags, "-c", ASK],
            capture_output=True,
            text=True,
            env={**BASE, **extra},
        )
        print(f"  {what:26} sys.flags.optimize is {done.stdout.strip()}")
""")


lesson.md(f"""
{figure("the-highest-setting-wins", "a table of what you asked for, what you might expect sys.flags.optimize to be, and what it actually is")}

The two middle rows are the ones worth remembering. A `PYTHONOPTIMIZE=2` left in a shell profile years ago is not overridden by putting `-O` on the command line today, and nothing tells you.

## sys.path is worked out by a Python program that is not on sys.path

Here is the part that surprises people. `sys.path` is not computed in C. It is computed by a Python program, `Modules/getpath.py`, which is compiled to bytecode when CPython itself is built and stored in the binary as a {term("marshal")}led blob {cite("Modules/getpath.c:830-840@v3.15.0rc1#_Py_Get_Getpath_CodeObject")}. During main startup that blob is turned back into a code object and evaluated {cite("Modules/getpath.c:855-894@v3.15.0rc1#_PyConfig_InitPathConfig")}, and what comes out is the whole {term("path configuration")}: `sys.prefix`, `sys.exec_prefix`, `sys.executable`, `sys._base_executable` and `sys.path`.

It cannot import anything, for the obvious reason that `sys.path` is what it is there to produce. So it is handed eleven C functions to stand in for the `os.path` it cannot have: `abspath`, `basename`, `dirname`, `hassuffix`, `isabs`, `isdir`, `isfile`, `isxfile`, `joinpath`, `readlines` and `realpath` {cite("Modules/getpath.c:560-582@v3.15.0rc1#getpath_methods")}. That list is the entire vocabulary the path search has to work with.

{figure("who-works-out-sys-path", "a flow from Modules getpath dot py through compilation and marshalling to the values it produces at startup")}

The output has one entry in it that people misread constantly. There is always a `pythonXY.zip` next to the standard library, and on a normal install that file does not exist. It is not a bug and it is not left over from anything. Putting a zip file there is a supported way to ship a whole standard library in one file, so the entry is added unconditionally and the import system simply finds nothing when it looks.

{lesson.claim("sys.path contains an entry for a zip file next to the standard library, and on an ordinary install that file is not there")}
""")


lesson.code(
    """
WHERE = \"\"\"
import os
import sys
print("  sys.executable       ", sys.executable)
print("  sys._base_executable ", sys._base_executable)
print("  sys.prefix           ", sys.prefix)
print("  sys.base_prefix      ", sys.base_prefix)
for entry in sys.path:
    shown = entry or "(the empty string)"
    print("  sys.path             ", shown, "exists:", os.path.exists(entry))
\"\"\"

if not CHILDREN:
    print(NO_CHILDREN)
else:
    print(child([], WHERE))
""",
    varies=(
        "every path here is where your Python happens to be installed, and inside a virtual "
        "environment sys.prefix and sys.base_prefix point at different places"
    ),
)


lesson.md(f"""
If you ran that inside a virtual environment, `sys.prefix` and `sys.base_prefix` came out different. That difference is the whole mechanism: a virtual environment is a `pyvenv.cfg` file that tells `getpath.py` where the real installation is, and everything else follows from the two prefixes.

## The front of sys.path is decided last

Everything above happens while the interpreter is starting. The front of `sys.path` does not. It is pushed on afterwards, once the interpreter is already running, by the code that is about to hand control to your program {cite("Modules/main.c:657-696@v3.15.0rc1#pymain_run_python")}.

What goes in depends on how you started. The directory the script is in, for a script. The current directory, for `-m`. The empty string, for `-c` and for the interactive prompt, which the import system reads as the current directory at the time of each import.

This is the cause of the most common confusion in Python. A file called `random.py` sitting next to your script shadows the standard library module of the same name, and it does so because its directory was put in front of the standard library after the standard library had already been located.

There is a switch for it. `-P` on the command line, or `PYTHONSAFEPATH` in the environment, is the {term("safe path")} option {cite("Modules/main.c:696-728@v3.15.0rc1#safe_path")}. Note what it does: the entry is never added, rather than added and then taken away. So `sys.path[0]` becomes whatever was going to be first anyway, which is that zip file from the previous section.

{lesson.claim("With -P the entry that would have gone on the front of sys.path is never added at all, so sys.path[0] becomes the first of the standard library entries instead")}
""")


lesson.code(
    """
import pathlib
import tempfile

SHOW = "import sys; print(repr(sys.path[0]))"

if not CHILDREN:
    print(NO_CHILDREN)
else:
    with tempfile.TemporaryDirectory() as folder:
        (pathlib.Path(folder) / "show.py").write_text(SHOW)
        script = str(pathlib.Path(folder) / "show.py")
        for what, args, where in [
            ("python -c code", ["-c", SHOW], None),
            ("python show.py", [script], None),
            ("python -m show", ["-m", "show"], folder),
            ("python -P show.py", ["-P", script], None),
        ]:
            done = subprocess.run(
                [sys.executable, *args], capture_output=True, text=True, cwd=where
            )
            print(f"  {what:22} {done.stdout.strip()}")
        print(f"  the script is in       {folder!r}")
""",
    varies=(
        "the temporary directory is different every run, and on macOS the child reports it with "
        "the symbolic links resolved so it looks slightly different from the last line"
    ),
)


lesson.md(f"""
{figure("what-goes-in-front", "a table of how you started python, what lands in sys path index zero, and when it was added")}

The last row is the one to reach for when something is being shadowed and you cannot work out what. If the problem goes away under `-P`, a file in your own directory was the cause.

## What all of it costs

Now the clock. The cell below starts an interpreter that runs nothing, ten times, and keeps the fastest, because the fastest run is the one where the machine was not busy doing something else.

{lesson.claim("Starting an interpreter that runs none of your code takes tens of milliseconds, and -S takes a noticeable slice off that because site is a real import")}
""")


lesson.code(
    """
import time


def best(flags, rounds=10):
    \"\"\"The fastest of a few runs, which is the honest number on a machine you share.\"\"\"
    fastest = None
    for _ in range(rounds):
        started = time.perf_counter()
        subprocess.run([sys.executable, *flags, "-c", "pass"], capture_output=True, check=True)
        taken = time.perf_counter() - started
        fastest = taken if fastest is None else min(fastest, taken)
    return fastest


if not CHILDREN:
    print(NO_CHILDREN)
else:
    for what, flags in [
        ("everything", []),
        ("no site, with -S", ["-S"]),
        ("no site and no environment", ["-I", "-S"]),
    ]:
        print(f"  {what:28} {best(flags) * 1000:5.1f} ms")
""",
    varies=(
        "startup time depends on your disk, your machine and whether the files are still in the "
        "operating system cache, so only the gaps between the three rows mean anything"
    ),
)


lesson.md(f"""
Those numbers include the cost of your machine starting a process at all, which is not the interpreter's fault, so treat the differences between the rows as the real content.

The two recordings below run the same program in two containers built from the same source. One is an ordinary release build. The other was configured with `--with-pydebug`, which is the build you would use if you were working on CPython itself.

{recording(ON_RELEASE)}

{recording(ON_DEBUG)}

{figure("what-startup-costs", "bars of milliseconds to start and do nothing, for a release build and a debug build, each with and without site")}

The debug build takes 56.5 ms against 26.5 ms. The obvious explanation is the assertions and the reference count bookkeeping, and the obvious explanation is mostly wrong. Look at the module counts instead. The release build reports 17 frozen and 0 from a file. The debug build reports 3 frozen and 14 from a file. That is not the same work done more slowly, it is different work.

A debug build turns frozen modules off, and it is one `#ifdef` in the defaults {cite("Python/initconfig.c:1193-1201@v3.15.0rc1#use_frozen_modules")}. The reasoning is good: if you are debugging CPython you want to step through the real `Lib/os.py` on disk, not through bytecode that was baked into the binary at build time. The price is that `os`, `site`, `codecs` and everything else frozen now comes off the disk, and the import bill goes from 11.6 ms to 30.8 ms. You can put it back with `-X frozen_modules=on`, or with `PYTHON_FROZEN_MODULES=on` in the environment {cite("Python/initconfig.c:2849-2866@v3.15.0rc1#frozen_modules")}.

{lesson.claim("A debug build starts in about twice the time of a release build, and most of the extra is not the assertions, it is the fourteen modules it reads off the disk because a debug build turns frozen modules off", unobservable="it is a comparison between two builds of the same source, and one interpreter cannot be both of them")}
""")


lesson.md("""
## Try it yourself

Four things, in rough order of how much you will learn.

Make a file called `random.py` in a directory, put `print("not the real one")` in it, put an empty `main.py` next to it that does `import random`, and run it. Then run it again with `-P`. That is the shadowing problem and its fix in about thirty seconds.

Change the threshold in the import time cell from 300 down to 0 and read the whole list. It is not long, and it is the complete set of things that have to exist before Python can run a single line. Look for `zipimport`, which is there so that the zip file entry from earlier can actually be used.

Add `("-X frozen_modules=off", ["-X", "frozen_modules=off"])` to the counting cell and watch the frozen count collapse and the from a file count rise. That is you turning a release build into a debug build for one setting, and it is worth doing before reading the last section again.

Set `PYTHONOPTIMIZE=2` in your shell and then try to get back to zero using only command line flags. There is exactly one way and it is not `-O`.

## What you now know

A fresh interpreter has a few dozen modules loaded before your first statement, and on a release build none of them were read from a file. They are either C compiled into the binary or Python bytecode frozen into it.

Startup is two halves on purpose. Core startup runs with no import system and no `sys.path`, which is why configuration errors come out as fatal errors rather than exceptions. Main startup is everything that needs an import system, including working out `sys.path`.

Settings can come from the command line, the environment or an embedder, and the answer is the highest number anybody asked for rather than whichever one is nearest. `-E` is the escape hatch, and it works by discarding the environment rather than by outranking it.

`sys.path` is produced by a Python program that is frozen into the binary and handed eleven C functions to stand in for `os.path`, because the module it would normally use cannot be imported until it has finished. Its output always includes a zip file that usually does not exist.

The front of `sys.path` is added last, after startup is over, and it is the directory of your script or the current directory. That is the whole mechanism behind accidentally shadowing a standard library module, and `-P` turns it off.

A plain start costs tens of milliseconds, of which `site` is a real slice, and a debug build costs about double, mostly because it reads from disk what a release build reads from its own binary.

## What is next

This lesson kept saying "the runtime" and "the interpreter" as if they were one thing. They are not. There is a runtime, there are interpreters inside it, and there are threads inside those, and each of the three owns a different pile of state. C04 made a second interpreter and never said what one is made of.

R02 opens that up. Where every piece of the state this book has been poking at for seventy lessons actually lives, which of those piles is shared and which is not, and why moving one field from one struct to another is a change worth arguing about.
""")


raise SystemExit(lesson.save())
