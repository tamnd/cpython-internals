#!/usr/bin/env python
"""O08. Where attributes really live.

The eighth lesson of the object model part. O07 built a dict and showed how much a small one
costs. This one is about the fact that an ordinary instance does not have one.

Every instance of a class tends to carry the same attribute names as its siblings, so the names
are kept once, on the type, and each instance holds only a bare array of values stored inside
the object itself. Two attributes cost about 125 bytes per instance that way and about 350 the
obvious way, and the compiler helps by writing down every `self.name` it sees while compiling
the class body.

The lesson measures all three shapes with tracemalloc, finds the 30 name cliff, and shows the
bytecode changing the moment something asks for `__dict__`.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("o08-where-attributes-really-live", "o08")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("o08-where-attributes-really-live").figure


lesson.md(f"""
# O08. Where attributes really live

{badge}

O07 built a dict and measured one. A dict with two string keys costs 184 bytes, and most of that is a hash table with six empty slots in it.

Now think about ten thousand instances of the same class. In the obvious design that is ten thousand hash tables, each holding the same two names, each mostly empty.

{figure("one-copy-of-the-keys", "the same two attributes, stored the obvious way and the way CPython does it")}

CPython does not do that. The names are kept once, on the type. Each instance carries a bare array of values, stored inside the object itself, and there is no dict at all until something asks for one.

This lesson measures the difference, finds the point where the trick stops working, and watches the bytecode change the moment you break it.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Objects/dictobject.c:7241-7274@v3.15.0rc1#_PyObject_InitInlineValues`.

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

Everything below was checked against the version this cell prints and against 3.14. The two agree on everything here except a couple of bytes in the memory measurements.
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
## The compiler already knows the names

Start somewhere unexpected. When the compiler works through a class body it keeps a list of every name assigned to `self` in any method, and stores that list on the class, {cite("Python/codegen.c:1614-1624@v3.15.0rc1")}.

You can read it.

{lesson.claim("the compiler records every attribute assigned to self inside a class body and stores the names on the class as __static_attributes__")}
""")


lesson.code("""
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def move(self, dx):
        self.x += dx
        self.moved = True


class Nothing:
    pass


print(f"  Point.__static_attributes__    {Point.__static_attributes__}")
print(f"  Nothing.__static_attributes__  {Nothing.__static_attributes__}")
""")


lesson.md(f"""
Note that `moved` is in there even though `__init__` never sets it. The compiler looked at every method, not just the constructor, and it is a purely syntactic list. Anything set on an instance from outside the class body does not appear. The tuple comes out sorted, {cite("Python/compile.c:992-1006@v3.15.0rc1#_PyCompile_StaticAttributesAsTuple")}, so the order you see is alphabetical and not the order the assignments appear in.

That tuple is not for you. It is for `_PyDict_NewKeysForClass`, {cite("Objects/dictobject.c:7210-7238@v3.15.0rc1#_PyDict_NewKeysForClass")}, which runs when the class is created. It builds one keys array, marks it `DICT_KEYS_SPLIT`, and walks `__static_attributes__` inserting each name.

{figure("how-the-keys-get-filled", "where the shared names come from")}

So by the time the first instance exists, the type already has a keys array with those names in it. The keys array is the same `PyDictKeysObject` from O07: a slot array, an entry array, the same probe loop. What is missing is the values. In a shared keys array the entries hold names and nothing else, {cite("Objects/dictobject.c:53-65@v3.15.0rc1")}.
""")


lesson.md(f"""
## What an instance actually holds

An instance of such a class gets its values allocated as part of the object, past whatever fields the type declared, {cite("Include/internal/pycore_object.h:948-956@v3.15.0rc1#_PyObject_InlineValues")}. There is no separate allocation and no pointer to chase.

{figure("what-an-instance-holds", "an ordinary instance, top to bottom")}

The setup is {cite("Objects/dictobject.c:7241-7274@v3.15.0rc1#_PyObject_InitInlineValues")} and it is short: take the keys array off the type, work out how many values it can hold, write four bytes of bookkeeping, and set every value pointer to `NULL`. The pointer where a dict would go is set to `NULL` as well.

Those four bytes are `capacity`, `size`, `embedded` and `valid`, {cite("Include/internal/pycore_dict.h:242-258@v3.15.0rc1#SHARED_KEYS_MAX_SIZE")}. After the value pointers comes one more byte per attribute actually set, holding the slot it went into, {cite("Include/internal/pycore_dict.h:326-342@v3.15.0rc1#_PyDictValues_AddToInsertionOrder")}. That little byte array is how a shared keys layout still gets per instance insertion order, and it is why two instances of the same class can iterate their attributes in different orders while sharing one set of names.

{lesson.claim("two instances of the same class keep their own attribute order even though the names themselves are stored once, on the type")}
""")


lesson.code("""
class Free:
    pass


first, second = Free(), Free()

first.alpha = 1
first.beta = 2

second.beta = 2
second.alpha = 1

print(f"  vars(first)   {list(vars(first))}")
print(f"  vars(second)  {list(vars(second))}")
print(f"  same contents {vars(first) == vars(second)}")
""")


lesson.md(f"""
`Free` has an empty `__static_attributes__`, so neither name was there when the class was made. They get added on first use, one at a time, by `insert_split_key`, {cite("Objects/dictobject.c:1908-1936@v3.15.0rc1#insert_split_key")}. It looks the name up in the shared keys, and if it is not there and there is still room, appends it. The name goes in once no matter how many instances set it.

## What it costs

Now measure. Three classes, the same two attributes on every instance, ten thousand instances each, and `tracemalloc` for the total.

{figure("the-cost-of-each-shape", "bytes per instance for each of the three shapes")}

{lesson.claim("an instance sharing its keys with its class costs roughly a third of what the same instance costs once it has a dict of its own")}
""")


lesson.code(
    """
import tracemalloc

POOL = [f"attr{n}" for n in range(40)]


class Shared:
    def __init__(self, n):
        self.attr0 = n
        self.attr1 = n


class Spread:
    def __init__(self, n):
        setattr(self, POOL[n % 40], n)
        setattr(self, POOL[(n + 1) % 40], n)


def touched(n):
    made = Shared(n)
    made.__dict__["attr0"] = n
    return made


def bytes_each(make, count=10000):
    tracemalloc.start()
    keep = [make(n) for n in range(count)]
    used, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert len(keep) == count
    return used // count


print(f"  two names, shared with the class   {bytes_each(Shared):4} bytes each")
print(f"  the same, after touching __dict__  {bytes_each(touched):4} bytes each")
print(f"  two names drawn from a pool of 40  {bytes_each(Spread):4} bytes each")
""",
    varies="These are measured byte counts, so they move by a byte or two between versions and "
    "they are smaller on a 32 bit build. The gap between the three lines is the point, and it "
    "is there everywhere.",
)


lesson.md(f"""
Same two attributes on every instance in all three cases. The first keeps them in the object. The second builds a dict for each one. The third cannot share, because the class ended up with forty distinct attribute names and the shared keys array only has room for thirty.

That limit is `SHARED_KEYS_MAX_SIZE`, and it is exactly 30. It is not a soft threshold. The keys array is created at a fixed size and `insert_split_key` stops inserting once the room runs out, at which point every further instance gets a dict of its own.

There is a wrinkle in it, and the wrinkle is one slot wide. `_PyDict_NewKeysForClass` sets the room to 30, and then the first instance ever created takes one, {cite("Objects/dictobject.c:7259-7262@v3.15.0rc1")}. Names that were already inserted at class creation time got in before that happened. Names discovered later did not.

So the answer to "how many attributes can a class share" is 30 if the class says so up front and 29 if it does not. Here is the whole thing, measured. The only difference between the two columns is whether `__static_attributes__` was there when the class was made.

{lesson.claim("a class shares up to 30 attribute names when they are known when the class is created, and only 29 when they are discovered later, because creating the first instance reserves one slot")}
""")


lesson.code(
    """
def setter(cls, n):
    def build(_):
        holder = cls()
        for name in POOL[:n]:
            setattr(holder, name, 0)
        return holder

    return build


for count in [28, 29, 30, 31]:
    told = type(f"Told{count}", (), {"__static_attributes__": tuple(POOL[:count])})
    quiet = type(f"Quiet{count}", (), {})
    up_front = bytes_each(setter(told, count), 2000)
    later = bytes_each(setter(quiet, count), 2000)
    print(f"  {count} names   known up front {up_front:5}   found later {later:5}")
""",
    varies="Byte counts again, so the exact numbers move by a few between builds. Where the "
    "jumps land does not, because SHARED_KEYS_MAX_SIZE is a constant.",
)


lesson.md(f"""
The jump is not gradual. Up to the limit each instance pays for its values and nothing else. Past it, each one pays for a whole dict, and the difference is close to sixfold.

Thirty is a real design choice rather than an accident. The comment on the constant says it has to stay under 250 so a count fits in one byte, and the number chosen is much smaller than that, because a class with more than thirty attributes is unusual and the cost of guessing high is a keys array that most classes barely use.

## What makes a dict appear

Nothing so far has created a dict. Reading `obj.name` reads the shared keys to find a slot number and then reads the values array, which is the fast path O05's `LOAD_ATTR_INSTANCE_VALUE` specialisation is built around.

{figure("reading-it-back", "which operations make a dict appear")}

Asking for `__dict__` is different. There has to be a real dict object to hand back, so one gets built, {cite("Objects/dictobject.c:7292-7311@v3.15.0rc1#_PyObject_MaterializeManagedDict_LockHeld")}. It is still a split dict: it takes a reference to the shared keys and points at the same values, {cite("Objects/dictobject.c:7276-7290@v3.15.0rc1#make_dict_from_instance_attributes")}, so writes through it still reach the instance. But the dict object exists from then on and the instance is bigger for good.

The interpreter can tell. There is a flag on the type, {cite("Include/object.h:472@v3.15.0rc1#Py_TPFLAGS_INLINE_VALUES")}, and the specialised attribute instructions check the values array is still valid before using it.

{lesson.claim("reading an attribute on an instance with inline values specialises to a different instruction than reading one on an instance whose dict has been materialised")}
""")


lesson.code("""
import dis


class Small:
    def __init__(self, n):
        self.value = n


def read_inline(obj):
    return obj.value


def read_after_dict(obj):
    return obj.value


for n in range(100):
    read_inline(Small(n))

for n in range(100):
    made = Small(n)
    made.__dict__["value"] = n
    read_after_dict(made)


def attr_form(func):
    return [i.opname for i in dis.get_instructions(func, adaptive=True) if "LOAD_ATTR" in i.opname]


print(f"  values still in the object  {attr_form(read_inline)}")
print(f"  after __dict__ was asked for {attr_form(read_after_dict)}")
""")


lesson.md("""
Same source line, same class, different instruction. The first form reads a slot number out of the inline cache and indexes the values array. The second could not use that shape, so it stayed general.

This is the practical version of everything above. If a library calls `vars(obj)` on every object it touches, or a debugger inspects `__dict__`, the objects get bigger and their attribute reads get slower, and nothing in the source you wrote changed.

Deleting an attribute does not break the sharing, which is worth checking because it used to.
""")


lesson.code("""
one, two = Shared(1), Shared(2)
del one.attr0

print(f"  vars(one)  {list(vars(one))}")
print(f"  vars(two)  {list(vars(two))}")
""")


lesson.md(f"""
The slot is set to `NULL` in that one instance's values array. The name stays in the shared keys, because it belongs to the class, and every sibling is untouched.

{figure("what-breaks-the-sharing", "the ways an instance ends up with a dict of its own")}

Assigning to `__dict__` is the blunt one. Hand an object a dict and that is the dict it keeps, values array abandoned.

The third case is worth naming. All of this only applies to types that opt in, through two flags, {cite("Include/object.h:482@v3.15.0rc1#Py_TPFLAGS_MANAGED_DICT")}. A class statement gets them. A C extension type has to ask, and most do not, which is why an object from a compiled library often has no `__dict__` at all or a plain one.

The pointer that would hold that dict is not even in the object proper. It sits in front of it, at a negative offset from the object header, {cite("Include/internal/pycore_object.h:922-939@v3.15.0rc1#MANAGED_DICT_OFFSET")}, in the same pre header region as the weak reference list. O01 walked past that region without saying what was in it. This is what was in it.
""")


lesson.md("""
## Try it yourself

Three things to poke at.

Find the cliff yourself, without knowing the number. Write a loop that builds a class with `n` attributes for `n` from 1 to 40, measures bytes per instance, and prints the first `n` where the number jumps. Then do it again with the names listed in `__static_attributes__` and watch the answer move by one.

Break the sharing three different ways and measure each. Assign to `__dict__`, call `vars()`, and add one attribute too many after the fact. Two of the three cost about the same and one is much worse, and the reason is in the section above.

Take a class you actually use, print its `__static_attributes__`, and compare that with the attributes its instances really end up with. Anything set from outside the class body will be missing, and every one of those is a name that gets added to the shared keys lazily rather than up front.

## What just happened

An ordinary instance does not have a dict. The attribute names live once, on the type, in a keys array marked as shared. Each instance carries only an array of value pointers, allocated as part of the object rather than beside it.

The compiler fills that keys array in advance. It records every `self.name` assignment in a class body and stores the sorted tuple as `__static_attributes__`, and the class creation code inserts those names into the shared keys before any instance exists. Names set from outside the class body get added on first use instead, and they have one fewer slot to fit into, because creating the first instance takes one.

Per instance insertion order survives, because after the value pointers there is one byte per attribute set, recording which slot it went into. Two instances can iterate the same attributes in different orders while the names are stored once.

The saving is roughly threefold for a small object, and it disappears in three ways. Too many distinct attribute names, thirty at the outside, and the shared keys array runs out of room. Asking for `__dict__` builds a real dict object, which still shares keys and values but is a permanent extra allocation and stops the attribute read from specialising. Assigning to `__dict__` abandons the values array outright.

Deleting an attribute does none of that. It sets one slot to `NULL` in one instance.

## What is next

O09 is integers. Small ones are shared, big ones are arrays of thirty bit digits, and there is a compact representation for anything that fits in a single digit that the interpreter checks for constantly. It is the first of four lessons on the built in types, where the theme stops being how objects work in general and becomes how much work has gone into the handful of types every program uses.
""")


raise SystemExit(lesson.save())
