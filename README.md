# cpython-internals

A complete teardown of CPython 3.15, taught from absolute zero, as reactive notebooks, animations and browser playgrounds. The same work produces a second artifact: a specification precise enough that you can rebuild a compatible Python from scratch in Go or Rust, with a conformance suite that tells you how far you got.

**Status: pre M0.** Nothing is built yet. The plan is in the [milestones](https://github.com/tamnd/cpython-internals/milestones) and the decisions that have not been made yet are in the [open questions](https://github.com/tamnd/cpython-internals/issues?q=is%3Aissue+label%3Akind%2Fopen-question).

## Who this is for

Two people, and pretending they are one person is how projects like this fail.

The first knows Python, has never written C, and has never built an interpreter. They need a path with no cliff in it, where every claim is something they can watch happen on their own screen. They will quit at the first paragraph that says "the compiler then emits the appropriate bytecode" without showing them.

The second already knows what a bytecode VM is and wants to write one that passes CPython's own test suite. They do not need motivation. They need exact field layouts, exact algorithms, exact edge cases, exact error messages and a harness.

Every chapter therefore produces two things. The chapter teaches, in prose and pictures and runnable cells. The blueprint specifies, with structures, algorithms, invariants, edge cases and port notes, and no motivation at all. CI checks that the two agree.

## What is different about it

**Three passes, not one walk.** Linear internals books order the material the way data flows, which means a beginner spends three weeks in the tokenizer and arrives at the eval loop exhausted. The drop off curve of every CPython resource has its cliff in the same place. This one does three complete traversals of the whole machine instead. Pass one is a single day, standard library only, browser only, and ends with the reader able to draw the entire pipeline from memory. Pass two opens every box in C. Pass three changes them.

**Nothing is asserted without an experiment.** There is a claim ledger, it is published, and CI fails the build if a behavioural claim in the prose has no runnable cell behind it. Claims that genuinely cannot be observed from Python are marked as such and capped at three per lesson, because without the cap they become the escape hatch that turns this back into a book.

**Every chapter runs in a browser.** Pyodide 314 is CPython 3.14 compiled to WebAssembly, so real bytecode, refcount, dictionary layout and garbage collection experiments work on a locked down school laptop with nothing installed. Chapters that need a debug build and a debugger ship a recorded session you can step through instead, generated in CI against a real build rather than captured by hand.

**CPython already contains three machine readable specifications of itself, and almost nobody teaches this.** `Grammar/python.gram` is the grammar. `Parser/Python.asdl` is the AST. `Python/bytecodes.c` is the interpreter semantics, written in a DSL that `Tools/cases_generator` compiles into the tier 1 interpreter, the tier 2 interpreter, the optimizer cases and every metadata table. CPython does not hand write its front end or its interpreter, it generates them. So the right architecture for a reimplementation is not to port the C, it is to add a backend, which is what the capstone does.

**The compiler is already exposed to Python.** `_testinternalcapi` exports `compiler_codegen`, `optimize_cfg` and `assemble_code_object` on a stock interpreter. You can run the CPython compiler one stage at a time, from a notebook, and diff the control flow graph before and after optimization, with no build. This is the best teaching hook in the codebase and no existing course uses it.

## What "compatible" is allowed to mean

Nobody has ever built a 100% compatible Python that is not CPython, and a project that claims otherwise gets taken apart in an afternoon, so the tiers are in the README rather than in a footnote.

| Tier | What it covers | Reachable |
|---|---|---|
| A | Language semantics: same results, same exceptions, same messages, same evaluation order | Yes, and this is the target |
| B | Introspection: `dis` output, code objects, line tables, exception tables, `ast.dump`, marshal | Mostly, and cheaply if you generate from CPython's own specs |
| C | The C API and ABI, so existing extension wheels load | No, not for a from scratch implementation, and the reasons are written down |
| D | `id()` values, exact refcounts, exact `getsizeof`, allocation addresses, scheduling, speed | No, and enumerating it is how you avoid wasting a week on it |

The capstone does not ship "it works". It ships a scorecard with a number, the failures enumerated, and each failure classified as a real semantic divergence or a tier D assertion. That is checkable by strangers, which a claim is not.

## Which CPython

Pinned to `v3.15.0rc1` today and moving to `v3.15.0` when it ships on 1 October 2026. Every code reference is written as `Python/ceval.c:1213@v3.15.0rc1#_PyEval_EvalFrameDefault` and checked by CI against the pinned tree, so when the pin moves we are told exactly which references broke instead of finding out from a reader. The trailing symbol is what makes that work: a bare line number drifts silently when upstream inserts a function above it, and the citation then points at something plausible and wrong, which is worse than pointing at nothing. A bot diffs every cited region against upstream weekly and files one issue per affected lesson.

3.15 is the right pin and the timing is good. It is the first release with a stable ABI for free threaded builds, it adds explicit lazy imports which drag a new object type through the grammar, the compiler, the import machinery and attribute lookup all at once, and its JIT is reported at 8 to 9 percent on x86-64 and 12 to 13 percent on AArch64 macOS. Pinning to 3.14 would mean rewriting the JIT chapter within a year.

## What is planned to be here

```
book/           the prose site, one directory per part
lessons/        marimo notebooks, the source of truth for every runnable cell
blueprints/     the normative specification, mechanical sections generated
anim/           manim scenes, built from one shared mobject library
apps/           the Gradio playgrounds
pyxray/         the instrumentation toolkit every lesson imports
xraywidgets/    anywidget components, one implementation for marimo and Jupyter
xraymanim/      the visual grammar, so a hundred animations look like one project
conformance/    the differential harness, the golden corpora and the scorecard
reimpl/go/      the Go reference implementation, which is the specification's test suite
reimpl/rust/    the Rust one, which is also the handoff to a serious runtime project
vendor/cpython/ the pinned submodule
```

## The plan

| | Milestone | What it ships |
|---|---|---|
| M0 | Foundations | The toolkit, the build matrix, the visual grammar, and one lesson built to the full bar |
| M1 | The Tourist | Twelve lessons, one day, browser only, the first public release |
| M2 | Toolchain | Building CPython five ways, the debugger, the test suite, and the pin moves to 3.15.0 |
| M3 | The front end | Tokenizer through code objects, and the compile explorer |
| M4 | The object model | Fourteen lessons and twelve blueprints, the largest content milestone |
| M5 | The interpreter | Dispatch, frames, zero cost exceptions, specialization, tier 2 and the JIT |
| M6 | Version bump rehearsal | Pay the maintenance cost early and measure it, while there are fifty lessons and not eighty five |
| M7 | Memory | obmalloc, reference counting, the cycle collector, and the free threaded collector |
| M8 | Concurrency and runtime | The GIL, free threading, subinterpreters, startup, import and the C API |
| M9 | Surgeon | Add an opcode, add syntax, break the GC on purpose, and build the conformance harness |
| M10 | Go | An implementation, a scorecard, and a bug filed against every blueprint that was not enough |
| M11 | Rust | A second implementation, which is the real test of whether the blueprints specify CPython |
| M12 | 1.0 | The numbers published with the failures named |

There are four sane places to stop and each one leaves something worth having. M1 alone is the best free introduction to CPython that exists. M5 covers what most readers actually want. M8 is complete coverage. M11 is the whole thing.

## Prior art

`InternalDocs/` in the CPython tree is upstream truth, maintained by the people who write the code, and nineteen documents is also a map of what they consider hard. We link to it and never paraphrase it. What it does not have is an on ramp, a runnable experiment or a picture, and that is the gap this fills.

Anthony Shaw's *CPython Internals* is the closest thing to a competitor and is good, particularly on the memory allocator. It is a book, so it is frozen against a Python from several releases ago, and everything after 3.11 is either absent or predates the current design. `zpoint/CPython-Internals` is deep and heavily illustrated and written against 3.8 era source. *Crafting Interpreters* is not about CPython and is still the best book on this subject, because every chapter is code the reader types, and it is the standard to hit.

The gap all of them share is the same: nothing that is current, sequenced, hands on, visual, and precise enough to reimplement from. Any two of those five exist. Not all five.

## Licence

Code is MIT. Prose, diagrams and animations are CC BY 4.0. Quoted CPython source is under the PSF Licence with the notice retained, and every excerpt carries its path, line and tag.
