#!/usr/bin/env python
"""Z02. How to be lost productively.

The second orientation lesson. Z01 taught the reader to read nine lines of C. This one is
about working out which nine, in a tree of two million lines.

Three ideas carry it. About a third of the C is written by a script and says so in its own
first three lines, so the first skill is closing a file again. A short map covers most of
the questions anyone actually asks. And when the code will not tell you why a line is
there, the history will, through a chain that starts at `Misc/NEWS.d` and ends in an
argument on an issue.

The scavenger hunt needs a copy of the tree, so there is a fetch cell the reader has to
turn on by hand. It is off by default, which keeps the notebook check offline and stops
anybody downloading 36 MB they did not ask for. With it off the same cells print the
answers, so nothing in the lesson is a dead end.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of
them. `just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, YOUR_INSTALL, Lesson
from nbdiagram import Diagrams

lesson = Lesson("z02-being-lost", "z02")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("z02-being-lost").figure

lesson.md(f"""
# Z02. How to be lost productively

{badge}

CPython is about two million lines. You are never going to read them, and nobody who works on it has read them either. What they have is a way of getting from a question to the twenty lines that answer it, usually in under a minute.

{figure("where-we-are", "the eight stages of the pipeline with none of them highlighted")}

That is the whole skill, and it breaks into four smaller ones: knowing roughly what is in each directory, recognising the files that a script wrote so you can close them again, knowing where the code stops explaining itself and the history takes over, and being willing to guess wrong twice before you guess right.

By the end you will have a map that fits on one screen, a rule for spotting {term("generated file", "generated files")} that works every time, and a worked example of tracing one strange line of C back to the argument that put it there.
""")


lesson.md("""
## About the source references

This lesson points at CPython's own source, like this: `Python/bytecodes.c:657-670@v3.15.0rc1#_BINARY_OP_MULTIPLY_INT`.

Read it as four parts: the file, the lines, the release those line numbers belong to, and the name of the thing they are inside.

Every reference is a link, and every one is checked against the pinned source on each change, so a stale reference fails the build instead of sending you somewhere wrong.

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

Most of this lesson is about a source tree rather than a running interpreter, but several of the cells read your own installation, and what they find depends on how it was built. The two cells that count files in your standard library will not match the numbers in the text, and they are not meant to. A framework install, a source build and a Colab image all ship a different set of files, and the shape of the answer is what the lesson is after.
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
## Two million lines, and where they are

Here is the tree, biggest first, with the count of how much of each directory was written by a script rather than a person.

{figure("the-tree", "a table of the main CPython directories with line counts and generated shares")}

Three things are worth noticing.

`Modules` is bigger than `Python` and `Objects` put together, and almost none of it is about how Python works. It is zlib, sqlite, ssl, the curses bindings and the ssl certificate tables, one file per standard library module that needed C. You will visit it when you want to know how `json` is fast, and otherwise never.

`Lib` is bigger than all the C put together, and more than half of that is tests. Tests are worth reading, by the way, because `Lib/test/test_dis.py` and friends are the closest thing to a specification of the parts of CPython nobody documented.

`Python`, `Objects` and `Include` are where this course lives. About 425,000 lines between them, which is still far too many, and that is why the rest of this lesson exists.

{lesson.claim("your own machine already has the Lib half of that tree on disk, a few hundred thousand lines of it, and you can find and count it without downloading anything")}. The next cell does it.
""")


lesson.code(
    """
import pathlib
import sysconfig

stdlib = pathlib.Path(sysconfig.get_paths()["stdlib"])
sources = [path for path in stdlib.rglob("*.py") if "site-packages" not in path.parts]

print("your standard library is at:", stdlib)
print("files of Python:", len(sources))
print("lines of Python:", sum(len(path.read_bytes().splitlines()) for path in sources))
""",
    varies=YOUR_INSTALL,
    quiet=True,
)


lesson.md(f"""
## A third of the C, nobody typed

This is the single most useful thing in the lesson, so it comes early.

{figure("generated-share", "a bar chart of the generated share of each directory")}

{lesson.claim("about a third of the C in the tree, 371,643 lines of it across 206 files, is produced by a script when CPython is built", unobservable="the count is over a checkout of CPython, and this lesson deliberately does not download one")}. If you open one of them looking for an explanation you will not find one, because you are reading the output of a program rather than the program.

The rule for spotting them is easy, and CPython is good about it: {lesson.claim("a generated file says so in its own first three lines, and usually names both the script that wrote it and the file it was written from, which is enough to find every one of them in your own standard library")}.

```c
// This file is generated by Tools/cases_generator/tier1_generator.py
// from:
//   Python/bytecodes.c
// Do not edit!
```

```c
// @generated by pegen from python.gram
```

```c
// File automatically generated by Parser/asdl_c.py.
```

```python
# This file is generated by Tools/cases_generator/py_metadata_generator.py
# from:
#   Python/bytecodes.c
```

Those are the first lines of {cite("Python/generated_cases.c.h:1-4@v3.15.0rc1#tier1_generator")}, {cite("Parser/parser.c:1-3@v3.15.0rc1#pegen")}, {cite("Python/Python-ast.c:1-3@v3.15.0rc1#asdl_c")}, and {cite("Lib/_opcode_metadata.py:1-3@v3.15.0rc1#py_metadata_generator")}.

You have generated files on your own machine, in the standard library, and you can find them with the same rule. The next cell does exactly that.
""")


lesson.code(
    '''
MARKERS = ("generated", "do not edit", "autogenerated")


def looks_generated(path):
    """CPython says so, in the first three lines of every file a script writes."""
    head = path.read_text(encoding="utf-8", errors="replace").split("\\n")[:3]
    return any(marker in " ".join(head).lower() for marker in MARKERS)


generated = sorted(path for path in sources if looks_generated(path))

print("of your", len(sources), "files,", len(generated), "were written by a script")
for path in generated[:6]:
    print("   ", path.relative_to(stdlib))
''',
    varies=YOUR_INSTALL,
    quiet=True,
)


lesson.md(f"""
Most of those are the codec tables in `encodings/`, which is fair enough, because nobody was going to type out four hundred character mappings by hand.

One of them is more interesting. {lesson.claim("_opcode_metadata.py in your own standard library is generated from Python/bytecodes.c, the same input as the biggest generated C file in the tree")}, and it is the table the `dis` module and everything built on it reads, including `pyxray`.
""")


lesson.code(
    """
for path in generated:
    if path.name == "_opcode_metadata.py":
        print(path)
        print()
        print(path.read_text().split("\\n\\n")[0])
        break
else:
    print("not in this build, which happens on some installs")
""",
    differs="This file is generated from Python/bytecodes.c, so it lists the specializations your version has. On 3.14 it is a plain dict rather than a frozendict, and the list is shorter, because 3.15 added several.",
)


lesson.md(f"""
So the file on your laptop and `Python/generated_cases.c.h` in the source tree are two outputs of one program, reading one input: `Python/bytecodes.c`. That file is the source of truth for what every {term("instruction")} does, and it is the one you should read.

{figure("where-not-to-look", "a table of seven generated files and the files to read instead")}

The last row is worth a moment. In Z01 you read `list_append_impl` and may have wondered where its arguments get parsed, since the function takes a `PyListObject *` and a `PyObject *` and Python calls do not arrive looking like that. The answer is a tool called {term("Argument Clinic")}, and the input it works from is a comment sitting directly above the function {cite("Objects/listobject.c:1221-1233@v3.15.0rc1#list_append_impl")}.

```c
/*[clinic input]
@critical_section
list.append

     object: object
     /

Append object to the end of the list.
[clinic start generated code]*/

static PyObject *
list_append_impl(PyListObject *self, PyObject *object)
/*[clinic end generated code: output=78423561d92ed405 input=122b0853de54004f]*/
```

The comment is the source. The signature underneath it is generated, and so is the argument parsing, the docstring and the method table entry, which all land in {cite("Objects/clinic/listobject.c.h:1-3@v3.15.0rc1#clinic")}. This is why so many CPython functions are named `something_impl`: the plain name belongs to the generated wrapper.
""")


lesson.md(f"""
## The same instruction, written twice

Here is what a generated file costs you, on the instruction that runs `6 * 7`.

{figure("two-versions", "the hand written and generated versions of one instruction side by side")}

This is the version a person wrote {cite("Python/bytecodes.c:657-670@v3.15.0rc1#_BINARY_OP_MULTIPLY_INT")}.

```c
pure op(_BINARY_OP_MULTIPLY_INT, (left, right -- res, l, r)) {{
    PyObject *left_o = PyStackRef_AsPyObjectBorrow(left);
    PyObject *right_o = PyStackRef_AsPyObjectBorrow(right);
    assert(PyLong_CheckExact(left_o));
    assert(PyLong_CheckExact(right_o));
    assert(_PyLong_BothAreCompact((PyLongObject *)left_o, (PyLongObject *)right_o));

    STAT_INC(BINARY_OP, hit);
    res = _PyCompactLong_Multiply((PyLongObject *)left_o, (PyLongObject *)right_o);
    EXIT_IF(PyStackRef_IsNull(res));
    l = left;
    r = right;
    INPUTS_DEAD();
}}
```

Fourteen lines, and only two of them do anything: take the two operands off the stack, multiply them. The rest is assertions and bookkeeping. Note that this is not quite C. `pure op(...)` is not a C construct, `(left, right -- res, l, r)` is a {term("stack effect")} written in a small language of CPython's own, and `INPUTS_DEAD()` is an instruction to the code generator rather than to the compiler.

Here is the beginning of what comes out the other end {cite("Python/generated_cases.c.h:556-572@v3.15.0rc1#BINARY_OP_MULTIPLY_INT")}.

```c
TARGET(BINARY_OP_MULTIPLY_INT) {{
    #if _Py_TAIL_CALL_INTERP
    int opcode = BINARY_OP_MULTIPLY_INT;
    (void)(opcode);
    #endif
    _Py_CODEUNIT* const this_instr = next_instr;
    (void)this_instr;
    frame->instr_ptr = next_instr;
    next_instr += 6;
    INSTRUCTION_STATS(BINARY_OP_MULTIPLY_INT);
    static_assert(INLINE_CACHE_ENTRIES_BINARY_OP == 5, "incorrect cache size");
```

That goes on for about sixty lines, with the type guards spliced in, the deoptimisation jumps written out, and the cache entries skipped by hand. All of it is correct and none of it is what you wanted to know.

Both files contain the string `BINARY_OP_MULTIPLY_INT`. Twenty five files in the tree contain the string `BINARY_OP`. If you grep for it and open the first hit, you have maybe a one in five chance of landing on the file that was written by a person.
""")


lesson.md(f"""
## A map that fits on one screen

Most questions about CPython are one of about seven questions wearing a hat.

{figure("the-map", "a table of seven common questions and the file that answers each")}

That is small enough to keep in your head, and {lesson.claim("a map of about ten keyword rules is enough to answer most questions about where in CPython to look, with one row left over for the ones it misses")}. The next cell turns it into something you can ask.

It is a keyword lookup and nothing cleverer, so it will miss. The point is that a map this small covers most of what you will want, and the last row is the escape hatch for everything else.
""")


lesson.code('''
MAP = [
    ("list dict tuple int str set type", "Objects/<name>object.c, and its struct in Include/"),
    ("instruction opcode bytecode dispatch", "Python/bytecodes.c, and nowhere else"),
    ("scope global nonlocal closure name", "Python/symtable.c"),
    ("compile codegen emit constant fold", "Python/codegen.c, then Python/flowgraph.c"),
    ("token tokenize indent lexer", "Parser/lexer/, and Grammar/Tokens"),
    ("grammar parse syntax tree ast", "Grammar/python.gram, and Parser/Python.asdl"),
    (
        "gc garbage cycle collect collected collector refcount freed",
        "Python/gc.c, and Include/refcount.h",
    ),
    ("malloc arena pool allocator memory", "Objects/obmalloc.c"),
    ("frame call stack traceback", "Python/ceval.c, and pycore_interpframe_structs.h"),
    ("import module package finder", "Lib/importlib/, and Python/import.c"),
]


def where(question):
    """The first place to open for a question, from a map that fits on one screen."""
    asked = set(question.lower().replace("?", " ").replace(",", " ").split())
    found = [answer for keys, answer in MAP if asked & set(keys.split())]
    return found or ["nothing on the map, so try InternalDocs/structure.md"]


for question in [
    "where does a dict get its type?",
    "what does the BINARY_OP opcode do",
    "why is my object not collected",
    "what colour should the bikeshed be",
]:
    print(question)
    for answer in where(question):
        print("   ", answer)
    print()
''')


lesson.md(f"""
## Which half of the standard library is C

There is one naming rule that saves more time than the rest of the map put together, and it is written down in {cite("InternalDocs/structure.md:7-14@v3.15.0rc1#layout")}.

A standard library module called `thing` is `Lib/thing.py`. If it has a C accelerator, the accelerator is `Modules/_thing.c` and it is importable as `_thing`. The tests are `Lib/test/test_thing.py` and the documentation is `Doc/library/thing.rst`.

That is enough to find the C behind any module in the standard library without looking anything up. `json` is fast because of `Modules/_json.c`. `datetime` has `Modules/_datetimemodule.c` behind it. `pickle` has `Modules/_pickle.c`.

{lesson.claim("a standard library module written in Python with a C accelerator behind it is called thing with the accelerator called _thing, and the running interpreter names both halves of every pair")}, so you can check the rule holds without leaving the notebook.
""")


lesson.code(
    """
import sys

builtin = set(sys.builtin_module_names)
everything = set(sys.stdlib_module_names)
pairs = sorted(name for name in everything if not name.startswith("_") and "_" + name in everything)

print("modules in the standard library:", len(everything))
print("compiled into this binary:      ", len(builtin))
print("Python outside, C inside:       ", len(pairs))
print()
print(pairs)
""",
    varies="How many modules are compiled into the binary is a build choice rather than a version. A framework install has far fewer than a source build, so the middle number moves a lot.",
)


lesson.md(f"""
Forty seven pairs, which is a lot more than most people expect.

The middle number is the one that will surprise you, because it depends entirely on how your interpreter was built and not on anything about Python. A module written in C can be linked into the executable, in which case it turns up in `sys.builtin_module_names` and has no file at all, or it can be built as a shared library that gets loaded on import, in which case it has a `.so` next to the standard library. Same source file either way.

The next cell shows all three cases at once, and {lesson.claim("whether a module written in C is linked into the interpreter or loaded from a file beside it is a build choice rather than a fact about Python, so the same module can have a file on one install and none on another")}. Run it on two different installations of the same Python version and the middle line can easily change.
""")


lesson.code(
    """
import _json
import json

for module in (json, _json, sys):
    location = getattr(module, "__file__", "no file, it is inside the binary")
    print(f"{module.__name__:6} {location}")
""",
    varies="Whether _json is a separate file or lives inside the binary is that same build choice, so this line differs between two installs of the same version.",
)


lesson.md("""
## Getting a copy of the tree

Everything so far has run against your own installation. The next part needs the source, and there is no way around that.

The good news is that you do not need all of it. A partial clone of seven directories at the tag this lesson was written against is about 36 MB and takes about fifteen seconds, which is fine even in a browser tab. It skips the history, which is why it is that small.

The cell below is off by default. Change `FETCH` to `True` if you want to do the hunt for real. If you leave it alone, the cells after it print the answers instead, so you can read straight through.
""")


lesson.code('''
import pathlib
import subprocess

FETCH = False  # change this to True to download about 36 MB of CPython

TREE = pathlib.Path("cpython")
TAG = "v3.15.0rc1"
PARTS = ["Grammar", "Include", "InternalDocs", "Misc", "Objects", "Parser", "Python"]


def fetch():
    """Seven directories of CPython at the pinned tag, without the history or the rest."""
    url = "https://github.com/python/cpython"
    clone = ["git", "clone", "--quiet", "--depth", "1", "--branch", TAG]
    clone += ["--filter=blob:none", "--sparse", url, str(TREE)]
    subprocess.run(clone, check=True)

    sparse = ["git", "-C", str(TREE), "sparse-checkout", "set", *PARTS]
    subprocess.run(sparse, check=True, capture_output=True)


if FETCH and not TREE.exists():
    fetch()

if TREE.exists():
    print("the tree is at", TREE.resolve())
else:
    print("not fetched, so the next cell prints the answers instead")
''')


lesson.md(f"""
## Six questions

Every one of these is answerable in under a minute with grep and the map. Try them yourself before you run the cell, either in the clone above or on GitHub, which lets you search a repository without cloning it.

1. What number does the {term("small integer cache")} stop at, and which file writes it down?
2. Which file says what `BINARY_OP_MULTIPLY_INT` does?
3. Which line gives the `int` type its name?
4. Which two files is `Parser/parser.c` generated from?
5. How many slots does a list get the first time it grows?
6. Which page of `InternalDocs` explains `_PyStackRef`, and which struct does it point at?

The cell runs a plain `grep -rn` over the clone if you fetched it, and falls back to the answers if you did not.
""")


lesson.code('''
INCLUDE = ["*.c", "*.h", "*.in", "*.md", "*.gram"]

QUESTIONS = [
    (
        "What number does the small integer cache stop at?",
        "define _PY_NSMALLPOSINTS",
        "Include",
        0,
        "pycore_runtime_structs.h:97: #define _PY_NSMALLPOSINTS 1025",
    ),
    (
        "Which file says what BINARY_OP_MULTIPLY_INT does?",
        "op(_BINARY_OP_MULTIPLY_INT",
        "Python",
        0,
        "bytecodes.c:657: pure op(_BINARY_OP_MULTIPLY_INT, ...)",
    ),
    (
        "Which line gives the int type its name?",
        \'"int",\',
        "Objects/longobject.c",
        0,
        \'longobject.c:6648: "int", /* tp_name */\',
    ),
    (
        "Which two files is Parser/parser.c generated from?",
        "regen-pegen:",
        "Makefile.pre.in",
        8,
        "Makefile.pre.in:2046: Grammar/python.gram and Grammar/Tokens",
    ),
    (
        "How many slots does a list get the first time it grows?",
        "new_allocated = ",
        "Objects/listobject.c",
        0,
        "listobject.c:129: four, and Z01 checked that against a real list",
    ),
    (
        "Which page explains _PyStackRef, and which struct does it point at?",
        "pycore_stackref",
        "InternalDocs",
        0,
        "stackrefs.md:8: it points at Include/internal/pycore_stackref.h",
    ),
]


def hunt(pattern, path, *, after=0):
    """grep the tree, trimmed to the first few lines so an answer fits on the screen."""
    command = ["grep", "-rn", "-A", str(after), *(f"--include={glob}" for glob in INCLUDE)]
    found = subprocess.run(
        [*command, pattern, str(TREE / path)], capture_output=True, text=True
    ).stdout.splitlines()
    return [line.replace(f"{TREE}/", "") for line in found[: 3 + after]]


for number, (question, pattern, path, after, answer) in enumerate(QUESTIONS, start=1):
    print(f"{number}. {question}")
    for line in hunt(pattern, path, after=after) if TREE.exists() else [answer]:
        print("   ", line)
    print()
''')


lesson.md(f"""
## When the code will not tell you why

Sooner or later you will find a line that is correct, that you understand, and that makes no sense. A cast that should not be needed. A branch for a case that cannot happen. A constant with no explanation.

The code will not tell you why it is there, but the history will.

{figure("the-trail", "the chain from a line of C to the issue that explains it")}

The command is `git log -S`, and the `-S` is the whole trick. It does not search commit messages, it searches for commits where the number of occurrences of a string in the file changed. So it finds the commit that added your line, skipping every reformat and every unrelated change to the same file.

```
git log -S'_PY_NSMALLPOSINTS' --oneline -- Include/internal/
```

The commit subject will start with `gh-` and a number, because CPython requires it. That number is both an issue and a search key for the pull request, and the two are different documents. The pull request has the review. The issue has the argument, and the argument is usually what you wanted.

If you do not have the history, `Misc/NEWS.d` gets you to the same place. It is one small file per user visible change, kept forever, filed by release, and {lesson.claim("each entry carries the issue number in its metadata, which is the link from a line of code to the argument about why the line is there")}.
""")


lesson.code('''
ENTRY = """\\
.. date: 2024-12-20-12-25-16
.. gh-issue: 127705
.. nonce: WmCz1z
.. section: Core and Builtins

Adds stackref debugging when ``Py_STACKREF_DEBUG`` is set. Finds all
double-closes and leaks, logging the origin and last borrow.
"""


def trail(entry):
    """Pull the two links out of one Misc/NEWS.d entry, which is where the trail starts."""
    fields = dict(
        line.removeprefix(".. ").split(": ", 1)
        for line in entry.splitlines()
        if line.startswith(".. ") and ": " in line
    )
    number = fields["gh-issue"]
    body = " ".join(line for line in entry.splitlines() if not line.startswith(".. "))
    return {
        "landed": fields["date"][:10],
        "section": fields["section"],
        "says": body.strip(),
        "the issue": f"https://github.com/python/cpython/issues/{number}",
        "its pull requests": f"https://github.com/python/cpython/pulls?q=gh-{number}",
    }


for key, value in trail(ENTRY).items():
    print(f"{key:18} {value}")
''')


lesson.md(f"""
## Where InternalDocs helps, and where it stops

There is a directory in the tree called `InternalDocs` that almost nobody outside the core team knows about. Eighteen markdown files, written by the people who maintain the code, about the parts that are hard.

{figure("internaldocs", "a table of what InternalDocs covers and what it does not")}

It is the best thing in the tree, and it is also incomplete on purpose. It gets written when somebody doing the work decides an explanation would have saved them a week. So the coverage tracks which parts have been rewritten recently rather than which parts are hardest for a newcomer.

That is why there is a page on the {term("JIT")}, which is two years old, and no page on the {term("tokenizer")}, which has been there since the beginning. Start with `InternalDocs/README.md` and be ready for the answer to be that nobody wrote it down.
""")


lesson.md(f"""
## The boss: where did `_PyStackRef` come from

Here is a real one. If you read almost any instruction in `Python/bytecodes.c`, including the fourteen lines above, you will hit this type.

```c
PyObject *left_o = PyStackRef_AsPyObjectBorrow(left);
```

The values on the {term("value stack", "evaluation stack")} are not `PyObject *` any more. They are `_PyStackRef`, and you have to convert to get at the object. That is a big change to the most performance sensitive code in the interpreter, and the definition tells you almost nothing about why {cite("Include/internal/pycore_structs.h:66-72@v3.15.0rc1#_PyStackRef")}.

```c
typedef union _PyStackRef {{
#if !defined(Py_GIL_DISABLED) && defined(Py_STACKREF_DEBUG)
    uint64_t index;
#else
    uintptr_t bits;
#endif
}} _PyStackRef;
```

A union with one member in it. That is a wrapper rather than a type, which is a hint that the point is what you are not allowed to do with it rather than what it holds.

So run the trail on it. `git log -S'_PyStackRef' --oneline --reverse` gives `22b0de2755ee` from June 2024, subject "gh-117139: Convert the evaluation stack to stack refs (#118450)". Note that this is not where the file came from: `Include/internal/pycore_stackref.h` was added two months earlier by `dc6b12d1b2ea`, "gh-117139: Add header for tagged pointers (GH-118330)", 200 lines and nothing using them yet. That is normal, because a `-S` search finds where a string first appears, which is often the commit that switched something on rather than the commit that built it, and both of these carry the same issue number anyway.

Open [python/cpython#117139](https://github.com/python/cpython/issues/117139), "Set up tagged pointers in the evaluation stack", opened March 2024 by Ken Jin, labelled `topic-free-threading`. Three sentences, which is what the exercise asked for:

The free threaded build cannot use ordinary reference counting on the evaluation stack, because every push and pop of a shared object becomes contention between threads, so PEP 703 needs deferred reference counting and deferred reference counting needs somewhere to record that a reference is deferred. Tagging spare bits of the pointer is that somewhere, and the evaluation stack was chosen as the only place to do it, so that the change would not leak into the C API. The same tag bits then turned out to pay for themselves in the ordinary build too, by letting small integers live directly in the stack slot instead of on the heap.

Now read the issue body next to the union above. The proposal was a type called `PyTaggedObject`, a union of a `PyObject *` and a `uintptr_t`. What shipped is called `_PyStackRef` and has no `PyObject *` member at all, which is exactly the point: if you cannot name the pointer you cannot accidentally use it without going through a conversion. That change happened during review, and it is written down nowhere in the source. The nearest thing to an explanation is {cite("InternalDocs/stackrefs.md:1-4@v3.15.0rc1#_PyStackRef")}, which was written afterwards.

Code tells you what. Commit messages tell you when. Issues tell you why, and they are the only ones that do.
""")


lesson.md(f"""
## How much of this you actually need

The eleven lessons in this repository so far cite CPython's source ninety nine times. Those ninety nine citations land on forty four files.

{figure("forty-four-files", "a bar chart of how many files each directory contributed")}

Forty four, out of 1,154 C and header files. The same few files answer nearly everything, because the interesting parts of CPython are concentrated and the bulk is codec tables and module bindings.

So the map is smaller than the tree suggests, and getting good at this is mostly getting confident about closing files quickly.
""")


lesson.md("""
## Try it yourself

**One.** Run the generated file detector over your own `Lib` directory and pick one of the results that is not an encoding table. Find the tool named in its header. Is that tool in your installation, or only in the source tree?

**Two.** Pick any three modules from the forty seven accelerator pairs. For each one, write down the path of the C file you expect, using only the naming rule. Then check them.

**Three.** `sys.builtin_module_names` on this machine gave you some number. Find another Python on the same machine, or another Colab runtime, and compare. If they differ, the difference is a build decision, and `Modules/Setup` and `configure.ac` are where it was made.

**Four.** Take the `where()` map and add three rows for questions you have actually had. If you cannot name the file, that is the useful outcome, and searching for it is the exercise.

**Five.** Fetch the tree, then find a line in `Objects/listobject.c` you do not understand. Run `git log -S` on it. You will need the full history for that, so clone without `--depth`, and expect it to be slow. Follow the chain to the issue and see whether it was worth it.
""")


lesson.md("""
## What just happened

You learned four things and none of them were about the C language.

About a third of the C in CPython is written by a script, and every generated file says so in its first three lines. Closing those files quickly is the single biggest difference between someone who can find things in this tree and someone who cannot.

Nearly every question anyone asks about CPython is answered in one of about ten files, and the map fits on one screen. `Objects/<name>object.c` for a type, `Python/bytecodes.c` for an instruction, `Python/symtable.c` for a name, `Python/gc.c` for a cycle.

The standard library has a naming rule that tells you where the C behind any module is, without looking anything up, and you checked it against forty seven pairs on your own machine.

And when a line makes no sense, the reason is in the history rather than the code. `git log -S` finds the commit, the commit names the issue, and the issue is where somebody explained themselves. You did that for `_PyStackRef` and came out with three sentences about free threading that the source alone would never have given you.
""")


lesson.md("""
## Where this goes next

That is the ramp finished. Z01 got you reading C, Z02 got you finding it, and between them you should be able to click any source reference in this material and get something out of it.

Everything from here on is a lesson about one box on the napkin from T10, and every one of them will point at the tree you now know how to search.
""")


raise SystemExit(lesson.save())
