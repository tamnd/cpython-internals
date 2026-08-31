#!/usr/bin/env python
"""O03. Dunders and the slots behind them.

The third lesson of the object model part. O02 opened the type struct and skipped past the
seventy odd function pointer fields in the middle of it. This lesson is about those fields and
about the one table that connects them to the names you write.

Python code never assigns to `tp_repr`. It defines `__repr__` and something fills the slot in.
That something is a table of ninety four rows in typeobject.c, and it is walked in both
directions: forwards when you define a class, backwards when a type written in C is made ready
and its slots have to be exposed as attributes.

Almost every rule people learn about dunder methods as a separate quirk falls out of that one
table. A dunder set on an instance does nothing. `__len__` gives you truthiness. `__getitem__`
gives you iteration. Defining `__eq__` makes your class unhashable. All four are the same
mechanism seen from different angles, and all four are checkable in a few lines.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("o03-dunders-and-slots", "o03")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("o03-dunders-and-slots").figure


lesson.md(f"""
# O03. Dunders and the slots behind them

{badge}

O02 opened the type struct and walked past the interesting part. In the middle of it are about seventy fields that are function pointers: `tp_repr`, `tp_hash`, `tp_call`, `tp_iter` and the rest. The interpreter reads those directly. When you write `repr(x)`, C code reaches into `Py_TYPE(x)->tp_repr` and calls whatever is there.

But you never set `tp_repr`. You write `__repr__` and it works. Something in between knows those two names belong together, and that something is a table.

{figure("the-table-runs-both-ways", "the same table read forwards for a Python class and backwards for a C type")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Objects/typeobject.c:11584-11590@v3.15.0rc1#slotdefs`.

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

Everything below was checked against the version this cell prints and against 3.14. The two agree on every line of output in this lesson.
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
## Ninety four rows

The table is called `slotdefs`, {cite("Objects/typeobject.c:11584-11590@v3.15.0rc1#slotdefs")}, and each row is written with one of a dozen small macros, {cite("Objects/typeobject.c:11546-11553@v3.15.0rc1#TPSLOT")}. A row holds the dunder name, the byte offset of the slot inside `PyHeapTypeObject`, a function to install when Python defines the name, a wrapper to expose when C defines the slot, and a docstring.

{figure("one-row-of-the-table", "the five things one row of slotdefs holds")}

The table is sorted by that offset rather than by name, which is the first clue that it is meant to be walked rather than searched.

Reading it backwards is a function called `add_operators`, {cite("Objects/typeobject.c:12456-12470@v3.15.0rc1#add_operators")}. It runs when a type is made ready, walks every row, and for each slot that has a function in it puts a {term("slot wrapper")} in the type's dict under the dunder name. That is where `int.__add__` comes from. Nobody wrote it. It is `nb_add` wrapped so Python can call it.

You can see the result on `object`. Sort its attributes by what kind of thing they are and the slot wrappers stand out from the ordinary methods, which came from a different table entirely.

{lesson.claim("the dunder methods on a builtin type are slot wrappers generated from its C slots, and they are a different kind of object from both the plain methods on the same type and the functions you write in a class body")}
""")


lesson.code(
    """
kinds = {}
for name in dir(object):
    kinds.setdefault(type(getattr(object, name)).__name__, []).append(name)

for kind, found in sorted(kinds.items()):
    print(f"  {kind:26} {len(found):>2}   {' '.join(sorted(found)[:3])}")
"""
)


lesson.md("""
Three of those kinds matter here. A `wrapper_descriptor` came out of a slot. A `method_descriptor` came out of the type's ordinary method table, which is a different table with no slots in it. And a plain `function` is what you get when you write the method yourself in a class body.

Line them up next to each other and the difference is one word of output.
""")


lesson.code(
    """
class P:
    def __repr__(self):
        return "p"


for label, value in [
    ("object.__repr__", object.__repr__),
    ("int.__add__", int.__add__),
    ("P.__repr__", P.__repr__),
]:
    print(f"  {label:18}  {type(value).__name__}")

print()
print(f"  object.__repr__.__objclass__  {object.__repr__.__objclass__}")
print("  so the wrapper remembers which type's slot it came out of")
"""
)


lesson.md(f"""
## Why a dunder on an instance does nothing

Now the other direction. When you write a class in Python, your `__repr__` goes into the class dict as an ordinary function. Then `fixup_slot_dispatchers` walks the same table, {cite("Objects/typeobject.c:12129-12138@v3.15.0rc1#fixup_slot_dispatchers")}, and for every row whose name is in your class dict it puts the row's dispatcher into the slot.

For `__repr__` that dispatcher is `slot_tp_repr`, and it is three lines long, {cite("Objects/typeobject.c:10524-10530@v3.15.0rc1#SLOT0")}. All it does is look the dunder name up and call it.

The important word is where it looks. It looks on the type.

{figure("looked-up-on-the-type", "repr going through the slot to a lookup on the type, with the instance dict never consulted")}

That is the whole explanation for a thing that catches everybody at least once. Setting `__repr__` on an instance puts it in the instance dict, where `repr()` will never look, because `repr()` goes through the slot and the slot goes to the type. The attribute is really there. You can call it by hand. The built in function still ignores it.

{lesson.claim("a dunder assigned to an instance is a real attribute you can call by name, and the built in function that would use it never sees it, because the slot looks the name up on the type")}
""")


lesson.code(
    """
class Q:
    pass


q = Q()
q.__repr__ = lambda: "set on the instance"

print(f"  it really is in the instance dict   {'__repr__' in q.__dict__}")
print(f"  calling it by name works            {q.__repr__()}")
print(f"  and repr(q) ignores it completely   {repr(q).startswith('<')}")
"""
)


lesson.md(f"""
The same machinery runs the other way when you assign to the class instead. `type.__setattr__` calls `update_slot`, {cite("Objects/typeobject.c:12086-12096@v3.15.0rc1#update_slot")}, which finds every row of the table with that name and refills the matching slot, on the type and on all of its subclasses.

So this is not something that happens once at class creation time. Assign `__repr__` to a class an hour later and `repr()` changes immediately, for that class and for everything that inherits from it. Delete it and the slot goes back to what it inherited.

{lesson.claim("assigning a dunder to a class updates the slot at once, on that class and on every subclass of it, and deleting it puts the inherited behaviour back")}
""")


lesson.code(
    """
class R:
    pass


class Child(R):
    pass


print(f"  to start with     repr is the default: {repr(R()).startswith('<')}")

R.__repr__ = lambda self: "the one I just assigned"
mine, inherited = repr(R()), repr(Child())
print(f"  after assigning   {mine}")
print(f"  and the subclass  {inherited}")

del R.__repr__
print(f"  after deleting    repr is the default again: {repr(R()).startswith('<')}")
"""
)


lesson.md(f"""
## One name, several slots

The table is not a one to one mapping and the comment above it says so, {cite("Objects/typeobject.c:11522-11531@v3.15.0rc1")}. Several names can point at one slot, and one name can appear in several rows.

{figure("one-name-many-slots", "four rows of the mapping and what each one buys you")}

`__len__` is the easy case. It appears twice, once as `mp_length` and once as `sq_length`, {cite("Objects/typeobject.c:11740-11753@v3.15.0rc1#MPSLOT")}, so defining it once fills both. That is why a class with only a `__len__` gets truthiness for free: `bool()` has no `__bool__` to call, so it falls back on the length.

`__getitem__` is the fun one. It fills `mp_subscript` and `sq_item`, and `sq_item` is the old sequence protocol, the one that predates iterators. Anything that wants to iterate will use it if there is no `__iter__`, asking for item 0, item 1, item 2 and so on until it gets an `IndexError`. So a class with a single `__getitem__` and nothing else is iterable, and supports `in`, without either of the dunders you would expect to need.

{lesson.claim("a class defining only __getitem__ can be iterated over and used with in, because that one name fills the sq_item slot and the old sequence protocol is still what iteration falls back on")}
""")


lesson.code(
    """
class Countdown:
    def __getitem__(self, index):
        if index > 4:
            raise IndexError(index)
        return 10 - index


it = Countdown()

print(f"  Countdown has no __iter__       {'__iter__' not in dir(Countdown)}")
print(f"  and no __contains__             {'__contains__' not in dir(Countdown)}")
print(f"  and yet list(it) is             {list(it)}")
print(f"  and 7 in it is                  {7 in it}")


class Sized:
    def __len__(self):
        return 3


print()
print(f"  Sized has no __bool__           {'__bool__' not in dir(Sized)}")
print(f"  and bool(Sized()) is            {bool(Sized())}")
"""
)


lesson.md(f"""
## One slot, two names

The other direction is more interesting, because when two names share a slot the slot has to decide between them at call time.

`__add__` and `__radd__` both fill `nb_add`. There is only one pointer, so `a + b` cannot dispatch on which method exists. Instead the dispatcher is generated by a macro that has the whole decision written into it, {cite("Objects/typeobject.c:10573-10600@v3.15.0rc1#SLOT1BINFULL")}, and it asks two questions before it will consider the reflected call.

{figure("who-goes-first", "the two questions the shared slot asks before running the reflected method")}

First, is the right hand type a subclass of the left hand type. Second, does the right hand type actually define `__radd__` itself rather than inheriting it. Only if both are true does `__radd__` go first. Otherwise `__add__` runs, and `__radd__` gets its ordinary turn afterwards if `__add__` returns `NotImplemented`.

The second question is the one worth remembering. The macro calls `method_is_overloaded`, and inheriting `__radd__` from a shared base does not count as overloading it.

{lesson.claim("a subclass that defines __radd__ itself is called before the base class __add__, and an unrelated class defining __radd__ is not, because both names share one slot and the dispatcher checks the subclass relationship first")}
""")


lesson.code(
    """
class Money:
    def __add__(self, other):
        return "Money.__add__ ran"


class Extra(Money):
    def __radd__(self, other):
        return "Extra.__radd__ ran"


class Other:
    def __radd__(self, other):
        return "Other.__radd__ ran"


print(f"  Money() + Other()   {Money() + Other()}")
print(f"  Money() + Money()   {Money() + Money()}")
print(f"  Money() + Extra()   {Money() + Extra()}")
print()
print("  the third line is the odd one, and it is odd on purpose:")
print("  a subclass gets to answer for itself before its base does")
"""
)


lesson.md(f"""
## Why defining __eq__ takes __hash__ away

This one usually gets taught as a rule to memorise. It is not a rule, it is two pieces of slot machinery meeting.

{figure("how-eq-loses-hash", "the three steps between defining eq and getting None in hash")}

When a new type inherits its slots from its base, the comparison slots get special treatment, and the question asked is `overrides_hash`, {cite("Objects/typeobject.c:8808-8818@v3.15.0rc1#overrides_hash")}. It looks for `__eq__` in the class dict, and if it does not find that it looks for `__hash__`. If either is there, neither `tp_richcompare` nor `tp_hash` is copied down from the base.

Then, later in making the type ready, `type_ready_set_hash` finds `tp_hash` still empty and no `__hash__` in the dict, {cite("Objects/typeobject.c:9370-9391@v3.15.0rc1#type_ready_set_hash")}. So it sets the slot to `PyObject_HashNotImplemented` and writes a real `None` into the class dict.

That last part is why the effect is so visible. Your class does not merely fail to inherit a hash. It has an actual `__hash__` attribute whose value is `None`, put there by C code, and you can look at it.

{lesson.claim("a class that defines __eq__ and not __hash__ ends up with a real None stored under __hash__ in its class dict, and putting a hash back is a one line assignment")}
""")


lesson.code(
    """
class Same:
    def __eq__(self, other):
        return True


class SameHashed:
    def __eq__(self, other):
        return True

    __hash__ = object.__hash__


print(f"  Same.__hash__ is                  {Same.__hash__}")
print(f"  and it is really in the dict:     {'__hash__' in Same.__dict__}")

try:
    hash(Same())
except TypeError as error:
    print(f"  hash(Same()) raises               TypeError: {error}")

print()
print(f"  SameHashed put one back, and it works: {isinstance(hash(SameHashed()), int)}")
"""
)


lesson.md("""
## Try it yourself

Three things to poke at.

Find every name that gives you a slot wrapper on some builtin type but a plain function on a class you write. Walk `dir(list)` and `dir(str)`, check the type of each attribute, and you have most of the table's left hand column without ever opening the C file.

Define a class with `__getitem__` that never raises `IndexError`, then call `list()` on it and be ready to interrupt. The old sequence protocol has no idea how long anything is, and the only thing that stops it is the exception. This is why `__iter__` was worth adding.

Take the `Money` and `Extra` example and make `Extra` inherit `__radd__` from a shared base instead of defining it. The answer changes, because the dispatcher asks whether the subclass defines the method itself.

## What just happened

There are about seventy function pointer slots in a type object and a table of ninety four rows connecting them to dunder names. Everything in this lesson is that table being read in one direction or the other.

Backwards, when a C type is made ready: `add_operators` turns each filled slot into a slot wrapper in the class dict, which is where `int.__add__` and `object.__repr__` come from.

Forwards, when you write a class: `fixup_slot_dispatchers` puts a generic dispatcher into each slot whose name you defined. That dispatcher looks the name up on the type every time it runs, which is why a dunder set on an instance is ignored and why assigning one to a class takes effect at once, on that class and on its subclasses.

The mapping is not one to one either way. `__len__` fills two slots, so it gives you truthiness. `__getitem__` fills two slots, so it gives you iteration and `in`. And `__add__` and `__radd__` share one slot, so the dispatcher has the subclass rule baked into it.

The `__eq__` and `__hash__` link is two mechanisms meeting: `overrides_hash` stops the slot being inherited, and `type_ready_set_hash` writes a literal `None` in its place.

## What is next

O04 is the method resolution order. Everything in this lesson assumed there was one obvious base class to inherit a slot from. With more than one base there is not, and CPython uses an algorithm with a name and a paper behind it to put the bases in an order that makes inheritance mean something. It also refuses to build the class at all when no such order exists, and seeing that failure is the fastest way to understand what the algorithm is protecting.
""")


raise SystemExit(lesson.save())
