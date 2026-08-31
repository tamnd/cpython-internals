#!/usr/bin/env python
"""O05. What a dot does.

The fifth lesson of the object model part. O04 built the list of classes a name gets looked up
in. This one is about the function that reads that list, and about the three other places it
looks before and after.

`PyObject_GenericGetAttr` is a hundred and twenty lines and it explains almost everything people
learn about attributes as separate rules. Why a property cannot be shadowed by an instance
attribute. Why a method can. Why `__getattr__` and `__getattribute__` are not variants of each
other. Why looking a name up on a class takes a different function entirely and passes `None`
where the instance would go.

Then there is the part that makes it fast, which is a per interpreter cache keyed on a version
number that gets zeroed whenever anything about a class changes, and the bytecode rewriting
itself around what the cache keeps saying.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("o05-what-a-dot-does", "o05")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("o05-what-a-dot-does").figure


lesson.md(f"""
# O05. What a dot does

{badge}

O04 finished with a four line loop: walk the MRO, do a dict lookup in each class, stop at the first hit. That loop is real, but it is only one of four things that happen when you write `x.name`, and it is not the first.

{figure("five-steps-in-order", "the four places a lookup checks, in the fixed order it checks them")}

Everything people learn about attributes as a separate rule is this one order. A property cannot be shadowed by an instance attribute, and a method can. `__getattr__` runs sometimes and `__getattribute__` runs always. Looking a name up on a class behaves differently from looking it up on an instance. Four rules, one function.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Objects/object.c:1887-1926@v3.15.0rc1#_PyObject_GenericGetAttrWithDict`.

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

Everything below was checked against the version this cell prints and against 3.14. One cell has a different wording on the two, and it says so.
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
## Four places, one order

The function is `_PyObject_GenericGetAttrWithDict`, {cite("Objects/object.c:1887-1926@v3.15.0rc1#_PyObject_GenericGetAttrWithDict")}, and `PyObject_GenericGetAttr` is a one line wrapper around it. Read past the error checking and it does four things in this order.

One: walk the type's MRO for the name. That is O04's loop, and the result is called `descr` for the rest of the function.

Two: if what came back has a `__get__` and also a `__set__`, call `__get__` right there and return. Something with both is a {term("data descriptor")}, and this branch is the only reason a property wins.

Three: otherwise look in the instance dict, and return that if it is there, {cite("Objects/object.c:1964-1979@v3.15.0rc1")}.

Four: otherwise fall back on what the MRO found. If it has a `__get__`, call it. If it is a plain value, return it. If there was nothing at all, raise `AttributeError`, {cite("Objects/object.c:1981-2002@v3.15.0rc1")}.

{figure("who-wins", "which of the type and the instance dict wins, for each kind of thing on the type")}

So the type is consulted first but usually does not win, because step two only fires for a data descriptor. The whole of the famous precedence rule is the position of one `if`.

{lesson.claim("with the same name present on the type and in the instance dict, a data descriptor on the type wins and a non data descriptor loses, and the instance dict entry is untouched either way")}
""")


lesson.code(
    """
class NonData:
    def __get__(self, obj, owner):
        return "the non data descriptor on the type"


class Data:
    def __get__(self, obj, owner):
        return "the data descriptor on the type"

    def __set__(self, obj, value):
        pass


class Sample:
    plain = "a plain class attribute"
    nondata = NonData()
    data = Data()


s = Sample()
for name in ["data", "plain", "nondata"]:
    s.__dict__[name] = "the instance dict"

for name in ["data", "plain", "nondata"]:
    print(f"  s.{name:8}  {getattr(s, name)}")
    print(f"    and s.__dict__[{name!r}] is still {s.__dict__[name]!r}")
"""
)


lesson.md(f"""
The instance dict entry for `data` is right there and the lookup ignored it. That is not a special case for properties, it is step two firing before step three.

This also explains something that sounds unrelated. A method is a function, and a function has `__get__` but no `__set__`, so it is a non data descriptor and step three beats it. That is why `obj.method = something` works and shadows the method for that one object, while `obj.some_property = something` does not shadow anything and instead calls the property's setter.

## Two hooks that are not the same hook

`__getattribute__` and `__getattr__` differ by five characters and by almost everything else.

{figure("two-hooks-not-one", "when each of the two hooks runs and what happens when it does not")}

`__getattribute__` is the slot. Everything above is the default implementation of it. Override it and you replace the whole four step function, for every attribute, including `__dict__` and `__class__`.

`__getattr__` is not a slot at all. There is no default. It is a name the slot dispatcher looks for, and if a class has one, `update_one_slot` installs a different dispatcher called `_Py_slot_tp_getattr_hook`, {cite("Objects/typeobject.c:10990-11026@v3.15.0rc1#_Py_slot_tp_getattr_hook")}. That one runs the normal lookup with errors suppressed, and only calls your `__getattr__` if the normal lookup came back empty.

There is a small piece of housekeeping worth seeing in that function. If a class has no `__getattr__`, the hook dispatcher swaps itself out of the slot for the simpler one and never runs again, {cite("Objects/typeobject.c:11002-11009@v3.15.0rc1")}.

{lesson.claim("__getattr__ runs only for names the normal lookup failed to find, while an overridden __getattribute__ runs for every name including __dict__")}
""")


lesson.code(
    """
class Fallback:
    on_the_class = 1

    def __getattr__(self, name):
        return f"__getattr__ made up {name!r}"


f = Fallback()
f.on_the_instance = 2

print(f"  f.on_the_class     {f.on_the_class}")
print(f"  f.on_the_instance  {f.on_the_instance}")
print(f"  f.missing          {f.missing}")


class Every:
    def __getattribute__(self, name):
        return f"__getattribute__ saw {name!r}"

    def __getattr__(self, name):
        return "this is never reached"


e = Every()
e.here = "this really is in the instance dict"

print()
print(f"  e.here      {e.here}")
print(f"  e.missing   {e.missing}")
print(f"  e.__dict__  {e.__dict__}")
"""
)


lesson.md(f"""
The last line is the one to sit with. `e.__dict__` went through `__getattribute__` too, so there is now no ordinary way to see what is actually in that object. `object.__getattribute__(e, "__dict__")` still works, because that calls the C function directly instead of going through the type.

Both hooks live on the type, like every other dunder in O03, so setting `__getattr__` on an instance does nothing at all.

{lesson.claim("assigning __getattr__ to an instance leaves it in the instance dict and has no effect on attribute lookup")}
""")


lesson.code(
    """
class Quiet:
    pass


q = Quiet()
q.__getattr__ = lambda name: "set on the instance"

print(f"  it is in the instance dict   {'__getattr__' in q.__dict__}")
try:
    value = q.missing
except AttributeError as error:
    print(f"  and q.missing still raises   AttributeError: {error}")
"""
)


lesson.md(f"""
## A class is looked up differently

`Klass.name` does not run `PyObject_GenericGetAttr`. A type is an object whose type is `type`, so the slot that runs is `type`'s own `tp_getattro`, which is `_Py_type_getattro_stackref`, {cite("Objects/typeobject.c:6570-6600@v3.15.0rc1#_Py_type_getattro_stackref")}.

{figure("a-class-is-different", "the metaclass MRO first, then the class's own MRO")}

Same shape, one level up. It looks in the metaclass's MRO first, and if it finds a data descriptor there it calls it and stops, {cite("Objects/typeobject.c:6600-6616@v3.15.0rc1")}. Only then does it look in the class's own MRO, {cite("Objects/typeobject.c:6618-6650@v3.15.0rc1")}.

There is one more difference and it is the one that matters in practice. When this function finds a descriptor on the class, it calls `__get__` with `NULL` for the instance, because there is no instance. That is the `None` you get as the second argument, and it is how a descriptor tells `Klass.thing` from `Klass().thing`.

{lesson.claim("a name defined on the metaclass is reachable through the class and not through an instance of it, and a descriptor found on a class is called with None where the instance would be")}
""")


lesson.code(
    """
class Meta(type):
    from_the_metaclass = "found on the metaclass"


class Klass(metaclass=Meta):
    from_the_class = "found on the class"


print(f"  Klass.from_the_class      {Klass.from_the_class}")
print(f"  Klass.from_the_metaclass  {Klass.from_the_metaclass}")
try:
    value = Klass().from_the_metaclass
except AttributeError as error:
    print(f"  Klass().from_the_metaclass  AttributeError: {error}")


class Watcher:
    def __get__(self, obj, owner):
        return f"obj={obj!r} owner={owner.__name__}"


class Holder:
    watched = Watcher()

    def __repr__(self):
        return "a Holder"


print()
print(f"  Holder.watched    {Holder.watched}")
print(f"  Holder().watched  {Holder().watched}")
"""
)


lesson.md(f"""
The two error messages are different too, and now you know why: one comes out of the object function and one out of the type function.

{lesson.claim("the AttributeError for an instance and for a class have different wording, and the exception carries the name and the object as attributes")}
""")


lesson.code(
    """
class Empty:
    pass


for target, label in [(Empty(), "an instance"), (Empty, "the class")]:
    try:
        value = target.nope
    except AttributeError as error:
        print(f"  {label:12}  {error}")


class Config:
    def __init__(self):
        self.threshold = 1


try:
    value = Config().treshold
except AttributeError as error:
    print()
    print(f"  error.name        {error.name!r}")
    print(f"  error.obj is it   {isinstance(error.obj, Config)}")
    print(f"  the message       {error}")
"""
)


lesson.md(f"""
The `name` and `obj` attributes are not decoration. `_PyObject_SetAttributeErrorContext` attaches them on the way out, {cite("Objects/object.c:1996-2002@v3.15.0rc1")}, and the traceback machinery uses them later to look for a near miss among the attributes the object actually has. So the suggestion is not in the message. It is added at print time, out of `obj`, and it costs nothing unless the program is already on its way to a traceback.

{lesson.claim("the did you mean suggestion is not part of the exception message and only appears when a traceback is formatted, because it is computed from the obj attribute at that point")}
""")


lesson.code(
    """
import traceback

try:
    value = Config().treshold
except AttributeError as error:
    print(f"  str(error)      {error}")
    print(f"  the traceback   {traceback.format_exc().splitlines()[-1]}")
""",
    differs="On 3.14 the suggestion is worded `Did you mean: 'threshold'?`. 3.15 spells out both names with the dot in front, which reads better when the name is a long one.",
)


lesson.md(f"""
## How this is not slow

Steps one and two happen on every single attribute access, and step one is a walk over the MRO doing a dict lookup per class. For `self.x` inside a loop that would be several dict lookups per iteration, which would be terrible.

It is not, because of a cache. Each interpreter has one flat hash table of four thousand and ninety six entries, and each entry holds a type version, a name, and the answer, {cite("Objects/typeobject.c:6306-6345@v3.15.0rc1#_PyType_LookupStackRefAndVersion")}.

{figure("the-version-tag", "the version tag, and what happens to it when a class changes")}

The version is `tp_version_tag`, a number on the type. A hit needs both the version and the interned name pointer to match, so one comparison of two words replaces the whole walk.

Invalidation is the elegant part. There is no pass over the cache looking for stale entries. `type_modified_unlocked` sets `tp_version_tag` to zero on the class and on every subclass, {cite("Objects/typeobject.c:1166-1195@v3.15.0rc1#type_modified_unlocked")}, and every entry that mentioned the old version simply stops matching. A type with a zero tag is never cached at all.

There are two limits worth knowing. A name longer than a hundred characters is never cached, {cite("Objects/typeobject.c:44-58@v3.15.0rc1#MCACHE_CACHEABLE_NAME")}, and a class that has been modified a thousand times stops getting new version tags for good, {cite("Objects/typeobject.c:1389-1392@v3.15.0rc1#MAX_VERSIONS_PER_CLASS")}. The second one is why a class you keep reassigning attributes on gets permanently slower.

{lesson.claim("the cache and the version tag are not visible from Python at all, since nothing exposes tp_version_tag, the hit rate, or the cache contents", unobservable="the effect is only measurable as a timing difference, and the specialised bytecode in the next section is the closest observable proxy")}

## Where you can see it

The cache is invisible, but the thing built on top of it is not. After a piece of bytecode has done the same kind of lookup a few times, the interpreter rewrites the instruction in place into a form that assumes the shape it keeps seeing. `dis` will show you the rewritten form if you ask for it.

{figure("specialised-then-not", "the instruction changing form, failing its guard, and settling on a new one")}

The guard on the specialised instruction is that same version tag, which is the connection. This is the very short version of a story that belongs to the interpreter part, but the attribute lookup case is the clearest one and it is right here.

{lesson.claim("the same LOAD_ATTR instruction takes a different specialised form depending on whether the attribute lives in the instance values, in a slot, on a module, or is a method")}
""")


lesson.code(
    """
import dis
import math


def attr_forms(func):
    return [i.opname for i in dis.get_instructions(func, adaptive=True) if "LOAD_ATTR" in i.opname]


def show(func, label):
    print(f"  {label:32} {attr_forms(func)}")


class Point:
    def __init__(self, x):
        self.x = x

    def scaled(self):
        return self.x * 2


class Slotted:
    __slots__ = ("x",)

    def __init__(self, x):
        self.x = x


def read_value(point):
    return point.x


def read_slot(point):
    return point.x


def read_method(point):
    return point.scaled()


def read_module(module):
    return module.pi


point = Point(1)
show(read_value, "before it has ever run")
read_value(point)
show(read_value, "after one call")

for _ in range(100):
    read_value(point)
    read_slot(Slotted(1))
    read_method(point)
    read_module(math)

show(read_value, "after a hundred")
show(read_slot, "a __slots__ class instead")
show(read_method, "a method rather than a value")
show(read_module, "an attribute of a module")
"""
)


lesson.md(f"""
Four different instructions, from four identical looking lines of Python. `LOAD_ATTR_INSTANCE_VALUE` reads a fixed offset in the inline values array with no dict lookup at all. `LOAD_ATTR_SLOT` reads a fixed offset in the object. `LOAD_ATTR_MODULE` skips straight to a module's dict. `LOAD_ATTR_METHOD_WITH_VALUES` fetches the function without building a bound method object.

Now break the assumption and watch it recover.

{lesson.claim("assigning a property over an attribute the specialised instruction was relying on makes the guard fail, and the instruction goes back to the general form and then settles on a different specialised one")}
""")


lesson.code(
    """
show(read_value, "specialised on instance values")

Point.x = property(lambda self: 99)
show(read_value, "right after the class changed")

read_value(point)
show(read_value, "after running it once more")

for _ in range(100):
    read_value(point)
show(read_value, "and after a hundred more")

print(f"  and read_value(point) now gives   {read_value(point)}")
"""
)


lesson.md("""
The instruction did not change the moment the class did. It changed the next time it ran and its guard failed, and even then it went back to the general form first and waited a while before committing to the new shape. That backoff is deliberate: an object that keeps changing shape should not pay to re specialise on every access.

## Try it yourself

Three things to poke at.

Write a class with `__getattribute__` that prints the name and then calls `object.__getattribute__` for the real answer, and use one of its instances normally for a few lines. The list of names that go through it is longer than you expect, and most of them are dunders you never wrote.

Take the precedence table and add a fifth row: a data descriptor on the type whose `__get__` raises `AttributeError`. Then call `hasattr`. The lookup function suppresses that one exception and nothing else, which is why `hasattr` returns `False` there and propagates a `ValueError` from the same place.

Time `point.x` on a plain class against the same attribute on a `__slots__` class, a thousand accesses each, using `timeit`. Then assign something new to the class in between and time it again. The numbers are the only view you get of the cache, and they move.

## What just happened

`x.name` is one function doing four things in a fixed order: walk the type's MRO, use what it found if that is a data descriptor, otherwise use the instance dict, otherwise fall back on what the MRO found and raise if there was nothing.

Everything that gets taught as a precedence rule is the position of one `if` in that function. A property has `__set__`, so it wins. A function does not, so an instance attribute of the same name shadows the method.

`__getattribute__` is the slot and runs for everything. `__getattr__` is not a slot, has no default, and only runs when the normal path came back empty. A class with one gets a different dispatcher installed, and that dispatcher removes itself when there is nothing to dispatch to.

Looking a name up on a class runs a different function that checks the metaclass first and then the class, and calls any descriptor it finds with `None` where the instance would go. The two `AttributeError` messages are different because they come from different functions, and the exception carries the name and the object so a traceback can suggest a near miss.

All of it is fast because of a four thousand entry cache keyed on a version number per type. Changing anything on a class zeroes that number on the class and every subclass, and every cached entry quietly stops matching. Nothing about the cache is visible from Python, but the specialised bytecode built on top of it is, and it takes a different form for instance values, slots, modules and methods.

## What is next

O06 is descriptors properly. This lesson used them as a thing that either has `__set__` or does not. The next one is about what they are: `property`, `classmethod`, `staticmethod` and the bound method you get from `obj.method` are all the same protocol, and three of the four are less than twenty lines of C.
""")


raise SystemExit(lesson.save())
