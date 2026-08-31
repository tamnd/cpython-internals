#!/usr/bin/env python
"""O04. The order things are found in.

The fourth lesson of the object model part. O03 explained which dictionary a name is found in.
This one explains the order those dictionaries get looked at, which is the only interesting
question once a class has more than one base.

The answer is a list, computed once when the class is made and stored on the type. It is not a
search. There is a forty line function called `pmerge` that builds it, and the whole of multiple
inheritance in Python is that function plus the fact that `super` reads the list of the instance
rather than the list of the class it appears in.

The lesson writes the merge out in Python, checks it against `__mro__` for a pile of classes
including some from the standard library, and then shows the two ways it can fail.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams

lesson = Lesson("o04-the-order-things-are-found-in", "o04")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("o04-the-order-things-are-found-in").figure


lesson.md(f"""
# O04. The order things are found in

{badge}

O03 said a slot dispatcher looks a dunder name up on the type, and that a class inherits slots from its base. With one base that is easy to picture. Go up one link, look in that dict, keep going until you run out.

With two bases there is no obvious next link.

{figure("the-diamond", "the four classes, and the two paths from D up to A")}

D inherits from B and from C, and both of those inherit from A. A defines `where`, C also defines `where`, B does not. So `D().where()` has two paths up the tree and they disagree.

Python does not search. It computes one flat list per class, once, and reads it front to back. This lesson is about how that list gets built, why it sometimes cannot be built at all, and why `super` is not what people assume.
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Objects/typeobject.c:3361-3400@v3.15.0rc1#pmerge`.

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
## Two bases and one question

Here is the diamond as code. B and C both inherit from A, D inherits from both, and A and C each define a `where` method.

The list D actually uses is on the type, under `__mro__`. It is a tuple of classes, it is computed when the class statement runs, and it is what the interpreter reads. `__bases__` is what you declared. `__mro__` is what that turned into.

{lesson.claim("a class with two bases carries a flat __mro__ tuple that flattens both paths into one order, and method lookup follows that order rather than searching the base classes")}
""")


lesson.code(
    """
class A:
    def where(self):
        return "A"


class B(A):
    pass


class C(A):
    def where(self):
        return "C"


class D(B, C):
    pass


print(f"  D.__bases__  {[c.__name__ for c in D.__bases__]}")
print(f"  D.__mro__    {[c.__name__ for c in D.__mro__]}")
print(f"  D().where()  {D().where()}")
"""
)


lesson.md(f"""
The answer is C, and A is last, even though A is where `where` was defined first and B is the base you wrote first.

The order you write the bases in is not decoration. It is a constraint the list has to satisfy, and swapping the two bases gives you a different list and a different method.

{lesson.claim("swapping the order of the declared bases changes the resulting MRO, so the bases tuple is an input to the computation and not just a record of what you typed")}
""")


lesson.code(
    """
class BC(B, C):
    pass


class CB(C, B):
    pass


print(f"  class BC(B, C)   {[c.__name__ for c in BC.__mro__]}")
print(f"  class CB(C, B)   {[c.__name__ for c in CB.__mro__]}")
"""
)


lesson.md(f"""
## The rules the order has to obey

The {term("MRO")} is not picked out of a hat. Three things have to hold, and they hold for every class in the list rather than only for the one you asked about.

{figure("three-rules", "the three constraints every MRO has to satisfy")}

First, a class comes before all of its bases. Second, the bases stay in the order they were declared. Third, both of those apply to every entry in the list, which is the part that makes the whole thing hard, because a constraint that B introduces can rule out an order that looked fine from D.

There is one more thing that always holds and that nobody has to enforce, because it falls out of the first two: `object` is last. Every class ends up with it somewhere in its bases, and nothing comes after it.

{lesson.claim("every class's MRO starts with the class itself, ends with object, and lists each declared base in the order it was declared")}
""")


lesson.code(
    """
import collections
import io

for cls in [D, BC, int, io.StringIO, collections.OrderedDict]:
    mro = cls.__mro__
    positions = [mro.index(b) for b in cls.__bases__]
    print(
        f"  {cls.__name__:13} first is {mro[0].__name__ == cls.__name__!s:5}"
        f"  last is {mro[-1].__name__:9}"
        f"  bases at {positions}, in order {positions == sorted(positions)}"
    )
"""
)


lesson.md(f"""
## Doing the merge by hand

The algorithm has a name, {term("C3 linearization")}, and a paper behind it, but the code is short enough to fit on a screen. In CPython it is `pmerge`, {cite("Objects/typeobject.c:3361-3400@v3.15.0rc1#pmerge")}.

{figure("merging-the-lists", "the merge picking one class at a time for the diamond")}

It takes several lists. For a class with bases B and C, the lists are B's MRO, C's MRO, and the declared bases tuple `(B, C)` on the end, {cite("Objects/typeobject.c:3480-3510@v3.15.0rc1#pmerge")}. Then it does one thing over and over: look at the front of each list, and take the first one that does not appear anywhere in the tail of any list.

That test is a helper of its own, `tail_contains`, {cite("Objects/typeobject.c:3246-3256@v3.15.0rc1#tail_contains")}, and it is the whole rule. If a class shows up later in some list, taking it now would put it in front of something that has to come first, so it waits.

When a class is taken it gets appended to the answer and every list that had it at the front moves along by one. Then the scan starts again from the top. If a full pass finds nothing to take and the lists are not all empty, the merge is stuck, and that is a different story further down.

Here it is in Python, next to the real thing. `c3` builds a class's order from its bases' orders the same way CPython does, and the assertion is what makes this worth reading: it matches `__mro__` exactly, for classes from this notebook and for classes from the standard library.

{lesson.claim("a twenty line C3 merge written in Python reproduces CPython's __mro__ exactly, for hand written diamonds and for classes taken from the standard library")}
""")


lesson.code(
    """
def merge(sequences):
    \"\"\"Take the first head that does not appear in any other list's tail.\"\"\"
    result = []
    sequences = [list(s) for s in sequences if s]
    while sequences:
        for sequence in sequences:
            head = sequence[0]
            if not any(head in s[1:] for s in sequences):
                break
        else:
            raise TypeError("no consistent order exists")
        result.append(head)
        for s in sequences:
            if s[0] is head:
                del s[0]
        sequences = [s for s in sequences if s]
    return result


def c3(cls):
    \"\"\"A class, then the merge of its bases' orders and the bases tuple itself.\"\"\"
    lists = [c3(base) for base in cls.__bases__]
    lists.append(list(cls.__bases__))
    return [cls, *merge(lists)]


checked = [D, BC, CB, B, C, A, bool, io.StringIO, collections.OrderedDict, Exception, type]
for cls in checked:
    assert c3(cls) == list(cls.__mro__), cls.__name__

print(f"  matched __mro__ exactly for all {len(checked)} of them")
print(f"  c3(D)  {[c.__name__ for c in c3(D)]}")
"""
)


lesson.md(f"""
That is a real reimplementation of the interesting part, and it took twenty lines. The C version is longer mostly because it has to manage memory and because it keeps an index into each list instead of deleting from the front.

CPython also has a shortcut. If there is exactly one base there is nothing to merge, so it skips straight to putting the new class in front of the base's order, {cite("Objects/typeobject.c:3453-3473@v3.15.0rc1")}. Single inheritance never runs the merge at all, which is worth knowing when you are wondering what a class statement costs.

{lesson.claim("a chain of single inheritance produces an MRO that is just each class prepended to its base's MRO, which is the fast path CPython takes without running the merge")}
""")


lesson.code(
    """
chain = object
for level in range(5):
    chain = type(f"Link{level}", (chain,), {})

print(f"  {[c.__name__ for c in chain.__mro__]}")
print("  each step only put the new class in front of the one below it")
"""
)


lesson.md(f"""
## When there is no such order

Sometimes the constraints contradict each other and no list satisfies all of them. The merge notices, because a whole pass finds no candidate while lists still have things in them.

{figure("no-order-exists", "two classes that each make sense and one combination that cannot")}

`class XY(X, Y)` says X comes before Y. `class YX(Y, X)` says the opposite. Each is fine alone. A class inheriting from both would need both at once, so there is no order, and instead of quietly picking one CPython refuses to make the class.

The message comes from `set_mro_error`, {cite("Objects/typeobject.c:3309-3331@v3.15.0rc1#set_mro_error")}, which collects the classes sitting at the front of the stuck lists and names them. Those are the candidates that were competing, which is usually enough to see what you did.

There is a second, simpler failure checked before the merge even starts. Listing the same base twice is not a contradiction, it is just meaningless, and `check_duplicates` catches it first, {cite("Objects/typeobject.c:3270-3298@v3.15.0rc1#check_duplicates")}.

{lesson.claim("a pair of bases that order two classes in opposite ways makes the class statement itself raise TypeError, and a repeated base is rejected earlier by a separate check with a different message")}
""")


lesson.code(
    """
class X:
    pass


class Y:
    pass


class XY(X, Y):
    pass


class YX(Y, X):
    pass


try:

    class Impossible(XY, YX):
        pass

except TypeError as error:
    print(f"  class Impossible(XY, YX)   TypeError: {error}")

try:

    class Twice(X, X):
        pass

except TypeError as error:
    print(f"  class Twice(X, X)          TypeError: {error}")
"""
)


lesson.md(f"""
Notice which classes got named in the first message. Not `XY` and `YX`, which are the bases you wrote, but `X` and `Y`, which are the two the merge could not choose between.

## super does not mean the base class

This is the part of the MRO that has real consequences for code people write, and the usual mental model of it is wrong.

{figure("super-follows-the-instance", "super reading the instance's MRO rather than the class it was written in")}

`super()` inside a method of `Left` does not mean "Left's base class". It means "whatever comes after Left in the MRO of this instance". The lookup is `_PySuper_LookupDescr`, {cite("Objects/typeobject.c:12586-12614@v3.15.0rc1#_PySuper_LookupDescr")}, and the first thing it does is fetch the MRO of the object's type, not of the class the call was written in. Then it finds the class in that list and starts from the entry after it.

So the same line of code, in the same method, goes somewhere different depending on what you called it on. `Left` does not know `Right` exists, and cannot know, because `Right` may be written years later.

{lesson.claim("super in a method resolves against the MRO of the instance's type, so an unchanged method in Left can dispatch to Right when the instance is a Both, even though Left never refers to Right")}
""")


lesson.code(
    """
class Base:
    def who(self):
        return ["Base"]


class Left(Base):
    def who(self):
        return ["Left", *super().who()]


class Right(Base):
    def who(self):
        return ["Right", *super().who()]


class Both(Left, Right):
    def who(self):
        return ["Both", *super().who()]


print(f"  Left().who()  {Left().who()}")
print(f"  Both().who()  {Both().who()}")
print(f"  Both.__mro__  {[c.__name__ for c in Both.__mro__]}")
"""
)


lesson.md("""
The same `super().who()` inside `Left` returned `Base` for one instance and `Right` for the other. That is the whole of what people mean by cooperative multiple inheritance, and it is one list lookup.

It also explains the rule that everything in such a chain has to call `super()`. If `Left.who` returned early instead, `Right.who` would never run, because nothing else is walking the list. The list is only walked by the chain of `super` calls themselves.

## The list is not frozen

Two things can change it after the class exists.

Assigning to `__bases__` recomputes the MRO, and not just for that class. `mro_hierarchy_for_complete_type` walks every subclass and rebuilds each one, because their orders were derived from this one and are now wrong.
""")


lesson.md(f"""
{cite("Objects/typeobject.c:1798-1810@v3.15.0rc1#mro_hierarchy_for_complete_type")} is the function. Existing instances see the change immediately, since they hold a pointer to the type and the type holds the list.

{lesson.claim("assigning to a class's __bases__ recomputes the MRO of that class and of every subclass, and instances that already exist pick up the new method at once")}
""")


lesson.code(
    """
class Old:
    def tag(self):
        return "Old"


class New:
    def tag(self):
        return "New"


class Thing(Old):
    pass


class Sub(Thing):
    pass


existing = Sub()
print(f"  before   Sub().tag() {existing.tag()}   {[c.__name__ for c in Sub.__mro__]}")

Thing.__bases__ = (New,)

print(f"  after    Sub().tag() {existing.tag()}   {[c.__name__ for c in Sub.__mro__]}")
"""
)


lesson.md(f"""
The other way in is a metaclass. Making a class ready calls `mro_invoke`, {cite("Objects/typeobject.c:3590-3609@v3.15.0rc1#mro_invoke")}, which checks whether the metaclass is plain `type`. If it is not, it calls the metaclass's `mro()` method instead of running the merge, and whatever comes back is the list, subject to a sanity check.

So the C3 rules are the default, not the law. A metaclass can hand back any order it likes and the interpreter will use it.

There is a cost. `type_mro_modified` turns off the type version tag for a class with a custom `mro()`, {cite("Objects/typeobject.c:1278-1298@v3.15.0rc1#type_mro_modified")}, which takes it out of the method cache that makes normal attribute lookup fast.

{lesson.claim("a metaclass that overrides mro can return an order the C3 rules would never produce, and attribute lookup uses that order without complaint")}
""")


lesson.code(
    """
class Reversed(type):
    def mro(cls):
        return [cls, *reversed(type.mro(cls)[1:-1]), object]


class P:
    def tag(self):
        return "P"


class Q(P):
    def tag(self):
        return "Q"


class Odd(Q, metaclass=Reversed):
    pass


print(f"  Odd.__mro__  {[c.__name__ for c in Odd.__mro__]}")
print(f"  Odd().tag()  {Odd().tag()}")
print("  P comes before Q, which is backwards, and the lookup follows it anyway")
"""
)


lesson.md(f"""
## Where a lookup actually goes

Now the loop that uses all of this. It is `find_name_in_mro`, {cite("Objects/typeobject.c:6144-6180@v3.15.0rc1#find_name_in_mro")}, and it is about as simple as it sounds: take the type's MRO tuple, walk it front to back, do a dict lookup in each class's dict, and stop at the first hit.

{figure("where-a-lookup-goes", "one list, walked front to back, one dict lookup per entry")}

No tree walking, no backtracking, no work about inheritance at all. All of that happened once, when the class was created. This is the payoff for computing the list up front, and it is why `__mro__` exists as a stored tuple rather than as a method that figures it out each time.

O05 picks the loop apart properly, including the cache that usually means it does not run at all.
""")


lesson.md("""
## Try it yourself

Three things to poke at.

Print the MROs of a few classes with genuinely deep hierarchies and see how long they get. `collections.OrderedDict`, `io.TextIOWrapper` and any exception class are good starting points. Then run `c3` from this notebook on them and confirm it still matches.

Take the diamond and give B a `where` method too. The answer changes, and you can predict it from `D.__mro__` before you run it. Then change the declared order to `class D(C, B)` and predict again.

Build a class hierarchy where the merge fails and the error message names classes you did not write in the failing class statement. Three levels is enough. The message lists the stuck heads, which are often further up than the bases you were looking at, and getting a feel for that is what makes the error readable.

## What just happened

Every class carries a flat list of classes called its MRO, computed once when the class is made, stored on the type, and read front to back by every attribute lookup.

The list is built by a merge. Take the MRO of each base, add the declared bases tuple, and repeatedly take the first head that does not appear in any other list's tail. Twenty lines of Python reproduce it exactly, including for classes out of the standard library. Single inheritance skips the merge entirely and just prepends.

The rules the list satisfies are that a class comes before its bases, that declared order is preserved, and that both hold for every entry rather than only the first. Sometimes no list satisfies them, and then the class statement raises `TypeError` and names the classes the merge was stuck between. A repeated base is caught before the merge by a separate check.

`super()` reads the MRO of the instance, not of the class it was written in, which is why a method in one class can dispatch to a class it has never heard of and why every link in such a chain has to call `super()` for the chain to continue.

The list is not permanent. Assigning `__bases__` recomputes it for the class and everything under it, and a metaclass with its own `mro()` can hand back any order at all, at the cost of the method cache.

## What is next

O05 is attribute lookup, the loop that reads the list this lesson built. Getting `x.y` involves more than the MRO: there is the instance dict, there is `__getattr__` as a fallback, there is the type attribute cache that makes most lookups skip the walk completely, and there is the fact that looking a name up on a class and on an instance take genuinely different paths through the code.
""")


raise SystemExit(lesson.save())
