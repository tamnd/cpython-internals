#!/usr/bin/env python
"""O10. One string, four layouts.

The tenth lesson of the object model part. O09 took apart the integer. This one takes apart
the other type every program uses constantly.

A Python string stores its characters in 1, 2 or 4 bytes each, and the choice is made once
per string by the single widest character in it. There are three C structs behind `str`, a
hash cached in the object, a UTF-8 copy that only appears when C code asks for it, and an
intern table that keeps exactly one copy of the strings that look like names.

Everything here is measured with `sys.getsizeof`, `hash` and a couple of pyxray helpers. No
part of it needs a debug build.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("o10-one-string-four-layouts", "o10")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("o10-one-string-four-layouts").figure


lesson.md(f"""
# O10. One string, four layouts

{badge}

Here is a question with a surprising answer. You have a string of one hundred characters. How many bytes does it take?

Anywhere from 141 to 460, and nothing about the length decides it. What decides it is the single widest character in the string. One emoji in an otherwise plain sentence makes every character in that sentence four bytes wide, including the spaces.

{figure("the-widest-character-decides", "the four storage layouts a string can have, chosen by its widest character")}

That is the headline, and this lesson measures it. Then it goes after the rest of what is packed into a string object: a cached hash, a UTF-8 copy that appears out of nowhere, and a table the interpreter uses to keep exactly one copy of the strings that look like names.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Objects/unicodeobject.c:1272-1311@v3.15.0rc1#PyUnicode_New`.

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

Everything below was checked against the version this cell prints and against 3.14. On strings the two agree completely, which is unusual for these lessons and worth saying out loud.
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
## The widest character sets the width for everything

A {term("code point", "code point")} is a number Unicode assigns to a character. The letter `h` is 104. The accented `e` in cafe is 233. The Chinese character for middle is 20013. A grinning face is 128512.

CPython stores the characters of a string as a flat array of fixed width numbers, and it uses the narrowest width that fits every character present. One byte if nothing goes above 255, two bytes if nothing goes above 65535, four bytes otherwise. The source calls this the {term("string kind", "kind")}, and the comment that lays out the three cases is at {cite("Include/cpython/unicodeobject.h:66-88@v3.15.0rc1")}.

There is a fourth case hiding inside the first. If every character is ASCII, so nothing above 127, the string gets a smaller struct as well as one byte characters, because a few fields it would otherwise need turn out to be unnecessary. That is why the table at the top of this lesson has four rows and the kind field only has three values.

You can measure all of this without touching C. `sys.getsizeof` reports the real allocation.

{lesson.claim("a string stores its characters in 1, 2 or 4 bytes each, chosen by the largest code point in the string, so adding one wide character widens every character in it")}
""")


lesson.code(
    """
import sys

samples = [
    ("plain ASCII", "hello"),
    ("with an accent", "caf\\xe9s"),
    ("Chinese", "\\u4e2d\\u6587xx"),
    ("with an emoji", "\\U0001f600abcd"),
]

print("  text             length  widest  bytes")
for label, text in samples:
    widest = max(map(ord, text))
    print(f"  {label:16} {len(text):6} {widest:7} {sys.getsizeof(text):6}")
""",
    varies="These byte counts are for a 64 bit build. A 32 bit build, including the one in "
    "your browser, has a smaller object header, so every number here comes out lower. The "
    "gaps between the rows behave the same way.",
)


lesson.md("""
Four strings of similar length, four different sizes. Now watch what happens when you take one string and add a single wide character to the end of it.

The interesting part is not that the string gets longer. It is that the characters already in it get wider, so the cost goes up by far more than one character's worth.
""")


lesson.code(
    """
base = "the quick brown fox jumps over the lazy dog"
plain = sys.getsizeof(base)

for suffix, label in [("x", "one more ASCII letter"), ("\\u4e2d", "one Chinese character")]:
    grown = sys.getsizeof(base + suffix)
    print(f"  {label:24} {plain} -> {grown} bytes, a jump of {grown - plain}")
""",
    varies="The jump is 62 on a 64 bit build and 54 on a 32 bit one, because part of it is "
    "the header growing and headers are smaller when pointers are. The part that comes from "
    "rewriting the characters is the same everywhere.",
)


lesson.md(f"""
One extra letter costs one byte. One extra Chinese character costs sixty two, and only two of those bytes are the character itself. Forty three more are the characters that were already there being rewritten at double width, one is the trailing zero doubling with them, and the last sixteen are the bigger header that every non-ASCII string carries.

The decision is made in `PyUnicode_New`, which is the function everything else eventually goes through. It takes a length and a maximum character, and the ladder that turns that maximum into a width is right at the top, {cite("Objects/unicodeobject.c:1272-1311@v3.15.0rc1#PyUnicode_New")}. The scan that finds the maximum in the first place is a separate pass over the text, {cite("Objects/unicodeobject.c:1586-1600@v3.15.0rc1#find_maxchar_surrogates")}.

{figure("how-a-string-gets-built", "the steps from raw text to a finished string object")}

There is one more thing worth knowing about that function. Look at the empty string case at {cite("Objects/unicodeobject.c:1274-1277@v3.15.0rc1")}: it does not allocate anything at all, it hands back a single object that the interpreter made once at startup. Every empty string in your program is the same object.
""")


lesson.code(
    """
made_one_way = "".join([])
made_another = "x".replace("x", "")
sliced_away = "hello"[5:]

print(f"  join of nothing, replace  {made_one_way is made_another}")
print(f"  and an empty slice too     {made_one_way is sliced_away}")
print(f"  it still costs something   {sys.getsizeof(made_one_way)} bytes")
print(f"  and it is immortal         {pyxray.obj.is_immortal(made_one_way)}")
""",
    varies="Forty one bytes on a 64 bit build, twenty one on a 32 bit one. An empty string "
    "is all header and a trailing zero, so it is the cleanest measurement of the header there "
    "is.",
)


lesson.md(f"""
## The characters live inside the object

The reason `sys.getsizeof` can tell you the whole story is that for almost every string, there is only one allocation. The struct and the characters are one block of memory, with the text starting immediately after the last field.

{figure("inside-a-string-object", "the fields of a short ASCII string, in order")}

That block is a single `PyObject_Malloc` of the struct size plus the characters plus one, {cite("Objects/unicodeobject.c:1322-1336@v3.15.0rc1")}. The plus one is a trailing zero byte, so the text can be handed to C functions that expect a null terminated string without copying it first.

CPython calls this the {term("compact string", "compact")} form, and there are two versions of it. ASCII strings use `PyASCIIObject`, which is the header, a length, a hash and four bytes of flags, {cite("Include/cpython/unicodeobject.h:156-161@v3.15.0rc1#PyASCIIObject")}. Everything else uses `PyCompactUnicodeObject`, which adds two more fields we will come back to, {cite("Include/cpython/unicodeobject.h:166-171@v3.15.0rc1#PyCompactUnicodeObject")}.

The comments describing the two forms, in the source's own words, are at {cite("Include/cpython/unicodeobject.h:114-124@v3.15.0rc1")} and {cite("Include/cpython/unicodeobject.h:125-136@v3.15.0rc1")}.

You can read the struct sizes straight out of the measurements. Take a string of a known length, subtract the characters, and what is left is the fixed part.

{lesson.claim("the characters of an ordinary string are stored inside the object, in the same allocation as the header, with a fixed overhead of 40 bytes for ASCII and 56 for everything else")}
""")


lesson.code(
    """
def overhead(sample_char):
    \"\"\"Fixed bytes per string object, found by comparing two lengths of the same kind.\"\"\"
    ten = sys.getsizeof(sample_char * 10)
    eleven = sys.getsizeof(sample_char * 11)
    per_char = eleven - ten
    return ten - 10 * per_char, per_char


kinds = [("ASCII", "a"), ("Latin-1", "\\xe9"), ("2 byte", "\\u4e2d"), ("4 byte", "\\U0001f600")]

for label, sample in kinds:
    fixed, per_char = overhead(sample)
    print(f"  {label:9} {per_char} bytes per character, {fixed} bytes of fixed cost")
""",
    varies="Again these are 64 bit numbers. The fixed cost drops on a 32 bit build because "
    "every pointer and every Py_ssize_t in the header halves. The bytes per character do not "
    "change, because those are set by Unicode and not by the machine.",
)


lesson.md(f"""
The fixed cost is 41 and 57 rather than 40 and 56 because of that trailing zero, which `str.__sizeof__` counts as one more character, {cite("Objects/unicodeobject.c:13466-13493@v3.15.0rc1#unicode_sizeof_impl")}.

So an ASCII string carries 40 bytes of overhead and a non-ASCII one carries 56. Sixteen bytes is the price of not being ASCII, before you pay for a single character.

{figure("what-a-hundred-characters-cost", "bytes for a hundred characters in each of the four layouts")}

There is a third struct, and it is the one you will almost never see. `PyUnicodeObject` keeps its characters in a separate block and holds a pointer to them, {cite("Include/cpython/unicodeobject.h:174-182@v3.15.0rc1#PyUnicodeObject")}. The source calls it the legacy form and says plainly what makes one: subclasses of `str`, {cite("Include/cpython/unicodeobject.h:137-152@v3.15.0rc1")}. Subclassing means an instance has to carry whatever the subclass adds, so the text cannot be glued to the end of the object any more.
""")


lesson.code(
    """
class Tagged(str):
    pass


text = "hello world"
subclassed = Tagged(text)

print(f"  a plain str      {sys.getsizeof(text)} bytes")
print(f"  a str subclass   {sys.getsizeof(subclassed)} bytes for the same characters")
print(f"  equal            {text == subclassed}")
print(f"  same object      {text is subclassed}")
""",
    varies="Both numbers shrink on a 32 bit build. What holds is the ratio: the subclass is "
    "about twice the size, because it pays for a second block plus the fields any subclass "
    "instance carries.",
)


lesson.md(f"""
## The hash is over the raw bytes, whatever they are

There is a `hash` field sitting in every string object, set to -1 until somebody asks for it, {cite("Include/cpython/unicodeobject.h:156-161@v3.15.0rc1#PyASCIIObject")}. The first `hash(text)` computes it and writes it back. Every call after that reads the field, {cite("Objects/unicodeobject.c:11666-11685@v3.15.0rc1#unicode_hash")}.

That matters more than it sounds. Dict lookups hash their key, and dict keys are usually strings, so without this cache every attribute access in the language would rehash a string it has already hashed a thousand times.

The interesting part is what gets hashed. Look at the call: it hashes `PyUnicode_DATA` for `length * kind` bytes. Not the characters, not the UTF-8 encoding. The raw storage buffer, exactly as it sits in memory.

Which means you can predict a string's hash from Python, if you know its kind. Encode the same text in the encoding that matches the storage and hash the bytes. The comment above the function even points this out for the ASCII case, and it turns out to hold for all four.

{lesson.claim("a string's hash is the hash of its raw storage buffer, so it equals the hash of the same text encoded in whichever fixed width encoding matches the string's kind")}
""")


lesson.code("""
checks = [
    ("ASCII", "hello world", "utf-8"),
    ("Latin-1", "caf\\xe9s and cr\\xeapes", "latin-1"),
    ("2 byte", "\\u4e2d\\u6587 text", "utf-16-le"),
    ("4 byte", "\\U0001f600 and friends", "utf-32-le"),
]

for label, text, encoding in checks:
    raw = text.encode(encoding)
    print(f"  {label:9} hash(text) == hash(bytes) is {hash(text) == hash(raw)}, via {encoding}")
""")


lesson.md("""
Four different encodings, four matches, because in each case the encoding produces exactly the bytes CPython already had in memory. This is not a coincidence and it is not an API you should rely on, but it is a direct look at the storage.

It also explains something you may have run into. Two strings that compare equal always hash the same, because equal strings always have the same kind. That is guaranteed by the rule that a string uses the narrowest kind that fits, so there is no way to have the same text stored two different ways.
""")


lesson.md(f"""
## A UTF-8 copy that appears when you are not looking

Those two extra fields on `PyCompactUnicodeObject` are `utf8_length` and `utf8`, and they hold a UTF-8 encoded copy of the text.

For an ASCII string there is nothing to hold. ASCII text encoded as UTF-8 is byte for byte the same thing, so the pointer just aims at the characters already in the object. That is exactly why ASCII gets its own smaller struct: the two fields would always say the same thing.

For anything wider, the copy does not exist until a piece of C code asks for the text as UTF-8. Then it is encoded once and kept, {cite("Objects/unicodeobject.c:5724-5732@v3.15.0rc1#unicode_fill_utf8")}, and every later ask hands back the same buffer, {cite("Objects/unicodeobject.c:4104-4125@v3.15.0rc1#PyUnicode_AsUTF8AndSize")}.

{figure("the-utf8-copy", "where the UTF-8 bytes come from for an ASCII string and for a wider one")}

`sys.getsizeof` counts that buffer if it is there, {cite("Objects/unicodeobject.c:13489-13490@v3.15.0rc1")}, so you can watch a string get bigger while its text stays the same.

The trick is finding something that triggers it. `text.encode("utf-8")` does not, because that builds a fresh `bytes` object and throws the working copy away. What does trigger it is any C function that declared its argument as a plain C string, because Argument Clinic converts those through the caching path.

{lesson.claim("a non-ASCII string can grow after it is created, because the first time C code asks for it as UTF-8 the encoded copy is stored on the object and counted by sys.getsizeof")}
""")


lesson.code("""
import codecs
import contextlib


def fresh(text):
    \"\"\"A brand new string object, built at runtime so no earlier cell has touched it.\"\"\"
    return "".join([text])


for text in ["a plain ascii sentence", "une phrase avec des accents \\xe9\\xe8"]:
    sample = fresh(text)
    before = sys.getsizeof(sample)
    sample.encode("utf-8")
    after_encode = sys.getsizeof(sample)
    with contextlib.suppress(LookupError):
        codecs.lookup(sample)
    after_lookup = sys.getsizeof(sample)
    kind = "ASCII" if max(map(ord, sample)) < 128 else "not ASCII"
    print(f"  {kind:9} {before} bytes, then {after_encode} after .encode(), then {after_lookup}")
""")


lesson.md("""
The ASCII string never moves. The accented one gains the length of its UTF-8 encoding plus one for a trailing zero, and it gains it from a call that failed with an exception. `codecs.lookup` never got as far as doing anything useful. It only needed the name as a C string, and asking was enough.

This is worth remembering when you are chasing memory. A dict of a hundred thousand non-ASCII keys can quietly get bigger the first time something passes those keys through a C API, and nothing in your code changed.
""")


lesson.md(f"""
## One copy of the strings that look like names

The last field in the flags word is the {term("interning", "interning")} state, and it has four values rather than the yes or no you might expect, {cite("Include/cpython/unicodeobject.h:201-204@v3.15.0rc1")}. Not interned, interned and mortal, interned and immortal, and interned and statically allocated.

Interning means the interpreter keeps a table of strings and hands back the one already in it rather than a new equal copy. Two benefits fall out. Comparing two interned strings can stop at the pointer, which is what makes attribute lookup fast. And a program with ten thousand references to the name `value` stores that name once.

Not everything gets interned. The compiler decides, and the rule is deliberately narrow, {cite("Objects/codeobject.c:116-137@v3.15.0rc1#should_intern_string")}: ASCII only, and every character has to be a letter, a digit or an underscore. A string constant that looks like it could be an identifier goes in the table. One with a space in it does not.

Names are treated differently from constants. Every entry in `co_names`, which is where attribute names and global names live, is interned as immortal, {cite("Objects/codeobject.c:182-197@v3.15.0rc1#intern_strings")}. Constants get the mortal version, so they can still be freed when the last code object using them goes away, {cite("Objects/codeobject.c:206-213@v3.15.0rc1")}.

You can see all four states from Python.

{lesson.claim("string constants are interned only if they are ASCII and look like identifiers, while every name in co_names is interned and immortal")}
""")


lesson.code("""
def reads_an_attribute(thing):
    identifier_shaped = "spam_and_eggs"
    has_a_space = "spam and eggs"
    return thing.some_attribute, identifier_shaped, has_a_space


names = reads_an_attribute.__code__.co_names
consts = [c for c in reads_an_attribute.__code__.co_consts if isinstance(c, str)]

print("  co_names, the names the code refers to")
for name in names:
    marks = f"interned {pyxray.obj.is_interned(name)!s:5} immortal {pyxray.obj.is_immortal(name)}"
    print(f"    {name:22} {marks}")

print("  co_consts, the string literals in the body")
for value in consts:
    marks = f"interned {pyxray.obj.is_interned(value)!s:5} immortal {pyxray.obj.is_immortal(value)}"
    print(f"    {value:22} {marks}")
""")


lesson.md(f"""
The attribute name is interned and immortal. The literal that looks like an identifier is interned but mortal. The literal with spaces in it is neither.

Two more paths get you into the table without the compiler's help. `sys.intern` puts a string there on request, which is the whole reason it exists. And any single character string in the Latin-1 range is already there, because the interpreter built all 256 of them at startup and hands them out, {cite("Include/internal/pycore_global_strings.h:920-923@v3.15.0rc1#_Py_LATIN1_CHR")}. The intern path checks for that case before it touches the table at all, {cite("Objects/unicodeobject.c:14284-14291@v3.15.0rc1")}.

There is one thing that can never be interned, and it is the subclass again. The intern function returns early for anything that is not exactly a `str`, on the grounds that it has no idea what putting a subclass in a shared table would do, {cite("Objects/unicodeobject.c:14244-14248@v3.15.0rc1")}.
""")


lesson.code("""
def build(text):
    \"\"\"Assemble a string at runtime so the compiler cannot hand back a constant.\"\"\"
    return "".join(list(text))


runtime = build("spam_and_eggs")
literal = "spam_and_eggs"

print(f"  built at runtime, interned      {pyxray.obj.is_interned(runtime)}")
print(f"  same object as the literal      {runtime is literal}")
print(f"  after sys.intern                {sys.intern(runtime) is literal}")
print()
print(f"  chr(65) twice, same object      {chr(65) is chr(65)}")
print(f"  chr(233) twice, same object     {chr(233) is chr(233)}")
print(f"  chr(256) twice, same object     {chr(256) is chr(256)}")
print()
print(f"  a str subclass, interned        {pyxray.obj.is_interned(Tagged('spam_and_eggs'))}")
""")


lesson.md(f"""
`chr(65)` and `chr(233)` give you the same object every time because those are two of the 256 that already exist. `chr(256)` builds a new one each time, because that is the first code point past the end of the table.

{figure("who-ends-up-in-the-table", "which strings the interpreter keeps exactly one copy of")}

The lesson to take from that last cell is the one every Python style guide already tells you: never use `is` on strings. It works for exactly the cases in this table and silently stops working for everything else, and which case you are in depends on how the string was built rather than on what it says.
""")


lesson.md("""
## Try it yourself

Three things to poke at, in rough order of effort.

The first is the width jump. Take a paragraph of English text, measure it, then append one character from a different script and measure again. Work out how much the character itself cost and how much came from rewriting everything else. Then try appending an emoji instead, and see how the same paragraph behaves going from one byte to four.

The second is the UTF-8 copy. Build a list of a few thousand non-ASCII strings, sum their sizes, run them all through `codecs.lookup` inside a `try`, and sum again. That difference is memory your program can gain without doing anything you would recognise as allocating.

The third is a small hunt. `should_intern_string` says ASCII letters, digits and underscore. Find a string constant in your own code that just misses the rule, and one that just makes it, and confirm with `pyxray.obj.is_interned` that they land on opposite sides. A leading digit is a good place to start, since `"9lives"` is not a valid identifier but does pass the rule.
""")


lesson.md("""
## What just happened

A string picks one of four storage layouts, and it picks by looking at the single widest character in the text. ASCII gets one byte per character and a 40 byte header. Latin-1 gets one byte and a 56 byte header. Everything up to U+FFFF gets two bytes, and anything above that gets four. Adding one wide character to a narrow string rewrites every character in it.

For nearly every string, the characters live in the same allocation as the header, immediately after the last field, with a trailing zero so C code can use the buffer directly. The exception is a subclass of `str`, which has to keep its text in a second block.

The hash is computed once and stored in the object, and what gets hashed is the raw storage buffer. That is why the hash of a string equals the hash of the same text encoded in whichever fixed width encoding matches its kind.

A UTF-8 copy is attached to non-ASCII strings the first time C code asks for one, and it stays attached. ASCII strings never need one, because their stored bytes already are UTF-8.

The interpreter keeps a single copy of strings that look like identifiers. Names in `co_names` are interned and immortal, identifier shaped constants are interned and mortal, everything else is on its own, and all 256 single character Latin-1 strings exist from startup.
""")


lesson.md("""
## What is next

O11 is lists and tuples, and after two lessons about objects that hold data directly it is a change of shape. A list is a pointer to an array of pointers, which means it has two sizes rather than one, and the way it grows when you append is a formula worth knowing. A tuple is simpler in every respect except one, which is that CPython keeps free lists of small ones and hands out recycled objects. That last part sets up O12.
""")


raise SystemExit(lesson.save())
