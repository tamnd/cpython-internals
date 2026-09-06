#!/usr/bin/env python
"""R09. Writing a C extension properly.

The last lesson of the runtime part, and the one that turns the book around. Everything up to
here watched CPython from Python. This one writes the C on the other side of the boundary and
finds out what the runtime expects from it.

Two small extension modules, compiled in the notebook where there is a compiler. The first is
one function written twice, differing by a single `Py_DECREF` on a branch that only runs on bad
input. The second is a container written three ways, one that never tells the collector it
exists, one that tells it and then lies about what it holds, and one that gets it right.

The two Tier 1 recordings are the parts a notebook cannot do. A debug build runs CPython's own
reference leak hunter over four tests that all pass an ordinary run, and a free threaded build
loads the same shared object three ways to show what one declaration at the bottom of the file
is worth.

Run this file to regenerate the notebook, or `just build-lessons` to regenerate all of them.
`just lessons` checks that the committed notebook still matches this file.
"""

from nbbuild import BANNER, Lesson
from nbdiagram import Diagrams
from tier1 import show as recording

lesson = Lesson("r09-writing-a-c-extension-properly", "r09")
badge = lesson.badge
cite = lesson.cite
term = lesson.term
figure = Diagrams("r09-writing-a-c-extension-properly").figure

ON_DEBUG = "r09-what-the-leak-hunter-catches"
ON_FREETHREADED = "r09-what-a-module-must-declare"


lesson.md(f"""
# R09. Writing a C extension properly

{badge}

Every lesson so far has watched CPython from the Python side. This one crosses over and writes the C, which is where all the rules you have been reading about stop being descriptions and start being your job.

There are only four of them, and none is hard. Hand back what you own and let go of what you borrowed. If your object can hold another object, tell the collector. Do your cleanup in the slot meant for it. Say honestly whether your code is safe without the lock. What makes them worth a lesson is that breaking any of the four produces no error, no warning and no crash. It produces a program that works, and slowly stops working, in a way that only a tool built for the purpose can see.

{figure("the-branch-nobody-tests", "two error paths side by side, one missing a single Py_DECREF")}
""")


lesson.md("""
## About the source references

Now and then this lesson points at CPython's own source, like this: `Python/gc.c:490-515@v3.15.0rc1`.

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

This lesson compiles C. Colab has a compiler and so does any machine with a working development setup, and a browser tab has neither a compiler nor the headers, so the cells check first and say so rather than failing. If you are reading this in a browser, everything below still reads, and the two recordings at the end are real output from real builds.

## Which interpreter is this
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
## The branch nobody tests

Start with the smallest of the four rules, because everything else is a version of it.

Every C API function that hands you an object hands you one of two things. A {term("new reference")} is yours, and you owe the runtime a `Py_DECREF` before you lose track of it. A {term("borrowed reference")} is not yours, and decrefing it is a bug of the other kind. The documentation says which for every function, and there is no way to tell by looking at the call.

Here is a function that gets it right on the path you test and wrong on the path you do not. It packs its argument into a tuple twice over and then hashes the tuple, which works for a number and fails for a list. `PyTuple_Pack` returns a new reference, and that tuple is holding two references to your argument. On the way out through the error the tuple is simply dropped.

{lesson.claim("Missing one Py_DECREF on an error branch costs two references per failed call, and nothing in the process complains")}
""")


lesson.code("""
import os
import subprocess
import sysconfig
import tempfile

ERRPATH = \"\"\"
#include <Python.h>

/* pair(x) hands back (x, x), but only if that tuple can be hashed. */

static PyObject *
leaky(PyObject *module, PyObject *arg)
{
    PyObject *pair = PyTuple_Pack(2, arg, arg);
    if (pair == NULL) {
        return NULL;
    }
    if (PyObject_Hash(pair) == -1) {
        return NULL;
    }
    return pair;
}

static PyObject *
careful(PyObject *module, PyObject *arg)
{
    PyObject *pair = PyTuple_Pack(2, arg, arg);
    if (pair == NULL) {
        return NULL;
    }
    if (PyObject_Hash(pair) == -1) {
        Py_DECREF(pair);
        return NULL;
    }
    return pair;
}

static PyMethodDef methods[] = {
    {"leaky", leaky, METH_O, "Build a pair, and get the error path wrong."},
    {"careful", careful, METH_O, "Build a pair, and get the error path right."},
    {NULL, NULL, 0, NULL},
};

static PyModuleDef_Slot slots[] = {
    {Py_mod_multiple_interpreters, Py_MOD_PER_INTERPRETER_GIL_SUPPORTED},
    {Py_mod_gil, Py_MOD_GIL_NOT_USED},
    {0, NULL},
};

static struct PyModuleDef errpath = {
    PyModuleDef_HEAD_INIT, "errpath", NULL, 0, methods, slots, NULL, NULL, NULL,
};

PyMODINIT_FUNC
PyInit_errpath(void)
{
    return PyModuleDef_Init(&errpath);
}
\"\"\"

SUFFIX = sysconfig.get_config_var("EXT_SUFFIX") or ".so"
WORK = tempfile.mkdtemp()
sys.path.insert(0, WORK)
NOTHING = "  no compiler and headers here, so there is nothing to build"


def build(name, source):
    \"\"\"Compile one C file into something this interpreter can import. Empty means it worked.\"\"\"
    written = os.path.join(WORK, name + ".c")
    with open(written, "w") as handle:
        handle.write(source)
    line = [*(sysconfig.get_config_var("CC") or "cc").split(), "-shared", "-fPIC"]
    if sys.platform == "darwin":
        line += ["-undefined", "dynamic_lookup"]
    line += ["-I", sysconfig.get_path("include"), written]
    line += ["-o", os.path.join(WORK, name + SUFFIX)]
    try:
        done = subprocess.run(line, capture_output=True, text=True, timeout=300)
    except OSError:
        return "there is no C compiler on this runtime"
    return "" if done.returncode == 0 else done.stderr.strip().splitlines()[-1]


TROUBLE = build("errpath", ERRPATH)
HAVE_C = not TROUBLE
if not HAVE_C:
    print(NOTHING)
else:
    import errpath

    for name in ("leaky", "careful"):
        work = getattr(errpath, name)
        victim = []
        before = sys.getrefcount(victim)
        failed = 0
        for _ in range(1000):
            try:
                work(victim)
            except TypeError:
                failed += 1
        left = sys.getrefcount(victim) - before
        print(f"  {name:8} {failed} calls raised, and left {left} references behind")
""")


lesson.md(f"""
Two thousand references to a list nobody can reach any more, and the process is perfectly happy. It will stay happy until the machine runs out of memory, which on a web server handling bad input all day is a Tuesday.

The fix is one line, and the habit that produces it is worth more than the line. C has no `finally`, so CPython's own source uses a single exit: every function that owns something has one cleanup block at the bottom, and every failure jumps to it with `goto error`. Once a function has more than one owned object that is the only shape that stays correct, because the alternative is repeating the right sequence of decrefs at every `return NULL` and getting one of them wrong. `Py_CLEAR` {cite("Include/refcount.h:483-500@v3.15.0rc1#Py_CLEAR")} exists for the same reason: it sets the field to `NULL` before dropping the reference, so nothing can see a half freed pointer if the deallocation runs code that comes back around.

## A box the collector cannot see

Now the second rule, which needs a container to show.

The {term("cycle collector")} finds garbage that reference counting cannot: a group of objects pointing at each other with nothing pointing in from outside. It does that by asking every candidate what it is holding, subtracting those references from the counts, and seeing what is left {cite("Python/gc.c:490-515@v3.15.0rc1#subtract_refs")} {cite("Python/gc.c:438-465@v3.15.0rc1#visit_decref")}.

{figure("how-the-collector-uses-traverse", "four steps from counting references to deciding what is held from outside")}

Asking is the {term("traverse function")} slot, `tp_traverse`, and there is no way for the runtime to check your answer. Report too little and the collector concludes your object is held from outside and leaves the whole cycle alone. That is the failure mode: not a crash, a leak.

Two lines of C decide whether any of that machinery applies to your type at all. `Py_TPFLAGS_HAVE_GC` {cite("Include/object.h:520-530@v3.15.0rc1#Py_TPFLAGS_HAVE_GC")} in the flags, and allocation through `PyObject_GC_New` {cite("Python/gc.c:2026-2044@v3.15.0rc1#_PyObject_GC_New")}, which puts a small header in front of your object so the collector has somewhere to keep its bookkeeping.

Here is one container, a box holding a single object, written three ways. The next cell is only the types.
""")


lesson.code("""
TYPES = \"\"\"
#include <Python.h>
#include <stddef.h>

typedef struct {
    PyObject_HEAD
    PyObject *item;
} BoxObject;

typedef struct {
    PyObject *loose;
    PyObject *half;
    PyObject *tracked;
    long freed;
    long finalized;
} boxes_state;

static struct PyModuleDef boxes_module;

static boxes_state *
state_of(PyObject *self)
{
    PyObject *module = PyType_GetModuleByDef(Py_TYPE(self), &boxes_module);
    return module == NULL ? NULL : (boxes_state *)PyModule_GetState(module);
}

static PyObject *
box_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    int tracked = PyType_HasFeature(type, Py_TPFLAGS_HAVE_GC);
    BoxObject *self = tracked ? PyObject_GC_New(BoxObject, type)
                              : PyObject_New(BoxObject, type);
    if (self == NULL) {
        return NULL;
    }
    self->item = NULL;
    if (tracked) {
        PyObject_GC_Track(self);
    }
    return (PyObject *)self;
}

static void
loose_dealloc(BoxObject *self)
{
    PyTypeObject *type = Py_TYPE(self);
    boxes_state *state = state_of((PyObject *)self);
    if (state != NULL) {
        state->freed++;
    }
    Py_CLEAR(self->item);
    type->tp_free((PyObject *)self);
    Py_DECREF(type);
}

static int
tracked_traverse(BoxObject *self, visitproc visit, void *arg)
{
    Py_VISIT(Py_TYPE(self));
    Py_VISIT(self->item);
    return 0;
}

static int
half_traverse(BoxObject *self, visitproc visit, void *arg)
{
    Py_VISIT(Py_TYPE(self));
    return 0;
}

static int
tracked_clear(BoxObject *self)
{
    Py_CLEAR(self->item);
    return 0;
}

static void
tracked_finalize(PyObject *self)
{
    boxes_state *state = state_of(self);
    if (state != NULL) {
        state->finalized++;
    }
}

static void
tracked_dealloc(BoxObject *self)
{
    PyTypeObject *type = Py_TYPE(self);
    if (PyObject_CallFinalizerFromDealloc((PyObject *)self) < 0) {
        return;
    }
    PyObject_GC_UnTrack(self);
    boxes_state *state = state_of((PyObject *)self);
    if (state != NULL) {
        state->freed++;
    }
    Py_CLEAR(self->item);
    type->tp_free((PyObject *)self);
    Py_DECREF(type);
}

static PyMemberDef box_members[] = {
    {"item", Py_T_OBJECT_EX, offsetof(BoxObject, item), 0, "the one thing in the box"},
    {NULL, 0, 0, 0, NULL},
};

static PyType_Slot loose_slots[] = {
    {Py_tp_new, box_new},
    {Py_tp_dealloc, loose_dealloc},
    {Py_tp_members, box_members},
    {0, NULL},
};

static PyType_Spec loose_spec = {
    .name = "boxes.Loose",
    .basicsize = sizeof(BoxObject),
    .flags = Py_TPFLAGS_DEFAULT,
    .slots = loose_slots,
};

static PyType_Slot half_slots[] = {
    {Py_tp_new, box_new},
    {Py_tp_dealloc, tracked_dealloc},
    {Py_tp_traverse, half_traverse},
    {Py_tp_clear, tracked_clear},
    {Py_tp_members, box_members},
    {0, NULL},
};

static PyType_Spec half_spec = {
    .name = "boxes.Half",
    .basicsize = sizeof(BoxObject),
    .flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC,
    .slots = half_slots,
};

static PyType_Slot tracked_slots[] = {
    {Py_tp_new, box_new},
    {Py_tp_dealloc, tracked_dealloc},
    {Py_tp_traverse, tracked_traverse},
    {Py_tp_clear, tracked_clear},
    {Py_tp_finalize, tracked_finalize},
    {Py_tp_members, box_members},
    {0, NULL},
};

static PyType_Spec tracked_spec = {
    .name = "boxes.Tracked",
    .basicsize = sizeof(BoxObject),
    .flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC,
    .slots = tracked_slots,
};
\"\"\"

print(f"  {len(TYPES.splitlines())} lines of C, three types, one field each")
""")


lesson.md(f"""
Three specs, and the differences are small enough to list. `Loose` has no GC flag, no traverse and no clear, so the collector never hears about it. `Half` has the flag and a `tp_traverse` that reports the type and forgets the field. `Tracked` reports both, and adds a `tp_finalize`.

Reporting the type is not optional decoration. Since 3.9, a {term("heap type")} is expected to visit `Py_TYPE(self)`, because an instance holds a reference to its own type and a type can be part of a cycle like anything else {cite("Objects/typeobject.c:2607-2645@v3.15.0rc1#subtype_traverse")}.

The rest of the file is the module itself. It is worth reading for one reason: the counters live in {term("module state")} rather than in C statics. A `m_size` above zero gets a struct allocated with every module object {cite("Objects/moduleobject.c:1027-1035@v3.15.0rc1#PyModule_GetState")}, and a type made with `PyType_FromModuleAndSpec` can find its way back to it {cite("Objects/typeobject.c:5973-6005@v3.15.0rc1#PyType_GetModuleByDef")}. Statics would be shared across every {term("subinterpreter")} in the process, which is a bug waiting for somebody else to find.
""")


lesson.code("""
MODULE = \"\"\"
static PyObject *
counts(PyObject *module, PyObject *unused)
{
    boxes_state *state = (boxes_state *)PyModule_GetState(module);
    return Py_BuildValue("(ll)", state->freed, state->finalized);
}

static PyObject *
reset(PyObject *module, PyObject *unused)
{
    boxes_state *state = (boxes_state *)PyModule_GetState(module);
    state->freed = 0;
    state->finalized = 0;
    Py_RETURN_NONE;
}

static PyMethodDef boxes_methods[] = {
    {"counts", counts, METH_NOARGS, "How many boxes were freed and finalized so far."},
    {"reset", reset, METH_NOARGS, "Put both counters back to zero."},
    {NULL, NULL, 0, NULL},
};

static int
add(PyObject *module, PyObject **slot, PyType_Spec *spec, const char *name)
{
    *slot = PyType_FromModuleAndSpec(module, spec, NULL);
    if (*slot == NULL) {
        return -1;
    }
    return PyModule_AddObjectRef(module, name, *slot);
}

static int
boxes_exec(PyObject *module)
{
    boxes_state *state = (boxes_state *)PyModule_GetState(module);
    if (add(module, &state->loose, &loose_spec, "Loose") < 0) {
        return -1;
    }
    if (add(module, &state->half, &half_spec, "Half") < 0) {
        return -1;
    }
    return add(module, &state->tracked, &tracked_spec, "Tracked");
}

static int
boxes_traverse(PyObject *module, visitproc visit, void *arg)
{
    boxes_state *state = (boxes_state *)PyModule_GetState(module);
    Py_VISIT(state->loose);
    Py_VISIT(state->half);
    Py_VISIT(state->tracked);
    return 0;
}

static int
boxes_clear(PyObject *module)
{
    boxes_state *state = (boxes_state *)PyModule_GetState(module);
    Py_CLEAR(state->loose);
    Py_CLEAR(state->half);
    Py_CLEAR(state->tracked);
    return 0;
}

static PyModuleDef_Slot boxes_slots[] = {
    {Py_mod_exec, boxes_exec},
    {Py_mod_multiple_interpreters, Py_MOD_PER_INTERPRETER_GIL_SUPPORTED},
    /* Honest, because two threads bumping state->freed would lose counts. */
    {Py_mod_gil, Py_MOD_GIL_USED},
    {0, NULL},
};

static struct PyModuleDef boxes_module = {
    PyModuleDef_HEAD_INIT,
    .m_name = "boxes",
    .m_size = sizeof(boxes_state),
    .m_methods = boxes_methods,
    .m_slots = boxes_slots,
    .m_traverse = boxes_traverse,
    .m_clear = boxes_clear,
};

PyMODINIT_FUNC
PyInit_boxes(void)
{
    return PyModuleDef_Init(&boxes_module);
}
\"\"\"

if not HAVE_C:
    print(NOTHING)
else:
    TROUBLE = build("boxes", TYPES + MODULE)
    HAVE_C = not TROUBLE
    if HAVE_C:
        import boxes

        made = [name for name in ("Loose", "Half", "Tracked") if hasattr(boxes, name)]
        print(f"  built and imported, with these types: {made}")
    else:
        print(f"  the compiler said: {TROUBLE}")
""")


lesson.md(f"""
Now put one of each in a cycle. A box whose `item` is the box itself has a reference count of one that nothing outside can reach, which is exactly the case reference counting alone cannot handle. Drop the name, run a collection, and ask the module how many boxes it has freed.

{lesson.claim("The GC flag on its own is not enough. A tp_traverse that forgets a field leaks just as completely as no tp_traverse at all")}
""")


lesson.code("""
import gc

KINDS = ("Loose", "Half", "Tracked")

if not HAVE_C:
    print(NOTHING)
else:
    print("  type      collector sees it   traverse reports   freed after a collection")
    for name in KINDS:
        kind = getattr(boxes, name)
        boxes.reset()
        box = kind()
        seen = gc.is_tracked(box)
        box.item = box
        reports = len(gc.get_referents(box))
        del box
        gc.collect()
        print(f"  {name:9} {seen!s:19} {reports:16}   {boxes.counts()[0]}")
""")


lesson.md(f"""
`Loose` is invisible. `Half` is visible and reports one thing, its type, so the collector subtracts one reference from a box whose count is two and decides somebody outside still wants it. `Tracked` reports both and gets collected. The three rows differ by four lines of C.

`gc.get_referents` in that table is `tp_traverse` called directly, which is the closest thing to a test you can write for it. If the numbers there do not match the fields your object owns, you have the `Half` bug.

{figure("three-boxes-one-cycle", "a table of three container types with what the collector sees of each and whether it was freed")}

There is a short list of what a `tp_traverse` handler may call, and it is short for a reason: traversal runs in the middle of a collection, where allocating, raising or running Python would be a disaster. Anything that could set an exception is out, which is why 3.15 added a whole family of functions ending in `_DuringGC` that do the same job as their ordinary versions and promise to have no side effects and never raise.

{figure("what-traverse-may-call", "a table of the six things a tp_traverse handler is allowed to call")}

## Where cleanup goes

`Tracked` has a third slot the other two do not, and it is the answer to a question every container eventually raises: where does cleanup go when the object is part of a cycle?

The {term("clear function")}, `tp_clear`, is what the collector calls to break the cycle {cite("Python/gc.c:1083-1120@v3.15.0rc1#delete_garbage")}. It drops exactly what `tp_traverse` reported. It is not the place for closing a file or releasing a lock, because it can be called while the rest of the cycle is being emptied around it.

`tp_finalize` is that place. It is the modern `__del__`: it runs once per object, before anything is torn down, on both routes to death. When a count reaches zero, `tp_dealloc` calls it on the way in {cite("Objects/object.c:595-630@v3.15.0rc1#PyObject_CallFinalizerFromDealloc")}. When the collector finds a cycle, it runs `tp_finalize` on the whole unreachable set first, then starts clearing. The runtime keeps a {term("finalized bit")} so it cannot happen twice.

{figure("where-the-two-hooks-run", "the two routes an object takes to being freed and where each hook runs on it")}

{lesson.claim("A tp_finalize runs exactly once per object whether the object died on a reference count or inside a cycle")}
""")


lesson.code("""
if not HAVE_C:
    print(NOTHING)
else:
    boxes.reset()
    plain = boxes.Tracked()
    plain.item = [1, 2, 3]
    del plain
    freed, final = boxes.counts()
    print(f"  died on its reference count: finalized {final}, freed {freed}")

    boxes.reset()
    looped = boxes.Tracked()
    looped.item = looped
    del looped
    gc.collect()
    freed, final = boxes.counts()
    print(f"  died inside a cycle:         finalized {final}, freed {freed}")
""")


lesson.md(f"""
One hook, both routes, once each. That is the whole reason `tp_finalize` replaced the old `tp_del` slot, which M09 covered from the collector's side: an object with the old slot in a cycle used to be uncollectable and got put on `gc.garbage` for a human to deal with.

## The promise at the bottom of the file

The fourth rule is one line, and on most builds it does nothing at all.

An {term("extension module")} on a {term("free threaded build")} has to say whether it is safe without the lock. `Py_mod_gil` with `Py_MOD_GIL_NOT_USED` is a promise. Saying nothing, or saying `Py_MOD_GIL_USED`, makes the runtime turn the lock back on for the whole process the moment your module is imported, and print a warning naming you.

The `boxes` module above says `Py_MOD_GIL_USED`, and that is not modesty. Two threads calling `state->freed++` would lose counts, because that is a read, an add and a write with nothing in between. Keeping the promise instead would mean a {term("critical section")} around every field the two types share, which C02 and C06 went through from the reading side. `errpath` says `Py_MOD_GIL_NOT_USED` and means it, because it has no state at all.

{lesson.claim("One imported module that has not declared itself safe turns the lock back on for the whole process", unobservable="the flip only happens on an interpreter built with --disable-gil, and this notebook is almost certainly not one")}

CPython's own test suite ships a shared object that exports two init functions differing only in that line, which makes the difference easy to weigh without compiling anything. This recording loads each of them on a free threaded build, in a child of its own so the answer is not contaminated by the previous one.

{recording(ON_FREETHREADED)}

The third case is the escape hatch. `PYTHON_GIL=0` tells the runtime you have read the module's source yourself and disagree with its declaration, and the warning goes away with the lock. It is exactly as safe as your reading was.

## Proving it

Four rules, and every way of breaking them looks like working code. So the last thing to write is the test that would have caught any of it.

The idea fits in a handful of lines. Give the thing you are watching a type of its own so it is easy to count. Collect. Count. Do the work. Collect and count again. Repeat, and throw the first few rounds away. If the count goes up by the same amount every single time, that is a leak; if it goes up once and settles, that is a cache filling.

{lesson.claim("An ordinary test run cannot see a reference leak at all, which is why CPython runs its own suite a second way")}
""")


lesson.code("""
class Held:
    \"\"\"Something for a box to hold, so that the thing being leaked has a name.\"\"\"


def alive():
    \"\"\"How many Held objects the collector can still find anywhere in this process.\"\"\"
    return sum(1 for one in gc.get_objects() if isinstance(one, Held))


def hunt(work, repeats=6, warmups=3):
    \"\"\"Run something over and over and report what each run left behind.\"\"\"
    deltas = []
    for _ in range(repeats):
        gc.collect()
        before = alive()
        work()
        gc.collect()
        deltas.append(alive() - before)
    return deltas[warmups:]


def a_cycle(kind):
    \"\"\"One box and one Held pointing at each other, with no name left for either.\"\"\"

    def work():
        box = kind()
        held = Held()
        held.box = box
        box.item = held

    return work


if not HAVE_C:
    print(NOTHING)
else:
    for name in KINDS:
        left = hunt(a_cycle(getattr(boxes, name)))
        verdict = "a leak" if all(one >= 1 for one in left) else "fine"
        print(f"  {name:9} {left!s:12} {verdict}")
""")


lesson.md(f"""
That is CPython's own `-R` flag with the interesting parts taken out. The real one counts references and allocated blocks and open file descriptors rather than instances of one class you picked, which means it needs a {term("debug build")}, since an ordinary build keeps no running total of references. It throws away the first few runs, because caches fill on first use and that is not a leak. And it only calls something a failure if every measured run leaked at least one {cite("Lib/test/libregrtest/refleak.py:196-209@v3.15.0rc1#check_rc_deltas")}, then prints the deltas it saw {cite("Lib/test/libregrtest/refleak.py:214-236@v3.15.0rc1#leaked")}.

{figure("what-the-hunter-counts", "four tests with the verdict an ordinary run gives and the verdict the leak hunter gives")}

This recording runs four small tests on a debug build, once the way anybody runs a test suite and once with `-R 3:3`, which means three warm up runs and three measured ones.

{recording(ON_DEBUG)}

All four pass the first time. Two fail the second, and one of the two that passes still gets a note, because it left something behind on the first measured run and then stopped. That last case is the reason the hunter is careful rather than strict, and also the reason a first attempt at your own leak test will produce noise.

## Try it yourself

Change `half_traverse` to report `self->item` and nothing else, so it visits the field but forgets the type. Rebuild and rerun the table. The box is still collected, because nothing in these examples puts a type in a cycle, which is exactly why the rule about visiting `Py_TYPE(self)` is easy to break and hard to notice.

Take the `Py_DECREF` out of `tracked_dealloc`'s `Py_CLEAR(self->item)` and run the hunter over `Tracked` again. You have written the `Half` bug a second way, with a complete `tp_traverse` and a `tp_dealloc` that does not finish the job.

Add a `tp_finalize` to `Loose` and put one in a cycle. Nothing runs, because a type the collector cannot see never gets a second chance.

Give `Tracked` a `__del__` written in Python by subclassing it, then put an instance in a cycle. Compare what runs against the C `tp_finalize` on the same object, and in which order.

## What you now know

An error branch that forgets one `Py_DECREF` leaks silently and forever, and the shape that prevents it is a single cleanup block reached by `goto`.

A container type needs three things before the collector can help it: the `Py_TPFLAGS_HAVE_GC` flag, allocation through `PyObject_GC_New`, and a `tp_traverse` that reports every field, including the type of a heap type. Miss the flag and you are invisible. Miss a field and you are visible and lying, which leaks just as thoroughly.

`tp_clear` breaks cycles and belongs to the collector. `tp_finalize` is where your cleanup goes, and it runs once per object on either route to death.

Module state exists so that C extensions do not keep things in statics, which subinterpreters share.

`Py_mod_gil` is a promise about thread safety that the runtime cannot check, so it believes you, and turns the lock back on for everybody if you decline to make it.

None of these failures produce an error. The tool that finds them runs your tests six times on a debug build and counts what is left, and it is the difference between code that passes review and code that runs for a year.

## What is next

That is the end of the runtime part, and the end of watching CPython work. R01 asked what happens before your first line, R08 asked what happens after your last one, and this one asked what the runtime expects from code you write in its own language.

What is left in this milestone is not lessons. It is the blueprints: the written down descriptions of state layout, the object model under free threading, the import system and the C API surface, precise enough that somebody could build them again in another language. The reimplementation track after that is the whole point of writing any of this down.
""")


raise SystemExit(lesson.save())
