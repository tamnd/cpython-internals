#!/usr/bin/env python
"""O06. What property actually is.

The sixth lesson of the object model part. O05 mentioned data descriptors as the thing that
beats the instance dict and left it there. This one is about what they are.

There is one protocol, made of three methods plus a fourth that runs at class creation time.
`property`, `classmethod`, `staticmethod`, the bound method you get from `obj.method`, every
`__slots__` entry and most of what a C extension puts on a type are all the same protocol with
different answers. Three of those are under ten lines of C each.

The lesson writes a descriptor by hand, takes apart the four familiar ones, and then looks at
the five descriptor types C code builds because it cannot write a class body.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("o06-what-property-actually-is", "o06")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("o06-what-property-actually-is").figure


lesson.md(f"""
# O06. What property actually is

{badge}

O05 said a data descriptor wins over the instance dict, and that a plain function does not. It never said what a descriptor is.

Here is the short answer. Put an object in a class dict, give it a `__get__` method, and reading that attribute calls the method instead of handing back the object.

{figure("four-of-a-kind", "four familiar features, one protocol, and the line counts")}

That is it. `property` is that. `classmethod` is that. So is `staticmethod`, and so is the `self` in every method you have ever written. Four things people learn as four separate features, and three of them are under ten lines of C.

This lesson builds one by hand, then reads the four real ones.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Objects/funcobject.c:1264-1270@v3.15.0rc1#func_descr_get`.

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
## Three methods, and one of them changes everything

A {term("descriptor", "any object that defines __get__, __set__ or __delete__ and is stored in a class dict")} is any object with `__get__`, `__set__` or `__delete__` on its type. There is no base class to inherit from and no registration step. Having the method is the whole qualification.

{figure("the-three-methods", "the three methods of the protocol, plus __set_name__")}

Write one and you can watch the calls go past.

{lesson.claim("an object with __get__ and __set__ in a class dict intercepts both reads and writes of that attribute on every instance of the class")}
""")


lesson.code("""
class Logged:
    \"\"\"Stores in the instance dict like normal, and prints every call on the way through.\"\"\"

    def __set_name__(self, owner, name):
        self.name = name
        print(f"  __set_name__ ran for {name!r} on {owner.__name__}")

    def __get__(self, obj, owner):
        if obj is None:
            return self
        print(f"  __get__ called with obj={obj!r} owner={owner.__name__}")
        return obj.__dict__[self.name]

    def __set__(self, obj, value):
        print(f"  __set__ called with value={value!r}")
        obj.__dict__[self.name] = value


class Point:
    x = Logged()

    def __repr__(self):
        return "a Point"


p = Point()
p.x = 3
print(f"  p.x is {p.x}")
print(f"  and the instance dict holds {p.__dict__}")
""")


lesson.md(f"""
Notice what the class body did not do. It never called `__set_name__`, and `Logged` never asked what attribute it was assigned to. Something ran it during the class statement, and there is a section on that at the end.

The other thing to notice is `if obj is None`. `__get__` gets called for `Point.x` as well as for `p.x`, and in the class case there is no instance to pass, so `obj` is `None`. Returning `self` there is the convention, and it is why `Point.x` in a debugger shows you the descriptor rather than blowing up.

Now the split O05 kept referring to. `Logged` has `__set__`, so it is a {term("data descriptor", "a descriptor whose type fills in tp_descr_set, meaning it has __set__ or __delete__")} and it beats the instance dict. Take `__set__` away and it becomes a non data descriptor, and the instance dict beats it instead.

{figure("data-or-not", "the one difference between a data and a non data descriptor")}

The test in C is one line, {cite("Objects/descrobject.c:1028-1032@v3.15.0rc1#PyDescr_IsData")}. It asks whether the descriptor's type has `tp_descr_set` filled in. Not whether the method does anything useful, not whether it is `__set__` or `__delete__`, just whether the slot is non null. That single bit decides the precedence question for every attribute in Python.
""")


lesson.md(f"""
## Every function you have ever written is a descriptor

Start with the one nobody thinks of as a descriptor. A `def` inside a class body makes a plain function object and puts it in the class dict. Nothing else happens at that point.

Then you write `g.greet()` and get a bound method, with `self` already filled in. That happens because `function` has a `__get__`.

{figure("a-function-becomes-a-method", "how a plain function turns into a bound method")}

{lesson.claim("reading a method off an instance calls the function's __get__ and produces a new bound method object each time, while reading it off the class returns the plain function")}
""")


lesson.code("""
class Greeter:
    def hello(self):
        return "hi"

    def __repr__(self):
        return "a Greeter"


g = Greeter()
raw = Greeter.__dict__["hello"]
print(f"  Greeter.__dict__['hello'] is a {type(raw).__name__}")
print(f"  Greeter.hello is that same object  {Greeter.hello is raw}")
print(f"  g.hello is not                     {g.hello is raw}")
print(f"  g.hello                            {g.hello}")
print(f"  g.hello.__func__ is raw            {g.hello.__func__ is raw}")
print(f"  g.hello.__self__ is g              {g.hello.__self__ is g}")
print(f"  raw.__get__(g, Greeter)            {raw.__get__(g, Greeter)}")
print(f"  raw.__get__(None, Greeter) is raw  {raw.__get__(None, Greeter) is raw}")
""")


lesson.md(f"""
The C is seven lines, {cite("Objects/funcobject.c:1264-1270@v3.15.0rc1#func_descr_get")}. If `obj` is `NULL` or `None`, hand back the function unchanged. Otherwise call `PyMethod_New`, {cite("Objects/classobject.c:64-84@v3.15.0rc1#PyMethod_New")}, which allocates a small object holding two pointers: the function and the instance. That is the entire mechanism behind `self`.

There is no `__set__` there, which makes a function a non data descriptor, which is why `g.hello = something_else` works and shadows the method for that one instance. A `property` would refuse.

The other consequence is that `g.hello` is a fresh object every time. Two reads give you two different bound methods that happen to compare equal.
""")


lesson.code("""
a = g.hello
b = g.hello
print(f"  g.hello is g.hello   {a is b}")
print(f"  g.hello == g.hello   {a == b}")
""")


lesson.md(f"""
This is why `obj.method` in a hot loop is not free, and it is also why the interpreter has a `LOAD_METHOD` style specialisation that calls the function directly and skips building the object. `PyMethod_New` does pull from a free list when it can, which takes the edge off. O12 is about those free lists.

## classmethod and staticmethod are a few lines each

Both are descriptors, both are plain Python level objects you can construct yourself, and both are shorter than you would guess.

`staticmethod` is six lines, {cite("Objects/funcobject.c:1794-1799@v3.15.0rc1#sm_descr_get")}. Its `__get__` returns the wrapped callable and ignores both arguments. That is the entire feature. It exists to stop the function's own `__get__` from running.

`classmethod` is eight, {cite("Objects/funcobject.c:1530-1537@v3.15.0rc1#cm_descr_get")}. It calls the same `PyMethod_New` a plain function does, but passes the class instead of the instance. So a classmethod really is a bound method, bound to a class object.

{lesson.claim("classmethod produces a bound method whose __self__ is the class, and the class it binds to is the one the lookup started from rather than the one that defined the method")}
""")


lesson.code("""
class Tools:
    @classmethod
    def cm(cls):
        return cls

    @staticmethod
    def sm():
        return "plain"


sm_raw = Tools.__dict__["sm"]
print(f"  Tools.cm                      {Tools.cm}")
print(f"  Tools.cm.__self__ is Tools    {Tools.cm.__self__ is Tools}")
print(f"  Tools().cm.__self__ is Tools  {Tools().cm.__self__ is Tools}")
print(f"  Tools.sm()                    {Tools.sm()}")
print(f"  staticmethod handed the function straight back  {Tools.sm is sm_raw.__wrapped__}")


class Sub(Tools):
    pass


print(f"  Sub.cm() is Sub               {Sub.cm() is Sub}")
""")


lesson.md(f"""
That last line is the useful part. `cm_descr_get` receives whichever class the lookup started from, so `Sub.cm()` gets `Sub` even though the method was defined on `Tools`. Alternative constructors work because of that one argument.

`Tools().cm` binds to the class too, not the instance. The C takes `type` when it has one and falls back to `Py_TYPE(obj)` when it does not, so calling a classmethod through an instance still gives you the class.

## property is the one with a setter

`property` is the longest of the four and still not long. Its `__get__` is {cite("Objects/descrobject.c:1685-1718@v3.15.0rc1#property_descr_get")}, and most of those lines are the error message for a property with no getter. The working part is two lines: return `self` when there is no instance, otherwise call the getter with the instance as its only argument.

What makes it different from the other three is `property_descr_set`, {cite("Objects/descrobject.c:1720-1755@v3.15.0rc1#property_descr_set")}. Having that filled in is what makes `property` a data descriptor, and it is the only reason a property cannot be shadowed by an instance attribute.
""")


lesson.code("""
class Config:
    def __init__(self):
        self._value = 1

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new):
        self._value = new

    def __repr__(self):
        return "a Config"


c = Config()
prop = Config.__dict__["value"]
print(f"  Config.__dict__['value'] is a {type(prop).__name__}")
print(f"  and it has __set__            {hasattr(prop, '__set__')}")
c.value = 5
print(f"  c.value     {c.value}")
print(f"  c.__dict__  {c.__dict__}")

c.__dict__["value"] = "a direct write into the instance dict"
print(f"  after writing straight into the dict, c.value is still {c.value}")
""")


lesson.md("""
The last two lines are worth sitting with. The instance dict genuinely has a `value` key in it now. Nothing raised, nothing cleaned it up, and the attribute still reads `5`. Attribute lookup checked the type first, found a data descriptor, and never looked at the dict at all. The key is just sitting there being ignored.

That is the same rule from O05, seen from the other side.

The error path is worth a look too, since the message tells you exactly which of the three functions was missing.
""")


lesson.code("""
class ReadOnly:
    @property
    def frozen(self):
        return 1


target = ReadOnly()
attempts = [
    ("assign", lambda: setattr(target, "frozen", 2)),
    ("delete", lambda: delattr(target, "frozen")),
]
for label, action in attempts:
    try:
        action()
    except AttributeError as error:
        print(f"  {label}  {error}")
""")


lesson.md(f"""
Both go through `property_descr_set`. It picks `prop_del` when the value is `NULL` and `prop_set` otherwise, finds neither is set, and formats a message naming the property and the class. The property learned its own name from `__set_name__`, which is the same mechanism `Logged` used at the top.

## The descriptors C code builds

C code cannot write a class body. When an extension type declares its attributes it fills in tables of C structs, and CPython turns those into descriptor objects when the type is created. There are five of them and you have been using them all along.

{figure("the-c-side", "the five descriptor types C code produces, and which are data descriptors")}

{lesson.claim("attributes defined from C appear as one of five descriptor types, and whether each is a data descriptor is decided by whether its type fills in tp_descr_set")}
""")


lesson.code("""
class Slotted:
    __slots__ = ("count",)


rows = [
    ("a __slots__ entry", Slotted.__dict__["count"]),
    ("int.numerator", int.__dict__["numerator"]),
    ("str.join", str.__dict__["join"]),
    ("int.__add__", int.__dict__["__add__"]),
    ("dict.fromkeys", dict.__dict__["fromkeys"]),
]
for label, descr in rows:
    kind = type(descr).__name__
    data = "data" if hasattr(descr, "__set__") else "non data"
    print(f"  {label:18} {kind:23} {data}")
""")


lesson.md(f"""
Five types, one protocol. `member_descriptor` reads a field at a fixed byte offset in the object, {cite("Objects/descrobject.c:163-181@v3.15.0rc1#member_get")}, which is what every `__slots__` entry is and what O03 was really describing. `getset_descriptor` calls a C getter function, {cite("Objects/descrobject.c:183-201@v3.15.0rc1#getset_get")}. `method_descriptor` binds a C function to the instance, {cite("Objects/descrobject.c:137-160@v3.15.0rc1#method_get")}, the C equivalent of `func_descr_get`. `wrapper_descriptor` wraps a slot function so you can call it from Python, {cite("Objects/descrobject.c:203-214@v3.15.0rc1#wrapperdescr_get")}. `classmethod_descriptor` is the C version of `classmethod`, {cite("Objects/descrobject.c:94-130@v3.15.0rc1#classmethod_get")}.

The two data descriptors in that list, `member_descriptor` and `getset_descriptor`, fill in `tp_descr_set`, {cite("Objects/descrobject.c:794-828@v3.15.0rc1#PyMemberDescr_Type")}. The other three leave it at zero and are non data descriptors, which is exactly why you can assign over `str.join` on a subclass and cannot assign over a slot.

These are the descriptors that carry the type check people run into. A Python descriptor gets whatever instance it is handed. A C one checks first, {cite("Objects/descrobject.c:216-240@v3.15.0rc1#descr_setcheck")}, because writing an `int` field at a fixed offset in an object that is not an `int` would corrupt memory.
""")


lesson.code("""
try:
    Slotted.__dict__["count"].__set__("not a Slotted at all", 1)
except TypeError as error:
    print(f"  {error}")
""")


lesson.md(f"""
## It only counts on the type

One rule that catches people. The protocol is only consulted for objects found on the type. Put a descriptor in an instance dict and it is an ordinary value.

{lesson.claim("a descriptor placed in an instance dict is returned as itself, because the lookup that would call __get__ only runs for objects found on the type")}
""")


lesson.code("""
class Sneaky:
    def __get__(self, obj, owner):
        return "the descriptor fired"


class Plain:
    pass


holder = Plain()
holder.from_the_instance = Sneaky()
Plain.from_the_class = Sneaky()

print(f"  holder.from_the_instance  {type(holder.from_the_instance).__name__}")
print(f"  holder.from_the_class     {holder.from_the_class}")
print(f"  Plain.from_the_class      {Plain.from_the_class}")
""")


lesson.md(f"""
Look back at O05's four steps and the reason is obvious. The instance dict branch reads the value and returns it, {cite("Objects/object.c:1887-1926@v3.15.0rc1#_PyObject_GenericGetAttrWithDict")}. Only the MRO branch checks for `__get__`.

That is not an oversight. If the instance dict were checked too, storing a function on an instance would silently turn it into a method, and every dict value would have to be tested for a descriptor slot before being handed back.

## How a descriptor learns its own name

Back to the loose end. `Logged` printed the attribute it was assigned to without being told, because `type` calls `__set_name__` on every value in the class dict on the way to building the class.

{figure("set-name-timing", "when __set_name__ runs during class creation")}

The function is `type_new_set_names`, {cite("Objects/typeobject.c:12274-12308@v3.15.0rc1#type_new_set_names")}. It copies the class dict, walks the copy, looks up `__set_name__` on each value, and calls it with the class and the key. The copy matters. It is why a descriptor can add more attributes to the class from inside `__set_name__` without the loop tripping over them.

{lesson.claim("__set_name__ runs once for every entry in the class dict during class creation, and never runs again for later assignments to the class")}
""")


lesson.code("""
print("  about to run the class statement")


class Watched:
    first = Logged()
    second = Logged()


print("  class statement finished, and both had already run")

Watched.third = Logged()
print("  assigning a descriptor to the class afterwards printed nothing")
print(f"  so Watched.__dict__['third'] has no name: {hasattr(Watched.__dict__['third'], 'name')}")
""")


lesson.md("""
The last line is the trap. Adding a descriptor to a class after the class statement gets you a descriptor that never learned its name, and it will fail the first time something reads it. Decorators that rewrite classes have to call `__set_name__` themselves, and `dataclasses` is one of the places in the standard library that does.

Errors get a note rather than being swallowed. If `__set_name__` raises, the class statement fails and the message tells you which descriptor and which attribute.
""")


lesson.code("""
class Fussy:
    def __set_name__(self, owner, name):
        raise ValueError("this name will not do")


try:

    class Doomed:
        field = Fussy()

except ValueError as error:
    print(f"  the error   {error}")
    for note in error.__notes__:
        print(f"  the note    {note}")
""")


lesson.md("""
## Try it yourself

Three things to poke at.

Write a caching descriptor. `__get__` computes a value, writes it into `obj.__dict__` under its own name, and returns it. Leave `__set__` off. The second read never reaches the descriptor at all, because a non data descriptor loses to the instance dict, and you get caching for free with no cache lookup. Then add an empty `__set__` and watch the caching stop working.

Take `property` apart and put it back together in Python. A class holding three functions, a `__get__` that calls the first, a `__set__` that calls the second or third, and a `__set_name__` that remembers the name for the error messages. Under twenty lines, and it will behave the same as the real one for everything in this notebook.

Find the descriptors on a type you use. `[n for n, v in vars(dict).items() if hasattr(type(v), "__get__")]` will list them, and the interesting part is how few things on a type are not descriptors.

## What just happened

A descriptor is any object in a class dict whose type has `__get__`, `__set__` or `__delete__`. There is nothing to inherit from and nothing to register. Reading such an attribute calls `__get__` instead of returning the object.

Whether it also has `__set__` or `__delete__` decides everything about precedence. The check is one line of C that asks whether `tp_descr_set` is non null. With it, the descriptor beats the instance dict and cannot be shadowed. Without it, the instance dict wins.

Functions are descriptors, which is where `self` comes from. `func_descr_get` is seven lines and hands back either the function or a new two pointer object holding the function and the instance. `staticmethod` is six lines that hand the callable back unchanged. `classmethod` is eight that bind to the class the lookup started from, which is what makes alternative constructors inherit properly. `property` is the long one at about thirty lines, and the extra length is error messages.

C code builds five descriptor types because it cannot write a class body. Two of them, the ones behind `__slots__` and behind read only attributes like `int.numerator`, are data descriptors. Those two also type check their instance before touching memory.

The protocol only applies to objects found on the type. In an instance dict a descriptor is just a value.

`__set_name__` runs once during class creation, over a copy of the class dict, and never runs again. A descriptor assigned to a class afterwards never learns its name.

## What is next

O07 is the dict. Every lesson so far has said "look in the instance dict" or "look in the class dict" as if that were a single simple step, and it is the most tuned data structure in the interpreter. It is a hash table with open addressing, it keeps insertion order without spending anything on it, and it has two completely different memory layouts depending on how it was made. O08 is about the second of those layouts, which is the one that makes ordinary objects small.
""")


raise SystemExit(lesson.save())
