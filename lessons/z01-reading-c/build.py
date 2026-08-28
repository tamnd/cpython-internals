#!/usr/bin/env python
"""Z01. C for people who will only ever read C.

The first of the two orientation lessons, and it sits in front of T01. Every other lesson
in this repository points at CPython's source. This one is about being able to click one
of those links and get something out of it.

It is built around a single nine line function, `list_append_impl` in
`Objects/listobject.c`, and everything else in the lesson is reached by following what
that function calls. Nothing here asks the reader to write C, install a compiler, or set
up a debugger.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of
them. `just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import Lesson
from nbdiagram import Diagrams

lesson = Lesson("z01-reading-c", "z01")
badge = lesson.badge
cite = lesson.cite
figure = Diagrams("z01-reading-c").figure

lesson.md(f"""
# Z01. C for people who will only ever read C

{badge}

Every lesson in this material points at CPython's own source, and CPython is written in C. If you have never read C, those links are a wall. This lesson takes the wall down.

{figure("where-we-are", "the eight stages of the pipeline with none of them highlighted")}

You are not going to learn C here. You are going to learn to read one specific dialect of it, the one CPython is written in, well enough to follow a function and know when you have understood it. That is a much smaller job, and it takes about an hour.

We are going to do the whole thing through one function: `list.append`. It is nine lines long, it calls two other things, and between them they use almost every idiom you will meet anywhere else in the codebase.

By the end you will be able to read a struct, follow a pointer, tell a new reference from a borrowed one, know what a macro is hiding, and recognise the `goto error` pattern that at first glance looks like terrible code and is in fact the correct answer.
""")


lesson.md("""
## About the source references

This lesson points at CPython's own source, like this: `Objects/listobject.c:1231-1239@v3.15.0rc1#list_append_impl`.

Read it as four parts: the file, the lines, the release those line numbers belong to, and the name of the thing they are inside.

Every reference is a link, and every one is checked against the pinned source on each change, so a stale reference fails the build instead of sending you somewhere wrong. Unlike every other lesson, here you really should click a few of them, because the point of the hour is to make that a thing you are willing to do.

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


lesson.code("""
import pyxray

pyxray.show()
""")


lesson.md(f"""
## A pointer is an arrow

If there is one thing that stops people reading C, it is the star. `PyObject *v`. `PyObject **items`. It looks like punctuation soup and it is actually very simple.

A pointer is a variable that holds an address instead of a value. That is the whole idea. When you see a star in a type, read it as "an arrow to", and read it from right to left. `PyObject *v` is "v is an arrow to a PyObject". `PyObject **items` is "items is an arrow to an arrow to a PyObject", which in practice means "items is an array of arrows".

Here is a Python list with two things in it, drawn as it actually sits in memory.

{figure("pointers-are-arrows", "a name pointing at a list struct, which points at a slot array, whose slots point at two strings")}

Three separate blocks of memory. The name in your program holds an address. The struct at that address holds five fields, one of which is another address. The array at that address holds addresses of the actual objects.

This is why `values[0]` is fast and why a list of a million things does not have to be a million things sitting next to each other. The list holds arrows, not objects.
""")


lesson.md(f"""
## A struct is a fixed layout

The second thing that stops people is the struct. It is even simpler than the pointer. A struct is a list of fields with fixed sizes, laid out one after another in memory, and it never changes shape at run time.

Here is the whole of a Python list, from {cite("Include/cpython/listobject.h:5-22@v3.15.0rc1#PyListObject")}:

```c
typedef struct {{
    PyObject_VAR_HEAD
    /* Vector of pointers to list elements.  list[0] is ob_item[0], etc. */
    PyObject **ob_item;

    /* ob_item contains space for 'allocated' elements.  The number
     * currently in use is ob_size.
     * Invariants:
     *     0 <= ob_size <= allocated
     *     len(list) == ob_size
     *     ob_item == NULL implies ob_size == allocated == 0
     * ...
     */
    Py_ssize_t allocated;
}} PyListObject;
```

Two fields, plus whatever `PyObject_VAR_HEAD` brings. That macro expands to three more fields, which T08 covered: the reference count, the type pointer, and the size. So a list is five fields and nothing else.

{figure("the-struct", "a table of the five fields of a list, their C types, and what each one is for")}

Read `Py_ssize_t` as "an integer big enough to index memory", which is 64 bits on any machine you own. Read `PyObject **ob_item` as "an arrow to an array of arrows", which is the slot array in the picture above.

The two comments in that struct are worth more than the code. Somebody wrote down the invariants, in the header, next to the fields they constrain. `0 <= ob_size <= allocated` is the entire contract of the list implementation in eleven characters. CPython's source is full of comments like this and they are usually the fastest way to understand a file.
""")


lesson.md(f"""
## Nine lines of C

Here is `list.append`, all of it, from {cite("Objects/listobject.c:1231-1239@v3.15.0rc1#list_append_impl")}:

```c
static PyObject *
list_append_impl(PyListObject *self, PyObject *object)
{{
    if (_PyList_AppendTakeRef(self, Py_NewRef(object)) < 0) {{
        return NULL;
    }}
    Py_RETURN_NONE;
}}
```

Line by line.

`static` means this function is private to this one file. Nothing outside `listobject.c` can call it. When you are searching for callers of something and it is `static`, you only have to search one file, which is a genuinely useful thing to notice.

`PyObject *` is the return type: an arrow to some Python value. Every function in CPython that is callable from Python returns one of these, because at that boundary nothing knows what type anything is.

`list_append_impl` has that `_impl` suffix because the argument parsing is generated by a tool called Argument Clinic. The generated wrapper unpacks the arguments and then calls this. When you go looking for a method's implementation, the `_impl` version is the one with the actual code in it.

`PyListObject *self` and `PyObject *object` are the two arguments. `self` is the list, and the type is specific because the caller already checked. `object` is the thing being appended, and the type is not specific because it can be anything.

`Py_NewRef(object)` hands back `object` and counts one more holder for it. This is the list taking ownership. Without it, the list would be holding an arrow to something that could be freed while the list still points at it.

`< 0` is the error check. Almost every CPython function that returns an `int` returns 0 for success and -1 for failure, so `if (something < 0)` reads as "if that failed".

`return NULL;` is how a function that returns a pointer says it failed. It does not return an error code, because there is nowhere to put one. The actual exception was already set by whatever went wrong further down.

`Py_RETURN_NONE;` is a macro that returns `None`. It exists because returning `None` used to need two lines and everybody got it wrong, so somebody wrapped it up.

That is the whole function. Nine lines, and you now know what all nine do.
""")


lesson.md(f"""
## Seven things you will see on every page

{figure("seven-idioms", "a table of seven CPython C idioms and how to read each one")}

Those seven cover most of what makes CPython's C look foreign to somebody arriving from Python. None of them are C language features you need to study. They are house style.

The leading underscore convention is worth one extra sentence, because it appears everywhere and the rule is simple. A name starting with `_Py` or `_PY` is private to CPython and can change in any release without notice. A name starting with `Py` with no underscore is public API and comes with a compatibility promise. When you see `_PyList_AppendTakeRef`, the underscore is telling you not to build anything on it.
""")


lesson.md(f"""
## New, borrowed, and stolen

This is the one part of CPython's C that has no equivalent in Python, and it is where all the real difficulty lives.

Every function that hands you a `PyObject *` does one of three things, and which one is written down only in prose.

{figure("new-or-borrowed", "a table of five calls and whether each returns a new, borrowed or stolen reference")}

A **new reference** means the count was increased on your behalf, and you owe a `Py_DECREF` before you drop the pointer. Forget it and the object leaks.

A **borrowed reference** means you got the pointer with no count increase. It is valid only as long as whatever you got it from keeps holding it. `PyList_GET_ITEM` is borrowed, which is why C code that reads an item out of a list and then calls back into Python has to take its own reference first, because the callback could clear the list from under it.

A **stolen reference** means the function took over a reference you were holding. `PyList_SET_ITEM` steals, which is why `list_append_impl` calls `Py_NewRef` before handing the object over: it is creating a reference specifically so there is one to give away.

You can watch the whole handover from Python. `list.pop` in C returns a new reference by giving you the one the list was holding, rather than by making a fresh one.
""")


lesson.code("""
from pyxray import obj


class Thing:
    \"\"\"Something whose reference count we can watch without the type interning it.\"\"\"


def ownership():
    \"\"\"Where the reference goes when a list takes an object and then gives it back.\"\"\"
    thing = Thing()
    print("just built, one name holds it      ", obj.refcount(thing))

    values = []
    values.append(thing)
    print("append took a reference of its own ", obj.refcount(thing))

    taken = values.pop()
    print("pop handed that same one to taken  ", obj.refcount(thing))
    print("and the list is empty now          ", values)
    print("and taken is the object itself     ", taken is thing)


ownership()
""")


lesson.md(f"""
The number after `pop` is 2 and not 3, and that is the whole point. The list did not make a new reference for you and then throw its own away. It handed you the one it was holding, which is what "returns a new reference" means from the caller's side.

You can see it in the source. Here is the end of {cite("Objects/listobject.c:1585-1617@v3.15.0rc1#list_pop_impl")}:

```c
    PyObject **items = self->ob_item;
    v = items[index];
    if (Py_SIZE(self) == 1) {{
        Py_INCREF(v);
        list_clear(self);
        return v;
    }}
```

`v = items[index]` reads an arrow out of the slot array. That is a borrowed reference at that moment, because nothing has been counted. Then `return v` at the bottom hands it to the caller as a new one, because the list is about to shrink and give up its own. The `Py_INCREF` in the middle is only there for the one item case, where `list_clear` would drop the count before the return could use it.

That is a real ownership bug waiting in three lines of code, and the way it was avoided is one extra increment in the branch that needed it. This is what people mean when they say reference counting is easy to get subtly wrong.
""")


lesson.md(f"""
## A macro is text substitution

{figure("macros-are-text", "four macros on the left and what the compiler actually sees on the right")}

Before the C compiler sees the file, a separate program called the preprocessor goes through it and replaces every macro with its definition, as text. That is all a macro is. No types, no scope, no address, no function call.

Here is `Py_RETURN_NONE`, from {cite("Include/object.h:623-629@v3.15.0rc1#Py_RETURN_NONE")}:

```c
/* Macro for returning Py_None from a function.
 * Only treat Py_None as immortal in the limited C API 3.12 and newer. */
#if defined(Py_LIMITED_API) && Py_LIMITED_API+0 < 0x030c0000
#  define Py_RETURN_NONE return Py_NewRef(Py_None)
#else
#  define Py_RETURN_NONE return Py_None
#endif
```

Two things to take from that.

The `#if` and `#else` are the preprocessor choosing which definition to use, before compilation. This is `#ifdef`, and CPython uses it heavily: for the free threaded build, for debug builds, for platform differences. When you are reading a file and a block looks like it contradicts another block a few lines up, check whether there is an `#ifdef` between them.

The two definitions are different for a real reason. `None` became immortal in 3.12, so on a modern build returning it costs nothing at all. On an older limited API build it still needs the count bumped. The macro hides the difference, which is exactly what macros are for.

The practical consequence of macros being text is that your editor's "go to definition" often fails on them, and a debugger will step straight through them as if they were not there. When you cannot find where something is defined, `grep` for `#define` and the name. Nothing else will find it.

`Py_NewRef` from the append function is the same idea, at {cite("Include/refcount.h:527-538@v3.15.0rc1#Py_NewRef")}, except it is a `static inline` function rather than a macro, which is the modern preference because it has types and does not evaluate its argument twice.
""")


lesson.md(f"""
## Following the call

`list_append_impl` calls one thing that does work, so let us follow it. Here is what the append actually does.

{figure("the-append-path", "the five steps from values.append(x) down to writing into a slot")}

`_PyList_AppendTakeRef` is at {cite("Include/internal/pycore_list.h:36-54@v3.15.0rc1#_PyList_AppendTakeRef")}, and the interesting half is this:

```c
    Py_ssize_t len = Py_SIZE(self);
    Py_ssize_t allocated = self->allocated;
    assert((size_t)len + 1 < PY_SSIZE_T_MAX);
    if (allocated > len) {{
        PyList_SET_ITEM(self, len, newitem);
        Py_SET_SIZE(self, len + 1);
        return 0;
    }}
    return _PyList_AppendTakeRefListResize(self, newitem);
```

Read it out loud. How many slots are in use. How many slots exist. If there is a spare one, write into it, add one to the size, done. Otherwise go and get more room.

Three things worth noticing about how that is written.

`self->allocated` is the arrow operator, and it is just `.` for a pointer. `self` is an arrow to a struct, so `self->allocated` means "follow the arrow and read the `allocated` field". You will see it thousands of times.

`assert` disappears entirely in a release build. It is documentation that gets checked in debug builds and costs nothing in the one you are running. When you see an assert, read it as the author telling you something they believe is always true.

`TakeRef` in the name is the ownership contract, in the name. This function steals the reference you hand it, which is why the caller wrote `Py_NewRef(object)` rather than just `object`. Whoever named it saved a paragraph of documentation.
""")


lesson.md(f"""
## The arithmetic you can check

The other branch is the interesting one, because it contains a piece of arithmetic you can verify from Python without any of this being visible.

When the list is full, it calls `list_resize`, at {cite("Objects/listobject.c:103-134@v3.15.0rc1#list_resize")}. The heart of it is one line, with a comment above it that tells you the answer:

```c
    /* This over-allocates proportional to the list size, making room
     * for additional growth.  The over-allocation is mild, but is
     * enough to give linear-time amortized behavior over a long
     * sequence of appends() in the presence of a poorly-performing
     * system realloc().
     * Add padding to make the allocated size multiple of 4.
     * The growth pattern is:  0, 4, 8, 16, 24, 32, 40, 52, 64, 76, ...
     */
    new_allocated = ((size_t)newsize + (newsize >> 3) + 6) & ~(size_t)3;
```

`newsize >> 3` is "divide by eight", because shifting right by three bits is dividing by two three times. `& ~(size_t)3` is "round down to a multiple of four", because it clears the bottom two bits. So the whole line is "one eighth more than you asked for, plus six, rounded down to a multiple of four".

{figure("growing", "a bar chart of how many slots a list has after each of its first ten resizes")}

That is a claim about behaviour, so let us check it rather than believe it. The next cell transcribes `list_resize` into Python, line for line, and runs it against a real list two thousand times.
""")


lesson.code("""
import struct
import sys

EMPTY = sys.getsizeof([])
POINTER = struct.calcsize("P")


def measured(values):
    \"\"\"How many slots the list really has, read out of the bytes it occupies.\"\"\"
    return (sys.getsizeof(values) - EMPTY) // POINTER


def predicted(length, allocated):
    \"\"\"`list_resize` from `Objects/listobject.c`, transcribed one line at a time.\"\"\"
    newsize = length + 1
    if allocated > length:
        return allocated
    if allocated >= newsize >= allocated >> 1:
        return allocated
    new_allocated = (newsize + (newsize >> 3) + 6) & ~3
    if newsize - length > new_allocated - newsize:
        new_allocated = (newsize + 3) & ~3
    return 0 if newsize == 0 else new_allocated


values = []
allocated = 0
wrong = 0
pattern = []
for length in range(2000):
    allocated = predicted(length, allocated)
    values.append(length)
    if measured(values) != allocated:
        wrong += 1
    if allocated not in pattern:
        pattern.append(allocated)

print("appends checked:", len(values))
print("disagreements:  ", wrong)
print("growth pattern: ", pattern[:10])
""")


lesson.md("""
Zero disagreements over two thousand appends, and the growth pattern the cell measured is the same list the C comment wrote down: 4, 8, 16, 24, 32, 40, 52, 64, 76, 92.

You just read a line of C, worked out what it does from first principles, reimplemented it in a language it was not written in, and confirmed the reimplementation against a running interpreter two thousand times. That is the whole method of this project in one cell, and you did it in an hour without a compiler.

It also answers a question you may have had for years. Appending a million items to a list does not do a million reallocations. It does about eighty, because each one buys roughly an eighth more room than the last. That is what "amortized constant time" means, and it is nine words of C.
""")


lesson.md(f"""
## goto, which is fine here

The last idiom is the one that looks worst and is the most defensible.

C has no `try` and no `finally`. If a function acquires three things and the fourth step fails, somebody has to release those three things, and doing it at every failure point means writing the same cleanup three times and getting it wrong once.

The answer CPython uses is a single cleanup block at the bottom and a `goto` to reach it. Here is the shape, from {cite("Objects/listobject.c:580-599@v3.15.0rc1#list_repr_impl")}:

```c
    PyUnicodeWriter *writer = PyUnicodeWriter_Create(prealloc);
    PyObject *item = NULL;
    if (writer == NULL) {{
        goto error;
    }}

    if (PyUnicodeWriter_WriteChar(writer, '[') < 0) {{
        goto error;
    }}
```

and about thirty lines later, after four more `goto error` jumps:

```c
error:
    Py_XDECREF(item);
    PyUnicodeWriter_Discard(writer);
    Py_ReprLeave((PyObject *)v);
    return NULL;
```

Every failure path goes to the same six lines. `item` is set to `NULL` up front so the cleanup can run even when the failure happened before `item` was ever used, and `Py_XDECREF` is the version that tolerates `NULL`.

When you see `goto error` in CPython, this is always what is happening. It is `finally`, spelled the only way C lets you spell it.
""")


lesson.md(f"""
## Where to look, once you can read it

{figure("what-to-reach-for", "a table of six questions and where in the tree the answer lives")}

Reading C turns out not to be the hard part of reading CPython. Knowing which of two million lines to open is, and Z02 is entirely about that.

One habit is worth starting today. When a line of C confuses you, run `git log -S` on it in a CPython checkout. That finds the commit that introduced that exact text, and the commit message usually links an issue, and the issue usually has somebody explaining why the obvious approach did not work. A surprising amount of CPython is the way it is for a reason somebody wrote down.
""")


lesson.md("""
## Try it yourself

**One.** Open `Objects/listobject.c` and find `list_insert_impl`. It is about the same size as append. Read it and write down, in one sentence each, what every line does. Then check whether it takes a new reference and where.

**Two.** The growth cell above starts from an empty list. Change it to start from `list(range(1000))` and see whether the prediction still holds. If it does not, work out which branch of `list_resize` you are now hitting that you were not before.

**Three.** Find three functions in `Objects/listobject.c` that return `int` and three that return `PyObject *`. Work out the failure value for each group without looking it up.

**Four.** `Py_CLEAR(item)` appears in the repr function above. Find its definition, work out why it is a multi line macro rather than just `Py_DECREF(item); item = NULL;`, and then find the comment in the source that explains it. The reason involves the object's own destructor.

**Five.** Pick any method on `list` you use often and find its `_impl` function. Read it. Most of them are under thirty lines and several are under ten.
""")


lesson.md("""
## What just happened

You read C, without writing any.

A pointer is a variable holding an address, and a star in a type means "an arrow to". A struct is a fixed set of fields laid out one after another, and a Python list is five of them. Following one arrow at a time is all that reading this code requires.

CPython's C has about seven house style idioms on top of the language. `static` for file local. `PyObject *` at every boundary. `NULL` and negative numbers as failure. `goto error` for cleanup. A leading underscore for private. `_impl` for the real body of a method. Names that state their own ownership contract, like `TakeRef`.

Reference ownership is the part with no Python equivalent and no compiler help. New, borrowed, or stolen, and only the documentation says which.

Macros are text substitution performed before compilation, which is why your tools lose them and why `grep` for `#define` is how you find them.

And nine lines of C, followed two calls deep, ended in one line of arithmetic that you were able to reimplement in Python and confirm against a running interpreter two thousand times over.

## Where this goes next

Z02 is the other half of the orientation. Reading a function is one skill and finding the right function is another, and the second one is what actually stops people in a tree this size. It covers the directory map, which files are generated and must never be read as source, and how to use the commit history to answer "why is this line here".

After that, T01 starts the pipeline, and the source references in it will be worth clicking.
""")


raise SystemExit(lesson.save())
