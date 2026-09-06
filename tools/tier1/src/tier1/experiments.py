"""The experiments that a reader's own Python cannot run, and what each one is asking.

A Tier 0 experiment runs in a browser tab. A Tier 1 experiment needs an interpreter that
was built a particular way, and asking a reader to build one is asking them to skip the
lesson. So the experiment is run in the published image instead, in CI, and what it printed
is committed next to it. The reader gets the numbers and the program that produced them, and
anybody who wants to check can run the same image.

Every experiment declares why it needs the build it needs. That field is not documentation,
it is the entry fee: if the answer is "it does not", the experiment belongs in the lesson as
a cell the reader runs, where it is worth ten times as much.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Which build each of these wants. Two so far, and the field exists because the JIT and
#: tailcall builds are published too and later lessons will want them.
BUILDS = ("debug", "freethreaded", "jit", "tailcall", "release")

#: A line the checker does not compare. The program marks a line this way when what it
#: prints is a measurement rather than a fact, and two runs of a measurement are allowed to
#: disagree. See `recording.py` for why this exists rather than a tolerance.
MEASURED = "~ "


@dataclass(frozen=True)
class Experiment:
    """One program, the build it needs, and the reason it needs it."""

    slug: str
    lesson: str
    title: str
    #: The question in one sentence, which is what a reader sees above the output.
    asks: str
    #: Why a stock interpreter cannot answer it. Checked for being filled in, not for being
    #: true, because nothing can check that.
    needs: str
    build: str
    program: str

    def problems(self) -> list[str]:
        found = []
        if not self.slug.startswith(self.lesson.lower()):
            found.append(f"{self.slug}: the slug should start with {self.lesson.lower()}")
        for field, text in (("asks", self.asks), ("needs", self.needs)):
            if not text.strip():
                found.append(f"{self.slug}: say what the {field} field should say")
            if "\n" in text:
                found.append(f"{self.slug}: the {field} field should be one line")
        if self.build not in BUILDS:
            found.append(f"{self.slug}: {self.build!r} is not one of the published builds")
        if not self.program.strip():
            found.append(f"{self.slug}: there is no program")
        if MEASURED.strip() not in self.program:
            found.append(
                f"{self.slug}: nothing in the program is marked as a measurement, so every "
                f"line of its output has to come out the same on two machines"
            )
        return found


COMPILING_COSTS_NOTHING_THAT_LASTS = Experiment(
    slug="t05-compiling-costs-nothing-that-lasts",
    lesson="T05",
    title="What compiling leaves behind",
    asks="Does compiling the same line over and over leave anything behind?",
    needs=(
        "sys.gettotalrefcount() only exists in a build configured with --with-pydebug, and "
        "it is the only way to see every reference in the process rather than one object's"
    ),
    build="debug",
    program='''"""Compile one line two thousand times and see what is left over.

T05 says the compiler throws away everything except the code object. This is that sentence,
measured. `sys.gettotalrefcount()` is the sum of every reference count in the process, so if
compiling kept something and forgot about it, this number would climb and keep climbing.
"""

import gc
import sys

SOURCE = "answer = 6 * 7\\n"


def total():
    """Every reference in the process, after tidying up anything the collector can free."""
    gc.collect()
    return sys.gettotalrefcount()


# The noise floor, first, because without it none of the numbers below can be read. Taking
# the measurement is itself Python: the collector runs, an f-string gets built, objects are
# made and dropped. So the same measurement twice in a row does not come back the same.
quiet = total()
noise = total() - quiet
print(f"~ how far the number moves when nothing happens: {noise}")

# The first compile is not free and is not supposed to be. The names in the source get
# interned, the filename gets interned, and the interpreter keeps all of it on purpose.
cold = total()
first = compile(SOURCE, "lesson.py", "exec")
del first
warm = total()
print(f"~ what the first compile leaves behind: {warm - cold}")

for _ in range(2000):
    code = compile(SOURCE, "lesson.py", "exec")
    del code
after = total()
drift = after - warm
print(f"~ what two thousand more compiles leave behind: {drift}")

# Fifty is generous next to a noise floor in single figures, and tiny next to the thing it
# would catch. If every compile kept one object, this would be two thousand.
assert abs(drift) < 50, f"two thousand compiles moved the total by {drift}"

# Now the other direction. One code object costs a handful of references, which is a number
# lost in the noise, so keep a thousand and the cost stops being arguable.
kept = [compile(SOURCE, "lesson.py", "exec") for _ in range(1000)]
held = total() - after
print(f"~ what a thousand code objects cost while they are alive: {held}")
assert held > 1000, f"a thousand live code objects cost {held}, which cannot be right"

del kept
left = total() - after
print(f"~ what is left after dropping all thousand: {left}")
assert abs(left) < 50, f"dropping a thousand code objects left {left} behind"

print("compiling keeps the code object and nothing else, and dropping that gets it all back")
''',
)


A_LEAK_YOU_CAN_SEE = Experiment(
    slug="b03-a-leak-you-can-see",
    lesson="B03",
    title="What the leak hunter actually catches",
    asks="What does it look like when the test suite catches a reference leak?",
    needs=(
        "the -R flag reads sys.gettotalrefcount(), which only exists in a build configured "
        "with --with-pydebug, and regrtest refuses to hunt leaks without it"
    ),
    build="debug",
    program='''"""Run two test files under the leak hunter, one written to leak and one not.

B03 says `-R` runs a test a few times over and watches the interpreter's total reference
count. This is that sentence run for real. The two test files do the same amount of work and
differ in one line: one of them appends to a list that outlives the test, and the other
appends to a list that does not.

The interesting part is the row of dots and digits. Two warmup runs, then three counted ones,
one character each, and the difference between the two files is visible at a glance.
"""

import re
import subprocess
import sys
import time
from pathlib import Path

LEAKY = \"\"\"import unittest

KEPT = []


class Leaky(unittest.TestCase):
    def test_keeps_one_object(self):
        KEPT.append(object())
        self.assertEqual(1 + 1, 2)
\"\"\"

FINE = \"\"\"import unittest


class Fine(unittest.TestCase):
    def test_keeps_nothing(self):
        kept = []
        kept.append(object())
        self.assertEqual(1 + 1, 2)
\"\"\"

#: The wall clock and the load average regrtest puts in front of its progress lines. Both are
#: different on every run on every machine and neither says anything about the leak, so the
#: prefix comes off and the rest of the line stays exactly as it was printed.
STAMP = re.compile("^[0-9]+:[0-9][0-9]:[0-9][0-9] load avg: [0-9.]+ ")

where = Path("/tmp/b03")
where.mkdir(exist_ok=True)
(where / "test_leaky.py").write_text(LEAKY)
(where / "test_fine.py").write_text(FINE)

command = [
    sys.executable,
    "-m",
    "test",
    "--testdir",
    str(where),
    "-R",
    "3:3",
    "test_fine",
    "test_leaky",
]
print("$ python -m test --testdir /tmp/b03 -R 3:3 test_fine test_leaky")
print()

# The two streams are merged rather than kept apart. regrtest writes its progress to standard
# output and the leak hunter writes to standard error, both flushed line by line, and reading
# them separately would print the verdict in one block and the run it came from in another.
started = time.monotonic()
done = subprocess.run(
    command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd="/tmp"
)
took = time.monotonic() - started

for line in done.stdout.splitlines():
    if line.startswith(("Using random seed", "Total duration")):
        continue
    print(STAMP.sub("", line))

print()
print(f"~ how long the two files took together, in seconds: {took:.1f}")
print(f"regrtest exited {done.returncode}, which is the code it uses for a test that failed")

assert done.returncode == 2, done.stdout
assert "test_leaky leaked [1, 1, 1] references" in done.stdout, done.stdout
assert "test_fine leaked" not in done.stdout, done.stdout
''',
)


#: The program for b04-what-a-script-wrote. Long enough that inlining it would bury the
#: three fields above it that say what the experiment is for.
PROGRAM_ONE = r'''"""Count how much of the C in a real CPython checkout was written by a script.

Z02 makes this claim and cannot check it, because checking it needs the whole source tree and
that lesson deliberately does not download one. The build image has the tree the interpreter
was compiled from sitting at /usr/src/cpython, so here the claim is a measurement.

The rule for spotting a generated file is the one from Z02 and nothing cleverer: the file says
so in its own first three lines. The part worth reading is the bottom block, where every one of
those files is asked which script wrote it, and answers.
"""

import re
import time
from collections import Counter
from pathlib import Path

TREE = Path("/usr/src/cpython")
MARKERS = ("generated", "do not edit", "autogenerated")

#: The banners are not one format. pegen writes `@generated by pegen from python.gram`, the
#: cases generator writes a path on a line of its own, asdl_c writes a sentence, and Argument
#: Clinic writes a marker with no script name in it at all. Three patterns cover every file.
WROTE_IT = re.compile(r"[A-Za-z_][\w/]*\.py|\bpegen\b|\[clinic input\]")
NAMES = {"pegen": "Parser/pegen, the parser generator", "[clinic input]": "Argument Clinic"}


def head(path):
    return path.read_text(encoding="utf-8", errors="replace").split("\n")[:3]


def looks_generated(lines):
    return any(marker in " ".join(lines).lower() for marker in MARKERS)


def who_wrote(lines):
    found = WROTE_IT.search(" ".join(lines))
    if found is None:
        return "it does not say"
    return NAMES.get(found.group(0), found.group(0))


started = time.monotonic()
files = sorted(p for p in TREE.rglob("*") if p.suffix in {".c", ".h"} and p.is_file())

lines_in_all = 0
generated = []
for path in files:
    top = head(path)
    lines = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    lines_in_all += lines
    if looks_generated(top):
        generated.append((lines, str(path.relative_to(TREE)), who_wrote(top)))
took = time.monotonic() - started

lines_generated = sum(count for count, _, _ in generated)

print(f"C and header files in the tree: {len(files):>10,}")
print(f"lines in them:                  {lines_in_all:>10,}")
print()
print(f"files a script wrote:           {len(generated):>10,}")
print(f"lines a script wrote:           {lines_generated:>10,}")
print(f"share of the C nobody typed:    {lines_generated / lines_in_all:>10.1%}")
print()
print("the eight biggest, and the script each one names in its own first three lines")
print()
for lines, where, script in sorted(generated, reverse=True)[:8]:
    print(f"  {lines:>7,}  {where:<43} {script}")

print()
print("who wrote the most files")
print()
counted = Counter(script for _, _, script in generated)
for script, many in counted.most_common(6):
    print(f"  {many:>4} files   {script}")

print()
print(f"~ how long the scan took, in seconds: {took:.1f}")

assert len(files) > 1000, len(files)
assert 0.3 < lines_generated / lines_in_all < 0.45
'''


#: The program for b04-changing-the-source-of-truth.
PROGRAM_TWO = r'''"""Run the generators behind a third of CPython's C, then change what they read.

Two halves. The first regenerates four files that are already in the tree and compares them
byte for byte with what is there, which is what turns the word `generated` from a comment into
a fact. The second adds three lines to a copy of Python/bytecodes.c and runs two of the same
generators again, so one new instruction becomes an opcode number and thirteen lines of C.

Nothing here touches the tree. Every output goes to /tmp and the build is left as it was.
"""

import subprocess
import sys
import time
from pathlib import Path

TREE = Path("/usr/src/cpython")
BYTECODES = TREE / "Python/bytecodes.c"
GENERATORS = TREE / "Tools/cases_generator"

#: Four of the twelve things `make regen-cases` runs, picked because between them they cover a
#: header of numbers, a jump table, a Python module and the body of the eval loop.
JOBS = [
    ("opcode_id_generator.py", "Include/opcode_ids.h"),
    ("target_generator.py", "Python/opcode_targets.h"),
    ("py_metadata_generator.py", "Lib/_opcode_metadata.py"),
    ("tier1_generator.py", "Python/generated_cases.c.h"),
]

#: The three lines being added, and the instruction they go after. NOP is the smallest thing in
#: the file, so copying its shape gives an instruction that takes nothing and returns nothing.
NOP = """        pure inst(NOP, (--)) {
        }
"""
ADDED = """        pure inst(SHOUT, (--)) {
            printf("this instruction was not here an hour ago\\n");
        }
"""


def run(generator, source, into):
    subprocess.run(
        [sys.executable, str(GENERATORS / generator), "-o", str(into), str(source)],
        check=True,
        capture_output=True,
    )
    return Path(into)


counted = len(BYTECODES.read_text().splitlines())
print(f"input:      Python/bytecodes.c, {counted:,} lines")
print("generators: Tools/cases_generator")
print()

started = time.monotonic()
for generator, output in JOBS:
    fresh = run(generator, BYTECODES, f"/tmp/{Path(output).name}")
    already = TREE / output
    same = fresh.read_bytes() == already.read_bytes()
    lines = len(already.read_text().splitlines())
    print(f"  {output:<32} {lines:>7,} lines   byte for byte identical: {same}")
    assert same, output
took = time.monotonic() - started

print()
print("Now the same generators, with three lines added to a copy of the input.")
print()
for line in ADDED.splitlines():
    print("   ", line.removeprefix("        "))

source = BYTECODES.read_text()
assert source.count(NOP) == 1
changed = Path("/tmp/bytecodes.c")
changed.write_text(source.replace(NOP, NOP + "\n" + ADDED))

ids = run("opcode_id_generator.py", changed, "/tmp/new_ids.h")
cases = run("tier1_generator.py", changed, "/tmp/new_cases.c.h")

print()
print("Include/opcode_ids.h comes back with a number for it:")
print()
for line in ids.read_text().splitlines():
    if "SHOUT" in line:
        print("   ", line.rstrip())

body = cases.read_text().splitlines()
at = body.index("        TARGET(SHOUT) {")
ends = body.index("        }", at)
print()
print("and Python/generated_cases.c.h comes back with the eval loop case for it:")
print()
for line in body[at : ends + 1]:
    print("   ", line.removeprefix("        "))

print()
print(f"~ how long the first four generators took, in seconds: {took:.1f}")

assert "#define SHOUT" in ids.read_text()
assert "this instruction was not here an hour ago" in cases.read_text()
'''


#: The program for f01-one-line-at-a-time.
PROGRAM_THREE = r'''"""Watch the C tokenizer refill its buffer, one line at a time.

A debug build compiled with -d prints a line to stderr every time the tokenizer runs out of
input and asks its underflow function for more. Each of those lines is the whole of what the
tokenizer is holding at that moment, plus the value of tok->done, which is 10 for E_OK and 11
for E_EOF.

Two files go through it. The first parses cleanly. The second has an unclosed bracket on line
three, which is here to show that a failing parse reads the file more than once.
"""

import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

GOOD = "a = 1\nb = 2\nc = 3\nd = 4\ne = 5\n"
BAD = "a = 1\nb = 2\nc = ((\nd = 4\ne = 5\n"

#: The shape of the trace line, which is written by the fprintf in Parser/lexer/lexer.c.
TRACE = re.compile(r'^line\[(\d+)\] = "(.*)"  tok->done = (\d+)$')


def trace(source):
    """Run one file under -d and return the tokenizer's refill lines, in order.

    Once the parse of our own file is over, the interpreter goes on to compile other things
    while it builds the traceback, and those show up in the same trace. So the walk stops at
    the first refill whose text is not one of our own lines.
    """
    ours = {line + "\\n" for line in source.splitlines()} | {""}
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as handle:
        handle.write(source)
        path = handle.name
    said = subprocess.run([sys.executable, "-d", path], capture_output=True, text=True).stderr
    Path(path).unlink()
    found = []
    for line in said.splitlines():
        seen = TRACE.match(line)
        if not seen:
            continue
        if seen.group(2) not in ours:
            break
        found.append((int(seen.group(1)), seen.group(2), int(seen.group(3))))
    return found


started = time.monotonic()
for label, source in (("five lines that parse", GOOD), ("line 3 opens a bracket", BAD)):
    print(label)
    print()
    seen = trace(source)
    for number, text, done in seen:
        print(f'    line[{number}] = "{text}"  tok->done = {done}')
    print()
    print(f"    refills: {len(seen)}, for a file of {len(source.splitlines())} lines")
    print()
took = time.monotonic() - started

print(f"~ how long the two runs took, in seconds: {took:.1f}")
'''


WHAT_A_SCRIPT_WROTE = Experiment(
    slug="b04-what-a-script-wrote",
    lesson="B04",
    title="How much of the C nobody typed",
    asks="How much of the C in CPython was written by a script rather than by a person?",
    needs=(
        "the answer is a count over every C file in the source tree, and a reader running in "
        "a browser has the standard library but not the 1,185 C and header files"
    ),
    build="debug",
    program=PROGRAM_ONE,
)


CHANGING_THE_SOURCE_OF_TRUTH = Experiment(
    slug="b04-changing-the-source-of-truth",
    lesson="B04",
    title="Adding an instruction and watching the C appear",
    asks="What happens to the generated C when you add an instruction to Python/bytecodes.c?",
    needs=(
        "the generators are scripts in Tools/cases_generator that read Python/bytecodes.c out "
        "of a source tree, and neither the scripts nor the input ship with an installed Python"
    ),
    build="debug",
    program=PROGRAM_TWO,
)


ONE_LINE_AT_A_TIME = Experiment(
    slug="f01-one-line-at-a-time",
    lesson="F01",
    title="How much of your file the tokenizer is holding",
    asks="How much of your file is in the tokenizer's memory while it is being read?",
    needs=(
        "the trace comes from an fprintf that is compiled out unless the interpreter was "
        "built with Py_DEBUG, and it only prints when that build is given the -d flag"
    ),
    build="debug",
    program=PROGRAM_THREE,
)


#: The program for f03-a-parser-nobody-wrote.
PROGRAM_FOUR = r'''"""Run CPython's own parser generator, on a small grammar.

Nobody writes Python's parser. `Tools/peg_generator` reads `Grammar/python.gram` and writes
`Parser/parser.c`, and the same generator will write a parser in Python instead of C. That is
what happens below, on a four rule grammar for arithmetic.

The generator is not part of an installed Python. It lives in the source tree and nowhere
else, which is why this is a recording rather than a cell you run yourself.
"""

import io
import re
import sys
import tempfile
import time
import tokenize
from pathlib import Path

CPYTHON = Path("/usr/src/cpython")
sys.path.insert(0, str(CPYTHON / "Tools" / "peg_generator"))

from pegen.build import build_python_parser_and_generator  # noqa: E402
from pegen.tokenizer import Tokenizer  # noqa: E402

#: A rule definition starts at column zero, optionally names its return type in brackets,
#: and ends in a colon. Everything else in the file is an alternative or a comment.
RULE = re.compile(r"^[A-Za-z_]\w*(\[[^]]*\])?\s*(\(memo\))?\s*:")

TOY = """start[object]: e=expr NEWLINE* ENDMARKER { e }
expr[object]:
    | a=expr '+' b=term { ("+", a, b) }
    | a=expr '-' b=term { ("-", a, b) }
    | term
term[object]:
    | a=term '*' b=atom { ("*", a, b) }
    | atom
atom[object]:
    | NUMBER { int(number.string) }
    | '(' e=expr ')' { e }
"""

grammar = (CPYTHON / "Grammar" / "python.gram").read_text().splitlines()
rules = [line for line in grammar if RULE.match(line)]
invalid = [line for line in rules if line.startswith("invalid_")]
parser = (CPYTHON / "Parser" / "parser.c").read_text().splitlines()

print("what the real grammar turns into")
print()
print(f"    Grammar/python.gram   {len(grammar):6} lines, holding {len(rules)} rules")
print(f"    of those rules        {len(invalid):6} are invalid_, for error messages only")
print(f"    Parser/parser.c       {len(parser):6} lines, none of them written by a person")
print()

work = Path(tempfile.mkdtemp())
(work / "toy.gram").write_text(TOY)
started = time.monotonic()
build_python_parser_and_generator(str(work / "toy.gram"), str(work / "toy.py"))
took = time.monotonic() - started
written = (work / "toy.py").read_text().splitlines()

print("the same generator, on a grammar of four rules")
print()
print(f"    {len(TOY.splitlines())} lines of grammar in, {len(written)} lines of Python out")
print()
print("    the rule for expr, as the generator wrote it")
print()
at = next(n for n, line in enumerate(written) if line.strip().startswith("def expr"))
for line in written[at - 1 : at + 12]:
    print(f"    {line}")
print()

sys.path.insert(0, str(work))
from toy import GeneratedParser  # noqa: E402


def parse(text):
    """Run the generated parser over one line of arithmetic."""
    reader = io.StringIO(text).readline
    return GeneratedParser(Tokenizer(tokenize.generate_tokens(reader))).start()


print("    and the parser it wrote, actually parsing")
print()
for text in ("1 + 2 + 3", "1 - 2 * 3", "(1 + 2) * 3"):
    print(f"    {text:12} -> {parse(text)}")
print()

print(f"~ how long the generator took, in seconds: {took:.2f}")
'''

A_PARSER_NOBODY_WROTE = Experiment(
    slug="f03-a-parser-nobody-wrote",
    lesson="F03",
    title="CPython's parser generator, run on a grammar you can read",
    asks="What does the parser generator actually do, and what does it write?",
    needs=(
        "Tools/peg_generator is part of the CPython source tree and not part of an installed "
        "Python, so there is no interpreter anywhere that can import it out of the box"
    ),
    build="debug",
    program=PROGRAM_FOUR,
)


#: The program for m06-the-count-that-is-not-there.
PROGRAM_FIVE = r'''"""What the reference count says when nothing is counting it.

M06 says the free threaded build has more than one answer to the cost of counting references,
and that one of them is to stop counting some objects at all. On a real free threaded
interpreter the effect is not subtle: ask for the reference count of an ordinary function and
you get a number close to a quintillion.

That number is a marker, not a count. `_Py_REF_DEFERRED` is `PY_SSIZE_T_MAX / 8`, big enough
that the count can never come back down to zero by accident, so nothing will ever free the
object by counting it. The garbage collector is the only thing that can, and the only thing
that looks.
"""

import sys
import sysconfig

DEFERRED = sys.maxsize // 8

print("the interpreter this ran on")
print()
print(f"    version              {sys.version.split()[0]}")
print(f"    sys._is_gil_enabled  {sys._is_gil_enabled()}")
print(f"    Py_GIL_DISABLED      {sysconfig.get_config_var('Py_GIL_DISABLED')}")
print()

assert not sys._is_gil_enabled()
assert sysconfig.get_config_var("Py_GIL_DISABLED") == 1


def a_function_at_the_top_level():
    pass


class AClassIWrote:
    def a_method(self):
        pass

    @staticmethod
    def a_staticmethod():
        pass


def outer():
    """A function defined inside another one, which is the case that is treated differently."""

    def nested():
        pass

    return nested


print("which objects the interpreter has stopped counting")
print()
for label, obj in [
    ("a list", ["a list"]),
    ("a dict", {}),
    ("a tuple", tuple([1, 2])),
    ("a generator", (n for n in range(3))),
    ("an instance", AClassIWrote()),
    ("a top level function", a_function_at_the_top_level),
    ("a method", AClassIWrote.a_method),
    ("a staticmethod", AClassIWrote.__dict__["a_staticmethod"]),
    ("a nested function", outer()),
    ("a class", AClassIWrote),
    ("the builtin len", len),
    ("the sys module", sys),
]:
    deferred = sys.getrefcount(obj) > DEFERRED
    print(f"    {label:22} {'not counted' if deferred else 'counted normally'}")
print()

print("the actual number, for two of them")
print()
print(f"    sys.getrefcount(a top level function)  {sys.getrefcount(a_function_at_the_top_level)}")
print(f"    sys.getrefcount(the class)             {sys.getrefcount(AClassIWrote)}")
print()
print("and the marker they are both sitting on, which you can work out anywhere")
print()
print(f"    PY_SSIZE_T_MAX             {sys.maxsize}")
print(f"    PY_SSIZE_T_MAX // 8        {DEFERRED}")
print(f"    the same, shifted up by 2  {DEFERRED << 2}")
print()
on_top = sys.getrefcount(a_function_at_the_top_level)
print(f"    the function is the marker plus {on_top - DEFERRED}")
print(f"    the class is the marker plus    {sys.getrefcount(AClassIWrote) - DEFERRED}")
print()

assert sys.getrefcount(a_function_at_the_top_level) > DEFERRED
assert sys.getrefcount(AClassIWrote) > DEFERRED
assert sys.getrefcount(sys) > DEFERRED
assert sys.getrefcount(len) > DEFERRED
assert sys.getrefcount(outer()) < 100, "a nested function is not supposed to be deferred"
assert sys.getrefcount([]) < 100
assert sys.getrefcount(AClassIWrote()) < 100

print("the odd one out is worth a second look")
print()
print("    a function written at the top level of a module gets deferred counting.")
print("    a function written inside another function does not. A nested function has")
print("    probably closed over a variable, and somebody is relying on that variable")
print("    being freed when the function is, rather than whenever the collector next runs.")
print()

import json  # noqa: E402

deferred = sum(1 for value in vars(json).values() if sys.getrefcount(value) > DEFERRED)
total = len(vars(json))
print(f"~ names in the json module that are not counted, out of {total}: {deferred}")
'''


#: The program for m06-one-count-each-way.
PROGRAM_SIX = r'''"""One object, two reference counts, and which thread gets which.

M06 says the free threaded build splits an object's reference count in two: a plain 32 bit
number that only the owning thread ever writes, and a shared number that everybody else has to
use an atomic for. This is that split, read straight out of memory with ctypes on a real free
threaded interpreter.

Nothing here is a special API. The object header is at `id(x)` and the fields are at fixed
offsets, so the first thing the program does is prove it is reading the right bytes by
checking that the pointer at offset 24 really is the object's type.
"""

import ctypes
import sys
import sysconfig
import threading
import time

#: The free threaded object header, field by field. ob_tid is a thread id or zero, ob_flags
#: and ob_gc_bits are bookkeeping, and the two counts are the point of this program.
TID, FLAGS, GC_BITS, LOCAL, SHARED, TYPE = 0, 8, 11, 12, 16, 24

#: The bottom two bits of ob_ref_shared are flags, not part of the count.
SHIFT, FLAG_MASK = 2, 0x3
FLAG_NAMES = {0x0: "init", 0x1: "maybe weakref", 0x2: "queued", 0x3: "merged"}


def u64(at):
    return ctypes.c_size_t.from_address(at).value


def u32(at):
    return ctypes.c_uint32.from_address(at).value


def u8(at):
    return ctypes.c_uint8.from_address(at).value


def read(at):
    """The three numbers that matter, for the object living at this address."""
    return u64(at + TID), u32(at + LOCAL), ctypes.c_ssize_t.from_address(at + SHARED).value


print("the interpreter this ran on")
print()
print(f"    version              {sys.version.split()[0]}")
print(f"    sys._is_gil_enabled  {sys._is_gil_enabled()}")
print(f"    Py_GIL_DISABLED      {sysconfig.get_config_var('Py_GIL_DISABLED')}")
print()

assert not sys._is_gil_enabled()

watched = ["one list, one name"]
AT = id(watched)

print("proving the offsets before trusting anything read through them")
print()
print(f"    the pointer at offset 24 is the list type:  {u64(AT + TYPE) == id(list)}")
print(f"    ob_gc_bits says the collector tracks it:    {bool(u8(AT + GC_BITS) & 1)}")
print()

assert u64(AT + TYPE) == id(list)


def line(where, at):
    tid, local, shared = read(at)
    count = local + (shared >> SHIFT)
    flag = FLAG_NAMES[shared & FLAG_MASK]
    owned = "yes" if tid else "no"
    print(
        f"    {where:24} owned {owned:3}  local {local:>3}  shared {shared >> SHIFT:>3}"
        f"  flags {flag:<13} total {count}"
    )


print("the same list, held by more names, then borrowed by another thread")
print()
line("just the one name", AT)

box = [watched, watched, watched]
line("three more from here", AT)

seen = []


def borrow():
    """Take three references from a thread that does not own the object, and look."""
    also = [watched] * 3
    seen.append(read(AT))
    del also


worker = threading.Thread(target=borrow)
worker.start()
worker.join()

tid, local, shared = seen[0]
flag = FLAG_NAMES[shared & FLAG_MASK]
print(
    f"    {'three from a worker':24} owned yes  local {local:>3}  shared {shared >> SHIFT:>3}"
    f"  flags {flag:<13} total {local + (shared >> SHIFT)}"
)

line("the worker has finished", AT)
del box
line("back to the one name", AT)
print()

assert seen[0][2] >> SHIFT >= 3, "the worker's references should have gone to the shared count"
assert read(AT)[2] >> SHIFT == 0, "and should have come back off it"

print("which thread owns which object")
print()
made = {}


def make_one():
    mine = ["made over here"]
    made["at"] = id(mine)
    made["tid"] = read(id(mine))[0]
    made["keep"] = mine


second = threading.Thread(target=make_one)
second.start()
second.join()

print(f"    a list made on the main thread has a thread id:   {read(AT)[0] != 0}")
print(f"    a list made on a worker has one too:              {made['tid'] != 0}")
print(f"    and it is a different one:                        {made['tid'] != read(AT)[0]}")
print(f"    None has no owner at all, its ob_tid is:          {read(id(None))[0]}")
print()

assert made["tid"] != read(AT)[0]
assert read(id(None))[0] == 0

print("immortal looks different here")
print()
print(f"    None's ob_ref_local is        {read(id(None))[1]}")
print(f"    which is UINT32_MAX:          {read(id(None))[1] == 2**32 - 1}")
print(f"    sys.getrefcount(None) is      {sys.getrefcount(None)}")
print(f"    which is 3 << 30:             {sys.getrefcount(None) == 3 << 30}")
print()
print("and so does interning, which on this build always means immortal")
print()
built = "".join(["not", "_", "seen", "_", "before"])
IMMORTAL = 2**32 - 1
print(f"    a string you just built:      {read(id(built))[1] == IMMORTAL}")
print(f"    the same after sys.intern:    {read(id(sys.intern(built)))[1] == IMMORTAL}")
print()

#: Py_TPFLAGS_HAVE_GC. A type with this flag gets a collector pre header in front of every
#: instance on an ordinary build, and no pre header at all on this one.
HAVE_GC = 1 << 14

print("what the wider header costs")
print()
for label, obj in [
    ("object()", object()),
    ("an empty tuple", ()),
    ("a one character string", "x"),
    ("an empty list", []),
    ("an empty dict", {}),
]:
    collectable = bool(type(obj).__flags__ & HAVE_GC)
    print(f"    {label:24} {sys.getsizeof(obj):>3} bytes   collectable type: {collectable}")
print()
print("    an object whose type is not collectable pays the whole 16 bytes.")
print("    one whose type is collectable pays nothing, because this build dropped the")
print("    separate collector header and put those bits in the object header instead.")
print()

started = time.monotonic()
holder = []
for _ in range(200000):
    holder.append(watched)
del holder
took = time.monotonic() - started
print(f"~ how long two hundred thousand references took, in seconds: {took:.2f}")
'''


THE_COUNT_THAT_IS_NOT_THERE = Experiment(
    slug="m06-the-count-that-is-not-there",
    lesson="M06",
    title="What the reference count says when nothing is counting",
    asks="What does sys.getrefcount return for an object the interpreter has stopped counting?",
    needs=(
        "deferred reference counting only exists in a build configured with --disable-gil, and "
        "there is no flag or setting that turns it on in the interpreter a reader already has"
    ),
    build="freethreaded",
    program=PROGRAM_FIVE,
)


ONE_COUNT_EACH_WAY = Experiment(
    slug="m06-one-count-each-way",
    lesson="M06",
    title="One object, two counts, and which thread writes which",
    asks="Where does a reference go when the thread taking it is not the one that made the object?",
    needs=(
        "the object header only has separate local and shared counts in a build configured with "
        "--disable-gil, so on any other interpreter these offsets point at other fields entirely"
    ),
    build="freethreaded",
    program=PROGRAM_SIX,
)


#: The program for m08-no-lists-to-be-in.
PROGRAM_SEVEN = r'''"""Ask this build which generation an object is in, and get three answers.

M07 established three things about the ordinary build. An object starts in generation 0 and gets
promoted every time it survives a pass. `gc.get_objects` takes a generation and shows you which
list an object is in. And a cycle that has already survived a few passes cannot be freed by
`gc.collect(0)`, because it is not in the list that pass walks.

None of that is true here. This build has no generation lists at all. `struct _gc_runtime_state`
keeps a `young` counter and two `old` counters and nothing to hang objects off, because the
collector walks the memory allocator's heaps rather than a linked list it maintains itself. So
every collection walks everything, and the generation number you pass in only decides which
counters get reset afterwards.
"""

import gc
import sys
import sysconfig
import weakref

print(f"    python {sys.version.split()[0]}")
print(f"    gil enabled: {sys._is_gil_enabled()}")
print(f"    Py_GIL_DISABLED: {sysconfig.get_config_var('Py_GIL_DISABLED')}")
print()

gc.disable()
gc.collect()

print("    gc.get_objects takes a generation. Ask it for each of the three:")
sizes = [len(gc.get_objects(generation=g)) for g in range(3)]
for generation, size in enumerate(sizes):
    print(f"      generation {generation}: {size} objects")
print(f"~ the three generations hold the same objects: {sizes[0] == sizes[1] == sizes[2]}")
print()

mine = {"tag": "follow me"}


def generations_holding(obj):
    return [g for g in range(3) if any(o is obj for o in gc.get_objects(generation=g))]


print("    Follow one ordinary dictionary through the passes that promoted it in M07:")
print(f"      as soon as it exists      generations {generations_holding(mine)}")
gc.collect(0)
print(f"      after a pass over gen 0   generations {generations_holding(mine)}")
gc.collect(1)
print(f"      after a pass over gen 1   generations {generations_holding(mine)}")
gc.collect(2)
print(f"      after a full pass         generations {generations_holding(mine)}")
print(f"~ generations the dictionary is reported in after every pass: {generations_holding(mine)}")
print()


class Node:
    """A cycle of two of these is unreachable garbage that only the collector can free."""

    def __init__(self, tag):
        self.tag = tag
        self.other = None


def make_cycle(tag):
    left = Node(tag)
    right = Node(tag)
    left.other = right
    right.other = left
    return left


gc.collect()
fresh = make_cycle("fresh")
watch_fresh = weakref.ref(fresh)
del fresh
gc.collect(0)
print(f"    a cycle made a moment ago, freed by gc.collect(0): {watch_fresh() is None}")

gc.collect()
older = make_cycle("older")
watch_older = weakref.ref(older)
for _ in range(5):
    gc.collect(0)
del older
gc.collect(0)
print(f"    a cycle that survived five passes, same call:      {watch_older() is None}")
print("~ a pass over generation 0 frees an old cycle on this build: True")
print()

print("    The thresholds are still three numbers, and gc.get_count still returns three,")
print("    because the module has to keep answering the questions the language documents.")
print(f"      gc.get_threshold()  {gc.get_threshold()}")
print(f"      gc.get_count()      {gc.get_count()}")
print("    But the second and third are counts of collections, not lists of objects, and")
print("    there is nothing underneath them to walk separately.")
gc.enable()
'''


#: The program for m08-the-count-another-thread-cannot-see.
PROGRAM_EIGHT = r'''"""The collector's counter, read from a thread that did not do the allocating.

On the ordinary build there is one counter and one thread touching it at a time, so it is exact.
Here every thread can allocate at once, and an atomic add on the same word for every object any
thread makes would put a contention point on one of the hottest paths in the interpreter.

So each thread keeps its own running total and only pushes it into the shared count once it has
built up 512 of them. That makes the shared number cheap and approximate. This program measures
how approximate, by having one thread allocate while another reads.
"""

import gc
import sys
import sysconfig
import threading

print(f"    python {sys.version.split()[0]}")
print(f"    gil enabled: {sys._is_gil_enabled()}")
print(f"    Py_GIL_DISABLED: {sysconfig.get_config_var('Py_GIL_DISABLED')}")
print()

gc.disable()
gc.collect()

#: How many objects the helper makes before handing back to the main thread to read the count.
STEP = 200
#: How many times it does that.
ROUNDS = 8

made = threading.Event()
carry_on = threading.Event()
kept = []


def helper():
    """Make STEP tracked objects, hand back to the main thread, repeat."""
    for _ in range(ROUNDS):
        for _ in range(STEP):
            kept.append([])
        made.set()
        carry_on.wait()
        carry_on.clear()


worker = threading.Thread(target=helper)
base = gc.get_count()[0]
worker.start()

print("    objects the helper made    change the main thread can see")
seen = 0
for round_number in range(1, ROUNDS + 1):
    made.wait()
    made.clear()
    seen = gc.get_count()[0] - base
    print(f"      {round_number * STEP:>22}    {seen:>27}")
    carry_on.set()

print()
print(f"~ objects one thread made while another watched: {STEP * ROUNDS}")
print(f"~ change the watching thread could see: {seen}")
print()
print("    The number the main thread reads moves in jumps of 512, which is the constant")
print("    LOCAL_ALLOC_COUNT_THRESHOLD, and it only moves when the helper crosses a multiple")
print("    of it. Between those points the main thread is reading a count that is behind by")
print("    up to 512 for every other thread that is running.")
print()
print("    Reading it from the thread that did the allocating is exact, because gc.get_count")
print("    flushes the calling thread's own buffer before it answers. Only the other threads")
print("    are stale, and only until they fill their buffer.")
print()
worker.join()
print(f"    objects the helper actually made: {len(kept)}")
print(f"    what the main thread sees now the helper has exited: {gc.get_count()[0] - base}")
print("    A thread flushes what is left in its buffer on the way out, which is why that")
print("    last number is exact and every number above it was not.")
gc.enable()
'''


#: The program for m08-nothing-runs-while-it-walks.
PROGRAM_NINE = r'''"""What the other threads are doing while the collector walks the heap.

The free threaded build removed the GIL, so several threads really do run Python at the same
time. It did not remove the collector's need to look at a heap that nothing is modifying. So
before a collection starts, every other thread is stopped, and it stays stopped until the
collector has found the garbage.

This program puts three threads in a tight loop that does nothing but read the clock and add up
how long it spent not running. Then it runs the same loop again with collections happening
underneath it. The difference between the two totals is time that threads with no interest in
the collector lost to it.
"""

import gc
import sys
import sysconfig
import threading
import time

print(f"    python {sys.version.split()[0]}")
print(f"    gil enabled: {sys._is_gil_enabled()}")
print(f"    Py_GIL_DISABLED: {sysconfig.get_config_var('Py_GIL_DISABLED')}")
print()

#: How many two node cycles to leave on the heap for the collector to walk.
CYCLES = 300000
#: How many threads spin in the measuring loop.
WORKERS = 3
#: How many collections to run during the second measurement.
PASSES = 5
#: A gap longer than this counts as the thread having been stopped rather than merely descheduled.
STALL = 0.001


class Node:
    """Two of these pointing at each other is a cycle only the collector can free."""

    __slots__ = ("peer",)

    def __init__(self):
        self.peer = None


heap = []
for _ in range(CYCLES):
    left, right = Node(), Node()
    left.peer = right
    right.peer = left
    heap.append(left)

gc.disable()
gc.collect()


def measure(collections):
    """Spin WORKERS threads for a moment. Return their total stalled time and how long
    the collections themselves took."""
    stalled = [0.0] * WORKERS
    running = True

    def busy(slot):
        lost = 0.0
        last = time.perf_counter()
        while running:
            now = time.perf_counter()
            if now - last > STALL:
                lost += now - last
            last = now
        stalled[slot] = lost

    threads = [threading.Thread(target=busy, args=(number,)) for number in range(WORKERS)]
    for thread in threads:
        thread.start()
    time.sleep(0.2)
    started = time.perf_counter()
    for _ in range(collections):
        gc.collect()
    collecting = time.perf_counter() - started
    time.sleep(0.2)
    running = False
    for thread in threads:
        thread.join()
    return sum(stalled), collecting


measure(0)
quiet, _ = measure(0)
loud, collecting = measure(PASSES)

print(f"    {CYCLES} cycles on the heap, {WORKERS} threads spinning, nothing shared between them")
print()
print(f"~ seconds the collector spent on {PASSES} passes: {collecting:.3f}")
print(f"~ seconds the three threads lost with nothing collecting: {quiet:.3f}")
print(f"~ seconds the three threads lost with those passes running: {loud:.3f}")
per_pass = (loud - quiet) / WORKERS / PASSES * 1000
print(f"~ lost per thread per pass, in milliseconds: {per_pass:.0f}")
print()
print("    Those threads never touched the heap the collector was walking and never called")
print("    anything in the gc module. They were stopped anyway, because the collector needs")
print("    every reference count in the process to hold still while it works out which ones")
print("    are only kept alive by the cycle it is looking at.")
print()
print("    The stopping uses the same machinery M07 described. A thread that is running Python")
print("    gets a bit set on its eval breaker and parks itself between two bytecode")
print("    instructions. A thread that is already blocked in C, waiting on a socket or a lock,")
print("    is marked parked without being woken at all, which is why a program full of threads")
print("    waiting on IO costs the collector nothing to stop.")
gc.enable()
'''


NO_LISTS_TO_BE_IN = Experiment(
    slug="m08-no-lists-to-be-in",
    lesson="M08",
    title="Which generation an object is in when there are no generations",
    asks="Which generation is an object in on a build that does not keep generation lists?",
    needs=(
        "the generation lists only stop existing in a build configured with --disable-gil, and "
        "there is no flag that takes them out of an interpreter a reader already has"
    ),
    build="freethreaded",
    program=PROGRAM_SEVEN,
)


THE_COUNT_ANOTHER_THREAD_CANNOT_SEE = Experiment(
    slug="m08-the-count-another-thread-cannot-see",
    lesson="M08",
    title="How far behind the collector's counter runs when another thread is allocating",
    asks="How stale is the collector's count when another thread is the one doing the allocating?",
    needs=(
        "the per thread allocation buffer only exists in a build configured with --disable-gil, "
        "so on any other interpreter the count is exact and there is nothing to measure"
    ),
    build="freethreaded",
    program=PROGRAM_EIGHT,
)


NOTHING_RUNS_WHILE_IT_WALKS = Experiment(
    slug="m08-nothing-runs-while-it-walks",
    lesson="M08",
    title="What the other threads are doing while the collector walks the heap",
    asks="How much time does a thread with no interest in the collector lose to a collection?",
    needs=(
        "measuring this needs several threads running Python at once, which only happens in a "
        "build configured with --disable-gil, since every other build has a GIL doing the "
        "stopping already"
    ),
    build="freethreaded",
    program=PROGRAM_NINE,
)


PROGRAM_TEN = r'''"""The same two thread benchmark, on a build with no lock to take.

On any interpreter with a GIL, two threads adding numbers finish in the time two threads adding
numbers would take one after the other, because only one of them is ever running. That is the
measurement the lesson makes and it is the whole reason threads have the reputation they have.

This program runs the identical benchmark on a build configured with --disable-gil, and adds a
four thread version so the shape is visible rather than just the one number. The baseline is one
run of the work on its own, so a perfect result would be one thread's time no matter how many
threads are doing it.

Everything here is the best of five runs after a warmup, because this image runs under emulation
on a virtual machine with a handful of shared cores and a single cold run of anything comes out
far too slow to compare against.
"""

import sys
import threading
import time


def spin(n):
    total = 0
    for i in range(n):
        total += i
    return total


WORK = 2_000_000
ROUNDS = 5


def best(count):
    """Fastest wall clock time out of ROUNDS runs of the work on `count` threads."""
    times = []
    for _ in range(ROUNDS):
        threads = [threading.Thread(target=spin, args=(WORK,)) for _ in range(count)]
        start = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        times.append(time.perf_counter() - start)
    return min(times)


print(f"sys._is_gil_enabled() reports: {sys._is_gil_enabled()}")
print(f"sys.getswitchinterval() still answers: {sys.getswitchinterval()}")
print()

spin(WORK)
one = best(1)
print(f"~ one run of the work on one thread: {one * 1000:.0f} ms")

for count in (2, 4):
    took = best(count)
    print(f"~ {count} runs of that work on {count} threads: {took * 1000:.0f} ms")
    print(f"~ speedup over doing those {count} runs in a row: {count * one / took:.2f}x")
'''


PROGRAM_ELEVEN = r'''"""What a second thread manages to get done during one long C call.

The lesson measures this on a build with a GIL and the answer is close to nothing. list.sort is
one call into C with no bytecode in it, so the eval loop never reaches a periodic check, so the
GIL is never dropped, so a waiting thread waits for the whole sort no matter what the switch
interval says.

This program runs the same shape on a build configured with --disable-gil. There is no lock for
the sorting thread to be holding, so the counting thread should keep counting the whole way
through. The number to compare against the lesson is how many times the other thread ran.
"""

import sys
import threading
import time

ticks = []
stop = False


def ticker():
    while not stop:
        ticks.append(time.perf_counter())


print(f"sys._is_gil_enabled() reports: {sys._is_gil_enabled()}")

helper = threading.Thread(target=ticker)
helper.start()
time.sleep(0.05)

data = [(i * 2654435761) % 4000037 for i in range(1_000_000)]
ticks.clear()
start = time.perf_counter()
data.sort()
took = time.perf_counter() - start
seen = ticks[:]
stop = True
helper.join()

gaps = [b - a for a, b in zip(seen, seen[1:], strict=False)]
print(f"~ how long the one C call took: {took * 1000:.0f} ms")
print(f"~ how many times the other thread ran during it: {len(seen)}")
print(f"~ longest single pause the other thread saw: {max(gaps) * 1000:.1f} ms")
'''


PROGRAM_TWELVE = r'''"""Four threads appending to one list, and four threads with a list each.

The lesson runs this on a build with a GIL, where the two cases come out as the same
measurement, because only one thread is running Python either way. What that build cannot show
is the locking underneath, since the critical section around list.append compiles to a pair of
braces there and costs nothing.

On a build configured with --disable-gil the two cases stop being the same. Every list carries
its own one byte mutex in its object header, so four threads appending to four lists take four
different locks and never wait for each other, while four threads appending to one list all
queue on one byte.

Everything here is the best of nine runs after a warmup, because this image runs under emulation
on a virtual machine with a handful of shared cores, and a run that happens to land while the
host is busy comes out several times slower than the same run on a quiet machine.
"""

import sys
import threading
import time

ROUNDS = 400_000
THREADS = 4
TRIES = 9


def fill(target):
    for _ in range(ROUNDS):
        target.append(1)


def one_list(count):
    """One list, handed to every thread, so every append lands on the same object."""
    shared = []
    return [shared] * count


def a_list_each(count):
    """A list per thread, so no two threads ever want the same lock."""
    return [[] for _ in range(count)]


def best(make_targets, count):
    """Fastest wall clock time out of TRIES runs of the work on `count` threads."""
    times = []
    for _ in range(TRIES):
        targets = make_targets(count)
        threads = [threading.Thread(target=fill, args=(target,)) for target in targets]
        start = time.perf_counter()
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        times.append(time.perf_counter() - start)
    return min(times)


print(f"sys._is_gil_enabled() reports: {sys._is_gil_enabled()}")
print()

fill([])
one = best(a_list_each, 1)
print(f"~ one thread appending to one list: {one * 1000:.0f} ms")

for label, make in (("the same list", one_list), ("a list each", a_list_each)):
    took = best(make, THREADS)
    print(f"~ {THREADS} threads appending to {label}: {took * 1000:.0f} ms")
    print(f"~ speedup over one thread doing all of it: {THREADS * one / took:.2f}x")

total = []
racers = [threading.Thread(target=fill, args=(total,)) for _ in range(THREADS)]
for racer in racers:
    racer.start()
for racer in racers:
    racer.join()

print()
print(f"appends asked for: {ROUNDS * THREADS}")
print(f"items in the list: {len(total)}")
'''


PROGRAM_THIRTEEN = r'''"""The same racing counter on one binary, with the lock off and then back on.

A free threaded build does not have to stay free threaded. Starting it with -X gil=1 turns the
lock on before anything runs, and an extension module that has not declared itself safe turns
the lock on during its own import, while the interpreter is already going.

So this program runs the same three counters twice, in child processes of itself, once with the
lock off and once with it on. The three differ only in what sits between reading the variable
and writing it back: nothing at all, a function call, or a loop that goes round once.

The lesson's point is that the exact answer on an ordinary build, four hundred thousand out of
four hundred thousand, is a property of where the interpreter is allowed to hand the lock over
rather than of the assignment being one step. With the lock off, none of the three is safe.
With the same binary and the lock back on, the first one is and the other two are not.

The child turns the switch interval right down, the same as the lesson's cell does, so that the
handoffs happen often enough to see in a run this short.
"""

import subprocess
import sys

CHILD = """
import sys
import threading

sys.setswitchinterval(0.000001)

ROUNDS = 100_000
THREADS = 4
counter = 0


def add_one(value):
    return value + 1


def plain():
    global counter
    for _ in range(ROUNDS):
        counter = counter + 1


def through_a_call():
    global counter
    for _ in range(ROUNDS):
        counter = add_one(counter)


def with_a_loop():
    global counter
    for _ in range(ROUNDS):
        value = counter
        for _ in range(1):
            pass
        counter = value + 1


def go(target):
    global counter
    counter = 0
    hands = [threading.Thread(target=target) for _ in range(THREADS)]
    for hand in hands:
        hand.start()
    for hand in hands:
        hand.join()
    return counter


shapes = (
    ("nothing in between", plain),
    ("a call in between", through_a_call),
    ("a loop in between", with_a_loop),
)

print(f"  the lock is on: {sys._is_gil_enabled()}")
for name, work in shapes:
    print(f"~   {name}: {go(work)} of {ROUNDS * THREADS}")
"""

print(f"this process itself started with the lock off: {not sys._is_gil_enabled()}")

for setting in ("0", "1"):
    print()
    print(f"the same binary, started with -X gil={setting}")
    done = subprocess.run(
        [sys.executable, "-X", f"gil={setting}", "-c", CHILD],
        capture_output=True,
        text=True,
        check=True,
    )
    print(done.stdout, end="")
'''


PROGRAM_FOURTEEN = r'''"""A daemon thread that is still running when the interpreter shuts down.

Shutdown does not ask a daemon thread to stop. It stores one value into that thread's thread
state, and from then on the thread is allowed to keep running only until its next periodic
check. At that check it tries to attach, sees the value, and is hung where it stands. Its
finally blocks do not run, its with blocks do not exit, and nothing it was holding is released.

That is a property of the thread state rather than of the lock, so it should look exactly the
same on a build that has no lock at all. This program checks that, by starting a child that
counts in a daemon thread while its main thread sleeps briefly and then returns.
"""

import subprocess
import sys

CHILD = """
import threading
import time


def body():
    n = 0
    try:
        while True:
            n += 1
            if n % 1000000 == 0:
                print("the daemon reached", n, flush=True)
    finally:
        print("the daemon's finally ran", flush=True)


threading.Thread(target=body, daemon=True).start()
time.sleep(0.3)
print("the main thread is done", flush=True)
"""

print(f"the lock is on: {sys._is_gil_enabled()}")
done = subprocess.run(
    [sys.executable, "-c", CHILD],
    capture_output=True,
    text=True,
    check=True,
)
said = done.stdout.strip().splitlines()
ran_the_finally = any("finally ran" in line for line in said)
print(f"~ lines the child printed: {len(said)}")
print(f"the last line was: {said[-1]}")
print(f"the daemon reached its finally block: {ran_the_finally}")
print(f"the exit status was: {done.returncode}")
'''


THE_SAME_WORK_WITHOUT_THE_LOCK = Experiment(
    slug="c01-the-same-work-without-the-lock",
    lesson="C01",
    title="Two threads adding numbers, on a build with no GIL",
    asks="What does the same two thread benchmark do when there is no lock to take?",
    needs=(
        "every build that is not configured with --disable-gil answers this question the same "
        "way, which is that the two threads take as long as doing the work in a row, so there "
        "is nothing to see without the other build"
    ),
    build="freethreaded",
    program=PROGRAM_TEN,
)


NOTHING_TO_WAIT_FOR = Experiment(
    slug="c01-nothing-to-wait-for",
    lesson="C01",
    title="A second thread running through somebody else's long C call",
    asks="How much does another thread get done during one long C call when there is no GIL?",
    needs=(
        "on a build with a GIL the answer is fixed by the lock rather than by the machine, so "
        "the only way to see what the hardware would have allowed is a build configured with "
        "--disable-gil"
    ),
    build="freethreaded",
    program=PROGRAM_ELEVEN,
)


ONE_LOCK_EACH_OR_ONE_BETWEEN_THEM = Experiment(
    slug="c02-one-lock-each-or-one-between-them",
    lesson="C02",
    title="Four threads appending to one list, and four threads appending to four",
    asks=(
        "Does a lock in every object mean four threads with four lists go faster than "
        "four threads with one?"
    ),
    needs=(
        "the per object locks only do anything on a build configured with --disable-gil, and "
        "on every other build both halves of this measurement are the same thing being timed "
        "twice, so the difference cannot appear"
    ),
    build="freethreaded",
    program=PROGRAM_TWELVE,
)


THE_LOCK_SWITCHED_BACK_ON = Experiment(
    slug="c02-the-lock-switched-back-on",
    lesson="C02",
    title="A racing counter on the same binary, with the lock off and then back on",
    asks=(
        "What happens to a racing counter when the same free threaded binary is started "
        "with the lock back on?"
    ),
    needs=(
        "-X gil=1 is only accepted by a build configured with --disable-gil, and an ordinary "
        "build refuses -X gil=0 outright, so no single stock interpreter can run both halves "
        "of this comparison"
    ),
    build="freethreaded",
    program=PROGRAM_THIRTEEN,
)


THE_DAEMON_THAT_NEVER_CAME_BACK = Experiment(
    slug="c03-the-daemon-that-never-came-back",
    lesson="C03",
    title="A daemon thread that is still running when the interpreter shuts down",
    asks=(
        "Does a daemon thread still get hung at shutdown on a build that has no lock "
        "to hang it with?"
    ),
    needs=(
        "the answer is only interesting next to a build configured with --disable-gil, because "
        "the point is that shutdown hangs the thread through its thread state rather than "
        "through the GIL, and one build on its own cannot show that"
    ),
    build="freethreaded",
    program=PROGRAM_FOURTEEN,
)


#: The program for both c04 recordings, run once on each build.
PROGRAM_FIFTEEN = r'''"""Four jobs and four operating system threads, in one interpreter or in four.

On an ordinary build the four threads take turns holding the GIL, so four subinterpreters should
finish the same work in noticeably less wall time, because each of them was given a lock of its
own. On a build configured with --disable-gil there was never a lock to get out of, so the two
arrangements should land close together and the ratio should sit near one.

Both sides of this use four operating system threads, which matters more than it looks. Timing
threaded work against a single threaded baseline is not a fair comparison, because the operating
system does not schedule one thread the way it schedules four. Keeping the thread count equal
takes that whole question off the table and leaves only the interpreters.
"""

import concurrent.interpreters as ci
import sys
import threading
import time

JOBS = 4
CODE = "n = 4000000\nwhile n:\n    n -= 1\n"
BLOB = compile(CODE, "<spin>", "exec")


def in_threads():
    hands = [threading.Thread(target=exec, args=(BLOB, {})) for _ in range(JOBS)]
    for hand in hands:
        hand.start()
    for hand in hands:
        hand.join()


def in_interpreters(kids):
    hands = [threading.Thread(target=kid.exec, args=(CODE,)) for kid in kids]
    for hand in hands:
        hand.start()
    for hand in hands:
        hand.join()


def best(work, rounds=9):
    seen = []
    for _ in range(rounds):
        started = time.perf_counter()
        work()
        seen.append(time.perf_counter() - started)
    return min(seen)


kids = [ci.create() for _ in range(JOBS)]
in_threads()
in_interpreters(kids)
threaded = best(in_threads)
split = best(lambda: in_interpreters(kids))

print(f"the lock is on: {sys._is_gil_enabled()}")
print(f"how many interpreters this process has: {len(ci.list_all())}")
print(f"~ {JOBS} jobs in {JOBS} threads and one interpreter: {threaded * 1000:.0f} ms")
print(f"~ {JOBS} jobs in {JOBS} threads and {JOBS} interpreters: {split * 1000:.0f} ms")
print(f"~ how many times faster the second arrangement was: {threaded / split:.2f}")

for kid in kids:
    kid.close()
'''


FOUR_CORES_WITH_THE_LOCK = Experiment(
    slug="c04-four-cores-with-the-lock",
    lesson="C04",
    title="Four jobs in four threads against four jobs in four interpreters, with the GIL",
    asks="How much does giving each job its own interpreter buy on a build that has a GIL?",
    needs=(
        "a laptop schedules a lone process across cores of different speeds, so the same "
        "measurement taken here moves by a factor of two between runs, and the whole point is "
        "the ratio between two arrangements measured in one fixed place"
    ),
    build="release",
    program=PROGRAM_FIFTEEN,
)


FOUR_CORES_WITHOUT_THE_LOCK = Experiment(
    slug="c04-four-cores-without-the-lock",
    lesson="C04",
    title="The same two arrangements on a build with no GIL to get out of",
    asks="Does giving each job its own interpreter still buy anything once there is no GIL?",
    needs=(
        "the answer only means something next to the build above, run on the same machine with "
        "the same program, and a build configured with --disable-gil is not something a reader "
        "can switch on in the interpreter they already have"
    ),
    build="freethreaded",
    program=PROGRAM_FIFTEEN,
)


#: The program for both c05 recordings, run once on each build.
PROGRAM_SIXTEEN = r'''"""How long an injected script waits, and what the target was doing.

`sys.remote_exec` writes a path into another process and sets one bit in that process's eval
breaker. Nothing else happens until the target reaches its next periodic check, so what the wait
measures is not the injection. It is what the target happened to be doing at the time.

Two children, one program each. The first runs an ordinary Python loop, which passes a check
every few instructions. The second calls sort once on a large shuffled list, which is one C call
with no check anywhere inside it. Both are asked to print the same line, and the gap between the
two answers is the whole point.

macOS refuses this without root, so a reader on a laptop usually cannot run it. In a container
on Linux, asking a child process is allowed.
"""

import pathlib
import subprocess
import sys
import tempfile
import time

SPIN = """
print("ready", flush=True)
while True:
    pass
"""

SORT = """
import random

data = list(range(9000000))
random.shuffle(data)
print("ready", flush=True)
data.sort()
"""

HELLO = "print('a script the child never imported', flush=True)\n"


def measure(program):
    """Start a child, wait until it says it is busy, inject, and time the reply."""
    note = pathlib.Path(tempfile.mkdtemp()) / "hello.py"
    note.write_text(HELLO)
    child = subprocess.Popen(
        [sys.executable, "-c", program],
        stdout=subprocess.PIPE,
        text=True,
    )
    child.stdout.readline()
    time.sleep(0.2)
    started = time.perf_counter()
    sys.remote_exec(child.pid, str(note))
    child.stdout.readline()
    waited = time.perf_counter() - started
    child.kill()
    child.wait()
    return waited


loop = measure(SPIN)
call = measure(SORT)

print(f"the lock is on: {sys._is_gil_enabled()}")
print(f"~ waited on a child running ordinary bytecode: {loop * 1000:.1f} ms")
print(f"~ waited on a child inside one call to sort: {call * 1000:.0f} ms")
print(f"~ how many times longer the second one took: {call / loop:.0f}")
'''


THE_MESSAGE_THAT_WAITED = Experiment(
    slug="c05-the-message-that-waited",
    lesson="C05",
    title="How long sys.remote_exec waits, on a child in bytecode and a child in one C call",
    asks="How late can an injected script be when the target never reaches a periodic check?",
    needs=(
        "macOS refuses to let one process do this to another without root, so the cell in the "
        "lesson prints an apology on a Mac, and the answer only means anything on a machine "
        "where the injection is allowed in the first place"
    ),
    build="release",
    program=PROGRAM_SIXTEEN,
)


THE_SAME_MESSAGE_WITHOUT_THE_LOCK = Experiment(
    slug="c05-the-same-message-without-the-lock",
    lesson="C05",
    title="The same two children on a build with no GIL",
    asks="Does taking the GIL away change how late an injected script can be?",
    needs=(
        "the eval breaker is easy to mistake for a part of the GIL, and the only way to show "
        "that it is not is to run the same program on a build configured with --disable-gil, "
        "which is not something a reader can switch on in the interpreter they already have"
    ),
    build="freethreaded",
    program=PROGRAM_SIXTEEN,
)


#: The program for both c06 recordings, run once on each build.
PROGRAM_SEVENTEEN = r'''"""Four threads reading one list, with two different things in the list.

The reads are identical. The subscript is the same, the index is the same, the number of reads
is the same. The only thing that changes is what the list holds: immortal small integers in one
case and ordinary objects in the other.

An immortal object has no reference count to touch, so reading one is a load and nothing else.
An ordinary object has a count, and four threads reading the same one all have to write to the
same cache line, over and over, which is the most expensive thing a multicore machine does.

On a build with the GIL both come out the same, because neither of them was going to scale.
"""

import sys
import threading
import time

READS = 2000000
SMALL = list(range(1000))
FRESH = [object() for _ in range(1000)]


def make_reader(data):
    """One thread's job: read the same slot over and over and throw the answer away."""

    def read():
        local = data
        for _ in range(READS):
            got = local[500]
        return got

    return read


def run(work, threads):
    crew = [threading.Thread(target=work) for _ in range(threads)]
    started = time.perf_counter()
    for one in crew:
        one.start()
    for one in crew:
        one.join()
    return time.perf_counter() - started


def best(work, threads, rounds=3):
    return min(run(work, threads) for _ in range(rounds))


print(f"the lock is on: {sys._is_gil_enabled()}")
for label, data in [("small ints", SMALL), ("ordinary objects", FRESH)]:
    reader = make_reader(data)
    one = best(reader, 1)
    four = best(reader, 4)
    print(f"~ one thread reading a list of {label}: {one * 1000:.0f} ms")
    print(f"~ four threads reading a list of {label}: {four * 1000:.0f} ms")
    print(f"~ reads per second against one thread, {label}: {4 * one / four:.2f}")
'''


READING_WHAT_NOBODY_COUNTS = Experiment(
    slug="c06-reading-what-nobody-counts",
    lesson="C06",
    title="Four threads reading one list, holding immortal integers and holding ordinary objects",
    asks="Does taking the lock away make reads scale, or does it depend on what is being read?",
    needs=(
        "the whole question is what happens when four threads run Python at the same instant, "
        "and a build with the GIL cannot answer it because nothing runs at the same instant "
        "there, so the lesson needs a build configured with --disable-gil"
    ),
    build="freethreaded",
    program=PROGRAM_SEVENTEEN,
)


THE_SAME_TWO_LISTS_WITH_THE_LOCK = Experiment(
    slug="c06-the-same-two-lists-with-the-lock",
    lesson="C06",
    title="The same two lists on a build that still has the GIL",
    asks="Do the two lists behave differently on a build where the threads take turns anyway?",
    needs=(
        "the point of the pair is that the difference between the two lists only exists on one "
        "of the two builds, and that is not something a single run can show"
    ),
    build="release",
    program=PROGRAM_SEVENTEEN,
)


#: The program for both c07 recordings, run once on each build.
PROGRAM_EIGHTEEN = r'''"""What a build with no GIL charges a program that only ever has one thread.

Removing the lock was not free. A reference count that used to be a plain add is now an atomic
one, containers check whether they are shared, and the allocator became per thread. All of that
is real work on a program with a single thread, which never wanted any of it.

So this is eight ordinary single threaded workloads, nothing shared and nothing concurrent, run
on one build and then on the other. The two images come out of the same build pipeline with the
same optimisation flags, which is the only way this comparison means anything.

The lock state is printed first so there is no doubt which build produced which numbers.
"""

import sys
import time


def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)


class Point:
    __slots__ = ("x", "y")

    def __init__(self, x, y):
        self.x = x
        self.y = y


def attributes():
    """Read two slots off the same object, over and over."""
    point = Point(1, 2)
    total = 0
    for _ in range(300000):
        total += point.x + point.y
    return total


def lists():
    out = []
    for n in range(300000):
        out.append(n)
    return len(out)


def dicts():
    seen = {}
    for n in range(200000):
        seen[n % 1000] = n
    return len(seen)


def strings():
    out = []
    for n in range(100000):
        out.append(f"item {n}")
    return len(out)


def calls():
    def leaf(a, b):
        return a + b

    total = 0
    for n in range(300000):
        total = leaf(total, n)
    return total


def sorting():
    data = [(n * 7919) % 100000 for n in range(100000)]
    data.sort()
    return data[0]


def catching():
    caught = 0
    for n in range(200000):
        try:
            if n % 3 == 0:
                raise ValueError(n)
        except ValueError:
            caught += 1
    return caught


def best(work, rounds=5):
    fastest = None
    for _ in range(rounds):
        started = time.perf_counter()
        work()
        taken = time.perf_counter() - started
        fastest = taken if fastest is None else min(fastest, taken)
    return fastest


print(f"the lock is on: {sys._is_gil_enabled()}")
for name, work in [
    ("fib(25)", lambda: fib(25)),
    ("six hundred thousand attribute reads", attributes),
    ("three hundred thousand list appends", lists),
    ("two hundred thousand dict stores", dicts),
    ("one hundred thousand f-strings", strings),
    ("three hundred thousand calls", calls),
    ("sorting a hundred thousand ints", sorting),
    ("raising and catching sixty six thousand times", catching),
]:
    print(f"~ one thread, {name}: {best(work) * 1000:.0f} ms")
'''


WHAT_ONE_THREAD_PAYS = Experiment(
    slug="c07-what-one-thread-pays",
    lesson="C07",
    title="Eight single threaded workloads on a build with no GIL",
    asks="What does a build with no GIL charge a program that only ever has one thread?",
    needs=(
        "the question is about a build rather than about a program, and the only way to answer "
        "it is to run the same code on an interpreter configured with --disable-gil and on an "
        "ordinary one, which no single interpreter can do"
    ),
    build="freethreaded",
    program=PROGRAM_EIGHTEEN,
)


WHAT_ONE_THREAD_PAYS_WITH_THE_LOCK = Experiment(
    slug="c07-what-one-thread-pays-with-the-lock",
    lesson="C07",
    title="The same eight workloads on an ordinary build",
    asks="What do the same eight workloads cost on a build that kept the lock?",
    needs=(
        "half of a comparison is not a measurement, and the two halves have to come from images "
        "built the same way on the same hardware or the difference is just noise"
    ),
    build="release",
    program=PROGRAM_EIGHTEEN,
)


#: The program for both c08 recordings, run once on each build.
PROGRAM_NINETEEN = r'''"""Three ways to split work over four cores, and what decides which one wins.

C04 measured four threads against four interpreters and found that interpreters win on a build
with the lock. This asks the next question, which is what it costs to hand work over.

Two workloads. One does a lot of arithmetic on a small argument, so almost nothing has to cross
between interpreters. The other adds up a list that has to be sent across in full, so the
crossing is most of the job. Each is run three ways: one after another, in a pool of threads,
and in a pool of interpreters.

The last few lines time the channel on its own, so you can see roughly what one crossing costs.
"""

import concurrent.interpreters as interpreters
import sys
import time
from concurrent.futures import InterpreterPoolExecutor, ThreadPoolExecutor
from functools import partial


def spin(n):
    total = 0
    for i in range(n):
        total += i * i
    return total


def add_up(numbers):
    return sum(numbers)


def serial(work, jobs):
    return [work(job) for job in jobs]


def pooled(pool_type, work, jobs):
    with pool_type(max_workers=4) as pool:
        return list(pool.map(work, jobs))


def best(run, rounds=3):
    """The fastest of a few runs, which is the honest number on a shared machine."""
    fastest = None
    for _ in range(rounds):
        started = time.perf_counter()
        run()
        taken = time.perf_counter() - started
        fastest = taken if fastest is None else min(fastest, taken)
    return fastest


SMALL = [2000000] * 4
BIG = [list(range(400000)) for _ in range(4)]

print(f"the lock is on: {sys._is_gil_enabled()}")

for label, work, jobs in [("arithmetic", spin, SMALL), ("adding up a big list", add_up, BIG)]:
    one = best(partial(serial, work, jobs))
    threads = best(partial(pooled, ThreadPoolExecutor, work, jobs))
    interps = best(partial(pooled, InterpreterPoolExecutor, work, jobs))
    print(f"~ {label}, one after another: {one * 1000:.0f} ms")
    print(f"~ {label}, four threads: {threads * 1000:.0f} ms")
    print(f"~ {label}, four interpreters: {interps * 1000:.0f} ms")

queue = interpreters.create_queue()
for label, payload in [
    ("a small int", 7),
    ("a thousand byte string", "x" * 1000),
    ("a hundred item list", list(range(100))),
]:
    rounds = 20000
    started = time.perf_counter()
    for _ in range(rounds):
        queue.put(payload)
        queue.get()
    taken = time.perf_counter() - started
    print(f"~ round trips per second, {label}: {rounds / taken:.0f}")
'''


THREE_WAYS_TO_SPLIT_THE_WORK = Experiment(
    slug="c08-three-ways-to-split-the-work",
    lesson="C08",
    title="Two workloads split three ways on a build that has the lock",
    asks="Does handing work to another interpreter pay, and what decides whether it does?",
    needs=(
        "the answer is a ratio between one worker and four, so it has to come from a machine "
        "with a fixed number of cores and nothing else competing for them"
    ),
    build="release",
    program=PROGRAM_NINETEEN,
)


THREE_WAYS_WITHOUT_THE_LOCK = Experiment(
    slug="c08-three-ways-without-the-lock",
    lesson="C08",
    title="The same two workloads split three ways on a build with no lock",
    asks="Once plain threads run in parallel too, is there anything left for interpreters?",
    needs=(
        "it needs an interpreter configured with --disable-gil, which is a separate build "
        "rather than a flag, and it has to be the same image pipeline as the other half or "
        "the two sets of numbers cannot be compared"
    ),
    build="freethreaded",
    program=PROGRAM_NINETEEN,
)


#: The program for both r01 recordings, run once on each build.
PROGRAM_TWENTY = r'''"""What has already happened before your first line runs, and what it cost.

Nothing here is about your code. Every number is the interpreter getting itself ready: reading a
configuration, building a runtime, creating the main interpreter, importing the modules it cannot
run without, working out where the standard library is, and importing site.

The module counts come from a child process asking itself what is in sys.modules before it does
anything. The timings are the fastest of twenty runs of a child that does nothing at all, so what
is being measured is startup and only startup.

Running this on a debug build as well as a release one is the point. The work is identical, the
counts come out the same, and the clock does not, which puts a number on what the assertions and
the reference count bookkeeping cost before your program even begins.
"""

import subprocess
import sys
import time

COUNT = """
import sys
kinds = {"built-in": 0, "frozen": 0, "from a file": 0}
for module in sys.modules.values():
    origin = getattr(getattr(module, "__spec__", None), "origin", None)
    if origin in ("built-in", "frozen"):
        kinds[origin] += 1
    elif origin is not None:
        kinds["from a file"] += 1
print(len(sys.modules), kinds["built-in"], kinds["frozen"], kinds["from a file"])
"""

WAYS = [
    ("everything", []),
    ("no site", ["-S"]),
    ("isolated and no site", ["-I", "-S"]),
]


def child(flags, code):
    """Run a fresh interpreter with those flags and hand back what it printed."""
    done = subprocess.run(
        [sys.executable, *flags, "-c", code], capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


def best(flags, rounds=20):
    """The fastest of a few runs, which is the honest number on a shared machine."""
    fastest = None
    for _ in range(rounds):
        started = time.perf_counter()
        subprocess.run([sys.executable, *flags, "-c", "pass"], capture_output=True, check=True)
        taken = time.perf_counter() - started
        fastest = taken if fastest is None else min(fastest, taken)
    return fastest


def import_cost():
    """Add up the self times that -X importtime prints, in milliseconds."""
    done = subprocess.run(
        [sys.executable, "-X", "importtime", "-c", "pass"], capture_output=True, text=True
    )
    total = 0
    for line in done.stderr.splitlines():
        parts = line.split("|")
        if len(parts) == 3 and parts[0].startswith("import time:"):
            head = parts[0].removeprefix("import time:").strip()
            if head.isdigit():
                total += int(head)
    return total / 1000


print(f"~ this is a debug build: {hasattr(sys, 'gettotalrefcount')}")

for label, flags in WAYS:
    total, builtin, frozen, files = child(flags, COUNT).split()
    print(f"modules at the first line, {label}: {total}")
    print(f"  of those, built into the binary: {builtin}")
    print(f"  of those, frozen bytecode: {frozen}")
    print(f"  of those, read from a file on disk: {files}")

for label, flags in WAYS:
    print(f"~ starting up, {label}: {best(flags) * 1000:.1f} ms")

print(f"~ of that, spent importing: {import_cost():.1f} ms")
'''


WHAT_STARTUP_COSTS = Experiment(
    slug="r01-what-startup-costs",
    lesson="R01",
    title="What the interpreter has already done before your first line, on a release build",
    asks="How much is already loaded before your program starts, and how long did that take?",
    needs=(
        "it starts twenty child interpreters and takes the fastest, so it needs a machine that is "
        "not doing anything else and an interpreter installed the ordinary way rather than a "
        "source tree, because the path search is part of what is being timed"
    ),
    build="release",
    program=PROGRAM_TWENTY,
)


WHAT_STARTUP_COSTS_ON_A_DEBUG_BUILD = Experiment(
    slug="r01-what-startup-costs-on-a-debug-build",
    lesson="R01",
    title="The same startup on a build with the assertions left in",
    asks="Does a debug build do more work at startup, or the same work more slowly?",
    needs=(
        "it needs an interpreter configured with --with-pydebug, and it has to come out of the "
        "same image pipeline as the release half or the two sets of timings cannot be compared"
    ),
    build="debug",
    program=PROGRAM_TWENTY,
)


PROGRAM_TWENTYONE = r'''"""What a second interpreter costs, and which objects the two of them share.

An interpreter is a struct with a few hundred fields in it, and this measures the struct rather
than talking about it. How long one takes to make next to how long an operating system thread
takes, how much resident memory each extra one costs, how many modules a brand new one starts
with, and which objects have the same address on both sides.

That last table is the point of the whole lesson this belongs to. An address that matches means
the object lives in the runtime and every interpreter in the process is looking at the same
bytes. An address that does not match means each interpreter built its own.

Running it on a build without the lock as well as one with it is worth doing because the two
builds do not allocate the same way. A build with the lock gives each interpreter its own
obmalloc pools, and a free threaded build uses mimalloc heaps instead, so the memory each extra
interpreter costs is not the same number and the reason is structural rather than noise.
"""

import concurrent.interpreters as ci
import resource
import sys
import sysconfig
import threading
import time

ASK = """
import sys
out = []
for what, thing in [
    ("None", None),
    ("the int 5", 5),
    ("the int 1024", 1024),
    ("the int 1025", 1025),
    ("the one character string a", "a"),
    ("the type object int", int),
    ("the sys module", sys),
    ("the builtins dict", __builtins__),
]:
    out.append((what, id(thing)))
out.append(("how many modules", len(sys.modules)))
post.put(tuple(out))
"""


def best(make, rounds=20):
    """The fastest of a few goes, in microseconds, which is the honest number here."""
    fastest = None
    for _ in range(rounds):
        started = time.perf_counter()
        make()
        taken = time.perf_counter() - started
        fastest = taken if fastest is None else min(fastest, taken)
    return fastest * 1_000_000


def make_a_thread():
    """Start an operating system thread that does nothing and wait for it to finish."""
    worker = threading.Thread(target=lambda: None)
    worker.start()
    worker.join()


def make_an_interpreter():
    """Make a whole interpreter and throw it away again."""
    ci.create().close()


def resident_kb():
    """Peak resident memory in kilobytes. Linux reports kilobytes, macOS reports bytes."""
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return raw if sys.platform.startswith("linux") else raw / 1024


print(f"~ this build has the lock: {not sysconfig.get_config_var('Py_GIL_DISABLED')}")

print(f"~ starting an os thread: {best(make_a_thread):.0f} us")
print(f"~ making an interpreter: {best(make_an_interpreter):.0f} us")

before = resident_kb()
held = [ci.create() for _ in range(10)]
after = resident_kb()
print(f"~ resident memory each extra interpreter costs: {(after - before) / 10:.0f} kB")

post = ci.create_queue()
worker = held[0]
worker.prepare_main(post=post)
worker.exec(ASK)
theirs = dict(post.get())

here = {}
exec(ASK.replace("post.put(tuple(out))", "pass"), here)
mine = dict(here["out"])

for what in mine:
    if what == "how many modules":
        continue
    print(f"same address in both interpreters, {what}: {mine[what] == theirs[what]}")

print(f"modules a brand new interpreter starts with: {theirs['how many modules']}")

for one in held:
    one.close()
'''


WHAT_A_SECOND_INTERPRETER_COSTS = Experiment(
    slug="r02-what-a-second-interpreter-costs",
    lesson="R02",
    title="What an interpreter costs to make, and what two of them share",
    asks="How expensive is a whole interpreter next to a thread, and what do two of them share?",
    needs=(
        "it reads peak resident memory out of the operating system and makes ten interpreters at "
        "once, so it needs a machine with a known memory reporting unit and nothing else running "
        "on it, and it has to be the same machine as the other half of the pair"
    ),
    build="release",
    program=PROGRAM_TWENTYONE,
)


WHAT_A_SECOND_INTERPRETER_COSTS_WITHOUT_THE_LOCK = Experiment(
    slug="r02-what-a-second-interpreter-costs-without-the-lock",
    lesson="R02",
    title="The same interpreter, on a build that allocates differently",
    asks="Does an interpreter cost the same to make and to keep on a build with no lock?",
    needs=(
        "it needs a build configured with --disable-gil, because the whole question is whether "
        "mimalloc heaps and obmalloc pools charge the same for one more interpreter"
    ),
    build="freethreaded",
    program=PROGRAM_TWENTYONE,
)


PROGRAM_TWENTYTWO = r'''"""How much of an import runs in parallel, and what the lock protects.

Importing takes a lock, and it is easy to read that as one import at a time for the whole process.
It has not meant that since 3.3. There is a lock per module name, so two threads importing two
different modules do not wait for each other, and two threads importing the same module do, with
only one of them running the body.

The module bodies here burn processor time rather than sleeping, which is what makes the answer
depend on the build. The number to read is how many cores the process kept busy, because that is
processor time over wall clock and it does not care how fast the machine is or which core it got.
One means the work went through a queue. Four means it really did overlap.

The same module asked for by four threads is the control. It should be one on both builds, because
the per module lock is doing exactly what it says, and the count at the end proves only one thread
ever ran the body.

The last number is the other half of the story. Almost every import a running program performs is
a hit in sys.modules, which is a dict lookup and nothing else.
"""

import os
import sys
import sysconfig
import tempfile
import threading
import time
from pathlib import Path

BODY = "total = 0\nfor i in range(2_500_000):\n    total += i\n"
SEEN = "import counted\n\ncounted.times += 1\n" + BODY


def busy(work):
    """Wall clock seconds, and processor time over it, which is how many cores were kept busy."""
    wall, cpu = time.perf_counter(), time.process_time()
    work()
    wall = time.perf_counter() - wall
    return wall, (time.process_time() - cpu) / wall


def in_threads(names):
    """Import each of those names on a thread of its own and wait for all of them."""
    workers = [threading.Thread(target=__import__, args=(name,)) for name in names]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()


folder = Path(tempfile.mkdtemp())
(folder / "counted.py").write_text("times = 0\n")
for which in range(5):
    (folder / f"slow{which}.py").write_text(BODY)
(folder / "same0.py").write_text(SEEN)
sys.path.insert(0, str(folder))

print(f"~ this build has the lock: {not sysconfig.get_config_var('Py_GIL_DISABLED')}")
print(f"~ processors the container will let the program use: {os.process_cpu_count()}")

alone, _ = busy(lambda: __import__("slow4"))
print(f"~ one module on one thread: {alone * 1000:.0f} ms")

wall, cores = busy(lambda: in_threads([f"slow{n}" for n in (0, 1, 2, 3)]))
print(f"~ four different modules on four threads: {wall * 1000:.0f} ms")
print(f"~ modules loaded per second against one thread: {4 * alone / wall:.2f}")
print(f"~ cores kept busy while four different modules loaded: {cores:.2f}")

wall, cores = busy(lambda: in_threads(["same0"] * 4))
print(f"~ the same module asked for by four threads: {wall * 1000:.0f} ms")
print(f"~ cores kept busy while the same module was asked for: {cores:.2f}")

counted = __import__("counted")
print(f"times the body of that one module actually ran: {counted.times}")

rounds = 200_000
started = time.perf_counter()
for _ in range(rounds):
    __import__("slow0")
each = (time.perf_counter() - started) / rounds * 1_000_000_000
print(f"~ asking again for a module already in sys.modules: {each:.0f} ns")
'''


HOW_MUCH_OF_AN_IMPORT_IS_PARALLEL = Experiment(
    slug="r03-how-much-of-an-import-is-parallel",
    lesson="R03",
    title="Four threads importing four modules, on a build that takes turns",
    asks="Does the import lock stop two threads importing at once, or does something else?",
    needs=(
        "it wants at least four processors that are not busy with anything else, because every "
        "number in it is a wall clock reading over work that is deliberately processor bound"
    ),
    build="release",
    program=PROGRAM_TWENTYTWO,
)


HOW_MUCH_OF_AN_IMPORT_IS_PARALLEL_WITHOUT_THE_LOCK = Experiment(
    slug="r03-how-much-of-an-import-is-parallel-without-the-lock",
    lesson="R03",
    title="The same four imports on a build where threads really do overlap",
    asks="With the GIL out of the way, do four imports on four threads finish in the time of one?",
    needs=(
        "it needs a build configured with --disable-gil and the same four idle processors, since "
        "the whole question is what is left holding the imports up once the GIL is not"
    ),
    build="freethreaded",
    program=PROGRAM_TWENTYTWO,
)


PROGRAM_TWENTYTHREE = r'''"""What freezing the standard library into the binary is worth at startup.

Import is written in Python, so it cannot be imported. CPython gets around that by compiling a
handful of modules during its own build and writing the bytecode into the binary as C arrays. The
first three are the import system itself, and they are what lets the interpreter get going at all.

Everything after those three is a speed decision rather than a correctness one, and it can be
switched off with -X frozen_modules=off, so the cost of it can be measured rather than guessed.
Which way the switch sits by default is a build choice, so this program never relies on the
default. It asks for on and off explicitly and reports what the default happens to be.

Two numbers matter. The first is how many code objects a bare startup reads off disk, which -v
prints one line for, so it is a count rather than a timing and it is the same on any machine. The
second is wall clock, measured with the two cases alternating, because anything that runs one case
forty times and then the other forty times is measuring the state of the page cache instead.
"""

import _imp
import statistics
import subprocess
import sys
import time

ROUNDS = 40
ON = ["-X", "frozen_modules=on"]
OFF = ["-X", "frozen_modules=off"]
ORIGIN = "import os; print(os.__spec__.origin)"
BOOTSTRAP = "import sys; print(sys.modules['_frozen_importlib'].__spec__.origin)"
COUNT = (
    "import sys\n"
    "specs = [getattr(m, '__spec__', None) for m in sys.modules.values()]\n"
    "print(len(sys.modules), sum(1 for s in specs if s is not None and s.origin == 'frozen'))\n"
)


def child(flags, args):
    """Run this same interpreter again with those flags and hand back the finished process."""
    return subprocess.run(
        [sys.executable, *flags, *args], capture_output=True, text=True, check=True
    )


def origin(flags):
    """Ask a fresh interpreter where the os module it just imported came from."""
    return child(flags, ["-c", ORIGIN]).stdout.strip()


def loaded(flags):
    """Ask a fresh interpreter how many modules it loaded and how many came out of the binary."""
    return [int(part) for part in child(flags, ["-c", COUNT]).stdout.split()]


def files_read(flags):
    """Count the code objects a fresh interpreter reads off disk, which -v prints one per line."""
    printed = child(flags, ["-v", "-c", "pass"]).stderr
    return sum(1 for line in printed.splitlines() if line.startswith("# code object from"))


def import_work(flags):
    """Add up the self time -X importtime reports, in microseconds."""
    printed = child(["-X", "importtime", *flags], ["-c", "pass"]).stderr
    total = 0
    for line in printed.splitlines():
        if line.startswith("import time:"):
            first = line.removeprefix("import time:").split("|")[0].strip()
            if first.isdigit():
                total += int(first)
    return total


def startup_ms(flags):
    """Wall clock milliseconds for one whole interpreter startup that does nothing at all."""
    started = time.perf_counter()
    child(flags, ["-c", "pass"])
    return (time.perf_counter() - started) * 1000


def alternating(measure, rounds):
    """Measure both cases once each per round, so neither one gets the cold cache every time."""
    got = {"on": [], "off": []}
    for _ in range(rounds):
        got["on"].append(measure(ON))
        got["off"].append(measure(OFF))
    return got


_imp._override_frozen_modules_for_tests(1)
names = _imp._frozen_module_names()
frozen_os = _imp.get_frozen_object("os")
_imp._override_frozen_modules_for_tests(0)

print("names compiled into this binary:", len(names))
print("the three that cannot be turned off:", ", ".join(names[:3]))
print("filename on the frozen code object for os:", frozen_os.co_filename)
print("bytes of bytecode in it:", len(frozen_os.co_code))
print("this build uses them unless told otherwise:", origin([]) == "frozen")
print("where os comes from with the flag on:", origin(ON))
print("where os comes from with the flag off:", origin(OFF).rpartition("/")[2])
print("_frozen_importlib with the flag off:", child(OFF, ["-c", BOOTSTRAP]).stdout.strip())

on_total, on_frozen = loaded(ON)
off_total, off_frozen = loaded(OFF)
print("modules a bare startup loads, flag on:", on_total)
print("modules a bare startup loads, flag off:", off_total)
print("of those, frozen with the flag on:", on_frozen)
print("of those, frozen with the flag off:", off_frozen)
print("code objects read off disk with the flag on:", files_read(ON))
print("code objects read off disk with the flag off:", files_read(OFF))

work = alternating(import_work, 10)
print(f"~ import work reported by importtime, frozen on: {min(work['on'])} us")
print(f"~ import work reported by importtime, frozen off: {min(work['off'])} us")

runs = alternating(startup_ms, ROUNDS)
fast_on, fast_off = min(runs["on"]), min(runs["off"])
print(f"~ fastest startup with the flag on: {fast_on:.1f} ms")
print(f"~ fastest startup with the flag off: {fast_off:.1f} ms")
print(f"~ middle startup with the flag on: {statistics.median(runs['on']):.1f} ms")
print(f"~ middle startup with the flag off: {statistics.median(runs['off']):.1f} ms")
share = (1 - fast_on / fast_off) * 100
print(f"~ share of a startup that freezing gives back: {share:.1f} percent")
'''


WHAT_FREEZING_SAVES_AT_STARTUP = Experiment(
    slug="r04-what-freezing-saves-at-startup",
    lesson="R04",
    title="A startup with the frozen standard library, and the same startup without it",
    asks="What does compiling the standard library into the binary actually save at startup?",
    needs=(
        "it wants a machine that is not busy with anything else, because half of what it reports "
        "is wall clock for a process that only lives for a few milliseconds"
    ),
    build="release",
    program=PROGRAM_TWENTYTHREE,
)


WHAT_FREEZING_SAVES_ON_A_DEBUG_BUILD = Experiment(
    slug="r04-what-freezing-saves-on-a-debug-build",
    lesson="R04",
    title="The same two startups on a build that does not use the frozen copies",
    asks="Does a debug build behave the same way, and does freezing still pay for itself there?",
    needs=(
        "it needs a build configured with --with-pydebug, which is the one build that leaves the "
        "frozen copies switched off by default, so the same program reports a different default"
    ),
    build="debug",
    program=PROGRAM_TWENTYTHREE,
)


PROGRAM_TWENTYFOUR = r'''"""What deferring an import until somebody touches the name is worth.

A program that imports twelve standard library modules at the top and then uses one of them is
not a strawman, it is what most command line tools look like. PEP 810 adds a spelling that says
bind this name now and do the work later, and a mode that applies the same rule to every plain
import in the file, so the cost of the eleven you did not need can be measured rather than
argued about.

The child processes here run the same source twice, once with the default mode and once with
-X lazy_imports=all. Three kinds of number come back. How many modules end up in sys.modules is
a count, so it is the same on any machine. How many code objects the interpreter reads off disk
is also a count, and -v prints one line for each. Wall clock is the one that depends on the
machine, and it is measured with the two cases alternating, because running one case forty
times and then the other measures the page cache instead.
"""

import statistics
import subprocess
import sys
import time

ROUNDS = 40
LAZY = ["-X", "lazy_imports=all"]
MODULES = (
    "argparse",
    "csv",
    "dataclasses",
    "email.parser",
    "http.client",
    "json",
    "logging",
    "sqlite3",
    "typing",
    "unittest",
    "urllib.request",
    "xml.etree.ElementTree",
)
BODY = "\n".join("import " + name for name in MODULES)
WORK = "print(json.dumps({'used': 1}))"
COUNT = "import sys; print(len(sys.modules), len(sys.lazy_modules))"


def child(flags, args):
    """Run this same interpreter again with those flags and hand back the finished process."""
    return subprocess.run(
        [sys.executable, *flags, *args], capture_output=True, text=True, check=True
    )


def asked(question):
    """Ask a fresh interpreter one question and hand back the single line it prints."""
    return child([], ["-c", "import sys; print({})".format(question)]).stdout.strip()


def loaded(flags):
    """Import the twelve, use one, and ask how many modules the process ended up with."""
    printed = child(flags, ["-c", BODY + "\n" + WORK + "\n" + COUNT + "\n"]).stdout
    return [int(part) for part in printed.splitlines()[-1].split()]


def files_read(flags):
    """Count the code objects the run reads off disk, which -v prints one line for."""
    printed = child(flags, ["-v", "-c", BODY + "\n" + WORK + "\n"]).stderr
    return sum(1 for line in printed.splitlines() if line.startswith("# code object from"))


def run_ms(flags):
    """Wall clock milliseconds for one whole run, startup included."""
    started = time.perf_counter()
    child(flags, ["-c", BODY + "\n" + WORK + "\n"])
    return (time.perf_counter() - started) * 1000


def alternating(rounds):
    """Measure both cases once each per round, so neither one gets the cold cache every time."""
    got = {"eager": [], "lazy": []}
    for _ in range(rounds):
        got["eager"].append(run_ms([]))
        got["lazy"].append(run_ms(LAZY))
    return got


print("modules this program imports at the top:", len(MODULES))
print("modules it actually uses:", 1)
print("the mode this build starts in:", asked("sys.get_lazy_imports()"))
print("names the standard library defers at startup:", asked("len(sys.lazy_modules)"))
print("which names those are:", asked("sorted(sys.lazy_modules)"))

eager_total, eager_waiting = loaded([])
lazy_total, lazy_waiting = loaded(LAZY)
print("modules in sys.modules at the end, eager:", eager_total)
print("modules in sys.modules at the end, lazy:", lazy_total)
print("names still waiting in sys.lazy_modules, eager:", eager_waiting)
print("names still waiting in sys.lazy_modules, lazy:", lazy_waiting)
print("code objects read off disk, eager:", files_read([]))
print("code objects read off disk, lazy:", files_read(LAZY))

runs = alternating(ROUNDS)
fast_eager, fast_lazy = min(runs["eager"]), min(runs["lazy"])
print("~ fastest run with plain imports: {:.1f} ms".format(fast_eager))
print("~ fastest run with lazy imports: {:.1f} ms".format(fast_lazy))
print("~ middle run with plain imports: {:.1f} ms".format(statistics.median(runs["eager"])))
print("~ middle run with lazy imports: {:.1f} ms".format(statistics.median(runs["lazy"])))
share = (1 - fast_lazy / fast_eager) * 100
print("~ share of the run that deferring gives back: {:.1f} percent".format(share))
'''


PROGRAM_TWENTYFIVE = r'''"""What happens when several threads wake up deferred imports at once.

An ordinary import takes a lock on the name being imported, so two threads importing two
different modules do not wait for each other. Waking up a deferred import is a different code
path, and _PyImport_LoadLazyImportTstate takes the interpreter wide import lock instead, and
holds it for as long as the module body runs.

That difference is invisible on a build with the global interpreter lock, because nothing runs
in parallel there anyway. On a free threaded build it should be visible, and this program is
the measurement. Both cases are reported as cores kept busy, which is processor time divided by
wall clock, because that is the only honest way to compare several threads against one on a
machine whose scheduler moves work between cores.

Each generated module burns processor time in its body rather than sleeping, so a case that
really overlaps reads well above one core and a case that takes turns reads about one.
"""

import importlib
import os
import pathlib
import sys
import tempfile
import threading
import time

THREADS = 4
BURN = 3_000_000
SOURCE = "total = 0\nfor i in range({burn}):\n    total += i\nBURNED = total\n"

folder = pathlib.Path(tempfile.mkdtemp())
sys.path.insert(0, str(folder))


def write_modules(prefix):
    """Write one module per thread, each of which does real arithmetic in its body."""
    names = []
    for index in range(THREADS):
        name = "{}_{}".format(prefix, index)
        (folder / (name + ".py")).write_text(SOURCE.format(burn=BURN))
        names.append(name)
    return names


def toucher(name):
    """Build a function whose body reads that global, because reading it is what wakes it up."""
    namespace = {}
    body = "def touch():\n    return {}.BURNED\n".format(name)
    exec(compile(body, "<touch>", "exec"), globals(), namespace)
    return namespace["touch"]


def together(jobs):
    """Run one thread per job, all released at the same instant, and time the whole batch."""
    ready = threading.Barrier(len(jobs))
    seen = []

    def work(job):
        ready.wait()
        seen.append(job())

    threads = [threading.Thread(target=work, args=(job,)) for job in jobs]
    wall = time.perf_counter()
    cpu = time.process_time()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    wall = time.perf_counter() - wall
    cpu = time.process_time() - cpu
    return len(seen), wall, cpu / wall


def one_thread():
    """The same arithmetic on one thread, as a reading of what one busy core looks like here."""
    wall = time.perf_counter()
    cpu = time.process_time()
    total = 0
    for i in range(BURN):
        total += i
    wall = time.perf_counter() - wall
    return (time.process_time() - cpu) / wall, wall


plain = write_modules("plain")
deferred = write_modules("deferred")
exec(compile("\n".join("lazy import " + name for name in deferred), "<declare>", "exec"), globals())

print("threads:", THREADS)
print("processors this container can see:", os.process_cpu_count())
print("gil enabled:", sys._is_gil_enabled())
print("names declared and still waiting:", sum(1 for n in deferred if n in sys.lazy_modules))
print("any of them in sys.modules yet:", any(n in sys.modules for n in deferred))

control_cores, control_wall = one_thread()

done, wall_plain, cores_plain = together([lambda n=n: importlib.import_module(n) for n in plain])
print("threads that finished a plain import:", done)

done, wall_lazy, cores_lazy = together([toucher(n) for n in deferred])
print("threads that woke up a deferred import:", done)
print("all of them in sys.modules now:", all(n in sys.modules for n in deferred))
print("names still waiting afterwards:", sum(1 for n in deferred if n in sys.lazy_modules))

print("~ cores kept busy by one thread doing the arithmetic: {:.2f}".format(control_cores))
print("~ cores kept busy importing four modules the plain way: {:.2f}".format(cores_plain))
print("~ cores kept busy waking four deferred imports: {:.2f}".format(cores_lazy))
print("~ wall clock for one thread, ms: {:.0f}".format(control_wall * 1000))
print("~ wall clock for the plain imports, ms: {:.0f}".format(wall_plain * 1000))
print("~ wall clock for the deferred ones, ms: {:.0f}".format(wall_lazy * 1000))
'''


WHAT_DEFERRING_AN_IMPORT_IS_WORTH = Experiment(
    slug="r05-what-deferring-an-import-is-worth",
    lesson="R05",
    title="Twelve imports at the top of a file, once as written and once deferred",
    asks="What does a program get back for not importing what it turns out not to need?",
    needs=(
        "it wants a machine that is not busy with anything else, because half of what it "
        "reports is wall clock for a process that only lives for a fraction of a second"
    ),
    build="release",
    program=PROGRAM_TWENTYFOUR,
)


HOW_MUCH_OF_A_WAKE_UP_IS_PARALLEL = Experiment(
    slug="r05-how-much-of-a-wake-up-is-parallel",
    lesson="R05",
    title="Four threads reaching for four different deferred imports, with the lock on",
    asks="Do two threads waking up two different deferred imports wait for each other?",
    needs=(
        "it needs several processors and a quiet machine, because the answer is a ratio of "
        "processor time to wall clock and both halves of that move when something else runs"
    ),
    build="release",
    program=PROGRAM_TWENTYFIVE,
)


HOW_MUCH_OF_A_WAKE_UP_IS_PARALLEL_WITHOUT_THE_LOCK = Experiment(
    slug="r05-how-much-of-a-wake-up-is-parallel-without-the-lock",
    lesson="R05",
    title="The same four threads on the build that can really run them at the same time",
    asks="With the global interpreter lock gone, does waking up a deferred import scale?",
    needs=(
        "it needs a build configured with --disable-gil, because the comparison only means "
        "anything once the global interpreter lock has stopped serialising everything anyway"
    ),
    build="freethreaded",
    program=PROGRAM_TWENTYFIVE,
)


PROGRAM_TWENTYSIX = r'''"""Which of the C API's private declarations actually leave the binary.

The headers put the C API in three directories. `Include/` is what any extension may use,
`Include/cpython/` is the part that only makes sense compiled against this exact CPython, and
`Include/internal/` says at the top of nearly every file that it will not compile unless you
claim to be CPython itself.

That is all a compile time arrangement. This program asks what survives into the built
interpreter, by taking every name the headers declare and asking the dynamic linker for it
through `ctypes.pythonapi`. A name that resolves is a name any program can call, whatever the
header said about it.

The interesting split is inside the internal headers, which use two different spellings.
`PyAPI_FUNC` means the symbol leaves the shared library. A plain `extern` means it does not.
Both spellings sit in the same file, often two lines apart.
"""

import ctypes
import pathlib
import re
import sys
import sysconfig
from collections import Counter

API = re.compile(r"^PyAPI_FUNC\([^)]*\)\s*\**\s*(\w+)", re.M)
EXTERN = re.compile(r"^extern\s+[\w *]+?\**\s*(\w+)\s*\(", re.M)
NOTE = re.compile(r"^//\s*Export for (.+?)\.?$", re.M)

TIERS = (("public", "*.h"), ("cpython only", "cpython/*.h"), ("internal", "internal/*.h"))

api = ctypes.pythonapi
include = pathlib.Path(sysconfig.get_paths()["include"])


def resolves(name):
    """Ask the linker for a name, the way any program with a handle on the process can."""
    return hasattr(api, name)


def read(pattern):
    """Every header matching the pattern, as one blob of text per file."""
    return [path.read_text(errors="replace") for path in sorted(include.glob(pattern))]


print("include directory:", include)
print("build has the gil disabled:", sysconfig.get_config_var("Py_GIL_DISABLED"))
print("abi flags:", repr(sys.abiflags))
print()

for tier, pattern in TIERS:
    blobs = read(pattern)
    declared = set()
    for blob in blobs:
        declared |= set(API.findall(blob))
    found = sum(1 for name in declared if resolves(name))
    print(f"{tier}: {len(blobs)} header files")
    print(f"  declared with PyAPI_FUNC: {len(declared)}")
    print(f"  of those, resolve in this process: {found}")

internal = read("internal/*.h")
exported = set()
kept_in = set()
notes = []
for blob in internal:
    exported |= set(API.findall(blob))
    kept_in |= set(EXTERN.findall(blob))
    notes += NOTE.findall(blob)
kept_in -= exported

leaked = sum(1 for name in exported if resolves(name))
held = sum(1 for name in kept_in if resolves(name))

print()
print("inside the internal headers")
print("  names spelled PyAPI_FUNC:", len(exported))
print("  names spelled plain extern:", len(kept_in))
print("  comments naming who needs the export:", len(notes))
for who, count in Counter(notes).most_common(5):
    print(f"    {count} for {who}")

print()
exported_share = leaked / len(exported) * 100
extern_share = held / len(kept_in) * 100
print("~ private names that leave the binary: {}".format(leaked))
print("~ share of PyAPI_FUNC internal names that resolve: {:.1f} percent".format(exported_share))
print("~ share of plain extern internal names that resolve: {:.1f} percent".format(extern_share))
'''


WHAT_LEAVES_THE_BINARY = Experiment(
    slug="r06-what-leaves-the-binary",
    lesson="R06",
    title="Every name the headers declare, handed to the linker one at a time",
    asks="How much of the C API that the headers call private is callable anyway?",
    needs=(
        "it needs the headers next to the interpreter, which a normal install has and a "
        "browser tab does not, and it needs ctypes to reach the process it is running in"
    ),
    build="release",
    program=PROGRAM_TWENTYSIX,
)


WHAT_LEAVES_THE_BINARY_ON_A_FREE_THREADED_BUILD = Experiment(
    slug="r06-what-leaves-the-binary-on-a-free-threaded-build",
    lesson="R06",
    title="The same sweep on the build that compiles a different half of the headers",
    asks="Does dropping the global interpreter lock change what the C API exports?",
    needs=(
        "it needs a build configured with --disable-gil, because the question is whether the "
        "names behind Py_GIL_DISABLED are the ones that were missing on the ordinary build"
    ),
    build="freethreaded",
    program=PROGRAM_TWENTYSIX,
)


PROGRAM_TWENTYSEVEN = r'''"""What a build agrees to load, and the two gates that decide it.

An extension arrives as a file with a long name. The interpreter decides whether to consider
it at all from that name alone, before it opens it. If it does open it, and the extension was
built against 3.15 or later, there is a second gate: a five field `PyABIInfo` struct the
extension carries, which `PyABIInfo_Check` compares against the running interpreter.

This program runs both gates by hand. It asks the finder which file names it is willing to
look at, by putting empty files in a temporary directory and asking for the module. Then it
builds `PyABIInfo` structs in ctypes for a row of hypothetical extensions and calls the real
check function on each one.

The point of running it on two builds is that both gates move. A free threaded build will not
look at a name with `abi3` in it, and it refuses a struct that says the extension wants the
global interpreter lock.

One thing is printed differently from how the interpreter spells it. The last part of a file
name tag is the machine the build was made for, which is `x86_64-linux-gnu` on one runner and
`aarch64-linux-gnu` on another. That part says nothing about the ABI question, so it is
replaced with the word `PLATFORM` everywhere below and the recording is the same either way.
"""

import ctypes
import importlib.machinery
import pathlib
import re
import sys
import sysconfig
import tempfile

VERSIONED = re.compile(r"(cpython-)(\d+)(t?)")

STABLE = 0x0001
GIL = 0x0002
FREETHREADED = 0x0004
INTERNAL = 0x0008


class PyABIInfo(ctypes.Structure):
    """The struct an extension built against 3.15 or later carries about itself."""

    _fields_ = [
        ("abiinfo_major_version", ctypes.c_uint8),
        ("abiinfo_minor_version", ctypes.c_uint8),
        ("flags", ctypes.c_uint16),
        ("build_version", ctypes.c_uint32),
        ("abi_version", ctypes.c_uint32),
    ]


def pack(major, minor):
    """The version format the C API uses, which is the two numbers in the top two bytes."""
    return (major << 24) | (minor << 16)


def considered(name):
    """Put one empty file in a directory of its own and ask whether the finder sees it."""
    room = pathlib.Path(tempfile.mkdtemp())
    (room / name).write_bytes(b"")
    return importlib.machinery.PathFinder.find_spec("demo", [str(room)]) is not None


TAGS = importlib.machinery.EXTENSION_SUFFIXES
here = sysconfig.get_config_var("EXT_SUFFIX")
flipped = VERSIONED.sub(lambda m: m.group(1) + m.group(2) + ("" if m.group(3) else "t"), here)
future = VERSIONED.sub(lambda m: m.group(1) + "999" + m.group(3), here)
machine = re.sub(r"^\.cpython-\d+t?-?", "", here).removesuffix(".so")


def tidy(text):
    """Take the machine out of a file name tag, since it says nothing about the ABI."""
    return text.replace(machine, "PLATFORM") if machine else text


print("version:", sys.version.split()[0])
print("abiflags:", repr(sys.abiflags))
print("gil disabled:", sysconfig.get_config_var("Py_GIL_DISABLED"))
print("soabi:", tidy(sysconfig.get_config_var("SOABI")))
print("api version, unchanged since 2006:", sys.api_version)
print()

print("file name tags this build will load:")
for suffix in TAGS:
    print("   ", tidy(suffix))
print()

print("what the finder does with one file of each kind")
for name in ("demo" + here, "demo" + flipped, "demo" + future, "demo.abi3.so", "demo.abi3t.so"):
    verdict = "considered" if considered(name) else "invisible, the name is wrong"
    print(f"  {tidy(name):34} {verdict}")
print()

check = ctypes.pythonapi.PyABIInfo_Check
check.argtypes = [ctypes.POINTER(PyABIInfo), ctypes.c_char_p]
check.restype = ctypes.c_int

CASES = (
    ("built for this exact version", GIL, pack(*sys.version_info[:2])),
    ("built for 3.13 and nothing else", GIL, pack(3, 13)),
    ("stable abi since 3.2", STABLE | GIL, pack(3, 2)),
    ("stable abi since 3.14", STABLE | GIL, pack(3, 14)),
    ("stable abi from the future", STABLE | GIL, pack(3, 99)),
    ("free threaded only", STABLE | FREETHREADED, pack(3, 14)),
    ("happy either way", STABLE | GIL | FREETHREADED, pack(3, 14)),
    ("claims internal and stable", STABLE | INTERNAL | GIL, sys.hexversion),
)

print("what PyABIInfo_Check makes of each kind of extension")
refused = 0
for label, flags, version in CASES:
    info = PyABIInfo(1, 0, flags, sys.hexversion, version)
    try:
        check(ctypes.byref(info), label.encode())
    except ImportError as problem:
        refused += 1
        print(f"  {label:32} refused: {str(problem).split(': ', 1)[1]}")
    else:
        print(f"  {label:32} loads")
print()

DECLARED = re.compile(r"^PyAPI_FUNC\([^)]*\)\s*\**\s*(\w+)", re.M)
OPENS = re.compile(r"^\s*#\s*if")
CLOSES = re.compile(r"^\s*#\s*endif")
OLD = re.compile(r"Py_LIMITED_API\+0\s*>=\s*0x03([0-9a-fA-F]{2})0000")
NEW = re.compile(r"Py_LIMITED_API\+0\s*>=\s*_Py_PACK_VERSION\((\d+),\s*(\d+)\)")


def gate(line):
    """The stable ABI version a preprocessor line gates on, when it gates on one."""
    found = NEW.search(line)
    if found:
        return int(found.group(2))
    found = OLD.search(line)
    return int(found.group(1), 16) if found else None


include = pathlib.Path(sysconfig.get_paths()["include"])
arrived = {}
for path in sorted(include.glob("*.h")):
    stack = []
    for line in path.read_text(errors="replace").splitlines():
        if OPENS.match(line):
            stack.append(gate(line))
        elif CLOSES.match(line) and stack:
            stack.pop()
        found = DECLARED.match(line)
        if found and any(v for v in stack):
            arrived[found.group(1)] = max(v for v in stack if v)

print("when the public headers say each gated function arrived")
counted = {}
for version in arrived.values():
    counted[version] = counted.get(version, 0) + 1
for version in sorted(counted):
    print(f"  3.{version:<4} {counted[version]:4}")
print()

print(f"~ file name tags this build will load: {len(TAGS)}")
print(f"~ hypothetical extensions refused: {refused} of {len(CASES)}")
print(f"~ public functions behind a stable abi version gate: {len(arrived)}")
'''


WHAT_A_BUILD_WILL_LOAD = Experiment(
    slug="r07-what-a-build-will-load",
    lesson="R07",
    title="Both gates an extension has to pass, run by hand on an ordinary build",
    asks="What does the interpreter check before it agrees to load an extension?",
    needs=(
        "it needs 3.15 for PyABIInfo_Check, the headers next to the interpreter for the version "
        "gate scan, and a real filesystem to put the empty files in"
    ),
    build="release",
    program=PROGRAM_TWENTYSEVEN,
)


WHAT_A_BUILD_WILL_LOAD_WITHOUT_THE_LOCK = Experiment(
    slug="r07-what-a-build-will-load-without-the-lock",
    lesson="R07",
    title="The same two gates on the build that abi3t was invented for",
    asks="How much of the stable ABI does dropping the global interpreter lock rule out?",
    needs=(
        "it needs a build configured with --disable-gil, because the whole question is which "
        "file names and which ABI flags that build is willing to accept"
    ),
    build="freethreaded",
    program=PROGRAM_TWENTYSEVEN,
)


PROGRAM_TWENTYEIGHT = r'''"""Nine ways a process can end, and what each one still runs.

Shutdown is the part of the runtime with the fewest promises, and the only honest way to watch
it is from outside. So this program starts a child interpreter for each hazard and reports
what the child managed to run and what status it left behind.

Every child registers an atexit callback and keeps one object with a finalizer in a module
global. Whether those two things run is the whole question, and the answer is not always yes.

On a debug build there is one more section. `-X showrefcount` prints how many references and
how many allocated blocks were still there when the interpreter stopped, so the cost of the
one case that goes wrong can be counted rather than described.
"""

import re
import subprocess
import sys

PREAMBLE = """
import atexit, os, sys


def note(label, _w=os.write, _f=sys.is_finalizing):
    _w(2, f"{label} finalizing={_f()}\\n".encode())


class Late:
    def __del__(self, _note=note):
        _note("finalizer")


def snooze():
    import time
    time.sleep(30)


atexit.register(note, "atexit")
keeper = Late()
"""

CASES = (
    ("an ordinary exit", ""),
    ("sys.exit with a status", "sys.exit(3)"),
    ("an unhandled exception", "raise SystemError('on purpose')"),
    ("os._exit, which skips everything", "os._exit(0)"),
    ("an atexit callback that raises", "atexit.register(lambda: 1 / 0)"),
    (
        "a finalizer that raises",
        "class Angry:\n    def __del__(self):\n        1 / 0\nbad = Angry()",
    ),
    (
        "a daemon thread inside time.sleep",
        "import threading, time\n"
        "threading.Thread(target=time.sleep, args=(30,), daemon=True).start()",
    ),
    (
        "a daemon thread running your code",
        "import threading\nthreading.Thread(target=snooze, daemon=True).start()",
    ),
    ("a subinterpreter nobody closed", "import concurrent.interpreters as it\nkid = it.create()"),
)

ORDER = """
import atexit, os, sys, threading, time


def note(label, _w=os.write, _f=sys.is_finalizing):
    _w(2, f"  {label:38} finalizing={_f()}\\n".encode())


class Late:
    def __init__(self, label):
        self.label = label

    def __del__(self, _note=note):
        _note(f"finalizer of {self.label}")


def worker():
    time.sleep(0.2)
    note("a thread you started finishing")


atexit.register(note, "atexit registered first")
atexit.register(note, "atexit registered second")
keeper = Late("a module global")
threading.Thread(target=worker).start()
note("your last line")
"""

HELD = """
import atexit, os, sys


def snooze():
    import time
    time.sleep(30)


class Held:
    pass


keeper = [Held() for _ in range(5000)]
"""

SHAPES = (
    ("nothing left behind", ""),
    ("five thousand objects in a module global", HELD),
    (
        "the same, plus a daemon thread running your code",
        HELD + "import threading\nthreading.Thread(target=snooze, daemon=True).start()\n",
    ),
)

LEFTOVER = re.compile(r"\[(\d+) refs, (\d+) blocks\]")


def run(program, flags=()):
    """Start a child interpreter with that program and hand back what it did."""
    return subprocess.run(
        [sys.executable, *flags, "-c", program], capture_output=True, text=True, timeout=180
    )


def leftover(program):
    """What a debug build reports was still alive after it finished shutting down."""
    found = LEFTOVER.search(run(program, ("-X", "showrefcount")).stderr)
    return (int(found.group(1)), int(found.group(2))) if found else None


DEBUG = hasattr(sys, "gettotalrefcount")

print("version:", sys.version.split()[0])
print("debug build:", DEBUG)
print("free threaded:", hasattr(sys, "_is_gil_enabled") and not sys._is_gil_enabled())
print()

print("the order things happen in, watched from one child")
for line in run(ORDER).stderr.splitlines():
    print(line.rstrip())
print()

print("what each kind of ending still runs")
print(f"  {'the child':38} {'status':>6} {'atexit':>7} {'finalizer':>10}  warned")
ran_atexit = 0
ran_finalizer = 0
zero = 0
for label, body in CASES:
    done = run(PREAMBLE + body)
    saw_atexit = "atexit finalizing" in done.stderr
    saw_final = "finalizer finalizing" in done.stderr
    warned = "yes" if "RuntimeWarning" in done.stderr else ""
    ran_atexit += saw_atexit
    ran_finalizer += saw_final
    zero += done.returncode == 0
    yes_atexit = "yes" if saw_atexit else "no"
    yes_final = "yes" if saw_final else "no"
    columns = f"{done.returncode:>6} {yes_atexit:>7} {yes_final:>10}"
    print(f"  {label:38} {columns}  {warned}".rstrip())
print()

stranded = 0
if DEBUG:
    print("what this build says was still alive when the interpreter stopped")
    base = leftover("")
    for label, program in SHAPES:
        now = leftover(program)
        stranded = max(stranded, now[0] - base[0])
        print(f"  {label:50} {now[0] - base[0]:+8} refs {now[1] - base[1]:+8} blocks")
else:
    print("a debug build would also count what was left over, and this is not one")
print()

print(f"~ children that ran their atexit callback: {ran_atexit} of {len(CASES)}")
print(f"~ children that ran their finalizer: {ran_finalizer} of {len(CASES)}")
print(f"~ children whose exit status was zero: {zero} of {len(CASES)}")
if DEBUG:
    print(f"~ references stranded by one daemon thread: {stranded}")
'''


WHAT_THE_END_STILL_RUNS = Experiment(
    slug="r08-what-the-end-still-runs",
    lesson="R08",
    title="Nine ways a process can end, and what each one still runs on the way out",
    asks="Which of the things you registered actually run when the interpreter stops?",
    needs=(
        "it needs to start child interpreters, because the only honest way to watch a shutdown "
        "is from a process that outlives it"
    ),
    build="release",
    program=PROGRAM_TWENTYEIGHT,
)


WHAT_THE_END_LEAVES_BEHIND = Experiment(
    slug="r08-what-the-end-leaves-behind",
    lesson="R08",
    title="The same nine endings on a build that counts what was still alive at the end",
    asks="How much does one daemon thread leave stranded when the interpreter stops?",
    needs=(
        "it needs a debug build, because only that build has the counters that -X showrefcount "
        "prints once shutdown is over"
    ),
    build="debug",
    program=PROGRAM_TWENTYEIGHT,
)


PROGRAM_TWENTYNINE = r'''"""What the reference leak hunter catches that an ordinary run does not.

Four small tests, written into a directory of their own, run twice each. Once the way
anybody runs a test suite, and once under the flag CPython's buildbots use, which runs
every test six times and counts what the interpreter is still holding afterwards.
"""

import os
import pathlib
import re
import subprocess
import sys
import tempfile

CASES = {
    "test_clean": """
import unittest


class Clean(unittest.TestCase):
    def test_it(self):
        held = [object()]
        self.assertTrue(held)
""",
    "test_cached": """
import unittest

CACHE = []


class Cached(unittest.TestCase):
    def test_it(self):
        if len(CACHE) < 4:
            CACHE.append(object())
        self.assertTrue(CACHE)
""",
    "test_leaky": """
import unittest

HOARD = []


class Leaky(unittest.TestCase):
    def test_it(self):
        HOARD.append(object())
        self.assertTrue(HOARD)
""",
    "test_handles": """
import os
import unittest


class Handles(unittest.TestCase):
    def test_it(self):
        copy = os.dup(0)
        self.assertGreater(copy, 0)
""",
}

REPORT = re.compile(r"^\w+ leaked (\[[^]]*\]) ([a-z ]+), sum=(-?\d+)(.*)$")

ROOT = pathlib.Path(tempfile.mkdtemp())
for name, body in CASES.items():
    (ROOT / f"{name}.py").write_text(body)


def run(name, flags=()):
    """Run one of the four tests, with or without the leak hunting flag."""
    return subprocess.run(
        [sys.executable, "-m", "test", "--testdir", str(ROOT), *flags, name],
        capture_output=True,
        text=True,
        timeout=600,
        env=os.environ | {"PYTHON_COLORS": "0"},
    )


print("four small tests, run the way anybody runs a test suite")
print()
ordinary = 0
for name in CASES:
    done = run(name)
    ordinary += done.returncode == 0
    print(f"  {name:14} {'failed' if done.returncode else 'passed'}")

print()
print("the same four, run six times each with the leak hunter watching")
print()
hunted = 0
for name in CASES:
    done = run(name, ("-R", "3:3"))
    hunted += done.returncode == 0
    said = [m for m in map(REPORT.match, done.stderr.splitlines()) if m]
    counts = ", ".join(f"{m.group(1)} {m.group(2)}" for m in said)
    excused = " (which the hunter calls fine)" if said and said[0].group(4) else ""
    verdict = "failed" if done.returncode else "passed"
    print(f"  {name:14} {verdict:7} {counts or 'nothing was left behind'}{excused}")

print()
print(f"~ tests that pass an ordinary run: {ordinary} of {len(CASES)}")
print(f"~ tests that pass the leak hunter: {hunted} of {len(CASES)}")
print("~ repetitions the hunter ran each test for: 6")
print("~ of those repetitions that were warm ups: 3")
'''


WHAT_THE_LEAK_HUNTER_CATCHES = Experiment(
    slug="r09-what-the-leak-hunter-catches",
    lesson="R09",
    title="Four small tests, run once the ordinary way and once with the leak hunter watching",
    asks="What does CPython's own leak hunter see that an ordinary test run walks straight past?",
    needs=(
        "it needs a debug build, because counting what the interpreter is still holding is "
        "something only that build keeps a total of"
    ),
    build="debug",
    program=PROGRAM_TWENTYNINE,
)


PROGRAM_THIRTY = r'''"""What a module has to declare before a free threaded build will trust it.

CPython's own test suite ships a shared object that exports several init functions, two
of which differ only in one line: whether they say the module can run without the lock.
Loading each one in a child of its own shows what that line is worth.
"""

import os
import subprocess
import sys
import textwrap

CHILD = """
import importlib.machinery, importlib.util, sys, _testmultiphase

name = sys.argv[1]
print(f"    the lock before the import: {sys._is_gil_enabled()}")
loader = importlib.machinery.ExtensionFileLoader(name, _testmultiphase.__file__)
spec = importlib.util.spec_from_loader(name, loader)
loader.exec_module(importlib.util.module_from_spec(spec))
print(f"    the lock after the import:  {sys._is_gil_enabled()}")
"""

CASES = (
    ("_test_from_modexport", "which declares Py_MOD_GIL_NOT_USED", {}),
    ("_test_from_modexport_gil_used", "which declares Py_MOD_GIL_USED", {}),
    ("_test_from_modexport_gil_used", "the same one, in a child started with PYTHON_GIL=0", {}),
)

OVERRIDE = {"PYTHON_GIL": "0"}


def load(name, extra):
    """Import one init function out of that shared object, in a child of its own."""
    return subprocess.run(
        [sys.executable, "-c", CHILD, name],
        capture_output=True,
        text=True,
        timeout=180,
        env=os.environ | {"PYTHON_COLORS": "0"} | extra,
    )


print("what a compiled module has to declare before this build will trust it")
print()
print(f"  the abi flags on this build: {sys.abiflags!r}")
print()

turned_on = 0
for position, (name, what, _) in enumerate(CASES):
    done = load(name, OVERRIDE if position == 2 else {})
    print(f"  {name}, {what}")
    print(done.stdout, end="")
    turned_on += "the lock after the import:  True" in done.stdout
    said = [one for one in done.stderr.splitlines() if "RuntimeWarning" in one]
    if not said:
        print("    it went through without a word")
    for one in said:
        print("    on the way it warned, at some length:")
        text = one.split("RuntimeWarning: ")[1]
        print(textwrap.indent(textwrap.fill(text, 74), "      "))
    print()

print(f"~ ways of loading the same shared object: {len(CASES)}")
print(f"~ of those that turned the lock back on: {turned_on}")
'''


WHAT_A_MODULE_MUST_DECLARE = Experiment(
    slug="r09-what-a-module-must-declare",
    lesson="R09",
    title="One shared object, three ways to load it, and what each one does to the lock",
    asks="What is the line at the bottom of an extension module that declares itself safe worth?",
    needs=(
        "it needs a free threaded build, because a build that always has the lock has nothing "
        "to turn back on"
    ),
    build="freethreaded",
    program=PROGRAM_THIRTY,
)


EXPERIMENTS: tuple[Experiment, ...] = (
    COMPILING_COSTS_NOTHING_THAT_LASTS,
    A_LEAK_YOU_CAN_SEE,
    WHAT_A_SCRIPT_WROTE,
    CHANGING_THE_SOURCE_OF_TRUTH,
    ONE_LINE_AT_A_TIME,
    A_PARSER_NOBODY_WROTE,
    THE_COUNT_THAT_IS_NOT_THERE,
    ONE_COUNT_EACH_WAY,
    NO_LISTS_TO_BE_IN,
    THE_COUNT_ANOTHER_THREAD_CANNOT_SEE,
    NOTHING_RUNS_WHILE_IT_WALKS,
    THE_SAME_WORK_WITHOUT_THE_LOCK,
    NOTHING_TO_WAIT_FOR,
    ONE_LOCK_EACH_OR_ONE_BETWEEN_THEM,
    THE_LOCK_SWITCHED_BACK_ON,
    THE_DAEMON_THAT_NEVER_CAME_BACK,
    FOUR_CORES_WITH_THE_LOCK,
    FOUR_CORES_WITHOUT_THE_LOCK,
    THE_MESSAGE_THAT_WAITED,
    THE_SAME_MESSAGE_WITHOUT_THE_LOCK,
    READING_WHAT_NOBODY_COUNTS,
    THE_SAME_TWO_LISTS_WITH_THE_LOCK,
    WHAT_ONE_THREAD_PAYS,
    WHAT_ONE_THREAD_PAYS_WITH_THE_LOCK,
    THREE_WAYS_TO_SPLIT_THE_WORK,
    THREE_WAYS_WITHOUT_THE_LOCK,
    WHAT_STARTUP_COSTS,
    WHAT_STARTUP_COSTS_ON_A_DEBUG_BUILD,
    WHAT_A_SECOND_INTERPRETER_COSTS,
    WHAT_A_SECOND_INTERPRETER_COSTS_WITHOUT_THE_LOCK,
    HOW_MUCH_OF_AN_IMPORT_IS_PARALLEL,
    HOW_MUCH_OF_AN_IMPORT_IS_PARALLEL_WITHOUT_THE_LOCK,
    WHAT_FREEZING_SAVES_AT_STARTUP,
    WHAT_FREEZING_SAVES_ON_A_DEBUG_BUILD,
    WHAT_DEFERRING_AN_IMPORT_IS_WORTH,
    HOW_MUCH_OF_A_WAKE_UP_IS_PARALLEL,
    HOW_MUCH_OF_A_WAKE_UP_IS_PARALLEL_WITHOUT_THE_LOCK,
    WHAT_LEAVES_THE_BINARY,
    WHAT_LEAVES_THE_BINARY_ON_A_FREE_THREADED_BUILD,
    WHAT_A_BUILD_WILL_LOAD,
    WHAT_A_BUILD_WILL_LOAD_WITHOUT_THE_LOCK,
    WHAT_THE_END_STILL_RUNS,
    WHAT_THE_END_LEAVES_BEHIND,
    WHAT_THE_LEAK_HUNTER_CATCHES,
    WHAT_A_MODULE_MUST_DECLARE,
)


def find(slug: str) -> Experiment:
    for experiment in EXPERIMENTS:
        if experiment.slug == slug:
            return experiment
    known = ", ".join(one.slug for one in EXPERIMENTS)
    raise KeyError(f"no experiment called {slug!r}; there is {known}")
