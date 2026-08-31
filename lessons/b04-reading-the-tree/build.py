#!/usr/bin/env python
"""B04. Reading the tree.

The last lesson of the build part, and the fourteenth overall. B01 got the reader a build, B02
a debugger and B03 a way to check they have not broken anything. This one is about the tree
those three were pointed at.

Z02 covers where things are for a reader who has no checkout, and does it by keyword. This
lesson is the other half, for a reader who does have one: which files are theirs to change,
which are the output of a script, and how to find out why a line is the way it is. The two
recorded experiments exist because Z02 has to mark its central claim unobservable, and a
lesson that comes after a build does not.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording

lesson = Lesson("b04-reading-the-tree", "b04")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("b04-reading-the-tree").figure

#: The two recorded runs. Both need the source tree the build came from, which is in the image
#: and not on a reader's machine, so both happened there.
SCAN = "b04-what-a-script-wrote"
GENERATORS = "b04-changing-the-source-of-truth"

lesson.md(f"""
# B04. Reading the tree

{badge}

The build you made in B01 came from about twelve hundred C files. You will open maybe thirty of them, ever.

So the useful skill is not knowing the tree, it is knowing three things about any file you land in: whether a person wrote it, whether you are allowed to change it, and why it says what it says. This lesson is those three, and it ends with you adding an instruction to CPython and watching the C for it appear.

{figure("three-kinds-of-file", "a table of the three kinds of file in the tree and what to do with each")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Include/opcode_ids.h:1-4@v3.15.0rc1`.

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
## Part of the tree is already on your machine

Before any of the C, the good news. Roughly half of CPython is written in Python, and the interpreter you are reading this on has all of it, on disk, in files you can open.

Better than that, it will tell you where. {lesson.claim("the running interpreter can hand you the file and the line range for anything in the standard library written in Python, in the same shape as the source references in this book")}, using two functions in `inspect`: {cite("Lib/inspect.py:886-897@v3.15.0rc1#getsourcefile")} gives you the file, and {cite("Lib/inspect.py:1162-1181@v3.15.0rc1#getsourcelines")} gives you the lines and the number of the first one.

{figure("a-reference-is-a-path", "the two parts of a source reference, a file and a line range")}

Put them together and you have made a reference of your own.
""")


lesson.code(
    """
import functools
import inspect
import json
import os
import textwrap
from pathlib import Path

# Where your standard library lives, asked of a module rather than of sysconfig. Both know,
# but a browser build serves the library out of a zip and sysconfig still reports the plain
# directory it would have been, while a module's own file is always the real answer.
LIB = Path(inspect.getsourcefile(textwrap)).parent


def reference(thing):
    \"\"\"A file and a line range, in the same shape as the references in this lesson.\"\"\"
    where = os.path.relpath(inspect.getsourcefile(thing), LIB)
    lines, first = inspect.getsourcelines(thing)
    return f"Lib/{where}:{first}-{first + len(lines) - 1}"


for thing in (functools.cache, json.JSONDecoder, textwrap.shorten, inspect.getsourcelines):
    print(f"{thing.__qualname__:18} {reference(thing)}")
""",
    differs=(
        "The line numbers are different on 3.14, because the files have been edited since. "
        "The point is that your own interpreter knows them, whatever they are."
    ),
)


lesson.md("""
Those are real line numbers in real files, and you can go one step further and read the thing itself. `functools.cache` is a decorator a lot of people use every week without ever having seen it, and it is three lines long.
""")


lesson.code("""
print(inspect.getsource(functools.cache))
""")


lesson.md(f"""
That is the entire implementation. `cache` is `lru_cache` with the size limit taken off.

This works for anything written in Python and nothing written in C, and the reason is worth knowing rather than guessing: `getsourcefile` looks at the file the module was loaded from, and for a C module that is a `.so` with no source in it, so it returns `None` rather than pretending.

## An index of a file, in nine lines

The second move is turning a file into a list of what is in it. Editors do this and so does `grep`, but doing it yourself once is what makes the source stop feeling like a wall of text.

{lesson.claim("the ast module can list every function and class in a file with the exact line range of each, which is enough to build an index of any Python file in the standard library")}, and the whole of it is `ast.parse` followed by a loop over the top level.
""")


lesson.code("""
import ast

# inspect.getsource rather than reading the file, because inspect asks whoever imported the
# module for the text and that works even when the library is packed into a zip.
name = Path(inspect.getsourcefile(textwrap)).name
tree = ast.parse(inspect.getsource(textwrap))

print(f"Lib/{name}")
print()
for node in tree.body:
    if isinstance(node, ast.FunctionDef | ast.ClassDef):
        kind = "class" if isinstance(node, ast.ClassDef) else "def"
        print(f"  {kind:6} {node.name:14} Lib/{name}:{node.lineno}-{node.end_lineno}")
""")


lesson.md(f"""
Six names, one file, and every one of them with a line range you could paste into a bug report.

Point that loop at a directory instead of a file and you have the index behind every jump to definition you have ever used. There is no more to it than this.

## The files nobody typed

Now the part that costs people afternoons.

Some files in the tree were not written by anyone. A script produced them while CPython was being built, and if you open one looking for an explanation you will not find one, because you are reading the output of a program rather than the program.

CPython is good about this. {lesson.claim("a generated file says so in its own first few lines, and usually names the script that wrote it, so you can find every one of them in your own standard library with a search for a handful of phrases")}. Here is {cite("Include/opcode_ids.h:1-4@v3.15.0rc1")}, which is four lines of banner before any code:

```c
// This file is generated by Tools/cases_generator/opcode_id_generator.py
// from:
//   Python/bytecodes.c
// Do not edit!
```

Your own standard library has a few of these. The next cell finds them.
""")


lesson.code(
    '''
import re
import zipfile

SKIP = ("test/", "site-packages/", "idlelib/")
SAYS = re.compile(r"auto[- ]?generated|generated by|do not edit|don\'t edit", re.IGNORECASE)
NAMES_A_SCRIPT = re.compile(r"[\\w/]+\\.py")


def wanted(name):
    return name.endswith(".py") and not name.startswith(SKIP)


def everything():
    """Every Python file in your standard library, paired with the text of it.

    A browser build ships the whole library as a single zip rather than as a directory, so
    pathlib cannot walk it there. Two lines of zipfile covers both cases.
    """
    if LIB.suffix == ".zip":
        with zipfile.ZipFile(LIB) as bundle:
            names = [one for one in bundle.namelist() if wanted(one)]
            return [(one, bundle.read(one).decode("utf-8", "replace")) for one in names]
    on_disk = [one for one in LIB.rglob("*.py") if wanted(one.relative_to(LIB).as_posix())]
    return [
        (one.relative_to(LIB).as_posix(), one.read_text(encoding="utf-8", errors="replace"))
        for one in on_disk
    ]


def banner(text):
    """The first six lines, which is where a generated file owns up to being one."""
    return "\\n".join(text.splitlines()[:6])


yours = everything()
generated = sorted((name, text) for name, text in yours if SAYS.search(banner(text)))

print(f"Python files in your standard library: {len(yours)}")
print(f"files that say a script wrote them:    {len(generated)}")
print()
for name, text in generated:
    #: Skip past the file's own name so a module called foo.py does not claim to have
    #: written itself.
    said = banner(text)[len(name.rpartition("/")[2]) :]
    wrote_it = NAMES_A_SCRIPT.search(said)
    print(f"  Lib/{name:26} {wrote_it.group(0) if wrote_it else 'does not say which script'}")
''',
    varies=(
        "How many files you have depends on the install rather than the version. A source "
        "build, a framework install and a Colab image all count differently, and some ship "
        "extra files of their own. The named ones in the middle are on all of them."
    ),
)


lesson.md("""
`Lib/token.py` is the one to look at. Every name in it, `NAME`, `NUMBER`, `INDENT`, the whole list T02 spent a lesson on, comes out of `Grammar/Tokens` through a script. Nobody has typed that file since 2018.

`Lib/_opcode_metadata.py` is the other interesting one, and it is the thread this lesson pulls on for the rest of the way. It is generated from `Python/bytecodes.c`, which is also where the C for the eval loop comes from.

That is your standard library, which is the small half. On the C side it is not a handful of files.
""")


lesson.md(recording(SCAN))


lesson.md(f"""
{figure("typed-and-not-typed", "a bar chart of generated against hand written lines of C")}

Four hundred thousand lines out of a million, and Argument Clinic alone wrote 164 files.

Two things in that list are worth a second look. `Programs/_freeze_module.py` wrote 25 files that are not in a fresh checkout at all, because freezing the startup modules happens during the build. And the twelve that say `it does not say` are almost all the Unicode tables, which are old enough to predate the convention.

Z02 makes the same claim about a third of the C being generated and has to mark it as something you cannot check, because checking it needs the whole tree. That is what the recording above is for. Same rule, same phrases, run against the tree the debug image was built from.
""")


lesson.md(f"""
## The file that four other files come from

{term("generated file", "Generated files")} are only annoying while you do not know where they came from. Once you do, they are the opposite: one file to read instead of four.

{figure("one-file-many-files", "a tree showing one input file producing four generated files through four scripts")}

`Python/bytecodes.c` is the source of truth for what every {term("instruction")} does. Nothing else in CPython describes an instruction. The scripts in `Tools/cases_generator/` read it and write the eval loop, the opcode numbers, the jump table and the Python side of the `dis` module, and {lesson.claim("running those scripts against the unchanged input reproduces the committed files byte for byte, which is what makes generated a fact about a file rather than a comment in it", unobservable="the scripts live in Tools/ and read Python/bytecodes.c, and neither of those ships with an installed Python, so this is the recorded run below rather than a cell")}.

The one that writes the opcode numbers is nine lines long. This is the whole of it, from {cite("Tools/cases_generator/opcode_id_generator.py:24-41@v3.15.0rc1#generate_opcode_header")}:

```python
def generate_opcode_header(filenames, analysis, outfile):
    write_header(__file__, filenames, outfile)
    out = CWriter(outfile, 0, False)
    with out.header_guard("Py_OPCODE_IDS_H"):
        out.emit("/* Instruction opcodes for compiled code */\\n")

        def write_define(name, op):
            out.emit(f"#define {{name:<38}} {{op:>3}}\\n")

        for op, name in sorted([(op, name) for (name, op) in analysis.opmap.items()]):
            write_define(name, op)
```

A header guard, a comment, and a loop that prints one `#define` per instruction. That is where every opcode number in Python comes from.

So there is a thing you can do that sounds much harder than it is: add an instruction to `Python/bytecodes.c`, run the scripts, and read what they wrote. The next recording does exactly that, on the tree in the debug image, and nothing it does touches the tree itself.
""")


lesson.md(recording(GENERATORS))


lesson.md(f"""
Read the last block twice. Three lines went into `bytecodes.c` and thirteen came out, and you wrote one of them.

`frame->instr_ptr = next_instr` and `next_instr += 1` are the interpreter moving along. `INSTRUCTION_STATS` is the counter T07 uses. The two `stack_pointer` lines are the eval loop putting the stack somewhere the rest of CPython can see it, because the C in the instruction body might call anything. `DISPATCH()` is the jump to the next instruction. Every instruction in CPython has that scaffolding around it and no instruction in `bytecodes.c` contains any of it.

That is the argument for the whole arrangement. The generated file is longer and duller than its input, which is exactly what you want from a machine.

If you were changing CPython for real, the command after the edit is `make regen-cases`, or `make regen-all` to rebuild every generated file at once. Forget it and the build quietly uses the old ones.

## Why is this line like this

The last skill is the one that stops you from breaking things.

Something in CPython will look wrong to you. A check that seems redundant, a branch that seems impossible, a comment that says "see the discussion" without saying where. Almost always somebody hit a real bug and this is the fix, and the way to find out is not to read harder.

{figure("four-ways-to-ask-why", "a table of four git commands and what each one answers about a line")}

The last two rows are the trick. {lesson.claim("every commit in CPython names an issue number in the first line of its message, so any line of code leads to a discussion")}: the format is `gh-NNNNNN: Summary of the changes made`, and the pull request template in the repository asks for it before anything else.

That number is the same number on the issue tracker, and the issue is where the argument happened. `git blame` gives you a commit, the commit gives you an issue, and the issue gives you three people disagreeing about the thing that is confusing you.

There is a second route to the same place that needs no git at all. Every user visible change ships a {term("blurb")} file in `Misc/NEWS.d/`, and at release time they are collected into one file per version with the issue numbers kept. The next cell takes three real entries from {cite("Misc/NEWS.d/3.15.0rc1.rst:11-33@v3.15.0rc1")} and turns them into links.
""")


lesson.code('''
ENTRIES = """
.. date: 2026-08-02-11-47-15
.. gh-issue: 154902
.. nonce: DIi6sf
.. section: Core and Builtins

Fix a crash when ``__conditional_annotations__`` is rebound to a non-set
object.

..

.. date: 2026-07-28-10-00-00
.. gh-issue: 133931
.. nonce: fnQzxD
.. section: Core and Builtins

Fix data races when setting attributes of function objects on the
free threaded build.

..

.. date: 2026-07-27-16-29-10
.. gh-issue: 154775
.. nonce: _ISRIk
.. section: Core and Builtins

When matching a complex literal in case statements, an extraneous
``+`` sign (for example, ``1++1j`` or ``1-+1j``) is no longer allowed.
"""

TRACKER = "https://github.com/python/cpython/issues"

for block in ENTRIES.strip().split("\\n..\\n"):
    fields = dict(re.findall(r"^\\.\\. (\\S+): (.+)$", block, re.MULTILINE))
    body = [line for line in block.splitlines() if line and not line.startswith("..")]
    print(f"{TRACKER}/{fields['gh-issue']}   {fields['section']}")
    print("   ", " ".join(body))
    print()
''')


lesson.md(f"""
Three lines of parsing, and now every change in a release is a link to the argument behind it.

## Where the prose is

CPython has more written English in it than most people expect, and the trouble is that it is in five places written for five different readers.

{figure("where-the-prose-is", "a table of five places CPython keeps prose and what each one is good for")}

`InternalDocs/` is the one worth knowing about, because it is the only one written for somebody in your position. It is short, it is honest about being incomplete, and it covers the parts of the interpreter that changed most recently, which are also the parts with the least written about them anywhere else.

The {term("devguide")} is the other one. It is a separate repository, it is what a new contributor is pointed at, and it is where the build instructions, the test instructions and the etiquette live.

## Try it yourself

**One.** Point `reference` at something in a C module, like `math.sin` or `sys.getsizeof`, and read the error. Then work out from the source of `getsourcefile` why it happens.

**Two.** Change the `ast` cell to walk the whole tree with `ast.walk` rather than the top level, and print methods as well as functions. Then count how many of the names in `textwrap.py` start with an underscore.

**Three.** Run the generated file scan again with the `SKIP` set emptied out. Most of what appears is somebody else's package, which is a decent reminder that the convention is not CPython's alone.

**Four.** If you have a checkout, open `Python/bytecodes.c` and find `NOP` at line 148. It is two lines. Then find `TARGET(NOP)` in `Python/generated_cases.c.h` and count how much longer the generated version is.

**Five.** Pick any line in `Lib/textwrap.py` that looks odd to you and run `git blame` on it in a checkout. Follow the commit to its issue. This is the exercise that changes how you read the rest of these lessons.

## What just happened

Your own interpreter can hand you a file and a line range for anything written in Python, which is the same thing the references in this book are.

A file and `ast.parse` and nine lines gets you an index of that file, which is what a jump to definition is underneath.

A generated file says so in its first few lines and usually names the script. About a third of the C in CPython is that, and you saw the count made on a real tree rather than asserted.

`Python/bytecodes.c` is one file that four generated files come from, and you watched four lines added to it become an opcode number and twelve lines of eval loop.

Every commit names an issue, so any line of C leads to the discussion that put it there. That is the answer to nearly every why in this material.

## Where this goes next

That is the toolkit. A build, a debugger, a way to check nothing broke, and a way to read the tree and its history.

The lessons go back to the interpreter now, and they assume all four. When one of them says a number came from `Python/bytecodes.c`, you know what that file is and what happens to it. When one of them says a check was added for a reason, you know how to find the reason.
""")


raise SystemExit(lesson.save())
