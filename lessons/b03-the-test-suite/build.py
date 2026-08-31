#!/usr/bin/env python
"""B03. Asking CPython whether it still works.

The third lesson of the build part, and the thirteenth overall. B01 got the reader a build and
B02 got them a debugger, and this is the third thing a build is for: changing something and
finding out within a minute whether the change was fine.

The shape is a narrowing. It opens on the whole suite, which is enormous and which nobody
runs, and closes on one command that runs one test method in under a second. Everything in
between is the bookkeeping regrtest does on top of unittest, and each piece of it is small
enough to rebuild in a cell, so the reader ends up having written a tiny version of the test
runner rather than having been told what it does.

The one thing they cannot run is the leak hunter, because `-R` reads `sys.gettotalrefcount()`
and that only exists in a debug build. So it was run for them in the pinned image and the
transcript is committed under `experiments/tier1/`.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording

lesson = Lesson("b03-the-test-suite", "b03")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("b03-the-test-suite").figure

#: The recorded run this lesson ends on. Needs a debug build, so it happened in the image.
LEAK = "b03-a-leak-you-can-see"

lesson.md(f"""
# B03. Asking CPython whether it still works

{badge}

CPython ships more test code than it ships library code. `Lib/test` is 709,292 lines of Python. Everything else in `Lib` put together is 351,408. Two lines of test for every line of the thing being tested.

{figure("how-big-it-is", "a bar chart comparing the size of Lib/test to the rest of Lib")}

Nobody runs all of that, and you never will either. What you will want, about ten minutes after your first change to CPython, is to run the handful of tests that cover the thing you touched, and to believe the answer. That is the whole of this lesson.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Lib/test/libregrtest/findtests.py:40-63@v3.15.0rc1#findtests`.

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
## It is unittest underneath

Before anything else, the good news. {lesson.claim("CPython's test suite is ordinary unittest, the same module you would use for your own project")}, and a test in it is a method on a class whose name starts with `test`. There is no secret framework. Run the next cell and you have run a test suite.
""")


lesson.code(
    """
import io
import unittest


class Arithmetic(unittest.TestCase):
    def test_adding(self):
        self.assertEqual(1 + 1, 2)

    def test_dividing(self):
        self.assertEqual(7 // 2, 3)

    def test_powers(self):
        self.assertEqual(2**10, 1000)


suite = unittest.TestLoader().loadTestsFromTestCase(Arithmetic)

printed = io.StringIO()
result = unittest.TextTestRunner(stream=printed, verbosity=2).run(suite)

print(printed.getvalue())
print(f"{result.testsRun} tests run, {len(result.failures)} failed, {len(result.errors)} errored")
""",
    varies=(
        "The line with the elapsed time and the line naming the file are different for "
        "everybody, because one is a measurement and the other is wherever this notebook "
        "happens to be running from."
    ),
)


lesson.md(f"""
Three methods found, run in alphabetical order, one of them wrong on purpose. `TestCase` is at {cite("Lib/unittest/case.py:393@v3.15.0rc1#TestCase")} and `test_powers` is a {term("test case")} in exactly the sense CPython's own suite means it.

So if it is all unittest, what is `regrtest` for?

{figure("what-regrtest-adds", "unittest on the left and what regrtest adds on the right")}

Everything in the right hand column is about running four hundred files in a row without one of them ruining the next one. A single file needs none of it. Four hundred files need all of it, and that difference is most of what {term("regrtest")} is.

## Finding the tests

Start with the first line of that column. Given a directory, which files are tests?

The answer is not clever, and you can write it yourself in one line. {lesson.claim("A file in Lib/test is a test file if its name starts with test_, and that is the entire rule")}: {cite("Lib/test/libregrtest/findtests.py:40-63@v3.15.0rc1#findtests")} lists the directory, keeps the names beginning with `test_`, drops the extension and sorts what is left.
""")


lesson.code("""
# A few of the names that really are in Lib/test, mixed in with the ones that are not tests.
NAMES = [
    "__init__.py",
    "libregrtest",
    "README",
    "regrtest.py",
    "support",
    "test_compile.py",
    "test_dis.py",
    "test_gc.py",
    "test_json",
]

found = sorted(name.removesuffix(".py") for name in NAMES if name.startswith("test_"))

print(f"{len(NAMES)} names in the directory, {len(found)} of them tests")
for one in found:
    print(f"    {one}")
""")


lesson.md(f"""
`test_json` has no extension and is still a test, because it is a directory full of them. `support` and `libregrtest` are the machinery, and they are skipped by the same rule that keeps everything else, which is why neither of them needs to be named anywhere.

Doing that for real over `Lib/test` finds 394 files and 40 directories, and inside the directories are another 429 files.

## Running one test rather than all of them

Now the part you came for.

{figure("narrowing-it-down", "a table of six ways to run the test suite from all of it to none of it")}

Reading down that table is reading the shape of the command. First the runner, then which files, then which tests inside them. Each step down costs you less time and tells you about less of CPython, and after a change to the compiler the third and fourth rows are the only ones you will type.

The second row deserves a word. `-j0` does not mean no processes, it means as many as this machine has cores, which is the one flag worth remembering if you ever do run the whole thing: {cite("Lib/test/libregrtest/main.py:94-100@v3.15.0rc1#num_workers")}. Half an hour becomes a few minutes.

The `-m` in the fourth row is the interesting one, because the way it matches is not quite what you would guess. The pattern is an ordinary shell glob, but it is tried against the whole dotted name of the test and then against each part of it separately: {cite("Lib/test/libregrtest/filter.py:52-77@v3.15.0rc1#_compile_match_function")}. {lesson.claim("A -m pattern matches if it matches the full test id or any single dotted part of it, so a bare method name finds that method in every class")}. That is why `-m test_boundaries` finds the method wherever it lives, and why `-m Dis*` picks a class.
""")


lesson.code("""
import fnmatch
import re

IDS = [
    "test.test_dis.DisTests.test_boundaries",
    "test.test_dis.DisTests.test_widths",
    "test.test_dis.DisWithFileTests.test_boundaries",
    "test.test_compile.TestSpecifics.test_extended_arg",
]


def matches(pattern, test_id):
    \"\"\"The rule from filter.py, in the two lines it actually is.\"\"\"
    against = re.compile(fnmatch.translate(pattern)).match
    return bool(against(test_id)) or any(against(part) for part in test_id.split("."))


for pattern in ("test_boundaries", "Dis*", "test.test_dis.DisTests.test_widths", "boundaries"):
    hit = [one for one in IDS if matches(pattern, one)]
    print(f"-m {pattern}")
    for one in hit:
        print(f"       {one}")
    if not hit:
        print("       nothing")
""")


lesson.md(f"""
The last pattern finds nothing, and that is worth a second. Globs are anchored at the front, so `boundaries` does not match `test_boundaries`. If a `-m` run says no tests ran, this is almost always why, and the exit code will tell you so.

{figure("what-the-exit-code-means", "a table of regrtest exit codes and what each one means")}

Those numbers live at {cite("Lib/test/libregrtest/results.py:18-22@v3.15.0rc1#EXITCODE_BAD_TEST")}, and 3 and 4 are the two that surprise people, because both of them mean the run was not clean even though no test failed.

## When a test dirties the room

Code 3 is the interesting one, and it is the second line of the regrtest column.

Four hundred test files run one after another in the same process, in a random order. If one of them sets an environment variable and leaves it set, some other file fails an hour later on a different machine and nobody ever works out why. So regrtest takes a copy of the things a test could plausibly disturb, runs the test, and compares: {cite("Lib/test/libregrtest/save_env.py:62-76@v3.15.0rc1#resources")} is the list, and it has 28 entries, from `os.environ` and `sys.path` down to whether the terminal still echoes what you type.

The whole idea fits in a cell.
""")


lesson.code("""
import os
import sys
import warnings


def snapshot():
    \"\"\"Three of the twenty eight things regrtest watches, copied rather than referenced.\"\"\"
    return {
        "os.environ": dict(os.environ),
        "sys.path": list(sys.path),
        "warnings.filters": list(warnings.filters),
    }


def a_tidy_test():
    assert sum(range(10)) == 45


def a_messy_test():
    os.environ["THIS_TEST_RAN"] = "yes"
    warnings.filterwarnings("ignore", message="nothing in particular")


for test in (a_tidy_test, a_messy_test):
    before = snapshot()
    test()
    after = snapshot()
    changed = [name for name in before if before[name] != after[name]]
    print(f"{test.__name__:15} changed {', '.join(changed) if changed else 'nothing'}")
""")


lesson.md(f"""
Both tests passed. One of them left the room untidy, and without that comparison nothing would ever have said so. With `--fail-env-changed` the untidy one is a failure, which is what CI runs, and without the flag it is a warning and exit code 3.

## Hunting a leak

The last line of the column is the one you need a different interpreter for.

A {term("reference leak")} is an object nobody can reach and nobody ever frees. It is not a failure, because the test passed. It is not visible from Python either, because the whole problem is that nothing points at the object any more. What you can see is the total: how many references exist in the entire process. That number is `sys.gettotalrefcount()`, and {lesson.claim("sys.gettotalrefcount only exists on a debug build, which is why hunting leaks needs one", unobservable="the function is compiled in only when CPython is configured with --with-pydebug, so an ordinary interpreter has nothing to call")}.

Given that number, the hunt is a loop. Run the test, take the total, run it again, take it again, and look at the differences. {cite("Lib/test/libregrtest/refleak.py:164-166@v3.15.0rc1#rc_deltas")} is that subtraction.

The first few runs are thrown away.

{figure("six-repetitions", "what the six runs of a leak hunt print, one character each")}

That is not a fudge, it is the only way the measurement works at all. The first time a test runs it fills caches, interns strings and imports modules, and every one of those looks exactly like a leak. So `-R 3:3` means three warmup runs, then three counted ones, and the defaults if you write `-R :` are five and four: {cite("Lib/test/libregrtest/cmdline.py:410-418@v3.15.0rc1#huntrleaks")}.

Then the verdict, which is one line of Python and worth reading twice: {cite("Lib/test/libregrtest/refleak.py:196-209@v3.15.0rc1#check_rc_deltas")}. {lesson.claim("A run is only reported as a leak when every counted repetition gained at least one reference, so a single noisy run is not enough")}.
""")


lesson.code("""
def is_a_leak(deltas):
    \"\"\"The rule from refleak.py. Every counted run has to have gained something.\"\"\"
    return all(delta >= 1 for delta in deltas)


SEEN = [
    ([0, 0, 0], "nothing moved at all"),
    ([1, 1, 1], "one reference more, every single run"),
    ([3, 0, 0], "one run gained three and the rest gained nothing"),
    ([8, -8, 1], "it went up, then came back down"),
    ([5, 5, 6], "several every run, which is a big leak"),
]

for deltas, what in SEEN:
    print(f"{deltas!s:12} {'leak' if is_a_leak(deltas) else 'fine':5} {what}")
""")


lesson.md("""
Rows three and four are real measurements of tests that do not leak, and a rule of "did the number go up" would have called both of them bugs. Then somebody spends an afternoon on the third one, finds nothing, and stops trusting the whole check.

Here is the hunt on a real debug build, with two test files that differ by one line.
""")


lesson.md(recording(LEAK))


lesson.md(f"""
`XX. ...` and `XX1 111`, one character per run. Both files leak during the warmups, because that is when the imports and the caches happen. After the colon the clean file settles to nothing and the leaky one keeps gaining exactly one object per run, forever, which is what `KEPT.append(object())` does.

Two lines of output and a failing exit code, from a test that passed.

## The tests you will live in

There are 823 test files and you will spend nearly all your time in about six of them, because they are the ones that cover the parts of CPython these lessons are about.

`test_dis` is T06's lesson, written as assertions about disassembly. `test_compile` and `test_peepholer` are T05's: what the compiler must produce and what the optimiser is allowed to change. `test_gc` is T09. `test_sys` covers the interpreter's own knobs, and `test_capi` is the enormous one that pokes at the C API from Python, which is where a reimplementation would find out what it had got wrong.

Two decorators show up all through them, and both come from `Lib/test/support`. `@support.cpython_only` marks a test that is about this implementation rather than about the language: {cite("Lib/test/support/__init__.py:1362-1366@v3.15.0rc1#cpython_only")}. PyPy and the rest skip those. `@support.requires_resource("network")` marks a test that needs something the runner has to be told it may use, which is what the `-u` flag turns on.

That first decorator is the interesting one if you ever write another Python. Everything not marked with it is a test of the language, and the language is what your implementation has to pass.
""")


lesson.md("""
## Try it yourself

**One.** Fix `test_powers` in the first cell so all three pass, then break a different one. The runner prints `FAIL` for a failed assertion and `ERROR` for an exception that was not an assertion, and it is worth seeing both.

**Two.** Add a pattern of your own to the `-m` cell. Try `test_*`, then `*boundaries`, then `DisTests.test_widths`, and work out from the results which of the two matching attempts each one is winning on.

**Three.** Add `sys.modules` to `snapshot` in the environment cell, then write a test that imports something small like `json` and watch the check catch it. Then work out why regrtest does not watch that one.

**Four.** If you have a full CPython checkout or a source build, run `python -m test test_dis` and time it, then `python -m test test_dis -m test_widths` and time that. If you do not, run `python -m unittest -v unittest.test` instead, which is the same idea against a suite everybody has.

**Five.** Take the `is_a_leak` cell and write down a delta list you think should be reported and is not. That list is the argument for changing the rule, and it is roughly how the current rule got written.

## What just happened

CPython's test suite is unittest. Everything else is bookkeeping for running four hundred files in one process without them tripping over each other.

A test file is a file whose name starts with `test_`, and the code that decides that is six lines long.

`-m` narrows a run down to one method, and it matches the whole dotted name or any single part of it, which is why a bare method name works and a bare word usually does not.

Exit code 3 means a test passed and left something changed. regrtest knows because it took a copy of 28 things first, and you built a small version of that yourself.

A leak is caught by watching a number that only exists on a debug build, throwing away the first few runs, and reporting only when every counted run gained something. You saw it catch a file whose only crime was one `append`.

## Where this goes next

B04 is reading the tree: which directory holds what, which files are generated by something else, and how to find the code behind a behaviour when nobody tells you where to look. After that, you have the whole toolkit, and the lessons stop being about tools and go back to being about the interpreter.
""")


raise SystemExit(lesson.save())
