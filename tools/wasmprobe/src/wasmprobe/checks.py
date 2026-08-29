"""The questions this project needs a browser Python to answer.

Every Tier 0 experiment in the lessons runs on Pyodide, which is CPython compiled to
WebAssembly by Emscripten. The promise is that somebody on a locked down laptop can do
real internals work with nothing installed, and that promise rests entirely on which
introspection surfaces survive that build. Nobody had checked.

Each check is a string of Python rather than a function, because the same source has to run
in two places: in this process, on a native interpreter, and inside a WebAssembly runtime
driven from Node. Shipping source means the two runs cannot drift apart, which they would
the first time somebody edited one and forgot the other.

A check returns something JSON can carry. It must not print, and it must not depend on any
earlier check having run, because a check that takes the runtime down with it means
everything after it starts from a fresh one.
"""

from __future__ import annotations

from dataclasses import dataclass

#: A Tier 0 experiment somewhere in the lessons needs this. If it fails in the browser,
#: that experiment has to move to Tier 1 and be shown from a recording instead.
TIER0 = "tier0"

#: Wanted, and survivable. A failure costs a nicer version of something we can still do.
NICE = "nice"

#: Neither. Recorded because the number is worth knowing and somebody will ask.
INFO = "info"


@dataclass(frozen=True)
class Check:
    """One question, the code that answers it, and what a failure would cost."""

    key: str
    question: str
    weight: str
    costs: str
    source: str
    #: Set when we already know this one fails in the browser and have decided what to do
    #: instead. The sentence goes in the report and the check stops failing the build, so a
    #: known gap stays visible without hiding the next one behind a permanently red job.
    accepted: str = ""

    @property
    def blocking(self) -> bool:
        """Should the build stop when this works natively and not in the browser."""
        return self.weight == TIER0 and not self.accepted


CHECKS = [
    Check(
        key="version",
        question="Which CPython is this, and what was it built for",
        weight=INFO,
        costs="Nothing. Every other answer here is about this interpreter.",
        source="""
import platform
import sys
import sysconfig

result = {
    "python": platform.python_version(),
    "platform": sysconfig.get_platform(),
    "pointer_bytes": sys.maxsize.bit_length() // 8 + 1,
    "free_threaded": bool(sysconfig.get_config_var("Py_GIL_DISABLED")),
}
""",
    ),
    Check(
        key="internal_capi_import",
        question="Is _testinternalcapi importable at all",
        weight=TIER0,
        costs="Everything that shows the compiler one stage at a time. It is the single "
        "best hook this project has, and without it T05 has nothing live to show.",
        # The first two are called for real by the checks below. The third is only looked
        # at, never called, because assemble_code_object asserts on its metadata instead of
        # raising and a failed assertion aborts the process rather than throwing something
        # a notebook could survive. Same reason pyxray.compiler.assemble does not call it.
        source="""
import _testinternalcapi

wanted = ("compiler_codegen", "optimize_cfg", "assemble_code_object")
result = {name: hasattr(_testinternalcapi, name) for name in wanted}
""",
    ),
    Check(
        key="compiler_codegen",
        question="Does compiler_codegen turn a tree into an instruction sequence",
        weight=TIER0,
        costs="The first compiler stage in T05 and in the pipeline explorer widget.",
        source="""
import _testinternalcapi
import ast

sequence, metadata = _testinternalcapi.compiler_codegen(ast.parse("answer = 6 * 7"), "<probe>", 0)
instructions = sequence.get_instructions()
result = {
    "instructions": len(instructions),
    "first": instructions[0][0],
    "metadata_keys": sorted(metadata),
}
""",
    ),
    Check(
        key="optimize_cfg",
        # This is how pyxray called optimize_cfg until this probe was written, and it is
        # kept as it was rather than updated, because the point of it now is the contrast
        # with the check below. Fixed in issue 77.
        question="Does optimize_cfg run when it is handed the constants from the metadata",
        weight=INFO,
        costs="Nothing now. It cost the whole middle stage until this measurement, and the "
        "answer was to build the constants list off the instruction sequence rather than "
        "ask for it. Still worth asking every run: the day this passes is the day constant "
        "folding can be shown in a browser as well as here.",
        source="""
import _testinternalcapi
import ast

sequence, metadata = _testinternalcapi.compiler_codegen(ast.parse("answer = 6 * 7"), "<probe>", 0)
optimized = _testinternalcapi.optimize_cfg(sequence, metadata["consts"], 0)
result = {"instructions": len(optimized.get_instructions())}
""",
    ),
    Check(
        key="optimize_cfg_direct",
        # The check above asks for the constants in the metadata that codegen returned, so
        # a missing key means it never reaches the function at all. This one builds its own
        # list of the right length off the instruction sequence, which is what
        # pyxray.compiler does now, so the answer is about optimize_cfg and nothing else.
        question="Does optimize_cfg run at all, given a constants list built by hand",
        weight=TIER0,
        costs="The middle stage. It is the one that makes 6 * 7 disappear, which is the "
        "single most convincing thing in the first part of the course.",
        source="""
import _testinternalcapi
import ast
import dis

sequence, metadata = _testinternalcapi.compiler_codegen(ast.parse("answer = 6 * 7"), "<probe>", 0)
slots = [one[1] for one in sequence.get_instructions() if one[0] in dis.hasconst]
consts = [object() for _ in range(max(slots, default=-1) + 1)]
optimized = _testinternalcapi.optimize_cfg(sequence, consts, 0)
result = {"slots": len(consts), "instructions": len(optimized.get_instructions())}
""",
    ),
    Check(
        key="optimize_cfg_short_consts",
        # Not a capability. A safety question, and the reason it is here is that a reader
        # types their own code into the pipeline widget, and a wrong constants list is one
        # of the easy ways to get there.
        question="What happens when optimize_cfg is handed a constants list that is too short",
        weight=INFO,
        costs="Nothing, and it is worth knowing. A clean exception means the widget can "
        "show the reader their mistake. A dead runtime means it has to check first.",
        source="""
import _testinternalcapi
import ast

sequence, metadata = _testinternalcapi.compiler_codegen(ast.parse("answer = 6 * 7"), "<probe>", 0)
try:
    _testinternalcapi.optimize_cfg(sequence, [], 0)
    result = {"raised": None}
except BaseException as error:
    result = {"raised": f"{type(error).__name__}: {error}"}
""",
    ),
    Check(
        key="ctypes_header",
        question="Can ctypes read the two fields in front of every object",
        weight=TIER0,
        costs="Object headers shown from a recording rather than from the reader's own "
        "live objects. A real loss and survivable.",
        source="""
import ctypes
import sys

value = [1, 2, 3]
word = ctypes.sizeof(ctypes.c_ssize_t)
result = {
    "refcount_field": ctypes.c_ssize_t.from_address(id(value)).value,
    "getrefcount": sys.getrefcount(value),
    "type_pointer_matches": ctypes.c_void_p.from_address(id(value) + word).value == id(list),
    "word_bytes": word,
}
""",
    ),
    Check(
        key="monitoring",
        question="Does sys.monitoring register a callback and fire it",
        weight=TIER0,
        costs="The stepper goes offline for Tier 0, and watching a function run one "
        "instruction at a time is most of T07.",
        source="""
import sys

TOOL = 5
seen = []
sys.monitoring.use_tool_id(TOOL, "wasmprobe")
try:
    def target():
        return 1 + 1
    sys.monitoring.register_callback(
        TOOL, sys.monitoring.events.PY_START, lambda *arguments: seen.append(arguments)
    )
    sys.monitoring.set_local_events(TOOL, target.__code__, sys.monitoring.events.PY_START)
    target()
finally:
    sys.monitoring.free_tool_id(TOOL)
allowed = [
    name
    for name in dir(sys.monitoring.events)
    if name.isupper() and not name.startswith("NO_")
]
result = {"fired": len(seen), "event_names": len(allowed)}
""",
    ),
    Check(
        key="settrace",
        question="Does sys.settrace still see call, line and return",
        weight=NICE,
        costs="The fallback for anything sys.monitoring cannot do. Losing both would be "
        "the bad case.",
        source="""
import sys

seen = []
def tracer(frame, event, argument):
    seen.append(event)
    return tracer
def target():
    return 2
sys.settrace(tracer)
try:
    target()
finally:
    sys.settrace(None)
result = {"events": seen}
""",
    ),
    Check(
        key="gc",
        question="Does the cycle collector behave the way T09 says it does",
        weight=TIER0,
        costs="T09 shows a cycle being collected. If the numbers are different in the "
        "browser the lesson is teaching Emscripten rather than CPython.",
        source="""
import gc
import weakref

class Node:
    pass
first, second = Node(), Node()
watch = weakref.ref(first)
first.other, second.other = second, first
del first, second
gc.collect()
# What gc.collect() returns counts everything it swept, including whatever else this
# process happened to be holding, so it is different every time. Whether this particular
# cycle went away is the question the lesson actually asks.
result = {
    "cycle_freed": watch() is None,
    "thresholds": list(gc.get_threshold()),
    "enabled": gc.isenabled(),
    "generations": len(gc.get_stats()),
}
""",
    ),
    Check(
        key="debugmallocstats",
        question="Does sys._debugmallocstats produce anything under Emscripten's allocator",
        weight=NICE,
        costs="One cell in T09. It writes to the real standard error rather than to "
        "sys.stderr, so a notebook cannot capture it anyway.",
        source="""
import sys

result = {"callable": callable(getattr(sys, "_debugmallocstats", None))}
""",
    ),
    Check(
        key="front_end_modules",
        question="Do dis, ast, symtable, tokenize and marshal all import",
        weight=TIER0,
        costs="Most of the first part of the course. These are pure Python or small C "
        "modules, so a failure here would be a surprise.",
        source="""
found = {}
for name in ("dis", "ast", "symtable", "tokenize", "marshal", "opcode", "_opcode"):
    try:
        __import__(name)
        found[name] = True
    except Exception as error:
        found[name] = f"{type(error).__name__}: {error}"
result = found
""",
    ),
    Check(
        key="disassembly",
        question="Does dis give the same instructions as a native interpreter",
        weight=TIER0,
        costs="Every bytecode listing in the course. A difference here is a difference in "
        "the compiled build rather than in the language.",
        source="""
import dis
import marshal

source = "answer = 6 * 7"
code = compile(source, "<probe>", "exec")
result = {
    "opnames": [one.opname for one in dis.get_instructions(source)],
    "code_size": len(code.co_code),
    "consts": [repr(one) for one in code.co_consts],
    "marshal_size": len(marshal.dumps(code)),
}
""",
    ),
    Check(
        key="small_integers",
        question="Where does the shared range of small integers stop",
        weight=INFO,
        costs="Nothing, and T08 measures it rather than asserting it for this reason.",
        source="""
top = 0
for candidate in range(0, 4096):
    if int(str(candidate)) is int(str(candidate)):
        top = candidate
result = {"top": top}
""",
    ),
    Check(
        key="threading",
        question="Can a thread be started",
        weight=NICE,
        costs="The whole concurrency part in the browser. Those lessons are late enough "
        "that a recording is an acceptable answer, and it has to be a deliberate one.",
        source="""
import threading

ran = []
worker = threading.Thread(target=lambda: ran.append(True))
worker.start()
worker.join()
result = {"ran": ran == [True], "active": threading.active_count()}
""",
    ),
]

BY_KEY = {check.key: check for check in CHECKS}
