# What stays in Tier 0 after measuring Pyodide

This is the written half of gate Q1. The measured half is `report.md` next to it, and the raw runs are in `native.json` and `pyodide.json`. Reproduce them with `just build-probe`, or open `probe.ipynb` and run the same checks on whatever browser you are sitting in front of.

## The short version

Tier 0 survives. Fifteen checks, twelve behave the same in a browser as they do on a native CPython, and none of the three differences takes an experiment out of Tier 0.

That is a better result than the issue expected. Rule 3 stands, and `pyxray.replay` stays a fallback in M2 rather than becoming a load bearing part of M0.

## What was measured

Pyodide 314.0.6 from npm, which is CPython 3.14.2 built for `emscripten-5.0.3-wasm32`, driven from Node. The control is a native CPython 3.14.7, deliberately 3.14 rather than the pinned 3.15, so a version difference does not get reported as a build difference.

## The three differences

**`compiler_codegen` returns no constants list.** It works and returns the same eight instructions in both places, but the metadata dictionary it hands back has only `argcount`, `kwonlyargcount` and `posonlyargcount` in this build. Native 3.14 and 3.15 both include `consts` as well. `pyxray.compiler.stages` used to pass `metadata["consts"]` straight into `optimize_cfg`, so that line raised `KeyError` in a browser.

The optimizer itself is fine. Build a constants list of the right length from the instruction sequence and `optimize_cfg` runs and returns the same seven instructions it returns natively. So this was a missing key rather than a missing stage, and the fix was in our code, not in Pyodide. It is fixed: `stages` builds that list itself now, from the sequence it is about to pass in, and records whether the values were real. Issue 77.

One thing does not survive the fix, and it is worth being plain about. Without the values, the optimizer cannot fold `6 * 7` into `42`, and on some code it makes a different decision than it would with them. So the stage runs in a browser and its output is not what the source compiles to. The pipeline widget says so on that pane rather than letting the reader assume, and the last pane, which is the finished code object, is the real answer on every build.

**A wrong constants list kills the runtime instead of raising.** Hand `optimize_cfg` a list that is too short and a native interpreter raises `ValueError: LOAD_CONST index 0 is out of range for consts (len=0)`. In WebAssembly the same call reads past the end of memory, the runtime does not come back, and in a notebook the kernel dies and the reader loses their work.

This does not remove anything from Tier 0, but it does constrain how the pipeline widget is written. It has to build the constants list itself and never pass one it was given, because there is no way to catch this. The probe notebook runs that check last, on its own, with a paragraph warning the reader first.

**A thread cannot be started.** `threading` imports and `threading.Thread(...)` constructs, and `start()` raises `RuntimeError: can't start new thread`. This is expected for a single threaded WebAssembly build without the pthread proxy, and it was already the assumption: the concurrency lessons are in M4 and were never Tier 0. Nothing moves.

## What works, and is worth saying out loud

`_testinternalcapi` imports, which was the check most likely to sink this. `compiler_codegen` and `optimize_cfg` are both there and both callable.

`assemble_code_object` is present, and the probe only checks that it exists rather than calling it. That is not laziness. It asserts on its metadata instead of raising, and a failed assertion aborts the process, so calling it to see what happens would be the same class of mistake as the constants list above. `pyxray.compiler.assemble` refuses to call it for the same reason, tracked in issue 35.

`ctypes` reads both fields in front of a live object: the reference count matches `sys.getrefcount`, and the type pointer one word further along really is `id(list)`. Object headers stay live in the browser rather than being shown from a recording.

`sys.monitoring` registers a tool, sets a local event and fires the callback. The stepper stays in Tier 0.

`sys.settrace` still reports call, line and return, so the fallback exists too.

The cycle collector frees a two node cycle, has three generations, and is enabled.

`dis`, `ast`, `symtable`, `tokenize`, `marshal`, `opcode` and `_opcode` all import, and `dis` gives the same five instructions, the same ten byte code object and the same 109 byte marshal blob as the native 3.14.

## Where the two are genuinely different machines

Four answers differ without anything being broken, and a lesson that asserts one of these numbers is teaching the build rather than the language.

Pointers are four bytes rather than eight. `sysconfig.get_platform()` is `emscripten-5.0.3-wasm32`. The third garbage collector threshold is 0 rather than 10, so the oldest generation is never collected on a schedule. And the metadata key described above.

The pointer size is the one to watch. Every diagram in the object lessons draws an eight byte word, and a reader in a browser who measures it gets four. T08 and T09 need a sentence about that, and it is a good sentence to have: it is the difference between memorising a number and knowing where the number comes from.

## The phone question, answered partly

The issue asks how long a cold boot takes on a mid range phone. This probe cannot answer that. It boots in a second or two from a local disk under Node, which is a floor and not a promise.

What it can measure is the part that dominates on a phone: 13.5 MB has to arrive before the first cell runs, which is the WebAssembly binary, the JavaScript glue, the standard library zip and the lock file. On a slow connection that is the wait, not the boot. Anything about tab memory, a service worker cache, or a real device is not answered here and is worth its own issue when the site actually exists.

## Running the lessons themselves

Everything above asks whether a surface exists. That is a proxy, and a good one, but the promise on the front page is that a chapter runs in a browser tab, and the only way to know that is to run the chapter. So there is a second run next to this one: `lessons.json` and `lessons.md`, made by `wasmprobe lessons`, which takes every lesson notebook, boots a fresh Pyodide runtime for it, and runs its code cells in order in one namespace.

pyxray is not installed there. It is mounted off the disk and put on `sys.path`, so the run needs no network and tests the source in this checkout rather than whatever is published today. The one thing changed is the `%pip` line in the install cell, which becomes `pass`. The rest of that cell still runs, because it also imports `sys` and prints the version banner and half the lesson below it depends on that.

Twelve lessons, 180 code cells, and eleven of the twelve run start to finish. The one that does not is T07, and it is worth reading before writing any more Tier 0 material. The cell recursing through `sorted` is meant to print a `RecursionError`, and in WebAssembly it overflows the interpreter's own call stack instead. That is not a Python exception and there is nothing to catch: the runtime does not come back, and in a notebook the reader loses the tab. The eleven cells after it never ran, and they are not retried in a fresh runtime, because a cell that ran in a different interpreter than the cells above it has not been tested, it has been let off. Issue 105 is the fix.

A cell that fails there is not automatically a bug in this repository, so failures are not all treated the same. A decision written in `ACCEPTED` in `lessons.py` keeps the failure in the report and out of the build's way. A failure nobody has written a decision about stops the build. CI runs this on every pull request, which means a lesson that stops working in a browser is caught the day it stops rather than whenever somebody next opens a tab.

## What this changes

Nothing moves from Tier 0 to Tier 1.

Three pieces of work fell out of it. Two are done. `pyxray.compiler.stages` builds its own constants list, so the compiler stages run in a browser, and it says whether the values were real so nothing claims a fold that did not happen (issue 77). The pipeline widget reaches the optimizer only through that function and takes a list from nobody, because the alternative is a dead kernel (issue 78). Still open: a sentence in the object lessons about the word size, measured rather than asserted, which is what those lessons already do for the small integer cache (issue 79).
