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
)


def find(slug: str) -> Experiment:
    for experiment in EXPERIMENTS:
        if experiment.slug == slug:
            return experiment
    known = ", ".join(one.slug for one in EXPERIMENTS)
    raise KeyError(f"no experiment called {slug!r}; there is {known}")
