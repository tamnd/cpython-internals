#!/usr/bin/env python
"""F12. What ends up on disk.

The twelfth and last lesson of the front end part, and the twenty sixth overall. Everything
from F01 onwards has gone one way: text in, code object out, eleven stages in between. This
one goes the other way. A code object becomes bytes on disk, and those bytes become the same
code object again without any of the eleven stages running.

That is the whole reason importing a module a second time is fast, and it is also the reason
a `__pycache__` directory exists at all.

The lesson is deliberately concrete. It compiles a two line file, reads the .pyc back as
bytes, decodes the header field by field, walks the marshalled blob with a reader written
here, and then writes a .pyc by hand and imports it with no source file anywhere on disk.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("f12-what-ends-up-on-disk", "f12")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("f12-what-ends-up-on-disk").figure


lesson.md(f"""
# F12. What ends up on disk

{badge}

Import a module and the second time is faster than the first. You already know why in outline: there is a `__pycache__` directory with a `.pyc` in it, and the second import reads that instead of compiling the source again.

This lesson opens the {term("pyc file")}. It is a sixteen byte header and then one object, and that object is the {term("code object")} F10 pulled apart, flattened into bytes by a module called {term("marshal")}. Nothing else is in the file.

By the end you will have decoded one by hand and written one by hand, and imported the one you wrote with no source file anywhere on disk.

{figure("the-round-trip", "source, code object, pyc file, and the same code object again")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/marshal.c:381-416@v3.15.0rc1#w_ref`.

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
## The file a file leaves behind

Start by making one. Everything in this lesson happens in a scratch directory so nothing lands anywhere you care about.

{lesson.claim("a .pyc is a sixteen byte header followed by one marshalled object and nothing else")}
""")


lesson.code(
    """
import marshal
import pathlib
import py_compile
import tempfile

WORK = pathlib.Path(tempfile.mkdtemp(prefix="f12-"))
SOURCE = "def greet(who):\\n    return f'hi {who}'\\n\\nWHO = 'world'\\n"

here = WORK / "greet.py"
here.write_text(SOURCE)
where = pathlib.Path(py_compile.compile(str(here), dfile="greet.py", doraise=True))
blob = where.read_bytes()

print(f"  {here.name} is {len(SOURCE)} bytes of text")
print(f"  {where.name} is {len(blob)} bytes")
print()
print(f"  header    {blob[:16].hex(' ')}")
print(f"  the rest  {len(blob) - 16} bytes, and marshal.loads gives back a")
print(f"            {type(marshal.loads(blob[16:])).__name__} object")
""",
    varies="The .pyc length is 3.15's. 3.14 compiles this file a little smaller.",
)


lesson.md(f"""
Sixteen bytes, four fields, four bytes each.

{figure("what-a-pyc-holds", "the four header fields and the marshalled object after them")}

The last two are how staleness gets decided. If the source file's modification time or its length is not what the header says, the `.pyc` is thrown away and the source is compiled again. That check is `Lib/importlib/_bootstrap_external.py:446-476@v3.15.0rc1#_validate_timestamp_pyc`, and it is four lines of real work.
""")


lesson.code(
    """
print(f"  magic  {int.from_bytes(blob[0:4], 'little'):>12}")
print(f"  flags  {int.from_bytes(blob[4:8], 'little'):>12}")
print(f"  mtime  {int.from_bytes(blob[8:12], 'little'):>12}   source {int(here.stat().st_mtime)}")
print(f"  size   {int.from_bytes(blob[12:16], 'little'):>12}   source {len(SOURCE)}")
""",
    varies="The timestamps are whenever you ran this. The two pairs match either way, which is the point.",
)


lesson.md(f"""
## Four bytes that are not really a number

The {term("magic number")} is the version check. Change anything about the bytecode, add an instruction or change what one does, and this number goes up, and every `.pyc` from before stops loading. `Lib/importlib/_bootstrap_external.py:413-444@v3.15.0rc1#_classify_pyc` is the eight lines that compare it.

Look closely at the four bytes and only two of them are the number. The other two are a carriage return and a newline, glued on by `Include/internal/pycore_magic_number.h:313-318@v3.15.0rc1#PYC_MAGIC_NUMBER_TOKEN`.

That is a trap, on purpose. If something copies a `.pyc` in text mode, on a system where that translates line endings, those two bytes are the ones that change. So the file fails the magic check loudly rather than loading and doing something strange three hundred bytes later.

{lesson.claim("half of the magic number is a carriage return and a newline put there to catch text mode copying")}
""")


lesson.code(
    """
magic = blob[:4]

print(f"  the four bytes    {magic.hex(' ')}")
print(f"  as characters     {magic!r}")
print()
print(f"  the version part  {int.from_bytes(magic[:2], 'little')}")
print(f"  the last two      {magic[2:]!r}, which is a carriage return and a newline")
""",
    varies="3.14 has a lower magic number, because the number goes up whenever the bytecode changes.",
)


lesson.md(f"""
## One byte, then whatever that byte said

Now the other three hundred bytes. {term("marshal", "Marshal")} has no schema and no lengths up front. Every object is one byte saying what it is, followed by exactly what that kind of object needs.

{figure("one-byte-two-jobs", "the type byte split into its top bit and its seven letter bits")}

The seven low bits are an ascii letter, which is why a `.pyc` in a hex dump is half readable. `Python/marshal.c:58-96@v3.15.0rc1` is the list, thirty of them, and reading the writer is mostly reading a chain of `else if` over types in `Python/marshal.c:460-495@v3.15.0rc1#w_object`.

{figure("some-of-the-type-codes", "six type codes and what follows each one")}

{lesson.claim("the first byte of any marshalled object is an ascii letter naming its type")}
""")


lesson.code("""
import marshal

for value in [None, True, 7, "abc", b"abc", (1, 2), 1.5, [1], {"a": 1}]:
    first = marshal.dumps(value)[0]
    letter = chr(first & 0x7F)
    shared = "yes" if first & 0x80 else "no"
    print(f"  {value!r:12} starts {first:#04x}  letter {letter!r}  in the table: {shared}")
""")


lesson.md(f"""
## Saying it once

That top bit is the other half of the format. When it is set, the object is put in a numbered table as it is read, and anything later in the file can point at it by number instead of repeating it.

{figure("said-once-then-pointed-at", "thirteen bytes with the second abcd replaced by a back reference")}

`Python/marshal.c:381-416@v3.15.0rc1#w_ref` is where the writer decides. The rule is not simply "seen before". An object with exactly one reference to it cannot be shared, so it is written out plainly and not numbered, unless it is an interned string, which is always numbered so that the same source produces the same bytes.

{lesson.claim("a value that shows up twice is written once and pointed at the second time")}
""")


lesson.code(
    """
pair = ("abcd", "abcd")
bytes_for_pair = marshal.dumps(pair)
print(f"  ('abcd', 'abcd') is {len(bytes_for_pair)} bytes:  {bytes_for_pair.hex(' ')}")
print()

long = "a fairly ordinary looking docstring, about sixty characters or so."
same = marshal.dumps((long, long))
apart = marshal.dumps((long, long.upper()))

print(f"  a {len(long)} character string, said twice     {len(same):4} bytes")
print(f"  the same string and a different one   {len(apart):4} bytes")
print(f"  so the back reference saved {len(apart) - len(same)} bytes on one string")
print()

body = marshal.dumps(compile(SOURCE, "greet.py", "exec"))
twice = marshal.dumps(compile(SOURCE + SOURCE.replace("greet", "greet2"), "greet.py", "exec"))

print(f"  the whole module marshals to      {len(body)} bytes")
print("  the same module with the function")
print(f"  written out a second time is      {len(twice)} bytes")
""",
    differs="3.14 compiles this module three bytes smaller. The saving from the back reference is the same on both.",
)


lesson.md(f"""
## A code object, flattened

Type `c` is the interesting one, and it is sixteen fields in a fixed order. Five plain four byte numbers first, then eleven more objects, each of which starts with its own type byte.

{figure("sixteen-fields-in-order", "the sixteen fields of a marshalled code object, grouped")}

`Python/marshal.c:1566-1600@v3.15.0rc1#TYPE_CODE` is the reader, and the order it reads in is the order the writer wrote in, which is the entire specification. Note where the last two are: the line table and the exception table, the two blobs F11 decoded, sitting at the end of every function in the file.

Here is a reader for the parts a `.pyc` actually uses. About fifty lines, and the last cell checks it against the real thing.

{lesson.claim("a reader written here decodes a marshalled code object into the fields the interpreter reads")}
""")


lesson.code("""
import struct

# The order the writer writes and the reader reads, which is the whole specification.
FIELDS = [
    "argcount",
    "posonlyargcount",
    "kwonlyargcount",
    "stacksize",
    "flags",
    "code",
    "consts",
    "names",
    "localsplusnames",
    "localspluskinds",
    "filename",
    "name",
    "qualname",
    "firstlineno",
    "linetable",
    "exceptiontable",
]

NUMBERS = {"argcount", "posonlyargcount", "kwonlyargcount", "stacksize", "flags", "firstlineno"}


class Reader:
    \"\"\"Enough of marshal to read a .pyc, and no more.\"\"\"

    def __init__(self, blob):
        self.blob = blob
        self.at = 0
        self.seen = []

    def take(self, count):
        out = self.blob[self.at : self.at + count]
        self.at += count
        return out

    def number(self):
        return int.from_bytes(self.take(4), "little", signed=True)

    def one(self):
        raw = self.take(1)[0]
        kind = chr(raw & 0x7F)
        slot = len(self.seen)
        if raw & 0x80:
            self.seen.append(None)
        value = self.body(kind)
        if raw & 0x80:
            self.seen[slot] = value
        return value

    def body(self, kind):
        if kind in "NTF":
            return {"N": None, "T": True, "F": False}[kind]
        if kind == "i":
            return self.number()
        if kind == "g":
            return struct.unpack("<d", self.take(8))[0]
        if kind == "s":
            return self.take(self.number())
        if kind in "zZ":
            return self.take(self.take(1)[0]).decode("ascii")
        if kind in "aAtu":
            return self.take(self.number()).decode("utf-8", "surrogatepass")
        if kind == ")":
            return tuple(self.one() for _ in range(self.take(1)[0]))
        if kind == "(":
            return tuple(self.one() for _ in range(self.number()))
        if kind == "r":
            return self.seen[self.number()]
        if kind == "c":
            return {one: self.number() if one in NUMBERS else self.one() for one in FIELDS}
        raise ValueError(f"no idea what {kind!r} means")
""")


lesson.md("""
Now point it at the file from the top of the lesson, skipping the sixteen byte header.
""")


lesson.code(
    """
module = Reader(blob[16:]).one()
real = marshal.loads(blob[16:])

for field in FIELDS:
    value = module[field]
    print(f"  {field:16} {value!r:.58}")

print()
print(f"  filename matches       {module['filename'] == real.co_filename}")
print(f"  bytecode matches       {module['code'] == real.co_code}")
print(f"  line table matches     {module['linetable'] == real.co_linetable}")
print(f"  the constants hold a nested code object: {module['consts'][0]['qualname']!r}")
""",
    varies="The bytecode and the tables are 3.15's, and 3.14 compiles this file slightly differently. The four lines at the bottom say the same thing on both.",
)


lesson.md(f"""
## Writing one by hand

Reading is only half of it. Nothing stops you writing the sixteen bytes yourself and handing Python the result.

This is a `.pyc` with no `.py` anywhere. Python will import it, because a sourceless import is a supported thing and `SourcelessFileLoader` is the loader that does it.

{lesson.claim("a .pyc assembled by hand imports and runs with no source file on disk")}
""")


lesson.code(
    """
import importlib
import importlib.util
from importlib.machinery import SourcelessFileLoader

code = compile("def greet(who):\\n    return f'hi {who}'\\n\\nWHO = 'world'\\n", "ghost.py", "exec")

header = importlib.util.MAGIC_NUMBER
header += (0).to_bytes(4, "little")
header += (0).to_bytes(4, "little")
header += (0).to_bytes(4, "little")

ghost = WORK / "ghost.pyc"
ghost.write_bytes(header + marshal.dumps(code))

print(f"  wrote {ghost.name}, {len(ghost.read_bytes())} bytes")
print(f"  is there a ghost.py next to it: {(WORK / 'ghost.py').exists()}")
print()

loader = SourcelessFileLoader("ghost", str(ghost))
spec = importlib.util.spec_from_file_location("ghost", str(ghost), loader=loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)

print(f"  imported it anyway, and it says: {module.greet(module.WHO)!r}")
""",
    differs="The handmade file is three bytes smaller on 3.14, because the bytecode inside it is.",
)


lesson.md(f"""
## What makes one stale

Two failure modes, and they are deliberately different.

A wrong magic number is an error, because it means the bytecode is from another version of Python and running it would be nonsense. A wrong timestamp is not an error at all, because it only means the source has changed, and the sensible thing to do then is compile it again and rewrite the file.

{lesson.claim("a wrong magic number raises and a wrong timestamp is fixed silently")}
""")


lesson.code(
    """
spoiled = bytearray(ghost.read_bytes())
spoiled[0] ^= 1
broken = WORK / "broken.pyc"
broken.write_bytes(bytes(spoiled))

loader = SourcelessFileLoader("broken", str(broken))
spec = importlib.util.spec_from_file_location("broken", str(broken), loader=loader)
try:
    loader.exec_module(importlib.util.module_from_spec(spec))
except ImportError as problem:
    print(f"  one bit flipped in the magic: {problem}")

print()

was = bytearray(where.read_bytes())
was[8] ^= 0xFF
where.write_bytes(bytes(was))
print(f"  put a wrong mtime in {where.name}: {int.from_bytes(was[8:12], 'little')}")

sys.path.insert(0, str(WORK))
greet = importlib.import_module("greet")

print(f"  imported it with no complaint: {greet.greet(greet.WHO)!r}")
print(f"  and the header now says        {int.from_bytes(where.read_bytes()[8:12], 'little')}")
print(f"  the file was quietly rewritten: {where.read_bytes() != bytes(was)}")
""",
    varies="The magic bytes are the version's and the timestamps are whenever you ran this. The two behaviours, one raising and one silently fixing itself, are the same on both.",
)


lesson.md("""
## Try it yourself

Three things to poke at.

Marshal a set and a frozenset and compare the bytes. One of them is allowed in a `.pyc` and the other is not, and the type codes tell you which.

Take the reader above and add a counter for how many objects go into the `seen` table, then run it on a large module out of the standard library. The ratio of table entries to total objects is how much the sharing is buying.

Write a `.pyc` whose code object came from a completely different source file than the name in the header suggests, import it, and then raise an exception inside it. The traceback will read from a file that says something else entirely, which is a good way to feel how little the runtime knows about where code came from.

## What just happened

A `.pyc` is four numbers and then one object. The numbers are a magic number that is really two bytes plus a carriage return and a newline, a flags word, and the source's timestamp and length. The object is a code object.

Marshal writes objects as one type byte and then whatever that type needs. The seven low bits of the byte are an ascii letter, and the top bit means "number this one, something later may point at it". A repeated value costs five bytes the second time regardless of how big it is.

A code object is sixteen fields in a fixed order, and the last two are the line table and the exception table from F11. Fifty lines of Python read the whole thing, and the same fifty lines read every `.pyc` on your machine.

And you can write one. Python does not care that no source file exists, only that the magic number matches.

## What is next

That is the front end done, F01 to F12. Text became tokens, tokens became a tree, the tree got names attached, the names became instructions, the instructions became a graph, the graph got optimised and flattened, and the result got written to disk and read back.

Everything after this is the other side: what happens when those instructions actually run.
""")


raise SystemExit(lesson.save())
