#!/usr/bin/env python
"""B02. Watching the interpreter stop.

The second lesson of the build part, and the twelfth overall. It is the one lesson in the
project that a reader cannot run all of, and the shape of it is built around that fact rather
than apologising for it.

The first half is pdb, which everybody already has, driven from a written list of commands so
that a debugging session becomes something you can read rather than something you have to
perform. The second half is gdb, which most readers do not have, so the two sessions were run
in the debug image this project publishes and committed under `debugger/`. The lesson lays
them out a few commands at a time with its own paragraphs in between.

The payoff is the count. Seventeen C frames for four Python calls, with exactly one
`_PyEval_EvalFrameDefault` among them, is T07's central claim sitting somewhere a reader can
count it. The immortal reference count is T08's, visible as a raw number in memory and
checkable from the browser with `sys.getrefcount` in the same lesson.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file. The transcripts
come from `gdbrec`, so nothing gdb printed is retyped here.
"""

from gdbrec import program_of, show
from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("b02-the-debugger", "b02")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("b02-the-debugger").figure

#: The transcripts this lesson reads. Only arm64 exists so far, because the machine that
#: recorded them is an arm64 one and a backtrace is not portable between architectures.
STACKS = "b02-the-two-stacks"
CRASH = "b02-where-a-crash-came-from"
ARCH = "arm64"

lesson.md(f"""
# B02. Watching the interpreter stop

{badge}

Every lesson so far has watched Python from inside Python. You printed a code object, you counted references, you walked the frame chain. All of it was the interpreter describing itself while it was running.

This lesson stops it instead.

{figure("where-we-are", "the eight stages of the pipeline with the last one highlighted")}

Stopping a program in the middle and looking at it is the oldest tool there is, and it comes in two halves. One half you already have and can run right now. The other half needs a debug build and a C debugger, so it was run for you and written down, command by command, and you can read it without installing anything.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Lib/pdb.py:488@v3.15.0rc1#Pdb`.

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
## The debugger you already have

`pdb` ships with Python and has since 1992. Most people meet it by typing `breakpoint()`, getting a `(Pdb)` prompt, and then not knowing what to type next.

The prompt is the problem. A debugging session at a prompt is something you perform once and then cannot show anybody, which is why so much debugging knowledge is passed around as folklore.

So do it the other way round. {lesson.claim("pdb reads its commands from whatever you hand it as standard input, so a debugging session can be written down in advance, run, and read back later")}, and the session below is a list of six strings. The class takes the streams as arguments: {cite("Lib/pdb.py:488@v3.15.0rc1#Pdb")}.

The program is four functions deep and ends in one multiplication, which is the same program the gdb sessions further down use.
""")


lesson.code(
    '''
import io
import pdb
from pathlib import Path

source = """def double(n):
    return n * 2


def middle(n):
    return double(n)


def top():
    return middle(21)


print(top())
"""

program = Path("program.py")
program.write_text(source)

commands = ["break double", "continue", "where", "args", "list", "continue"]

typed = io.StringIO("\\n".join(commands) + "\\n")
printed = io.StringIO()

session = pdb.Pdb(stdin=typed, stdout=printed, readrc=False)
session.run(compile(source, str(program), "exec"), {"__name__": "__main__"})

print(printed.getvalue())

program.unlink()
''',
    varies="The path in front of every line number is wherever this notebook is running, so it is different for everybody. The line numbers themselves are not.",
)


lesson.md(f"""
Read that as six answers rather than as a wall of text.

`break double` picks a function. `continue` runs until it is called. `where` prints the call stack, innermost first, and there are four Python frames in it because there were four Python calls. `args` prints the arguments of the frame you are stopped in, and `n` is 21. `list` shows the source around the stopping point, with `B->` marking the line the breakpoint is on.

That is the whole vocabulary. Six commands, and you have just done a real debugging session and can hand it to somebody else as a file.

## What a debugger actually is

A debugger sounds like it must be doing something special. It is not. {lesson.claim("pdb is ordinary Python that asks the interpreter to call it back on every function call, line and return, which is a hook any program can install")}, and the hook is one function call: {cite("Lib/bdb.py:232-236@v3.15.0rc1#start_trace")}.

Here is a debugger in a handful of lines. It does one thing, which is print the calls it was asked to watch, and there is nothing missing from it except features.
""")


lesson.code("""
import sys

# The hook fires on every call anywhere in the process, and in a notebook that includes
# Jupyter's own, so this only prints the three functions the cell is about.
WATCHING = {"top", "middle", "double"}


def watch(frame, event, arg):
    if frame.f_code.co_qualname in WATCHING:
        print(f"call    {frame.f_code.co_qualname:8}  line {frame.f_lineno}")
    return None


def double(n):
    return n * 2


def middle(n):
    return double(n)


def top():
    return middle(21)


sys.settrace(watch)
top()
sys.settrace(None)
""")


lesson.md(f"""
Three calls, in the order they happened. `pdb` is that with a prompt attached, a list of breakpoints, and the good sense to return itself so it keeps getting called.

The name check is the only thing in there that is not about debugging. A trace hook is global: once it is installed the interpreter calls it for every function anywhere, so without the check you would also watch whatever Jupyter does between one line of this cell and the next.

In 3.14 and later, pdb prefers {term("monitoring events", "sys.monitoring")} when it can get it and falls back to `sys.settrace` otherwise, which is the `if` in the lines cited above. The idea is the same either way: the interpreter offers to tell you when things happen, and a debugger is whatever you do with that offer.

## What none of this can see

Everything above lives inside the interpreter, which is exactly why it stops where it does.

{figure("four-ways-to-look", "a table of four debugging tools and what each one can see")}

`pdb` can tell you that `double` called `n * 2`. It cannot tell you what happened next, because what happened next was C. It also cannot help you at all if the process dies outright, because a dead process has no Python left in it to run a debugger written in Python.

For those two questions you need a debugger that works on the process rather than in it. That means {term("gdb")}, and gdb means a debug build, and a debug build means either twenty minutes with a compiler or the container from B01.

## Somebody already ran it

So it was run for you.

Both sessions below were run in the debug image this project publishes, pinned by digest, and every line gdb printed was written down and committed under `debugger/`. They are checked the same way the rest of this material is: a job re runs both sessions in the same image and compares them line by line, with addresses allowed to move and nothing else. If a future CPython changes the shape of the stack, that job goes red and this lesson gets rewritten.

You do not need any of it to read what follows. If you want to run it yourself, `just build-gdb` in a checkout will, and the exercises at the end say how to do it by hand.

## Two stacks, one moment

The program is deliberately dull. Four functions, one multiplication, one `print`.
""")


lesson.md(f"""
```python
{program_of(STACKS, ARCH)}
```
""")


lesson.md(f"""
The multiplication is the target. `n * 2` in Python is `PyNumber_Multiply` in C, {cite("Objects/abstract.c:1176@v3.15.0rc1#PyNumber_Multiply")}, and stopping there stops the interpreter at a moment that can be described from both sides at once.

Getting there takes four commands, and the first one is not obvious.
""")


lesson.md(show(STACKS, ARCH, first=1, last=4))


lesson.md(f"""
The temporary breakpoint on `pymain_run_file` is there because of something worth knowing on its own. By the time the interpreter reaches your file it has already run a great deal of Python, most of it `site.py` setting up the import system, and a lot of that Python multiplies things. Break on `PyNumber_Multiply` first and you stop inside `posixpath.dirname` before your program has started. So the session stops once at the point the interpreter is about to run your file, {cite("Modules/main.c:446@v3.15.0rc1#pymain_run_file")}, and only then sets the real breakpoint.

Now the interpreter is frozen, holding 21 and 2, and there are two ways to ask it what it is doing.
""")


lesson.md(show(STACKS, ARCH, first=5, last=5))


lesson.md(f"""
Seventeen frames. Read from the bottom: `main` calls `Py_BytesMain` calls `pymain_main`, down through the file running machinery, into `PyEval_EvalCode`, and then into the eval loop.

Now count the eval loop frames. There is exactly one.

{figure("two-stacks", "seventeen C frames beside four Python frames")}

{lesson.claim("four nested Python calls run inside a single _PyEval_EvalFrameDefault frame, so the C stack does not grow one frame per Python call", unobservable="counting C frames means attaching a debugger to the process, and there is no second process in a browser tab")}. That is T07's whole point, and here it is as a number you can count rather than a claim you have to take.

The other side of the same instant looks like this.
""")


lesson.md(show(STACKS, ARCH, first=6, last=6))


lesson.md("""
Four frames, and they are the four functions in the program. This is the same chain you walked from the inside in T07 by following `f_back`, except that here nothing in the program is cooperating. The process is stopped and gdb is reading its memory.

Two answers to one question, both true. C says seventeen, Python says four, and neither is a simplification of the other. The C stack is where the interpreter is. The Python stack is what the interpreter is doing.

The last two commands go one level further down, into a single object.
""")


lesson.md(show(STACKS, ARCH, first=7, last=8))


lesson.md(f"""
`v` is the left operand, the 21. Every Python object starts with a header, and the first thing in that header is a pointer to its type, so `((PyObject *) v)->ob_type->tp_name` reads the string `"int"` straight out of memory. Nothing asked the object what it was. The answer was already lying there.

The second number is the good one. `3221225472` is not a count of anything. It is 3 times 2 to the 30, which CPython uses to mark an object as {term("immortal object", "immortal")}: {cite("Include/refcount.h:47@v3.15.0rc1#_Py_IMMORTAL_INITIAL_REFCNT")}.

{lesson.claim("small integers report a reference count of 3221225472, which is a marker meaning never free this rather than a count of references")}, and you can check the same number from a browser tab right now.
""")


lesson.code("""
import sys

print("sys.getrefcount(21) =", sys.getrefcount(21))
print("3 << 30            =", 3 << 30)
print("the same number:", sys.getrefcount(21) == 3 << 30)
""")


lesson.md(f"""
The same value, from two completely different places. One came out of a stopped process on another machine with a C expression, the other came from a function call in your browser. That agreement is the point of this lesson: the debugger is not showing you a different Python, it is showing you the same one from further back.

## Where py-bt comes from

`py-bt` looks like magic and is not. gdb loads a Python script that CPython ships in its own tree, {cite("Tools/gdb/libpython.py:2122-2131@v3.15.0rc1#PyBacktrace")}, and that script does what you would do by hand.

{figure("where-py-bt-comes-from", "five steps from the C stack to a Python filename and line number")}

It scans the C stack for frames named `_PyEval_EvalFrameDefault`, {cite("Tools/gdb/libpython.py:1778-1791@v3.15.0rc1#is_evalframe")}, reads the `frame` argument out of each one, and follows it into a `_PyInterpreterFrame`, {cite("Include/internal/pycore_interpframe_structs.h:29-53@v3.15.0rc1#_PyInterpreterFrame")}. From there `f_executable` is the code object, and the code object has the filename, the function name and the table that turns an instruction offset into a line number.

Five pointer hops. Somebody wrote them down once, and now everybody gets `py-bt`.

## Where a crash came from

The second session is about the case pdb cannot reach at all.
""")


lesson.md(f"""
{figure("two-ways-to-stop", "an exception compared with a segfault")}

An exception is a thing the interpreter builds and hands back to you, with a traceback that names the file and the line. A {term("segmentation fault")} is not. The kernel takes the process away mid instruction, and there is no interpreter left to explain anything. Nothing prints. The shell reports 139 and you are on your own.

Pure Python does not usually get you there, which is why the program below has to work at it. `ctypes` is the door out of the language, and past that door a mistake is a crash rather than an exception. Extension modules live on the other side of the same door, so this is a small version of what a bug in one looks like from outside.
""")


lesson.md(f"""
```python
{program_of(CRASH, ARCH)}
```
""")


lesson.md(show(CRASH, ARCH, first=1, last=2))


lesson.md("""
`SIGSEGV` and an address, and then a C stack whose top frame does not even have a name, because it is inside the C library where there is nothing to unwind with. That is roughly what a crash report from a C extension looks like when it reaches you, and it is not much to go on.

Then one command.
""")


lesson.md(show(CRASH, ARCH, first=3, last=4))


lesson.md("""
A filename, a line number and a function name, out of a process that is no longer running. `py-list` then reads the Python source around that line out of the same stopped process.

That is the whole reason this material bothers with a debug build. Everything else in these twelve lessons could be done from a browser tab. This could not, and it is also the thing you will actually want on the worst day of a project.

## Try it yourself

**One.** Change the command list in the pdb cell. Try `step` instead of `continue`, or add `p n * 2` after `args` to evaluate an expression at the stopping point. Every command is documented in the `pdb` module docs.

**Two.** Put `print(frame.f_locals)` inside `watch` in the four line tracer and run it again. You now have a tool that prints every argument of every call in your program, which is about fifty lines short of a profiler.

**Three.** Return `watch` from `watch` instead of `None` and see how much more it prints. That one line is the difference between tracing calls and tracing lines, and it is why real tracers are careful about what they return.

**Four.** Run the two stacks session yourself: `docker run --rm -it --cap-add=SYS_PTRACE --security-opt seccomp=unconfined ghcr.io/tamnd/cpython-internals/cpython:debug gdb -q /usr/local/bin/python3`. Write the program to a file first, and try `py-locals` and `py-up`, which this lesson did not use.

**Five.** Take the crash program and wrap the `ctypes` call in `try` and `except Exception`. Run it again and watch the crash go straight through the handler, because there is no exception involved and nothing for it to catch.

## What just happened

You have a debugger already, it takes its commands from a list as happily as from a keyboard, and a session written down is a session you can share.

pdb is not special. It is a callback the interpreter offers to anybody, and a four line version of it fits in a cell.

A stopped interpreter has two stacks, and both are honest. Seventeen C frames and four Python frames described the same instant, with one `_PyEval_EvalFrameDefault` covering all four Python calls.

The object header is right there in memory. The type name and the reference count of the number 21 came out of a C expression, and one of those numbers is a marker meaning immortal rather than a count, which you checked yourself from a browser.

`py-bt` is five pointer hops that somebody wrote down once, in a file CPython ships in its own tree.

And when a process dies with no traceback at all, that same file gets you the Python line that did it.

## Where this goes next

B03 is the test suite, which is the other thing a build gives you. CPython ships about six hundred thousand lines of tests, and knowing how to run one of them against a change you made is what turns reading this material into being able to alter CPython.
""")


raise SystemExit(lesson.save())
