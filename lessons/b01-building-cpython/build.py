#!/usr/bin/env python
"""B01. Building CPython, and whether you need to.

The first lesson of the build part, and the eleventh lesson overall. It lands here rather
than at lesson one on purpose: a beginner who has to compile CPython before they can see
anything interesting will not compile CPython, and the ten lessons in front of this one
needed nothing but a browser tab.

The argument the lesson makes is that there are three ways to have a CPython to poke at and
only one of them is building. The container comes before the compiler here, and it is in the
body rather than in a footnote at the end.

The one original piece of work in it is the `_Py_` macro finding: `sysconfig` cannot see any
macro in `pyconfig.h` whose name starts with an underscore, which is why a tail calling build
used to print `stock release build` in this project's own banner. That is #110.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of
them. `just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("b01-building-cpython", "b01")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("b01-building-cpython").figure

lesson.md(f"""
# B01. Building CPython, and whether you need to

{badge}

Ten lessons in, and every one of them ran on an interpreter somebody else built. That binary was configured once, on a machine you have never seen, with a specific list of flags, and it has been carrying that list around ever since. The next cell prints it.

{figure("where-we-are", "the eight stages of the pipeline with none of them highlighted")}

Some of what you have already measured was decided by that list rather than by Python. Whether `sys.gettotalrefcount` exists, how big an object is, whether a hot loop leaves the interpreter entirely: all build, none language.

So this lesson is about producing your own. It is also about the more useful fact that you probably do not have to, which is why the container is in the middle of the lesson and not in a footnote at the end.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `configure.ac:1771-1785@v3.15.0rc1#Py_DEBUG`.

Read it as four parts: the file, the lines, the release those line numbers belong to, and the name of the thing they are inside.

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

Everything below was checked against the version this cell prints and against 3.14. Where the two disagree, the lesson says so.
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
## What your interpreter remembers about being built

Start with the thing you already have. {lesson.claim("a CPython built with configure keeps the argument list it was given, and sysconfig hands it back at run time")}, along with a few hundred other settings from the same build.
""")


lesson.code(
    """
import pyxray

pyxray.builds.report()
""",
    varies="Everything in this cell is a property of your interpreter and not of Python, so no two readers get the same output. That is the point of running it.",
)


lesson.md(f"""
Three things to notice in that output.

The configure line is a real command somebody typed. If you installed Python from python.org, from a distribution, from Homebrew or through a tool like `uv`, that list is the recipe that packager used, and it usually has ten to twenty entries in it. Almost nobody has ever looked at their own.

The settings table is the short list this project cares about. `Py_DEBUG` decides whether {term("reference count", "reference counts")} are visible. `Py_GIL_DISABLED` decides whether you are on the free threaded build, where the object header is a different shape. `SIZEOF_VOID_P` is the number T08 measured rather than asserted, because it is 8 on a laptop and 4 in a browser.

And the last block says which of the five builds this project publishes you are on, which for most readers is none of them. That is a real answer, not a failure. Those five are what this project builds, not the only ways to build CPython.

## Three ways in, and only one of them is building

{figure("three-ways-in", "a table of the three routes to having a CPython to experiment on, and what each one costs")}

The browser row is what you have been using. Every lesson so far ran under {term("Pyodide")}, which is a real CPython compiled to {term("WebAssembly")}, and nothing in T01 through T10 needed anything else.

The container row is the honest middle. This project publishes ten images, five configurations across two architectures, and they carry the source tree and a debugger. One command and you are inside a debug build:

```
docker run --rm -it ghcr.io/tamnd/cpython-internals/cpython:debug
```

The images are pinned by digest rather than by tag, so the one you pull is the exact one the lessons were checked against. There is also a devcontainer, so VS Code will do the pull for you.

The third row is building it yourself, and it is worth doing once. Not because the material needs it, but because a compiler and twenty minutes turns CPython from a program you use into a program you can change.

## What a build actually is

{figure("what-a-build-is", "a five step chain from configure.ac to the python binary, with what runs each step")}

Only the two ends of that chain are interesting.

`configure` is a shell script, and a huge one, but nobody wrote it. It is generated from `configure.ac` by a tool called autoconf, and `configure.ac` is the file CPython developers actually edit. When you run `./configure --with-pydebug`, the script tries several hundred small experiments on your machine, then writes down what it found in two files.

`Makefile` is the first. It holds the compiler, the flags, and the list of things to build, which is why `sysconfig` can tell you `CC` and `OPT` years later.

`pyconfig.h` is the second, and it is the more interesting one. It is a header full of `#define` lines saying what your system has and what you asked for. Every C file in CPython includes it, and it is how one source tree becomes a different program on Linux, on macOS and in a browser.

Then `make` compiles a few hundred C files and links them. {lesson.claim("the python binary is a small program, and almost all of the interpreter lives in the library it links against", unobservable="the split between the binary and libpython is a link time arrangement, and Python is only ever handed the result")}: {cite("Makefile.pre.in:1004-1006@v3.15.0rc1#BUILDPYTHON")}.

## The files in the tree that nobody wrote

Here is the thing that catches everybody the first time they go looking for the parser.

{figure("generated-or-written", "five files from the CPython tree, four of them generated and one written by hand")}

`Parser/parser.c` is about forty thousand lines and no human has ever read it in order. Its first line says so: `// @generated by pegen from python.gram`. The file you want is `Grammar/python.gram`, which is two thousand lines and is the actual grammar of Python.

The same is true three more times. `Python/Python-ast.c` comes from `Parser/Python.asdl`, and `Python/generated_cases.c.h` and `Include/opcode_ids.h` both come from `Python/bytecodes.c`. Each generated file says who wrote it in its first two lines, and three of them add `// Do not edit!`.

`make regen-all` rebuilds all of them: {cite("Makefile.pre.in:1956-1962@v3.15.0rc1")}. It needs a working Python to run the generators, which is the chicken and egg you would expect, and it is solved the boring way: the generated files are committed, so you can build CPython without already having one.

The rule that follows is short. If a file's first two lines say it was generated, do not edit it and do not read it as an explanation of anything. Find its input.

## The five builds, and what moves between them

{figure("the-five-builds", "a table of the five configurations, their configure flags, what each one changes and how to detect it")}

Same source, same commit, five binaries. The debug build is the one worth understanding, because it is the one that changes the numbers.

`--with-pydebug` sets `Py_DEBUG`, at {cite("configure.ac:1771-1785@v3.15.0rc1#Py_DEBUG")}, and that macro turns on assertions all through the interpreter, adds `sys.gettotalrefcount`, and makes the allocator fill freed memory with a recognisable byte pattern so a use after free shows up as garbage rather than as the old value still being there.

It also makes objects bigger and everything two to three times slower. So the rule this project follows is that behaviour comes from the debug build and timings never do.

## The flag sysconfig cannot see

The tail calling build is where this gets awkward, and the awkwardness is worth a section because it is the kind of thing that costs somebody an afternoon.

`--with-tail-call-interp` builds the eval loop as a chain of tail calls instead of one enormous switch. Configure records it by defining `_Py_TAIL_CALL_INTERP` in `pyconfig.h`, at {cite("configure.ac:7467-7489@v3.15.0rc1#_Py_TAIL_CALL_INTERP")}.

Ask `sysconfig` for that macro and you get nothing back. {lesson.claim("sysconfig cannot see any macro in pyconfig.h whose name starts with an underscore, so _Py_TAIL_CALL_INTERP is missing from get_config_vars even on a build that defines it")}, and the reason is one regular expression: {cite("Lib/sysconfig/__init__.py:438@v3.15.0rc1#define_rx")}.

```python
define_rx = re.compile("#define ([A-Z][A-Za-z0-9_]+) (.*)\\n")
```

The name has to start with a capital letter. Every underscored macro in the header is dropped on the floor, and there are usually about fourteen of them.

Reading them yourself is the same regular expression with the capital letter taken out, which is all `pyxray.build.header` is. Run it and compare each name against what `sysconfig` says about it.
""")


lesson.code(
    """
import sysconfig
from pathlib import Path

from pyxray.build import header

where = Path(sysconfig.get_config_h_filename())
print(f"pyconfig.h would be at {where}")
print()

hidden = header()
if hidden:
    print("macros in there that sysconfig will not show you:")
    for name in sorted(hidden):
        print(f"  {name:45} sysconfig says {sysconfig.get_config_var(name)}")
else:
    print("There is no header on disk here, which is what a browser build looks like.")
    print("Everything you can ask this interpreter comes from sysconfig alone,")
    print("so the underscored macros are not just hidden, they are gone.")
""",
    varies="Which macros are in your pyconfig.h depends on your platform and your build, so the list is different for everybody. That every one of them reads back as None is not. In a browser there is no header at all.",
)


lesson.md(f"""
This is not a hypothetical. This project's own banner, the one at the top of every lesson, read that macro under the wrong name and then could not have seen it anyway, so a tail calling interpreter printed `stock release build` for months. Reading the header directly is four lines, and `pyxray.build.header` now does it.

The general lesson is more useful than the specific bug. `sysconfig` is a snapshot of what the build system knew, and `pyconfig.h` is what the compiler actually saw. When the two disagree, the header is right.

## Two flags for opposite jobs

{figure("flags-worth-knowing", "--enable-optimizations and --with-pydebug side by side, and what each one is for")}

`--enable-optimizations` turns on {term("profile guided optimization")}: build the interpreter, run a chunk of the test suite to see which branches are hot, then throw the build away and do it again using what it learned. It is worth about ten percent and it turns a five minute build into anywhere from twenty minutes to an hour. See {cite("configure.ac:1847-1860@v3.15.0rc1#Py_OPT")}.

So the two flags people reach for are for opposite jobs, and mixing them up is the classic mistake. A benchmark on a debug build is meaningless. A crash investigation on a PGO build is a wall of inlined frames.

For everything this project does, plain `./configure --with-pydebug --with-assertions && make -j` is right, and it takes about five minutes on a laptop.

## Try it yourself

**One.** Run `pyxray.builds.report()` and read your own configure line. Find one flag in it you do not recognise and look it up in `configure.ac`.

**Two.** Print `sysconfig.get_config_var("CFLAGS")`. Find the optimization level in there and say whether you are on a `-O0`, `-O2` or `-O3` build.

**Three.** Open `Grammar/python.gram` on GitHub and find the rule for `if_stmt`. Then open `Parser/parser.c` and find the function that rule generated. The second one is much harder to read, which is the whole argument for the first one existing.

**Four.** Pull the debug image and check its own banner: `docker run --rm ghcr.io/tamnd/cpython-internals/cpython:debug python -c "import sys; print(sys.gettotalrefcount())"`. Then try the same command against `:release` and watch it fail.

**Five.** If you have twenty minutes and a compiler, clone CPython at `v3.15.0rc1`, run `./configure --with-pydebug` and `make -j`, and compare the `report()` output from your build against the one you got in exercise one.

## What just happened

Your interpreter has been carrying its own build recipe around the whole time, and `sysconfig` will hand it back.

A build is `configure.ac` becoming `configure`, `configure` writing a `Makefile` and a `pyconfig.h`, and `make` turning a few hundred C files into a binary. The header is where one source tree becomes a different program on every platform.

Four of the largest files in the tree were written by a generator and say so in their first line. Editing them is a wasted afternoon, and reading them as an explanation is worse.

Five builds, one source. The debug build tells you about behaviour and lies about speed. The release build is the other way round. The free threaded build is a different interpreter rather than a flag.

`sysconfig` hides every macro whose name starts with an underscore, which is a real bug in this project's own banner and a good reminder that a convenient API is not always the complete one.

And the container is a first class route, not a fallback. Ten lessons happened without a compiler and the rest can too.

## Where this goes next

B02 is the debugger. Once there is a debug build to point it at, `gdb` and `lldb` will stop a running interpreter in the middle of `_PyEval_EvalFrameDefault` and let you look at the frame, which is the first time the C in these lessons becomes something you can step through rather than read.

If you are staying in the browser, B02 has recorded sessions for exactly that, so nothing there is closed to you either.
""")


raise SystemExit(lesson.save())
