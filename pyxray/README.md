# pyxray

Instrumentation for looking inside a running CPython, from a notebook.

Every lesson in this repository imports this package. The reason it exists is that a lesson about the small integer cache should contain one line about the small integer cache, not thirty lines of introspection scaffolding the reader has to skip past to find the idea.

Nothing here needs a debug build, a C compiler or `ctypes`. The reader on a locked down laptop in a browser tab is the reader this project is written for, and they have to be able to see a real reference count on a real object rather than a picture of one.

## What is in it

`pyxray.build` answers "which interpreter am I actually looking at". Every observation in this material is build dependent, so every lesson opens with `pyxray.show()` and the banner is not optional. It reports the version, the debug and free threaded flags, whether the JIT is running, and a probed list of capabilities, and it says out loud when the running version is not the one the prose was written against.

`pyxray.obj` is the object header as far as it can be seen from Python: identity, type, reference count, immortality, size, and whether the cycle collector is tracking it. It also has the probes the lessons need, including the small integer range and whether a string is the one in the intern table.

`pyxray.bytecode` presents `dis` as data rather than as printed text, and adds the three things a lesson keeps needing that `dis` does not hand you: the specialized opcode next to the one the compiler actually emitted, the inline cache entries that follow an instruction, and a side by side comparison of two disassemblies. Two more helpers answer the questions readers actually get stuck on. `argument_meaning(opname)` says what the argument byte of an instruction is counting or indexing, which is a different answer for every instruction and is why `LOAD_CONST 1` and `CALL 1` have nothing to do with each other. `jumps(code)` gives every jump with the arithmetic written out, because a jump argument counts instructions rather than bytes and it counts from after the jump including its cache slot, and getting either of those wrong lands you two instructions away from where you meant to be.

`pyxray.stack` is the value stack, which is the thing you have to be holding in your head to read a listing. It shows the height either side of every instruction, and it works out `co_stacksize` from scratch by walking the flow graph the way `calculate_stackdepth` does in `Python/flowgraph.c`. That walk is a reimplementation rather than a lookup, so it can be wrong, and there is a test that runs it over every code object in the standard library and compares against the number CPython wrote. Thirty three thousand of them agree.

`pyxray.compiler` runs CPython's front end one stage at a time through `_testinternalcapi`, so a reader can watch the compiler emit an instruction sequence and watch the optimizer rewrite it. This is the best teaching hook in the codebase and almost nobody uses it. Two smaller helpers sit next to it. `pseudo_instructions()` lists the opcodes that exist only inside the compiler and never reach a code object, read out of the opcode table rather than typed into a list that would go stale. `folds(expression)` answers whether the compiler worked an expression out ahead of time, by compiling it and looking for arithmetic in the result, which is how a lesson can find the exact size where folding stops without anyone having to know the limit.

`pyxray.tokens` is the tokenizer as a table you can read, with the column positions lined up under the line they came from, which is the only way indentation errors ever make sense.

`pyxray.trees` is the syntax tree as something you can walk, compare and round trip, rather than as the nested brackets `ast.dump` prints.

`pyxray.scopes` answers where a name lives. It puts `symtable`'s decision and the opcode the compiler produced from that decision in the same row, so you can see the two agree instead of taking either one on trust.

`pyxray.cite` turns a citation into a clickable link using the same parser CI checks citations with, so there is one implementation of the format rather than two.

`pyxray.theme` is the colours, the type sizes and the spacing, in one place. The diagrams, the charts and the animations all import it, which is why they look like one project.

## Using it

```python
import pyxray

pyxray.show()

value = [1, 2, 3]
print(pyxray.obj.header(value).describe())
print(pyxray.bytecode.table("x = 1 + 2"))
```

## Things it gets right that are easy to get wrong

**Reference counts are corrected for the call that asks.** `sys.getrefcount` is documented as returning one more than you expect, because passing the object creates a reference. As of 3.14 that is only sometimes true. Passing a local now compiles to `LOAD_FAST_BORROW`, which hands over a borrowed reference and costs nothing, while passing a global still compiles to `LOAD_GLOBAL`, which costs one. A fixed subtraction therefore reports 0 for a local and 1 for a global that both hold exactly one reference. `pyxray.obj.refcount` looks at the instruction that pushed the argument and corrects for that specific call, so the same object gives the same answer from a test, a notebook cell and a function body. `pyxray.obj.raw_refcount` is there for the lesson that explains why the correction is needed.

**Immortal objects report no count rather than a parked one.** `None` and `True` and every type object have their reference count parked at a value the interpreter never decrements. Printing 3221225472 next to a paragraph about reference counting teaches the wrong model, so `refcount` returns `None` for them and `header().describe()` says the object is never freed.

**Numbers come from probes, never from prose.** The small integer cache stops at 256 on 3.14 and at 1024 on 3.15. Every tutorial that hard coded 256 became wrong without its author being told. `small_int_range()` walks outward from zero building each integer with `int(str(n))`, so the compiler cannot fold the two occurrences into one constant and make everything look shared.

**Opcode facts come from the tables CPython generates for itself.** `_opcode_metadata` is generated from `Python/bytecodes.c` by `Tools/cases_generator` at build time, so asking it is asking the same source the interpreter was compiled from. A hand written table would be wrong within one release, which is the thesis of this project applied to itself.

**Asking a question does not change the answer.** `is_interned` interns a fresh copy rather than the string it was given, because interning the original would put it in the table and every call after the first would answer True regardless of the truth.

## Version differences the test suite pins down

The suite runs on 3.15.0rc1, which is the pin, and on 3.14, which is what Pyodide and Colab give a reader today. Three differences are asserted from both sides rather than described in a comment, so that a lesson which relies on one of them cannot quietly stop being true.

The small integer cache upper bound is 256 on 3.14 and 1024 on 3.15, which breaks the canonical `257 is 257` example. `RESUME` carries no inline cache entry on 3.14 and one on 3.15, so it occupies two bytes on one and four on the other, and any prose that walks offsets by hand from a 3.14 disassembly is off by two from its second instruction onward. `LOAD_FAST_BORROW` exists on both, and is the reason the reference count correction cannot be a constant.

## What it deliberately does not do

`_testinternalcapi.assemble_code_object` is the third compiler hook and it is the one that would let a lesson build a code object by hand. It is not wired up. It asserts on its metadata rather than raising, and a failed assertion aborts the process, which in a notebook kills the kernel and loses whatever the reader had done. `pyxray.compiler.assemble` raises `NotImplementedError` with the two specific traps written out. Wiring it up safely means validating every key and its type before the call, which is tracked as its own piece of work.

## Running the tests

```
just test          # the pinned interpreter, 3.15.0rc1
just test-3-14     # the same suite on the version the browser tier runs
```
